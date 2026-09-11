"""Kitobning dizayn tizimi — ranglar, shriftlar, sahifa qolipi.

RANGLAR LOGOTIPDAN. Ular `web/src/app/globals.css` da piksel darajasida
o'lchangan va shu yerda TAKRORLANADI — ikki joyda boshqacha bo'lsa,
kitob bilan sayt boshqa-boshqa brend bo'lib ko'rinardi.

NEGA MATN OQ FONDA. Brend rangi to'q ko'k, lekin kitob BOSILADI va
o'nlab sahifa o'qiladi. To'q fonda uzun matn o'qish charchatadi va
printerda siyoh yeydi. Shuning uchun brend ranglari MUQOVA, bo'lim
ajratkichlari va BOB SARLAVHALARIDA ishlatiladi (7-promptning
0-qismidagi shart shunday), tana matni esa oq fonda qora-ko'k bilan.

NEGA DejaVu. ReportLab ning ichki shriftlarida o'zbek lotinchasining
`oʻ`/`gʻ` harflari YO'Q va ular qora kvadrat bo'lib chiqadi. DejaVu
ularni ham, `’ “ ” — • ₿` belgilarini ham qamrab oladi (tekshirilgan).
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ILDIZ = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------- #
#  Ranglar — logotipdan o'lchangan
# --------------------------------------------------------------------------- #

TURKUAZ = colors.HexColor("#01aac1")  # H ustuni
TURKUAZ_OCH = colors.HexColor("#00bcd5")  # H ko'ndalang chizig'i
APELSIN = colors.HexColor("#f47f16")  # C yoyi
KOK = colors.HexColor("#10469c")  # S yoyi
KOK_TOQ = colors.HexColor("#133c7c")  # past-chap shakl
SARIQ = colors.HexColor("#f0b02a")  # tepa-o'ng shakl
FON_TOQ = colors.HexColor("#0a2450")  # sayt foni

MATN = colors.HexColor("#1a2433")
MATN_PAST = colors.HexColor("#5b6878")
CHIZIQ = colors.HexColor("#d7dee8")
YUMSHOQ_FON = colors.HexColor("#f2f6fb")

#: Chizmalarda: o'suvchi va tushuvchi sham.
SHAM_OSDI = colors.HexColor("#12a15f")
SHAM_TUSHDI = colors.HexColor("#d8453a")

# --------------------------------------------------------------------------- #
#  Shriftlar
# --------------------------------------------------------------------------- #

SHRIFT = "HCS"
SHRIFT_QALIN = "HCS-Qalin"
SHRIFT_MONO = "HCS-Mono"

_DEJAVU = Path("/usr/share/fonts/truetype/dejavu")


def shriftlarni_qayd_et() -> None:
    """Bir marta chaqiriladi. Ikkinchi chaqiruv zararsiz."""
    if SHRIFT in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont(SHRIFT, str(_DEJAVU / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(SHRIFT_QALIN, str(_DEJAVU / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont(SHRIFT_MONO, str(_DEJAVU / "DejaVuSansMono.ttf")))
    pdfmetrics.registerFontFamily(SHRIFT, normal=SHRIFT, bold=SHRIFT_QALIN)


# --------------------------------------------------------------------------- #
#  Sahifa o'lchamlari
# --------------------------------------------------------------------------- #

SAHIFA = A4
CHAP = 22 * mm
ONG = 20 * mm
TEPA = 20 * mm
PAST = 20 * mm
MATN_ENI = SAHIFA[0] - CHAP - ONG


def uslublar() -> dict[str, ParagraphStyle]:
    """Kitobdagi barcha matn uslublari."""
    shriftlarni_qayd_et()
    asos = {"fontName": SHRIFT, "textColor": MATN}
    return {
        # --- Muqova ---
        "muqova_sarlavha": ParagraphStyle(
            "muqova_sarlavha",
            fontName=SHRIFT_QALIN,
            fontSize=34,
            leading=40,
            alignment=TA_CENTER,
            textColor=colors.white,
            spaceAfter=6,
        ),
        "muqova_kichik": ParagraphStyle(
            "muqova_kichik",
            fontName=SHRIFT,
            fontSize=13,
            leading=19,
            alignment=TA_CENTER,
            textColor=TURKUAZ_OCH,
        ),
        "muqova_izoh": ParagraphStyle(
            "muqova_izoh",
            fontName=SHRIFT,
            fontSize=9.5,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#9ab0d2"),
        ),
        # --- Bo'lim ajratkichi ---
        "bolim_raqam": ParagraphStyle(
            "bolim_raqam",
            fontName=SHRIFT,
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=APELSIN,
            spaceAfter=8,
        ),
        "bolim_nom": ParagraphStyle(
            "bolim_nom",
            fontName=SHRIFT_QALIN,
            fontSize=26,
            leading=32,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
        # --- Bob ---
        "bob_raqam": ParagraphStyle(
            "bob_raqam", fontName=SHRIFT, fontSize=10, leading=13,
            textColor=APELSIN, spaceAfter=3,
        ),
        "bob_nom": ParagraphStyle(
            "bob_nom", fontName=SHRIFT_QALIN, fontSize=20, leading=25,
            textColor=KOK_TOQ, spaceAfter=10,
        ),
        "sarlavha2": ParagraphStyle(
            "sarlavha2", fontName=SHRIFT_QALIN, fontSize=13, leading=17,
            textColor=KOK, spaceBefore=12, spaceAfter=5,
        ),
        "sarlavha3": ParagraphStyle(
            "sarlavha3", fontName=SHRIFT_QALIN, fontSize=10.5, leading=14,
            textColor=MATN, spaceBefore=8, spaceAfter=3,
        ),
        # --- Tana ---
        "tana": ParagraphStyle(
            "tana", **asos, fontSize=10, leading=15.5,
            alignment=TA_JUSTIFY, spaceAfter=7,
        ),
        "royxat": ParagraphStyle(
            "royxat", **asos, fontSize=10, leading=15,
            leftIndent=12, bulletIndent=2, spaceAfter=3,
        ),
        "izoh": ParagraphStyle(
            "izoh", fontName=SHRIFT, fontSize=8.5, leading=12.5,
            textColor=MATN_PAST, spaceAfter=5,
        ),
        # --- Maxsus bloklar ---
        "savol": ParagraphStyle(
            "savol", fontName=SHRIFT, fontSize=11, leading=16,
            textColor=KOK, spaceAfter=9, leftIndent=8,
            borderPadding=0,
        ),
        "xulosa_matn": ParagraphStyle(
            "xulosa_matn", **asos, fontSize=9.5, leading=14.5,
            alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "chizma_izoh": ParagraphStyle(
            "chizma_izoh", fontName=SHRIFT, fontSize=8.5, leading=12,
            textColor=MATN_PAST, alignment=TA_CENTER, spaceBefore=2, spaceAfter=10,
        ),
        # --- Mundarija ---
        "mundarija_bolim": ParagraphStyle(
            "mundarija_bolim", fontName=SHRIFT_QALIN, fontSize=11, leading=16,
            textColor=KOK_TOQ, spaceBefore=10, spaceAfter=3,
        ),
        "mundarija_bob": ParagraphStyle(
            "mundarija_bob", **asos, fontSize=9.5, leading=14, leftIndent=10,
        ),
    }


def qamrab_olinmagan(matn: str) -> set[str]:
    """Shrift QAMRAMAYDIGAN belgilar.

    NEGA KERAK. DejaVu keng qamrovli, lekin emoji YO'Q. Emoji
    ishlatilsa, PDF da u qora/bo'sh kvadrat ("tofu") bo'lib chiqadi
    va buni faqat PDF ni ochib ko'rgandagina sezasiz.

    Aynan shunday bo'ldi: "📊 REAL GRAFIK MISOLI" yozuvidagi emoji
    kitobda kvadrat bo'lib turdi. Endi buni test ushlaydi.
    """
    shriftlarni_qayd_et()
    xarita = pdfmetrics.getFont(SHRIFT).face.charToGlyph
    return {b for b in matn if ord(b) not in xarita and b not in "\n\r\t"}
