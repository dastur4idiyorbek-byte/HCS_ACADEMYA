"""Modul 4.0.0 — sessiya jadvali (`docs/MODUL_4_0_0.md`, 8-bo'lim)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.portlash_radari.vaqt import (
    KASHFIYOT,
    TASDIQ,
    JadvalSozlamasi,
    bajariladiganlar,
    keyingi_sham,
    keyingisi,
    kun_va_tartib,
    kunlik_yangilash_vaqti,
    oldingi_rasmiy_slot,
    sham_boshi,
)

J = JadvalSozlamasi()


def t(soat: int, daqiqa: int = 0, kun: int = 14) -> datetime:
    return datetime(2026, 10, kun, soat, daqiqa, tzinfo=UTC)


def test_kunda_12_sessiya_va_vaqtlari() -> None:
    """A — shamdan 1 soat, B — 15 daqiqa oldin (UTC)."""
    vaqtlar = set()
    hozir = t(0, 1)
    for _ in range(24 * 60):
        for r in bajariladiganlar(hozir, J):
            vaqtlar.add((r.turi, r.vaqt.hour, r.vaqt.minute))
        hozir += timedelta(minutes=1)
    assert {(h, m) for turi, h, m in vaqtlar if turi == KASHFIYOT} == {
        (23, 0), (3, 0), (7, 0), (11, 0), (15, 0), (19, 0)
    }
    assert {(h, m) for turi, h, m in vaqtlar if turi == TASDIQ} == {
        (23, 45), (3, 45), (7, 45), (11, 45), (15, 45), (19, 45)
    }


def test_2345_dagi_tasdiq_keyingi_kunning_birinchi_sessiyasi() -> None:
    """Qirg'iziston: kun 05:45 da boshlanadi = 23:45 UTC (oldingi kalendar kuni)."""
    (b,) = [r for r in bajariladiganlar(t(23, 45, kun=13), J) if r.turi == TASDIQ]
    assert b.sham_vaqti == t(0, 0, kun=14)
    assert kun_va_tartib(b.sham_vaqti) == ("2026-10-14", 1)


def test_kunning_oxirgi_sessiyasi_01_45_bishkek() -> None:
    """19:45 UTC = 01:45 Bishkek — o'sha kunning 6-sessiyasi."""
    (b,) = [r for r in bajariladiganlar(t(19, 45), J) if r.turi == TASDIQ]
    assert kun_va_tartib(b.sham_vaqti) == ("2026-10-14", 6)


def test_kechikish_chegarasi() -> None:
    """B — 14 daqiqa, A — 40 daqiqa. Undan keyin sessiya o'tkazib yuboriladi."""
    assert [r.turi for r in bajariladiganlar(t(3, 59), J)] == [TASDIQ]
    assert [r.turi for r in bajariladiganlar(t(4, 0), J)] == []
    assert [r.turi for r in bajariladiganlar(t(3, 40), J)] == [KASHFIYOT]
    assert [r.turi for r in bajariladiganlar(t(3, 41), J)] == []


def test_vaqti_kelmagan_sessiya_bajarilmaydi() -> None:
    assert bajariladiganlar(t(2, 59), J) == []


def test_keyingisi_kun_almashishida() -> None:
    r = keyingisi(t(19, 50), J)
    assert (r.turi, r.vaqt) == (KASHFIYOT, t(23, 0))
    r = keyingisi(t(23, 10), J)
    assert (r.turi, r.vaqt) == (TASDIQ, t(23, 45))
    r = keyingisi(t(23, 50), J, TASDIQ)
    assert r.vaqt == t(3, 45, kun=15)


def test_sham_hisobi() -> None:
    assert sham_boshi(t(5, 59)) == t(4)
    assert keyingi_sham(t(4)) == t(8)
    assert keyingi_sham(t(3, 59)) == t(4)


def test_sham_bo_lmagan_vaqt_rad_etiladi() -> None:
    with pytest.raises(ValueError):
        kun_va_tartib(t(5))


def test_naive_vaqt_rad_etiladi() -> None:
    with pytest.raises(ValueError):
        sham_boshi(datetime(2026, 10, 14, 5))


def test_ketma_ket_zanjiri_qoshnisi() -> None:
    assert oldingi_rasmiy_slot(TASDIQ, t(4)) == (KASHFIYOT, t(4))
    assert oldingi_rasmiy_slot(KASHFIYOT, t(4)) == (TASDIQ, t(0))
    with pytest.raises(ValueError):
        oldingi_rasmiy_slot("qolda", t(4))


def test_kunlik_yangilash_vaqti() -> None:
    assert kunlik_yangilash_vaqti(t(0, 4), 0, 5) == t(0, 5, kun=13)
    assert kunlik_yangilash_vaqti(t(0, 5), 0, 5) == t(0, 5)
