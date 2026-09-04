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
    from core.analysis.turlar import Holat, blok, blok_sozla, ha

    b = blok_sozla(
        blok("Zona Sifati", [ha("fibonacci"), ha("fvg")]),
        frozenset({"fibonacci"}),
    )
    holatlar = {t.nom: t.holat for t in b.tekshiruvlar}
    assert holatlar["fibonacci"] is Holat.MALUMOT_YOQ
    assert holatlar["fvg"] is Holat.HA
    assert b.maxraj == 1


def test_ablatsiya_blokni_bosh_qoldirsa_blok_otmaydi() -> None:
    """Yagona ijobiy tekshiruv o'chirilsa — blok 0/1 bo'lib qoladi."""
    from core.analysis.turlar import blok, blok_sozla, ha, yoq

    b = blok_sozla(
        blok("Zona Sifati", [ha("fibonacci"), yoq("fvg")]),
        frozenset({"fibonacci"}),
    )
    assert not b.otdi


def test_ablatsiya_ZANJIR_ICHIDA_qollanadi() -> None:
    """O'chirilgan tekshiruv nomzodni OLDINGA o'tkaza olsin.

    2026-09-04 da topilgan xato: ablatsiya zanjir TUGAGANDAN keyin
    qo'llanardi. Natijada 2-blokda uzilgan nomzodning 3- va
    4-bloklari umuman hisoblanmagan bo'lardi va tekshiruvni
    o'chirish uni oldinga o'tkaza olmasdi — ablatsiya faqat bitta
    yo'nalishda ishlardi.

    Bu test zanjirning uzilishi ablatsiyadan KEYIN hisoblanishini
    tekshiradi: struktura bloki faqat bitta ijobiy tekshiruv bilan
    o'tgan bo'lsa va o'sha tekshiruv o'chirilsa, zanjir aynan shu
    blokda uzilishi kerak — "nomalum" bo'lib qolmasligi kerak.
    """
    from core.analysis.chain.block_chain_engine import ZanjirKirish, zanjir_yur

    shamlar = seriya(200)
    ochiq = zanjir_yur(ZanjirKirish(symbol="BTC", shamlar=shamlar))
    hammasi = zanjir_yur(
        ZanjirKirish(
            symbol="BTC",
            shamlar=shamlar,
            ochirilgan=frozenset({
                "swing_ketma_ketligi", "bos_tasdiqlangan", "qarshi_choch_yoq",
                "nisbiy_kuch", "yangi_coin_naqshi",
            }),
        )
    )
    # Barcha tekshiruv o'chirilganda struktura bloki "o'lchanmadi"
    # holatiga tushadi va zanjirni UZMAYDI — ya'ni keyingi bloklar
    # HISOBLANADI. Eski mexanizmda bu mumkin emas edi.
    assert len(hammasi.zanjir.bloklar) >= len(ochiq.zanjir.bloklar)


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


# --------------------------------------------------------------------------- #
#  Oyna chegarasi — tezlik VA jonli bilan moslik
# --------------------------------------------------------------------------- #


def test_oyna_chegaralangan() -> None:
    """Chegarasiz qoldirilsa ikki narsa buziladi.

    (1) backtest jonlidan BOSHQA oynani ko'radi — jonli tizim
        birjadan butun tarixni so'ramaydi
    (2) har qadamda ish hajmi o'sadi (O(n²)) — 730 kunlik sinovda
        15 daqiqalik qator 89 000 shamgacha yetardi
    """
    from core.backtest.zanjir_engine import ASOSIY_OYNA, PASTKI_OYNA, _shamlar

    ds = Dataset()
    ds.add("BTC", "1d", seriya(1200))

    hammasi = ds.series["BTC"].up_to("1d", BOSH + timedelta(days=1500))
    kesilgan = _shamlar(ds, "BTC", "1d", BOSH + timedelta(days=1500))

    assert len(hammasi) == 1200
    assert len(kesilgan) == ASOSIY_OYNA
    # Eng SO'NGGI shamlar olinadi, eng eskilari emas
    assert kesilgan[-1].open_time == hammasi[-1].open_time
    assert PASTKI_OYNA > 0


def test_nomalum_coin_bosh_royxat() -> None:
    from core.backtest.zanjir_engine import _shamlar

    assert _shamlar(Dataset(), "YOQ", "1d", BOSH) == []


def test_sigim_ochiq_savdolar_sonini_cheklaydi(config) -> None:  # noqa: ANN001
    """`max_open_signals` dan ortiq savdo ochilmasin."""
    from core.backtest.zanjir_engine import ZanjirNatijasi

    dvigatel = ZanjirBacktest(config, "sinov", sigim=True)
    natija = ZanjirNatijasi(nom="sinov")
    ochiq: dict[str, Savdo] = {}
    nomzodlar = [
        (0.5 + i / 100, Savdo(f"C{i}", BOSH, 100.0, 95.0, (110.0,)))
        for i in range(config.risk_engine.max_open_signals + 3)
    ]

    dvigatel._joylashtir(nomzodlar, ochiq, natija)

    assert len(ochiq) == config.risk_engine.max_open_signals
    assert natija.sigim_radlari["max_open_signals"] == 3


