"""Bobning qayta ishlatiladigan bo'laklari: xulosa, savollar, real misol joyi.

Nima uchun alohida fayl: 24 ta bobda bir xil ko'rinadigan bloklar
bor. Ular har bobda qaytadan yozilsa, o'ntasi bir xil, o'n to'rttasi
boshqacha bo'lib ketardi.
"""

from __future__ import annotations

from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from scripts.kitob.chizma import ramka as chizma_ramkasi
from scripts.kitob.uslub import (
    APELSIN,
    CHIZIQ,
    KOK,
    KOK_TOQ,
    MATN,
    MATN_PAST,
    SHRIFT,
    SHRIFT_QALIN,
    TURKUAZ,
    YUMSHOQ_FON,
)

MATN_ENI = 168 * mm


def savol_bilan_boshla(u: dict, savol: str) -> list:
    """Har bob SAVOLDAN boshlanadi (7-prompt, 2-qism, 1-band)."""
    jadval = Table(
        [[Paragraph(savol, u["savol"])]],
        colWidths=[MATN_ENI],
    )
    jadval.setStyle(
        TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBEFORE", (0, 0), (0, -1), 2.2, APELSIN),
            ("BACKGROUND", (0, 0), (-1, -1), YUMSHOQ_FON),
        ])
    )
    return [jadval, Spacer(1, 5 * mm)]


def chizma_bilan(d: Drawing, izoh: str, u: dict) -> KeepTogether:
    """Sxema + uning tagidagi izohi. Ular sahifada AJRALMAYDI.

    `KeepTogether` shart: chizma bir sahifada, izohi keyingisida
    qolsa, o'quvchi "bu izoh nimaga tegishli" deb qidirardi.
    """
    chizma_ramkasi(d, d.width, d.height)
    d.hAlign = "CENTER"
    return KeepTogether([d, Paragraph(izoh, u["chizma_izoh"])])


def real_misol(u: dict, tavsif: str) -> KeepTogether:
    """TUR 2 — haqiqiy grafik skrinshoti uchun JOY.

    Admin keyin shu ramka ichiga TradingView/Binance skrinshotini
    qo'yadi. Joy ATAYLAB ko'zga tashlanadigan qilib belgilanadi:
    kitobda "to'ldirilmagan joy" yashirin qolsa, u shundayligicha
    bosilib ketardi.
    """
    ichki = [
        Paragraph(
            f'<font name="{SHRIFT_QALIN}" size="9" color="#f47f16">'
            "▣ REAL GRAFIK MISOLI — ADMIN TO'LDIRADI</font>",
            u["izoh"],
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            f'<font name="{SHRIFT}" size="8.5" color="#5b6878">{tavsif}</font>',
            u["izoh"],
        ),
        Spacer(1, 22 * mm),
    ]
    jadval = Table([[ichki]], colWidths=[MATN_ENI])
    jadval.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.1, APELSIN),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff8f0")),
        ])
    )
    return KeepTogether([Spacer(1, 3 * mm), jadval, Spacer(1, 5 * mm)])


def xulosa(u: dict, gaplar: list[str]) -> KeepTogether:
    """Bob oxiridagi qisqa xulosa — 3-5 gap."""
    ichki: list = [
        Paragraph(
            f'<font name="{SHRIFT_QALIN}" size="10" color="#133c7c">XULOSA</font>',
            u["izoh"],
        ),
        Spacer(1, 1.5 * mm),
    ]
    for gap in gaplar:
        ichki.append(Paragraph(f"•&nbsp;&nbsp;{gap}", u["xulosa_matn"]))
    jadval = Table([[ichki]], colWidths=[MATN_ENI])
    jadval.setStyle(
        TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("BACKGROUND", (0, 0), (-1, -1), YUMSHOQ_FON),
            ("LINEBEFORE", (0, 0), (0, -1), 2.2, TURKUAZ),
        ])
    )
    return KeepTogether([Spacer(1, 4 * mm), jadval])


def tekshiring(u: dict, savollar: list[str]) -> KeepTogether:
    """"O'zingizni tekshiring" — javobsiz savollar.

    JAVOB ATAYLAB BERILMAYDI: o'quvchi o'ylab ko'rsin. Javob
    yonida tursa, ko'z uni o'zi o'qib qo'yadi va savol ishlamaydi.
    """
    ichki: list = [
        Paragraph(
            f'<font name="{SHRIFT_QALIN}" size="10" color="#133c7c">'
            "O‘ZINGIZNI TEKSHIRING</font>",
            u["izoh"],
        ),
        Spacer(1, 1.5 * mm),
    ]
    for i, savol in enumerate(savollar, start=1):
        ichki.append(Paragraph(f"{i}.&nbsp;&nbsp;{savol}", u["xulosa_matn"]))
    jadval = Table([[ichki]], colWidths=[MATN_ENI])
    jadval.setStyle(
        TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("BOX", (0, 0), (-1, -1), 0.7, CHIZIQ),
        ])
    )
    return KeepTogether([Spacer(1, 3 * mm), jadval])


def jadval(u: dict, sarlavhalar: list[str], qatorlar: list[list[str]], enlar: list[float]) -> Table:
    """Brend uslubidagi jadval."""
    malumot = [[Paragraph(f"<b>{s}</b>", u["xulosa_matn"]) for s in sarlavhalar]]
    malumot += [[Paragraph(k, u["xulosa_matn"]) for k in q] for q in qatorlar]
    t = Table(malumot, colWidths=enlar, repeatRows=1)
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), KOK_TOQ),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), SHRIFT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, CHIZIQ),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, YUMSHOQ_FON]),
        ])
    )
    return t


def p(u: dict, matn: str) -> Paragraph:
    """Oddiy tana xatboshisi — eng ko'p ishlatiladigan chaqiruv."""
    return Paragraph(matn, u["tana"])


def h2(u: dict, matn: str) -> Paragraph:
    return Paragraph(matn, u["sarlavha2"])


def h3(u: dict, matn: str) -> Paragraph:
    return Paragraph(matn, u["sarlavha3"])


def royxat(u: dict, bandlar: list[str]) -> list:
    """Nuqtali ro'yxat."""
    return [Paragraph(f"•&nbsp;&nbsp;{b}", u["royxat"]) for b in bandlar]


#: Atamani birinchi marta kiritishda QALIN qilish uchun qisqartma.
def a(matn: str) -> str:
    """Yangi atama — qalin (7-prompt, 2-qism, 3-band)."""
    return f'<font name="{SHRIFT_QALIN}">{matn}</font>'


__all__ = [
    "APELSIN", "KOK", "MATN", "MATN_PAST", "TURKUAZ",
    "a", "chizma_bilan", "h2", "h3", "jadval", "p", "real_misol",
    "royxat", "savol_bilan_boshla", "tekshiring", "xulosa",
]
