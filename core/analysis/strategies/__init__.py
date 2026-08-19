"""Strategiya modullari (plug-in arxitekturasi, 6.1-band).

Mavjud:
  - `classic_ta`            — asosiy S/R + indikator strategiyasi (3.1-band)
  - `opening_range_scalp`   — kunlik sham ochilishi skalpingi (3.9-band)
"""

from core.analysis.strategies.base import Strategy, StrategyInput

__all__ = ["Strategy", "StrategyInput"]
