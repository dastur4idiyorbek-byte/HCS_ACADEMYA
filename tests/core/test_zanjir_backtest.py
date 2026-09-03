"""Zanjir backtest dvigateli — savdo simulyatsiyasi va ablatsiya mexanizmi."""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta

import pytest

from core.backtest.dataset import Dataset
from core.backtest.zanjir_engine import Savdo, ZanjirBacktest
from core.config.loader import load_config
from core.domain.models import Candle

BOSH = datetime(2024, 1, 1, tzinfo=UTC)


def seriya(n: int, narx: float = 100.0, qadam: timedelta = timedelta(days=1)) -> list[Candle]:
    """Trend + to'lqin + shovqin — sun'iy, lekin struktura beradigan qator."""
    rnd = random.Random(11)
    out = []
    for i in range(n):
        narx *= 1 + 0.0015 + 0.02 * math.sin(i / 9) + rnd.uniform(-0.012, 0.012)
        out.append(
            Candle(
                open_time=BOSH + qadam * i,
                open=narx,
                high=narx * (1 + abs(rnd.uniform(0, 0.015))),
                low=narx * (1 - abs(rnd.uniform(0, 0.015))),
                close=narx,
                volume=rnd.uniform(500, 2000),
            )
        )
    return out


@pytest.fixture
def dataset() -> Dataset:
    ds = Dataset()
    for s in ("BTC", "ETH"):
        ds.add(s, "1d", seriya(300))
        ds.add(s, "15m", seriya(300, qadam=timedelta(minutes=15)))
    return ds


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


def test_dvigatel_uchdan_uchgacha_ishlaydi(config, dataset) -> None:  # noqa: ANN001
    natija = ZanjirBacktest(config, "sinov").yur(dataset, ["BTC", "ETH"])
    assert natija.qadamlar > 0
    # Uzilish statistikasi to'ldirilishi shart — "nega signal yo'q"
    # savoliga javob shu yerdan chiqadi.
    assert natija.uzilishlar


def test_bir_coinda_ikkita_savdo_ochilmaydi(config, dataset) -> None:  # noqa: ANN001
    """Ochiq savdo YANGI SIGNALDAN OLDIN yangilanadi.

    Teskarisi bo'lsa bitta coinda bir vaqtda ikkita pozitsiya
    ochilib, natija ikki barobar ko'rinardi.
    """
    natija = ZanjirBacktest(config, "sinov").yur(dataset, ["BTC"])
    for a, b in zip(natija.savdolar, natija.savdolar[1:], strict=False):
        assert a.chiqish_vaqti is not None
        assert a.chiqish_vaqti <= b.kirish_vaqti


def test_ablatsiya_tekshiruvni_maxrajdan_chiqaradi(config, dataset) -> None:  # noqa: ANN001
    """Vaznni nolga tushirish EMAS — maxrajdan CHIQARISH.

    Nolga tushirish blokni sun'iy zaiflashtirardi va biz "tekshiruv
    yomon" degan yolg'on xulosa chiqarardik.
    """
    from core.analysis.turlar import Holat

    dvigatel = ZanjirBacktest(
        config, "test", ochirilgan_tekshiruvlar=frozenset({"fibonacci"})
    )
    from core.analysis.turlar import Zanjir, blok, ha

    z = Zanjir((blok("Zona Sifati", [ha("fibonacci"), ha("fvg")]),))
    yangi = dvigatel._ablatsiya(z)
    holatlar = {t.nom: t.holat for t in yangi.bloklar[0].tekshiruvlar}
    assert holatlar["fibonacci"] is Holat.MALUMOT_YOQ
    assert holatlar["fvg"] is Holat.HA
    assert yangi.bloklar[0].maxraj == 1


def test_ablatsiya_blokni_bosh_qoldirsa_zanjir_uziladi(config) -> None:  # noqa: ANN001
    from core.analysis.turlar import Zanjir, blok, ha, yoq

    dvigatel = ZanjirBacktest(
        config, "test", ochirilgan_tekshiruvlar=frozenset({"fibonacci"})
    )
    z = Zanjir((blok("Zona Sifati", [ha("fibonacci"), yoq("fvg")]),))
    yangi = dvigatel._ablatsiya(z)
    assert yangi.uzildi_blokda == "Zona Sifati"


