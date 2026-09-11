"""Kitobni SAYT uchun JSON ga chiqaradi.

NEGA MAZMUN IKKI MARTA YOZILMAYDI. Kitob matni `bolim*.py` da
turadi va undan PDF quriladi. Sayt uchun ikkinchi nusxa yozilsa,
vaqt o'tib ular ajralib ketardi: PDF da tuzatilgan xato saytda
qolib ketardi (loyihada bu allaqachon bir necha marta bo'lgan).

Shuning uchun bu skript AYNAN O'SHA funksiyalarni chaqiradi va
natijani o'qiydi: har bir flowable — bitta blok.

CHIZMALAR SVG BO'LIB CHIQADI. Rasm emas: SVG har o'lchamda aniq
qoladi va faylda joy kam egallaydi. Ular oq fonda chizilgan
(kitob bosiladi), shuning uchun saytda oq kartochka ichida
ko'rsatiladi — matn esa saytning o'z rangida.

Ishlatish:
    python -m scripts.kitob.eksport
"""

from __future__ import annotations

import argparse
import io
import json
import re
from pathlib import Path
from typing import Any

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import KeepTogether, Paragraph, Table

from scripts.kitob.bolim1 import bolim1
from scripts.kitob.bolim2 import bolim2
from scripts.kitob.bolim3 import bolim3
from scripts.kitob.bolim4 import bolim4
from scripts.kitob.bolim5 import bolim5
from scripts.kitob.bolim6 import bolim6
from scripts.kitob.kirish import kirish
from scripts.kitob.uslub import ILDIZ, uslublar
from scripts.kitob.yakun import yakun

#: Chiqish joyi — PDF bilan BIR JILDDA.
#:
#: `src/lib/` da EMAS: u yerdagi JSON sayt to'plamiga (bundle)
#: kiritilardi va 300 KB ortiqcha yuk bo'lardi. Bu yerdan esa u
#: server tomonda, so'rov paytida o'qiladi.
STANDART_CHIQISH = ILDIZ / "web" / "kitob" / "mazmun.json"

#: Chizmalardagi shrift — saytning o'z shrifti bilan bir xil oila.
VEB_SHRIFTI = (
    "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, "
    "'Helvetica Neue', Arial, sans-serif"
)

#: Bo'lim kaliti -> (nomi, mazmun funksiyasi).
#: Kalitlar `web/src/lib/kitob.ts` dagi `KITOB_BOLIMLARI` bilan bir xil —
#: test ikkalasining mos kelishini ushlab turadi.
BOLIMLAR: tuple[tuple[str, Any], ...] = (
    ("kirish", kirish),
    ("asoslar", bolim1),
    ("fundamental", bolim2),
    ("texnik", bolim3),
    ("smc", bolim4),
    ("ict", bolim5),
    ("risk", bolim6),
    ("yakun", yakun),
)

#: Uslub nomi -> saytdagi blok turi.
USLUB_TURI = {
    "tana": "matn",
    "royxat": "royxat",
    "sarlavha2": "h2",
    "sarlavha3": "h3",
    "izoh": "izoh",
    "savol": "savol",
    "xulosa_matn": "xulosa_qator",
    "chizma_izoh": "chizma_izoh",
    "bob_raqam": "bob_raqam",
    "bob_nom": "bob_nom",
}


def _tozala(xom: str) -> str:
    """ReportLab belgilarini HTML ga o'giradi.

    `<font name="...">` — PDF uchun qalin qilishning yagona usuli
    edi (`bloklar.a()`). Saytda esa `<strong>` kerak.
    """
    matn = xom
    matn = re.sub(r'<font name="[^"]*-?Qalin"[^>]*>', "<strong>", matn)
    matn = re.sub(r'<font name="[^"]*"[^>]*>', "<span>", matn)
    matn = matn.replace("</font>", "</strong>")
    matn = matn.replace("&nbsp;", " ")
    return matn.strip()


def _svg(d: Drawing) -> str:
    """Chizmani SVG matniga aylantiradi."""
    xotira = io.StringIO()
    renderSVG.drawToFile(d, xotira)
    svg = xotira.getvalue()
    # XML sarlavhasi va DOCTYPE brauzerda kerak emas va React ga
    # `dangerouslySetInnerHTML` orqali qo'yilganda xalaqit beradi.
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"<!DOCTYPE[^>]*>", "", svg, flags=re.DOTALL)
    # SHRIFT NOMINI BRAUZER TUSHUNADIGAN QILISH.
    #
    # ReportLab `font-family: HCS` deb yozadi — bu bizning ichki
    # nomimiz va brauzerda bunday shrift yo'q. Natijada chizmadagi
    # barcha yozuv serifga (Times) tushib qolardi, matn esa saytning
    # o'z shriftida turardi — ikkisi yonma-yon g'alati ko'rinardi.
    svg = svg.replace("font-family: HCS-Qalin", f"font-family: {VEB_SHRIFTI}; font-weight: bold")
    svg = svg.replace("font-family: HCS", f"font-family: {VEB_SHRIFTI}")
    return svg.strip()


