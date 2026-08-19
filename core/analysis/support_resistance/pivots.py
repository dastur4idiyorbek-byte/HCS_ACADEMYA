"""Swing pivotlarni aniqlash — S/R zonalarining xom ashyosi.

Pivot high — atrofidagi shamlardan baland cho'qqi, pivot low — chuqurlik.
Aynan shu nuqtalarda bozor yo'nalishni o'zgartirgan, shuning uchun ular
kelajakda ham qarshilik/qo'llab-quvvatlash bo'lib xizmat qiladi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.domain.enums import ZoneKind
from core.domain.models import Candle


@dataclass(frozen=True, slots=True)
class Pivot:
    """Bitta swing nuqtasi."""

    index: int
    price: float
    kind: ZoneKind
    at: datetime

    @property
    def is_high(self) -> bool:
        return self.kind is ZoneKind.RESISTANCE


def find_pivots(candles: list[Candle], lookback: int = 5) -> list[Pivot]:
    """Barcha swing high va low nuqtalarini topadi.

    Args:
        candles: shamlar (eng eskisidan eng yangisiga).
        lookback: chap va o'ngdagi tasdiqlovchi shamlar soni. Kattaroq qiymat
            — kamroq, lekin ahamiyatliroq pivotlar.

    Eslatma: oxirgi `lookback` ta sham pivot bo'la olmaydi — ular hali
    o'ng tomondan tasdiqlanmagan. Bu ataylab: tasdiqlanmagan cho'qqiga
    tayanish "kelajakka qarash" (lookahead) xatosi bo'lardi va backtest
    natijalarini soxtalashtirardi.
    """
    if lookback < 1:
        raise ValueError("lookback kamida 1 bo'lishi kerak")
    if len(candles) < lookback * 2 + 1:
        return []

    pivotlar: list[Pivot] = []
    for i in range(lookback, len(candles) - lookback):
        oyna = candles[i - lookback : i + lookback + 1]

        if _is_pivot_high(candles, i, oyna, lookback):
            pivotlar.append(
                Pivot(i, candles[i].high, ZoneKind.RESISTANCE, candles[i].open_time)
            )
        if _is_pivot_low(candles, i, oyna, lookback):
            pivotlar.append(
                Pivot(i, candles[i].low, ZoneKind.SUPPORT, candles[i].open_time)
            )

    return pivotlar


def _is_pivot_high(candles: list[Candle], index: int, window: list[Candle], lookback: int) -> bool:
    """Tekis cho'qqida (plateau) faqat BIRINCHI sham pivot deb olinadi.

    Aks holda bir xil balandlikdagi ketma-ket shamlar bir nechta bir xil
    pivot berardi va zona sun'iy ravishda "ko'p test qilingan" ko'rinardi.
    """
    narx = candles[index].high
    if narx < max(sham.high for sham in window):
        return False
    boshlanish = index - lookback
    return all(candles[j].high < narx for j in range(boshlanish, index))


def _is_pivot_low(candles: list[Candle], index: int, window: list[Candle], lookback: int) -> bool:
    narx = candles[index].low
    if narx > min(sham.low for sham in window):
        return False
    boshlanish = index - lookback
    return all(candles[j].low > narx for j in range(boshlanish, index))


def count_touches(
    candles: list[Candle],
    low: float,
    high: float,
    from_index: int = 0,
) -> tuple[int, datetime | None]:
    """Narx zonaga necha marta kirganini sanaydi.

    Ketma-ket shamlar zona ichida turgani BITTA test hisoblanadi — narx
    zonada bir necha sham turgani "bir necha marta sinaldi" degani emas.

    Returns:
        `(testlar soni, oxirgi test vaqti)`.
    """
    soni = 0
    oxirgi: datetime | None = None
    ichida_edi = False

    for sham in candles[from_index:]:
        ichida = sham.low <= high and sham.high >= low
        if ichida and not ichida_edi:
            soni += 1
            oxirgi = sham.open_time
        ichida_edi = ichida

    return soni, oxirgi
