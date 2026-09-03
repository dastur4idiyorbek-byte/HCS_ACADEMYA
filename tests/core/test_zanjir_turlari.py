"""Blok/zanjir tiplari — uzilish qoidasi va MALUMOT_YOQ mantig'i."""

from __future__ import annotations

import pytest

from core.analysis.turlar import Zanjir, blok, ha, malumot_yoq, yoq


def test_bosh_blok_zanjirni_uzadi() -> None:
    """0/4 — zanjir shu yerda uziladi (2-prompt, 4-qism)."""
    b = blok("Test", [yoq("a"), yoq("b"), yoq("c"), yoq("d")])
    assert not b.otdi
    assert b.kuch == 0
    assert b.maxraj == 4


def test_bitta_ijobiy_yetarli() -> None:
    """1/4 — blok o'tadi, zaiflik darajasi bilan."""
    b = blok("Test", [ha("a"), yoq("b"), yoq("c"), yoq("d")])
    assert b.otdi
    assert b.nisbat == pytest.approx(0.25)


def test_malumot_yoq_maxrajga_kirmaydi() -> None:
    """Bu — modulning eng muhim qoidasi.

    Tarixi yo'q manba blokni nolga tushirmasligi kerak, aks holda
    backtestda zanjir HECH QACHON ulanmaydi.
    """
    b = blok("Test", [ha("a"), yoq("b"), malumot_yoq("c"), malumot_yoq("d")])
    assert b.maxraj == 2
    assert b.nisbat == pytest.approx(0.5)


def test_hammasi_malumotsiz_blok_uzmaydi() -> None:
    """O'lchanmagan blok — "bo'sh" emas, u shunchaki jim turadi."""
    b = blok("Test", [malumot_yoq("a"), malumot_yoq("b")])
    assert b.olchanmadi
    assert b.otdi
    assert b.maxraj == 0


def test_qattiq_tosiq_hamma_narsani_bekor_qiladi() -> None:
    """Unlock to'sig'i — 4/4 bo'lsa ham blok o'tmaydi."""
    b = blok("Test", [ha("a"), ha("b"), ha("c"), ha("d")], qattiq_tosiq="unlock")
    assert not b.otdi
    assert "TO'SILDI" in str(b)


def test_ishonch_olchangan_bloklar_ortachasi() -> None:
    b1 = blok("A", [ha("x"), ha("y"), yoq("z"), yoq("w")])  # 0.50
    b2 = blok("B", [ha("x"), ha("y"), ha("z"), yoq("w")])  # 0.75
    z = Zanjir((b1, b2))
    assert z.ishonch() == pytest.approx(0.625)


def test_olchanmagan_blok_ishonchni_pasaytirmaydi() -> None:
    """Aks holda ma'lumot yo'qligi natijani jimgina buzardi."""
    b1 = blok("A", [ha("x"), ha("y"), ha("z"), ha("w")])
    bosh = blok("B", [malumot_yoq("x")])
    assert Zanjir((b1, bosh)).ishonch() == pytest.approx(1.0)


def test_uzilgan_zanjir_toliq_emas() -> None:
    z = Zanjir((blok("A", [yoq("x")]),), uzildi_blokda="A")
    assert not z.toliq
    assert "uzildi" in z.matn()


def test_ishonchsiz_zanjirda_nol() -> None:
    assert Zanjir(()).ishonch() == 0.0
