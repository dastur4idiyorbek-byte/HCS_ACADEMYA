"""3.1-band: indikatorlar — S/R zonasini TASDIQLOVCHI qatlam.

MUHIM: bu modul mustaqil signal manbai EMAS. U faqat "narx muhim S/R
zonasida va Discount zonada" degan holat aniqlangandan keyin chaqiriladi
va shu holatni tasdiqlaydimi degan savolga javob beradi.

Yolg'iz "RSI 30dan past chiqdi" kabi indikator-asosli signal YO'Q.

    volatility.py    — ATR (o'lchov birligi, 6-bosqichda qo'shilgan)
    trend.py         — EMA50/EMA200, ADX
    momentum.py      — RSI(14), MACD(12/26/9)
    volume.py        — hajm o'rtachasi va nisbati
    snapshot.py      — barcha qiymatlarni bitta obyektga yig'ish
    confirmation.py  — S/R holatini tasdiqlash hukmi
"""

from core.analysis.indicators.confirmation import (
    Confirmation,
    ConfirmationFactor,
    confirm,
)
from core.analysis.indicators.momentum import (
    MacdResult,
    macd,
    rsi,
    rsi_recovering_from_oversold,
    rsi_series,
)
from core.analysis.indicators.snapshot import IndicatorSnapshot, build_snapshot
from core.analysis.indicators.trend import (
    adx,
    ema,
    ema_series,
    is_trending,
    timeframe_trend,
    trend_direction,
)
from core.analysis.indicators.volatility import atr, atr_pct, true_range, true_ranges
from core.analysis.indicators.volume import volume_average, volume_confirms, volume_ratio

__all__ = [
    "Confirmation",
    "ConfirmationFactor",
    "IndicatorSnapshot",
    "MacdResult",
    "adx",
    "atr",
    "atr_pct",
    "build_snapshot",
    "confirm",
    "ema",
    "ema_series",
    "is_trending",
    "macd",
    "rsi",
    "rsi_recovering_from_oversold",
    "rsi_series",
    "timeframe_trend",
    "trend_direction",
    "true_range",
    "true_ranges",
    "volume_average",
    "volume_confirms",
    "volume_ratio",
]
