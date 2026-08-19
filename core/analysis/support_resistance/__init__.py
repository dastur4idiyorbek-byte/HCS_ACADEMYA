"""3.1-band: Support/Resistance zonalarini aniqlash — BIRLAMCHI tahlil.

Tahlil EMA/RSI/MACD'dan emas, aynan shu moduldan boshlanadi. Aniqlanadi:
  - swing pivotlar (tarixiy burilish nuqtalari)
  - yaqin pivotlarni birlashtirish orqali ZONALAR (nuqta emas, oraliq)
  - har bir zona necha marta test qilingani
  - Fibonacci 38.2% / 50% / 61.8% — YORDAMCHI sifatida

Chiqadigan tip: `ZoneMap` (`core.domain.models.SRZone` ro'yxati bilan).
"""

from core.analysis.support_resistance.detector import SupportResistanceDetector, ZoneMap
from core.analysis.support_resistance.fibonacci import (
    SwingRange,
    fibonacci_levels,
    find_swing_range,
)
from core.analysis.support_resistance.pivots import Pivot, count_touches, find_pivots

__all__ = [
    "Pivot",
    "SupportResistanceDetector",
    "SwingRange",
    "ZoneMap",
    "count_touches",
    "fibonacci_levels",
    "find_pivots",
    "find_swing_range",
]
