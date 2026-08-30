"""Sof domain modellari — modullar o'rtasidagi umumiy "til".

Bu obyektlar hech qanday tashqi kutubxonaga (aiogram, SQLAlchemy) bog'liq
emas. DB modellari (`core/storage/models.py`) va Telegram qatlami shularni
o'zaro aylantiradi. Sabab: 0.1-band — "miya" va "tana" qat'iy ajratilgan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.domain.enums import (
    BlockReason,
    ExitOrderType,
    HalalStatus,
    HealthBand,
    OrderType,
    SignalSource,
    SignalStatus,
    TrendDirection,
    ZoneKind,
)

# --------------------------------------------------------------------------- #
#  Bozor ma'lumotlari
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Candle:
    """Bitta OHLCV sham."""

    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool = True

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open


@dataclass(frozen=True, slots=True)
class PriceTick:
    """WebSocket'dan kelgan bitta narx nuqtasi."""

    symbol: str
    price: float
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class MarketRankEntry:
    """Kapitalizatsiya reytingidagi bitta yozuv (CoinGecko/CMC)."""

    rank: int
    symbol: str
    name: str
    market_cap_usd: float
    volume_24h_usd: float


# --------------------------------------------------------------------------- #
#  3.4 — Halol skrining
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class HalalVerdict:
    """Bitta coin bo'yicha halollik qarori.

    `reason` — 3.6-banddagi "Nega bu coin halol?" tugmasi uchun matn manbai.
    """

    symbol: str
    status: HalalStatus
    reason: str

    @property
    def is_tradable(self) -> bool:
        return self.status.is_tradable


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    """3.4-band natijasi — halol ro'yxat va uning izohi."""

    symbols: list[str]
    verdicts: list[HalalVerdict]
    scanned_depth: int
    generated_at: datetime
    complete: bool                       # kerakli songa yetildimi
    skipped: list[HalalVerdict] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.symbols)


# --------------------------------------------------------------------------- #
#  3.1 — Support / Resistance
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SRZone:
    """Support yoki Resistance zonasi (nuqta emas, oraliq)."""

    kind: ZoneKind
    low: float
    high: float
    touches: int
    last_touch: datetime | None = None
    from_fibonacci: bool = False

    @property
    def center(self) -> float:
        return (self.low + self.high) / 2

    @property
    def width(self) -> float:
        return self.high - self.low

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high

    def distance_to(self, price: float) -> float:
        """Narxdan zonagacha masofa (zona ichida bo'lsa 0)."""
        if self.contains(price):
            return 0.0
        return self.low - price if price < self.low else price - self.high


# --------------------------------------------------------------------------- #
#  3.2 — Ko'p timeframe
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class TimeframeTrend:
    timeframe: str
    direction: TrendDirection
    adx: float | None = None


@dataclass(frozen=True, slots=True)
class MultiTimeframeView:
    """3.2-band: pastki TF yuqori TF ga zid bo'lmasligi kerak."""

    trends: list[TimeframeTrend]

    def direction_of(self, timeframe: str) -> TrendDirection | None:
        for trend in self.trends:
            if trend.timeframe == timeframe:
                return trend.direction
        return None

    def all_aligned(self, direction: TrendDirection) -> bool:
        return bool(self.trends) and all(t.direction is direction for t in self.trends)

    def alignment_ratio(self, direction: TrendDirection) -> float | None:
        """Timeframelarning qanchasi shu yo'nalishda (0..1).

        `all_aligned()` "hammasi yoki hech biri" deb javob beradi — bu
        to'siq uchun mos edi. Ball uchun esa DARAJA kerak: 4 tadan 3 tasi
        ko'tarilishda bo'lsa, bu 4 tadan 0 tasi bilan bir xil emas
        (3.5-band: "bor/yo'q" emas, darajali).

        `None` — timeframe umuman yo'q, ya'ni hisoblab bo'lmaydi.
        """
        if not self.trends:
            return None
        mos = sum(1 for t in self.trends if t.direction is direction)
        return mos / len(self.trends)


