"""Binance Futures va CoinGecko mijozlari — bepul, kalitsiz.

MANBA YIQILSA SESSIYA TO'XTAMAYDI (ticker va juftliklardan tashqari:
ularsiz hech narsa hisoblab bo'lmaydi). Masalan funding kelmasa —
3-tekshiruv hamma coinda ⚪ bo'ladi, qolgan oltitasi ishlayveradi.

HAR MANBANING HOLATI YOZILADI (`ManbaJurnali`). Sahifa uni
ko'rsatadi. Eng muhim holat — 451: Binance server mintaqasini
cheklagan. Loyiha hujjatlarida bu GitHub serverlari uchun allaqachon
uchragan (`docs/ARXITEKTURA.md`); futures uchun zaxira domen yo'q.
Shuning uchun u jimgina "ma'lumot yo'q" bo'lib qolmasdan, ochiq
yoziladi.

SO'ROVLAR TEJAMKOR (`docs/MODUL_4_0_0.md`, 12-bo'lim): hamma symbol
uchun bitta ommaviy so'rov, coin boshiga so'rov esa faqat elakdan
o'tgan 20-30 tasiga.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from core.portlash_radari.belgi import KOTIROVKA, ajrat
from core.portlash_radari.vaqt import ms, ms_dan
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

OK = "ok"
XATO = "xato"


# --------------------------------------------------------------------- #
#  Manba holati
# --------------------------------------------------------------------- #


@dataclass
class ManbaHolati:
    holat: str = OK
    kod: int | None = 200
    izoh: str = ""
    #: Coin boshiga so'rovlar uchun: nechtasi o'tdi / jami
    otdi: int = 0
    jami: int = 0

    def lugat(self) -> dict:
        izoh = self.izoh
        if self.jami:
            izoh = (f"{self.otdi}/{self.jami} " + izoh).strip()
        return {"holat": self.holat, "kod": self.kod, "izoh": izoh}


@dataclass
class ManbaJurnali:
    """Sessiya davomida har manba qanday javob bergani."""

    manbalar: dict[str, ManbaHolati] = field(default_factory=dict)

    def yoz(self, nom: str, kod: int | None, izoh: str = "") -> None:
        ok = kod == 200
        self.manbalar[nom] = ManbaHolati(OK if ok else XATO, kod, izoh)

    def hisobla(self, nom: str, kod: int | None) -> None:
        """Coin boshiga so'rov: o'tganlar sanaladi, oxirgi xato kodi saqlanadi."""
        h = self.manbalar.setdefault(nom, ManbaHolati(OK, 200, ""))
        h.jami += 1
        if kod == 200:
            h.otdi += 1
        else:
            h.kod = kod
        # Yarmidan ko'pi yiqilsa — xato. Bitta-ikkita yo'q coin (masalan
        # yangi listingda OI tarixi hali yo'q) manbani "buzuq" qilmaydi.
        h.holat = OK if h.otdi * 2 >= h.jami else XATO

    def lugat(self) -> dict[str, dict]:
        return {nom: h.lugat() for nom, h in sorted(self.manbalar.items())}

    def cheklangan(self) -> bool:
        """Binance server mintaqasini cheklaganmi (451)."""
        return any(h.kod == 451 for h in self.manbalar.values())


# --------------------------------------------------------------------- #
#  Ma'lumot turlari
# --------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Juftlik:
    symbol: str
    #: Binance `baseAsset` (`1000PEPE`)
    asosiy: str
    #: Reestr va CoinGecko uchun (`PEPE`)
    belgi: str
    kopaytirgich: int
    onboard: datetime | None


@dataclass(frozen=True, slots=True)
class Ticker:
    narx: float | None
    ozgarish_24s: float | None
    #: Quote (USDT) hajmi — dollarda
    hajm_24s: float | None


@dataclass(frozen=True, slots=True)
class Sham:
    ochilish: datetime
    yuqori: float
    past: float
    yopilish: float


@dataclass(frozen=True, slots=True)
class Taminot:
    """CoinGecko dan — kapitalizatsiya va token ta'minoti."""

    market_cap: float | None
    narx: float | None
    muomalada: float | None
    jami: float | None
    maksimal: float | None

    @property
    def aylanma_pct(self) -> float | None:
        """Aylanmadagi / maksimal (maksimal yo'q bo'lsa — umumiy), %."""
        maxraj = self.maksimal or self.jami
        if self.muomalada is None or not maxraj or maxraj <= 0:
            return None
        return min(100.0 * self.muomalada / maxraj, 100.0)


