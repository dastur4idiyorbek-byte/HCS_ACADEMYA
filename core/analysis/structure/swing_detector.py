"""2.1 — Swing nuqtalar: 5 shamli fraktal va HH/HL/LH/LL ketma-ketligi.

FRAKTAL TA'RIFI (2-prompt, 4-qism): 2 chap + 1 o'rta + 2 o'ng.
O'rta shamning `high` i to'rt qo'shnisidan baland bo'lsa — Swing High.
`low` i to'rttasidan past bo'lsa — Swing Low.

NIMA UCHUN 5 SHAM, 3 EMAS: 3 shamli fraktal har bir kichik
tebranishni "swing" deb belgilaydi va struktura shovqinga to'ladi.
5 sham — ICT/SMC amaliyotidagi standart, va u tasdiqlanishi uchun
o'ngdan 2 sham YOPILISHI kerak — ya'ni oxirgi 2 sham hech qachon
swing bo'la olmaydi. Bu KECHIKISH emas, LOOKAHEAD HIMOYASI: aks
holda hali shakllanmagan cho'qqini "swing" deb o'qir edik.

SHUBHALI SHAM. `price_reconciliation.py` belgilagan vaqtlar swing
nuqta sifatida QABUL QILINMAYDI — bitta birjaning yolg'on wicki
strukturani buzmasin (2-prompt, 2-qism).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.domain.models import Candle

#: Fraktal yarim kengligi: 2 chap + 2 o'ng
FRAKTAL_QANOT = 2


class SwingTuri(str, Enum):
    YUQORI = "yuqori"
    PAST = "past"


@dataclass(frozen=True, slots=True)
class Swing:
    turi: SwingTuri
    narx: float
    vaqt: datetime
    #: Sham indeksi — BOS/CHOCH hisoblashda tartib uchun kerak
    indeks: int


def swinglar(
    shamlar: list[Candle],
    qanot: int = FRAKTAL_QANOT,
    shubhali: set[datetime] | None = None,
) -> list[Swing]:
    """Barcha swing nuqtalarni vaqt tartibida qaytaradi.

    Args:
        shamlar: eng eskisidan eng yangisiga
        qanot: fraktal yarim kengligi (standart 2)
        shubhali: `price_reconciliation` belgilagan vaqtlar — rad etiladi
    """
    rad = shubhali or set()
    natija: list[Swing] = []

    for i in range(qanot, len(shamlar) - qanot):
        sham = shamlar[i]
        if sham.open_time in rad:
            continue
        chap = shamlar[i - qanot : i]
        ong = shamlar[i + 1 : i + 1 + qanot]
        qoshnilar = chap + ong

        if all(sham.high > q.high for q in qoshnilar):
            natija.append(Swing(SwingTuri.YUQORI, sham.high, sham.open_time, i))
        elif all(sham.low < q.low for q in qoshnilar):
            natija.append(Swing(SwingTuri.PAST, sham.low, sham.open_time, i))

    return natija


def ketma_ketlik_kotarilish(nuqtalar: list[Swing]) -> bool:
    """HH/HL ketma-ketligi bormi — ko'tarilish strukturasi.

    Oxirgi IKKI yuqori va IKKI past nuqta olinadi:
        yuqori[-1] > yuqori[-2]  (Higher High)
        past[-1]   > past[-2]    (Higher Low)

    IKKALASI HAM shart. Faqat HH bo'lsa — narx yangi cho'qqi qildi,
    lekin pastki nuqta ham tushgan bo'lishi mumkin (kengayuvchi
    diapazon), bu ko'tarilish emas.
    """
    yuqorilar = [s.narx for s in nuqtalar if s.turi is SwingTuri.YUQORI]
    pastlar = [s.narx for s in nuqtalar if s.turi is SwingTuri.PAST]
    if len(yuqorilar) < 2 or len(pastlar) < 2:
        return False
    return yuqorilar[-1] > yuqorilar[-2] and pastlar[-1] > pastlar[-2]


def oxirgi(nuqtalar: list[Swing], turi: SwingTuri) -> Swing | None:
    """Berilgan turdagi eng so'nggi swing."""
    for s in reversed(nuqtalar):
        if s.turi is turi:
            return s
    return None
