"""3.8-band: yopilgan signalning natijasi va konteksti.

Nima uchun alohida tip: postmortem bazadan emas, SOF ma'lumotdan ishlaydi.
Shu sababli naqsh izlash mantig'i backtestda ham, jonli rejimda ham bir xil
kod bilan sinaladi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from core.domain.enums import SignalSource, SignalStatus


class Outcome(str, Enum):
    """Signal qanday yakunlandi."""

    TP2 = "tp2"              # to'liq maqsadga yetdi
    TP1_THEN_STOP = "tp1_then_stop"  # TP1 olindi, keyin Stop
    STOP = "stop"            # Stop yedi
    CANCELLED = "cancelled"  # Entry'ga yetmasdan bekor bo'ldi

    @property
    def is_win(self) -> bool:
        """TP1 ham foyda hisoblanadi — pozitsiyaning bir qismi yopilgan."""
        return self in {Outcome.TP2, Outcome.TP1_THEN_STOP}

    @property
    def is_loss(self) -> bool:
        return self is Outcome.STOP

    @property
    def counts_in_stats(self) -> bool:
        """Bekor qilingan signal statistikaga kirmaydi — u savdo bo'lmagan."""
        return self is not Outcome.CANCELLED


@dataclass(frozen=True, slots=True)
class ClosedSignal:
    """Tahlil uchun yopilgan signal va uning konteksti.

    Kontekst (ball, bozor salomatligi) signal BERILGAN paytdagi holat —
    keyinroq qayta hisoblab bo'lmaydi, shuning uchun u signal bilan birga
    saqlanadi.
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
        vaqt = self.holding_time
        return None if vaqt is None else vaqt.total_seconds() / 3600


def outcome_from_status(
    status: SignalStatus,
    reached_tp1: bool,
) -> Outcome:
    """DB holatidan natija turini aniqlaydi.

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
