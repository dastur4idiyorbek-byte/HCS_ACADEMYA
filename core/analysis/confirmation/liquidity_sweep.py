"""4.1 — Liquidity Sweep.

TA'RIF (2-prompt): narx oldingi swing nuqtadan config qilingan %
o'tib, N sham ichida QAYTIB KIRGAN.

MA'NOSI: swing past ostida stop-loss buyurtmalari to'planadi. Katta
o'yinchi narxni o'sha yerga tushirib, stoplarni "yalab" oladi va
keyin yuqoriga qaytaradi. Bu — kirish uchun eng kuchli belgilardan
biri, chunki likvidlik allaqachon olib bo'lingan.

IKKI SHART BIRGA: faqat "o'tdi" — bu oddiy tushish, zona buzilgan.
Faqat "qaytdi" — hech narsa bo'lmagan. Ikkalasi birga — sweep.
"""

from __future__ import annotations

from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.domain.models import Candle

#: Swingdan shu foizdan ko'p o'tishi kerak — shovqinni kesish uchun.
#: 🔴 O'LCHANMAGAN. Promptda 0.1-0.5% oralig'i berilgan.
SWEEP_ENG_KAM_PCT = 0.1

#: Shuncha sham ichida qaytib kirishi kerak.
#: 🔴 O'LCHANMAGAN.
SWEEP_QAYTISH_SHAM = 3


def sweep_bormi(
    shamlar: list[Candle],
    nuqtalar: list[Swing],
    eng_kam_pct: float = SWEEP_ENG_KAM_PCT,
    qaytish_sham: int = SWEEP_QAYTISH_SHAM,
) -> bool:
    """Oxirgi swing PAST yalanganmi va narx qaytganmi."""
    past = None
    for s in reversed(nuqtalar):
        if s.turi is SwingTuri.PAST:
            past = s
            break
    if past is None:
        return False

    chegara = past.narx * (1 - eng_kam_pct / 100)

    for i in range(past.indeks + 1, len(shamlar)):
        if shamlar[i].low > chegara:
            continue
        # Yalash topildi — endi N sham ichida qaytish tekshiriladi
        oyna = shamlar[i : i + qaytish_sham + 1]
        if any(sham.close > past.narx for sham in oyna):
            return True
    return False
