"""Strategiya modullari (plug-in arxitekturasi, 6.1-band).

Mavjud:
  - `classic_ta`            — asosiy S/R + indikator strategiyasi (3.1-band)
  - `opening_range_scalp`   — kunlik sham ochilishi skalpingi (3.9-band)
  - `correction_entry`      — pasayishdagi tuzilmaviy kirish (3.10-band)
  - `narx_harakati`         — yorish -> qayta sinov -> tasdiq
                              (`docs/NARX_HARAKATI_STRATEGIYALARI.md`)

Yangi strategiya qo'shish uchun `registry.py` ga qarang: bitta fayl va
bitta ro'yxat yozuvi kifoya.
"""

from core.analysis.strategies.base import Strategy, StrategyInput
from core.analysis.strategies.classic_ta import ClassicTaStrategy
from core.analysis.strategies.narx_harakati_strategiya import NarxHarakatiStrategy
from core.analysis.strategies.opening_range_scalp import OpeningRangeScalpStrategy
from core.analysis.strategies.registry import build_strategies, required_timeframes

__all__ = [
    "ClassicTaStrategy",
    "NarxHarakatiStrategy",
    "OpeningRangeScalpStrategy",
    "Strategy",
    "StrategyInput",
    "build_strategies",
    "required_timeframes",
]
