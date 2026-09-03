"""Konfiguratsiya yuklovchisi va tekshiruvlari."""

from __future__ import annotations

import textwrap

import pytest

from core.config import ConfigError, load_config
from core.config.schema import AppConfig


def test_default_yaml_yuklanadi(config: AppConfig) -> None:
    assert config.project.name == "HALOL CRYPTO SAVDO"
    assert config.halal_screening.target_count == 150
    assert config.risk_engine.friday_filter.timezone == "Asia/Tashkent"


def test_korrelyatsiya_guruhi_topiladi(config: AppConfig) -> None:
    assert config.risk_engine.correlation_group_of("btc") == "btc_major"
    assert config.risk_engine.correlation_group_of("ETH") == "btc_major"
    assert config.risk_engine.correlation_group_of("NOMAVJUD") is None


def test_eski_tahlil_bloklari_qolmagan(config: AppConfig) -> None:
    """2026-09-03: eski tahlil moduli bilan birga sozlamalari ham ketdi.

    Bu test yangi modul qurilganda ESKI nomlarni qayta ishlatib
    yubormaslik uchun turadi: `scoring`, `analysis`, `trade_rules`
    nomlari eski 100 balllik tizimni anglatardi.
    """
    for eski in ("analysis", "scoring", "trade_rules", "market_health", "strategies"):
        assert not hasattr(config, eski), f"{eski} bloki qaytib kelibdi"


def test_nomalum_kalit_rad_etiladi(tmp_path) -> None:
    """Terish xatosi jim o'tib ketmasligi kerak — noto'g'ri sozlama xavfli."""
    yomon = tmp_path / "yomon.yaml"
    yomon.write_text("halal_screening:\n  target_kount: 30\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="noma'lum kalit"):
        load_config(yomon)


def test_notogri_pogonalar_rad_etiladi(tmp_path) -> None:
    yomon = tmp_path / "yomon.yaml"
    yomon.write_text(
        textwrap.dedent(
            """
            position_sizing:
              risk_tiers:
                - {max_balance: 10000, daily_risk_pct: 2.0}
                - {max_balance: 1000, daily_risk_pct: 3.0}
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="o'sish tartibida|null"):
        load_config(yomon)


def test_mavjud_bolmagan_fayl_standartlarga_qaytadi(tmp_path) -> None:
    config = load_config(tmp_path / "yoq.yaml")
    assert config.project.name == "HALOL CRYPTO SAVDO"


def test_bozor_malumotlari_manbalari_tasdiqlangan(config: AppConfig) -> None:
    """Foydalanuvchi tanlagan qarorlar: Binance + CoinMarketCap."""
    assert config.market_data.exchange == "binance"
    assert config.market_data.ranking_source == "coinmarketcap"


def test_notogri_birja_rad_etiladi(tmp_path) -> None:
    yomon = tmp_path / "yomon.yaml"
    yomon.write_text("market_data:\n  exchange: kraken\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="exchange noma'lum"):
        load_config(yomon)


def test_notogri_reyting_manbai_rad_etiladi(tmp_path) -> None:
    yomon = tmp_path / "yomon.yaml"
    yomon.write_text("market_data:\n  ranking_source: messari\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="ranking_source noma'lum"):
        load_config(yomon)
