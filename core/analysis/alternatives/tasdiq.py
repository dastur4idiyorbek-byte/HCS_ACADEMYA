"""4A / 4B / 4C — Tasdiqlash blokining alternativ yo'llari.

   4A Hajm sakrashi  — oxirgi sham hajmi o'rtachadan sezilarli yuqori
   4B Tez harakat    — oxirgi sham diapazoni o'rtachadan sezilarli keng
   4C Qayta sinov    — buzilgan darajaga qaytib, ushlab turish (retest)

Uchovi ham SOF SHAMDAN hisoblanadi — backtestda to'liq o'lchanadi.
"""

from __future__ import annotations

from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.domain.models import Candle

#: Hajm o'rtachadan shu koeffitsientdan ko'p oshsa — spike.
#: 🔴 O'LCHANMAGAN.
HAJM_KOEFF = 2.0
HAJM_DAVR = 20

#: Tez harakat: oxirgi sham diapazoni o'rtachadan shu koeffitsientdan ko'p.
#: 🔴 O'LCHANMAGAN.
TEZ_KOEFF = 1.5
TEZ_DAVR = 10

#: Retest: buzilgan darajaga qaytishda shu foiz tolerantlik ichida.
#: 🔴 O'LCHANMAGAN.
RETEST_TOLERANS_PCT = 0.5


def hajm_sakrashi(
    shamlar: list[Candle],
    davr: int = HAJM_DAVR,
    koeff: float = HAJM_KOEFF,
) -> bool:
    """Oxirgi sham hajmi oldingi `davr` sham o'rtachasidan `koeff` ko'pmi."""
    if len(shamlar) < davr + 1:
        return False
    ortacha = sum(s.volume for s in shamlar[-davr - 1 : -1]) / davr
    if ortacha <= 0:
        return False
    return shamlar[-1].volume >= ortacha * koeff


def tez_harakat(
    shamlar: list[Candle],
    davr: int = TEZ_DAVR,
    koeff: float = TEZ_KOEFF,
) -> bool:
    """Oxirgi sham diapazoni oldingi `davr` sham o'rtachasidan `koeff` kengmi."""
    if len(shamlar) < davr + 1:
        return False
    ortacha = sum(s.range for s in shamlar[-davr - 1 : -1]) / davr
    if ortacha <= 0:
        return False
    return shamlar[-1].range >= ortacha * koeff


def qayta_sinov(
    shamlar: list[Candle],
    nuqtalar: list[Swing],
    tolerantlik_pct: float = RETEST_TOLERANS_PCT,
) -> bool:
    """Buzilgan swing yuqori darajaga qaytib, narx ushlab turildimi.

    Uch shart KETMA-KET:

      1. Oxirgi swing YUQORI topiladi (qarshilik darajasi).
      2. U keyin YOPILISH bilan buzilgan (BOS).
      3. Narx darajaga qaytib kelgan va hozir ham uning ostiga
         yopilmagan (qo'llab-quvvatlashga aylandi).
    """
    for s in reversed(nuqtalar):
        if s.turi is not SwingTuri.YUQORI:
            continue
        daraja = s.narx
        keyingilar = shamlar[s.indeks + 1 :]
        if len(keyingilar) < 2:
            return False

        buzildi = any(sham.close > daraja for sham in keyingilar)
        if not buzildi:
            return False

        chegara = daraja * (1 - tolerantlik_pct / 100)
        qaytdi = any(sham.low <= daraja for sham in keyingilar)
        ushlandi = shamlar[-1].close >= chegara
        return qaytdi and ushlandi
    return False