# --------------------------------------------------------------------------- #
#  3.5 — Ball tizimi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    """Bitta omil bo'yicha ball — darajali (graduated), "bor/yo'q" emas."""

    name: str
    earned: float
    maximum: float
    explanation: str
    #: BONUS omilmi — bazaviy 100 ballik tizimdan TASHQARIDA.
    #:
    #: CryptoSpot3% omillari (struktura, sweep, Kill Zone) ball
    #: BERADI, lekin bermasligi ham normal. "Nega bu signal?" ekrani
    #: topilmagan bonusni umuman ko'rsatmaydi: bo'sh "yo'q" qatori
    #: foydalanuvchini chalkashtiradi.
    bonus: bool = False

    @property
    def ratio(self) -> float:
        return self.earned / self.maximum if self.maximum else 0.0


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """3.6-band: "Nega bu signal?" tugmasi shu obyektdan to'ldiriladi."""

    symbol: str
    components: list[ScoreComponent]
    #: CryptoSpot3% shartnomasi TO'LIQ bajarilganmi — YORLIQ, darvoza
    #: emas. Signal bilan birga saqlanadi, chunki keyinroq qayta
    #: hisoblab bo'lmaydi (bozor holati o'zgargan bo'ladi).
    setup_complete: bool = False

    @property
    def total(self) -> float:
        return sum(c.earned for c in self.components)

    @property
    def maximum(self) -> float:
        return sum(c.maximum for c in self.components)

    @property
    def base_total(self) -> float:
        """Faqat bazaviy omillar — chegara SHU shkalada o'lchangan.

        Chegaralar (50/55) `scripts.kalibrlash` bilan 100 ballik
        bazaviy shkalada o'lchangan. Bonuslar shkalani 125 ga
        kengaytiradi, ya'ni ular faqat nomzodni YUQORIGA suradi.
        """
        return sum(c.earned for c in self.components if not c.bonus)

    @property
    def bonus_total(self) -> float:
        return sum(c.earned for c in self.components if c.bonus)

    def component(self, name: str) -> ScoreComponent | None:
        for item in self.components:
            if item.name == name:
                return item
        return None


# --------------------------------------------------------------------------- #
#  Signal
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SignalLevels:
    """Signal narx darajalari. Faqat spot/long: Stop < Entry < TP1 < TP2."""

    entry: float
    stop: float
    tp1: float
    tp2: float

    def __post_init__(self) -> None:
        if not (self.stop < self.entry < self.tp1 < self.tp2):
            raise ValueError(
                "Darajalar tartibi noto'g'ri. Spot/long uchun shart: "
                f"Stop({self.stop}) < Entry({self.entry}) < TP1({self.tp1}) < TP2({self.tp2})"
            )
        if self.stop <= 0:
            raise ValueError("Narx musbat bo'lishi kerak")

    @property
    def stop_distance_pct(self) -> float:
        """Entry'dan Stop'gacha masofa, foizda (3.3-band: 1% dan oshmasligi kerak)."""
        return (self.entry - self.stop) / self.entry * 100

    @property
    def tp1_distance_pct(self) -> float:
        return (self.tp1 - self.entry) / self.entry * 100

    @property
    def tp2_distance_pct(self) -> float:
        return (self.tp2 - self.entry) / self.entry * 100

    @property
    def risk_reward_tp2(self) -> float:
        """TP2 kamida 1:3 bo'lishi kerak (3.3-band)."""
        return (self.tp2 - self.entry) / (self.entry - self.stop)


@dataclass(frozen=True, slots=True)
class EntryPlan:
    """5.1.0-band: kirish rejasi — buyurtma turi va uning sababi.

    Chiqish har doim OCO (TP + Stop birgalikda), shuning uchun u yerda
    tanlov yo'q — `exit_order_type` doim `OCO`.
    """

    order_type: OrderType
    entry_price: float
    current_price: float
    distance_pct: float
    reason: str
    is_valid: bool = True
    exit_order_type: ExitOrderType = ExitOrderType.OCO


