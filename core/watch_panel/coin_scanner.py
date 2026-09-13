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
from core.analysis.fundamental.catalyst_watch import Katalizator
from core.analysis.fundamental.fundamental_block import FundamentalKirish, TokenUnlock
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
from core.watch_panel.fundamental_manba import (
    BozorKayfiyati,
    FundamentalManba,
    SektorJadvali,
)
from core.watch_panel.repository import KuzatuvRepository
from core.watch_panel.top20_selector import Royxatlar, royxatlarni_qur
from core.watch_panel.unlock_manba import UnlockHodisasi, UnlockManba

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
        # UNLOCK KALENDARI — boshqa manba (DefiLlama), shuning uchun
        # alohida obyekt. Bu `katalizator` tekshiruvini va uning
        # qattiq to'sig'ini jonlantiradi.
        self._unlock = UnlockManba()

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
        sektor = await self._fundamental.sektor_jadvali()
        unlock = await self._unlock.jadval()
        logger.info(
            "Fundamental: F&G=%s, stablecoin=%s%%, funding=%d juftlik, "
            "sektor=%d kategoriya (bozor %s%%), unlock=%d coin",
            kayfiyat.fear_greed,
            kayfiyat.stablecoin_ozgarish_pct,
            len(funding),
            len(sektor.ozgarishlar),
            sektor.bozor_ozgarish,
            len(unlock),
        )
        # XARITANI TUZATISH UCHUN. Kategoriya identifikatori
        # javobda topilmasa, o'sha coinlar sektor ma'lumotisiz
        # qoladi. Admin buni logdan ko'radi va
        # `sektor_xaritasi.py` dagi qatorni to'g'rilaydi.
        if sektor.nomalum_idlar:
            logger.warning(
                "Sektor xaritasi: javobda topilmagan identifikatorlar: %s",
                ", ".join(sektor.nomalum_idlar),
            )

        yolak = asyncio.Semaphore(BIR_VAQTDA)

        async def bitta(symbol: str) -> KuzatuvNatija | None:
            async with yolak:
                try:
                    return await self._coinni_bahola(
                        symbol, btc, tf, kayfiyat, funding, sektor, unlock
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
        sektor: SektorJadvali,
        unlock: dict[str, UnlockHodisasi],
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
                fundamental=await self._fundamental_kirish(
                    symbol, kayfiyat, funding, sektor, unlock
                ),
                etalon=symbol == "BTC",
                timeframelar=tf,
                unlock_yaqin_kun=self._config.zanjir.bloklar.unlock_yaqin_kun,
                unlock_katta_pct=self._config.zanjir.bloklar.unlock_katta_pct,
            )
        )

    async def _fundamental_kirish(  # noqa: PLR0913 — har biri alohida manba
        self,
        symbol: str,
        kayfiyat: BozorKayfiyati,
        funding: dict[str, float],
        sektor: SektorJadvali,
        unlock: dict[str, UnlockHodisasi],
    ) -> FundamentalKirish:
        """Jonli fundamental ma'lumotni blok kutgan shaklga soladi.

        ULANMAGAN MANBALAR `None` BO'LIB QOLADI (netflow,
        yangiliklar, delisting). Ular tekshiruvda MALUMOT_YOQ
        beradi — "yo'q" EMAS — va maxrajga kirmaydi.

        UNLOCK IKKI JOYGA BERILADI, va bu takror EMAS:

            `voqea`  — ichki tekshiruvning OVOZI (unlock yaqinmi)
            `unlock` — QATTIQ TO'SIQ, chegaralari sozlamadan

        Ikkinchisi birinchisidan kuchliroq: u coinni butunlay
        chetlatadi. Sabab bir xil bo'lgani uchun blok ularni
        ikki marta hisoblamaydi (`fundamental_blok` da `or`).
        """
        juft = to_binance_symbol(symbol, self._config.halal_screening.quote_asset).upper()
        hodisa = unlock.get(symbol.upper())
        return FundamentalKirish(
            holat=BozorHolati(
                funding_rate=funding.get(juft),
                oi_ozgarish_pct=await self._fundamental.oi_ozgarishi(juft),
            ),
            oqim=PulOqimi(
                stablecoin_ozgarish_pct=kayfiyat.stablecoin_ozgarish_pct,
            ),
            voqea=Katalizator(
                unlock_kun=hodisa.kun_qoldi if hodisa else None,
                unlock_ulush_pct=hodisa.pct if hodisa else None,
            ),
            kayf=Kayfiyat(
                fear_greed=kayfiyat.fear_greed,
                sektor_kuchli=sektor.kuchli(symbol),
            ),
            unlock=(
                TokenUnlock(
                    kun_qoldi=hodisa.kun_qoldi,
                    pct=hodisa.pct,
                    izoh=hodisa.izoh,
                )
                if hodisa
                else None
            ),
        )

    async def _shamlar(self, symbol: str, timeframe: str) -> list[Candle]:
        return await self._provider.fetch_candles(symbol, timeframe, OYNA)

    async def yop(self) -> None:
        await self._fundamental.yop()
        await self._unlock.yop()
