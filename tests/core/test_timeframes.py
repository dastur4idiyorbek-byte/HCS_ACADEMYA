"""3.2-band (tuzatilgan): timeframe to'plami va ko'p timeframe muvofiqligi."""

from __future__ import annotations

from core.analysis.strategies.classic_ta import ClassicTaStrategy
from core.config.schema import AppConfig
from core.domain.enums import TrendDirection
from core.domain.models import MultiTimeframeView, TimeframeTrend

#: Joriy to'plam. 15m/30m olib tashlandi: 15m da ATR narxning ~0.5% i,
#: ya'ni support zonasigacha masofa ham shuncha — Stop esa kamida 1%
#: bo'lishi kerak (3.3-band). Tuzilma va risk qoidasi turli shkalada
#: qolib, darajalar tez-tez rad etilardi (42-bo'lim).
STANDART = ["1h", "4h", "1d"]


def test_standart_toplam_ishlatiladi(config: AppConfig) -> None:
    assert config.analysis.timeframes == STANDART


def test_kirish_timeframe_eng_pastki(config: AppConfig) -> None:
    """S/R + indikatorlar eng pastki timeframeda hisoblanadi."""
    assert config.analysis.entry_timeframe == "1h"
    assert config.analysis.entry_timeframe == config.analysis.timeframes[0]


def test_tasdiqlovchi_timeframelar_qolganlari(config: AppConfig) -> None:
    """Katta rasm — 4h. Kunlik bu yerda emas: u salomatlik kengligi uchun."""
    assert config.analysis.htf_confirmation == ["4h"]


def test_salomatlik_timeframei_alohida(config: AppConfig) -> None:
    """Bozor kengligi tasdiq timeframelaridan MUSTAQIL o'lchanadi.

    Ansiz `compute_health()` kirish timeframeiga tushib ketardi va
    bozor kengligi soatlik o'lchovga aylanib, kun bo'yi tebranardi.
    """
    assert config.analysis.market_health_timeframe == "1d"
    assert config.analysis.market_health_timeframe not in config.analysis.htf_confirmation


def test_kirish_timeframe_tasdiqlovchilar_orasida_yoq(config: AppConfig) -> None:
    """Kirish TF o'zini tasdiqlamasligi kerak."""
    assert config.analysis.entry_timeframe not in config.analysis.htf_confirmation


def test_pozitsion_timeframelar_zaxirada(config: AppConfig) -> None:
    """Yuqori TF'lar kelajakdagi pozitsion strategiya uchun saqlanadi."""
    assert "1w" in config.analysis.positional_timeframes
    assert "1M" in config.analysis.positional_timeframes
    assert "1w" not in config.analysis.timeframes


def test_klassik_strategiya_kirish_va_tasdiqni_soraydi(config: AppConfig) -> None:
    assert ClassicTaStrategy(config).required_timeframes() == ["1h", "4h"]


def test_barcha_timeframelar_bir_xil_trendda_bolishi_tekshiriladi() -> None:
    """Qat'iy qoida: pastki TF yuqorisiga zid bo'lmasligi kerak."""
    kotarilish = MultiTimeframeView(
        [TimeframeTrend(tf, TrendDirection.UP) for tf in STANDART]
    )
    assert kotarilish.all_aligned(TrendDirection.UP)

    zid = MultiTimeframeView(
        [
            TimeframeTrend("1h", TrendDirection.UP),
            TimeframeTrend("4h", TrendDirection.DOWN),
            TimeframeTrend("1d", TrendDirection.UP),
        ]
    )
    assert not zid.all_aligned(TrendDirection.UP)
    assert zid.direction_of("4h") is TrendDirection.DOWN
    assert zid.alignment_ratio(TrendDirection.UP) == 2 / 3, (
        "to'siq emas, DARAJA: 3 tadan 2 tasi mos"
    )


def test_bosh_korinish_muvofiq_emas() -> None:
    """Ma'lumot yo'q bo'lsa "hammasi mos" deb qaralmasligi kerak (fail-safe)."""
    assert not MultiTimeframeView([]).all_aligned(TrendDirection.UP)
