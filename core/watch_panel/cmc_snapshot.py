"""Kapitalizatsiya va sutkalik hajm — CoinGecko dan.

NEGA COINGECKO, CoinMarketCap EMAS. CMC kalit talab qiladi; bu
ma'lumot esa kalitsiz, bepul olinadi. Loyihada CMC ham bor
(`dominance.py`), lekin u faqat BTC ustunligini beradi va kalitga
bog'liq — kalit tugasa panel bo'sh qolardi.

MANBA YO'Q BO'LSA — HECH NARSA TO'XTAMAYDI. So'rov yiqilsa
`None` qaytadi va panel bu qatorlarni ko'rsatmaydi. Bozor
ma'lumoti — qo'shimcha, asosiy emas: struktura tahlili birjadan
mustaqil keladi.

QAT'IY CHEGARA: bu faylda Entry/Stop/TP hisoblanmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config.schema import MarketDataConfig
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Bitta so'rovda nechta coin. CoinGecko chegarasi — 250.
SAHIFA = 250

#: Nechta sahifa so'raladi.
#:
#: 2 sahifa = kapitalizatsiya bo'yicha eng katta 500 coin. Bizning
#: 80 talik ro'yxat butunlay shu ichida: undagi eng kichik coinlar
#: ham 500 talikdan chiqmaydi. Uchinchi sahifa so'rash — bekorga
#: so'rov.
SAHIFALAR = 2

SOROV_KUTISH = 15.0


@dataclass(frozen=True, slots=True)
class BozorSurati:
    """Bitta coinning bozor ko'rsatkichlari."""

    symbol: str
    narx: float | None
    market_cap: float | None
    hajm_24s: float | None
    ozgarish_1s: float | None
    ozgarish_24s: float | None
    ozgarish_7k: float | None


class CoinGeckoSurati:
    """Kapitalizatsiya ma'lumotini oladi."""

    def __init__(self, config: MarketDataConfig) -> None:
        self._config = config
        self._session = None

    async def _sessiya(self):  # noqa: ANN202
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def yop(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def ol(self, symbols: list[str]) -> dict[str, BozorSurati]:
        """Berilgan coinlar uchun surat. Xato bo'lsa — bo'sh lug'at."""
        kerak = {s.upper() for s in symbols}
        if not kerak:
            return {}

        natija: dict[str, BozorSurati] = {}
        for sahifa in range(1, SAHIFALAR + 1):
            qatorlar = await self._sahifa(sahifa)
            for qator in qatorlar:
                symbol = str(qator.get("symbol", "")).upper()
                if symbol not in kerak or symbol in natija:
                    continue
                natija[symbol] = BozorSurati(
                    symbol=symbol,
                    narx=_son(qator.get("current_price")),
                    market_cap=_son(qator.get("market_cap")),
                    hajm_24s=_son(qator.get("total_volume")),
                    ozgarish_1s=_son(qator.get("price_change_percentage_1h_in_currency")),
                    ozgarish_24s=_son(qator.get("price_change_percentage_24h_in_currency")),
                    ozgarish_7k=_son(qator.get("price_change_percentage_7d_in_currency")),
                )
            if len(natija) == len(kerak):
                break
        return natija

    async def _sahifa(self, sahifa: int) -> list[dict]:
        manzil = f"{self._config.coingecko_base_url}/coins/markets"
        parametr = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": str(SAHIFA),
            "page": str(sahifa),
            "price_change_percentage": "1h,24h,7d",
        }
        try:
            sessiya = await self._sessiya()
            async with sessiya.get(
                manzil, params=parametr, timeout=SOROV_KUTISH
            ) as javob:
                if javob.status != 200:
                    logger.warning(
                        "CoinGecko %s sahifa uchun %s qaytardi", sahifa, javob.status
                    )
                    return []
                malumot = await javob.json()
        except Exception:  # noqa: BLE001 — manba yo'qligi panelni to'xtatmasin
            logger.exception("CoinGecko so'rovi yiqildi (sahifa %s)", sahifa)
            return []
        return malumot if isinstance(malumot, list) else []


def _son(x: object) -> float | None:
    """Raqamga aylantiradi. Aylanmasa `None` — nol EMAS.

    Nol qaytarish "kapitalizatsiya nolga teng" degan yolg'on
    ma'no berardi; `None` esa "bilmayman" deydi va ekranda
    "ma'lumot yo'q" bo'lib chiqadi.
    """
    if x is None:
        return None
    try:
        return float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
