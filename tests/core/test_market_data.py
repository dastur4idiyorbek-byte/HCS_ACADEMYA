"""6.2-band: bozor ma'lumotlari qatlami — narx keshi, backoff, sakrash detektori."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.config.schema import MarketDataConfig
from core.domain.models import PriceTick
from core.market_data import (
    BackoffPolicy,
    PriceCache,
    SpikeDetector,
    from_binance_symbol,
    to_binance_symbol,
)
from core.market_data.binance import BinancePriceStream
from core.market_data.ranking import (
    CoinGeckoRanking,
    CoinMarketCapRanking,
    RankingUnavailableError,
    build_ranking_provider,
)

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


# --------------------------------------------------------------------------- #
#  Coin belgilari
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("kiruvchi", "kutilgan"),
    [("BTC", "btcusdt"), ("btc", "btcusdt"), ("BTCUSDT", "btcusdt"), ("eth", "ethusdt")],
)
def test_binance_juftlik_nomi(kiruvchi: str, kutilgan: str) -> None:
    assert to_binance_symbol(kiruvchi) == kutilgan


def test_binance_juftligidan_coin_ajratiladi() -> None:
    assert from_binance_symbol("BTCUSDT") == "BTC"
    assert from_binance_symbol("ETHUSDT") == "ETH"


# --------------------------------------------------------------------------- #
#  Narx keshi va eskirish (fail-safe)
# --------------------------------------------------------------------------- #


def test_narx_keshi_yangilanadi() -> None:
    kesh = PriceCache()
    kesh.update(PriceTick("BTC", 67000.0, HOZIR))
    assert kesh.price_of("btc") == 67000.0
    assert kesh.age_seconds("BTC", HOZIR) == 0


def test_eskirgan_narx_aniqlanadi() -> None:
    kesh = PriceCache()
    kesh.update(PriceTick("BTC", 67000.0, HOZIR))
    keyin = HOZIR + timedelta(seconds=120)

    assert kesh.age_seconds("BTC", keyin) == 120
    assert kesh.is_stale("BTC", max_age=90, now=keyin)
    assert not kesh.is_stale("BTC", max_age=180, now=keyin)


def test_narx_umuman_yoq_bolsa_eskirgan_hisoblanadi() -> None:
    """Fail-safe: ma'lumot yo'qligi "yangi" degani emas."""
    kesh = PriceCache()
    assert kesh.age_seconds("BTC") is None
    assert kesh.is_stale("BTC", max_age=90)


def test_eng_eski_narx_yoshi() -> None:
    kesh = PriceCache()
    kesh.update(PriceTick("BTC", 1.0, HOZIR))
    kesh.update(PriceTick("ETH", 1.0, HOZIR - timedelta(seconds=45)))

    assert kesh.oldest_age({"BTC", "ETH"}, HOZIR) == 45
    assert kesh.oldest_age({"BTC", "SOL"}, HOZIR) is None, "yo'q coin -> noaniq"


# --------------------------------------------------------------------------- #
#  Qayta ulanish siyosati
# --------------------------------------------------------------------------- #


def test_backoff_oshib_boradi() -> None:
    siyosat = BackoffPolicy([2, 4, 8, 16])
    assert [siyosat.next_delay() for _ in range(4)] == [2.0, 4.0, 8.0, 16.0]


def test_backoff_oxirgi_qiymatda_qoladi() -> None:
    siyosat = BackoffPolicy([2, 4])
    [siyosat.next_delay() for _ in range(5)]
    assert siyosat.next_delay() == 4.0, "cheksiz o'sib ketmasligi kerak"


def test_backoff_muvaffaqiyatdan_keyin_tiklanadi() -> None:
    siyosat = BackoffPolicy([2, 4, 8])
    siyosat.next_delay()
    siyosat.next_delay()
    siyosat.reset()
    assert siyosat.next_delay() == 2.0


def test_bosh_backoff_rad_etiladi() -> None:
    with pytest.raises(ValueError, match="bo'sh"):
        BackoffPolicy([])


# --------------------------------------------------------------------------- #
#  4.7 — Sakrash detektori (kill switch)
# --------------------------------------------------------------------------- #


def test_keskin_kotarilish_aniqlanadi() -> None:
    detektor = SpikeDetector(threshold_pct=5.0, window=timedelta(seconds=60))
    detektor.observe("BTC", 100.0, HOZIR)
    natija = detektor.observe("BTC", 106.0, HOZIR + timedelta(seconds=10))

    assert natija is not None
    assert natija > 0, "ko'tarilish musbat bo'lishi kerak"


def test_keskin_tushish_aniqlanadi() -> None:
    detektor = SpikeDetector(threshold_pct=5.0, window=timedelta(seconds=60))
    detektor.observe("BTC", 100.0, HOZIR)
    natija = detektor.observe("BTC", 93.0, HOZIR + timedelta(seconds=10))

    assert natija is not None
    assert natija < 0, "tushish manfiy bo'lishi kerak"


def test_sekin_harakat_sakrash_emas() -> None:
    detektor = SpikeDetector(threshold_pct=5.0, window=timedelta(seconds=60))
    detektor.observe("BTC", 100.0, HOZIR)
    assert detektor.observe("BTC", 102.0, HOZIR + timedelta(seconds=30)) is None


def test_oyna_tashqarisidagi_narx_hisobga_olinmaydi() -> None:
    """Bir soatda 5% — bu sakrash emas, oddiy harakat."""
    detektor = SpikeDetector(threshold_pct=5.0, window=timedelta(seconds=60))
    detektor.observe("BTC", 100.0, HOZIR)
    assert detektor.observe("BTC", 106.0, HOZIR + timedelta(minutes=30)) is None


def test_coinlar_alohida_kuzatiladi() -> None:
    detektor = SpikeDetector(threshold_pct=5.0, window=timedelta(seconds=60))
    detektor.observe("BTC", 100.0, HOZIR)
    assert detektor.observe("ETH", 50.0, HOZIR + timedelta(seconds=5)) is None


# --------------------------------------------------------------------------- #
#  WebSocket xabarlarini o'qish
# --------------------------------------------------------------------------- #


@pytest.fixture
def stream() -> BinancePriceStream:
    return BinancePriceStream(MarketDataConfig())


def test_trade_xabari_oqiladi(stream: BinancePriceStream) -> None:
    xom = '{"stream":"btcusdt@trade","data":{"s":"BTCUSDT","p":"67123.45","T":1787140800000}}'
    tick = stream._parse(xom)

    assert tick is not None
    assert tick.symbol == "BTC"
    assert tick.price == 67123.45
    assert tick.timestamp.tzinfo is not None


@pytest.mark.parametrize(
    "yomon",
    ['{"buzuq"', "{}", '{"data":{"s":"BTCUSDT"}}', '{"data":{"s":"BTCUSDT","p":"abc","T":1}}', ""],
)
def test_buzuq_xabar_oqimni_toxtatmaydi(stream: BinancePriceStream, yomon: str) -> None:
    """0.3-band: bitta buzuq xabar butun kuzatuvni to'xtatmasligi kerak."""
    assert stream._parse(yomon) is None


