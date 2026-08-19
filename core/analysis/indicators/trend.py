"""Trend indikatorlari — EMA va ADX.

3.1-band: bular S/R zonasini TASDIQLOVCHI omillar, mustaqil signal manbai
EMAS. "EMA50 EMA200 dan yuqori" — o'zi signal emas; u faqat "narx muhim
S/R zonasida" degan holat aniqlangandan keyin ma'noga ega bo'ladi.

Barcha funksiyalar sof: shamlar ro'yxatini oladi, raqam qaytaradi.
Kutubxona (`pandas-ta`, `TA-Lib`) ishlatilmaydi — sabab `docs/ARXITEKTURA.md`
9-bo'limda.
"""

from __future__ import annotations

from core.analysis.indicators.volatility import true_range
from core.domain.enums import TrendDirection
from core.domain.models import Candle


def ema_series(values: list[float], period: int) -> list[float | None]:
    """Eksponensial siljuvchi o'rtacha, har bir nuqta uchun.

    Dastlabki qiymat — birinchi `period` ta qiymatning oddiy o'rtachasi
    (SMA). Bu — standart yondashuv: EMA'ni birinchi qiymatdan boshlash
    uzoq vaqt davomida noto'g'ri natija berardi.

    Yetarli ma'lumot bo'lmagan nuqtalarda `None` qaytadi — bu jimgina nol
    qaytarishdan xavfsizroq.
    """
    if period <= 0:
        raise ValueError("Davr musbat bo'lishi kerak")
    if len(values) < period:
        return [None] * len(values)

    koeffitsient = 2 / (period + 1)
    natija: list[float | None] = [None] * (period - 1)

    joriy = sum(values[:period]) / period
    natija.append(joriy)

    for qiymat in values[period:]:
        joriy = (qiymat - joriy) * koeffitsient + joriy
        natija.append(joriy)

    return natija


def ema(values: list[float], period: int) -> float | None:
    """Oxirgi EMA qiymati."""
    qator = ema_series(values, period)
    return qator[-1] if qator else None


def closes(candles: list[Candle]) -> list[float]:
    return [sham.close for sham in candles]


def trend_direction(
    price: float,
    ema_fast: float | None,
    ema_slow: float | None,
    require_price_above_fast: bool = True,
) -> TrendDirection:
    """3.1-band: long faqat narx EMA'lardan yuqori VA EMA50 > EMA200 bo'lsa.

    Args:
        require_price_above_fast: `True` (standart, spetsifikatsiya bo'yicha) —
            narx IKKALA EMA'dan yuqori bo'lishi shart. `False` — trend
            tuzilishi EMA50 > EMA200 va narx > EMA200 bilan aniqlanadi.

            Nima uchun bu sozlanadi: support zonasiga qaytish (pullback)
            deyarli har doim narxni EMA50 dan pastga tushiradi — aks holda u
            support'ga yetib bormaydi. Qat'iy talab bilan "arzon joydan
            kirish" imkoniyati juda kamayadi. Qaysi variant foydaliroq —
            16-bosqichdagi backtest ko'rsatadi.

    Ma'lumot yetishmasa `FLAT` qaytadi — noaniqlik "trend bor" degani emas
    (0.3-band).
    """
    if ema_fast is None or ema_slow is None:
        return TrendDirection.FLAT

    tuzilma_kotarilish = ema_fast > ema_slow
    tuzilma_tushish = ema_fast < ema_slow

    if require_price_above_fast:
        kotarilish = price > ema_fast and price > ema_slow and tuzilma_kotarilish
        tushish = price < ema_fast and price < ema_slow and tuzilma_tushish
    else:
        kotarilish = price > ema_slow and tuzilma_kotarilish
        tushish = price < ema_slow and tuzilma_tushish

    if kotarilish:
        return TrendDirection.UP
    if tushish:
        return TrendDirection.DOWN
    return TrendDirection.FLAT


def timeframe_trend(
    candles: list[Candle],
    fast: int,
    slow: int,
    require_price_above_fast: bool = True,
) -> TrendDirection:
    """Bitta timeframe uchun trend yo'nalishi (3.2-band muvofiqligi uchun)."""
    if len(candles) < slow:
        return TrendDirection.FLAT
    narxlar = closes(candles)
    return trend_direction(
        narxlar[-1], ema(narxlar, fast), ema(narxlar, slow), require_price_above_fast
    )


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


def is_trending(candles: list[Candle], period: int, threshold: float) -> bool | None:
    """4.4-band: bozor trendda mi yoki tekismi.

    Returns:
        `True`/`False`, yoki `None` — hisoblab bo'lmadi (signal berilmaydi).
    """
    qiymat = adx(candles, period)
    return None if qiymat is None else qiymat >= threshold
