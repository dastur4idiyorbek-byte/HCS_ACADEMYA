"""1.3 — Voqea/katalizator: Listing/Delisting + Token Unlock.

BU TEKSHIRUV BOSHQALARIDAN FARQ QILADI. U ball ham qo'yadi, lekin
asosiy vazifasi — QATTIQ TO'SIQ (2-prompt, 4-qism, BLOK 1):

    Token Unlock YAQIN (<7 kun) VA KATTA (supply'ning >5%i)
    YOKI Delisting xavfi aniq
    -> COIN BUTUNLAY CHETLASHTIRILADI

Nima uchun qattiq to'siq, ball emas: bu — KELAJAKDAGI, sanasi
ma'lum, orqaga qaytarib bo'lmaydigan sotuv bosimi. Uni "bitta ichki
tekshiruv 0 ball oldi" deb yumshatish — 3 ta boshqa tekshiruv uni
yopib ketishi mumkin degani. Halol savdo bunday xavfni bilib turib
mijozga bermaydi.

BACKTESTDA JONLI-ONLY. Unlock kalendarining tarixiy arxivi bepul
mavjud emas, shuning uchun backtestda bu tekshiruv `MALUMOT_YOQ`
qaytaradi va to'siq ishlamaydi. Bu — o'lchovni BUZMAYDI: to'siq
faqat signalni KAMAYTIRADI, ya'ni jonli natija backtestdagidan
yomon bo'lmaydi (`docs/FUNDAMENTAL_MALUMOT_MANBALARI.md`).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.turlar import Tekshiruv, ha, malumot_yoq, yoq

#: Unlock shu kun ichida bo'lsa — "yaqin".
UNLOCK_YAQIN_KUN = 7

#: Unlock supply'ning shu foizidan katta bo'lsa — "katta".
#: Promptda 5-10% oralig'i berilgan; ehtiyotkor uchi olindi.
#: 🔴 O'LCHANMAGAN.
UNLOCK_KATTA_PCT = 5.0


@dataclass(frozen=True, slots=True)
class Katalizator:
    """1.3 uchun xom ma'lumot."""

    #: Keyingi unlock'gacha necha kun. `None` — kalendar yo'q.
    unlock_kun: int | None = None
    #: O'sha unlock supply'ning necha foizi
    unlock_ulush_pct: float | None = None
    #: Delisting e'lon qilinganmi (yoki kuzatuv ro'yxatida)
    delisting_xavfi: bool | None = None
    #: Yangi listing (ijobiy katalizator) so'nggi kunlarda bo'ldimi
    yangi_listing: bool | None = None


def katalizator(malumot: Katalizator) -> tuple[Tekshiruv, str | None]:
    """Tekshiruv natijasi VA qattiq to'siq sababi (bo'lsa).

    Returns:
        `(tekshiruv, tosiq_sababi)`. `tosiq_sababi` `None` bo'lmasa —
        coin butunlay chetlashtiriladi, qolgan bloklar hisoblanmaydi.
    """
    tosiq = _tosiq_sababi(malumot)
    if tosiq is not None:
        return yoq("katalizator", tosiq), tosiq

    ovozlar: list[bool] = []
    sabablar: list[str] = []

    if malumot.unlock_kun is not None:
        # To'siqdan o'tgan bo'lsa ham, unlock yaqin bo'lsa — salbiy belgi.
        toza = malumot.unlock_kun > UNLOCK_YAQIN_KUN
        ovozlar.append(toza)
        sabablar.append(f"unlock {malumot.unlock_kun} kun")

    if malumot.yangi_listing is not None:
        ovozlar.append(bool(malumot.yangi_listing))
        sabablar.append("yangi listing" if malumot.yangi_listing else "listing yo'q")

    if malumot.delisting_xavfi is not None:
        ovozlar.append(not malumot.delisting_xavfi)
        sabablar.append("delisting xavfi yo'q" if not malumot.delisting_xavfi else "DELISTING")

    if not ovozlar:
        return malumot_yoq("katalizator", "unlock/listing kalendari yo'q"), None

    izoh = ", ".join(sabablar)
    return (ha("katalizator", izoh) if all(ovozlar) else yoq("katalizator", izoh)), None


def _tosiq_sababi(malumot: Katalizator) -> str | None:
    """Qattiq to'siq shartlari. Ikkalasi ham MUSTAQIL — biri yetarli."""
    if malumot.delisting_xavfi:
        return "delisting xavfi e'lon qilingan"

    yaqin = malumot.unlock_kun is not None and malumot.unlock_kun <= UNLOCK_YAQIN_KUN
    katta = (
        malumot.unlock_ulush_pct is not None
        and malumot.unlock_ulush_pct > UNLOCK_KATTA_PCT
    )
    if yaqin and katta:
        return (
            f"unlock {malumot.unlock_kun} kundan keyin, "
            f"supply'ning {malumot.unlock_ulush_pct:.1f}%i"
        )
    return None
