"""HAR BIR modul import qilinadimi.

NIMA UCHUN BU TEST BOR. 2026-09-04 da server ishga tushmadi:

    ModuleNotFoundError: No module named 'core.halal_screening.screener'

`screener.py` eski tahlil moduli bilan birga o'chirilgan edi, lekin
`core/halal_screening/__init__.py` dagi importi qolib ketgandi. Bu
xato:

  * `ruff` ni O'TDI — u modul mavjudligini tekshirmaydi;
  * 795 ta testni O'TDI — hech bir test o'sha paketni import
    qilmasdi;
  * `next build` ni O'TDI — u Pythonga tegmaydi;
  * va faqat RAILWAY'DA, ishga tushish paytida ko'rindi.

Ya'ni butun tekshiruv zanjiri yashil edi, server esa buzuq. Bu —
eng yomon turdagi xato.

Shuning uchun bu test hech narsani "sinamaydi": u shunchaki har bir
modulni IMPORT QILADI. Import paytida yiqiladigan har qanday xato
(yo'q modul, sintaksis, aylanma bog'liqlik) shu yerda ushlanadi.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

ILDIZ = Path(__file__).resolve().parents[1]

#: Import qilinadigan paketlar. `scripts` ham kiradi — `seed.py`
#: aynan shu tarzda yiqilgan edi.
PAKETLAR = ("core", "bot", "scripts")

#: Import qilinmaydiganlar.
#:
#: `scripts.*` ichida uzoq yuradigan o'lchov skriptlari bor, lekin
#: ular ham import paytida hech narsa qilmasligi kerak (`if __name__
#: == "__main__"` himoyasi). Shuning uchun ro'yxat BO'SH: istisno
#: qo'shish — tekshiruvda teshik ochish.
ISTISNOLAR: frozenset[str] = frozenset()


def modullar() -> list[str]:
    """`core`, `bot`, `scripts` ichidagi barcha modul nomlari."""
    topilgan: list[str] = []
    for paket_nomi in PAKETLAR:
        paket_yoli = ILDIZ / paket_nomi
        if not paket_yoli.is_dir():
            continue
        topilgan.append(paket_nomi)
        for modul in pkgutil.walk_packages([str(paket_yoli)], prefix=f"{paket_nomi}."):
            if modul.name not in ISTISNOLAR:
                topilgan.append(modul.name)
    return sorted(set(topilgan))


BARCHASI = modullar()


def test_modullar_topildi() -> None:
    """Ro'yxat bo'sh bo'lsa, test hech narsani tekshirmayotgan bo'lardi."""
    assert len(BARCHASI) > 50, f"Faqat {len(BARCHASI)} ta modul topildi — yig'ish buzilgan"


@pytest.mark.parametrize("nom", BARCHASI)
def test_modul_import_qilinadi(nom: str) -> None:
    """Modul import paytida yiqilmasin.

    Yiqilsa: xabarda modul nomi va sabab turadi. Odatiy sabablar —
    o'chirilgan fayldan qolgan import, nomi o'zgargan funksiya,
    yoki aylanma bog'liqlik.
    """
    importlib.import_module(nom)
