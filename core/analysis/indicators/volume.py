"""Hajm tasdig'i (3.1-band).

Shart: oxirgi shamning hajmi so'nggi 20 sham o'rtachasidan yuqori. Sabab —
narx S/R zonasidan qaytayotganda hajm oshishi bu harakatning haqiqiy
ekanini ko'rsatadi. Hajmsiz harakat ko'pincha yolg'on chiqadi.
"""

from __future__ import annotations

from core.domain.models import Candle


def volume_average(candles: list[Candle], period: int = 20) -> float | None:
    """So'nggi `period` shamning o'rtacha hajmi (oxirgi shamni hisobga olmasdan).

    Oxirgi sham o'rtachaga kiritilmaydi — aks holda u o'zini o'zi bilan
    taqqoslardi va katta hajm o'rtachani ko'tarib, farqni yashirardi.
    """
    if period <= 0:
        raise ValueError("Davr musbat bo'lishi kerak")
    if len(candles) < period + 1:
        return None
    oyna = candles[-(period + 1) : -1]
    return sum(sham.volume for sham in oyna) / len(oyna)


def volume_ratio(candles: list[Candle], period: int = 20) -> float | None:
    """Oxirgi hajmning o'rtachaga nisbati. 1.0 — o'rtacha, 2.0 — ikki barobar."""
    ortacha = volume_average(candles, period)
    if ortacha is None or ortacha <= 0:
        return None
    return candles[-1].volume / ortacha


def volume_confirms(candles: list[Candle], period: int = 20, min_ratio: float = 1.0) -> bool:
    """Hajm harakatni tasdiqlaydimi.

    Ma'lumot yetishmasa `False` — noaniqlik tasdiq emas (0.3-band).
    """
    nisbat = volume_ratio(candles, period)
    return nisbat is not None and nisbat >= min_ratio
