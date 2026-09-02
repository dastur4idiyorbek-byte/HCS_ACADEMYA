"""3.7-band: Bozor Salomatligi Indeksi — tizimning markaziy pulsi.

Formula (har sham yopilganda qayta hisoblanadi, 0-100):
    BTC Dominance holati (barqarormi, keskin o'zgaryaptimi)
  + Halol ro'yxatdagi coinlarning umumiy trend yo'nalishi
  + Volatillik rejimi (ADX)
  + Agregat foydalanuvchi sig'imi (5.2-band)
  + Faol signallar to'yinganlik darajasi

Natija:
    🟢 80-100 — chegara past (erkin)
    🟡 40-79  — ehtiyotkorroq (chegara balandroq)
    🔴 0-39   — yangi signal to'xtaydi, faqat kuzatuv

Indeks quyidagilarni boshqaradi:
  - `RiskEngine.score_threshold()` — minimal ball chegarasi (3.5)
  - `MaxOpenSignalsRule` — bir vaqtda ochiq signallar soni (4.2)
  - `MarketHealthRule` — 40 dan past bo'lsa signal umuman yo'q (4.9)
"""

from core.analysis.market_health.breadth import UniverseFacts, universe_facts
from core.analysis.market_health.calculator import MarketHealthCalculator, describe
from core.analysis.market_health.factors import build_factors
from core.analysis.market_health.inputs import HealthInputs

__all__ = [
    "HealthInputs",
    "MarketHealthCalculator",
    "UniverseFacts",
    "build_factors",
    "describe",
    "universe_facts",
]
