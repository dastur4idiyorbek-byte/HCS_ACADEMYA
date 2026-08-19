"""Inline va reply klaviaturalar.

1.3-band talabi: pullik bo'limlar obunasiz foydalanuvchiga UMUMAN
KO'RINMASLIGI kerak — hatto menyuda ham. Shuning uchun menyu qurilishi
foydalanuvchining tarifiga bog'liq: yashirish emas, umuman qo'shmaslik.

HOLAT: 3-bosqichda to'ldiriladi.
"""

from __future__ import annotations

from core.domain.enums import SubscriptionTier

#: Har bir menyu bandi qaysi minimal tarifni talab qiladi
MENU_REQUIREMENTS: dict[str, SubscriptionTier | None] = {
    "tariflar": None,                          # hammaga ochiq
    "yordam": None,
    "signallar": SubscriptionTier.LITE,
    "portfel": SubscriptionTier.LITE,
    "statistika": SubscriptionTier.LITE,
    "video_darslar": SubscriptionTier.PRO,
    "strategiyalar": SubscriptionTier.PREMIUM,
}


def visible_menu_items(tier: SubscriptionTier | None) -> list[str]:
    """Foydalanuvchi ko'rishi mumkin bo'lgan menyu bandlari.

    Obunasi yo'q foydalanuvchi (`tier is None`) faqat ochiq bandlarni ko'radi.
    """
    ko_rinadigan = []
    for nom, talab in MENU_REQUIREMENTS.items():
        if talab is None or tier is not None and tier.covers(talab):
            ko_rinadigan.append(nom)
    return ko_rinadigan
