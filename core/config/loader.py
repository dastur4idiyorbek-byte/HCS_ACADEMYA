"""Qatlamli konfiguratsiya yuklovchisi.

Qatlamlar (yuqoridagi pastdagini bosadi):
  1. Dataclass standart qiymatlari (`core/config/schema.py`)
  2. YAML fayli (`config/default.yaml`, `HCS_CONFIG_FILE` bilan almashtiriladi)
  3. Bazadagi admin sozlamalari (`risk_config` / `price_config`) — ishga tushgandan
     keyin `AppConfig.apply_overrides()` orqali qo'llaniladi

Nima uchun dataclass: konfiguratsiya tiplashtirilgan bo'lsa, noto'g'ri kalit
yoki yetishmayotgan qiymat ishga tushish paytida darhol xato beradi — signal
berish paytida emas (0.3-band: fail-safe).
"""

from __future__ import annotations

import dataclasses
import os
import types
import typing
from pathlib import Path
from typing import Any, TypeVar

import yaml

from core.config.schema import AppConfig

T = TypeVar("T")

DEFAULT_CONFIG_PATH = Path("config/default.yaml")
_ENV_CONFIG_VAR = "HCS_CONFIG_FILE"


class ConfigError(ValueError):
    """Konfiguratsiya noto'g'ri yoki to'liq emas."""


def _is_dataclass_type(tp: Any) -> bool:
    return isinstance(tp, type) and dataclasses.is_dataclass(tp)


def _unwrap_optional(tp: Any) -> Any:
    """`X | None` dan `X` ni ajratib oladi."""
    origin = typing.get_origin(tp)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def _build(cls: type[T], data: Any, path: str = "") -> T:
    """YAML lug'atidan dataclass quradi (ichma-ich, ro'yxatlar bilan)."""
    if data is None:
        return cls()  # type: ignore[call-arg]
    if not isinstance(data, dict):
        raise ConfigError(
            f"{path or cls.__name__}: lug'at (mapping) kutilgan, "
            f"{type(data).__name__} keldi"
        )

    hints = typing.get_type_hints(cls)
    known = {f.name for f in dataclasses.fields(cls)}

    unknown = set(data) - known
    if unknown:
        raise ConfigError(
            f"{path or cls.__name__}: noma'lum kalit(lar): {', '.join(sorted(unknown))}"
        )

    kwargs: dict[str, Any] = {}
    for field in dataclasses.fields(cls):
        if field.name not in data:
            continue
        raw = data[field.name]
        field_path = f"{path}.{field.name}" if path else field.name
        kwargs[field.name] = _coerce(hints[field.name], raw, field_path)

    try:
        return cls(**kwargs)  # type: ignore[call-arg]
    except TypeError as exc:  # pragma: no cover — himoya
        raise ConfigError(f"{path or cls.__name__}: {exc}") from exc


def _coerce(tp: Any, raw: Any, path: str) -> Any:
    """Bitta qiymatni e'lon qilingan tipga moslashtiradi."""
    tp = _unwrap_optional(tp)

    if _is_dataclass_type(tp):
        return _build(tp, raw, path)

    origin = typing.get_origin(tp)
    if origin in (list, typing.List):  # noqa: UP006
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ConfigError(f"{path}: ro'yxat kutilgan, {type(raw).__name__} keldi")
        (item_type,) = typing.get_args(tp) or (Any,)
        return [_coerce(item_type, item, f"{path}[{i}]") for i, item in enumerate(raw)]

    if tp is float and isinstance(raw, int) and not isinstance(raw, bool):
        return float(raw)
    return raw


def load_yaml(path: str | Path | None = None) -> dict[str, Any]:
    """YAML faylini o'qiydi. Fayl bo'lmasa — bo'sh lug'at (standartlar ishlaydi)."""
    resolved = Path(path or os.getenv(_ENV_CONFIG_VAR) or DEFAULT_CONFIG_PATH)
    if not resolved.exists():
        return {}
    with resolved.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{resolved}: ildizda lug'at kutilgan")
    return data


def load_config(path: str | Path | None = None) -> AppConfig:
    """`AppConfig` ni yuklaydi va tekshiradi."""
    config = _build(AppConfig, load_yaml(path))
    validate(config)
    return config


