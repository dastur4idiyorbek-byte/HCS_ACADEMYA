"""6.3-band: backtest — tarixiy ma'lumotda strategiyani sinash.

Spetsifikatsiya buni MAJBURIY deb belgilaydi: "jonli pulga qo'yishdan
oldin kamida 1-2 yillik tarixiy ma'lumotda sinash".

ASOSIY QARORI: backtest jonli tizim bilan BIR XIL kodni ishlatadi —
`SignalCycle` va `SignalTracker` o'zgarishsiz. Agar backtest o'z nusxasini
ishlatganda, ikki xil kod ikki xil natija berardi va sinovning ma'nosi
qolmasdi.

LOOKAHEAD HIMOYASI: `Dataset` sham ro'yxatini to'g'ridan-to'g'ri bermaydi.
Har bir so'rov vaqt chegarasi bilan keladi va faqat o'sha paytgacha
ochilgan shamlar qaytariladi. "Kelajakka qarash" — backtestning eng keng
tarqalgan va eng qimmat xatosi.

    dataset.py  — tarixiy ma'lumot va vaqt kesimi
    engine.py   — siklni qayta o'ynatish
    report.py   — natija va konfiguratsiyalarni taqqoslash
"""

from core.backtest.dataset import (
    TIMEFRAME_MINUTES,
    Dataset,
    SymbolSeries,
    aggregate,
    build_dataset,
)
from core.backtest.engine import Backtester, BacktestResult, BacktestTrade
from core.backtest.report import MIN_TRADES_FOR_CONCLUSION, compare, render

__all__ = [
    "MIN_TRADES_FOR_CONCLUSION",
    "BacktestResult",
    "BacktestTrade",
    "Backtester",
    "TIMEFRAME_MINUTES",
    "Dataset",
    "SymbolSeries",
    "aggregate",
    "build_dataset",
    "compare",
    "render",
]
