"""Sozlamadagi HAR BIR timeframe yuklanadigan to'plamda bo'lishi shart.

Nima uchun bu test bor
----------------------
`risk_engine.btc_filter.timeframe` `"1h"` deb qolib ketgan edi. Kirish
timeframei 4h ga o'tgach, "1h" seriya umuman yuklanmay qoldi va
`BtcMarketRule` fail-safe tarmog'iga tushdi:

    "BTC holati noma'lum — umumiy bozor filtri tekshirilmadi."

Natijada ball chegarasidan o'tgan HAR BIR nomzod shu yerda to'xtadi —
jonli o'lchovda 119 tadan 119 tasi. Xato yo'q, log toza, tizim
shunchaki signal bermaydi.

Bu test aynan shu sinfni qulflaydi: sozlama yuklanmaydigan timeframega
ishora qilsa, darhol aytadi.
"""

from __future__ import annotations

import pytest

from core.analysis.strategies import build_strategies, required_timeframes
from core.config.schema import AppConfig


def _yuklanadigan(config: AppConfig) -> set[str]:
    """Sikl haqiqatda yuklaydigan timeframelar.

    `bot/services/runner.py` dagi `_load_candles()` bilan bir xil
    hisoblanadi: strategiyalar talabi + salomatlik timeframei.
    """
    return required_timeframes(build_strategies(config)) | {
        config.analysis.market_health_timeframe
    }


def _sozlamadagi(config: AppConfig) -> list[tuple[str, str]]:
    """`(sozlama yo'li, timeframe)` juftliklari."""
    analysis = config.analysis
    juftlar = [
        ("analysis.entry_timeframe", analysis.entry_timeframe),
        ("analysis.market_health_timeframe", analysis.market_health_timeframe),
        ("risk_engine.btc_filter.timeframe", config.risk_engine.btc_filter.timeframe),
        (
            "strategies.opening_range_scalp.timeframe",
            config.strategies.opening_range_scalp.timeframe,
        ),
    ]
    juftlar += [("analysis.htf_confirmation", tf) for tf in analysis.htf_confirmation]
    return juftlar


def test_tekshiruv_ozi_ishlaydi(config: AppConfig) -> None:
    """Test qurilmasi buzuq bo'lsa hamma narsa yashil ko'rinardi."""
    assert _yuklanadigan(config), "yuklanadigan to'plam bo'sh"
    assert len(_sozlamadagi(config)) >= 4


@pytest.mark.parametrize(
    ("yol", "timeframe"),
    _sozlamadagi(AppConfig()),
    ids=lambda q: q if isinstance(q, str) else str(q),
)
def test_sozlamadagi_timeframe_yuklanadi(yol: str, timeframe: str) -> None:
    """Sozlamada ko'rsatilgan timeframe haqiqatda yuklanishi kerak."""
    yuklanadi = _yuklanadigan(AppConfig())
    assert timeframe in yuklanadi, (
        f"{yol} = {timeframe!r}, lekin yuklanadiganlar: {sorted(yuklanadi)}.\n"
        "Bu seriya bo'sh keladi va unga tayangan qoida jimgina "
        "fail-safe holatiga tushadi — xato ko'rinmaydi, tizim ishlamaydi."
    )


def test_btc_filtri_kirish_timeframei_bilan_mos(config: AppConfig) -> None:
    """BTC filtri aynan shu sabab bir hafta hamma signalni bloklagan."""
    assert config.risk_engine.btc_filter.timeframe in _yuklanadigan(config)
