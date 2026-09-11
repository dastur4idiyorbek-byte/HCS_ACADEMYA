"""Kitob qolipi — muqova, bo'lim ajratkichi, sahifa raqami, mundarija.

MUNDARIJA AVTOMATIK. Sahifa raqamlari qo'lda yozilmaydi: kitob
o'sganda ular darrov eskiradi va o'quvchi noto'g'ri sahifaga
boradi. ReportLab ning `TableOfContents` i sarlavhalarni yig'ib,
IKKINCHI yugurishda to'g'ri raqamni qo'yadi.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)
from reportlab.platypus.tableofcontents import TableOfContents

from scripts.kitob.uslub import (
    APELSIN,
    CHAP,
    CHIZIQ,
    FON_TOQ,
    ILDIZ,
    KOK_TOQ,
    MATN_PAST,
    ONG,
    PAST,
    SAHIFA,
    SHRIFT,
    SHRIFT_QALIN,
    TEPA,
    TURKUAZ_OCH,
    uslublar,
)

LOGO = ILDIZ / "web" / "public" / "logo.jpg"


class Kitob(BaseDocTemplate):
    """Uch xil sahifa qolipi: muqova, bo'lim ajratkichi, oddiy sahifa."""

    def __init__(self, yol: str) -> None:
        super().__init__(
            yol,
            pagesize=SAHIFA,
            leftMargin=CHAP,
            rightMargin=ONG,
            topMargin=TEPA,
            bottomMargin=PAST,
            title="Noldan kripto savdogariga",
            author="HCS Academy",
            subject="Halol Crypto Savdo o'quv qo'llanmasi",
        )
        ramka = Frame(
            CHAP, PAST,
            SAHIFA[0] - CHAP - ONG,
            SAHIFA[1] - TEPA - PAST,
            id="asosiy",
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        toliq = Frame(0, 0, SAHIFA[0], SAHIFA[1], id="toliq",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="toq", frames=[toliq], onPage=self._toq_fon),
            PageTemplate(id="oddiy", frames=[ramka], onPage=self._pastki_qator),
        ])
        self._uslublar = uslublar()

    # -- fon va pastki qator ------------------------------------------- #

    def _toq_fon(self, kanvas, _hujjat) -> None:  # noqa: ANN001
        kanvas.saveState()
        kanvas.setFillColor(FON_TOQ)
        kanvas.rect(0, 0, SAHIFA[0], SAHIFA[1], fill=1, stroke=0)
        kanvas.restoreState()

    def _pastki_qator(self, kanvas, hujjat) -> None:  # noqa: ANN001
        """Sahifa raqami va kitob nomi — har oddiy sahifada."""
        kanvas.saveState()
        y = PAST - 7 * mm
        kanvas.setStrokeColor(CHIZIQ)
        kanvas.setLineWidth(0.5)
        kanvas.line(CHAP, y + 4 * mm, SAHIFA[0] - ONG, y + 4 * mm)
        kanvas.setFont(SHRIFT, 7.5)
        kanvas.setFillColor(MATN_PAST)
        kanvas.drawString(CHAP, y, "HCS Academy — Noldan kripto savdogariga")
        kanvas.drawRightString(SAHIFA[0] - ONG, y, str(hujjat.page))
        kanvas.restoreState()

    # -- mundarija uchun sarlavhalarni qayd etish ----------------------- #

    def afterFlowable(self, flowable) -> None:  # noqa: ANN001, N802
        """Sarlavha chizilgach, uni mundarijaga qo'shadi.

        USLUB NOMIGA TAYANMAYDI. Ilgari shunday edi va u JIMGINA
        buzilgan: `_chekkali()` uslubni klonlaganda nom
        `bob_nom_chekka` bo'lib qolardi va bo'lim sarlavhasi
        mundarijaga umuman tushmasdi. Endi har bir sarlavha
        `_mundarija` belgisini o'zi olib yuradi.
        """
        belgi = getattr(flowable, "_mundarija", None)
        if belgi is not None:
            daraja, matn = belgi
            self.notify("TOCEntry", (daraja, matn, self.page))


class ToqChiziq(Flowable):
    """To'q fonli sahifada ingichka apelsin chiziq."""

    def __init__(self, eni: float = 40 * mm) -> None:
        super().__init__()
        self.width = eni
        self.height = 3 * mm

    def draw(self) -> None:
        self.canv.setStrokeColor(APELSIN)
        self.canv.setLineWidth(1.6)
        self.canv.line(0, 1.5 * mm, self.width, 1.5 * mm)


