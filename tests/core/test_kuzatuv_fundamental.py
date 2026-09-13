"""Fundamental manbalar — jonli ma'lumot o'qish.

TARMOQQA CHIQMAYDI. `_json` o'rniga soxta javob qo'yiladi: test
HTTP ni emas, MA'LUMOTNI O'QISHNI tekshiradi. Manba javobining
shakli o'zgarsa, aynan shu testlar yiqiladi.
"""

from __future__ import annotations

import asyncio

import pytest

from core.config.schema import MarketDataConfig
from core.watch_panel.fundamental_manba import (
    OI_OYNA_KUN,
    FundamentalManba,
)


def manba(javoblar: dict[str, object]) -> FundamentalManba:
    """Manzilning bir qismiga qarab soxta javob qaytaradi."""
    m = FundamentalManba(MarketDataConfig())

    async def soxta(manzil: str, parametr: dict | None = None):  # noqa: ANN202, ARG001
        for kalit, javob in javoblar.items():
            if kalit in manzil:
                return javob
        return None

    m._json = soxta  # type: ignore[assignment]
    return m


def yur(korutina):  # noqa: ANN001, ANN201
    return asyncio.run(korutina)


# --------------------------------------------------------------------------- #
#  Fear & Greed
# --------------------------------------------------------------------------- #


def test_fear_greed_oqiladi() -> None:
    m = manba({"alternative.me": {"data": [{"value": "42", "value_classification": "Fear"}]}})
    assert yur(m.bozor_kayfiyati()).fear_greed == 42


def test_fear_greed_buzuq_javobda_none() -> None:
    """Manba yiqilsa — `None`, nol EMAS.

    Nol "qo'rquv eng yuqori" degan KUCHLI signal bo'lardi, aslida
    biz hech narsa bilmaymiz.
    """
    for javob in (None, {}, {"data": []}, {"data": [{}]}, {"data": "yo'q"}):
        m = manba({"alternative.me": javob})
        assert yur(m.bozor_kayfiyati()).fear_greed is None


# --------------------------------------------------------------------------- #
#  Funding rate — BITTA so'rovda hamma juftlik
# --------------------------------------------------------------------------- #


def test_funding_jadvali_bitta_sorovda_keladi() -> None:
    m = manba({
        "premiumIndex": [
            {"symbol": "BTCUSDT", "lastFundingRate": "0.0001"},
            {"symbol": "ETHUSDT", "lastFundingRate": "-0.00025"},
        ]
    })
    jadval = yur(m.funding_jadvali())
    assert jadval == {"BTCUSDT": 0.0001, "ETHUSDT": -0.00025}


def test_funding_buzuq_qatorlar_tashlanadi() -> None:
    """Bitta buzuq qator qolganini yo'qotmasin."""
    m = manba({
        "premiumIndex": [
            {"symbol": "BTCUSDT", "lastFundingRate": "0.0001"},
            {"symbol": "XXX", "lastFundingRate": "yo'q"},
            {"lastFundingRate": "0.5"},
            "matn",
        ]
    })
    assert yur(m.funding_jadvali()) == {"BTCUSDT": 0.0001}


def test_funding_javob_kelmasa_bosh_lugat() -> None:
    m = manba({"premiumIndex": None})
    assert yur(m.funding_jadvali()) == {}


# --------------------------------------------------------------------------- #
#  Open Interest
# --------------------------------------------------------------------------- #


def test_oi_ozgarishi_foizda() -> None:
    m = manba({
        "openInterestHist": [
            {"sumOpenInterestValue": "1000000"},
            {"sumOpenInterestValue": "1100000"},
            {"sumOpenInterestValue": "1200000"},
        ]
    })
    assert yur(m.oi_ozgarishi("BTCUSDT")) == 20.0


def test_oi_kamaygani_manfiy_chiqadi() -> None:
    m = manba({
        "openInterestHist": [
            {"sumOpenInterestValue": "2000000"},
            {"sumOpenInterestValue": "1500000"},
        ]
    })
    assert yur(m.oi_ozgarishi("BTCUSDT")) == -25.0


def test_futures_bozori_yoq_coin_xato_emas() -> None:
    """Spot-only coin uchun javob bo'sh — bu NORMAL holat."""
    for javob in (None, [], [{"sumOpenInterestValue": "100"}]):
        m = manba({"openInterestHist": javob})
        assert yur(m.oi_ozgarishi("SPOTONLY")) is None