def _jadval(t: Table) -> dict[str, Any]:
    qatorlar = [
        [_tozala(k.text) if isinstance(k, Paragraph) else str(k) for k in q]
        for q in t._cellvalues  # noqa: SLF001 — ochiq API yo'q
    ]
    return {"tur": "jadval", "sarlavha": qatorlar[0], "qatorlar": qatorlar[1:]}


def _quti(t: Table) -> dict[str, Any] | None:
    """Bitta katakli jadval — xulosa, savollar yoki real misol qutisi."""
    ichki = t._cellvalues[0][0]  # noqa: SLF001
    if not isinstance(ichki, list):
        return None
    qatorlar = [_tozala(f.text) for f in ichki if isinstance(f, Paragraph)]
    qatorlar = [q for q in qatorlar if q]
    if not qatorlar:
        return None
    bosh = re.sub(r"<[^>]+>", "", qatorlar[0]).strip()
    turi = {
        "XULOSA": "xulosa",
        "O‘ZINGIZNI TEKSHIRING": "savollar",
    }.get(bosh)
    if turi is None and "REAL GRAFIK" in bosh:
        turi = "real_misol"
    if turi is None:
        return None
    return {"tur": turi, "qatorlar": qatorlar[1:]}


def _bloklar(oqim: list) -> list[dict[str, Any]]:
    """Flowable ro'yxatini saytga tushunarli bloklarga aylantiradi."""
    natija: list[dict[str, Any]] = []
    for flow in _yoyilgan(oqim):
        if isinstance(flow, Drawing):
            natija.append({"tur": "chizma", "svg": _svg(flow)})
        elif isinstance(flow, Paragraph):
            turi = USLUB_TURI.get(flow.style.name)
            if turi is None:
                continue
            matn = _tozala(flow.text)
            if matn:
                natija.append({"tur": turi, "matn": matn})
        elif isinstance(flow, Table):
            quti = _quti(flow)
            if quti is not None:
                natija.append(quti)
            elif len(flow._cellvalues) > 1:  # noqa: SLF001
                natija.append(_jadval(flow))
            elif (savol := _savol_qutisi(flow)) is not None:
                natija.append(savol)
    return natija


def _savol_qutisi(t: Table) -> dict[str, Any] | None:
    """Bob boshidagi savol — bitta katakli, ichida bitta xatboshi."""
    ichki = t._cellvalues[0][0]  # noqa: SLF001
    if isinstance(ichki, Paragraph) and ichki.style.name == "savol":
        return {"tur": "savol", "matn": _tozala(ichki.text)}
    return None


def _yoyilgan(oqim: list):  # noqa: ANN202
    """`KeepTogether` ichidagilarni ham chiqaradi."""
    for flow in oqim:
        if isinstance(flow, KeepTogether):
            yield from _yoyilgan(flow._content)  # noqa: SLF001
        else:
            yield flow


def _boblarga_bol(bloklar: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bloklarni boblarga ajratadi — `bob_raqam` yangi bobni boshlaydi."""
    boblar: list[dict[str, Any]] = []
    joriy: dict[str, Any] | None = None
    for blok in bloklar:
        if blok["tur"] == "bob_raqam":
            joriy = {"raqam": blok["matn"], "nom": "", "bloklar": []}
            boblar.append(joriy)
        elif blok["tur"] == "bob_nom" and joriy is not None:
            joriy["nom"] = blok["matn"]
        elif joriy is not None:
            joriy["bloklar"].append(blok)
    return boblar


def eksport(chiqish: Path) -> dict[str, Any]:
    u = uslublar()
    mazmun: dict[str, Any] = {"bolimlar": []}
    for kalit, funksiya in BOLIMLAR:
        boblar = _boblarga_bol(_bloklar(funksiya(u)))
        mazmun["bolimlar"].append({"kalit": kalit, "boblar": boblar})
    chiqish.parent.mkdir(parents=True, exist_ok=True)
    chiqish.write_text(json.dumps(mazmun, ensure_ascii=False, indent=1) + "\n")
    return mazmun


def main() -> None:
    p = argparse.ArgumentParser(description="Kitobni sayt uchun JSON ga chiqaradi")
    p.add_argument("--chiqish", default=str(STANDART_CHIQISH))
    args = p.parse_args()
    yol = Path(args.chiqish)
    mazmun = eksport(yol)
    boblar = sum(len(b["boblar"]) for b in mazmun["bolimlar"])
    olcham = yol.stat().st_size / 1024
    print(f"Tayyor: {yol}  ({len(mazmun['bolimlar'])} bo'lim, {boblar} bob, {olcham:.0f} KB)")


if __name__ == "__main__":
    main()