def test_obuna_royxati_url_ga_kiradi(stream: BinancePriceStream) -> None:
    stream.subscribe({"BTC", "ETH"})
    url = stream._url()
    assert "btcusdt@trade" in url
    assert "ethusdt@trade" in url


def test_bir_xil_obuna_qayta_ulanishga_sabab_bolmaydi(stream: BinancePriceStream) -> None:
    stream.subscribe({"BTC"})
    stream._resubscribe.clear()
    stream.subscribe({"BTC"})
    assert not stream._resubscribe.is_set(), "o'zgarmagan obuna ulanishni uzmasligi kerak"


def test_obuna_ozgarsa_qayta_ulanish_soraladi(stream: BinancePriceStream) -> None:
    stream.subscribe({"BTC"})
    stream._resubscribe.clear()
    stream.subscribe({"BTC", "ETH"})
    assert stream._resubscribe.is_set()


# --------------------------------------------------------------------------- #
#  Reyting manbai
# --------------------------------------------------------------------------- #


def test_kalit_yoq_bolsa_coingecko_tanlanadi(monkeypatch) -> None:
    """Fail-safe: kalit yo'qligi tizimni to'xtatmasligi kerak."""
    monkeypatch.delenv("CMC_API_KEY", raising=False)
    provider = build_ranking_provider(MarketDataConfig(ranking_source="coinmarketcap"))
    assert isinstance(provider, CoinGeckoRanking)


def test_kalit_bor_bolsa_cmc_zaxira_bilan(monkeypatch) -> None:
    monkeypatch.setenv("CMC_API_KEY", "test-kalit")
    provider = build_ranking_provider(MarketDataConfig(ranking_source="coinmarketcap"))
    assert provider._primary.__class__ is CoinMarketCapRanking
    assert provider._fallback.__class__ is CoinGeckoRanking


