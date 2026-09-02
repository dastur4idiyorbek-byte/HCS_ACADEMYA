"""Bozor kengligi: nechta halol coin KO'TARILISHDA.

Bu — Bozor Salomatligi Indeksining ASOSIY omili (3.7-band). Uni ikki
joy hisoblaydi: jonli tizim (`bot/services/runner.py`) va backtest
(`core/backtest/engine.py`).

NIMA UCHUN ALOHIDA MODUL. Ikkisi hisobni O'ZIDA takrorlaganda ular
jimgina ajralib ketardi. Bu mavhum xavf emas — aynan shunday bo'ldi:
jonli tizim haftalik strukturani, backtest esa 4 soatlikni o'qiyotgan
edi va farq faqat backtest jonli natijaga umuman o'xshamagach
topildi (`docs/ARXITEKTURA.md`, 68-bo'lim).

Endi ikkalasi shu bitta funksiyani chaqiradi. Ajralish uchun joy
qolmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.analysis.indicators import adx
from core.analysis.market_structure import analyze_structure
from core.config.schema import AnalysisConfig
from core.domain.enums import TrendDirection
from core.domain.models import Candle


@dataclass(frozen=True, slots=True)
class UniverseFacts:
    """Butun halol ro'yxat bo'yicha o'lchangan faktlar."""

    #: coin -> struktura yo'nalishi
    structures: dict[str, TrendDirection] = field(default_factory=dict)
    #: coin -> ADX qiymati
    adx_values: dict[str, float] = field(default_factory=dict)


def universe_facts(
    candles: dict[str, dict[str, list[Candle]]],
    analysis: AnalysisConfig,
) -> UniverseFacts:
    """Har bir coin uchun struktura yo'nalishi va ADX.

    Args:
        candles: coin -> timeframe -> shamlar.
        analysis: qaysi timeframe va qanday chegaralar.

    Struktura SALOMATLIK timeframeida o'lchanadi. Ma'lumot bo'lmasa
    kirish timeframeiga qaytadi — bu jonli tizimdagi xatti-harakat va
    backtest ham aynan shunday qilishi kerak.

    Tarixi yetarli bo'lmagan coin hisobga UMUMAN kirmaydi (0.3-band:
    noaniqlik dalil emas). Chegara `min_candles`: u ilgari 200 edi va
    haftalik timeframeda ~3.8 yil tarix talab qilardi — ko'p altcoin
    jimgina "ko'tarilishda emas" deb sanalardi va kenglik sun'iy
    tushardi (33-bo'lim).
    """
    salomatlik_tf = analysis.market_health_timeframe
    kirish_tf = analysis.entry_timeframe
    indikator = analysis.indicators
    struktura_sozlamasi = analysis.market_structure

    strukturalar: dict[str, TrendDirection] = {}
    adx_qiymatlari: dict[str, float] = {}

    for symbol, tf_shamlar in candles.items():
        seriya = tf_shamlar.get(salomatlik_tf) or tf_shamlar.get(kirish_tf, [])
        if len(seriya) < indikator.min_candles:
            continue

        strukturalar[symbol] = analyze_structure(
            seriya,
            struktura_sozlamasi.swing_lookback,
            struktura_sozlamasi.min_swings,
            struktura_sozlamasi.fallback_min_pct,
        ).direction

        qiymat = adx(seriya, indikator.adx_period)
        if qiymat is not None:
            adx_qiymatlari[symbol] = qiymat

    return UniverseFacts(structures=strukturalar, adx_values=adx_qiymatlari)