def _son(x: object) -> float | None:
    """Raqamga aylantiradi. Aylanmasa `None` — nol EMAS (nol boshqa ma'no)."""
    if x is None or isinstance(x, bool):
        return None
    try:
        son = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return son if son == son else None  # NaN -> None


# --------------------------------------------------------------------- #
#  HTTP asosi
# --------------------------------------------------------------------- #


class _Http:
    def __init__(self, kutish: float) -> None:
        self._kutish = kutish
        self._session = None

    async def _sessiya(self):  # noqa: ANN202
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def yop(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def _json(self, manzil: str, parametr: dict | None = None) -> tuple[object, int | None]:
        """(javob, HTTP kod). Tarmoq xatosida kod `None`."""
        try:
            sessiya = await self._sessiya()
            async with sessiya.get(manzil, params=parametr, timeout=self._kutish) as javob:
                if javob.status != 200:
                    if javob.status == 451:
                        logger.error(
                            "%s -> 451: server mintaqasi Binance tomonidan cheklangan", manzil
                        )
                    else:
                        logger.warning("%s -> %s", manzil, javob.status)
                    return None, javob.status
                return await javob.json(content_type=None), 200
        except asyncio.CancelledError:
            raise
        except Exception as xato:  # noqa: BLE001 — manba yo'qligi sessiyani to'xtatmasin
            logger.warning("So'rov yiqildi: %s (%s)", manzil, xato)
            return None, None


# --------------------------------------------------------------------- #
#  Binance Futures
# --------------------------------------------------------------------- #


class BinanceFutures(_Http):
    """USDⓈ-M futures ochiq endpointlari."""

    def __init__(
        self,
        base_url: str,
        stablecoinlar: Iterable[str] = (),
        kutish: float = 15.0,
        parallel: int = 5,
    ) -> None:
        super().__init__(kutish)
        self._base = base_url.rstrip("/")
        self._stablecoin = {s.upper() for s in stablecoinlar}
        self._cheklov = asyncio.Semaphore(max(parallel, 1))

    async def juftliklar(self, jurnal: ManbaJurnali) -> list[Juftlik]:
        """USDT perpetual, savdoda, coin asosli — stablecoinlarsiz."""
        malumot, kod = await self._json(f"{self._base}/fapi/v1/exchangeInfo")
        jurnal.yoz("juftliklar", kod)
        return juftliklarni_ajrat(malumot, self._stablecoin)

    async def tickerlar(self, jurnal: ManbaJurnali) -> dict[str, Ticker]:
        malumot, kod = await self._json(f"{self._base}/fapi/v1/ticker/24hr")
        jurnal.yoz("ticker", kod)
        return tickerlarni_ajrat(malumot)

    async def funding_stavkalari(self, jurnal: ManbaJurnali) -> dict[str, float]:
        malumot, kod = await self._json(f"{self._base}/fapi/v1/premiumIndex")
        jurnal.yoz("funding", kod)
        return fundingni_ajrat(malumot)

    async def funding_oraliqlari(self, jurnal: ManbaJurnali) -> dict[str, int]:
        """`fundingInfo` FAQAT oralig'i o'zgartirilgan coinlarni qaytaradi —
        qolganlari 8 soat."""
        malumot, kod = await self._json(f"{self._base}/fapi/v1/fundingInfo")
        jurnal.yoz("funding_oraliq", kod)
        return oraliqlarni_ajrat(malumot)

    async def oi_tarixi(
        self, symbol: str, soat: int, jurnal: ManbaJurnali
    ) -> tuple[float, ...]:
        """So'nggi `soat` soatlik OI (kontrakt soni), eskidan yangiga."""
        async with self._cheklov:
            malumot, kod = await self._json(
                f"{self._base}/futures/data/openInterestHist",
                {"symbol": symbol, "period": "1h", "limit": str(soat + 1)},
            )
        jurnal.hisobla("oi", kod)
        return oi_ni_ajrat(malumot)

    async def long_short(self, symbol: str, jurnal: ManbaJurnali) -> float | None:
        async with self._cheklov:
            malumot, kod = await self._json(
                f"{self._base}/futures/data/globalLongShortAccountRatio",
                {"symbol": symbol, "period": "1h", "limit": "1"},
            )
        jurnal.hisobla("long_short", kod)
        return long_short_ni_ajrat(malumot)

    async def shamlar(
        self,
        symbol: str,
        interval: str,
        boshi: datetime | None = None,
        limit: int = 30,
        jurnal: ManbaJurnali | None = None,
    ) -> list[Sham] | None:
        """Shamlar. `None` — so'rov yiqildi (bo'sh ro'yxat esa — sham yo'q)."""
        parametr = {"symbol": symbol, "interval": interval, "limit": str(limit)}
        if boshi is not None:
            parametr["startTime"] = str(ms(boshi))
        async with self._cheklov:
            malumot, kod = await self._json(f"{self._base}/fapi/v1/klines", parametr)
        if jurnal is not None:
            jurnal.hisobla("shamlar", kod)
        if kod != 200:
            return None
        return shamlarni_ajrat(malumot)

    async def kunlik_ortacha(
        self, symbol: str, hozir: datetime, kun: int = 30
    ) -> tuple[float | None, int] | None:
        """Yopilgan kunlik shamlar quote hajmining o'rtachasi.

        BUGUNGI (yopilmagan) sham hisobga kirmaydi — u kun yarmida
        o'rtachani sun'iy pasaytirardi.
        """
        async with self._cheklov:
            malumot, kod = await self._json(
                f"{self._base}/fapi/v1/klines",
                {"symbol": symbol, "interval": "1d", "limit": str(kun + 1)},
            )
        if kod != 200 or not isinstance(malumot, list):
            return None
        return kunlik_ortachani_hisobla(malumot, hozir, kun)


def juftliklarni_ajrat(malumot: object, stablecoinlar: set[str]) -> list[Juftlik]:
    if not isinstance(malumot, dict):
        return []
    qatorlar = malumot.get("symbols")
    if not isinstance(qatorlar, list):
        return []
    natija: list[Juftlik] = []
    for q in qatorlar:
        if not isinstance(q, dict):
            continue
        if q.get("contractType") != "PERPETUAL" or q.get("quoteAsset") != KOTIROVKA:
            continue
        if q.get("status") != "TRADING":
            continue
        # Oltin, indeks, aksiya kabi coin bo'lmagan kontraktlar chiqariladi.
        # Maydon yo'q bo'lsa — eski javob shakli, coin deb olinadi.
        if q.get("underlyingType", "COIN") != "COIN":
            continue
        symbol = q.get("symbol")
        asosiy = q.get("baseAsset")
        if not isinstance(symbol, str) or not isinstance(asosiy, str) or not asosiy:
            continue
        belgi, kopaytirgich = ajrat(asosiy)
        if belgi in stablecoinlar:
            continue
        onboard_ms = _son(q.get("onboardDate"))
        natija.append(
            Juftlik(
                symbol=symbol.upper(),
                asosiy=asosiy.upper(),
                belgi=belgi,
                kopaytirgich=kopaytirgich,
                onboard=ms_dan(onboard_ms) if onboard_ms else None,
            )
        )
    return natija


def tickerlarni_ajrat(malumot: object) -> dict[str, Ticker]:
    if not isinstance(malumot, list):
        return {}
    natija: dict[str, Ticker] = {}
    for q in malumot:
        if not isinstance(q, dict) or not isinstance(q.get("symbol"), str):
            continue
        natija[q["symbol"].upper()] = Ticker(
            narx=_son(q.get("lastPrice")),
            ozgarish_24s=_son(q.get("priceChangePercent")),
            hajm_24s=_son(q.get("quoteVolume")),
        )
    return natija


def fundingni_ajrat(malumot: object) -> dict[str, float]:
    if not isinstance(malumot, list):
        return {}
    natija: dict[str, float] = {}
    for q in malumot:
        if not isinstance(q, dict) or not isinstance(q.get("symbol"), str):
            continue
        stavka = _son(q.get("lastFundingRate"))
        if stavka is not None:
            natija[q["symbol"].upper()] = stavka
    return natija


def oraliqlarni_ajrat(malumot: object) -> dict[str, int]:
    if not isinstance(malumot, list):
        return {}
    natija: dict[str, int] = {}
    for q in malumot:
        if not isinstance(q, dict) or not isinstance(q.get("symbol"), str):
            continue
        soat = _son(q.get("fundingIntervalHours"))
        if soat is not None and soat > 0:
            natija[q["symbol"].upper()] = int(soat)
    return natija


def oi_ni_ajrat(malumot: object) -> tuple[float, ...]:
    """`sumOpenInterest` — KONTRAKT SONI (dollar emas), vaqt bo'yicha tartiblab."""
    if not isinstance(malumot, list):
        return ()
    juftlar: list[tuple[float, float]] = []
    for q in malumot:
        if not isinstance(q, dict):
            continue
        vaqt = _son(q.get("timestamp"))
        oi = _son(q.get("sumOpenInterest"))
        if vaqt is not None and oi is not None:
            juftlar.append((vaqt, oi))
    return tuple(oi for _, oi in sorted(juftlar))


def long_short_ni_ajrat(malumot: object) -> float | None:
    if not isinstance(malumot, list) or not malumot:
        return None
    oxirgi = max(
        (q for q in malumot if isinstance(q, dict)),
        key=lambda q: _son(q.get("timestamp")) or 0.0,
        default=None,
    )
    if oxirgi is None:
        return None
    r = _son(oxirgi.get("longShortRatio"))
    return r if r is not None and r > 0 else None


def shamlarni_ajrat(malumot: object) -> list[Sham]:
    if not isinstance(malumot, list):
        return []
    natija: list[Sham] = []
    for q in malumot:
        if not isinstance(q, list) or len(q) < 5:
            continue
        vaqt, yuqori, past, yopilish = _son(q[0]), _son(q[2]), _son(q[3]), _son(q[4])
        if None in (vaqt, yuqori, past, yopilish):
            continue
        natija.append(Sham(ms_dan(vaqt), yuqori, past, yopilish))  # type: ignore[arg-type]
    return sorted(natija, key=lambda s: s.ochilish)


def kunlik_ortachani_hisobla(
    malumot: list, hozir: datetime, kun: int
) -> tuple[float | None, int]:
    """Kline qatorlari -> (o'rtacha quote hajm, nechta kun).

    Kline: [ochilish, o, h, l, c, hajm, yopilish, quote_hajm, ...].
    Faqat `yopilish < hozir` bo'lgan (yopilgan) shamlar olinadi.
    """
    hozir_ms = ms(hozir)
    hajmlar: list[float] = []
    for q in malumot:
        if not isinstance(q, list) or len(q) < 8:
            continue
        yopilish = _son(q[6])
        quote = _son(q[7])
        if yopilish is None or quote is None or yopilish >= hozir_ms:
            continue
        hajmlar.append(quote)
    hajmlar = hajmlar[-kun:]
    if not hajmlar:
        return None, 0
    return sum(hajmlar) / len(hajmlar), len(hajmlar)


# --------------------------------------------------------------------- #
#  CoinGecko — kapitalizatsiya va ta'minot
# --------------------------------------------------------------------- #

#: CoinGecko narxi Binance narxidan shuncha ko'p farq qilsa, topilgan
#: coin BOSHQA loyiha deb hisoblanadi (bir xil belgili ikki coin).
NARX_FARQI_MAX = 0.25

#: `symbols=` ishlamasa (eski API), shuncha sahifa ko'riladi.
ZAXIRA_SAHIFALAR = 4
SAHIFA = 250


class CoinGeckoTaminot(_Http):
    """Elakdan o'tgan coinlar uchun BITTA so'rov.

    `/coins/markets?symbols=...` — ro'yxatdagi belgilarni bir so'rovda
    beradi (`include_tokens=top`: bir belgida bir nechta coin bo'lsa,
    kapitalizatsiyasi eng kattasi). Bu endpoint javob bermasa, eng
    katta 1000 coin sahifalab ko'riladi.
    """

    def __init__(self, base_url: str, kutish: float = 15.0) -> None:
        super().__init__(kutish)
        self._base = base_url.rstrip("/")

    async def ol(self, belgilar: Iterable[str], jurnal: ManbaJurnali) -> dict[str, Taminot]:
        kerak = sorted({b.upper() for b in belgilar if b})
        if not kerak:
            return {}
        natija: dict[str, Taminot] = {}
        oxirgi_kod: int | None = 200
        # URL juda uzun bo'lmasin — 50 tadan bo'linadi.
        for i in range(0, len(kerak), 50):
            bolak = kerak[i : i + 50]
            malumot, kod = await self._json(
                f"{self._base}/coins/markets",
                {
                    "vs_currency": "usd",
                    "symbols": ",".join(b.lower() for b in bolak),
                    "include_tokens": "top",
                    "per_page": str(SAHIFA),
                },
            )
            oxirgi_kod = kod
            if kod != 200:
                break
            natija.update(taminotni_ajrat(malumot, set(bolak)))

        if oxirgi_kod != 200:
            # Avvalgi bo'laklarda topilgani SAQLANADI — faqat qolgani izlanadi.
            natija.update(await self._sahifalab(set(kerak) - set(natija)))
            jurnal.yoz("coingecko", 200 if natija else oxirgi_kod, "sahifalab")
        else:
            jurnal.yoz("coingecko", 200)
        return natija

    async def _sahifalab(self, kerak: set[str]) -> dict[str, Taminot]:
        natija: dict[str, Taminot] = {}
        for sahifa in range(1, ZAXIRA_SAHIFALAR + 1):
            malumot, kod = await self._json(
                f"{self._base}/coins/markets",
                {
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": str(SAHIFA),
                    "page": str(sahifa),
                },
            )
            if kod != 200:
                break
            for belgi, t in taminotni_ajrat(malumot, kerak).items():
                natija.setdefault(belgi, t)
            if len(natija) == len(kerak):
                break
        return natija


def taminotni_ajrat(malumot: object, kerak: set[str]) -> dict[str, Taminot]:
    """Bir belgida bir nechta coin bo'lsa — kapitalizatsiyasi eng kattasi."""
    if not isinstance(malumot, list):
        return {}
    natija: dict[str, Taminot] = {}
    for q in malumot:
        if not isinstance(q, dict):
            continue
        belgi = str(q.get("symbol", "")).upper()
        if belgi not in kerak:
            continue
        t = Taminot(
            market_cap=_son(q.get("market_cap")),
            narx=_son(q.get("current_price")),
            muomalada=_son(q.get("circulating_supply")),
            jami=_son(q.get("total_supply")),
            maksimal=_son(q.get("max_supply")),
        )
        avvalgi = natija.get(belgi)
        if avvalgi is None or (t.market_cap or 0) > (avvalgi.market_cap or 0):
            natija[belgi] = t
    return natija


def narx_mosmi(taminot: Taminot, binance_narx: float | None, kopaytirgich: int) -> bool:
    """CoinGecko coini Binance coini bilan bir xilmi (narx bo'yicha).

    Narx noma'lum bo'lsa — tekshirib bo'lmaydi, ishoniladi.
    """
    if taminot.narx is None or not binance_narx or taminot.narx <= 0:
        return True
    cg = taminot.narx * kopaytirgich
    return abs(cg - binance_narx) / binance_narx <= NARX_FARQI_MAX