def test_stop_tp_dan_oldin_tekshiriladi(config) -> None:  # noqa: ANN001
    """Bitta shamda ikkalasi tegilsa — ehtiyotkor taxmin: STOP.

    Teskarisi natijani chiroyliroq ko'rsatardi va bu — o'zini aldash.
    """
    dvigatel = ZanjirBacktest(config, "test")
    savdo = Savdo(
        symbol="BTC", kirish_vaqti=BOSH, entry=100.0, stop=90.0, tplar=(120.0,)
    )
    sham = Candle(
        open_time=BOSH + timedelta(days=1),
        open=100, high=130, low=85, close=125, volume=1,
    )
    assert dvigatel._yangila(savdo, sham, BOSH + timedelta(days=1))
    assert savdo.sabab == "stop"


def test_tp1_dan_keyin_stop_breakevenga_kochadi(config) -> None:  # noqa: ANN001
    dvigatel = ZanjirBacktest(config, "test")
    savdo = Savdo(
        symbol="BTC", kirish_vaqti=BOSH, entry=100.0, stop=90.0, tplar=(110.0, 130.0)
    )
    sham = Candle(
        open_time=BOSH + timedelta(days=1),
        open=100, high=115, low=99, close=112, volume=1,
    )
    dvigatel._yangila(savdo, sham, BOSH + timedelta(days=1))
    assert savdo.tp_soni == 1
    assert savdo.stop == 100.0


def test_muddat_tugasa_yopiladi(config) -> None:  # noqa: ANN001
    """Pul band bo'lib qolmasin (5-qism, vaqt chegarasi)."""
    dvigatel = ZanjirBacktest(config, "test")
    savdo = Savdo(
        symbol="BTC", kirish_vaqti=BOSH, entry=100.0, stop=90.0, tplar=(200.0,)
    )
    kech = BOSH + timedelta(days=100)
    sham = Candle(open_time=kech, open=100, high=105, low=95, close=101, volume=1)
    assert dvigatel._yangila(savdo, sham, kech)
    assert savdo.sabab == "muddat"


def test_xarajat_natijadan_ayiriladi(config) -> None:  # noqa: ANN001
    """Har savdoda 2 × (komissiya + sirg'anish) = 0.3%."""
    dvigatel = ZanjirBacktest(config, "test")
    savdo = Savdo(
        symbol="BTC", kirish_vaqti=BOSH, entry=100.0, stop=90.0, tplar=(110.0,)
    )
    dvigatel._yop(savdo, 100.0, BOSH + timedelta(days=1), "test")
    kutilgan = -2 * (config.backtest.fee_pct + config.backtest.slippage_pct)
    assert savdo.natija_pct == pytest.approx(kutilgan)


def test_qismli_sotish_hisobga_olinadi(config) -> None:  # noqa: ANN001
    """TP1 da 50%, qolgani yopilish narxida."""
    dvigatel = ZanjirBacktest(config, "test")
    savdo = Savdo(
        symbol="BTC", kirish_vaqti=BOSH, entry=100.0, stop=90.0, tplar=(120.0, 140.0)
    )
    savdo.tp_soni = 1
    dvigatel._yop(savdo, 100.0, BOSH + timedelta(days=1), "muddat")
    # 50% x +20% + 50% x 0% - 0.3% = 9.7%
    assert savdo.natija_pct == pytest.approx(9.7)


def test_profit_factor_hisobi(config, dataset) -> None:  # noqa: ANN001
    from core.backtest.zanjir_engine import ZanjirNatijasi

    n = ZanjirNatijasi(nom="x")
    n.savdolar = [
        Savdo("A", BOSH, 100, 90, (), natija_pct=10.0),
        Savdo("B", BOSH, 100, 90, (), natija_pct=-5.0),
    ]
    assert n.profit_factor == pytest.approx(2.0)
    assert n.foydali_pct == pytest.approx(50.0)


def test_pasayish_choqqidan_olchanadi(config) -> None:  # noqa: ANN001
    from core.backtest.zanjir_engine import ZanjirNatijasi

    n = ZanjirNatijasi(nom="x")
    n.savdolar = [
        Savdo("A", BOSH, 100, 90, (), natija_pct=20.0),
        Savdo("B", BOSH, 100, 90, (), natija_pct=-30.0),
        Savdo("C", BOSH, 100, 90, (), natija_pct=5.0),
    ]
    assert n.eng_chuqur_pasayish == pytest.approx(30.0)