def validate(config: AppConfig) -> None:
    """Mantiqiy izchillikni tekshiradi — noto'g'ri sozlama bilan ishga tushmaslik uchun."""
    problems: list[str] = []

    if abs(config.scoring.weights.total() - 100) > 1e-9:
        problems.append(
            "scoring.weights yig'indisi 100 bo'lishi kerak, hozir: "
            f"{config.scoring.weights.total()}"
        )
    if abs(config.market_health.weights.total() - 100) > 1e-9:
        problems.append(
            "market_health.weights yig'indisi 100 bo'lishi kerak, hozir: "
            f"{config.market_health.weights.total()}"
        )

    thresholds = config.scoring.thresholds
    if thresholds.health_mid_min >= thresholds.health_high_min:
        problems.append("scoring.thresholds: health_mid_min < health_high_min bo'lishi kerak")

    rules = config.trade_rules
    if rules.min_tp_distance_pct > rules.max_tp_distance_pct:
        problems.append("trade_rules: min_tp_distance_pct > max_tp_distance_pct")
    if rules.max_stop_distance_pct <= 0:
        problems.append("trade_rules: max_stop_distance_pct musbat bo'lishi kerak")

    tiers = config.position_sizing.risk_tiers
    if not tiers:
        problems.append("position_sizing.risk_tiers bo'sh bo'lmasligi kerak")
    else:
        bounded = [t for t in tiers if t.max_balance is not None]
        if len(tiers) - len(bounded) != 1 or tiers[-1].max_balance is not None:
            problems.append(
                "position_sizing.risk_tiers: oxirgi pog'ona `max_balance: null` "
                "bo'lishi kerak (va faqat bittasi)"
            )
        limits = [t.max_balance for t in bounded]
        if limits != sorted(limits):
            problems.append(
                "position_sizing.risk_tiers: max_balance o'sish tartibida bo'lishi kerak"
            )
        if any(t.daily_risk_pct <= 0 for t in tiers):
            problems.append("position_sizing.risk_tiers: daily_risk_pct musbat bo'lishi kerak")

    method = config.position_sizing.allocation_method
    if method not in {"sequential_decay", "equal_split"}:
        problems.append(
            f"position_sizing.allocation_method noma'lum: {method!r} "
            "(ruxsat: 'sequential_decay', 'equal_split')"
        )
    fraction = config.position_sizing.sequential_decay_fraction
    if not 0 < fraction <= 1:
        problems.append(
            "position_sizing.sequential_decay_fraction (0, 1] oralig'ida bo'lishi kerak"
        )

    friday = config.risk_engine.friday_filter
    if not 0 <= friday.weekday <= 6:
        problems.append("risk_engine.friday_filter.weekday 0..6 oralig'ida bo'lishi kerak")
    try:
        # Faqat parslash tekshiriladi — noto'g'ri format ishga tushishda aniqlansin
        _ = (friday.start_time, friday.end_time)
    except ValueError as exc:
        problems.append(f"risk_engine.friday_filter: {exc}")

    ruxsat_etilgan_manbalar = {"coinmarketcap", "coingecko"}
    if config.market_data.ranking_source not in ruxsat_etilgan_manbalar:
        problems.append(
            f"market_data.ranking_source noma'lum: {config.market_data.ranking_source!r} "
            f"(ruxsat: {', '.join(sorted(ruxsat_etilgan_manbalar))})"
        )

    ruxsat_etilgan_birjalar = {"binance", "bybit"}
    if config.market_data.exchange not in ruxsat_etilgan_birjalar:
        problems.append(
            f"market_data.exchange noma'lum: {config.market_data.exchange!r} "
            f"(ruxsat: {', '.join(sorted(ruxsat_etilgan_birjalar))})"
        )

    analysis = config.analysis
    if analysis.entry_timeframe not in analysis.timeframes:
        problems.append("analysis.entry_timeframe `timeframes` ro'yxatida bo'lishi kerak")
    missing_htf = set(analysis.htf_confirmation) - set(analysis.timeframes)
    if missing_htf:
        problems.append(
            f"analysis.htf_confirmation `timeframes` da yo'q: {', '.join(sorted(missing_htf))}"
        )

    if problems:
        raise ConfigError("Konfiguratsiya xatolari:\n  - " + "\n  - ".join(problems))
