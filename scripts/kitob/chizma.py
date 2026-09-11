"""Sxematik chizmalar — kitobning ENG MUHIM qismi.

7-promptning 2.1-bandi: har bir texnik tushuncha MATN BILANGINA EMAS,
grafik misol bilan tushuntiriladi. Chizmasiz nazariy tushuntirish
qabul qilinmaydi.

NEGA SOXTA (SXEMATIK) SHAMLAR, HAQIQIY EMAS. Darslik chizmasi
tushunchani ENG TOZA holatda ko'rsatishi kerak: haqiqiy grafikda
Order Block ham, shovqin ham, boshqa o'nlab narsa ham bir vaqtda
turadi va yangi o'quvchi nimaga qarashni bilmaydi. Haqiqiy misollar
uchun alohida joy qoldiriladi (`real_misol`), u yerni admin
skrinshot bilan to'ldiradi.

NARXLAR QO'LDA YOZILADI. Tasodifiy son generatori chiroyli ko'rinishi
mumkin, lekin u ba'zan tushunchani BUZADI (masalan "bu yerda swing
bo'lishi kerak" degan joyda swing chiqmay qoladi). Har bir chizma —
o'sha tushunchaning aniq ko'rinishi.
"""

from __future__ import annotations

from dataclasses import dataclass

from reportlab.graphics.shapes import (
    Circle,
    Drawing,
    Group,
    Line,
    Polygon,
    PolyLine,
    Rect,
    String,
)
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from scripts.kitob.uslub import (
    APELSIN,
    CHIZIQ,
    KOK,
    KOK_TOQ,
    MATN,
    MATN_PAST,
    SARIQ,
    SHAM_OSDI,
    SHAM_TUSHDI,
    SHRIFT,
    SHRIFT_QALIN,
    TURKUAZ,
    shriftlarni_qayd_et,
)

#: Chizmaning standart o'lchami — matn kengligiga mos.
ENI = 160 * mm
BOYI = 62 * mm

#: Chizma ichidagi chekka — yorliqlar kesilmasligi uchun.
CHEKKA_CHAP = 6 * mm
CHEKKA_ONG = 6 * mm
CHEKKA_TEPA = 7 * mm
CHEKKA_PAST = 6 * mm


@dataclass(frozen=True)
class Sham:
    """Bitta sham: ochilish, eng yuqori, eng past, yopilish."""

    o: float
    h: float
    l: float  # noqa: E741 — bozor atamasi, `low`
    c: float

    @property
    def osdi(self) -> bool:
        return self.c >= self.o


def shamlar(qatorlar: list[tuple[float, float, float, float]]) -> list[Sham]:
    return [Sham(*q) for q in qatorlar]


class Kanvas:
    """Narx/vaqtni chizma koordinatalariga o'giradigan yordamchi.

    Nima uchun alohida sinf: har bir chizmada "narx 105 qayerda
    turadi" degan savol qayta-qayta chiqadi. U bitta joyda hisoblansa,
    gorizontal chiziq ham, zona to'rtburchagi ham, yorliq ham AYNAN
    bir joyga tushadi.
    """

    def __init__(
        self,
        eni: float,
        boyi: float,
        sham_soni: int,
        eng_past: float,
        eng_baland: float,
        *,
        bosh_joy_ong: float = 0.0,
        tepa_joy: float = 0.0,
    ) -> None:
        self.eni = eni
        self.boyi = boyi
        self._x0 = CHEKKA_CHAP
        self._x1 = eni - CHEKKA_ONG - bosh_joy_ong
        self._y0 = CHEKKA_PAST
        # `tepa_joy` — eng baland sham USTIDA qoldiriladigan bo'sh joy.
        # Nuqta yorliqlari (`nuqta`) shamdan yuqoriroqqa yoziladi va
        # ular chizmadan chiqib ketmasligi kerak. Chizma balandligini
        # oshirish yordam bermaydi: narx oralig'i baribir butun
        # balandlikka cho'ziladi.
        self._y1 = boyi - CHEKKA_TEPA - tepa_joy
        self._n = max(sham_soni, 1)
        # Narx oralig'iga 8% "havo" qo'shiladi: aks holda eng baland
        # soya chizmaning tepasiga yopishib qoladi.
        oraliq = max(eng_baland - eng_past, 1e-9)
        self._past = eng_past - oraliq * 0.08
        self._baland = eng_baland + oraliq * 0.08

    @property
    def qadam(self) -> float:
        return (self._x1 - self._x0) / self._n

    def x(self, indeks: float) -> float:
        """Sham markazining x koordinatasi."""
        return self._x0 + self.qadam * (indeks + 0.5)

    def y(self, narx: float) -> float:
        ulush = (narx - self._past) / (self._baland - self._past)
        return self._y0 + ulush * (self._y1 - self._y0)

    @property
    def chap(self) -> float:
        return self._x0

    @property
    def ong(self) -> float:
        return self._x1


