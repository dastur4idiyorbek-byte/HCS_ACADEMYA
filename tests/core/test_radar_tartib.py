"""Modul 4.0.0 — elak, o'rin, holat, ketma-ket, namuna."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

from core.config.schema import RadarConfig
from core.portlash_radari import tartib
from core.portlash_radari.sozlama import standart
from core.portlash_radari.tartib import TartibKirishi

CH = standart(RadarConfig())
HOZIR = datetime(2026, 10, 14, 7, 45, tzinfo=UTC)


def test_elak_3_barobar() -> None:
    assert tartib.elakdan_otadimi(3e6, 1e6, 30, False, CH) == (True, 3.0)
    otdi, nisbat = tartib.elakdan_otadimi(2.9e6, 1e6, 30, False, CH)
    assert (otdi, round(nisbat, 2)) == (False, 2.9)


def test_yangi_listing_o_rtachasiz_otadi() -> None:
    assert tartib.elakdan_otadimi(1e6, None, 0, True, CH) == (True, None)
    # tarix qisqa -> nisbat hisoblanmaydi
    assert tartib.elakdan_otadimi(9e6, 1e6, 3, False, CH) == (False, None)


def test_yangi_listing_belgisi() -> None:
    assert tartib.yangi_listingmi(HOZIR - timedelta(days=5), HOZIR, 30, CH)
    assert not tartib.yangi_listingmi(HOZIR - timedelta(days=400), HOZIR, 30, CH)
    assert tartib.yangi_listingmi(None, HOZIR, 3, CH)
    assert not tartib.yangi_listingmi(None, HOZIR, 7, CH)


def test_orin_qoidasi_toliq() -> None:
    """✅ soni -> tasdiqlangan -> yoqilg'i -> hajm nisbati -> symbol."""
    k = [
        TartibKirishi("EEE", 4, False, 1, None),
        TartibKirishi("DDD", 4, False, 1, 2.0),
        TartibKirishi("CCC", 4, False, 2, 1.0),
        TartibKirishi("BBB", 4, True, 0, 1.0),
        TartibKirishi("AAA", 5, False, 0, None),
        TartibKirishi("FFF", 4, False, 1, None),
    ]
    assert tartib.orinlar(k) == {
        "AAA": 1, "BBB": 2, "CCC": 3, "DDD": 4, "EEE": 5, "FFF": 6,
    }


def test_holat_tasdiqlangan_va_vaqtinchalik() -> None:
    assert tartib.holat("tasdiq", True, True) == tartib.TASDIQLANGAN
    assert tartib.holat("tasdiq", False, True) == tartib.VAQTINCHALIK
    assert tartib.holat("tasdiq", True, False) == tartib.NOMZOD
    assert tartib.holat("tasdiq", False, False) == tartib.ODDIY


def test_a_sessiyasi_yoq_bolsa_tasdiq_bilinmaydi() -> None:
    assert tartib.holat("tasdiq", True, None) == tartib.NOMZOD
    assert tartib.holat("kashfiyot", True, None) == tartib.NOMZOD
    assert tartib.holat("qolda", False, True) == tartib.ODDIY


def test_ketma_ket_kechirimsiz() -> None:
    assert tartib.ketma_ket("tasdiq", True, 2) == 3
    assert tartib.ketma_ket("tasdiq", True, None) == 1
    assert tartib.ketma_ket("tasdiq", False, 5) == 0
    assert tartib.ketma_ket("qolda", True, 5) == 0


def test_namuna_takrorlanadi_va_chegaralangan() -> None:
    royxat = [f"C{i}USDT" for i in range(50)]
    a = tartib.namuna_tanla(royxat, 10, "tasdiq:2026-10-14T08:00:00+00:00")
    b = tartib.namuna_tanla(list(reversed(royxat)), 10, "tasdiq:2026-10-14T08:00:00+00:00")
    assert a == b and len(a) == 10 and len(set(a)) == 10
    # so'ralganidan kam bo'lsa — hammasi
    assert sorted(tartib.namuna_tanla(royxat[:3], 10, "x")) == sorted(royxat[:3])
    assert tartib.namuna_tanla(royxat, 0, "x") == []


def test_elak_chegarasi_sozlamadan() -> None:
    ch = dataclasses.replace(CH, elak_hajm_x=10.0)
    assert tartib.elakdan_otadimi(5e6, 1e6, 30, False, ch)[0] is False
