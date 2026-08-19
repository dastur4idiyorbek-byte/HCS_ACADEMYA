"""3.9-band: Kunlik Sham Ochilishi Skalping (Opening Range Scalping).

Asosiy S/R strategiyasidan MUSTAQIL, qo'shimcha modul. Kuzatilgan bozor
xatti-harakati: yangi kunlik sham ochilganda (UTC 00:00), ko'p treyder shu
daqiqada kirib, narx qisqa muddatli 1-2% harakat qiladi.

Muhim xususiyatlar:
  - HAR KUNI ISHLASHI SHART EMAS — shart bajarilmasa o'tkazib yuboriladi
  - Alohida risk byudjeti bilan ishlaydi, lekin umumiy kunlik limitdan
    (5.1-band) oshib ketmaydi
  - Bir xil Risk Engine orqali nazorat qilinadi

HOLAT: interfeys tayyor, mantiq 12-bosqichda to'ldiriladi.
"""

from __future__ import annotations

from core.analysis.strategies.base import Strategy, StrategyInput
from core.config.schema import AppConfig
from core.domain.models import SignalCandidate


class OpeningRangeScalpStrategy(Strategy):
    name = "opening_range_scalp"

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @property
    def enabled(self) -> bool:
        return self._config.strategies.opening_range_scalp.enabled

    def required_timeframes(self) -> list[str]:
        return ["1m", "15m", "1d"]

    @property
    def daily_risk_share_pct(self) -> float:
        """Umumiy kunlik byudjetdan shu strategiyaga ajratilgan ulush."""
        return self._config.strategies.opening_range_scalp.daily_risk_share_pct

    def analyze(self, data: StrategyInput) -> SignalCandidate | None:
        raise NotImplementedError("opening_range_scalp mantig'i 12-bosqichda quriladi")
