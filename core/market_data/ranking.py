"""3.4-band: kapitalizatsiya reytingi manbalari.

Asosiy manba — CoinMarketCap (API kaliti talab qiladi, `CMC_API_KEY`).
Zaxira — CoinGecko (kalitsiz).

Fail-safe (0.3-band): reyting olinmasa, halol ro'yxat YANGILANMAYDI va
oldingi tasdiqlangan ro'yxat kuchda qoladi. Bo'sh ro'yxat qaytarish
xavfli bo'lardi — tizim "halol coin yo'q" deb o'ylab qolardi.
"""

from __future__ import annotations

import os

from core.config.schema import MarketDataConfig
from core.domain.models import MarketRankEntry
from core.market_data.base import RankingProvider
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

CMC_API_KEY_ENV = "CMC_API_KEY"


class RankingUnavailableError(RuntimeError):
    """Reyting olinmadi — chaqiruvchi eski ro'yxat bilan davom etishi kerak."""


class CoinMarketCapRanking(RankingProvider):
    """CoinMarketCap `/cryptocurrency/listings/latest`.

    Bepul (Basic) reja oyiga 10 000 so'rov beradi. Bizga 12 soatda bir marta
    kerak — kuniga 2 so'rov, ya'ni bepul reja ortig'i bilan yetadi.
    """

    def __init__(self, config: MarketDataConfig, api_key: str | None = None) -> None:
        self._config = config
        self._api_key = api_key or os.getenv(CMC_API_KEY_ENV, "").strip()
        self._session = None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def _get_session(self):  # noqa: ANN202
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"X-CMC_PRO_API_KEY": self._api_key, "Accept": "application/json"}
            )
        return self._session

    async def fetch_ranking(self, limit: int) -> list[MarketRankEntry]:
        if not self.is_configured:
            raise RankingUnavailableError(
                f"{CMC_API_KEY_ENV} o'rnatilmagan — CoinMarketCap reytingi olinmadi. "
                "Kalitni .env fayliga qo'shing yoki ranking_source ni 'coingecko' qiling."
            )

        url = f"{self._config.coinmarketcap_base_url}/cryptocurrency/listings/latest"
        params = {"start": "1", "limit": str(min(limit, 5000)), "convert": "USD"}

        session = await self._get_session()
        async with session.get(url, params=params) as javob:
            if javob.status != 200:
                matn = await javob.text()
                raise RankingUnavailableError(
                    f"CoinMarketCap javobi: {javob.status} — {matn[:200]}"
                )
            xom = await javob.json()

        yozuvlar = xom.get("data") or []
        if not yozuvlar:
            raise RankingUnavailableError("CoinMarketCap bo'sh ro'yxat qaytardi")

        natija = [
            MarketRankEntry(
                rank=yozuv.get("cmc_rank", index + 1),
                symbol=yozuv["symbol"],
                name=yozuv.get("name", yozuv["symbol"]),
                market_cap_usd=float(yozuv["quote"]["USD"].get("market_cap") or 0),
                volume_24h_usd=float(yozuv["quote"]["USD"].get("volume_24h") or 0),
            )
            for index, yozuv in enumerate(yozuvlar)
        ]
        logger.info("CoinMarketCap reytingi olindi: %d ta coin", len(natija))
        return natija

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()


class CoinGeckoRanking(RankingProvider):
    """Zaxira manba — API kaliti talab qilmaydi."""

    #: Bitta so'rovda qaytadigan eng ko'p yozuv (CoinGecko cheklovi)
    PER_PAGE_MAX = 250
    #: Cheksiz aylanishdan himoya
    MAX_PAGES = 10

    def __init__(self, config: MarketDataConfig) -> None:
        self._config = config
        self._session = None

    async def _get_session(self):  # noqa: ANN202
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def fetch_ranking(self, limit: int) -> list[MarketRankEntry]:
        """Reytingni sahifalab yuklaydi.

        CoinGecko bitta so'rovda ko'pi bilan `PER_PAGE_MAX` ta yozuv
        qaytaradi. Ilgari kod `min(limit, 250)` deb yozardi va faqat
        birinchi sahifani so'rardi — ya'ni 500 ta so'ralsa ham 250 tasi
        kelardi, JIMGINA. Skanerlash chuqurligini oshirish hech qanday
        ta'sir bermasdi va buni bilish ham qiyin edi: xato yo'q, log
        ham "250 ta coin olindi" deb yozardi.
        """
        session = await self._get_session()
        natija: list[MarketRankEntry] = []

        for sahifa in range(1, self.MAX_PAGES + 1):
            qolgan = limit - len(natija)
            if qolgan <= 0:
                break
            xom = await self._fetch_page(session, sahifa, min(qolgan, self.PER_PAGE_MAX))
            if not xom:
                break
            natija.extend(self._parse(xom, len(natija)))
            if len(xom) < self.PER_PAGE_MAX:
                break  # oxirgi sahifa

        if not natija:
            raise RankingUnavailableError("CoinGecko bo'sh ro'yxat qaytardi")

        logger.info("CoinGecko reytingi olindi: %d ta coin (so'ralgan: %d)", len(natija), limit)
        return natija

    async def _fetch_page(self, session, page: int, per_page: int) -> list[dict]:  # noqa: ANN001
        url = f"{self._config.coingecko_base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": str(per_page),
            "page": str(page),
        }
        async with session.get(url, params=params) as javob:
            if javob.status != 200:
                raise RankingUnavailableError(f"CoinGecko javobi: {javob.status}")
            return await javob.json()

    @staticmethod
    def _parse(raw: list[dict], offset: int) -> list[MarketRankEntry]:
        return [
            MarketRankEntry(
                rank=yozuv.get("market_cap_rank") or offset + index + 1,
                symbol=yozuv["symbol"].upper(),
                name=yozuv.get("name", yozuv["symbol"]),
                market_cap_usd=float(yozuv.get("market_cap") or 0),
                volume_24h_usd=float(yozuv.get("total_volume") or 0),
            )
            for index, yozuv in enumerate(raw)
        ]

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()


class FallbackRanking(RankingProvider):
    """Asosiy manba ishlamasa zaxiraga o'tadi.

    Ikkalasi ham ishlamasa `RankingUnavailableError` ko'tariladi — chaqiruvchi
    eski, tasdiqlangan halol ro'yxat bilan davom etadi.
    """

    def __init__(self, primary: RankingProvider, fallback: RankingProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    async def fetch_ranking(self, limit: int) -> list[MarketRankEntry]:
        try:
            return await self._primary.fetch_ranking(limit)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Asosiy reyting manbai ishlamadi (%s) — zaxiraga o'tamiz", exc)
            return await self._fallback.fetch_ranking(limit)


def build_ranking_provider(config: MarketDataConfig) -> RankingProvider:
    """Konfiguratsiyaga qarab reyting manbaini quradi."""
    cmc = CoinMarketCapRanking(config)
    gecko = CoinGeckoRanking(config)

    if config.ranking_source == "coinmarketcap":
        if not cmc.is_configured:
            logger.warning(
                "%s o'rnatilmagan — reyting uchun CoinGecko ishlatiladi", CMC_API_KEY_ENV
            )
            return gecko
        return FallbackRanking(cmc, gecko)
    return gecko
