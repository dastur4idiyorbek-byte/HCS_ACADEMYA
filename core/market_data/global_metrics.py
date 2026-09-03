"""Bozor kesimlari — TOTAL, ustunliklar va hosilalari.

FAQAT SAYT UCHUN. Loyiha egasining sharti: haftalik va kunlik
qarash signalga bog'lanmaydi, asosiy tahlil 4 soatlikda qoladi.

NIMA UCHUN ALOHIDA MODUL. Bu qiymatlar birjadan SHAM sifatida
kelmaydi — manba faqat hozirgi holatni beradi. Shuning uchun
ular har kuni saqlanadi va tarix o'zimizda yig'iladi
(`BozorKesimiRepository`).

MANBA: CoinGecko `/global` — kalit talab qilmaydi. BTC
dominance uchun loyihada allaqachon CoinMarketCap bor
(`dominance.py`), lekin u faqat BTC ni beradi va kalit talab
qiladi. Bu yerda oltita kesim kerak.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config.schema import MarketDataConfig
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class BozorKesimlari:
    """Bir lahzadagi oltita kesim.

    `others` — top 10 dan tashqaridagi kapitalizatsiya. U reyting
    ma'lumotisiz hisoblanmaydi, shuning uchun `None` bo'lishi
    mumkin: ma'lumot yo'qligi yashirilmaydi.
    """

    total: float
    btc_d: float
    eth_d: float
    usdt_d: float
    total2: float
    total3: float
    others: float | None = None

    def kesimlar(self) -> dict[str, float]:
        """Saqlanadigan kod → qiymat jadvali."""
        natija = {
            "TOTAL": self.total,
            "BTC.D": self.btc_d,
            "USDT.D": self.usdt_d,
            "TOTAL2": self.total2,
            "TOTAL3": self.total3,
        }
        if self.others is not None:
            natija["OTHERS"] = self.others
        return natija


class CoinGeckoGlobalMetrics:
    """`/global` — umumiy kapitalizatsiya va ustunlik foizlari."""

    def __init__(self, config: MarketDataConfig) -> None:
        self._config = config
        self._session = None

    async def _get_session(self):  # noqa: ANN202
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def fetch(self, top10_market_cap: float | None = None) -> BozorKesimlari | None:
        """Kesimlarni oladi. Olinmasa `None` — hech narsa to'xtamaydi.

        Args:
            top10_market_cap: eng yirik 10 coinning jami
                kapitalizatsiyasi. Berilsa `OTHERS` hisoblanadi
                (TradingView'dagi ta'rif: top 10 dan tashqarisi).
                Berilmasa `OTHERS` bo'sh qoladi — taxmin
                qilinmaydi.
        """
        url = f"{self._config.coingecko_base_url}/global"
        try:
            session = await self._get_session()
            async with session.get(url) as javob:
                if javob.status != 200:
                    logger.warning("Bozor kesimlari olinmadi (%s)", javob.status)
                    return None
                tana = await javob.json()
        except Exception:  # noqa: BLE001 — tarmoq xatosi siklni to'xtatmasin
            logger.warning("Bozor kesimlari so'rovi bajarilmadi", exc_info=True)
            return None

        return _parse(tana, top10_market_cap)

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()


def _parse(payload: dict, top10_market_cap: float | None) -> BozorKesimlari | None:
    """Javobdan kesimlarni hisoblaydi.

    TOTAL2 va TOTAL3 — hosilalar, ular manbadan kelmaydi:

        TOTAL2 = TOTAL × (1 − BTC.D)
        TOTAL3 = TOTAL × (1 − BTC.D − ETH.D)

    Bu ta'riflar TradingView'dagi bilan bir xil.
    """
    data = payload.get("data")
    if not isinstance(data, dict):
        logger.warning("Bozor kesimlari javobi kutilgan shaklda emas")
        return None

    kapitalizatsiya = (data.get("total_market_cap") or {}).get("usd")
    ulushlar = data.get("market_cap_percentage") or {}
    btc = ulushlar.get("btc")
    eth = ulushlar.get("eth")
    usdt = ulushlar.get("usdt")

    if not isinstance(kapitalizatsiya, int | float) or kapitalizatsiya <= 0:
        logger.warning("Umumiy kapitalizatsiya topilmadi")
        return None
    if not isinstance(btc, int | float) or not isinstance(eth, int | float):
        logger.warning("Ustunlik foizlari topilmadi")
        return None

    total = float(kapitalizatsiya)
    btc_d = float(btc)
    eth_d = float(eth)
    # USDT ustunligi ba'zan ro'yxatga tushmaydi — nol emas, YO'Q
    # deb belgilanadi va qator umuman chiqmaydi.
    usdt_d = float(usdt) if isinstance(usdt, int | float) else 0.0

    others = None
    if top10_market_cap is not None and top10_market_cap > 0:
        others = max(0.0, total - top10_market_cap)

    return BozorKesimlari(
        total=total,
        btc_d=btc_d,
        eth_d=eth_d,
        usdt_d=usdt_d,
        total2=total * (1 - btc_d / 100),
        total3=total * (1 - (btc_d + eth_d) / 100),
        others=others,
    )
