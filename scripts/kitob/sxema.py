"""Umumiy sxemalar — sham grafigi EMAS.

1-bo'lim (Asoslar) tushunchalari grafik bilan tushuntirilmaydi:
blokcheyn, hamyon, birja — bularda narx yo'q. Ularga quti va
strelkalardan iborat oddiy sxema kerak.

QOIDA: sxema tushunchani BIR QARASHDA ko'rsatishi kerak. Agar
sxemani tushunish uchun matnni o'qish shart bo'lsa, u ishlamayapti.
"""

from __future__ import annotations

import math

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
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
    "SARIQ", "SHRIFT", "TURKUAZ", "YUMSHOQ_FON", "Drawing", "Line", "colors", "mm",
    "matn", "oq", "quti", "taroziya", "yangi", "zanjir_boglami",
]
