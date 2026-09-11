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
BOLIM_FAYLLARI = (
    "bolim1.py", "bolim2.py", "bolim3.py",
    "bolim4.py", "bolim5.py", "bolim6.py", "yakun.py",
)


def _bob_funksiyalari(fayl: Path) -> list[ast.FunctionDef]:
    """Fayldagi bob funksiyalari.

    `yakun.py` ham bob — uning funksiyasi `yakun` deb ataladi,
    `_bobN` emas. Uni ro'yxatdan tashqarida qoldirish oxirgi bobni
    tekshiruvsiz qoldirardi.
    """
    daraxt = ast.parse(fayl.read_text())
    return [
        tugun
        for tugun in daraxt.body
        if isinstance(tugun, ast.FunctionDef)
        and (tugun.name.startswith("_bob") or tugun.name == "yakun")
    ]


def _matn_satrlari(fayl: Path) -> list[str]:
    """Fayldagi PDF GA TUSHADIGAN satrlar.

    IZOH VA DOKSTRINGLAR HISOBGA OLINMAYDI. Ular kitobga chiqmaydi,
    lekin ularda misol keltirilgan belgi (masalan emoji haqida
    yozilgan izoh) tekshiruvni yolg'on qizil qilardi.
    """
    daraxt = ast.parse(fayl.read_text())
    dokstringlar = set()
    for tugun in ast.walk(daraxt):
        if isinstance(tugun, ast.Module | ast.FunctionDef | ast.ClassDef):
            d = ast.get_docstring(tugun, clean=False)
            if d is not None:
                dokstringlar.add(d)
    return [
        t.value
        for t in ast.walk(daraxt)
        if isinstance(t, ast.Constant)
        and isinstance(t.value, str)
        and t.value not in dokstringlar
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


def test_shrift_barcha_belgilarni_qamraydi() -> None:
    """Kitob matnida shrift bilmaydigan belgi bo'lmasin.

    HAQIQIY XATONING REGRESSIYA TESTI. "▣ REAL GRAFIK MISOLI"
    yozuvida ilgari 📊 emoji turgan edi va u PDF da BO'SH KVADRAT
    bo'lib chiqardi — DejaVu da emoji yo'q. Buni faqat PDF ni
    ochib ko'rgandagina sezish mumkin edi.

    Test kitobning BARCHA manba fayllarini skanerlaydi.
    """
    pytest.importorskip("reportlab")
    from scripts.kitob.uslub import qamrab_olinmagan

    yomonlar: dict[str, set[str]] = {}
    for fayl in sorted(KITOB.glob("*.py")):
        topilgan = qamrab_olinmagan("".join(_matn_satrlari(fayl)))
        if topilgan:
            yomonlar[fayl.name] = topilgan
    assert not yomonlar, (
        f"Shrift qamramaydigan belgilar: {yomonlar}. "
        "Ular PDF da bo'sh kvadrat bo'lib chiqadi."
    )


#: Chizmali bo'limlar — bu yerda HAQIQIY GRAFIK MISOLI joyi ham shart.
GRAFIKLI_BOLIMLAR = ("bolim3.py", "bolim4.py", "bolim5.py")


@pytest.mark.parametrize("fayl_nomi", GRAFIKLI_BOLIMLAR)
def test_grafikli_boblarda_real_misol_joyi_bor(fayl_nomi: str) -> None:
    """3, 4 va 5-bo'lim boblarida admin uchun joy qoldirilsin.

    7-promptning 2.1-bandi (TUR 2): bu bo'limlarning har bir bobi
    oxirida haqiqiy skrinshot uchun aniq belgilangan joy bo'lishi
    kerak. Sxema nazariyani ko'rsatadi, haqiqiy grafik esa uni
    bozorda qanday ko'rinishini.
    """
    boblar = _bob_funksiyalari(KITOB / fayl_nomi)
    assert boblar, f"{fayl_nomi} da bob topilmadi"
    joysizlar = [b.name for b in boblar if "real_misol" not in _chaqiruvlar(b)]
    assert not joysizlar, (
        f"{fayl_nomi}: real misol joyi yo'q bob(lar) — {joysizlar}"
    )


def _chizma_funksiyalari(fayl: Path):  # noqa: ANN202
    """Fayldagi chizma yasovchi funksiyalar (`_sxema_`, `_grafik_`, `_diagramma_`)."""
    daraxt = ast.parse(fayl.read_text())
    return [
        t.name
        for t in daraxt.body
        if isinstance(t, ast.FunctionDef)
        and t.name.startswith(("_sxema_", "_grafik_", "_diagramma_"))
    ]


@pytest.mark.parametrize("fayl_nomi", [*BOLIM_FAYLLARI, "yakun.py"])
def test_chizma_yorliqlari_ramkadan_chiqmaydi(fayl_nomi: str) -> None:
    """Yorliq chizma chegarasidan tashqarida qolmasin.

    HAQIQIY XATONING REGRESSIYA TESTI. Ba'zi izohlar chizma
    balandligidan yuqoriga yozilgan edi va PDF da ular ramkadan
    chiqib, yuqoridagi xatboshi ustiga tushib qolardi.

    Koordinata narxdan hisoblangani uchun buni ko'z bilan har
    chizmada tekshirish kerak bo'lardi — shuning uchun test.
    """
    pytest.importorskip("reportlab")
    import importlib

    modul = importlib.import_module(f"scripts.kitob.{fayl_nomi[:-3]}")
    nomlar = _chizma_funksiyalari(KITOB / fayl_nomi)
    assert nomlar, f"{fayl_nomi} da chizma funksiyasi topilmadi"

    yomonlar: list[str] = []
    for nom in nomlar:
        d = getattr(modul, nom)()
        chap, past, ong, tepa = d.getBounds()
        # 1 punkt bag'rikenglik: ramka chizig'ining o'z qalinligi.
        if chap < -1 or past < -1 or ong > d.width + 1 or tepa > d.height + 1:
            yomonlar.append(
                f"{nom}: chegara ({chap:.0f},{past:.0f})-({ong:.0f},{tepa:.0f}) "
                f"o'lcham {d.width:.0f}x{d.height:.0f}"
            )
    assert not yomonlar, "Chizmadan chiqib ketgan element:\n" + "\n".join(yomonlar)
