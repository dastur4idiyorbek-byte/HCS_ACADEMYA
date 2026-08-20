"""1.3-band: pullik bo'limlar obunasiz foydalanuvchiga UMUMAN ko'rinmasligi kerak."""

from __future__ import annotations

from bot.keyboards import main_menu, visible_menu_items
from core.domain.enums import SubscriptionTier


def test_obunasiz_foydalanuvchi_pullik_bolimlarni_kormaydi() -> None:
    bandlar = visible_menu_items(None)
    assert "signallar" not in bandlar
    assert "video_darslar" not in bandlar
    assert "strategiyalar" not in bandlar
    assert "tariflar" in bandlar, "tarif sotib olish yo'li ochiq qolishi kerak"


def test_lite_faqat_signal_koradi() -> None:
    bandlar = visible_menu_items(SubscriptionTier.LITE)
    assert "signallar" in bandlar
    assert "video_darslar" not in bandlar


def test_pro_video_darslarni_koradi() -> None:
    bandlar = visible_menu_items(SubscriptionTier.PRO)
    assert "video_darslar" in bandlar
    assert "strategiyalar" not in bandlar


def test_premium_hammasini_koradi() -> None:
    bandlar = visible_menu_items(SubscriptionTier.PREMIUM)
    assert {"signallar", "video_darslar", "strategiyalar"} <= set(bandlar)


def test_yuqori_tarif_pastini_qamrab_oladi() -> None:
    assert SubscriptionTier.PREMIUM.covers(SubscriptionTier.LITE)
    assert SubscriptionTier.PRO.covers(SubscriptionTier.LITE)
    assert not SubscriptionTier.LITE.covers(SubscriptionTier.PRO)


# --------------------------------------------------------------------------- #
#  Admin panel tugmasi
# --------------------------------------------------------------------------- #


def _matnlar(markup) -> list[str]:  # noqa: ANN001
    return [tugma.text for qator in markup.inline_keyboard for tugma in qator]


def test_oddiy_foydalanuvchi_admin_tugmasini_kormaydi() -> None:
    """1.1-band: admin panelning mavjudligi oshkor qilinmaydi."""
    matnlar = _matnlar(main_menu(None))

    assert not any("Admin" in m for m in matnlar), matnlar


def test_obunachi_ham_admin_tugmasini_kormaydi() -> None:
    matnlar = _matnlar(main_menu(SubscriptionTier.PREMIUM))

    assert not any("Admin" in m for m in matnlar), matnlar


def test_admin_panel_tugmasini_koradi() -> None:
    """`/panel` yozishni bilish shart bo'lmasligi kerak."""
    matnlar = _matnlar(main_menu(None, is_admin=True))

    assert any("Admin" in m for m in matnlar), matnlar


def test_admin_tugmasi_panelga_olib_boradi() -> None:
    tugmalar = [
        tugma
        for qator in main_menu(None, is_admin=True).inline_keyboard
        for tugma in qator
    ]
    panel = [tugma for tugma in tugmalar if "Admin" in tugma.text]

    assert panel[0].callback_data == "menu:panel"


def test_admin_tugmasi_oddiy_bandlarni_yoqotmaydi() -> None:
    """Tugma QO'SHILADI, mavjud bandlarni almashtirmaydi."""
    oddiy = set(_matnlar(main_menu(SubscriptionTier.LITE)))
    adminda = set(_matnlar(main_menu(SubscriptionTier.LITE, is_admin=True)))

    assert oddiy < adminda
    assert len(adminda - oddiy) == 1
