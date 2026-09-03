"""Kirish buyurtmasi turini tanlash — QO'LDA kiritilgan signal uchun.

| Holat                                      | Buyurtma turi |
|--------------------------------------------|---------------|
| Narx hali kutilgan Entry zonasiga yetmagan | LIMIT         |
| Narx allaqachon Entry zonasida             | MARKET        |

Chiqish har doim OCO (TP + Stop birgalikda) — u yerda tanlov yo'q.

2026-09-03 — bu funksiya `core/analysis/entry_order.py` dan KO'CHIRILDI.
Sabab: eski tahlil moduli o'chirildi, lekin admin qo'lda signal kiritishi
(5-bosqich) qoladi va unga kirish rejasi kerak. Funksiyaning o'zi ball
tizimiga hech qachon bog'liq bo'lmagan — u faqat ikkita narxni
solishtiradi. Chegaralar endi konfiguratsiyadan emas, ARGUMENTDAN keladi:
ular uchun alohida config bloki saqlab turishning ma'nosi yo'q.

O'LCHOV ESLATMASI: avtomatik siklda `entry` HAR DOIM joriy narxga teng
bo'lardi, ya'ni LIMIT tarmog'i o'lik edi (docs/GIPOTEZA_DAFTARI.md,
audit 3-bosqichi). Qo'lda kiritishda esa admin Entry'ni o'zi yozadi —
shuning uchun bu yerda ikkala tarmoq ham tirik.
"""

from __future__ import annotations

from core.domain.enums import OrderType
from core.domain.models import EntryPlan, SignalLevels

#: Suzuvchi nuqta xatosiga chidamlilik. Ansiz 100.15 narxi 0.15%
#: chegarasiga tushmay qolardi (hisob 0.15000000000000568 beradi).
_EPSILON = 1e-9

#: Joriy narx Entry'dan shu foizdan yaqin bo'lsa — MARKET.
MARKET_CHEGARA_PCT = 0.15
#: Narx Entry'dan shu foizdan PASTGA tushsa — zona buzilgan (fail-safe).
ZONA_BUZILDI_PCT = 0.30

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
    market_chegara_pct: float = MARKET_CHEGARA_PCT,
    zona_buzildi_pct: float = ZONA_BUZILDI_PCT,
) -> EntryPlan:
    """Joriy narx va Entry orasidagi masofaga qarab buyurtma turini tanlaydi.

    Returns:
        `EntryPlan`. `is_valid=False` bo'lsa signal berilmasligi kerak.
    """
    if current_price <= 0:
        raise ValueError("Joriy narx musbat bo'lishi kerak")

    entry = levels.entry
    # Musbat — narx Entry'dan yuqorida (hali zonaga tushmagan),
    # manfiy — narx Entry'dan pastda (zonani kesib o'tgan).
    distance_pct = (current_price - entry) / entry * 100

    if abs(distance_pct) <= market_chegara_pct + _EPSILON:
        return EntryPlan(
            order_type=OrderType.MARKET,
            entry_price=current_price,
            current_price=current_price,
            distance_pct=distance_pct,
            reason=MARKET_REASON.format(distance=distance_pct),
        )

    if distance_pct < -(zona_buzildi_pct + _EPSILON):
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
