"""5.4-band: portfel modellari.

Nima uchun `core/services/` da emas, `core/domain/` da: bular sof
ma'lumot tiplari, biznes mantiq emas. Repository'lar ham, xizmatlar ham
ularni ishlatadi — agar ular `services` da tursa, aylanma bog'liqlik
paydo bo'lardi (repository -> services -> repository).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class PositionOutcome:
    """Yopilgan pozitsiyaning natijasi."""

    pnl_usd: float
    pnl_pct: float
    partial_exit_price: float | None
    partial_close_pct: float | None

    @property
    def is_profit(self) -> bool:
        return self.pnl_usd > 0


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    """Portfel hisobi uchun pozitsiya ko'rinishi (DB modelidan ajratilgan)."""

    symbol: str
    amount_usd: float
    entry_price: float
    trade_date: date
    closed_at: datetime | None = None
    pnl_usd: float | None = None
    pnl_pct: float | None = None

    @property
    def is_open(self) -> bool:
        return self.closed_at is None


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    """5.4-band: "Mening portfelim" bo'limi uchun umumiy holat."""

    total_positions: int
    open_positions: int
    closed_positions: int
    winning: int
    losing: int
    total_invested_usd: float
    realized_pnl_usd: float
    best_pnl_pct: float | None
    worst_pnl_pct: float | None

    @property
    def win_rate(self) -> float | None:
        if self.closed_positions == 0:
            return None
        return self.winning / self.closed_positions

    @property
    def realized_pnl_pct(self) -> float | None:
        """Yopilgan pozitsiyalarga qo'yilgan pulga nisbatan foyda."""
        if self.total_invested_usd <= 0:
            return None
        return self.realized_pnl_usd / self.total_invested_usd * 100


@dataclass(frozen=True, slots=True)
class PublicStats:
    """3.6 / 5.4-band: hammaga ochiq shaffoflik raqamlari.

    Shaxsiy ma'lumot OSHKOR QILINMAYDI — faqat agregat.
    """

    period_label: str
    signals_created: int
    signals_activated: int
    tp1_count: int
    tp2_count: int
    stop_count: int
    participants: int
    total_volume_usd: float
    average_score: float | None
    average_risk_reward: float | None

    @property
    def closed(self) -> int:
        return self.tp2_count + self.stop_count

    @property
    def win_rate(self) -> float | None:
        return None if self.closed == 0 else self.tp2_count / self.closed