def test_oi_nolga_bolinmaydi() -> None:
    m = manba({
        "openInterestHist": [
            {"sumOpenInterestValue": "0"},
            {"sumOpenInterestValue": "500"},
        ]
    })
    assert yur(m.oi_ozgarishi("BTCUSDT")) is None


def test_oi_oyna_sorovda_uzatiladi() -> None:
    """So'ralgan kun soni `OI_OYNA_KUN` ga bog'langan bo'lsin."""
    olingan: dict[str, str] = {}

    m = FundamentalManba(MarketDataConfig())

    async def soxta(manzil: str, parametr: dict | None = None):  # noqa: ANN202, ARG001
        olingan.update(parametr or {})
        return None

    m._json = soxta  # type: ignore[assignment]
    yur(m.oi_ozgarishi("BTCUSDT"))
    assert olingan["limit"] == str(OI_OYNA_KUN + 1)
    assert olingan["symbol"] == "BTCUSDT"


# --------------------------------------------------------------------------- #
#  Stablecoin zaxirasi — KAPITALIZATSIYA, narx emas
# --------------------------------------------------------------------------- #


def test_stablecoin_kapitalizatsiya_osishi() -> None:
    # USDT: 100 -> 105, USDC: 100 -> 100. Jami 200 -> 205 = +2.5%
    m = manba({
        "market_chart": {
            "market_caps": [[0, 100.0], [1, 102.0], [2, 105.0]],
        }
    })
    # Ikkala coin ham bir xil soxta javobni oladi: 100 -> 105
    assert yur(m.bozor_kayfiyati()).stablecoin_ozgarish_pct == 5.0


def test_stablecoin_narx_maydonini_ISHLATMAYDI() -> None:
    """O'zim qilgan xato: narx o'zgarishi stablecoinda doim ~0.

    Agar kod `price_change_percentage_7d` ga qaytsa, bu test
    yiqiladi — chunki soxta javobda `market_caps` bor, narx
    maydoni esa yo'q.
    """
    m = manba({"market_chart": {"market_caps": [[0, 1000.0], [1, 1200.0]]}})
    natija = yur(m.bozor_kayfiyati()).stablecoin_ozgarish_pct
    assert natija == 20.0, "kapitalizatsiya o'zgarishi o'qilmadi"


def test_stablecoin_manba_yiqilsa_none() -> None:
    for javob in (None, {}, {"market_caps": []}, {"market_caps": [[0, 0.0]]}):
        m = manba({"market_chart": javob})
        assert yur(m.bozor_kayfiyati()).stablecoin_ozgarish_pct is None


# --------------------------------------------------------------------------- #
#  Ulanmagan manbalar — MALUMOT_YOQ, "yo'q" EMAS
# --------------------------------------------------------------------------- #


def test_ulanmagan_manba_tekshiruvni_YOQ_qilmaydi() -> None:
    """Netflow, sektor, yangilik ulanmagan — ular maxrajga kirmaydi."""
    from core.analysis.fundamental.capital_flow import PulOqimi, pul_oqimi
    from core.analysis.turlar import Holat

    # Faqat stablecoin bor, netflow yo'q
    natija = pul_oqimi(PulOqimi(stablecoin_ozgarish_pct=1.5))
    assert natija.holat is Holat.HA
    assert "netflow" not in natija.izoh

    # Hech biri yo'q — MALUMOT_YOQ, YOQ emas
    bosh = pul_oqimi(PulOqimi())
    assert bosh.holat is Holat.MALUMOT_YOQ


@pytest.mark.parametrize(
    ("fng", "kutilgan"),
    [(20, True), (54, True), (55, False), (80, False)],
)
def test_fear_greed_chegarasi(fng: int, kutilgan: bool) -> None:
    """Qo'rquv paytida xarid — chegara 55 (`FNG_YUQORI_CHEGARA`)."""
    from core.analysis.fundamental.sentiment_sector import Kayfiyat, kayfiyat
    from core.analysis.turlar import Holat

    natija = kayfiyat(Kayfiyat(fear_greed=fng))
    assert (natija.holat is Holat.HA) is kutilgan
