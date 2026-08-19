"""3.1-band: asosiy strategiya — Support/Resistance BIRINCHI, indikatorlar ikkinchi.

To'g'ri tartib (spetsifikatsiyaning markaziy arxitektura tuzatishi):
  1. AVVAL: narx grafigida muhim S/R zonalari aniqlanadi
  2. KEYIN: narx shu zonaga yaqinlashganda, indikatorlar zonani TASDIQLAYDIMI
     deb tekshiriladi
  3. Faqat "narx muhim S/R zonasida + indikatorlar tasdiqlayapti" bo'lsa
     signal ko'rib chiqiladi

Yolg'iz indikator-asosli signal ("RSI 30dan past chiqdi") YO'Q.

HOLAT: interfeys tayyor, mantiq 6–8-bosqichlarda to'ldiriladi
(S/R -> indikatorlar -> ball hisoblash), 7-bo'limdagi tartibga muvofiq.
"""

from __future__ import annotations

from core.analysis.strategies.base import Strategy, StrategyInput
from core.config.schema import AppConfig
from core.domain.models import SignalCandidate


class ClassicTaStrategy(Strategy):
    name = "classic_ta"

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @property
    def enabled(self) -> bool:
        return self._config.strategies.classic_ta.enabled

    def required_timeframes(self) -> list[str]:
        analysis = self._config.analysis
        return [analysis.entry_timeframe, *analysis.htf_confirmation]

    def analyze(self, data: StrategyInput) -> SignalCandidate | None:
        raise NotImplementedError(
            "classic_ta mantig'i 6–8-bosqichlarda quriladi: "
            "support_resistance -> indicators -> scoring"
        )
