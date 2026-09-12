"""Jonli bozor yig'masi — xarid bosimi, oyna va yirik savdolar."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from core.config.schema import MarketDataConfig
from core.watch_panel.live_market_data import (
    OYNA_SONIYA,
    YIRIK_USD,
    BozorYigichi,
    Savdo,
)


def yigich() -> BozorYigichi:
    y = BozorYigichi(MarketDataConfig(), "USDT")
    y.kuzat(["BTC"])
    return y


def xabar(*, narx: float, miqdor: float, maker: bool, sekund: int = 0) -> str:
    """Binance `aggTrade` paketi.

    `m: true` — xaridor MAKER, ya'ni tashabbuskor SOTUVCHI.
    """
    vaqt = datetime.now(UTC) - timedelta(seconds=sekund)
    return json.dumps(
        {
            "stream": "btcusdt@aggTrade",
            "data": {
                "s": "BTCUSDT",
                "p": str(narx),
                "q": str(miqdor),
                "T": int(vaqt.timestamp() * 1000),
                "m": maker,
            },
        }
    )


# --------------------------------------------------------------------------- #
#  Xarid bosimi
# --------------------------------------------------------------------------- #


def test_maker_bayrogi_teskari_oqiladi() -> None:
    """`m: false` — tashabbuskor XARIDOR. Bu eng oson adashiladigan joy."""
    y = yigich()
    y._xabar(xabar(narx=100.0, miqdor=1.0, maker=False))
    yigma = y.yigma("BTC")
    assert yigma.xarid_bosimi == 100.0


def test_maker_true_sotish_hisoblanadi() -> None:
    y = yigich()
    y._xabar(xabar(narx=100.0, miqdor=1.0, maker=True))
    assert y.yigma("BTC").xarid_bosimi == 0.0


def test_xarid_bosimi_summa_boyicha_olchanadi_soni_boyicha_emas() -> None:
    """Bitta katta xarid, o'nta mayda sotish — bosim XARID tomonda.

    Savdolar SONI bo'yicha o'lchansa, javob teskari chiqardi va
    "kim ko'proq pul qo'ydi" degan savolga javob bermasdi.
    """
    y = yigich()
    y._xabar(xabar(narx=100.0, miqdor=90.0, maker=False))  # $9 000 xarid
    for _ in range(10):
        y._xabar(xabar(narx=100.0, miqdor=1.0, maker=True))  # $1 000 sotish
    yigma = y.yigma("BTC")
    assert yigma.xarid_bosimi == 90.0


def test_savdo_bolmasa_bosim_none_nol_emas() -> None:
    """Ma'lumot yo'qligi "0% xarid" degani EMAS."""
    yigma = yigich().yigma("BTC")
    assert yigma.xarid_bosimi is None
    assert yigma.narx is None


# --------------------------------------------------------------------------- #
#  Oyna
# --------------------------------------------------------------------------- #


def test_oynadan_chiqqan_savdo_tashlanadi() -> None:
    y = yigich()
    y._xabar(xabar(narx=100.0, miqdor=1.0, maker=False, sekund=OYNA_SONIYA + 60))
    y._xabar(xabar(narx=200.0, miqdor=1.0, maker=True))
    yigma = y.yigma("BTC")
    # Eski XARID tashlandi — faqat yangi SOTISH qoldi.
    assert yigma.xarid_bosimi == 0.0
    assert yigma.narx == 200.0


def test_oyna_ichidagi_savdo_qoladi() -> None:
    y = yigich()
    y._xabar(xabar(narx=100.0, miqdor=1.0, maker=False, sekund=OYNA_SONIYA - 60))
    assert y.yigma("BTC").xarid_bosimi == 100.0


def test_navbat_cheksiz_osmaydi() -> None:
    """Xotira oqmasin — eski savdolar tozalanadi."""
    y = yigich()
    for i in range(200):
        y._xabar(xabar(narx=100.0, miqdor=1.0, maker=False, sekund=OYNA_SONIYA + i))
    y.yigma("BTC")
    assert len(y._savdolar["BTC"]) == 0


# --------------------------------------------------------------------------- #
#  Yirik savdolar
# --------------------------------------------------------------------------- #


def test_yirik_savdo_chegarasi() -> None:
    y = yigich()
    y._xabar(xabar(narx=1.0, miqdor=YIRIK_USD - 1, maker=False))
    assert y.yigma("BTC").yirik_savdo == 0

    y._xabar(xabar(narx=1.0, miqdor=YIRIK_USD + 1, maker=False))
    assert y.yigma("BTC").yirik_savdo == 1


def test_yiriklar_json_oqiladigan_shaklda() -> None:
    y = yigich()
    y._xabar(xabar(narx=2.0, miqdor=YIRIK_USD, maker=False))
    qatorlar = json.loads(y.yigma("BTC").yiriklar_json())
    assert len(qatorlar) == 1
    assert qatorlar[0]["xarid"] is True
    assert qatorlar[0]["narx"] == 2.0
    assert qatorlar[0]["summa"] > YIRIK_USD


# --------------------------------------------------------------------------- #
#  Ro'yxat o'zgarishi
# --------------------------------------------------------------------------- #


def test_royxatdan_chiqqan_coin_tarixi_tashlanadi() -> None:
    """Coin qaytsa, eski 15 daqiqa "hozirgi" deb ko'rsatilmasin."""
    y = yigich()
    y._xabar(xabar(narx=100.0, miqdor=1.0, maker=False))
    assert len(y._savdolar["BTC"]) == 1

    y.kuzat(["ETH"])
    assert "BTC" not in y._savdolar


def test_notanish_symbol_jimgina_tashlanadi() -> None:
    y = yigich()
    paket = json.loads(xabar(narx=100.0, miqdor=1.0, maker=False))
    paket["data"]["s"] = "DOGEUSDT"
    y._xabar(json.dumps(paket))
    assert y.yigma("BTC").narx is None


def test_buzuq_paket_yiqitmaydi() -> None:
    y = yigich()
    for xom in ("", "{", "null", "[]", '{"data": 5}', '{"data": {"s": "BTCUSDT"}}'):
        y._xabar(xom)
    assert y.yigma("BTC").narx is None


# --------------------------------------------------------------------------- #
#  URL
# --------------------------------------------------------------------------- #


def test_url_barcha_coinlarni_bitta_ulanishda_soraydi() -> None:
    """20 ta alohida soket emas — bitta combined stream."""
    y = BozorYigichi(MarketDataConfig(), "USDT")
    y.kuzat(["BTC", "ETH", "SOL"])
    url = y._url()
    assert url.count("@aggTrade") == 3
    assert "btcusdt@aggTrade" in url
    assert "ethusdt@aggTrade" in url


def test_savdo_tipi_summani_ozi_hisoblamaydi() -> None:
    """`Savdo` — oddiy yozuv; summa chaqiruvchida hisoblanadi.

    Ikki joyda hisoblansa, ular ajralib ketardi.
    """
    s = Savdo(datetime.now(UTC), narx=10.0, summa_usd=100.0, xarid=True)
    assert s.summa_usd == 100.0