def _yozuv(  # noqa: PLR0913
    matn: str,
    x: float,
    y: float,
    *,
    olcham: float = 7,
    rang=MATN,  # noqa: ANN001
    qalin: bool = False,
    markaz: bool = False,
    ong: bool = False,
) -> String:
    s = String(x, y, matn, fontSize=olcham, fillColor=rang)
    s.fontName = SHRIFT_QALIN if qalin else SHRIFT
    if markaz:
        s.textAnchor = "middle"
    elif ong:
        s.textAnchor = "end"
    return s


def _fon(d: Drawing, s: String) -> None:
    """Yozuv ostiga OQ TAGLIK qo'yadi.

    NEGA KERAK. Chizmadagi yorliq shamning ustiga tushib qolishi
    mumkin va u o'qilmay qoladi — aynan shunday bo'ldi: "bo'yin
    chizig'i" yozuvi birinchi shamning ustida turib qoldi.

    Yorliqni ko'chirish yechim emas: sham joyi har chizmada boshqa.
    Oq taglik esa har holatda ishlaydi.
    """
    shriftlarni_qayd_et()
    eni = pdfmetrics.stringWidth(s.text, s.fontName, s.fontSize)
    boyi = s.fontSize
    x = s.x
    if s.textAnchor == "middle":
        x -= eni / 2
    elif s.textAnchor == "end":
        x -= eni
    d.add(
        Rect(
            x - 1.2, s.y - boyi * 0.26, eni + 2.4, boyi * 1.08,
            fillColor=colors.Color(1, 1, 1, alpha=0.82),
            strokeColor=None,
        )
    )


def _fonli(d: Drawing, s: String) -> None:
    """Taglik + yozuv — tartib muhim: taglik oldin chiziladi."""
    _fon(d, s)
    d.add(s)


def _sham_guruhi(k: Kanvas, ketma: list[Sham], *, xira: set[int] | None = None) -> Group:
    """Shamlarni chizadi. `xira` — orqa fonga surilgan shamlar indeksi."""
    g = Group()
    kenglik = k.qadam * 0.56
    xira = xira or set()
    for i, sh in enumerate(ketma):
        x = k.x(i)
        rang = SHAM_OSDI if sh.osdi else SHAM_TUSHDI
        if i in xira:
            rang = colors.HexColor("#c3ccd8")
        # Soya
        g.add(Line(x, k.y(sh.l), x, k.y(sh.h), strokeColor=rang, strokeWidth=0.8))
        # Tana. Doji (ochilish = yopilish) uchun eng kam balandlik
        # beriladi — aks holda sham butunlay yo'qolib ketardi.
        past, baland = min(sh.o, sh.c), max(sh.o, sh.c)
        boyi = max(k.y(baland) - k.y(past), 0.9)
        g.add(
            Rect(
                x - kenglik / 2,
                k.y(past),
                kenglik,
                boyi,
                fillColor=rang,
                strokeColor=rang,
                strokeWidth=0.4,
            )
        )
    return g


def sham_chizma(
    ketma: list[Sham],
    *,
    eni: float = ENI,
    boyi: float = BOYI,
    bosh_joy_ong: float = 0.0,
    tepa_joy: float = 0.0,
    xira: set[int] | None = None,
) -> tuple[Drawing, Kanvas]:
    """Bo'sh sham grafigi + uning kanvasi.

    Kanvas qaytariladi, chunki chaqiruvchi ustiga chiziq, zona va
    yorliq qo'shadi — ular AYNAN shamlar bilan bir o'lchovda
    turishi kerak.
    """
    shriftlarni_qayd_et()
    d = Drawing(eni, boyi)
    eng_past = min(s.l for s in ketma)
    eng_baland = max(s.h for s in ketma)
    k = Kanvas(
        eni, boyi, len(ketma), eng_past, eng_baland,
        bosh_joy_ong=bosh_joy_ong, tepa_joy=tepa_joy,
    )
    d.add(_sham_guruhi(k, ketma, xira=xira))
    return d, k


# --------------------------------------------------------------------------- #
#  Ustiga qo'yiladigan belgilar
# --------------------------------------------------------------------------- #


def gorizontal(
    d: Drawing,
    k: Kanvas,
    narx: float,
    yorliq: str,
    *,
    rang=KOK,  # noqa: ANN001
    uzuq: bool = True,
    yorliq_chapda: bool = False,
) -> None:
    """Gorizontal daraja + uning yorlig'i."""
    y = k.y(narx)
    d.add(
        Line(
            k.chap, y, k.ong, y,
            strokeColor=rang,
            strokeWidth=1.1,
            strokeDashArray=[3, 2] if uzuq else None,
        )
    )
    if yorliq_chapda:
        _fonli(d, _yozuv(yorliq, k.chap + 2, y + 2.5, rang=rang, qalin=True))
    else:
        _fonli(d, _yozuv(yorliq, k.ong - 2, y + 2.5, rang=rang, qalin=True, ong=True))


