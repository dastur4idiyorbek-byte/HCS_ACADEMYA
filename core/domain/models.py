"""Sof domain modellari — modullar o'rtasidagi umumiy "til".

Bu obyektlar hech qanday tashqi kutubxonaga (aiogram, SQLAlchemy) bog'liq
emas. DB modellari (`core/storage/models.py`) va Telegram qatlami shularni
o'zaro aylantiradi. Sabab: 0.1-band — "miya" va "tana" qat'iy ajratilgan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.domain.enums import (
    BlockReason,
    EventStatus,
    ExitOrderType,
    HalalStatus,
    HealthBand,
    OrderType,
    Outcome,
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
class TakeProfit:
    """Bitta foyda nuqtasi va unda sotiladigan ulush.

    Ulush foizda va butun signal bo'yicha yig'indisi 100 bo'lishi
    kerak — ya'ni "TP1 da yarmi, TP2 da qolgani" degan reja
    raqamda ham to'liq ifodalanadi.
    """

    price: float
    #: Pozitsiyaning necha foizi shu nuqtada sotiladi
    close_pct: float
    #: Haqiqiy qarshilik zonasidan olinganmi (yoki formuladan)
    from_structure: bool = True


@dataclass(frozen=True, slots=True)
class SignalLevels:
    """Signal narx darajalari. Faqat spot/long: Stop < Entry < TP1 < ... < TPn.

    TP SONI QAT'IY EMAS — 1, 2 yoki 3 bo'lishi mumkin, bozorda
    nechta haqiqiy nishon borligiga qarab. Ilgari bu yerda `tp1` va
    `tp2` maydonlari turardi, ya'ni "har doim aynan ikkita" degan
    qoida MODELGA yozib qo'yilgan edi. Bozor esa unday emas: toza
    ko'tarilishda ustda bitta ham qarshilik bo'lmasligi, keng
    diapazonda esa uchtasi bo'lishi mumkin.

    `tp1` va `final_tp` nomlari saqlanadi, chunki ularning ma'nosi
    TP soniga bog'liq emas:

        tp1      — BIRINCHI foyda nuqtasi. Stop shundan keyin kirish
                   narxiga ko'tariladi (breakeven).
        final_tp — YAKUNIY nishon. Signal shu yerda yopiladi va R/R
                   shu bo'yicha o'lchanadi.

    Bitta TP bo'lganda ikkalasi bir xil narx bo'ladi — bu to'g'ri:
    birinchi nuqta ham, oxirgisi ham o'sha.
    """

    entry: float
    stop: float
    takes: tuple[TakeProfit, ...]

    def __post_init__(self) -> None:
        if not self.takes:
            raise ValueError("Kamida bitta TP bo'lishi kerak")
        if self.stop <= 0:
            raise ValueError("Narx musbat bo'lishi kerak")
        if self.stop >= self.entry:
            raise ValueError(
                "Darajalar tartibi noto'g'ri. Spot/long uchun shart: "
                f"Stop({self.stop}) < Entry({self.entry})"
            )

        oldingi = self.entry
        for index, tp in enumerate(self.takes, start=1):
            if tp.price <= oldingi:
                raise ValueError(
                    "Darajalar tartibi noto'g'ri. Spot/long uchun shart: "
                    f"Entry({self.entry}) < TP1 < ... < TPn; "
                    f"TP{index}({tp.price}) oldingi darajadan ({oldingi}) yuqori emas"
                )
            oldingi = tp.price

        ulush = sum(tp.close_pct for tp in self.takes)
        if abs(ulush - 100.0) > 0.01:
            raise ValueError(
                f"TP ulushlari yig'indisi 100% bo'lishi kerak, hozir {ulush:g}%"
            )

    # ------------------------------------------------------------------ #
    #  O'qish
    # ------------------------------------------------------------------ #

    @property
    def tp_count(self) -> int:
        return len(self.takes)

    @property
    def tp1(self) -> float:
        """BIRINCHI foyda nuqtasi — breakeven shundan keyin."""
        return self.takes[0].price

    @property
    def final_tp(self) -> float:
        """YAKUNIY nishon — signal shu yerda yopiladi."""
        return self.takes[-1].price

    @property
    def tp_prices(self) -> tuple[float, ...]:
        return tuple(tp.price for tp in self.takes)

    @property
    def stop_distance_pct(self) -> float:
        """Entry'dan Stop'gacha masofa, foizda (3.3-band)."""
        return (self.entry - self.stop) / self.entry * 100

    @property
    def tp1_distance_pct(self) -> float:
        return (self.tp1 - self.entry) / self.entry * 100

    @property
    def final_tp_distance_pct(self) -> float:
        return (self.final_tp - self.entry) / self.entry * 100

    @property
    def risk_reward(self) -> float:
        """YAKUNIY nishon bo'yicha nisbat (3.3-band)."""
        return (self.final_tp - self.entry) / (self.entry - self.stop)

    def tp_price(self, index: int) -> float | None:
        """1 dan boshlab nomerlangan TP narxi, yo'q bo'lsa `None`."""
        if 1 <= index <= len(self.takes):
            return self.takes[index - 1].price
        return None


