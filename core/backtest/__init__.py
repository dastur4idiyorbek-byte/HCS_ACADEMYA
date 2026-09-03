"""6.3-band: backtest freymvorki — tarixiy ma'lumotda sinash vositasi.

Spetsifikatsiya buni MAJBURIY deb belgilaydi: "jonli pulga qo'yishdan
oldin kamida 1-2 yillik tarixiy ma'lumotda sinash".

2026-09-03 — eski tahlil moduli olib tashlandi. U bilan birga siklni
qayta o'ynatuvchi `engine.py`, natijani chizuvchi `report.py` (eski
voronka bosqichlariga bog'langan) va `warmup.py` (eski indikator
sozlamalariga bog'langan) ham ketdi. QOLGANI — strategiyadan MUSTAQIL
freymvork:

    dataset.py  — tarixiy ma'lumot va LOOKAHEADSIZ vaqt kesimi
    yuklash.py  — shamlarni yuklash va oynaga bog'langan kesh

LOOKAHEAD HIMOYASI: `Dataset` sham ro'yxatini to'g'ridan-to'g'ri
bermaydi. Har bir so'rov vaqt chegarasi bilan keladi va faqat o'sha
paytgacha ochilgan shamlar qaytariladi. "Kelajakka qarash" —
backtestning eng keng tarqalgan va eng qimmat xatosi.
"""

from core.backtest.dataset import (
    TIMEFRAME_MINUTES,
    Dataset,
    SymbolSeries,
    aggregate,
    build_dataset,
)
from core.backtest.yuklash import KeshYetishmaydi, keshdan_yigish, yukla

__all__ = [
    "TIMEFRAME_MINUTES",
    "Dataset",
    "KeshYetishmaydi",
    "SymbolSeries",
    "aggregate",
    "build_dataset",
    "keshdan_yigish",
    "yukla",
]