def test_sigimsiz_hech_narsa_toslmaydi(config) -> None:  # noqa: ANN001
    """Sukut holat — sig'im O'CHIQ, zanjirning o'z sifati o'lchanadi."""
    from core.backtest.zanjir_engine import ZanjirNatijasi

    dvigatel = ZanjirBacktest(config, "sinov")
    natija = ZanjirNatijasi(nom="sinov")
    ochiq: dict[str, Savdo] = {}
    nomzodlar = [
        (0.5, Savdo(f"C{i}", BOSH, 100.0, 95.0, (110.0,)))
        for i in range(config.risk_engine.max_open_signals + 5)
    ]

    dvigatel._joylashtir(nomzodlar, ochiq, natija)

    assert len(ochiq) == len(nomzodlar)
    assert not natija.sigim_radlari


def test_sigim_korrelyatsiya_guruhini_hisobga_oladi(config) -> None:  # noqa: ANN001
    """Bitta guruhdan bitta signal — SOL va ADA birga ochilmasin."""
    from core.backtest.zanjir_engine import ZanjirNatijasi

    risk = config.risk_engine
    assert risk.correlation_group_of("SOL") == risk.correlation_group_of("ADA")

    dvigatel = ZanjirBacktest(config, "sinov", sigim=True)
    natija = ZanjirNatijasi(nom="sinov")
    ochiq: dict[str, Savdo] = {}
    nomzodlar = [
        (0.9, Savdo("SOL", BOSH, 100.0, 95.0, (110.0,))),
        (0.8, Savdo("ADA", BOSH, 100.0, 95.0, (110.0,))),
    ]

    dvigatel._joylashtir(nomzodlar, ochiq, natija)

    assert set(ochiq) == {"SOL"}
    assert natija.sigim_radlari["korrelyatsiya"] == 1


def test_sigimda_kuchli_nomzod_orinni_oladi(config) -> None:  # noqa: ANN001
    """O'rin cheklangan bo'lsa — ALIFBO emas, ISHONCH hal qilsin.

    Alifbo tartibida saralansa natija coinlar ro'yxatining tartibiga
    bog'lanib qolardi va o'lchov o'zi haqida yolg'on gapirardi.
    """
    from core.backtest.zanjir_engine import ZanjirNatijasi

    risk = config.risk_engine
    dvigatel = ZanjirBacktest(config, "sinov", sigim=True)
    natija = ZanjirNatijasi(nom="sinov")
    ochiq: dict[str, Savdo] = {}
    # "ZZZ" eng oxirgi, lekin ishonchi eng yuqori.
    nomzodlar = [
        (0.10, Savdo(f"AAA{i}", BOSH, 100.0, 95.0, (110.0,)))
        for i in range(risk.max_open_signals)
    ]
    nomzodlar.append((0.99, Savdo("ZZZ", BOSH, 100.0, 95.0, (110.0,))))

    dvigatel._joylashtir(nomzodlar, ochiq, natija)

    assert "ZZZ" in ochiq


def test_zaiflik_hisoboti_yigiladi(config, dataset) -> None:  # noqa: ANN001
    """Har bir tekshiruvning holati sanalsin.

    Modulning asl g'oyasi: katta blokni to'rtga bo'lish — qaysi
    biri ZAIF ekanini ko'rish uchun. Bu ma'lumot ilgari tizim
    ichida bor edi, lekin tashqariga chiqarilmasdi.
    """
    natija = ZanjirBacktest(config, "sinov").yur(dataset, ["BTC", "ETH"])

    assert natija.tekshiruv_holatlari
    for nom, hisob in natija.tekshiruv_holatlari.items():
        assert set(hisob) == {"ha", "yoq", "malumot_yoq"}, nom
        assert sum(hisob.values()) > 0, nom


def test_zaiflik_maxraji_har_xil(config, dataset) -> None:  # noqa: ANN001
    """1-blokdagi tekshiruv 4-blokdagidan KO'PROQ marta ko'riladi.

    Zanjir uzilganda keyingi bloklar umuman hisoblanmaydi. Agar
    hisobotda umumiy qadam soni maxraj qilib olinsa, 4-blokdagi
    tekshiruvlar sun'iy ravishda "zaif" ko'rinardi.
    """
    natija = ZanjirBacktest(config, "sinov").yur(dataset, ["BTC", "ETH"])
    holatlar = natija.tekshiruv_holatlari

    def jami(nom: str) -> int:
        return sum(holatlar.get(nom, {}).values())

    assert jami("bozor_holati") >= jami("swing_ketma_ketligi")
    assert jami("swing_ketma_ketligi") >= jami("liquidity_sweep")
