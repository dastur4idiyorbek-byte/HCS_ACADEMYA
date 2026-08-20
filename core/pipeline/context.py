"""Signal sikli uchun kiruvchi ma'lumotlar va natija.

Nima uchun alohida tiplar: sikl o'zi tarmoqqa ham, bazaga ham murojaat
qilmaydi — u tayyor ma'lumotni oladi va qaror qaytaradi. Shu sababli
butun zanjir (skrining -> tahlil -> ball -> Risk Engine) backtestda ham
o'zgarishsiz ishlaydi (6.3-band).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.domain.models import (
    Candle,
    HalalVerdict,
    MarketHealth,
    ScoreBreakdown,
    Signal,
    SignalCandidate,
)


@dataclass(frozen=True, slots=True)
class SymbolData:
    """Bitta coin uchun barcha kerakli ma'lumot."""

    symbol: str
    halal_verdict: HalalVerdict
    candles: dict[str, list[Candle]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CycleInput:
    """Siklga beriladigan to'liq holat."""

    now: datetime
    symbols: list[SymbolData]
    market_health: MarketHealth | None
    open_signals: list[Signal] = field(default_factory=list)

    # Risk Engine uchun bozor konteksti
    btc_change_24h_pct: float | None = None
    daily_loss_pct: float = 0.0
    weekly_loss_pct: float = 0.0
    consecutive_stops: int = 0
    consecutive_stop_until: datetime | None = None
    kill_switch_active: bool = False
    kill_switch_reason: str | None = None
    #: symbol -> narx yoshi (sekund)
    price_ages: dict[str, float] = field(default_factory=dict)
    #: symbol -> ADX
    adx_values: dict[str, float] = field(default_factory=dict)
    #: symbol -> ATR foizi
    atr_values: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RejectedCandidate:
    """Rad etilgan nomzod va sababi — admin dashboardi uchun (3.7-band)."""

    symbol: str
    stage: str
    detail: str
    score: float | None = None


@dataclass(frozen=True, slots=True)
class CycleResult:
    """Siklning natijasi.

    `emitted` bo'sh bo'lishi — XATO EMAS. 0.2-band: "signal bermaslik
    normal holat". `rejected` esa nima uchun ekanini tushuntiradi.
    """

    emitted: list[SignalCandidate]
    rejected: list[RejectedCandidate]
    threshold: float | None
    market_health: MarketHealth | None
    analyzed_count: int
    breakdowns: dict[str, ScoreBreakdown] = field(default_factory=dict)

    @property
    def emitted_count(self) -> int:
        return len(self.emitted)

    def summary(self) -> str:
        """Log va admin uchun bir qatorli xulosa."""
        salomatlik = (
            f"{self.market_health.value:.0f}" if self.market_health else "nomalum"
        )
        chegara = f"{self.threshold:.0f}" if self.threshold is not None else "yopiq"
        return (
            f"Sikl: {self.analyzed_count} coin tahlil qilindi, "
            f"{self.emitted_count} signal chiqdi "
            f"(salomatlik {salomatlik}, chegara {chegara})"
        )
