"""5.4-band: shaxsiy portfel va foyda/zarar hisobi.

MUHIM CHEGARA (5-bo'lim): bu — moliyaviy maslahat emas. Bot haqiqiy
hisobga ulanmaydi, pulni ushlab turmaydi. Foydalanuvchi "Men kirdim" deb
o'zi qayd etadi, tizim esa faqat hisob-kitob qiladi.

QISMLI YOPISH: TP1 ga yetilganda pozitsiyaning bir qismi yopiladi
(`portfolio.tp1_close_pct`). Ansiz "TP1 oldi, keyin Stop" holati sof zarar
ko'rinardi — foydalanuvchi raqamlarga ishonmay qolardi.
"""

from __future__ import annotations

from core.config.schema import PortfolioConfig
from core.domain.portfolio import (
    PortfolioSummary,
    PositionOutcome,
    PositionSnapshot,
    blended_result_pct,
)


def compute_outcome(
    amount_usd: float,
    entry_price: float,
    exit_price: float,
    config: PortfolioConfig,
    tp1_price: float | None = None,
) -> PositionOutcome:
    """Pozitsiyaning yakuniy foyda/zararini hisoblaydi.

    Args:
        amount_usd: foydalanuvchi kiritgan miqdor.
        entry_price: kirish narxi.
        exit_price: qolgan qismning yopilish narxi (TP2 yoki Stop).
        tp1_price: TP1 ga yetilgan bo'lsa uning narxi. `None` — yetilmagan.

    Misol (TP1 oldi, keyin Stop):
        $100, entry 100, TP1 103 (50% yopildi), Stop 99
        -> 50% × +3% + 50% × −1% = +1% = +$1.00
        Qismli yopish hisobga olinmasa, natija −$1.00 ko'rinardi.
    """
    if entry_price <= 0:
        raise ValueError("Kirish narxi musbat bo'lishi kerak")
    if amount_usd <= 0:
        raise ValueError("Miqdor musbat bo'lishi kerak")

    foiz = blended_result_pct(entry_price, exit_price, tp1_price, config.tp1_close_pct)
    if tp1_price is None:
        return PositionOutcome(
            pnl_usd=amount_usd * foiz / 100,
            pnl_pct=foiz,
            partial_exit_price=None,
            partial_close_pct=None,
        )

    return PositionOutcome(
        pnl_usd=amount_usd * foiz / 100,
        pnl_pct=foiz,
        partial_exit_price=tp1_price,
        partial_close_pct=config.tp1_close_pct,
    )


def summarize(positions: list[PositionSnapshot]) -> PortfolioSummary:
    """Pozitsiyalar ro'yxatidan portfel holatini yig'adi."""
    yopilganlar = [p for p in positions if p.pnl_pct is not None]
    foizlar = [p.pnl_pct for p in yopilganlar if p.pnl_pct is not None]

    return PortfolioSummary(
        total_positions=len(positions),
        open_positions=len(positions) - len(yopilganlar),
        closed_positions=len(yopilganlar),
        winning=sum(1 for p in yopilganlar if (p.pnl_usd or 0) > 0),
        losing=sum(1 for p in yopilganlar if (p.pnl_usd or 0) < 0),
        total_invested_usd=sum(p.amount_usd for p in yopilganlar),
        realized_pnl_usd=sum(p.pnl_usd or 0 for p in yopilganlar),
        best_pnl_pct=max(foizlar) if foizlar else None,
        worst_pnl_pct=min(foizlar) if foizlar else None,
    )


__all__ = ["blended_result_pct", "compute_outcome", "summarize"]
