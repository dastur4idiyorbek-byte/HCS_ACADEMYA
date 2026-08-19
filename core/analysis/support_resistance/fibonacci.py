"""Fibonacci retracement darajalari — YORDAMCHI vosita.

3.1-band: Fibonacci mustaqil signal manbai emas. U pivotlardan olingan
zonalarni to'ldiradi: agar muhim Fibonacci darajasi allaqachon mavjud
zonaga to'g'ri kelsa, bu zonaning ishonchliligini oshiradi.

Yolg'iz Fibonacci darajasi (hech qanday pivot tasdiqlamagan) zaif dalil —
shuning uchun bunday zonalar `from_fibonacci=True` bilan belgilanadi va
ball hisoblashda (8-bosqich) pastroq baholanadi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.domain.models import Candle


@dataclass(frozen=True, slots=True)
class SwingRange:
    """Fibonacci hisoblanadigan narx diapazoni."""

    low: float
    high: float
    low_index: int
    high_index: int

    @property
    def size(self) -> float:
        return self.high - self.low

    @property
    def is_uptrend(self) -> bool:
        """Chuqurlik cho'qqidan OLDIN kelgan bo'lsa — ko'tarilish harakati."""
        return self.low_index < self.high_index


def find_swing_range(candles: list[Candle], lookback: int | None = None) -> SwingRange | None:
    """Oxirgi muhim harakat diapazonini topadi (eng past va eng baland nuqta)."""
    oyna = candles if lookback is None else candles[-lookback:]
    if len(oyna) < 2:
        return None

    past_index = min(range(len(oyna)), key=lambda i: oyna[i].low)
    baland_index = max(range(len(oyna)), key=lambda i: oyna[i].high)

    diapazon = SwingRange(
        low=oyna[past_index].low,
        high=oyna[baland_index].high,
        low_index=past_index,
        high_index=baland_index,
    )
    return diapazon if diapazon.size > 0 else None


def fibonacci_levels(
    swing: SwingRange,
    ratios: list[float],
) -> list[tuple[float, float]]:
    """Retracement darajalarini hisoblaydi.

    Ko'tarilish harakatida (low -> high) narx qaytib tushganda qo'llab-
    quvvatlash izlaydi: `high - diapazon × nisbat`.
    Tushish harakatida esa qarshilik izlanadi: `low + diapazon × nisbat`.

    Returns:
        `(nisbat, narx)` juftliklari.
    """
    if swing.size <= 0:
        return []

    if swing.is_uptrend:
        return [(nisbat, swing.high - swing.size * nisbat) for nisbat in ratios]
    return [(nisbat, swing.low + swing.size * nisbat) for nisbat in ratios]
