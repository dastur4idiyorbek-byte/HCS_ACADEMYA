"""Umumiy sxemalar — sham grafigi EMAS.

1-bo'lim (Asoslar) tushunchalari grafik bilan tushuntirilmaydi:
blokcheyn, hamyon, birja — bularda narx yo'q. Ularga quti va
strelkalardan iborat oddiy sxema kerak.

QOIDA: sxema tushunchani BIR QARASHDA ko'rsatishi kerak. Agar
sxemani tushunish uchun matnni o'qish shart bo'lsa, u ishlamayapti.
"""

from __future__ import annotations

import math

from reportlab.graphics.shapes import (
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

from scripts.kitob.uslub import (
    APELSIN,
    CHIZIQ,
    KOK,
    KOK_TOQ,
    MATN,
    MATN_PAST,
    SARIQ,
    SHRIFT,
    SHRIFT_QALIN,
    TURKUAZ,
    YUMSHOQ_FON,
    shriftlarni_qayd_et,
)

ENI = 160 * mm

#: Ustunli diagramma ranglari — modul darajasida, chunki ularni
#: funksiya argumentida chaqirish har chaqiruvda yangi obyekt yasardi.
USTUN_MUSBAT = colors.HexColor("#12a15f")
USTUN_MANFIY = colors.HexColor("#d8453a")


def yangi(eni: float = ENI, boyi: float = 55 * mm) -> Drawing:
    shriftlarni_qayd_et()
    return Drawing(eni, boyi)


def matn(
    d: Drawing,
    x: float,
    y: float,
    qator: str,
    *,
    olcham: float = 7.5,
    rang=MATN,  # noqa: ANN001
    qalin: bool = False,
    markaz: bool = True,
) -> None:
    s = String(x, y, qator, fontSize=olcham, fillColor=rang)
    s.fontName = SHRIFT_QALIN if qalin else SHRIFT
    if markaz:
        s.textAnchor = "middle"
    d.add(s)


def quti(  # noqa: PLR0913
    d: Drawing,
    x: float,
    y: float,
    eni: float,
    boyi: float,
    qatorlar: list[str],
    *,
    ramka=KOK,  # noqa: ANN001
    ichi=YUMSHOQ_FON,  # noqa: ANN001
    sarlavha_rang=KOK_TOQ,  # noqa: ANN001
) -> None:
    """Yorliqli quti. Birinchi qator — sarlavha (qalin)."""
    d.add(Rect(x, y, eni, boyi, fillColor=ichi, strokeColor=ramka, strokeWidth=1.0))
    if not qatorlar:
        return
    qator_boyi = 9.5
    jami = qator_boyi * len(qatorlar)
    ust = y + boyi / 2 + jami / 2 - qator_boyi + 2.5
    for i, q in enumerate(qatorlar):
        matn(
            d, x + eni / 2, ust - i * qator_boyi, q,
            olcham=8 if i == 0 else 7,
            rang=sarlavha_rang if i == 0 else MATN_PAST,
            qalin=i == 0,
        )


def oq(  # noqa: PLR0913
    d: Drawing,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    rang=APELSIN,  # noqa: ANN001
    yorliq: str = "",
    uzuq: bool = False,
) -> None:
    """Strelka + ustidagi yorliq."""
    d.add(
        Line(
            x0, y0, x1, y1,
            strokeColor=rang,
            strokeWidth=1.1,
            strokeDashArray=[3, 2] if uzuq else None,
        )
    )
    burchak = math.atan2(y1 - y0, x1 - x0)
    uz = 3.2
    d.add(
        Polygon(
            [
                x1, y1,
                x1 - uz * math.cos(burchak - 0.42), y1 - uz * math.sin(burchak - 0.42),
                x1 - uz * math.cos(burchak + 0.42), y1 - uz * math.sin(burchak + 0.42),
            ],
            fillColor=rang,
            strokeColor=rang,
        )
    )
    if yorliq:
        matn(d, (x0 + x1) / 2, (y0 + y1) / 2 + 3, yorliq, olcham=7, rang=rang)


def zanjir_boglami(d: Drawing, x0: float, y: float, eni: float, boyi: float, soni: int,
                   nomlar: list[list[str]]) -> None:
    """Blok -> blok -> blok ko'rinishidagi zanjir."""
    oraliq = 9 * mm
    for i in range(soni):
        x = x0 + i * (eni + oraliq)
        quti(d, x, y, eni, boyi, nomlar[i], ramka=TURKUAZ, ichi=colors.HexColor("#eef9fb"))
        if i:
            oq(d, x - oraliq + 1, y + boyi / 2, x - 1.5, y + boyi / 2, rang=APELSIN)


def taroziya(d: Drawing, x: float, y: float, chap: str, ong: str, *, boyi: float = 4 * mm) -> None:
    """Ikki tomonlama solishtiruv chizig'i (masalan CEX va DEX)."""
    d.add(Line(x, y, x + 60 * mm, y, strokeColor=CHIZIQ, strokeWidth=0.8))
    matn(d, x, y + boyi, chap, olcham=7, rang=MATN_PAST, markaz=False)
    matn(d, x + 60 * mm, y + boyi, ong, olcham=7, rang=MATN_PAST, markaz=False)


__all__ = [
    "APELSIN", "CHIZIQ", "KOK", "KOK_TOQ", "MATN", "MATN_PAST",
    "SARIQ", "SHRIFT", "TURKUAZ", "YUMSHOQ_FON",
    "Drawing", "Group", "Line", "Rect", "colors", "mm",
    "chiziqli", "matn", "oq", "quti", "shkala", "taroziya", "ustunli",
    "yangi", "zanjir_boglami",
]


# --------------------------------------------------------------------------- #
#  Oddiy diagrammalar — fundamental bo'lim uchun
# --------------------------------------------------------------------------- #


def _oq_qatorlar(d: Drawing, x0: float, y0: float, eni: float, boyi: float) -> None:
    """Diagramma maydonining ramkasi va nol chizig'i emas — faqat ramka."""
    d.add(Rect(x0, y0, eni, boyi, fillColor=None, strokeColor=CHIZIQ, strokeWidth=0.6))


def chiziqli(  # noqa: PLR0913
    d: Drawing,
    x0: float,
    y0: float,
    eni: float,
    boyi: float,
    qiymatlar: list[float],
    *,
    rang=KOK,  # noqa: ANN001
    yorliq: str = "",
) -> None:
    """Oddiy chiziqli diagramma (masalan DXY yoki narx yo'nalishi)."""
    _oq_qatorlar(d, x0, y0, eni, boyi)
    past, baland = min(qiymatlar), max(qiymatlar)
    oraliq = max(baland - past, 1e-9)
    n = len(qiymatlar)
    nuqtalar = []
    for i, q in enumerate(qiymatlar):
        x = x0 + eni * (i / max(n - 1, 1))
        y = y0 + boyi * 0.12 + (boyi * 0.76) * ((q - past) / oraliq)
        nuqtalar += [x, y]
    d.add(PolyLine(nuqtalar, strokeColor=rang, strokeWidth=1.5))
    if yorliq:
        matn(d, x0 + eni / 2, y0 + boyi + 3, yorliq, olcham=7.5, qalin=True, rang=rang)


def ustunli(  # noqa: PLR0913
    d: Drawing,
    x0: float,
    y0: float,
    eni: float,
    boyi: float,
    qiymatlar: list[float],
    *,
    yorliqlar: list[str] | None = None,
    musbat=USTUN_MUSBAT,  # noqa: ANN001
    manfiy=USTUN_MANFIY,  # noqa: ANN001
    sarlavha: str = "",
) -> None:
    """Nol chizig'i atrofidagi ustunlar (Netflow, Funding Rate).

    NOL CHIZIG'I MUHIM: bu diagrammalarda ishora (musbat/manfiy)
    kattalikdan ko'ra ko'proq narsa aytadi.
    """
    _oq_qatorlar(d, x0, y0, eni, boyi)
    eng = max(abs(q) for q in qiymatlar) or 1.0
    nol_y = y0 + boyi / 2
    d.add(Line(x0, nol_y, x0 + eni, nol_y, strokeColor=MATN_PAST, strokeWidth=0.8))
    matn(d, x0 - 3, nol_y - 2, "0", olcham=6.5, rang=MATN_PAST, markaz=False)
    qadam = eni / len(qiymatlar)
    for i, q in enumerate(qiymatlar):
        h = (boyi / 2 - 4) * (q / eng)
        x = x0 + qadam * i + qadam * 0.25
        d.add(
            Rect(
                x, nol_y if h >= 0 else nol_y + h,
                qadam * 0.5, abs(h),
                fillColor=musbat if q >= 0 else manfiy,
                strokeColor=None,
            )
        )
        if yorliqlar:
            matn(d, x + qadam * 0.25, y0 - 6, yorliqlar[i], olcham=6.5, rang=MATN_PAST)
    if sarlavha:
        matn(d, x0 + eni / 2, y0 + boyi + 3, sarlavha, olcham=7.5, qalin=True)


def shkala(  # noqa: PLR0913
    d: Drawing,
    x0: float,
    y0: float,
    eni: float,
    qiymat: float,
    *,
    chap_yorliq: str,
    ong_yorliq: str,
    sarlavha: str = "",
) -> None:
    """0-100 oralig'idagi shkala va undagi belgi (Fear & Greed).

    RANG O'TISHI YO'Q, uchta bo'lak bor: chizmada rang o'tishi
    chiroyli, lekin "men qayerdaman" degan savolga javob bermaydi.
    """
    boyi = 5 * mm
    bolaklar = [
        (0, 25, colors.HexColor("#d8453a")),
        (25, 45, colors.HexColor("#f0b02a")),
        (45, 55, colors.HexColor("#c9d3de")),
        (55, 75, colors.HexColor("#7cc47f")),
        (75, 100, colors.HexColor("#12a15f")),
    ]
    for bosh, oxir, rang in bolaklar:
        d.add(
            Rect(
                x0 + eni * bosh / 100, y0,
                eni * (oxir - bosh) / 100, boyi,
                fillColor=rang, strokeColor=None,
            )
        )
    x = x0 + eni * qiymat / 100
    d.add(Polygon([x, y0 + boyi + 1, x - 2.6, y0 + boyi + 6, x + 2.6, y0 + boyi + 6],
                  fillColor=MATN, strokeColor=MATN))
    matn(d, x, y0 + boyi + 8, f"{qiymat:.0f}", olcham=7.5, qalin=True)
    matn(d, x0, y0 - 7, chap_yorliq, olcham=7, rang=MATN_PAST, markaz=False)
    s = String(x0 + eni, y0 - 7, ong_yorliq, fontSize=7, fillColor=MATN_PAST)
    s.fontName = SHRIFT
    s.textAnchor = "end"
    d.add(s)
    if sarlavha:
        matn(d, x0 + eni / 2, y0 + boyi + 14, sarlavha, olcham=7.5, qalin=True)