def test_coingecko_tanlansa_kalit_kerak_emas(monkeypatch) -> None:
    monkeypatch.delenv("CMC_API_KEY", raising=False)
    provider = build_ranking_provider(MarketDataConfig(ranking_source="coingecko"))
    assert isinstance(provider, CoinGeckoRanking)


# --------------------------------------------------------------------------- #
#  Reyting: sahifalash
# --------------------------------------------------------------------------- #


class SoxtaJavob:
    def __init__(self, payload: list[dict]) -> None:
        self.status = 200
        self._payload = payload

    async def json(self) -> list[dict]:
        return self._payload

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *_: object) -> None:
        pass


class SoxtaSession:
    """Sahifalarni yozib oladigan HTTP sessiya (tarmoqqa chiqmaydi)."""

    def __init__(self, jami: int) -> None:
        self._jami = jami
        self.sorovlar: list[tuple[int, int]] = []

    def get(self, url: str, params: dict) -> SoxtaJavob:  # noqa: ARG002
        sahifa = int(params["page"])
        per_page = int(params["per_page"])
        self.sorovlar.append((sahifa, per_page))

        boshi = (sahifa - 1) * per_page
        yozuvlar = [
            {
                "symbol": f"c{i}",
                "name": f"Coin {i}",
                "market_cap_rank": i + 1,
                "market_cap": 1_000_000,
                "total_volume": 100_000,
            }
            for i in range(boshi, min(boshi + per_page, self._jami))
        ]
        return SoxtaJavob(yozuvlar)


def _coingecko(session: SoxtaSession) -> CoinGeckoRanking:
    provider = CoinGeckoRanking(MarketDataConfig())
    provider._session = session
    provider._get_session = lambda: _tayyor(session)  # type: ignore[assignment]
    return provider


async def _tayyor(qiymat):  # noqa: ANN001, ANN202
    return qiymat


async def test_reyting_bir_sahifadan_kop_yuklanadi() -> None:
    """250 dan ortiq so'ralganda hammasi kelishi kerak.

    Ilgari kod `min(limit, 250)` deb yozib, faqat birinchi sahifani
    so'rardi: 500 ta so'ralsa ham 250 tasi kelardi, JIMGINA. Skanerlash
    chuqurligini oshirish hech qanday ta'sir bermasdi va buni sezish
    ham qiyin edi — xato yo'q, log "250 ta coin olindi" deb yozardi.
    """
    session = SoxtaSession(jami=600)
    natija = await _coingecko(session).fetch_ranking(500)

    assert len(natija) == 500
    assert session.sorovlar == [(1, 250), (2, 250)]
    assert natija[0].symbol == "C0"
    assert natija[-1].symbol == "C499"


async def test_bir_sahifaga_sigsa_ikkinchisi_soralmaydi() -> None:
    session = SoxtaSession(jami=600)
    natija = await _coingecko(session).fetch_ranking(30)

    assert len(natija) == 30
    assert session.sorovlar == [(1, 30)], "ortiqcha so'rov yuborilmasin"


async def test_royxat_tugasa_toxtaydi() -> None:
    """Birja ro'yxati so'ralgandan kalta bo'lsa — bu xato emas."""
    session = SoxtaSession(jami=310)
    natija = await _coingecko(session).fetch_ranking(500)

    assert len(natija) == 310
    assert len(session.sorovlar) == 2, "bo'sh sahifalar cheksiz so'ralmasin"


async def test_bosh_reyting_xato_beradi() -> None:
    """0.3-band: bo'sh ro'yxat bilan davom etish — eski ro'yxatni yo'qotish."""
    with pytest.raises(RankingUnavailableError):
        await _coingecko(SoxtaSession(jami=0)).fetch_ranking(150)


# --------------------------------------------------------------------------- #
#  Tarixiy shamlar: 1000 dan ortig'i SAHIFALAB yuklanadi
# --------------------------------------------------------------------------- #


class SoxtaKlinesJavobi:
    """`session.get(...)` qaytaradigan kontekst menejeri."""

    def __init__(self, xom: list) -> None:
        self._xom = xom

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> list:
        return self._xom


