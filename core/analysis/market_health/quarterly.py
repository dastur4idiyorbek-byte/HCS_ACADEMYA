"""QT — Quarterly Theory (AMDX), CryptoSpot3% metodikasining 5-qismi.

Katta vaqt oralig'i to'rtga bo'linadi:

    A  Accumulation   — yig'ish, tor diapazon
    M  Manipulation   — yolg'on harakat, likvidlik yig'ib olinadi
    D  Distribution   — asosiy harakat
    X  Continuation   — tasdiqlanish va davom etish

Sutkalik oyna UTC bo'yicha to'rt olti soatlik chorakka bo'linadi.
Kripto 24/7 ishlaydi, ya'ni forexdagi kabi qat'iy "sessiya ochilishi"
yo'q — lekin savdo hajmi haqiqatan Osiyo / London / Nyu-York
soatlarida farqlanadi.

OCHIQ AYTILADIGAN CHEKLOV
-------------------------
Chorak -> ball moslashuvi (`QuarterPhase.score`) SOAT bo'yicha, ya'ni
u bozor holatidan QAT'I NAZAR har kuni bir xil ritmda o'zgaradi.
Bu — o'lchanmagan taxmin, shuning uchun:

  * uning Bozor Salomatligi Indeksidagi vazni ATAYLAB kichik (5);
  * qiymatlar BOSHLANG'ICH va backtest bilan tasdiqlanishi kerak.

Loyihada haddan tashqari vazn berilgan, lekin bashorat kuchi
o'lchanmagan ko'rsatkich allaqachon zarar keltirgan (BTC Dominance —
`docs/ARXITEKTURA.md`, 33- va 57-bo'limlar). Shu xato takrorlanmasin.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

#: Sutka nechta chorakka bo'linadi (AMDX -> to'rtta)
QUARTERS = 4
HOURS_PER_QUARTER = 24 // QUARTERS


class QuarterPhase(str, Enum):
    """AMDX davri."""

    ACCUMULATION = "A"
    MANIPULATION = "M"
    DISTRIBUTION = "D"
    CONTINUATION = "X"

    @property
    def score(self) -> float:
        """Davr uchun ball ulushi (0..1) — BOSHLANG'ICH qiymatlar.

        Mantiq: X (tasdiqlanish) — eng ishonchli davr, M (manipulyatsiya)
        — eng xavflisi, chunki aynan o'sha yerda yolg'on harakatlar
        bo'ladi. A va D orasida.
        """
        return {"A": 0.75, "M": 0.25, "D": 0.5, "X": 1.0}[self.value]

    @property
    def label(self) -> str:
        return {
            "A": "A (Accumulation) — yig'ish davri",
            "M": "M (Manipulation) — yolg'on harakat davri",
            "D": "D (Distribution) — asosiy harakat davri",
            "X": "X (Continuation) — tasdiqlanish va davom etish",
        }[self.value]

    @property
    def next_phase(self) -> QuarterPhase:
        tartib = list(QuarterPhase)
        return tartib[(tartib.index(self) + 1) % QUARTERS]


def quarterly_phase(moment: datetime) -> QuarterPhase:
    """Berilgan UTC vaqti sutkaning qaysi choragida.

    Vaqt mintaqasi belgilanmagan `datetime` UTC deb qabul qilinadi:
    tizimda barcha vaqtlar UTC da saqlanadi (`core/utils/time.py`).
    """
    chorak = min(QUARTERS - 1, moment.hour // HOURS_PER_QUARTER)
    return list(QuarterPhase)[chorak]


def describe_phase(moment: datetime) -> str:
    """Saytdagi shkala ostida ko'rsatiladigan bir qatorli matn."""
    davr = quarterly_phase(moment)
    return f"{davr.label}; keyingisi — {davr.next_phase.value}"
