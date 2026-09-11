"""Kitobni yig'adi va PDF ga chiqaradi.

Ishlatish:
    python -m scripts.kitob.qur                  # hamma tayyor bo'limlar
    python -m scripts.kitob.qur --chiqish yo'l   # boshqa faylga

NEGA IKKI MARTA QURILADI. Mundarija sahifa raqamlarini BIRINCHI
yugurishda yig'adi va faqat IKKINCHISIDA to'g'ri chop etadi
(`multiBuild` shuni o'zi qiladi).
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from scripts.kitob.bolim1 import bolim1
from scripts.kitob.bolim2 import bolim2
from scripts.kitob.bolim3 import bolim3
from scripts.kitob.bolim4 import bolim4
from scripts.kitob.bolim5 import bolim5
from scripts.kitob.bolim6 import bolim6
from scripts.kitob.kirish import kirish
from scripts.kitob.qolip import Kitob, mundarija, muqova
from scripts.kitob.uslub import ILDIZ, uslublar
from scripts.kitob.yakun import yakun

#: Tayyor bo'limlar — 7-promptning 3-qismi bo'yicha birma-bir qo'shiladi.
BOLIMLAR = (bolim1, bolim2, bolim3, bolim4, bolim5, bolim6)

FAYL_NOMI = "HCS_Academy_Noldan_kripto_savdogariga.pdf"
STANDART_CHIQISH = ILDIZ / "docs" / "kitob" / FAYL_NOMI

#: Sayt PDF ni SHU yerdan beradi (`web/src/app/api/kitob/route.ts`).
#:
#: NEGA NUSXA OLINADI. `docs/kitob/*.pdf` — `.gitignore` da: har
#: qurishda o'zgaradigan binar fayl git tarixini shishiradi. Lekin
#: Railway da reportlab yo'q, shuning uchun saytdagi nusxa git ga
#: KIRITILADI. Ilgari nusxa QO'LDA ko'chirilardi va bir marta
#: eskirib qoldi: docs dagi yangi, saytdagi eski edi — hech kim
#: sezmadi. Endi bitta buyruq ikkalasini ham yangilaydi.
VEB_NUSXA = ILDIZ / "web" / "kitob" / FAYL_NOMI


def qur(chiqish: Path) -> tuple[int, Path]:
    """PDF yasaydi. Qaytaradi: (sahifa soni, yo'l)."""
    chiqish.parent.mkdir(parents=True, exist_ok=True)
    u = uslublar()

    hikoya: list = []
    hikoya += muqova(u)  # oxirida o'zi oddiy qolipga o'tadi
    hikoya += mundarija(u)
    hikoya += kirish(u)
    for bolim in BOLIMLAR:
        hikoya += bolim(u)
    hikoya += yakun(u)

    hujjat = Kitob(str(chiqish))
    hujjat.multiBuild(hikoya)

    from pypdf import PdfReader

    return len(PdfReader(str(chiqish)).pages), chiqish


def main() -> None:
    p = argparse.ArgumentParser(description="HCS Academy kitobini quradi")
    p.add_argument("--chiqish", default=str(STANDART_CHIQISH))
    p.add_argument(
        "--veb-nusxasiz",
        action="store_true",
        help="saytdagi nusxa (web/kitob/) yangilanmasin",
    )
    args = p.parse_args()
    sahifalar, yol = qur(Path(args.chiqish))
    print(f"Tayyor: {yol}  ({sahifalar} sahifa)")
    if not args.veb_nusxasiz and yol.resolve() != VEB_NUSXA.resolve():
        VEB_NUSXA.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(yol, VEB_NUSXA)
        print(f"Sayt nusxasi: {VEB_NUSXA}")


if __name__ == "__main__":
    main()
