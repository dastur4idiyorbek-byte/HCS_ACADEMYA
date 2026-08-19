"""5.2-band: agregat foydalanuvchi balans mexanizmi.

Bu — tajribali treyderning tabiiy fikrini tizimga aylantiradi:
*"Odamlarning ko'pchiligi allaqachon band, hozir yana signal tashlashning
keragi yo'q."*

Misol (spetsifikatsiyadan): 10 ta obunachi, signal tashlandi, 7 tasi kirdi.
Shu 7 talikning kunlik limiti deyarli to'lgan — ular uchun yangi signal
keraksiz. Qolgan 3 kishi hali limitga yetmagan — ular uchun mantiqiy.

MUHIM: bu **majburiy qat'iy to'xtatish EMAS**. Natija Bozor Salomatligi
Indeksining bir qismi sifatida ishlatiladi (3.7-band) — sig'im past bo'lsa
indeks pasayadi, signal chastotasi tabiiy ravishda kamayadi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config.schema import AggregateConfig
from core.position_sizing.budget import DailyRiskBudget


@dataclass(frozen=True, slots=True)
class AggregateCapacity:
    """Faol foydalanuvchilarning umumiy sig'imi."""

    active_users: int
    users_with_headroom: int
    free_budget_usd: float
    total_budget_usd: float

    @property
    def headroom_ratio(self) -> float:
        """Hali limitiga yetmagan foydalanuvchilar ulushi (0..1).

        Bu — Bozor Salomatligi Indeksiga kiradigan asosiy ko'rsatkich.
        Foydalanuvchi yo'q bo'lsa 1.0 qaytadi: tizim o'zini cheklamaydi,
        boshqa filtrlar baribir ishlaydi.
        """
        if self.active_users <= 0:
            return 1.0
        return self.users_with_headroom / self.active_users

    @property
    def budget_free_ratio(self) -> float:
        """Umumiy byudjetning bo'sh ulushi (0..1) — pul bilan o'lchangan sig'im."""
        if self.total_budget_usd <= 0:
            return 1.0
        return max(0.0, min(1.0, self.free_budget_usd / self.total_budget_usd))

    def describe(self) -> str:
        """Admin dashboard uchun bir qatorli izoh."""
        if self.active_users <= 0:
            return "Faol foydalanuvchi yo'q — sig'im cheklovi qo'llanilmaydi."
        return (
            f"{self.users_with_headroom}/{self.active_users} foydalanuvchida hali "
            f"kunlik xavf sig'imi bor "
            f"(bo'sh byudjet: ${self.free_budget_usd:,.0f} / ${self.total_budget_usd:,.0f})."
        )


def compute_aggregate_capacity(
    budgets: list[DailyRiskBudget],
    config: AggregateConfig,
) -> AggregateCapacity:
    """Faol foydalanuvchilarning kunlik byudjetlaridan agregat sig'imni hisoblaydi.

    Foydalanuvchi "sig'imi bor" deb hisoblanadi, agar byudjetining band ulushi
    `capacity_used_threshold` dan past bo'lsa.
    """
    if not budgets:
        return AggregateCapacity(0, 0, 0.0, 0.0)

    threshold = config.capacity_used_threshold
    with_headroom = sum(1 for b in budgets if b.used_ratio < threshold)
    free = sum(b.remaining_usd for b in budgets)
    total = sum(b.total_usd for b in budgets)

    return AggregateCapacity(
        active_users=len(budgets),
        users_with_headroom=with_headroom,
        free_budget_usd=free,
        total_budget_usd=total,
    )
