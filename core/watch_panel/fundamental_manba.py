"""Fundamental blok uchun JONLI ma'lumot manbalari.

--------------------------------------------------------------------
NEGA BU MODUL ENDI YOZILDI
--------------------------------------------------------------------

`docs/FUNDAMENTAL_MALUMOT_MANBALARI.md` 2026-09 da shunday xulosa
qilgan: "1-blokni qurib bo'ladi, lekin uni O'LCHAB bo'lmaydi".

O'sha xulosa TO'G'RI — lekin u BACKTEST haqida. Ablatsiya va
walk-forward ikki yillik tarix talab qiladi, va Open Interest,
sektor rotatsiyasi, yangiliklar kabi manbalarda bunday tarix yo'q.

Kuzatuv paneli esa:

    - backtest QILMAYDI
    - savdo qarori QABUL QILMAYDI
    - faqat HOZIRGI holatni ko'rsatadi

Ya'ni unga tarix umuman kerak emas — faqat "hozir nima bo'lyapti"
kerak. Shu sababli bu yerda o'sha manbalarni ishlatish mumkin, va
bu hujjatdagi xulosaga ZID EMAS: chegara "o'lchash" bilan
"ko'rsatish" orasida.

--------------------------------------------------------------------
NIMA ULANDI, NIMA YO'Q
--------------------------------------------------------------------

    ✅ Fear & Greed        alternative.me        kalitsiz, bepul
    ✅ Funding Rate        Binance futures       kalitsiz, BITTA so'rov
    ✅ Open Interest       Binance futures       kalitsiz, coin boshiga
    ✅ Stablecoin zaxira   CoinGecko             kalitsiz
    ✅ Sektor rotatsiyasi  CoinGecko categories  kalitsiz, BITTA so'rov
    ✅ Token Unlock        DefiLlama             `unlock_manba.py`

    ❌ Exchange Netflow    CryptoQuant/Glassnode — PULLIK
    ❌ Yangiliklar         CryptoPanic           — bepul planda deyarli yo'q
    ❌ Delisting           tarixiy/jonli API yo'q

Ulanmaganlari `None` bo'lib qoladi va tekshiruvda MALUMOT_YOQ
beradi — "yo'q" EMAS. Bu `turlar.py` dagi tamoyil: bilmaslik
salbiy javob emas va maxrajga kirmaydi.

--------------------------------------------------------------------

MANBA YIQILSA — HECH NARSA TO'XTAMAYDI. Har bir so'rov alohida
o'raladi; biri javob bermasa qolgani ishlaydi va o'sha ko'rsatkich
`None` bo'ladi.

QAT'IY CHEGARA: bu faylda Entry/Stop/TP hisoblanmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config.schema import MarketDataConfig
from core.utils.logging_setup import get_logger
from core.watch_panel.sektor_xaritasi import SEKTOR, slug

logger = get_logger(__name__)

SOROV_KUTISH = 15.0

#: Fear & Greed indeksi — kalit talab qilmaydi.
FNG_MANZIL = "https://api.alternative.me/fng/?limit=1&format=json"

#: Binance futures — kalitsiz, ochiq.
#:
#: `premiumIndex` symbolsiz chaqirilsa BARCHA juftlikni bitta
#: javobda beradi. 80 coin uchun 80 ta so'rov o'rniga bittasi.
FUNDING_MANZIL = "https://fapi.binance.com/fapi/v1/premiumIndex"
OI_MANZIL = "https://fapi.binance.com/futures/data/openInterestHist"

#: Stablecoin zaxirasi — USDT va USDC birgalikda.
#:
#: Ularning kapitalizatsiyasi o'ssa, bozorga yangi pul kirgan
#: degani: stablecoin sotib olingan, lekin hali coinlarga
#: o'tmagan — "quruq porox".
STABLECOIN_IDLARI = "tether,usd-coin"

#: Sektor rotatsiyasi — kategoriya natijalari va bozor etaloni.
#:
#: `/coins/categories` BARCHA kategoriyani bitta javobda beradi,
#: `/global` esa butun bozorning sutkalik o'zgarishini. Ikkalasi
#: ham skanda BIR MARTA so'raladi.
#:
#: NEGA 24 SOAT, 7 KUN EMAS. `Kayfiyat.sektor_kuchli` izohida "7
#: kun" yozilgan, lekin CoinGecko bepul kategoriya endpointida
#: FAQAT sutkalik o'zgarish bor. 7 kunlikni olish uchun har
#: kategoriya bo'yicha tarix kerak — bu o'nlab so'rov. Panel
#: "hozir pul qayerga oqyapti" degan savolga javob bergani uchun
#: sutkalik oyna yetarli; farq shu yerda ochiq yozildi.
KATEGORIYA_YOLI = "/coins/categories"
GLOBAL_YOLI = "/global"


#: OI o'zgarishi necha kunlik oynada o'lchanadi.
#:
#: 🔴 O'LCHANMAGAN. 7 kun — haftalik gorizont, panelning 4 soatlik
#: skani uchun oraliq qiymat. Panel qaror qabul qilmagani uchun bu
#: raqam pulga ta'sir qilmaydi (`GIPOTEZA_DAFTARI.md`).
OI_OYNA_KUN = 7


@dataclass(frozen=True, slots=True)
class BozorKayfiyati:
    """Butun bozorga tegishli ko'rsatkichlar — bir marta olinadi.

    Coin boshiga so'ralmaydi: Fear & Greed butun bozor uchun bitta
    raqam, stablecoin zaxirasi ham shunday.
    """

    fear_greed: int | None = None
    stablecoin_ozgarish_pct: float | None = None


@dataclass(frozen=True, slots=True)
class SektorJadvali:
    """Kategoriya natijalari + bozor etaloni.

    "Sektor kuchli" = shu kategoriya butun bozordan tez o'sgan.
    Mutlaq o'sish emas, NISBIY: hamma narsa 5% o'sgan kunda 3%
    o'sgan sektor aslida orqada qolgan.
    """

    ozgarishlar: dict[str, float]
    bozor_ozgarish: float | None

    def kuchli(self, symbol: str) -> bool | None:
        """Coin sektori bozordan kuchliroqmi. Bilmasak — `None`."""
        kategoriya = SEKTOR.get(symbol.upper())
        if kategoriya is None or self.bozor_ozgarish is None:
            return None
        sektor = self.ozgarishlar.get(kategoriya)
        if sektor is None:
            return None
        return sektor > self.bozor_ozgarish

    @property
    def nomalum_idlar(self) -> tuple[str, ...]:
        """Xaritada bor, lekin javobda topilmagan kategoriyalar.

        MANBA YIQILGANDA BO'SH QAYTADI. Aks holda so'rov javob
        bermagan paytda log "hamma identifikator xato" deb
        yozardi — aslida xarita joyida, tarmoq yo'q edi.
        """
        if not self.ozgarishlar:
            return ()
        return tuple(sorted({k for k in SEKTOR.values() if k not in self.ozgarishlar}))


class FundamentalManba:
    """Jonli fundamental ma'lumotni oladi."""

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

    async def _json(self, manzil: str, parametr: dict | None = None):  # noqa: ANN202
        """So'rov yuboradi. Xato bo'lsa `None` — panel to'xtamaydi."""
        try:
            sessiya = await self._sessiya()
            async with sessiya.get(
                manzil, params=parametr, timeout=SOROV_KUTISH
            ) as javob:
                if javob.status != 200:
                    logger.warning("%s -> %s", manzil, javob.status)
                    return None
                return await javob.json(content_type=None)
        except Exception:  # noqa: BLE001 — manba yo'qligi panelni to'xtatmasin
            logger.exception("Fundamental manba so'rovi yiqildi: %s", manzil)
            return None

    # ----------------------------------------------------------------- #
    #  Butun bozor
    # ----------------------------------------------------------------- #

    async def bozor_kayfiyati(self) -> BozorKayfiyati:
        """Fear & Greed va stablecoin zaxirasi — skanda BIR MARTA."""
        return BozorKayfiyati(
            fear_greed=await self._fear_greed(),
            stablecoin_ozgarish_pct=await self._stablecoin_ozgarishi(),
        )

    async def _fear_greed(self) -> int | None:
        malumot = await self._json(FNG_MANZIL)
        if not isinstance(malumot, dict):
            return None
        qatorlar = malumot.get("data")
        if not isinstance(qatorlar, list) or not qatorlar:
            return None
        try:
            return int(qatorlar[0]["value"])
        except (KeyError, TypeError, ValueError):
            return None

    async def _stablecoin_ozgarishi(self) -> float | None:
        """USDT + USDC KAPITALIZATSIYASINING 7 kunlik o'zgarishi (%).

        NIMA UCHUN `market_chart`, `coins/markets` EMAS.

        Birinchi yozuvda CoinGecko ning NARX o'zgarishi maydoni
        ishlatilgan edi. U stablecoinda deyarli har doim ~0% —
        chunki bu NARX o'zgarishi, va stablecoinning narxi ta'rifi
        bo'yicha $1 atrofida turadi. Ya'ni tekshiruv abadiy
        "o'zgarish yo'q" deb turaverardi va hech narsani
        o'lchamasdi.

        Bizga kerak bo'lgan narsa — KAPITALIZATSIYA o'zgarishi: u
        yangi pul chiqarilganini bildiradi. `coins/markets` da
        kapitalizatsiya uchun faqat 24 soatlik maydon bor, 7
        kunlik esa yo'q. `market_chart` tarixni beradi va undan
        aniq 7 kunlik farqni hisoblash mumkin.

        IKKALASI QO'SHILADI, o'rtachasi olinmaydi: USDT USDC dan
        bir necha barobar katta va oddiy o'rtacha kichikroqning
        shovqinini haddan tashqari kuchaytirardi.
        """
        boshi = 0.0
        oxiri = 0.0
        for coin_id in STABLECOIN_IDLARI.split(","):
            juft = await self._market_chart(coin_id)
            if juft is None:
                continue
            avval, hozir = juft
            boshi += avval
            oxiri += hozir

        if boshi <= 0:
            return None
        return round(100.0 * (oxiri - boshi) / boshi, 3)

    async def _market_chart(self, coin_id: str) -> tuple[float, float] | None:
        """Coinning 7 kun oldingi va hozirgi kapitalizatsiyasi."""
        malumot = await self._json(
            f"{self._config.coingecko_base_url}/coins/{coin_id}/market_chart",
            {"vs_currency": "usd", "days": "7", "interval": "daily"},
        )
        if not isinstance(malumot, dict):
            return None
        qatorlar = malumot.get("market_caps")
        if not isinstance(qatorlar, list) or len(qatorlar) < 2:
            return None
        try:
            avval = float(qatorlar[0][1])
            hozir = float(qatorlar[-1][1])
        except (IndexError, TypeError, ValueError):
            return None
        return (avval, hozir) if avval > 0 else None

    # ----------------------------------------------------------------- #
    #  Coin boshiga
    # ----------------------------------------------------------------- #

    async def funding_jadvali(self) -> dict[str, float]:
        """BARCHA juftlikning funding rate'i — BITTA so'rovda.

        Kalit — `BTCUSDT` ko'rinishidagi Binance symbol.
        """
        malumot = await self._json(FUNDING_MANZIL)
        if not isinstance(malumot, list):
            return {}

        jadval: dict[str, float] = {}
        for qator in malumot:
            if not isinstance(qator, dict):
                continue
            symbol = qator.get("symbol")
            stavka = qator.get("lastFundingRate")
            if not isinstance(symbol, str):
                continue
            try:
                jadval[symbol.upper()] = float(stavka)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
        return jadval

    async def oi_ozgarishi(self, binance_symbol: str) -> float | None:
        """Open Interest necha foiz o'zgargan (`OI_OYNA_KUN` kunda).

        Binance bu ma'lumotni FAQAT 30 kunga beradi — backtest uchun
        yaroqsiz, lekin "hozir nima bo'lyapti" uchun yetarli.

        Futures bozori yo'q coin uchun javob bo'sh bo'ladi va
        `None` qaytadi — bu XATO EMAS: spot-only coinlar bor.
        """
        malumot = await self._json(
            OI_MANZIL,
            {
                "symbol": binance_symbol.upper(),
                "period": "1d",
                "limit": str(OI_OYNA_KUN + 1),
            },
        )
        if not isinstance(malumot, list) or len(malumot) < 2:
            return None

        try:
            avval = float(malumot[0]["sumOpenInterestValue"])
            hozir = float(malumot[-1]["sumOpenInterestValue"])
        except (KeyError, IndexError, TypeError, ValueError):
            return None
        if avval <= 0:
            return None
        return round(100.0 * (hozir - avval) / avval, 2)

    # ----------------------------------------------------------------- #
    #  Sektor rotatsiyasi
    # ----------------------------------------------------------------- #

    async def sektor_jadvali(self) -> SektorJadvali:
        """Kategoriya natijalari — skanda BIR MARTA, ikkita so'rov."""
        return SektorJadvali(
            ozgarishlar=await self._kategoriyalar(),
            bozor_ozgarish=await self._bozor_ozgarishi(),
        )

    async def _kategoriyalar(self) -> dict[str, float]:
        """Kategoriya -> sutkalik o'zgarish (%).

        Kalit sifatida `id` ham, nomdan yasalgan slug ham
        yoziladi: CoinGecko ba'zi kategoriyalarni nomi bilan
        ataydi va xaritadagi qator faqat biriga tushishi mumkin.
        """
        malumot = await self._json(
            f"{self._config.coingecko_base_url}{KATEGORIYA_YOLI}"
        )
        if not isinstance(malumot, list):
            return {}

        jadval: dict[str, float] = {}
        for qator in malumot:
            if not isinstance(qator, dict):
                continue
            try:
                ozgarish = float(qator["market_cap_change_24h"])
            except (KeyError, TypeError, ValueError):
                continue
            for maydon in ("id", "name"):
                qiymat = qator.get(maydon)
                if isinstance(qiymat, str) and qiymat.strip():
                    jadval.setdefault(slug(qiymat), ozgarish)
        return jadval

    async def _bozor_ozgarishi(self) -> float | None:
        """Butun bozor kapitalizatsiyasining sutkalik o'zgarishi (%)."""
        malumot = await self._json(f"{self._config.coingecko_base_url}{GLOBAL_YOLI}")
        if not isinstance(malumot, dict):
            return None
        ichki = malumot.get("data")
        if not isinstance(ichki, dict):
            return None
        try:
            return float(ichki["market_cap_change_percentage_24h_usd"])
        except (KeyError, TypeError, ValueError):
            return None
