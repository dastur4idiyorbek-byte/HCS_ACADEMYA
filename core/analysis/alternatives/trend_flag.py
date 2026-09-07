"""2A — Trend chizig'i + Flag naqshi.

Struktura bloki ZAIF bo'lganda (1/4) birinchi alternativ.

QOIDA. Ko'tarilish: oxirgi ikki swing PAST yuqoriga qarab ketgan
(higher low) va narx shu trend chizig'idan yuqorida ushlanib turgan
bo'lsa — ✅.

FLAG. Qutb (keskin ko'tarilish) dan keyin narx yangi cho'qqi
qilmasdan tor oraliqda konsolidatsiya qiladi. Bu yerda soddalashtirilgan
shakli olinadi: oxirgi swing yuqori qutb hisoblanadi, undan keyin narx
qutbdan yuqoriga chiqmagan bo'lsa — flag bor deb qaraladi.
"""

from __future__ import annotations

from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.domain.models import Candle

#: Narx trend chizig'idan shu foizgacha pastda bo'lsa ham "ustida" deb qaraladi.
#: 🔴 O'LCHANMAGAN.
TREND_TOLERANS_PCT = 1.0


def trend_chizigi_qiymati(a: Swing, b: Swing, indeks: int) -> float | None:
    """Ikki swing PAST orqali o'tgan chiziqning `indeks` dagi qiymati."""
    if b.indeks == a.indeks:
        return None
    qiyalik = (b.narx - a.narx) / (b.indeks - a.indeks)
    return a.narx + qiyalik * (indeks - a.indeks)


def trend_flag(shamlar: list[Candle], nuqtalar: list[Swing]) -> bool:
    """HL trend + narx trend chizig'i ustida + qutbdan keyin flag."""
    pastlar = [s for s in nuqtalar if s.turi is SwingTuri.PAST]
    if len(pastlar) < 2 or len(shamlar) < 3:
        return False

    a, b = pastlar[-2], pastlar[-1]
    if b.narx <= a.narx:
        return False  # higher low kerak

    oxirgi_indeks = len(shamlar) - 1
    chiziq = trend_chizigi_qiymati(a, b, oxirgi_indeks)
    if chiziq is None:
        return False
    if shamlar[-1].close < chiziq * (1 - TREND_TOLERANS_PCT / 100):
        return False

    # Flag: qutb (oxirgi swing yuqori) dan keyin narx undan yuqoriga chiqmagan
    yuqorilar = [s for s in nuqtalar if s.turi is SwingTuri.YUQORI]
    if yuqorilar:
        qutb = yuqorilar[-1]
        keyingilar = shamlar[qutb.indeks + 1 :]
        if any(sham.high > qutb.narx for sham in keyingilar):
            return False  # yangi cho'qqi — flag emas, davom etgan trend

    return True
