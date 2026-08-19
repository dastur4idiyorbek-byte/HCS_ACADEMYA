"""Volatillik o'lchovlari — ATR va True Range.

DIQQAT (3.1-band): bu modul S/R zonalarini TASDIQLOVCHI indikator emas.
ATR bu yerda **o'lchov birligi** sifatida ishlatiladi: zonalar qanchalik
keng bo'lishi, narx zonaga qanchalik yaqin ekani — barchasi ATR bilan
o'lchanadi. Coin narxi $0.0004 yoki $67 000 bo'lishidan qat'i nazar,
"yaqin" tushunchasi bir xil ma'no beradi.

Tasdiqlovchi indikatorlar (EMA, RSI, MACD, hajm) 7-bosqichda qo'shiladi.
"""

from __future__ import annotations

from core.domain.models import Candle


def true_range(current: Candle, previous: Candle | None) -> float:
    """Bitta shamning haqiqiy diapazoni.

    Uchtasining eng kattasi: sham diapazoni, oldingi yopilishdan yuqoriga
    sakrash, oldingi yopilishdan pastga sakrash. Sakrash (gap) hisobga
    olinishi shart — aks holda volatillik kam ko'rsatiladi.
    """
    if previous is None:
        return current.high - current.low
    return max(
        current.high - current.low,
        abs(current.high - previous.close),
        abs(current.low - previous.close),
    )


def true_ranges(candles: list[Candle]) -> list[float]:
    return [
        true_range(sham, candles[i - 1] if i > 0 else None)
        for i, sham in enumerate(candles)
    ]


def atr(candles: list[Candle], period: int = 14) -> float | None:
    """Average True Range (Wilder usuli bo'yicha silliqlangan).

    Returns:
        ATR qiymati, yoki `None` — shamlar yetarli emas. `None` qaytishi
        chaqiruvchi uchun "hisoblab bo'lmadi" degani va 0.3-band bo'yicha
        signal berilmasligiga olib keladi.
    """
    if period <= 0:
        raise ValueError("Davr musbat bo'lishi kerak")
    if len(candles) < period + 1:
        return None

    tr = true_ranges(candles)[1:]  # birinchi sham uchun oldingi yopilish yo'q
    if len(tr) < period:
        return None

    # Wilder silliqlash: birinchi qiymat oddiy o'rtacha, keyin ketma-ket
    qiymat = sum(tr[:period]) / period
    for keyingi in tr[period:]:
        qiymat = (qiymat * (period - 1) + keyingi) / period
    return qiymat


def atr_pct(candles: list[Candle], period: int = 14) -> float | None:
    """ATR ni oxirgi narxga nisbatan foizda — coinlar orasida taqqoslash uchun.

    Risk Engine'dagi `VolatilityRule` (4.6-band) shu qiymatga tayanadi.
    """
    qiymat = atr(candles, period)
    if qiymat is None or not candles:
        return None
    oxirgi = candles[-1].close
    return None if oxirgi <= 0 else qiymat / oxirgi * 100