def muqova(u: dict) -> list:
    """Birinchi sahifa: logotip, sarlavha, kichik sarlavha."""
    ichki = []
    ichki.append(Spacer(1, 52 * mm))
    if LOGO.is_file():
        rasm = Image(str(LOGO), width=46 * mm, height=46 * mm)
        rasm.hAlign = "CENTER"
        ichki.append(rasm)
    ichki.append(Spacer(1, 14 * mm))
    ichki.append(Paragraph("NOLDAN<br/>KRIPTO SAVDOGARIGA", u["muqova_sarlavha"]))
    ichki.append(Spacer(1, 6 * mm))
    chiziq = ToqChiziq()
    chiziq.hAlign = "CENTER"
    ichki.append(chiziq)
    ichki.append(Spacer(1, 6 * mm))
    ichki.append(
        Paragraph("HCS Academy — Halol Crypto Savdo o'quv qo'llanmasi", u["muqova_kichik"])
    )
    ichki.append(Spacer(1, 40 * mm))
    ichki.append(
        Paragraph(
            "Bu kitob — TA'LIM uchun. Unda moliyaviy maslahat yo'q "
            "va birorta coin tavsiya qilinmaydi.",
            u["muqova_izoh"],
        )
    )
    # Muqova o'z ramkasida (to'liq sahifa) chizilgani uchun chekkani
    # o'zi qo'yadi: matn sahifa qirrasiga yopishmasin.
    return [*[_chekkali(x) for x in ichki], NextPageTemplate("oddiy"), PageBreak()]


def _chekkali(flow):  # noqa: ANN001, ANN202
    """Flowable ni chap-o'ng chekka bilan o'raydi."""
    if isinstance(flow, Paragraph):
        flow.style = flow.style.clone(
            flow.style.name + "_chekka",
            leftIndent=CHAP,
            rightIndent=ONG,
        )
    return flow


def bolim_ajratkich(u: dict, raqam: str, nom: str) -> list:
    """To'q fonli sahifa — yangi bo'lim boshlanishi.

    TARTIB MUHIM. `NextPageTemplate` KEYINGI sahifaga ta'sir qiladi,
    shuning uchun u `PageBreak` dan OLDIN turishi shart. Ilgari
    teskari edi va ajratkich oq sahifada chiqib qolgandi — oq
    fonda oq matn, ya'ni bo'sh sahifa.
    """
    sarlavha = _chekkali(Paragraph(nom, u["bolim_nom"]))
    sarlavha._mundarija = (0, f"{raqam} — {nom}")  # noqa: SLF001
    return [
        NextPageTemplate("toq"),
        PageBreak(),
        Spacer(1, 95 * mm),
        _chekkali(Paragraph(raqam, u["bolim_raqam"])),
        sarlavha,
        NextPageTemplate("oddiy"),
        PageBreak(),
    ]


def mundarija(u: dict) -> list:
    """Avtomatik mundarija."""
    t = TableOfContents()
    t.levelStyles = [
        u["mundarija_bolim"].clone("toc0"),
        u["mundarija_bob"].clone("toc1"),
    ]
    t.dotsMinLevel = 1
    return [
        Paragraph("MUNDARIJA", u["bob_nom"]),
        Spacer(1, 4 * mm),
        t,
        PageBreak(),
    ]  # `bob_nom` uslubi, lekin `_mundarija` belgisi YO'Q — o'zini sanamaydi


def bob_sarlavha(u: dict, raqam: str, nom: str, *, mundarijaga: bool = True) -> list:
    """Bob sarlavhasi. `mundarijaga=False` — Mundarijaning o'zi uchun.

    Mundarija sahifasi ham `bob_nom` uslubini ishlatadi va ilgari
    U O'ZI mundarijada birinchi qator bo'lib turardi.
    """
    nom_p = Paragraph(nom, u["bob_nom"])
    if mundarijaga:
        nom_p._mundarija = (1, f"{raqam}. {nom}")  # noqa: SLF001
    return [Paragraph(raqam, u["bob_raqam"]), nom_p]


__all__ = [
    "KOK_TOQ", "SHRIFT_QALIN", "TURKUAZ_OCH", "colors",
    "Kitob", "bob_sarlavha", "bolim_ajratkich", "muqova", "mundarija",
]
