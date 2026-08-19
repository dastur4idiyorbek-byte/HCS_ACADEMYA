"""Tahlil qatlami ("miya"ning asosiy qismi).

Modullar tartibi 3.1-bandga mos — S/R BIRLAMCHI, indikatorlar tasdiqlovchi:

    support_resistance/  — S/R zonalarini aniqlash (BIRINCHI, markaziy)
    indicators/          — EMA, RSI, MACD, hajm (TASDIQLOVCHI, mustaqil emas)
    scoring/             — ball hisoblash va reytinglash
    market_health/       — Bozor Salomatligi Indeksi (3.7)
    postmortem/          — Signal Xotirasi, o'z-o'zini tekshiruv (3.8)
    strategies/          — plug-in strategiyalar (6.1)

Qo'shimcha:
    entry_order.py       — kirish buyurtmasi turi (LIMIT/MARKET, 5.1.0-band)
"""

from core.analysis.entry_order import decide_entry_plan

__all__ = ["decide_entry_plan"]
