"""Logotipdan ranglarni PIKSEL DARAJASIDA o'qib chiqaradi.

Nima uchun bu skript kerak: dizayn ranglari "ko'zga chiroyli" deb
TAXMIN QILINMAGAN — ular `public/logo.jpg` faylidan aniq koordinatalar
bo'yicha o'lchangan. Logotip o'zgarsa, shu skript qayta ishga tushiriladi
va `src/app/globals.css` dagi qiymatlar yangilanadi. Aks holda ranglar
vaqt o'tishi bilan asl logotipdan "sudralib" ketadi.

Ishga tushirish:
    python3 scripts/logo_ranglari.py

Talab: Pillow (`pip install Pillow`). Bu skript qurilish (build)
jarayonining qismi EMAS — u faqat qo'lda tekshirish uchun.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover — faqat qo'lda ishlatiladi
    sys.exit("Pillow o'rnatilmagan: pip install Pillow")

LOGO = Path(__file__).resolve().parent.parent / "public" / "logo.jpg"

#: (nom, x, y) — 640x640 logotipdagi aniq nuqtalar.
#: Har biri 9x9 kvadratning MEDIANASI olinadi: JPEG siqilishi bitta
#: pikselni buzishi mumkin, mediana esa bunga chidamli.
NUQTALAR: list[tuple[str, int, int]] = [
    ("H turkuaz (ustun)", 210, 300),
    ("H turkuaz (ko'ndalang, ochroq)", 270, 318),
    ("C apelsin (yoy)", 420, 185),
    ("S ko'k (yoy)", 440, 370),
    ("S ko'k to'q (past-chap shakl)", 55, 590),
    ("Sariq (tepa-o'ng shakl)", 600, 25),
    ("Fon (oq-kulrang)", 560, 120),
]


def mediana(im: Image.Image, cx: int, cy: int, r: int = 4) -> tuple[int, int, int]:
    piksellar = [
        im.getpixel((x, y))
        for x in range(cx - r, cx + r + 1)
        for y in range(cy - r, cy + r + 1)
    ]
    return tuple(sorted(p[i] for p in piksellar)[len(piksellar) // 2] for i in range(3))


def hex_kod(rang: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rang)


def main() -> None:
    im = Image.open(LOGO).convert("RGB")
    if im.size != (640, 640):
        print(f"OGOHLANTIRISH: logotip {im.size}, koordinatalar 640x640 uchun.")
    kenglik = max(len(nom) for nom, _, _ in NUQTALAR)
    for nom, x, y in NUQTALAR:
        rang = mediana(im, x, y)
        print(f"{nom:<{kenglik}}  ({x:3},{y:3})  {hex_kod(rang)}  rgb{rang}")


if __name__ == "__main__":
    main()
