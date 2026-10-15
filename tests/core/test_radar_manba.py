"""Modul 4.0.0 — Binance va CoinGecko javoblarini ajratish.

Bu muhitda Binance'ga ulanib bo'lmaydi, shuning uchun javob shakllari
Binance hujjatidagi namunalar bilan sinaladi. Buzuq javob sessiyani
yiqitmasligi kerak — "bilmayman" bo'lib qolishi kerak.
"""

from __future__ import annotations

from datetime import UTC, datetime

from core.portlash_radari import manba as m
from core.portlash_radari.vaqt import ms


def test_juftliklar_faqat_usdt_perpetual_coin() -> None:
    javob = {"symbols": [
        {"symbol": "LSKUSDT", "baseAsset": "LSK", "quoteAsset": "USDT",
         "contractType": "PERPETUAL", "status": "TRADING", "underlyingType": "COIN",
         "onboardDate": 1569398400000},
        {"symbol": "1000PEPEUSDT", "baseAsset": "1000PEPE", "quoteAsset": "USDT",
         "contractType": "PERPETUAL", "status": "TRADING"},
        {"symbol": "BTCUSDC", "baseAsset": "BTC", "quoteAsset": "USDC",
         "contractType": "PERPETUAL", "status": "TRADING"},
        {"symbol": "ETHUSDT_261225", "baseAsset": "ETH", "quoteAsset": "USDT",
         "contractType": "CURRENT_QUARTER", "status": "TRADING"},
        {"symbol": "OLDUSDT", "baseAsset": "OLD", "quoteAsset": "USDT",
         "contractType": "PERPETUAL", "status": "SETTLING"},
        {"symbol": "XAUUSDT", "baseAsset": "XAU", "quoteAsset": "USDT",
         "contractType": "PERPETUAL", "status": "TRADING", "underlyingType": "COMMODITY"},
        {"symbol": "USDCUSDT", "baseAsset": "USDC", "quoteAsset": "USDT",
         "contractType": "PERPETUAL", "status": "TRADING"},
        "buzuq",
    ]}
    natija = m.juftliklarni_ajrat(javob, {"USDC"})
    assert [j.symbol for j in natija] == ["LSKUSDT", "1000PEPEUSDT"]
    assert natija[1].belgi == "PEPE" and natija[1].kopaytirgich == 1000
    assert natija[0].onboard == datetime(2019, 9, 25, 8, 0, tzinfo=UTC)
    assert m.juftliklarni_ajrat(None, set()) == []
    assert m.juftliklarni_ajrat({"symbols": "x"}, set()) == []


def test_ticker_funding_oraliq() -> None:
    t = m.tickerlarni_ajrat([
        {"symbol": "LSKUSDT", "lastPrice": "1.2", "priceChangePercent": "287.0",
         "quoteVolume": "82000000"},
        {"symbol": "BADUSDT", "lastPrice": "abc", "priceChangePercent": None},
    ])
    assert t["LSKUSDT"] == m.Ticker(1.2, 287.0, 82e6)
    assert t["BADUSDT"] == m.Ticker(None, None, None)
    assert m.fundingni_ajrat([{"symbol": "X", "lastFundingRate": "-0.0034"},
                              {"symbol": "Y", "lastFundingRate": ""}]) == {"X": -0.0034}
    assert m.oraliqlarni_ajrat([{"symbol": "X", "fundingIntervalHours": 4},
                                {"symbol": "Y", "fundingIntervalHours": 0}]) == {"X": 4}


def test_oi_vaqt_boyicha_tartiblanadi_va_kontrakt_soni() -> None:
    javob = [
        {"sumOpenInterest": "141", "sumOpenInterestValue": "999", "timestamp": 3},
        {"sumOpenInterest": "100", "sumOpenInterestValue": "1", "timestamp": 1},
        {"sumOpenInterest": "x", "timestamp": 2},
    ]
    assert m.oi_ni_ajrat(javob) == (100.0, 141.0)
    assert m.oi_ni_ajrat({"code": -1121}) == ()


def test_long_short_eng_oxirgisi() -> None:
    assert m.long_short_ni_ajrat([
        {"longShortRatio": "1.5", "timestamp": 1},
        {"longShortRatio": "2.7", "timestamp": 5},
    ]) == 2.7
    assert m.long_short_ni_ajrat([]) is None
    assert m.long_short_ni_ajrat([{"longShortRatio": "0", "timestamp": 1}]) is None


