"""Bozor ma'lumotlari uchun umumiy shartnomalar.

Nima uchun abstraksiya: birjani almashtirish (Binance -> Bybit) yoki
backtestda tarixiy ma'lumotni "jonli oqim" sifatida uzatish uchun. Kuzatuv
kodi manba nima ekanini bilmasligi kerak.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.domain.models import Candle, MarketRankEntry, PriceTick
from core.utils.time_utils import utc_now


class PriceStream(ABC):
    """Real vaqtli narx oqimi."""

    @abstractmethod
    def subscribe(self, symbols: set[str]) -> None:
        """Kuzatiladigan coinlar ro'yxatini belgilaydi (o'zgarishi mumkin)."""

    @abstractmethod
    async def stream(self) -> AsyncIterator[PriceTick]:
        """Narx nuqtalarini uzluksiz yetkazadi."""

    @abstractmethod
    async def close(self) -> None:
        ...


class CandleProvider(ABC):
    """Tarixiy OHLCV manbai (indikatorlar va backtest uchun)."""

    @abstractmethod
    async def fetch_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        ...


class RankingProvider(ABC):
    """Kapitalizatsiya reytingi manbai (3.4-band)."""

    @abstractmethod
    async def fetch_ranking(self, limit: int) -> list[MarketRankEntry]:
        ...


@dataclass(slots=True)
class PriceCache:
    """Oxirgi narxlar va ularning yoshi.

    6.2-band: `stale_price_seconds` dan eski narx bilan signal BERILMAYDI.
    Bu tekshiruvni Risk Engine'dagi `FreshDataRule` bajaradi, lekin yoshni
    shu yerda hisoblanadi.
    """

    prices: dict[str, PriceTick] = field(default_factory=dict)

    def update(self, tick: PriceTick) -> None:
        self.prices[tick.symbol.upper()] = tick

    def get(self, symbol: str) -> PriceTick | None:
        return self.prices.get(symbol.upper())

    def price_of(self, symbol: str) -> float | None:
        tick = self.get(symbol)
        return tick.price if tick else None

    def age_seconds(self, symbol: str, now: datetime | None = None) -> float | None:
        """Narx necha sekund oldin yangilangan. `None` — narx umuman yo'q."""
        tick = self.get(symbol)
        if tick is None:
            return None
        return ((now or utc_now()) - tick.timestamp).total_seconds()

    def is_stale(self, symbol: str, max_age: float, now: datetime | None = None) -> bool:
        """Fail-safe: narx yo'q bo'lsa ham "eskirgan" deb qaraladi."""
        yosh = self.age_seconds(symbol, now)
        return yosh is None or yosh > max_age

    def oldest_age(self, symbols: set[str], now: datetime | None = None) -> float | None:
        """Berilgan coinlar orasidagi eng eski narxning yoshi."""
        yoshlar = [self.age_seconds(s, now) for s in symbols]
        if not yoshlar or any(y is None for y in yoshlar):
            return None
        return max(yoshlar)  # type: ignore[type-var]


class BackoffPolicy:
    """Qayta ulanish kutish siyosati (6.2-band).

    Ketma-ket uzilishlarda kutish vaqti oshib boradi, muvaffaqiyatli
    ulanishdan keyin qayta boshlanadi.
    """

    def __init__(self, delays: list[int]) -> None:
        if not delays:
            raise ValueError("Kutish oraliqlari bo'sh bo'lmasligi kerak")
        self._delays = delays
        self._attempt = 0

    def next_delay(self) -> float:
        """Keyingi kutish vaqti (sekund)."""
        delay = self._delays[min(self._attempt, len(self._delays) - 1)]
        self._attempt += 1
        return float(delay)

    def reset(self) -> None:
        self._attempt = 0

    @property
    def attempts(self) -> int:
        return self._attempt


@dataclass(slots=True)
class SpikeDetector:
    """4.7-band: favqulodda to'xtash (kill switch) uchun sakrash detektori.

    Belgilangan oyna ichida narx ±N% dan ortiq harakat qilsa, kill switch
    ishga tushadi va inson tekshirmaguncha o'chmaydi.
    """

    threshold_pct: float
    window: timedelta
    _history: dict[str, list[tuple[datetime, float]]] = field(default_factory=dict)

    def observe(self, symbol: str, price: float, at: datetime) -> float | None:
        """Narxni qayd etadi. Sakrash aniqlansa uning foizini qaytaradi."""
        upper = symbol.upper()
        tarix = self._history.setdefault(upper, [])
        tarix.append((at, price))

        chegara = at - self.window
        while tarix and tarix[0][0] < chegara:
            tarix.pop(0)

        if len(tarix) < 2:
            return None

        narxlar = [p for _, p in tarix]
        eng_past, eng_baland = min(narxlar), max(narxlar)
        if eng_past <= 0:
            return None

        ozgarish = (eng_baland - eng_past) / eng_past * 100
        if ozgarish < self.threshold_pct:
            return None

        # Yo'nalishni aniqlaymiz: oxirgi narx eng balandga yaqinmi yoki pastga
        oxirgi = narxlar[-1]
        return ozgarish if oxirgi >= (eng_past + eng_baland) / 2 else -ozgarish

    def reset(self, symbol: str | None = None) -> None:
        if symbol is None:
            self._history.clear()
        else:
            self._history.pop(symbol.upper(), None)


#: Kill switch ishga tushganda chaqiriladigan funksiya turi
KillSwitchCallback = Callable[[str, float], None]
