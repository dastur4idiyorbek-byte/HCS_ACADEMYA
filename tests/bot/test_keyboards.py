"""1.3-band: pullik bo'limlar obunasiz foydalanuvchiga UMUMAN ko'rinmasligi kerak."""

from __future__ import annotations

from bot.keyboards import visible_menu_items
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
