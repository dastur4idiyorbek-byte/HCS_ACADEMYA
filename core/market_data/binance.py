"""Binance public WebSocket va REST mijozi.

6.2-band: API kalitsiz, bepul. Faqat ochiq (public) endpointlar.

Fail-safe talablari (0.3 va 6.4-band):
  - uzilish va qayta ulanish MAJBURIY log qilinadi
  - qayta ulanish eksponensial kutish bilan
  - obuna ro'yxati o'zgarsa, ulanish qayta quriladi
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import websockets
from websockets.exceptions import ConnectionClosed

from core.config.schema import MarketDataConfig
from core.domain.models import Candle, PriceTick
from core.market_data.base import BackoffPolicy, CandleProvider, PriceStream
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Binance timeframe nomlari loyihanikiga mos keladi, faqat oylik farq qiladi
_TIMEFRAME_MAP = {"1M": "1M", "1w": "1w", "1d": "1d", "4h": "4h", "1h": "1h",
                  "30m": "30m", "15m": "15m", "5m": "5m", "1m": "1m"}


def to_binance_symbol(symbol: str, quote: str = "USDT") -> str:
    """`BTC` -> `btcusdt` (WebSocket kichik harf talab qiladi)."""
    upper = symbol.upper()
    if upper.endswith(quote.upper()):
        return upper.lower()
    return f"{upper}{quote.upper()}".lower()


def from_binance_symbol(stream_symbol: str, quote: str = "USDT") -> str:
    """`BTCUSDT` -> `BTC`."""
    upper = stream_symbol.upper()
    return upper[: -len(quote)] if upper.endswith(quote.upper()) else upper


class BinancePriceStream(PriceStream):
    """Bir nechta coin narxini bitta birlashtirilgan (combined) oqimda oladi."""

    def __init__(self, config: MarketDataConfig, quote_asset: str = "USDT") -> None:
        self._config = config
        self._quote = quote_asset
        self._symbols: set[str] = set()
        self._backoff = BackoffPolicy(config.reconnect_backoff_seconds)
        self._resubscribe = asyncio.Event()
        self._closed = False

    def subscribe(self, symbols: set[str]) -> None:
        """Kuzatiladigan coinlarni belgilaydi.

        Ro'yxat o'zgargan bo'lsa, mavjud ulanish uzilib qayta quriladi —
        Binance combined stream URL'i ulanish paytida belgilanadi.
        """
        yangi = {s.upper() for s in symbols}
        if yangi == self._symbols:
            return
        qoshildi = yangi - self._symbols
        chiqdi = self._symbols - yangi
        self._symbols = yangi
        logger.info(
            "Narx obunasi yangilandi: jami=%d qo'shildi=%s chiqdi=%s",
            len(yangi),
            sorted(qoshildi) or "—",
            sorted(chiqdi) or "—",
        )
        self._resubscribe.set()

    def _url(self) -> str:
        oqimlar = "/".join(
            f"{to_binance_symbol(s, self._quote)}@trade" for s in sorted(self._symbols)
        )
        return f"{self._config.ws_base_url}?streams={oqimlar}"

    async def stream(self) -> AsyncIterator[PriceTick]:
        """Narx nuqtalarini uzluksiz yetkazadi, uzilishda qayta ulanadi."""
        while not self._closed:
            if not self._symbols:
                # Kuzatiladigan signal yo'q — bo'sh ulanish ochmaymiz
                self._resubscribe.clear()
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(self._resubscribe.wait(), timeout=5.0)
                continue

            self._resubscribe.clear()
            try:
                async for tick in self._connect_and_read():
                    yield tick
            except ConnectionClosed as exc:
                kutish = self._backoff.next_delay()
                logger.warning(
                    "WebSocket uzildi (%s). %.0f soniyadan keyin qayta ulanamiz "
                    "(urinish %d).",
                    exc,
                    kutish,
                    self._backoff.attempts,
                )
                await asyncio.sleep(kutish)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                kutish = self._backoff.next_delay()
                logger.exception(
                    "WebSocket xatosi. %.0f soniyadan keyin qayta ulanamiz.", kutish
                )
                await asyncio.sleep(kutish)

    async def _connect_and_read(self) -> AsyncIterator[PriceTick]:
        url = self._url()
        logger.info("WebSocket ulanmoqda: %d ta coin", len(self._symbols))

        async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
            self._backoff.reset()
            logger.info("WebSocket ulandi")

            while not self._closed:
                if self._resubscribe.is_set():
                    logger.info("Obuna o'zgardi — ulanish qayta quriladi")
                    return

                try:
                    xom = await asyncio.wait_for(ws.recv(), timeout=30.0)
                except TimeoutError:
                    # 30 soniya jimlik — ping bilan tekshiramiz
                    continue

                tick = self._parse(xom)
                if tick is not None:
                    yield tick

    def _parse(self, raw: str | bytes) -> PriceTick | None:
        """Binance trade xabarini `PriceTick` ga aylantiradi.

        Buzuq xabar butun oqimni to'xtatmasligi kerak — log qilinadi va
        o'tkazib yuboriladi (0.3-band).
        """
        try:
            xabar = json.loads(raw)
            data = xabar.get("data", xabar)
            symbol = from_binance_symbol(data["s"], self._quote)
            return PriceTick(
                symbol=symbol,
                price=float(data["p"]),
                timestamp=datetime.fromtimestamp(data["T"] / 1000, tz=UTC),
            )
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            logger.warning("Tushunarsiz WebSocket xabari o'tkazib yuborildi")
            return None

    async def close(self) -> None:
        self._closed = True
        self._resubscribe.set()


#: Binance bitta so'rovda shundan ortiq sham qaytarmaydi
BINANCE_MAX_KLINES = 1000


class BinanceCandleProvider(CandleProvider):
    """REST orqali tarixiy OHLCV (indikatorlar va backtest uchun)."""

    def __init__(self, config: MarketDataConfig, quote_asset: str = "USDT") -> None:
        self._config = config
        self._quote = quote_asset
        self._session = None

    async def _get_session(self):  # noqa: ANN202
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _fetch_page(
        self,
        pair: str,
        interval: str,
        limit: int,
        end_time: int | None,
        eng_yangi_sahifa: bool,
    ) -> list[Candle]:
        """Bitta so'rov — Binance ko'pi bilan 1000 sham qaytaradi."""
        url = f"{self._config.rest_base_url}/api/v3/klines"
        params: dict[str, str | int] = {
            "symbol": pair,
            "interval": interval,
            "limit": min(limit, BINANCE_MAX_KLINES),
        }
        if end_time is not None:
            params["endTime"] = end_time

        session = await self._get_session()
        async with session.get(url, params=params) as javob:
            javob.raise_for_status()
            xom = await javob.json()

        return [
            Candle(
                open_time=datetime.fromtimestamp(qator[0] / 1000, tz=UTC),
                open=float(qator[1]),
                high=float(qator[2]),
                low=float(qator[3]),
                close=float(qator[4]),
                volume=float(qator[5]),
                # Faqat ENG YANGI shamning yopilmagan bo'lishi mumkin.
                # Eski sahifalarning oxirgi shami allaqachon yopilgan —
                # aks holda backtest tarixning har 1000 shamida bittasini
                # "yopilmagan" deb belgilab chiqardi.
                closed=not (eng_yangi_sahifa and index == len(xom) - 1),
            )
            for index, qator in enumerate(xom)
        ]

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        """Tarixiy shamlar, eng eskisidan eng yangisiga.

        1000 DAN ORTIQ SO'RALSA SAHIFALAB YUKLANADI. Ilgari so'rov
        `min(limit, 1000)` bilan qirqilardi va bu JIMGINA sodir
        bo'lardi: `--days 730` deb yozilgan backtest 4 soatlik
        timeframeda aslida atigi ~166 kunni ko'rardi. Spetsifikatsiya
        esa 1-2 yillik sinovni MAJBURIY deb belgilaydi — ya'ni
        majburiy shart bajarilgandek ko'rinib, aslida bajarilmasdi.

        Sahifalar ORQAGA qarab olinadi: har safar oldingi sahifaning
        eng eski shamidan bir millisekund oldingi vaqt `endTime` ga
        beriladi.
        """
        interval = _TIMEFRAME_MAP.get(timeframe)
        if interval is None:
            raise ValueError(f"Qo'llab-quvvatlanmaydigan timeframe: {timeframe}")

        pair = to_binance_symbol(symbol, self._quote).upper()
        yigilgan: list[Candle] = []
        end_time: int | None = None

        while len(yigilgan) < limit:
            kerak = limit - len(yigilgan)
            if yigilgan:
                # Ikkinchi va undan keyingi sahifalar oldida pauza —
                # aks holda uzoq tarix so'ralganda o'nlab so'rov bir
                # zumda ketadi va Binance IP ni bloklaydi.
                await asyncio.sleep(self._config.candle_page_pause_seconds)
            sahifa = await self._fetch_page(
                pair, interval, kerak, end_time, eng_yangi_sahifa=not yigilgan
            )
            if not sahifa:
                # Tarix tugadi — coin bunchalik eski emas.
                break
            yigilgan = sahifa + yigilgan
            end_time = int(sahifa[0].open_time.timestamp() * 1000) - 1
            if len(sahifa) < min(kerak, BINANCE_MAX_KLINES):
                break

        return yigilgan[-limit:] if len(yigilgan) > limit else yigilgan

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
