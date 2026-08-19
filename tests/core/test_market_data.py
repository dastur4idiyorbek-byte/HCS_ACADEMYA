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
