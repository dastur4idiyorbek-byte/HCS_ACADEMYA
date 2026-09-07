"""Fundamental blok — Token Unlock va Delisting qattiq to'siqlari."""

from __future__ import annotations

from core.analysis.fundamental.fundamental_block import (
    DelistingXavfi,
    FundamentalKirish,
    TokenUnlock,
    delisting_tosig,
    fundamental_blok,
    unlock_tosig,
)


def test_delisting_aniq_tosadi() -> None:
    assert delisting_tosig(DelistingXavfi(True, "Binance ogohlantirdi")) is not None
    assert delisting_tosig(DelistingXavfi(False)) is None
    assert delisting_tosig(None) is None


def test_unlock_yaqin_va_katta_tosadi() -> None:
    tosiq = unlock_tosig(TokenUnlock(kun_qoldi=3, pct=8.0), yaqin_kun=7, katta_pct=5.0)
    assert tosiq is not None
    assert "Token Unlock" in tosiq


def test_unlock_uzoq_yoki_kichik_tosmaydi() -> None:
    assert unlock_tosig(TokenUnlock(10, 8.0), yaqin_kun=7, katta_pct=5.0) is None
    assert unlock_tosig(TokenUnlock(3, 3.0), yaqin_kun=7, katta_pct=5.0) is None
    # Ma'lumot yo'q — to'siq yo'q (MALUMOT_YOQ tamoyili)
    assert unlock_tosig(TokenUnlock(None, 8.0), yaqin_kun=7, katta_pct=5.0) is None
    assert unlock_tosig(None, yaqin_kun=7, katta_pct=5.0) is None


def test_blok_delisting_bilan_otmaydi() -> None:
    kirish = FundamentalKirish(delisting=DelistingXavfi(True, "delist"))
    blok = fundamental_blok(kirish)
    assert not blok.otdi
    assert blok.qattiq_tosiq is not None


def test_blok_unlock_bilan_otmaydi() -> None:
    kirish = FundamentalKirish(unlock=TokenUnlock(2, 6.0))
    blok = fundamental_blok(kirish)
    assert not blok.otdi
    assert "Token Unlock" in (blok.qattiq_tosiq or "")


def test_blok_unlocksiz_otadi() -> None:
    blok = fundamental_blok(FundamentalKirish())
    assert blok.otdi  # bo'sh kirish — o'lchanmagan, zanjirni uzmaydi
