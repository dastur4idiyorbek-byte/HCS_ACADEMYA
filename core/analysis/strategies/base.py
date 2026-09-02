"""6.1-band: strategiya "plug-in" interfeysi.

Barcha strategiyalar (`classic_ta`, `opening_range_scalp` va kelajakdagilar)
BIR XIL interfeysga ega bo'lishi kerak — Risk Engine ularni bir xil tarzda
chaqiradi. Yangi strategiya qo'shish uchun shu papkaga yangi fayl qo'shish
kifoya, boshqa hech qayerni o'zgartirish shart emas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from core.analysis.market_structure import MarketStructure, analyze_structure
from core.config.schema import MarketStructureConfig
from core.domain.models import Candle, HalalVerdict, MarketHealth, SignalCandidate


@dataclass(slots=True)
class StrategyInput:
    """Strategiyaga beriladigan barcha ma'lumot.

    Strategiya tarmoqqa yoki bazaga MUROJAAT QILMAYDI — faqat shu obyektdan
    o'qiydi. Shu sababli har bir strategiya backtestda ham, jonli rejimda ham
    bir xil kod bilan ishlaydi (6.3-band talabi).

    FAKT QATLAMI. Struktura (HH/HL/BOS) shu yerda BIR MARTA hisoblanadi
    va keshlanadi. Ilgari uni har bir strategiya o'zi hisoblardi —
    `analyze_structure()` yettita joyda chaqirilardi va bitta fakt
    haqida yettita javob bo'lishi mumkin edi. Aynan shu turkumdagi
    farq backtest bilan jonli tizimni uch marta ajratib yubordi
    (`docs/ARXITEKTURA.md`, 68 va 69-bo'limlar).

    Endi bitta coin uchun bitta kirish quriladi va barcha strategiyalar
    o'sha bitta faktni o'qiydi.
    """

    symbol: str
    now: datetime
    halal_verdict: HalalVerdict
    # timeframe -> shamlar (eng eskisidan eng yangisiga)
    candles: dict[str, list[Candle]] = field(default_factory=dict)
    market_health: MarketHealth | None = None
    #: Struktura qanday o'qilishi — BITTA sozlama, barcha strategiya uchun
    structure_config: MarketStructureConfig = field(
        default_factory=MarketStructureConfig
    )
    #: timeframe -> hisoblangan struktura (ichki kesh, qo'lda to'ldirilmaydi)
    _structures: dict[str, MarketStructure] = field(default_factory=dict, repr=False)

    def series(self, timeframe: str) -> list[Candle]:
        return self.candles.get(timeframe, [])

    def last_price(self, timeframe: str) -> float | None:
        seriya = self.series(timeframe)
        return seriya[-1].close if seriya else None

    def structure(self, timeframe: str) -> MarketStructure:
        """Shu timeframedagi struktura — bir marta hisoblanadi.

        Strategiyalar `analyze_structure()` ni O'ZLARI chaqirmasligi
        kerak: sozlama bitta joyda turadi va ikki strategiya bir xil
        sham qatori haqida boshqa-boshqa javob bera olmaydi.
        """
        keshlangan = self._structures.get(timeframe)
        if keshlangan is None:
            sozlama = self.structure_config
            keshlangan = analyze_structure(
                self.series(timeframe),
                sozlama.swing_lookback,
                sozlama.min_swings,
                sozlama.fallback_min_pct,
            )
            self._structures[timeframe] = keshlangan
        return keshlangan


class Strategy(ABC):
    """Barcha strategiyalar uchun umumiy shartnoma."""

    #: Konfiguratsiya va loglarda ishlatiladigan barqaror nom
    name: str = "strategy"

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Strategiya konfiguratsiyada yoqilganmi."""

    @abstractmethod
    def required_timeframes(self) -> list[str]:
        """Qaysi timeframelar kerak — ma'lumot yuklovchi shu ro'yxatga tayanadi."""

    @abstractmethod
    def analyze(self, data: StrategyInput) -> SignalCandidate | None:
        """Nomzod qaytaradi yoki `None`.

        `None` — bu XATO EMAS, normal holat (0.2-band): "hozir signal berish
        to'g'ri emas" degani. Strategiya hech qachon signal berishga
        MAJBURLANMAYDI.
        """
