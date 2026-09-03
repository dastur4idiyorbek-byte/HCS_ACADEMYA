"""Bitget public REST mijozi — Binance'ga QO'SHIMCHA manba.

Ikkita vazifasi bor va ikkalasi ham 2-promptning 2-qismidan:

  1. Binance'da bo'lmagan coinlar uchun sham manbai
  2. Bitta birjaning tasodifiy "wick"ini rad etish uchun IKKINCHI
     fikr (`price_reconciliation.py` shu ikkalasini solishtiradi)

API kalitsiz, faqat ochiq endpointlar — Binance mijozidagi kabi.

BITGET FARQLARI (Binance bilan solishtirganda):
  - juftlik nomi: `BTCUSDT` (bir xil), lekin `granularity` boshqacha
    yoziladi: `1day`, `4h`, `15min`
  - sham massivi ORQAGA emas, ILGARIGA saralangan holda keladi
  - vaqt chegarasi `endTime` emas, `endTime` (ms) — bir xil, lekin
    javob `data` kalitining ichida turadi
  - bitta so'rovda ko'pi bilan 1000 sham (Binance bilan bir xil)
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from core.config.schema import MarketDataConfig
from core.domain.models import Candle
from core.market_data.base import CandleProvider
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Bitget bitta so'rovda shundan ortiq sham qaytarmaydi
BITGET_MAX_KLINES = 1000

#: Loyihaning timeframe nomi -> Bitget `granularity`.
#: Bitget `1d` emas `1day`, `15m` emas `15min` yozadi — mos jadval
#: bo'lmasa so'rov jimgina bo'sh ro'yxat qaytaradi.
_GRANULARITY = {
    "1M": "1M",
    "1w": "1week",
    "1d": "1day",
    "4h": "4h",
    "1h": "1h",
    "30m": "30min",
    "15m": "15min",
    "5m": "5min",
    "1m": "1min",
}


def to_bitget_symbol(symbol: str, quote: str = "USDT") -> str:
    """`BTC` -> `BTCUSDT` (Bitget KATTA harf talab qiladi)."""
    upper = symbol.upper()
    if upper.endswith(quote.upper()):
        return upper
    return f"{upper}{quote.upper()}"


class BitgetCandleProvider(CandleProvider):
    """Bitget REST orqali tarixiy OHLCV.

    Interfeys `BinanceCandleProvider` bilan AYNAN bir xil — chaqiruvchi
    qaysi birja ekanini bilmasligi kerak. Aks holda "ikkinchi manba"
    qo'shish har bir chaqiruv joyini o'zgartirishni talab qilardi.
    """

    def __init__(
        self,
        config: MarketDataConfig,
        quote_asset: str = "USDT",
        base_url: str = "https://api.bitget.com",
    ) -> None:
        self._config = config
        self._quote = quote_asset
        self._base_url = base_url.rstrip("/")
        self._session = None

    async def _get_session(self):  # noqa: ANN202
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _fetch_page(
        self, pair: str, granularity: str, limit: int, end_time: int | None
    ) -> list[Candle]:
        """Bitta so'rov.

        `closed` HAR DOIM True: bu provayder tarix uchun ishlatiladi,
        jonli oxirgi sham uchun emas. Binance mijozidagi "eng yangi
        sham yopilmagan" mantig'i bu yerda takrorlanmaydi — chunki
        ikkinchi manba faqat SOLISHTIRISH uchun kerak va yopilmagan
        shamni solishtirish ikki birjaning turli soniyasini
        taqqoslash degani bo'lardi.
        """
        url = f"{self._base_url}/api/v2/spot/market/history-candles"
        params: dict[str, str | int] = {
            "symbol": pair,
            "granularity": granularity,
            "limit": min(limit, BITGET_MAX_KLINES),
        }
        if end_time is not None:
            params["endTime"] = end_time

        session = await self._get_session()
        async with session.get(url, params=params) as javob:
            javob.raise_for_status()
            xom = await javob.json()

        # Bitget javobni `{"code": "00000", "data": [...]}` shaklida
        # beradi. Xato bo'lsa ham HTTP 200 qaytaradi va faqat `code`
        # boshqacha bo'ladi — `raise_for_status()` buni USHLAMAYDI.
        if str(xom.get("code")) != "00000":
            logger.warning(
                "Bitget xato javobi: %s %s — %s",
                pair, granularity, xom.get("msg", "sabab yo'q"),
            )
            return []

        return [
            Candle(
                open_time=datetime.fromtimestamp(int(qator[0]) / 1000, tz=UTC),
                open=float(qator[1]),
                high=float(qator[2]),
                low=float(qator[3]),
                close=float(qator[4]),
                volume=float(qator[5]),
                closed=True,
            )
            for qator in xom.get("data", [])
        ]

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        until: datetime | None = None,
    ) -> list[Candle]:
        """Tarixiy shamlar, eng eskisidan eng yangisiga.

        Sahifalash Binance mijozidagi bilan bir xil naqshda: sahifalar
        ORQAGA olinadi, har safar oldingi sahifaning eng eski shamidan
        bir millisekund oldingi vaqt `endTime` ga beriladi.

        Bitget javobni O'SISH tartibida qaytaradi, lekin buni kafolat
        deb qabul qilmaymiz: sahifa har safar `open_time` bo'yicha
        qayta saralanadi. Tartib buzilsa sahifalash mantig'i jimgina
        cheksiz siklga tushardi.
        """
        granularity = _GRANULARITY.get(timeframe)
        if granularity is None:
            raise ValueError(f"Qo'llab-quvvatlanmaydigan timeframe: {timeframe}")

        pair = to_bitget_symbol(symbol, self._quote)
        yigilgan: list[Candle] = []
        end_time = int(until.timestamp() * 1000) if until is not None else None

        while len(yigilgan) < limit:
            kerak = limit - len(yigilgan)
            if yigilgan:
                await asyncio.sleep(self._config.candle_page_pause_seconds)
            sahifa = sorted(
                await self._fetch_page(pair, granularity, kerak, end_time),
                key=lambda c: c.open_time,
            )
            if not sahifa:
                break
            yigilgan = sahifa + yigilgan
            end_time = int(sahifa[0].open_time.timestamp() * 1000) - 1
            if len(sahifa) < min(kerak, BITGET_MAX_KLINES):
                break

        return yigilgan[-limit:] if len(yigilgan) > limit else yigilgan

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
