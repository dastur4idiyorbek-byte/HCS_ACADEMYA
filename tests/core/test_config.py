"""Konfiguratsiya yuklovchisi va tekshiruvlari."""

from __future__ import annotations

import textwrap

import pytest

from core.config import ConfigError, load_config
from core.config.schema import AppConfig


def test_default_yaml_yuklanadi(config: AppConfig) -> None:
    assert config.project.name == "HALOL CRYPTO SAVDO"
    assert config.halal_screening.target_count == 30
    assert config.risk_engine.friday_filter.timezone == "Asia/Tashkent"


def test_ball_vaznlari_yigindisi_100(config: AppConfig) -> None:
    assert config.scoring.weights.total() == pytest.approx(100)


def test_sr_eng_katta_vaznga_ega(config: AppConfig) -> None:
    """3.1/3.5-band: S/R birlamchi omil — vazni eng yuqori bo'lishi SHART."""
    weights = config.scoring.weights
    boshqalar = [weights.trend, weights.rsi, weights.volume, weights.macd, weights.risk_reward]
    assert weights.support_resistance > max(boshqalar)


def test_bozor_salomatligi_vaznlari_yigindisi_100(config: AppConfig) -> None:
    assert config.market_health.weights.total() == pytest.approx(100)


def test_korrelyatsiya_guruhi_topiladi(config: AppConfig) -> None:
    assert config.risk_engine.correlation_group_of("btc") == "btc_major"
    assert config.risk_engine.correlation_group_of("ETH") == "btc_major"
    assert config.risk_engine.correlation_group_of("NOMAVJUD") is None


def test_notogri_vaznlar_rad_etiladi(tmp_path) -> None:
    yomon = tmp_path / "yomon.yaml"
    yomon.write_text(
        textwrap.dedent(
            """
            scoring:
              weights:
                support_resistance: 90
                trend: 90
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="yig'indisi 100"):
        load_config(yomon)


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