@dataclass(slots=True)
class Signal:
    """Yaratilgan yoki kuzatilayotgan signal."""

    symbol: str
    levels: SignalLevels
    source: SignalSource
    entry_plan: EntryPlan | None = None
    status: SignalStatus = SignalStatus.PENDING
    score: float | None = None
    breakdown: ScoreBreakdown | None = None
    halal_reason: str | None = None
    note: str | None = None
    created_at: datetime | None = None
    activated_at: datetime | None = None
    closed_at: datetime | None = None
    signal_id: int | None = None
    #: TP1 ga bir marta yetganmi. Nima uchun `status` yetarli emas: TP1 dan
    #: keyin narx Stop'ga tushsa, `status` STOPPED bo'lib qoladi va "TP1
    #: olingan edi" fakti yo'qoladi — qismli sotish esa hisobga olinishi
    #: kerak (5.4-band).
    tp1_reached: bool = False

    @property
    def correlation_symbol(self) -> str:
        return self.symbol.upper()

    @property
    def effective_stop(self) -> float:
        """AMALDAGI Stop — TP1 olingach kirish narxiga ko'tariladi.

        Nima uchun: TP1 da pozitsiyaning bir qismi sotiladi va qo'lda
        foyda qoladi. Qolgan qismni eski Stopda ushlab turish shu
        foydani qaytarib berish xavfini saqlaydi. Stop kirish narxiga
        ko'tarilsa, eng yomon holat — nolga chiqish (breakeven), ya'ni
        olingan TP1 foydasi himoyalanadi.

        Bu SPOT uchun ayniqsa mos: leverage yo'q, ya'ni pozitsiyani
        "nolda" yopish haqiqatan ham zararsiz chiqish.
        """
        return self.levels.entry if self.tp1_reached else self.levels.stop

    @property
    def stop_at_breakeven(self) -> bool:
        """Stop kirish narxiga ko'tarilganmi — ekranda shu bilan aytiladi."""
        return self.tp1_reached and self.effective_stop != self.levels.stop


@dataclass(frozen=True, slots=True)
class SignalCandidate:
    """Risk Engine'ga taqdim etiladigan nomzod (hali signal emas)."""

    symbol: str
    levels: SignalLevels
    source: SignalSource
    breakdown: ScoreBreakdown
    halal_verdict: HalalVerdict
    entry_plan: EntryPlan | None = None
    #: CryptoSpot3% MUSTAQIL kirish shartnomasi bajarildimi (B yo'li).
    #:
    #: `core.analysis.scoring.setup_route.SetupVerdict` — bu yerda tip
    #: yozilmaydi, chunki `core/domain/` tahlil modullariga bog'liq
    #: bo'lmasligi kerak (0.1-band: "miya" va "tana" ajratilgan, domen
    #: esa ikkalasidan ham quyida turadi).
    setup: object | None = None

    @property
    def score(self) -> float:
        return self.breakdown.total

    @property
    def setup_qualified(self) -> bool:
        """Metodika shartnomasi to'liq bajarilganmi."""
        return bool(getattr(self.setup, "qualified", False))


# --------------------------------------------------------------------------- #
#  4 — Risk Engine natijasi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Risk Engine qarori.

    0.3-band (fail-safe): noaniqlik bo'lsa `allowed=False`. Har bir rad etish
    sababi `reasons` da — log va admin dashboard uchun.
    """

    allowed: bool
    reasons: list[BlockReason] = field(default_factory=list)
    details: list[str] = field(default_factory=list)

    @classmethod
    def allow(cls) -> RiskDecision:
        return cls(allowed=True)

    @classmethod
    def block(cls, reason: BlockReason, detail: str) -> RiskDecision:
        return cls(allowed=False, reasons=[reason], details=[detail])

    def merged_with(self, other: RiskDecision) -> RiskDecision:
        """Ikki qarorni "VA" mantig'i bilan birlashtiradi (4-bo'lim boshlanishi)."""
        return RiskDecision(
            allowed=self.allowed and other.allowed,
            reasons=[*self.reasons, *other.reasons],
            details=[*self.details, *other.details],
        )


# --------------------------------------------------------------------------- #
#  3.7 — Bozor Salomatligi Indeksi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class HealthFactor:
    """Indeksning bitta tarkibiy qismi."""

    name: str
    score: float          # 0..1 normallashtirilgan
    weight: float
    explanation: str

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass(frozen=True, slots=True)
class MarketHealth:
    """3.7-band: 0-100 oralig'idagi markaziy indeks."""

    value: float
    factors: list[HealthFactor]
    computed_at: datetime

    @property
    def band(self) -> HealthBand:
        if self.value >= 80:
            return HealthBand.HIGH
        if self.value >= 40:
            return HealthBand.MID
        return HealthBand.LOW


# --------------------------------------------------------------------------- #
#  5 — Pozitsiya hajmi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PositionSuggestion:
    """5.1-band: tavsiya, buyruq emas.

    Bot hech qachon "shuncha oling" demaydi — bu faqat hisob-kitob.
    """

    symbol: str
    balance: float
    daily_risk_pct: float
    daily_budget_usd: float
    remaining_budget_usd: float
    risk_amount_usd: float
    position_size_usd: float
    stop_distance_pct: float
    units: float
    entry: float
    within_daily_limit: bool
    note: str | None = None
