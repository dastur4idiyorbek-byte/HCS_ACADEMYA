"""Trend KUCHI — ADX.

EMA OLIB TASHLANDI. Uning ikkita ishi bor edi: trend YO'NALISHINI
aniqlash va uni tasdiqlash. Ikkalasini ham endi SMC strukturasi
bajaradi (`core/analysis/market_structure.py`) — u narxning o'z
qadamlarini (HH/HL/LH/LL) o'qiydi va shuning uchun KECHIKMAYDI.

EMA200 esa 200 shamlik o'rtacha: haftalik timeframeda bu ~3.8 yil
tarix degani va ko'p altcoinlarda bunday tarix umuman yo'q edi.
Ular jimgina "trend aniqlanmadi" toifasiga tushardi
(`docs/ARXITEKTURA.md`, 33- va 58-bo'limlar).

ADX qoladi: u YO'NALISHNI emas, KUCHNI o'lchaydi — struktura javob
bermaydigan savol. Ikkalasi bir-birini almashtirmaydi.

Barcha funksiyalar sof: shamlar ro'yxatini oladi, raqam qaytaradi.
Kutubxona (`pandas-ta`, `TA-Lib`) ishlatilmaydi — sabab `docs/ARXITEKTURA.md`
9-bo'limda.
"""

from __future__ import annotations

from core.analysis.indicators.volatility import true_range
from core.domain.models import Candle


def closes(candles: list[Candle]) -> list[float]:
    return [sham.close for sham in candles]


# --------------------------------------------------------------------------- #
#  ADX — trend KUCHI (yo'nalishi emas)
# --------------------------------------------------------------------------- #


def _wilder_smooth(values: list[float], period: int) -> list[float]:
    """Wilder silliqlash: birinchi qiymat yig'indi, keyin ketma-ket."""
    if len(values) < period:
        return []
    silliq = [sum(values[:period])]
    for qiymat in values[period:]:
        silliq.append(silliq[-1] - silliq[-1] / period + qiymat)
    return silliq


def adx(candles: list[Candle], period: int = 14) -> float | None:
    """Average Directional Index — trend qanchalik kuchli.

    ADX yo'nalishni ko'rsatmaydi, faqat kuchni. Past ADX — tekis (sideways)
    bozor, bunda 4.4-band bo'yicha signal berilmaydi.

    Returns:
        0–100 oralig'idagi qiymat, yoki `None` — ma'lumot yetarli emas.
    """
    if period <= 0:
        raise ValueError("Davr musbat bo'lishi kerak")
    # ADX uchun kamida 2×period sham kerak: DI hisoblash + ADX silliqlash
    if len(candles) < period * 2 + 1:
        return None

    plus_dm: list[float] = []
    minus_dm: list[float] = []
    tr: list[float] = []

    for i in range(1, len(candles)):
        joriy, oldingi = candles[i], candles[i - 1]
        yuqoriga = joriy.high - oldingi.high
        pastga = oldingi.low - joriy.low

        plus_dm.append(yuqoriga if yuqoriga > pastga and yuqoriga > 0 else 0.0)
        minus_dm.append(pastga if pastga > yuqoriga and pastga > 0 else 0.0)
        tr.append(true_range(joriy, oldingi))

    silliq_tr = _wilder_smooth(tr, period)
    silliq_plus = _wilder_smooth(plus_dm, period)
    silliq_minus = _wilder_smooth(minus_dm, period)

    if not silliq_tr:
        return None

    dx_qatori: list[float] = []
    for tr_q, plus_q, minus_q in zip(silliq_tr, silliq_plus, silliq_minus, strict=True):
        if tr_q <= 0:
            dx_qatori.append(0.0)
            continue
        plus_di = 100 * plus_q / tr_q
        minus_di = 100 * minus_q / tr_q
        yigindi = plus_di + minus_di
        dx_qatori.append(0.0 if yigindi <= 0 else 100 * abs(plus_di - minus_di) / yigindi)

    if len(dx_qatori) < period:
        return None

    qiymat = sum(dx_qatori[:period]) / period
    for dx in dx_qatori[period:]:
        qiymat = (qiymat * (period - 1) + dx) / period
    return qiymat


