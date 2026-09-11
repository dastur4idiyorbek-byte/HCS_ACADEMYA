"""HCS Academy kitobi — sifat qorovullari.

7-PROMPTNING MAJBURIY SHARTI (2.1-band): har bir texnik/amaliy
tushuncha grafik misol bilan tushuntiriladi, va har bo'limdan keyin
"har bobda kamida bitta chizma bormi" deb TEKSHIRILADI.

Bu tekshiruv qo'lda qilinsa unutiladi. Shuning uchun u test.
Birinchi yugurishdayoq haqiqiy kamchilik topdi: 1-bo'limning
3-bobida chizma yo'q edi.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ILDIZ = Path(__file__).resolve().parents[1]
KITOB = ILDIZ / "scripts" / "kitob"

#: Bo'lim fayllari — yangi bo'lim qo'shilganda shu yerga qo'shiladi.
BOLIM_FAYLLARI = ("bolim1.py",)


def _bob_funksiyalari(fayl: Path) -> list[ast.FunctionDef]:
    """Fayldagi `_bobN` funksiyalari."""
    daraxt = ast.parse(fayl.read_text())
    return [
        tugun
        for tugun in daraxt.body
        if isinstance(tugun, ast.FunctionDef) and tugun.name.startswith("_bob")
    ]


def _chaqiruvlar(tugun: ast.FunctionDef) -> set[str]:
    nomlar = set()
    for ichki in ast.walk(tugun):
        if isinstance(ichki, ast.Call) and isinstance(ichki.func, ast.Name):
            nomlar.add(ichki.func.id)
    return nomlar


@pytest.mark.parametrize("fayl_nomi", BOLIM_FAYLLARI)
def test_har_bobda_kamida_bitta_chizma(fayl_nomi: str) -> None:
    """Chizmasiz bob — qabul qilinmaydi."""
    fayl = KITOB / fayl_nomi
    boblar = _bob_funksiyalari(fayl)
    assert boblar, f"{fayl_nomi} da birorta bob topilmadi"

    chizmasiz = [b.name for b in boblar if "chizma_bilan" not in _chaqiruvlar(b)]
    assert not chizmasiz, (
        f"{fayl_nomi}: chizmasiz bob(lar) bor — {chizmasiz}. "
        "7-promptning 2.1-bandi har bobda kamida bitta sxema talab qiladi."
    )


@pytest.mark.parametrize("fayl_nomi", BOLIM_FAYLLARI)
def test_har_bobda_xulosa_va_savol(fayl_nomi: str) -> None:
    """Har bob xulosa bilan tugaydi (2-qism, 5-band)."""
    boblar = _bob_funksiyalari(KITOB / fayl_nomi)
    xulosasiz = [b.name for b in boblar if "xulosa" not in _chaqiruvlar(b)]
    assert not xulosasiz, f"{fayl_nomi}: xulosasiz bob(lar) — {xulosasiz}"


@pytest.mark.parametrize("fayl_nomi", BOLIM_FAYLLARI)
def test_har_bob_savoldan_boshlanadi(fayl_nomi: str) -> None:
    """Bob MUAMMO/SAVOLDAN boshlanadi (2-qism, 1-band)."""
    boblar = _bob_funksiyalari(KITOB / fayl_nomi)
    savolsiz = [
        b.name for b in boblar if "savol_bilan_boshla" not in _chaqiruvlar(b)
    ]
    assert not savolsiz, f"{fayl_nomi}: savolsiz boshlanadigan bob(lar) — {savolsiz}"


def test_kitob_quriladi(tmp_path) -> None:  # noqa: ANN001
    """PDF haqiqatan yasaladimi va sahifalari bormi.

    Bu test ATAYLAB PDF ni oxirigacha quradi. Sabab: kitobning
    ko'p xatosi (yo'q shrift belgisi, chizmadagi noto'g'ri
    koordinata) faqat chizish paytida chiqadi.
    """
    pytest.importorskip("reportlab")
    from scripts.kitob.qur import qur

    sahifalar, yol = qur(tmp_path / "sinov.pdf")
    assert yol.is_file()
    assert sahifalar >= 15, f"kutilganidan kam sahifa: {sahifalar}"  # noqa: PLR2004


def test_mundarija_ozini_sanamaydi(tmp_path) -> None:  # noqa: ANN001
    """Mundarija sahifasi mundarijaning birinchi qatori bo'lib qolmasin.

    Haqiqiy xatoning regressiya testi: sarlavha USLUB NOMI bo'yicha
    qayd etilardi va Mundarijaning o'z sarlavhasi ham o'sha uslubda
    edi.
    """
    pytest.importorskip("pypdf")
    from pypdf import PdfReader

    from scripts.kitob.qur import qur

    _, yol = qur(tmp_path / "sinov.pdf")
    mundarija_sahifasi = PdfReader(str(yol)).pages[1].extract_text()
    # Sarlavha sifatida BIR marta uchraydi, ro'yxat qatori sifatida emas.
    assert mundarija_sahifasi.count("MUNDARIJA") == 1, mundarija_sahifasi[:400]
    assert "1-BO" in mundarija_sahifasi, "bo'lim sarlavhasi mundarijaga tushmagan"
