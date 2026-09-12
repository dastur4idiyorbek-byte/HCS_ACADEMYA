"""Kunlik qidiruv chegarasi (7-qism)."""

from __future__ import annotations

import pytest

from core.config.schema import KuzatuvConfig
from core.domain.enums import SubscriptionTier
from core.watch_panel.search_limiter import chegara_ol


def test_har_tarif_oz_chegarasini_oladi() -> None:
    c = KuzatuvConfig(
        qidiruv_obunasiz=1, qidiruv_lite=3, qidiruv_pro=10, qidiruv_premium=30
    )
    assert chegara_ol(c, None) == 1
    assert chegara_ol(c, SubscriptionTier.LITE) == 3
    assert chegara_ol(c, SubscriptionTier.PRO) == 10
    assert chegara_ol(c, SubscriptionTier.PREMIUM) == 30


def test_obuna_chegarani_faqat_OSHIRADI() -> None:
    """Yuqoriroq tarif hech qachon kamroq qidiruv bermaydi."""
    c = KuzatuvConfig()
    ketma = [
        chegara_ol(c, None),
        chegara_ol(c, SubscriptionTier.LITE),
        chegara_ol(c, SubscriptionTier.PRO),
        chegara_ol(c, SubscriptionTier.PREMIUM),
    ]
    assert ketma == sorted(ketma)


def test_chegara_koddan_emas_configdan() -> None:
    """Raqamni admin o'zgartira olishi kerak (prompt talabi)."""
    c = KuzatuvConfig(qidiruv_pro=77)
    assert chegara_ol(c, SubscriptionTier.PRO) == 77


@pytest.mark.parametrize("tarif", [None, "nomalum", 0, ""])
def test_nomalum_tarif_obunasiz_chegarani_oladi(tarif: object) -> None:
    """Noma'lum tarifni "cheksiz" deb o'qish TESHIK ochardi."""
    c = KuzatuvConfig(qidiruv_obunasiz=1, qidiruv_premium=30)
    assert chegara_ol(c, tarif) == 1  # type: ignore[arg-type]
