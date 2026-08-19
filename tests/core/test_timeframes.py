"""3.2-band (tuzatilgan): timeframe to'plami va ko'p timeframe muvofiqligi."""

from __future__ import annotations

from core.analysis.strategies.classic_ta import ClassicTaStrategy
from core.config.schema import AppConfig
from core.domain.enums import TrendDirection
from core.domain.models import MultiTimeframeView, TimeframeTrend

STANDART = ["15m", "30m", "1h", "4h", "1d"]


def test_standart_toplam_ishlatiladi(config: AppConfig) -> None:
    """Eski to'plam (1h..1oy) signal chastotasini keskin kamaytirardi."""
    assert config.analysis.timeframes == STANDART


def test_kirish_timeframe_eng_pastki(config: AppConfig) -> None:
    """S/R + indikatorlar eng pastki timeframeda tasdiqlanadi."""
    assert config.analysis.entry_timeframe == "15m"
    assert config.analysis.entry_timeframe == config.analysis.timeframes[0]


def test_tasdiqlovchi_timeframelar_qolganlari(config: AppConfig) -> None:
    assert config.analysis.htf_confirmation == STANDART[1:]


def test_kirish_timeframe_tasdiqlovchilar_orasida_yoq(config: AppConfig) -> None:
    """Kirish TF o'zini tasdiqlamasligi kerak."""
    assert config.analysis.entry_timeframe not in config.analysis.htf_confirmation


def test_pozitsion_timeframelar_zaxirada(config: AppConfig) -> None:
    """Yuqori TF'lar kelajakdagi pozitsion strategiya uchun saqlanadi."""
    assert "1w" in config.analysis.positional_timeframes
    assert "1M" in config.analysis.positional_timeframes
    assert "1w" not in config.analysis.timeframes


def test_klassik_strategiya_standart_toplamni_soraydi(config: AppConfig) -> None:
    assert ClassicTaStrategy(config).required_timeframes() == STANDART


def test_barcha_timeframelar_bir_xil_trendda_bolishi_tekshiriladi() -> None:
    """Qat'iy qoida: pastki TF yuqorisiga zid bo'lmasligi kerak."""
    kotarilish = MultiTimeframeView(
        [TimeframeTrend(tf, TrendDirection.UP) for tf in STANDART]
    )
    assert kotarilish.all_aligned(TrendDirection.UP)

    zid = MultiTimeframeView(
        [
            TimeframeTrend("15m", TrendDirection.UP),
            TimeframeTrend("30m", TrendDirection.UP),
            TimeframeTrend("1h", TrendDirection.UP),
            TimeframeTrend("4h", TrendDirection.DOWN),
            TimeframeTrend("1d", TrendDirection.UP),
        ]
    )
    assert not zid.all_aligned(TrendDirection.UP)
    assert zid.direction_of("4h") is TrendDirection.DOWN


def test_bosh_korinish_muvofiq_emas() -> None:
    """Ma'lumot yo'q bo'lsa "hammasi mos" deb qaralmasligi kerak (fail-safe)."""
    assert not MultiTimeframeView([]).all_aligned(TrendDirection.UP)