#: TP soniga qarab standart ulushlar — SOZLAMA YO'Q joylar uchun.
#:
#: Ishlab chiqarish yo'li ulushni `portfolio.tp_close_shares` dan
#: oladi. Bu jadval faqat testlar va qo'lda qurilgan darajalar
#: uchun zaxira: raqam o'ylab topilmasin, lekin domen sozlamaga
#: bog'lanib ham qolmasin (0.1-band).
STANDART_TP_ULUSHLARI: dict[int, tuple[float, ...]] = {
    1: (100.0,),
    2: (50.0, 50.0),
    3: (40.0, 30.0, 30.0),
}


def signal_levels(
    entry: float,
    stop: float,
    tp1: float,
    tp2: float | None = None,
    tp3: float | None = None,
    *,
    shares: tuple[float, ...] | None = None,
    from_structure: bool | tuple[bool, ...] = True,
) -> SignalLevels:
    """Narxlardan `SignalLevels` quradi — TP soni berilganiga qarab.

    `tp2` va `tp3` ixtiyoriy: bitta TP ham to'liq signal. Ulush
    berilmasa `STANDART_TP_ULUSHLARI` dan olinadi.
    """
    narxlar = [n for n in (tp1, tp2, tp3) if n is not None]
    ulushlar = shares or STANDART_TP_ULUSHLARI.get(
        len(narxlar), tuple(100.0 / len(narxlar) for _ in narxlar)
    )
    if len(ulushlar) != len(narxlar):
        raise ValueError(
            f"{len(narxlar)} ta TP uchun {len(ulushlar)} ta ulush berildi"
        )
    manbalar = (
        from_structure
        if isinstance(from_structure, tuple)
        else (from_structure,) * len(narxlar)
    )
    return SignalLevels(
        entry=entry,
        stop=stop,
        takes=tuple(
            TakeProfit(price=narx, close_pct=ulush, from_structure=manba)
            for narx, ulush, manba in zip(narxlar, ulushlar, manbalar, strict=True)
        ),
    )


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
    #: Nechta TP ga yetilgan (0 dan `levels.tp_count` gacha).
    #:
    #: Ilgari bu yerda `tp1_reached: bool` turardi — u "TP ikkita"
    #: degan taxminni ichiga yashirgan edi. Uchta TP bo'lganda
    #: "birinchisiga yetdi" va "ikkinchisiga ham yetdi" bir xil
    #: ko'rinardi.
    reached_tps: int = 0
    #: Narxning kirishdan keyingi ENG YUQORI nuqtasi. Surilgan Stop
    #: shundan hisoblanadi; `None` — hali kuzatuv boshlanmagan.
    peak_price: float | None = None
    #: SURILGAN Stop (trailing). Kuzatuvchi hisoblab qo'yadi — domen
    #: modeli sozlamani bilmaydi va bilmasligi ham kerak.
    #: `None` — surish o'chirilgan yoki hali ishga tushmagan.
    trailing_stop: float | None = None

    @property
    def tp1_reached(self) -> bool:
        """Birinchi TP ga yetildimi — breakeven va qismli sotish sharti.

        Nima uchun `status` yetarli emas: TP dan keyin narx Stop'ga
        tushsa, `status` STOPPED bo'lib qoladi va "TP olingan edi"
        fakti yo'qoladi — qismli sotish esa hisobga olinishi kerak
        (5.4-band).
        """
        return self.reached_tps >= 1

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

        SURILGAN STOP undan ham yuqori bo'lishi mumkin. Stop faqat
        YUQORIGA harakat qiladi: pastga tushirish signal berilgandagi
        va'dani buzardi — foydalanuvchi bir xavfga rozi bo'lgan,
        keyin u kattalashib ketardi.
        """
        asos = self.levels.entry if self.tp1_reached else self.levels.stop
        if self.trailing_stop is None:
            return asos
        return max(asos, self.trailing_stop)

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


# --------------------------------------------------------------------------- #
#  3.8 / 3.7 — Qatlamlar ORASIDA yuradigan yozuvlar
#
#  Quyidagi ikki tip tahlil qatlamida tug'iladi, lekin XOTIRA qatlami
#  ham ularni o'qiydi. Ilgari ular `analysis/postmortem` va
#  `pipeline/events` da edi va `storage` o'sha yerlardan import
#  qilardi — ya'ni poydevor tepadagi qavatlarga suyanardi
#  (`docs/ARXITEKTURA.md`, qurilish xaritasi).
#
#  Ikkalasi ham sof ma'lumot: ularda mantiq yo'q, faqat shakl bor.
#  Shuning uchun joyi shu yerda.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ClosedSignal:
    """Tahlil uchun yopilgan signal va uning konteksti.

    Kontekst (ball, bozor salomatligi) signal BERILGAN paytdagi holat —
    keyinroq qayta hisoblab bo'lmaydi, shuning uchun u signal bilan
    birga saqlanadi.
    """

    signal_id: int
    symbol: str
    source: SignalSource
    outcome: Outcome
    score: float | None
    market_health_at_entry: float | None
    result_pct: float | None
    created_at: datetime
    activated_at: datetime | None
    closed_at: datetime
    is_false_signal: bool
    correlation_group: str | None = None

    @property
    def holding_time(self) -> timedelta | None:
        """Faol bo'lgandan yopilgungacha o'tgan vaqt."""
        if self.activated_at is None:
            return None
        return self.closed_at - self.activated_at

    @property
    def holding_hours(self) -> float | None:
        muddat = self.holding_time
        return None if muddat is None else muddat.total_seconds() / 3600


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    """Bitta coin, bitta bosqich — Jonli Oshxona uchun."""

    symbol: str
    stage: str
    status: EventStatus
    reason: str | None = None
    #: Shu coinning yakuniy balli (ma'lum bo'lsa)
    score: float | None = None
    at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PeriodStats:
    """Davr bo'yicha umumiy raqamlar (3.6-band shaffofligi).

    `ClosedSignal` bilan bir sababdan shu yerda: hisobotni tahlil
    qatlami QURADI, xotira qatlami esa uni SAQLAYDI. Sof sonlar —
    ichida mantiq yo'q.
    """

    total: int
    tp2: int
    tp1_then_stop: int
    stop: int
    cancelled: int
    false_signals: int
    average_score: float | None
    average_holding_hours: float | None

    @property
    def traded(self) -> int:
        """Haqiqiy savdoga aylangan signallar (bekor qilinganlarsiz)."""
        return self.total - self.cancelled

    @property
    def win_rate(self) -> float | None:
        return None if self.traded == 0 else (self.tp2 + self.tp1_then_stop) / self.traded

    @property
    def stop_rate(self) -> float | None:
        return None if self.traded == 0 else self.stop / self.traded


def outcome_from_status(status: SignalStatus, reached_tp1: bool) -> Outcome:
    """DB holatidan natija turini aniqlaydi.

    Sof o'tkazish: holat -> natija. Mantiq yo'q, qaror yo'q. Shu
    sababdan joyi poydevorda — uni tahlil qatlami ham (postmortem),
    xotira qatlami ham (`repositories.py`) chaqiradi. Ilgari u
    `analysis/postmortem` da edi va `storage` uni o'sha yerdan
    olardi (qurilish xaritasi, 1-teskari g'isht).

    Args:
        reached_tp1: signal Stop yeyishdan oldin TP1 ga yetganmi
            (`signal_events` jadvalidan bilinadi).
    """
    if status is SignalStatus.TP2_HIT:
        return Outcome.TP2
    if status is SignalStatus.STOPPED:
        return Outcome.TP1_THEN_STOP if reached_tp1 else Outcome.STOP
    if status is SignalStatus.CANCELLED:
        return Outcome.CANCELLED
    raise ValueError(f"Yopilmagan signal tahlil qilinmaydi: {status.value}")
