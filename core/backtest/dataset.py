"""Backtest uchun tarixiy ma'lumot to'plami.

ENG MUHIM TALAB: "kelajakka qarash" (lookahead) bo'lmasligi. Backtest
har bir qadamda faqat O'SHA PAYTGACHA mavjud bo'lgan shamlarni ko'rishi
kerak. Ansiz natijalar chiroyli chiqadi va jonli savdoda hammasi buziladi
— bu backtestning eng keng tarqalgan va eng qimmat xatosi.

Shuning uchun `Dataset` sham ro'yxatini TO'G'RIDAN-TO'G'RI bermaydi: har
bir so'rov vaqt chegarasi bilan keladi va faqat shu vaqtgacha yopilgan
shamlar qaytariladi.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import datetime

from core.domain.models import Candle


@dataclass(slots=True)
class SymbolSeries:
    """Bitta coin uchun timeframelar bo'yicha shamlar."""

    symbol: str
    candles: dict[str, list[Candle]] = field(default_factory=dict)
    #: Tez qidirish uchun oldindan hisoblangan vaqt indekslari
    _times: dict[str, list[datetime]] = field(default_factory=dict, repr=False)

    def add(self, timeframe: str, candles: list[Candle]) -> None:
        tartiblangan = sorted(candles, key=lambda c: c.open_time)
        self.candles[timeframe] = tartiblangan
        self._times[timeframe] = [c.open_time for c in tartiblangan]

    def up_to(self, timeframe: str, moment: datetime) -> list[Candle]:
        """Faqat `moment` gacha OCHILGAN shamlar.

        Chegara: `open_time <= moment`. Oxirgi sham hali yopilmagan
        bo'lishi mumkin — bu jonli rejimdagi holatni aynan takrorlaydi.
        """
        vaqtlar = self._times.get(timeframe)
        if not vaqtlar:
            return []
        chegara = bisect_right(vaqtlar, moment)
        return self.candles[timeframe][:chegara]

    @property
    def timeframes(self) -> list[str]:
        return list(self.candles)


@dataclass(slots=True)
class Dataset:
    """Barcha coinlar uchun tarixiy ma'lumot."""

    series: dict[str, SymbolSeries] = field(default_factory=dict)

    def add(self, symbol: str, timeframe: str, candles: list[Candle]) -> None:
        seriya = self.series.setdefault(symbol, SymbolSeries(symbol))
        seriya.add(timeframe, candles)

    @property
    def symbols(self) -> list[str]:
        return sorted(self.series)

    def window(self, symbol: str, moment: datetime) -> dict[str, list[Candle]]:
        """Bitta coin uchun barcha timeframelar, `moment` gacha kesilgan."""
        seriya = self.series.get(symbol)
        if seriya is None:
            return {}
        return {tf: seriya.up_to(tf, moment) for tf in seriya.timeframes}

    def timeline(self, timeframe: str) -> list[datetime]:
        """Backtest qadamlari — berilgan timeframedagi barcha sham vaqtlari.

        Bir nechta coin bo'lsa, ularning vaqtlari birlashtiriladi va
        takrorlanmaydigan qilib tartiblanadi.
        """
        vaqtlar: set[datetime] = set()
        for seriya in self.series.values():
            vaqtlar.update(c.open_time for c in seriya.candles.get(timeframe, []))
        return sorted(vaqtlar)

    def price_at(self, symbol: str, moment: datetime, timeframe: str) -> float | None:
        """Berilgan vaqtdagi yopilish narxi."""
        shamlar = self.series[symbol].up_to(timeframe, moment) if symbol in self.series else []
        return shamlar[-1].close if shamlar else None

    def future_candles(
        self, symbol: str, timeframe: str, after: datetime
    ) -> list[Candle]:
        """`after` dan KEYINGI shamlar — FAQAT signal natijasini kuzatish uchun.

        DIQQAT: bu funksiya tahlilda ishlatilmaydi. U signal berilgandan
        keyin narx qanday harakat qilganini bilish uchun kerak — ya'ni
        natijani hisoblash uchun, qaror qabul qilish uchun emas.
        """
        seriya = self.series.get(symbol)
        if seriya is None:
            return []
        barcha = seriya.candles.get(timeframe, [])
        return [c for c in barcha if c.open_time > after]


#: Timeframe nomi -> daqiqalar. Yig'ish uchun kerak.
TIMEFRAME_MINUTES: dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


def aggregate(candles: list[Candle], source_minutes: int, target_minutes: int) -> list[Candle]:
    """Pastki timeframe shamlaridan yuqori timeframe shamlarini yig'adi.

    Nima uchun kerak: ko'p timeframe muvofiqligi (3.2-band) faqat shamlar
    BIR XIL narx harakatidan olingan bo'lsa ma'noga ega. Har bir timeframe
    alohida qator bo'lsa, ular hech qachon muvofiq bo'lmaydi va tizim
    hech qachon signal bermaydi — bu backtestda aynan shunday yuz berdi.

    Haqiqiy birjalarda ham 4 soatlik sham 15 daqiqaliklardan yig'iladi.
    """
    if target_minutes % source_minutes != 0:
        raise ValueError(
            f"{target_minutes} daqiqa {source_minutes} daqiqaga bo'linmaydi"
        )
    nisbat = target_minutes // source_minutes
    if nisbat <= 1:
        return list(candles)

    natija: list[Candle] = []
    for boshi in range(0, len(candles), nisbat):
        guruh = candles[boshi : boshi + nisbat]
        if not guruh:
            continue
        natija.append(
            Candle(
                open_time=guruh[0].open_time,
                open=guruh[0].open,
                high=max(c.high for c in guruh),
                low=min(c.low for c in guruh),
                close=guruh[-1].close,
                volume=sum(c.volume for c in guruh),
                closed=len(guruh) == nisbat,
            )
        )
    return natija


def build_dataset(
    base_candles: dict[str, list[Candle]],
    base_timeframe: str,
    timeframes: list[str],
) -> Dataset:
    """Bitta asosiy qatordan barcha timeframelarni quradi.

    Args:
        base_candles: coin -> eng past timeframedagi shamlar.
        base_timeframe: asosiy timeframe nomi (masalan `"15m"`).
        timeframes: kerakli timeframelar ro'yxati.
    """
    asos_daqiqa = TIMEFRAME_MINUTES[base_timeframe]
    dataset = Dataset()

    for symbol, shamlar in base_candles.items():
        for tf in timeframes:
            nishon = TIMEFRAME_MINUTES.get(tf)
            if nishon is None or nishon < asos_daqiqa:
                continue
            dataset.add(symbol, tf, aggregate(shamlar, asos_daqiqa, nishon))

    return dataset
