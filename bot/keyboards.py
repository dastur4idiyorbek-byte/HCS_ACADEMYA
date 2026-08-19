"""Inline va reply klaviaturalar.

1.3-band talabi: pullik bo'limlar obunasiz foydalanuvchiga UMUMAN
KO'RINMASLIGI kerak — hatto menyuda ham. Shuning uchun menyu tugmalari
foydalanuvchining tarifiga qarab QURILADI: yashirish emas, umuman
qo'shmaslik.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.i18n import DEFAULT_LANGUAGE, t
from core.domain.enums import HalalStatus, SubscriptionPeriod, SubscriptionTier

#: Har bir menyu bandi qaysi minimal tarifni talab qiladi (`None` — ochiq)
MENU_REQUIREMENTS: dict[str, SubscriptionTier | None] = {
    "tariflar": None,
    "yordam": None,
    "signallar": SubscriptionTier.LITE,
    "portfel": SubscriptionTier.LITE,
    "statistika": SubscriptionTier.LITE,
    "video_darslar": SubscriptionTier.PRO,
    "strategiyalar": SubscriptionTier.PREMIUM,
}

#: Menyu bandlari uchun tugma matnlari (i18n kalitlari)
MENU_LABELS: dict[str, str] = {
    "tariflar": "obuna.tariflar",
    "yordam": "umumiy.yordam",
    "signallar": "signal.faol_signallar",
    "portfel": "portfel.sarlavha",
    "statistika": "portfel.statistika",
    "video_darslar": "kontent.sarlavha",
    "strategiyalar": "admin.kontent",
}


def visible_menu_items(tier: SubscriptionTier | None) -> list[str]:
    """Foydalanuvchi ko'rishi mumkin bo'lgan menyu bandlari."""
    return [
        nom
        for nom, talab in MENU_REQUIREMENTS.items()
        if talab is None or (tier is not None and tier.covers(talab))
    ]


def main_menu(
    tier: SubscriptionTier | None, language: str = DEFAULT_LANGUAGE
) -> InlineKeyboardMarkup:
    """Asosiy menyu — faqat ruxsat etilgan bandlar bilan."""
    builder = InlineKeyboardBuilder()
    for nom in visible_menu_items(tier):
        builder.button(text=t(MENU_LABELS[nom], language), callback_data=f"menu:{nom}")
    builder.adjust(2)
    return builder.as_markup()


def tier_menu(language: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for tier in SubscriptionTier:
        builder.button(text=t(f"obuna.{tier.value}", language), callback_data=f"tier:{tier.value}")
    builder.button(text=t("umumiy.orqaga", language), callback_data="menu:home")
    builder.adjust(1)
    return builder.as_markup()


def period_menu(
    tier: SubscriptionTier, language: str = DEFAULT_LANGUAGE
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for period in SubscriptionPeriod:
        builder.button(
            text=t(f"obuna.{period.value}", language),
            callback_data=f"period:{tier.value}:{period.value}",
        )
    builder.button(text=t("umumiy.orqaga", language), callback_data="menu:tariflar")
    builder.adjust(1)
    return builder.as_markup()


def back_button(target: str = "home", language: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("umumiy.orqaga", language), callback_data=f"menu:{target}"
                )
            ]
        ]
    )


def cancel_button(language: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("umumiy.bekor", language), callback_data="fsm:cancel")]
        ]
    )


# --------------------------------------------------------------------------- #
#  Admin (1.5-band)
# --------------------------------------------------------------------------- #

#: Admin panel bo'limlari — kengaytiriladigan (yangi bo'lim shu yerga qo'shiladi)
ADMIN_SECTIONS: list[tuple[str, str]] = [
    ("yangi_signal", "admin.yangi_signal"),
    ("tolovlar", "admin.tolovlar"),
    ("narxlar", "admin.narxlar"),
    ("kontent", "admin.kontent"),
    ("halol_royxat", "admin.halol_royxat"),
    ("broadcast", "admin.broadcast"),
    ("qoidabuzarlik", "admin.qoidabuzarlik"),
    ("salomatlik", "admin.salomatlik"),
    ("hisobot", "admin.hisobot"),
    ("risk", "admin.risk_sozlamalari"),
]


def admin_panel(language: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for kod, kalit in ADMIN_SECTIONS:
        builder.button(text=t(kalit, language), callback_data=f"admin:{kod}")
    builder.adjust(2)
    return builder.as_markup()


def payment_review(payment_id: int, language: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("admin.tasdiqla", language), callback_data=f"pay:approve:{payment_id}"
                ),
                InlineKeyboardButton(
                    text=t("admin.rad_et", language), callback_data=f"pay:reject:{payment_id}"
                ),
            ]
        ]
    )


def halal_status_menu(symbol: str, language: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """1.4-band: coinni halol/shubhali/harom deb belgilash."""
    labels = {
        HalalStatus.HALAL: "✅ Halol",
        HalalStatus.MASHBOOH: "⚠️ Shubhali",
        HalalStatus.HARAM: "🚫 Harom",
    }
    builder = InlineKeyboardBuilder()
    for status, matn in labels.items():
        builder.button(text=matn, callback_data=f"coin:{symbol}:{status.value}")
    builder.adjust(1)
    return builder.as_markup()


def tier_choice(prefix: str, language: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    """Admin FSM'larida tarif tanlash uchun umumiy klaviatura."""
    builder = InlineKeyboardBuilder()
    for tier in SubscriptionTier:
        builder.button(text=tier.value.capitalize(), callback_data=f"{prefix}:{tier.value}")
    builder.adjust(3)
    return builder.as_markup()


def signal_actions(
    signal_id: int, language: str = DEFAULT_LANGUAGE
) -> InlineKeyboardMarkup:
    """3.6-band: har bir signal ostida shaffoflik tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("signal.nega_signal", language), callback_data=f"sig:why:{signal_id}"
                ),
                InlineKeyboardButton(
                    text=t("signal.nega_halol", language), callback_data=f"sig:halal:{signal_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("signal.men_kirdim", language), callback_data=f"sig:enter:{signal_id}"
                )
            ],
        ]
    )
