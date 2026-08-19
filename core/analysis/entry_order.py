"""5.1.0-band: kirish buyurtmasi turini avtomatik tanlash.

| Holat                                        | Buyurtma turi |
|----------------------------------------------|---------------|
| Narx hali kutilgan Entry zonasiga yetmagan   | LIMIT         |
| Narx allaqachon Entry zonasida               | MARKET        |

Chiqish har doim OCO (TP + Stop birgalikda) — u yerda tanlov yo'q.

Uchinchi holat (spetsifikatsiyada ko'rsatilmagan, lekin amalda uchraydi):
narx Entry'dan PASTGA tushib ketgan bo'lsa, bu — support zonasi ushlab
tura olmadi degani. Bunday holatda signal berilmaydi (0.3-band fail-safe):
zona buzilgan, kirish asosi yo'qolgan.
"""

from __future__ import annotations

from core.config.schema import EntryOrderConfig
from core.domain.enums import OrderType
from core.domain.models import EntryPlan, SignalLevels

#: Suzuvchi nuqta xatosiga chidamlilik. Ansiz 100.15 narxi 0.15% chegarasiga
#: tushmay qolardi (hisob 0.15000000000000568 beradi) va foydalanuvchi
#: chegarani aynan belgilaganida kutilmagan natija olardi.
_EPSILON = 1e-9

MARKET_REASON = (
    "Narx allaqachon kirish zonasida ({distance:+.2f}%) — kutish shart emas, "
    "bozor narxida kirish tavsiya etiladi."
)
LIMIT_REASON = (
    "Narx kirish zonasidan {distance:.2f}% yuqorida — Limit buyurtma qo'yiladi, "
    "narx zonaga kelganda avtomatik bajariladi."
)
ZONE_BROKEN_REASON = (
    "Narx kirish nuqtasidan {distance:.2f}% pastga tushib ketgan — qo'llab-quvvatlash "
    "zonasi ushlab tura olmadi. Kirish asosi yo'qolgan, signal berilmaydi."
)


def decide_entry_plan(
    current_price: float,
    levels: SignalLevels,
    config: EntryOrderConfig,
) -> EntryPlan:
    """Joriy narx va Entry orasidagi masofaga qarab buyurtma turini tanlaydi.

    Args:
        current_price: bozordagi hozirgi narx.
        levels: signal darajalari (Stop < Entry < TP1 < TP2).
        config: `analysis.entry_order` sozlamalari.

    Returns:
        `EntryPlan`. `is_valid=False` bo'lsa signal berilmasligi kerak.
    """
    if current_price <= 0:
        raise ValueError("Joriy narx musbat bo'lishi kerak")

    entry = levels.entry
    # Musbat — narx Entry'dan yuqorida (hali zonaga tushmagan),
    # manfiy — narx Entry'dan pastda (zonani kesib o'tgan).
    distance_pct = (current_price - entry) / entry * 100

    if abs(distance_pct) <= config.market_threshold_pct + _EPSILON:
        return EntryPlan(
            order_type=OrderType.MARKET,
            entry_price=current_price,
            current_price=current_price,
            distance_pct=distance_pct,
            reason=MARKET_REASON.format(distance=distance_pct),
        )

    if distance_pct < -(config.zone_broken_threshold_pct + _EPSILON):
        return EntryPlan(
            order_type=OrderType.LIMIT,
            entry_price=entry,
            current_price=current_price,
            distance_pct=distance_pct,
            reason=ZONE_BROKEN_REASON.format(distance=abs(distance_pct)),
            is_valid=False,
        )

    if distance_pct < 0:
        # MARKET chegarasidan tashqarida, lekin zona hali buzilmagan —
        # narx Entry'dan biroz pastda. Limit buyurtma Entry'da qoladi;
        # amalda u darhol bajariladi, lekin reja o'zgarmaydi.
        return EntryPlan(
            order_type=OrderType.LIMIT,
            entry_price=entry,
            current_price=current_price,
            distance_pct=distance_pct,
            reason=(
                f"Narx kirish nuqtasidan {abs(distance_pct):.2f}% pastda, lekin zona "
                "hali buzilmagan — Limit buyurtma kirish narxida qoladi."
            ),
        )

    return EntryPlan(
        order_type=OrderType.LIMIT,
        entry_price=entry,
        current_price=current_price,
        distance_pct=distance_pct,
        reason=LIMIT_REASON.format(distance=distance_pct),
    )
