"""80 coinni skanlaydi — 1-qism modullarini chaqiradi, SIGNAL BERMAYDI.

ISHLASH TARTIBI:

    1. BTC shamlarini bir marta yuklaydi (nisbiy kuch uchun etalon)
    2. Har coin uchun uch timeframe: 4h, 1h, 15m
    3. Rejim B (`observation_mode.kuzatuv_yur`) bilan baholaydi
    4. Saralaydi (`top20_selector`) va bazaga yozadi

FILTR BIRINCHI — RESURS TEJASH. Downtrend coin uchun 1h va 15m
shamlar UMUMAN so'ralmaydi: u baribir ro'yxatga kirmaydi. 80
coinning yarmi tushayotgan bo'lsa, bu yuzlab API so'rovini
tejaydi.

XATO BITTA COINNI YIQITADI, BUTUN SKANNI EMAS. Birja bitta coin
uchun javob bermasa, qolgan 79 tasi baribir tekshiriladi. Aks
holda bitta nosoz symbol butun panelni bo'sh qoldirardi.

QAT'IY CHEGARA: bu faylda Entry/Stop/TP hisoblanmaydi.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from core.analysis.fundamental.capital_flow import PulOqimi
from core.analysis.fundamental.fundamental_block import FundamentalKirish
from core.analysis.fundamental.market_regime import BozorHolati
from core.analysis.fundamental.sentiment_sector import Kayfiyat
from core.analysis.observation_mode import (
    KuzatuvKirish,
    KuzatuvNatija,
    Timeframelar,
    kuzatuv_yur,
)
from core.config.schema import AppConfig
from core.domain.models import Candle
from core.market_data.binance import BinanceCandleProvider, to_binance_symbol
from core.storage.database import Database
from core.utils.logging_setup import get_logger
from core.watch_panel.fundamental_manba import BozorKayfiyati, FundamentalManba
from core.watch_panel.repository import KuzatuvRepository
from core.watch_panel.top20_selector import Royxatlar, royxatlarni_qur

logger = get_logger(__name__)

#: Necha sham so'raladi.
#:
#: 200 — struktura uchun ham, zona uchun ham yetarli va Binance
#: bitta so'rovda beradigan miqdordan (1000) ancha past. Zanjir
#: siklidagi 500 dan kamroq: u yerda backtest bilan bir xil oyna
#: SHART edi, bu yerda esa hech narsa solishtirilmaydi.
OYNA = 200

#: Nechta coin bir vaqtda tekshiriladi.
#:
#: Birjaga bir zumda 80 ta so'rov yuborish — tezlik chegarasiga
#: urilishning eng oson yo'li. 5 ta yetarli: 80 coin ~16 to'lqinda
#: tugaydi va har biri bir necha yuz millisekund.
BIR_VAQTDA = 5


@dataclass
class SkanNatijasi:
    """Bitta yugurishning hisoboti."""

    tekshirildi: int = 0
    otdi: int = 0
    xatolar: dict[str, str] = field(default_factory=dict)
    royxatlar: Royxatlar | None = None


class KuzatuvSkaneri:
    """80 coinni kuzatadi. SIGNAL YOZMAYDI — faqat holat yozadi."""

    def __init__(
        self,
        config: AppConfig,
        provider: BinanceCandleProvider,
        database: Database,
    ) -> None:
        self._config = config
        self._provider = provider
        self._db = database
        # FUNDAMENTAL MANBA — jonli ma'lumot (funding, OI, F&G,
        # stablecoin). Blok endi bo'sh emas.
        self._fundamental = FundamentalManba(config.market_data)

    @property
    def _timeframelar(self) -> Timeframelar:
        return Timeframelar(
            struktura=self._config.kuzatuv.tf_struktura,
            zona=self._config.kuzatuv.tf_zona,
            pastki=self._config.kuzatuv.tf_pastki,
        )

    async def yur(self) -> SkanNatijasi:
        """Bitta to'liq skan."""
        natija = SkanNatijasi()
        tf = self._timeframelar
        coinlar = list(self._config.zanjir.kuzatiladigan_coinlar)

        btc = await self._shamlar("BTC", tf.struktura)
        if not btc:
            logger.warning("BTC shamlari olinmadi — nisbiy kuch hisoblanmaydi")

        # FUNDAMENTAL — skanda BIR MARTA olinadi.
        #
        # Fear & Greed va stablecoin zaxirasi butun bozorga tegishli;
        # funding rate esa Binance dan BITTA so'rovda hamma juftlik
        # uchun keladi. Coin boshiga so'rash 80 barobar ko'p so'rov
        # bo'lardi va javob AYNI bo'lardi.
        kayfiyat = await self._fundamental.bozor_kayfiyati()
        funding = await self._fundamental.funding_jadvali()
        logger.info(
            "Fundamental: F&G=%s, stablecoin=%s%%, funding jadvali=%d juftlik",
            kayfiyat.fear_greed,
            kayfiyat.stablecoin_ozgarish_pct,
            len(funding),
        )

        yolak = asyncio.Semaphore(BIR_VAQTDA)

        async def bitta(symbol: str) -> KuzatuvNatija | None:
            async with yolak:
                try:
                    return await self._coinni_bahola(
                        symbol, btc, tf, kayfiyat, funding
                    )
                except Exception as xato:  # noqa: BLE001 — bitta coin butun skanni yiqitmasin
                    logger.exception("Kuzatuv: %s tekshirilmadi", symbol)
                    natija.xatolar[symbol] = str(xato)
                    return None

        javoblar = await asyncio.gather(*(bitta(s) for s in coinlar))
        baholanganlar = [j for j in javoblar if j is not None]

        natija.tekshirildi = len(baholanganlar)
        royxatlar = royxatlarni_qur(baholanganlar)
        natija.otdi = royxatlar.jami_korinadi + max(
            0, len([b for b in baholanganlar if b.otdi]) - royxatlar.jami_korinadi
        )
        natija.royxatlar = royxatlar

        korinadigan = {id(n) for n in (*royxatlar.top, *royxatlar.kuzatuvda)}
        qolganlar = [n for n in baholanganlar if id(n) not in korinadigan]

        async with self._db.session() as session:
            await KuzatuvRepository(session).royxatlarni_yoz(royxatlar, qolganlar)

        logger.info(
            "Kuzatuv skani: %d coin, %d ta Top, %d ta kuzatuvda, %d xato",
            natija.tekshirildi,
            len(royxatlar.top),
            len(royxatlar.kuzatuvda),
            len(natija.xatolar),
        )
        return natija

    async def _coinni_bahola(  # noqa: PLR0913 — har biri alohida manba
        self,
        symbol: str,
        btc: list[Candle],
        tf: Timeframelar,
        kayfiyat: BozorKayfiyati,
        funding: dict[str, float],
    ) -> KuzatuvNatija:
        """Bitta coin. Filtrdan o'tmasa — pastki TF lar so'ralmaydi."""
        struktura = await self._shamlar(symbol, tf.struktura)

        # BIRINCHI O'TISH: faqat struktura bilan. Coin filtrdan
        # o'tmasa, 1h va 15m so'rovlari BEKORGA ketardi.
        oldindan = kuzatuv_yur(
            KuzatuvKirish(
                symbol=symbol,
                struktura_shamlar=struktura,
                btc_shamlar=btc,
                etalon=symbol == "BTC",
                timeframelar=tf,
            )
        )
        if not oldindan.otdi:
            return oldindan

        zona_shamlar, pastki_shamlar = await asyncio.gather(
            self._shamlar(symbol, tf.zona),
            self._shamlar(symbol, tf.pastki),
        )
        return kuzatuv_yur(
            KuzatuvKirish(
                symbol=symbol,
                struktura_shamlar=struktura,
                zona_shamlar=zona_shamlar,
                pastki_shamlar=pastki_shamlar,
                btc_shamlar=btc,
                fundamental=await self._fundamental_kirish(symbol, kayfiyat, funding),
                etalon=symbol == "BTC",
                timeframelar=tf,
                unlock_yaqin_kun=self._config.zanjir.bloklar.unlock_yaqin_kun,
                unlock_katta_pct=self._config.zanjir.bloklar.unlock_katta_pct,
            )
        )

    async def _fundamental_kirish(
        self, symbol: str, kayfiyat: BozorKayfiyati, funding: dict[str, float]
    ) -> FundamentalKirish:
        """Jonli fundamental ma'lumotni blok kutgan shaklga soladi.

        ULANMAGAN MANBALAR `None` BO'LIB QOLADI (netflow, sektor,
        yangiliklar, delisting). Ular tekshiruvda MALUMOT_YOQ
        beradi — "yo'q" EMAS — va maxrajga kirmaydi.
        """
        juft = to_binance_symbol(symbol, self._config.halal_screening.quote_asset).upper()
        return FundamentalKirish(
            holat=BozorHolati(
                funding_rate=funding.get(juft),
                oi_ozgarish_pct=await self._fundamental.oi_ozgarishi(juft),
            ),
            oqim=PulOqimi(
                stablecoin_ozgarish_pct=kayfiyat.stablecoin_ozgarish_pct,
            ),
            kayf=Kayfiyat(fear_greed=kayfiyat.fear_greed),
        )

    async def _shamlar(self, symbol: str, timeframe: str) -> list[Candle]:
        return await self._provider.fetch_candles(symbol, timeframe, OYNA)

    async def yop(self) -> None:
        await self._fundamental.yop()
