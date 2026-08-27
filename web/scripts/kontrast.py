"""Rang juftliklarining WCAG kontrastini `globals.css` DAN o'qib tekshiradi.

Nima uchun bu skript kerak: kontrast raqamlarini hujjatga qo'lda yozib
qo'yish — eng tez eskiradigan narsa. Kimdir rangni bir oz o'zgartirsa,
hujjatdagi "4.66 : 1" o'z-o'zidan noto'g'ri bo'lib qoladi va buni hech
kim sezmaydi. Shuning uchun qiymatlar CSS faylining O'ZIDAN o'qiladi.

Ishga tushirish:
    python3 scripts/kontrast.py      # 0 — hammasi joyida, 1 — muammo bor
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "src" / "app" / "globals.css"

#: (matn o'zgaruvchisi, fon o'zgaruvchisi, minimal nisbat, izoh)
#: 4.5 — oddiy matn uchun WCAG AA; 3.0 — interfeys elementi (chiziq, ramka).
TEKSHIRUVLAR: list[tuple[str, str, float, str]] = [
    ("--rang-sarlavha", "--rang-panel", 4.5, "sarlavha kartochkada"),
    ("--rang-matn", "--rang-panel", 4.5, "asosiy matn kartochkada"),
    ("--rang-matn-past", "--rang-panel", 4.5, "ikkinchi darajali matn kartochkada"),
    ("--rang-ramka", "--rang-panel", 3.0, "ramka chizig'i kartochkada"),
    ("--rang-sarlavha", "--rang-fon", 4.5, "sarlavha sahifada"),
    ("--rang-matn", "--rang-fon", 4.5, "asosiy matn sahifada"),
    ("--rang-matn-past", "--rang-fon", 4.5, "ikkinchi darajali matn sahifada"),
    # Yorliqlar (Badge) sahifaning to'q ko'kida chiziladi, kartochkada emas
    ("--rang-yaxshi", "--rang-fon", 4.5, "yaxshi holat yorlig'i"),
    ("--rang-ortacha", "--rang-fon", 4.5, "o'rtacha holat yorlig'i"),
    ("--rang-past", "--rang-fon", 4.5, "past holat yorlig'i"),
]


def ranglarni_oq(css: str) -> dict[str, str]:
    """`--nom: #hex;` va `--nom: var(--boshqa);` zanjirini yechadi."""
    xom = dict(re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", css))
    yechilgan: dict[str, str] = {}

    def yech(nom: str, chuqurlik: int = 0) -> str | None:
        if chuqurlik > 8 or nom not in xom:
            return None
        qiymat = xom[nom].strip()
        if qiymat.startswith("#"):
            return qiymat
        moslik = re.fullmatch(r"var\((--[a-z0-9-]+)\)", qiymat)
        return yech(moslik.group(1), chuqurlik + 1) if moslik else None

    for nom in xom:
        hex_kod = yech(nom)
        if hex_kod:
            yechilgan[nom] = hex_kod
    return yechilgan


def yorqinlik(hex_kod: str) -> float:
    h = hex_kod.lstrip("#")
    kanallar = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        kanallar.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = kanallar
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def nisbat(a: str, b: str) -> float:
    la, lb = yorqinlik(a), yorqinlik(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def main() -> int:
    ranglar = ranglarni_oq(CSS.read_text(encoding="utf-8"))
    xato = 0
    for matn, fon, kerak, izoh in TEKSHIRUVLAR:
        if matn not in ranglar or fon not in ranglar:
            print(f"XATO  {izoh}: o'zgaruvchi topilmadi ({matn} yoki {fon})")
            xato += 1
            continue
        r = nisbat(ranglar[matn], ranglar[fon])
        belgi = "OK  " if r >= kerak else "XATO"
        if r < kerak:
            xato += 1
        print(f"{belgi}  {izoh:38} {r:5.2f} : 1  (kerak {kerak})")
    if xato:
        print(f"\n{xato} ta juftlik talabdan past — rangni ochroq qiling.")
    return 1 if xato else 0


if __name__ == "__main__":
    sys.exit(main())