class SoxtaKlinesSessiyasi:
    """Binance klines javobini taqlid qiladi — tarmoqqa chiqmaydi.

    Tarix CHEKLI: `jami` tadan ortiq sham yo'q. Shu bilan "tarix
    tugadi" holati ham sinaladi.
    """

    def __init__(self, jami: int, interval_ms: int = 4 * 3600 * 1000) -> None:
        self.jami = jami
        self.interval_ms = interval_ms
        self.eng_yangi = 1_800_000_000_000
        self.sorovlar: list[dict] = []
        self.closed = False

    def get(self, _url: str, params: dict):  # noqa: ANN201
        self.sorovlar.append(dict(params))
        limit = int(params["limit"])
        oxiri = int(params.get("endTime", self.eng_yangi))

        # Eng eski ruxsat etilgan sham vaqti
        eng_eski = self.eng_yangi - (self.jami - 1) * self.interval_ms
        songgi = min(oxiri, self.eng_yangi)
        # `songgi` dan orqaga qarab `limit` ta sham
        vaqtlar = []
        t = songgi - (songgi - self.eng_yangi) % self.interval_ms
        while len(vaqtlar) < limit and t >= eng_eski:
            vaqtlar.append(t)
            t -= self.interval_ms
        vaqtlar.reverse()

        return SoxtaKlinesJavobi(
            [[v, "1.0", "2.0", "0.5", "1.5", "100.0"] for v in vaqtlar]
        )


def _provayder(sessiya) -> object:  # noqa: ANN001
    from core.market_data.binance import BinanceCandleProvider

    provider = BinanceCandleProvider(MarketDataConfig())
    provider._session = sessiya
    return provider


@pytest.mark.asyncio
async def test_ming_shamdan_ortigi_sahifalab_yuklanadi() -> None:
    """`--days 730` JIMGINA ~166 kunga aylanardi.

    Eski kod so'rovni `min(limit, 1000)` bilan qirqardi va bu hech
    qayerda aytilmasdi. 4 soatlik timeframeda 1000 sham — atigi 166
    kun. Spetsifikatsiya esa 1-2 yillik sinovni MAJBURIY deb
    belgilaydi: shart bajarilgandek ko'rinib, aslida bajarilmasdi.
    """
    sessiya = SoxtaKlinesSessiyasi(jami=5000)
    provider = _provayder(sessiya)

    shamlar = await provider.fetch_candles("BTC", "4h", 2500)

    assert len(shamlar) == 2500
    assert len(sessiya.sorovlar) == 3, "1000 + 1000 + 500"
    assert all(
        oldingi.open_time < keyingi.open_time
        for oldingi, keyingi in zip(shamlar, shamlar[1:], strict=False)
    ), "eng eskisidan eng yangisiga tartiblangan bo'lishi kerak"


@pytest.mark.asyncio
async def test_faqat_eng_songgi_sham_yopilmagan_bolishi_mumkin() -> None:
    """Sahifalashda har 1000 shamda bittasi "yopilmagan" bo'lib qolmasin.

    Javobning oxirgi shami yopilmagan bo'lishi mumkin — lekin bu
    faqat ENG YANGI sahifaga tegishli. Eski sahifalarga ham
    qo'llanilsa, backtest tarix bo'ylab sochilgan soxta "yopilmagan"
    shamlarni ko'rardi.
    """
    provider = _provayder(SoxtaKlinesSessiyasi(jami=5000))

    shamlar = await provider.fetch_candles("BTC", "4h", 2500)

    yopilmagan = [s for s in shamlar if not s.closed]
    assert len(yopilmagan) == 1
    assert yopilmagan[0] is shamlar[-1]


@pytest.mark.asyncio
async def test_tarix_tugasa_bor_narsa_qaytadi() -> None:
    """Coin so'ralgancha eski bo'lmasa — cheksiz so'rov yuborilmasin."""
    sessiya = SoxtaKlinesSessiyasi(jami=1200)
    provider = _provayder(sessiya)

    shamlar = await provider.fetch_candles("BTC", "4h", 5000)

    assert len(shamlar) == 1200
    assert len(sessiya.sorovlar) <= 3, "tarix tugagach to'xtashi kerak"


@pytest.mark.asyncio
async def test_kichik_sorov_bitta_sahifada_qoladi() -> None:
    """Jonli bot yo'li o'zgarmasligi kerak: 1000 gacha — bitta so'rov."""
    sessiya = SoxtaKlinesSessiyasi(jami=5000)
    provider = _provayder(sessiya)

    shamlar = await provider.fetch_candles("BTC", "4h", 200)

    assert len(shamlar) == 200
    assert len(sessiya.sorovlar) == 1
    assert "endTime" not in sessiya.sorovlar[0]
