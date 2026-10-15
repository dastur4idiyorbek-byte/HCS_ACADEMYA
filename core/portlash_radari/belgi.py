"""Binance futures symbolidan asl coin belgisini ajratish.

NIMA UCHUN KERAK. Binance juda arzon coinlarni ko'paytirgich bilan
sotadi: `1000PEPEUSDT` — 1000 ta PEPE narxi. Halol reestr va
CoinGecko esa `PEPE` ni biladi. Belgi to'g'ri ajratilmasa, reestr
coinni "baholanmagan" deb ko'rsatardi va kapitalizatsiya topilmasdi.

FAQAT MA'LUM KO'PAYTIRGICHLAR. "1" bilan boshlangan har nomni
kesib tashlash xato: `1INCH` — coinning o'z nomi. Shuning uchun
faqat Binance haqiqatan ishlatadigan uchta prefiks taniladi.

Foiz hisobiga ko'paytirgich ta'sir qilmaydi: 1000 ta PEPE ham, bitta
PEPE ham bir xil foizga o'sadi.
"""

from __future__ import annotations

import re

#: Binance ishlatadigan ko'paytirgichlar. Uzunroq prefiks OLDIN
#: tekshiriladi: `1000000MOG` ni `1000` deb kesib `000MOG` qoldirmaslik uchun.
KOPAYTIRGICHLAR: tuple[tuple[str, int], ...] = (
    ("1000000", 1_000_000),
    ("1000", 1_000),
    ("1M", 1_000_000),
)

#: Prefiksdan keyin HARF kelishi shart — aks holda bu coinning o'z
#: raqamli nomi (masalan `1000` dan keyin raqam).
_HARF = re.compile(r"[A-Z]")

#: Saytda yashirish uchun kiritiladigan symbol: faqat katta harf va raqam.
_SYMBOL = re.compile(r"^[A-Z0-9]{2,30}USDT$")

KOTIROVKA = "USDT"


def ajrat(asosiy: str) -> tuple[str, int]:
    """`1000PEPE` -> (`PEPE`, 1000). Ko'paytirgichsiz nom o'zgarmaydi."""
    nom = asosiy.strip().upper()
    for prefiks, kopaytirgich in KOPAYTIRGICHLAR:
        if nom.startswith(prefiks):
            qoldiq = nom[len(prefiks) :]
            if qoldiq and _HARF.match(qoldiq):
                return qoldiq, kopaytirgich
    return nom, 1


def asl_belgi(asosiy: str) -> str:
    """Reestr va CoinGecko uchun belgi."""
    return ajrat(asosiy)[0]


def symboldan_asosiy(symbol: str) -> str:
    """`LSKUSDT` -> `LSK`. Kotirovka bilan tugamasa — o'zi."""
    upper = symbol.strip().upper()
    return upper[: -len(KOTIROVKA)] if upper.endswith(KOTIROVKA) else upper


def stablecoinmi(belgi: str, stablecoinlar: set[str] | frozenset[str]) -> bool:
    return belgi.upper() in stablecoinlar


def binance_symbol(kiritilgan: str) -> str | None:
    """Admin kiritgan matndan Binance symbol (`lsk` -> `LSKUSDT`).

    Yaroqsiz bo'lsa `None` — bazaga xom matn yozilmaydi.
    """
    nom = re.sub(r"\s+", "", kiritilgan).upper()
    if not nom.endswith(KOTIROVKA):
        nom += KOTIROVKA
    return nom if _SYMBOL.match(nom) else None
