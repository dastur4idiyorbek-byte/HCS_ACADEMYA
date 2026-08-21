"""BTC Dominance manbai — Bozor Salomatligi indeksining 1-omili (3.7-band).

Nima uchun alohida modul: dominance reyting bilan bir xil manbadan
(CoinMarketCap) keladi, lekin BOSHQA endpoint'dan va boshqa maqsadda.
Reyting 12 soatda bir marta kerak, dominance esa har siklda.

Ma'lumot olinmasa `None` qaytadi — chaqiruvchi buni "omil hisoblanmadi"
deb qabul qiladi va tizim to'xtamaydi (0.3-band).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from core.config.schema import MarketDataConfig
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

CMC_API_KEY_ENV = "CMC_API_KEY"


@dataclass(frozen=True, slots=True)
class DominanceSnapshot:
    """BTC dominance va uning sutkalik o'zgarishi.

    Attributes:
        value: hozirgi dominance foizi (masalan 54.2).
        change_24h: sutkalik o'zgarish FOIZ PUNKTLARIDA (masalan -1.8).
            Manba bermasa `None` — omil buni hisobga oladi.
    """

    value: float
    change_24h: float | None = None


class CoinMarketCapDominance:
    """CoinMarketCap `/global-metrics/quotes/latest`.

    Bepul (Basic) reja oyiga 10 000 so'rov beradi. Sikl 15 daqiqada bir
    marta ishlasa — kuniga 96 so'rov, oyiga ~2 900. Bepul rejaga sig'adi.
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

    async def fetch(self) -> DominanceSnapshot | None:
        """Hozirgi dominance. Olinmasa `None` — sikl to'xtamaydi.

        Hech qanday istisno tashqariga chiqmaydi: bu omil indeksning
        beshdan biri, lekin uning yo'qligi butun siklni to'xtatmasligi
        kerak (0.3-band).
        """
        if not self.is_configured:
            return None

        url = f"{self._config.coinmarketcap_base_url}/global-metrics/quotes/latest"
        try:
            session = await self._get_session()
            async with session.get(url) as javob:
                if javob.status != 200:
                    matn = await javob.text()
                    logger.warning(
                        "BTC dominance olinmadi (%s): %s", javob.status, matn[:200]
                    )
                    return None
                tana = await javob.json()
        except Exception:  # noqa: BLE001 — tarmoq xatosi siklni to'xtatmasin
            logger.warning("BTC dominance so'rovi bajarilmadi", exc_info=True)
            return None

        return _parse(tana)

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()


#: Sutkalik o'zgarish uchun mumkin bo'lgan maydon nomlari. CMC bu maydonni
#: har doim ham qaytarmaydi va nomini o'zgartirgan — shuning uchun bir
#: nechtasi sinab ko'riladi, topilmasa `None` (omil buni hisobga oladi).
_CHANGE_KEYS = (
    "btc_dominance_24h_percentage_change",
    "btc_dominance_24h_change",
)


def _parse(payload: dict) -> DominanceSnapshot | None:
    """Javobdan dominance ajratadi. Shakl kutilganidan boshqa bo'lsa `None`."""
    data = payload.get("data")
    if not isinstance(data, dict):
        logger.warning("BTC dominance javobi kutilgan shaklda emas")
        return None

    qiymat = data.get("btc_dominance")
    if not isinstance(qiymat, int | float):
        logger.warning("BTC dominance qiymati topilmadi")
        return None

    ozgarish = None
    for kalit in _CHANGE_KEYS:
        nomzod = data.get(kalit)
        if isinstance(nomzod, int | float):
            ozgarish = float(nomzod)
            break

    return DominanceSnapshot(value=float(qiymat), change_24h=ozgarish)
