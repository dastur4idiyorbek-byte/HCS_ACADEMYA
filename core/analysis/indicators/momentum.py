"""Momentum indikatorlari — RSI va MACD.

3.1-band: bular kirish TASDIG'I. Yolg'iz "RSI 30dan past chiqdi" signal
EMAS — bu spetsifikatsiyada aniq taqiqlangan. Ular faqat narx muhim S/R
zonasida bo'lganda ma'noga ega.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.indicators.trend import ema_series


def rsi_series(values: list[float], period: int = 14) -> list[float | None]:
    """Relative Strength Index (Wilder silliqlash bilan).

    Yetarli ma'lumot bo'lmagan nuqtalarda `None`.
    """
    if period <= 0:
        raise ValueError("Davr musbat bo'lishi kerak")
    if len(values) <= period:
        return [None] * len(values)

    ozgarishlar = [values[i] - values[i - 1] for i in range(1, len(values))]
    osishlar = [max(o, 0.0) for o in ozgarishlar]
    tushishlar = [max(-o, 0.0) for o in ozgarishlar]

    natija: list[float | None] = [None] * period

    ortacha_osish = sum(osishlar[:period]) / period
    ortacha_tushish = sum(tushishlar[:period]) / period
    natija.append(_rsi_from(ortacha_osish, ortacha_tushish))

    for i in range(period, len(ozgarishlar)):
        ortacha_osish = (ortacha_osish * (period - 1) + osishlar[i]) / period
        ortacha_tushish = (ortacha_tushish * (period - 1) + tushishlar[i]) / period
        natija.append(_rsi_from(ortacha_osish, ortacha_tushish))

    return natija


def _rsi_from(avg_gain: float, avg_loss: float) -> float:
    """Tushish umuman bo'lmasa RSI = 100 (nolga bo'lish o'rniga)."""
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def rsi(values: list[float], period: int = 14) -> float | None:
    qator = rsi_series(values, period)
    return qator[-1] if qator else None


def rsi_recovering_from_oversold(
    values: list[float],
    period: int,
    oversold: float,
    lookback: int = 5,
) -> bool:
    """3.1-band: "RSI 30dan qaytish" — tasdiqlovchi shart.

    Shart: oxirgi `lookback` sham ichida RSI `oversold` dan past bo'lgan VA
    hozir undan yuqoriga chiqqan. Ya'ni narx haddan tashqari sotilgan
    holatdan CHIQMOQDA — hali unda turgani emas.
    """
    qator = [q for q in rsi_series(values, period)[-(lookback + 1):] if q is not None]
    if len(qator) < 2:
        return False
    return qator[-1] > oversold and any(q <= oversold for q in qator[:-1])


@dataclass(frozen=True, slots=True)
class MacdResult:
    """MACD chizig'i, signal chizig'i va ular orasidagi farq."""

    macd: float
    signal: float
    histogram: float
    previous_histogram: float | None

    @property
    def bullish_cross(self) -> bool:
        """MACD signal chiziqni PASTDAN kesib o'tdi — kirish tasdig'i."""
        if self.previous_histogram is None:
            return False
        return self.previous_histogram <= 0 < self.histogram

    @property
    def is_bullish(self) -> bool:
        """MACD signal chiziqdan yuqorida (kesish allaqachon bo'lgan)."""
        return self.histogram > 0

    @property
    def above_zero(self) -> bool:
        """MACD nol chizig'idan yuqorida — umumiy momentum ko'tarilishda.

        Bu `is_bullish` dan FARQ qiladi: MACD musbat bo'lsa-yu, signal
        chiziqdan pastda bo'lsa, momentum bor, lekin sekinlashmoqda.
        """
        return self.macd > 0


def macd(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> MacdResult | None:
    """Moving Average Convergence Divergence.

    Returns:
        `MacdResult`, yoki `None` — ma'lumot yetarli emas.
    """
    if fast >= slow:
        raise ValueError("`fast` davri `slow` dan kichik bo'lishi kerak")
    if len(values) < slow + signal_period:
        return None

    tez = ema_series(values, fast)
    sekin = ema_series(values, slow)

    macd_qatori = [
        t - s for t, s in zip(tez, sekin, strict=True) if t is not None and s is not None
    ]
    if len(macd_qatori) < signal_period:
        return None

    signal_qatori = ema_series(macd_qatori, signal_period)
    juftlar = [
        (m, s)
        for m, s in zip(macd_qatori[-len(signal_qatori):], signal_qatori, strict=True)
        if s is not None
    ]
    if not juftlar:
        return None

    macd_q, signal_q = juftlar[-1]
    oldingi = juftlar[-2][0] - juftlar[-2][1] if len(juftlar) >= 2 else None

    return MacdResult(
        macd=macd_q,
        signal=signal_q,
        histogram=macd_q - signal_q,
        previous_histogram=oldingi,
    )