def test_kunlik_ortacha_yopilmagan_shamni_olmaydi() -> None:
    hozir = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
    kun = 86_400_000
    bugun = ms(datetime(2026, 10, 14, tzinfo=UTC))
    qatorlar = [
        [bugun - 2 * kun, "1", "1", "1", "1", "0", bugun - kun - 1, "100"],
        [bugun - kun, "1", "1", "1", "1", "0", bugun - 1, "300"],
        [bugun, "1", "1", "1", "1", "0", bugun + kun - 1, "999999"],  # yopilmagan
    ]
    assert m.kunlik_ortachani_hisobla(qatorlar, hozir, 30) == (200.0, 2)
    assert m.kunlik_ortachani_hisobla([], hozir, 30) == (None, 0)


def test_shamlar() -> None:
    s = m.shamlarni_ajrat([[2000, "1", "3", "0.5", "2"], [1000, "1", "2", "1", "1.5"], [5]])
    assert [x.yopilish for x in s] == [1.5, 2.0]


def test_coingecko_bir_belgida_eng_katta_kapitalizatsiya() -> None:
    javob = [
        {"symbol": "lsk", "market_cap": 1e6, "current_price": 9.0},
        {"symbol": "lsk", "market_cap": 2e8, "current_price": 1.2,
         "circulating_supply": 70.6, "total_supply": 100, "max_supply": None},
        {"symbol": "zzz", "market_cap": 5e9},
    ]
    t = m.taminotni_ajrat(javob, {"LSK"})
    assert set(t) == {"LSK"}
    assert t["LSK"].market_cap == 2e8
    assert round(t["LSK"].aylanma_pct, 1) == 70.6


def test_aylanma_maksimaldan_hisoblanadi() -> None:
    t = m.Taminot(None, None, muomalada=50.0, jami=60.0, maksimal=100.0)
    assert t.aylanma_pct == 50.0
    assert m.Taminot(None, None, 50.0, None, None).aylanma_pct is None


def test_narx_mosligi_kopaytirgich_bilan() -> None:
    t = m.Taminot(1e9, 0.00001, None, None, None)
    assert m.narx_mosmi(t, 0.0101, 1000)
    assert not m.narx_mosmi(t, 0.02, 1000)
    assert m.narx_mosmi(m.Taminot(1e9, None, None, None, None), 5.0, 1)


def test_jurnal_451_ni_taniydi_va_coin_boshiga_sanaydi() -> None:
    j = m.ManbaJurnali()
    j.yoz("ticker", 451)
    assert j.cheklangan()
    for kod in (200, 200, 400):
        j.hisobla("oi", kod)
    assert j.lugat()["oi"] == {"holat": "ok", "kod": 400, "izoh": "2/3"}
    j.hisobla("oi", None)
    j.hisobla("oi", None)
    assert j.lugat()["oi"]["holat"] == "xato"


async def test_coingecko_symbols_ishlamasa_sahifalab_qidiradi() -> None:
    class Soxta(m.CoinGeckoTaminot):
        def __init__(self) -> None:
            super().__init__("https://cg.test")
            self.chaqiruvlar: list[dict] = []

        async def _json(self, manzil, parametr=None):  # noqa: ANN001, ANN202
            self.chaqiruvlar.append(parametr)
            if "symbols" in parametr:
                return None, 400
            if parametr["page"] == "1":
                return [{"symbol": "lsk", "market_cap": 2e8}], 200
            return [], 200

    cg = Soxta()
    jurnal = m.ManbaJurnali()
    natija = await cg.ol(["LSK", "ABC"], jurnal)
    assert natija["LSK"].market_cap == 2e8
    assert jurnal.lugat()["coingecko"]["izoh"] == "sahifalab"
    assert len(cg.chaqiruvlar) == 1 + m.ZAXIRA_SAHIFALAR


def test_coingecko_nol_va_manfiy_nomalum() -> None:
    t = m.taminotni_ajrat(
        [{"symbol": "new", "market_cap": 0, "current_price": 1.0,
          "circulating_supply": 0, "total_supply": 1000, "max_supply": 0}],
        {"NEW"},
    )["NEW"]
    assert t.market_cap is None and t.muomalada is None and t.maksimal is None
    assert t.aylanma_pct is None


async def test_shamlar_delisting_bosh_tarmoq_xatosi_none() -> None:
    class Soxta(m.BinanceFutures):
        def __init__(self, kod: int | None) -> None:
            super().__init__("https://fapi.test")
            self.kod = kod

        async def _json(self, manzil, parametr=None):  # noqa: ANN001, ANN202
            return None, self.kod

    assert await Soxta(400).shamlar("GONEUSDT", "1h") == []
    assert await Soxta(429).shamlar("LSKUSDT", "1h") is None
    assert await Soxta(None).shamlar("LSKUSDT", "1h") is None
