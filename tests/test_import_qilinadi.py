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


def _ixtiyoriy_kutubxonalar() -> frozenset[str]:
    """`requirements-ml.txt` dagi kutubxona nomlari.

    NIMA UCHUN KERAK. Bu kutubxonalar (numpy, pandas, xgboost)
    ATAYLAB serverga ham, test muhitiga ham o'rnatilmaydi — ular
    ~100 MB joy egallaydi va faqat model o'rgatishda kerak
    (`requirements-ml.txt` ning o'zidagi izohga qarang). Model
    skriptlari esa `scripts/` ichida turadi va bu test ularni ham
    import qiladi.

    Ro'yxat FAYLDAN o'qiladi, qo'lda yozilmaydi: yangi kutubxona
    qo'shilsa, bu yer o'zi biladi.

    BU TESHIK EMAS. Faqat SHU nomlar yo'qligi kechiriladi. Boshqa
    har qanday `ModuleNotFoundError` — o'chirilgan fayldan qolgan
    import, nomi o'zgargan modul — avvalgidek testni yiqitadi.
    """
    fayl = ILDIZ / "requirements-ml.txt"
    if not fayl.is_file():
        return frozenset()
    nomlar = set()
    for qator in fayl.read_text().splitlines():
        toza = qator.split("#", 1)[0].strip()
        if not toza or toza.startswith("-"):
            continue
        nomlar.add(toza.split("==")[0].split(">=")[0].split("[")[0].strip())
    return frozenset(nomlar)


IXTIYORIY = _ixtiyoriy_kutubxonalar()


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
    try:
        importlib.import_module(nom)
    except ModuleNotFoundError as xato:
        if xato.name in IXTIYORIY:
            pytest.skip(f"`{xato.name}` o'rnatilmagan (requirements-ml.txt)")
        raise