def zona(
    d: Drawing,
    k: Kanvas,
    bosh_i: float,
    oxir_i: float,
    past: float,
    baland: float,
    yorliq: str,
    *,
    rang=APELSIN,  # noqa: ANN001
    shaffoflik: float = 0.18,
) -> None:
    """Rangli to'rtburchak zona (Order Block, FVG, Discount/Premium)."""
    x0 = k.x(bosh_i) - k.qadam * 0.5
    x1 = k.x(oxir_i) + k.qadam * 0.5
    y0, y1 = k.y(past), k.y(baland)
    ichki = colors.Color(rang.red, rang.green, rang.blue, alpha=shaffoflik)
    d.add(
        Rect(x0, y0, x1 - x0, y1 - y0, fillColor=ichki, strokeColor=rang, strokeWidth=0.9)
    )
    if yorliq:
        d.add(
            _yozuv(
                yorliq, (x0 + x1) / 2, (y0 + y1) / 2 - 2.5,
                rang=rang, qalin=True, markaz=True,
            )
        )


def nuqta(
    d: Drawing,
    k: Kanvas,
    indeks: int,
    narx: float,
    yorliq: str,
    *,
    rang=KOK_TOQ,  # noqa: ANN001
    tepada: bool = True,
) -> None:
    """Swing nuqtasi kabi belgilangan joy."""
    x, y = k.x(indeks), k.y(narx)
    d.add(Circle(x, y, 1.9, fillColor=rang, strokeColor=colors.white, strokeWidth=0.6))
    _fonli(
        d, _yozuv(yorliq, x, y + (5 if tepada else -9), rang=rang, qalin=True, markaz=True)
    )


def strelka(
    d: Drawing,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    rang=MATN_PAST,  # noqa: ANN001
) -> None:
    """Ingichka strelka — nimaga qarash kerakligini ko'rsatadi."""
    d.add(Line(x0, y0, x1, y1, strokeColor=rang, strokeWidth=0.8))
    # Uchi: yo'nalish bo'yicha kichik uchburchak.
    import math

    burchak = math.atan2(y1 - y0, x1 - x0)
    uz = 2.6
    d.add(
        Polygon(
            [
                x1, y1,
                x1 - uz * math.cos(burchak - 0.4), y1 - uz * math.sin(burchak - 0.4),
                x1 - uz * math.cos(burchak + 0.4), y1 - uz * math.sin(burchak + 0.4),
            ],
            fillColor=rang,
            strokeColor=rang,
        )
    )


def izoh_matni(  # noqa: ANN001, PLR0913
    d: Drawing, x: float, y: float, matn: str, *, rang=MATN_PAST, markaz: bool = False
) -> None:
    _fonli(d, _yozuv(matn, x, y, rang=rang, markaz=markaz))


def izoh_tepada(d: Drawing, x: float, matn: str, *, rang=MATN_PAST, qator: int = 0) -> None:  # noqa: ANN001
    """Chizmaning TEPASIGA yozadi — narx koordinatasidan mustaqil.

    NEGA KERAK. Ilgari izohlar narx bilan qo'yilardi ("y = 111"),
    lekin chizmaning narx oralig'i ma'lumotdan hisoblanadi. Shu
    sababli izoh ba'zan ramkadan chiqib, yuqoridagi xatboshi ustiga
    tushib qolardi. Bu yerda esa joy CHIZMA o'lchamidan olinadi.
    """
    # Bazaviy chiziq shrift balandligicha pastroqda: yozuvning YUQORI
    # qismi bazaviy chiziqdan tepada turadi va u ramkadan chiqib
    # ketardi.
    _fonli(d, _yozuv(matn, x, d.height - 11 - qator * 7.5, rang=rang, markaz=True))


def izoh_pastda(d: Drawing, x: float, matn: str, *, rang=MATN_PAST, qator: int = 0) -> None:  # noqa: ANN001
    """Chizmaning PASTIGA yozadi."""
    _fonli(d, _yozuv(matn, x, 3 + qator * 7.5, rang=rang, markaz=True))


def chiziq(  # noqa: ANN001
    d: Drawing,
    nuqtalar: list[tuple[float, float]],
    *,
    rang=TURKUAZ,
    qalinlik: float = 1.2,
    uzuq: bool = False,
) -> None:
    tekis = [q for nuqta_ in nuqtalar for q in nuqta_]
    d.add(
        PolyLine(
            tekis,
            strokeColor=rang,
            strokeWidth=qalinlik,
            strokeDashArray=[3, 2] if uzuq else None,
        )
    )


def ramka(d: Drawing, eni: float, boyi: float) -> None:
    """Chizma atrofidagi ingichka ramka — sahifada ajralib tursin."""
    d.add(
        Rect(
            0.5, 0.5, eni - 1, boyi - 1,
            fillColor=None, strokeColor=CHIZIQ, strokeWidth=0.7,
        )
    )


__all__ = [
    "APELSIN", "BOYI", "ENI", "KOK", "KOK_TOQ", "MATN", "MATN_PAST",
    "SARIQ", "SHAM_OSDI", "SHAM_TUSHDI", "SHRIFT", "TURKUAZ",
    "Kanvas", "Sham", "chiziq", "gorizontal", "izoh_matni", "nuqta",
    "izoh_pastda", "izoh_tepada",
    "ramka", "sham_chizma", "shamlar", "strelka", "zona",
]
