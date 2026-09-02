"""3.7-band: Bozor Salomatligi Indeksi — tizimning markaziy pulsi.

Indeks uchta narsani boshqaradi: signal ball chegarasi (3.5), ochiq
signallar limiti (4.2) va umuman signal berish/bermaslik (4.9). Shuning
uchun uning xatti-harakati aniq bo'lishi kerak.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.analysis.market_health import HealthInputs, MarketHealthCalculator, describe
from core.config import load_config
from core.domain.enums import HealthBand, TrendDirection
from core.domain.models import Candle
from core.position_sizing import AggregateCapacity
from core.risk_engine import RiskEngine

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def _zigzag(nuqtalar: list[float], qadam: int = 6) -> list[Candle]:
    """Burilish narxlari orqali silliq zigzag — struktura sinovlari uchun."""
    from datetime import timedelta

    shamlar: list[Candle] = []
    indeks = 0
    for i in range(len(nuqtalar) - 1):
        boshi, oxiri = nuqtalar[i], nuqtalar[i + 1]
        for j in range(qadam):
            narx = boshi + (oxiri - boshi) * (j + 1) / qadam
            shamlar.append(
                Candle(
                    open_time=HOZIR + timedelta(hours=indeks),
                    open=narx, high=narx + 0.05, low=narx - 0.05,
                    close=narx, volume=1000.0,
                )
            )
            indeks += 1
    oxirgi = nuqtalar[-1]
    for _ in range(qadam):
        shamlar.append(
            Candle(
                open_time=HOZIR + timedelta(hours=indeks),
                open=oxirgi, high=oxirgi + 0.05, low=oxirgi - 0.05,
                close=oxirgi, volume=1000.0,
            )
        )
        indeks += 1
    return shamlar


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


@pytest.fixture
def calculator(config):  # noqa: ANN001, ANN201
    return MarketHealthCalculator(config)


def kirish(**kwargs) -> HealthInputs:
    """Sog'lom bozor — barcha omillar yaxshi."""
    asosiy = {
        "computed_at": HOZIR,
        "btc_dominance": 54.0,
        "btc_dominance_change_24h": 0.1,
        "universe_structures": {f"C{i}": TrendDirection.UP for i in range(30)},
        "universe_adx": {f"C{i}": 45.0 for i in range(30)},
        "capacity": AggregateCapacity(10, 10, 1000.0, 1000.0),
        "open_signals": 0,
        "max_open_signals": 5,
    }
    return HealthInputs(**{**asosiy, **kwargs})


# --------------------------------------------------------------------------- #
#  Umumiy xatti-harakat
# --------------------------------------------------------------------------- #


def test_ideal_bozorda_indeks_yuqori(calculator) -> None:  # noqa: ANN001
    salomatlik = calculator.compute(kirish())

    # 100 EMAS: QT (AMDX) omili soatga bog'liq va faqat X davrida
    # to'liq ball beradi. Uning vazni 5, ya'ni shift 95-100 oralig'ida
    # yuradi — "yashil" bandga (80+) yetish uchun bu yetarli.
    assert salomatlik.value >= 95.0
    assert salomatlik.band is HealthBand.HIGH


def test_qt_omili_shiftni_bogmaydi(calculator) -> None:  # noqa: ANN001
    """Bu loyihada "erishib bo'lmas shift" uch marta muammo bo'lgan
    (32, 46, 47-bo'limlar). QT omili indeksni jimgina bo'g'masligi
    kerak.

    Davr endi SOATDAN emas, sham strukturasidan o'qiladi — shuning
    uchun sinov ham vaqtni emas, MA'LUMOTNI o'zgartiradi.
    """
    from datetime import timedelta

    def sham(i: int, h: float, low: float, c: float):  # noqa: ANN202
        from core.domain.models import Candle

        return Candle(
            open_time=HOZIR + timedelta(hours=i),
            open=c,
            high=h,
            low=low,
            close=c,
            volume=1000.0,
        )

    # Ma'lumot yo'q (davr aniqlanmaydi) va sokinlik (A davri)
    bosh = calculator.compute(kirish(reference_candles=[]))
    sokin = calculator.compute(
        kirish(
            reference_candles=[
                *[sham(i, 105, 95, 100) for i in range(14)],
                *[sham(14 + i, 100.5, 99.5, 100) for i in range(6)],
            ]
        )
    )

    assert bosh.value >= 95.0, "davr noma'lum bo'lsa ham shift baland qolsin"
    assert sokin.value >= 95.0


def test_qt_davri_soatga_bogliq_emas(calculator) -> None:  # noqa: ANN001
    """Bir xil ma'lumot — bir xil indeks, soat qanday bo'lishidan qat'i nazar."""
    from datetime import timedelta

    ertalab = calculator.compute(kirish(computed_at=HOZIR.replace(hour=3)))
    kechqurun = calculator.compute(kirish(computed_at=HOZIR.replace(hour=19)))

    assert ertalab.value == pytest.approx(kechqurun.value)
    assert timedelta(hours=16)  # vaqt farqi bor, natija esa bir xil


def test_yomon_bozorda_indeks_past(calculator) -> None:  # noqa: ANN001
    salomatlik = calculator.compute(
        kirish(
            btc_dominance_change_24h=-3.0,
            universe_structures={f"C{i}": TrendDirection.DOWN for i in range(30)},
            universe_adx={f"C{i}": 12.0 for i in range(30)},
            capacity=AggregateCapacity(10, 0, 0.0, 1000.0),
            open_signals=5,
        )
    )

    assert salomatlik.value < 40
    assert salomatlik.band is HealthBand.LOW


def test_indeks_har_doim_0_100_oraligida(calculator) -> None:  # noqa: ANN001
    holatlar = [
        kirish(),
        kirish(btc_dominance_change_24h=-10.0),
        kirish(universe_structures={}, universe_adx={}, capacity=None),
        kirish(open_signals=100, max_open_signals=5),
    ]
    for holat in holatlar:
        assert 0 <= calculator.compute(holat).value <= 100


def test_vaznlar_yigindisi_yuz(config) -> None:  # noqa: ANN001
    assert config.market_health.weights.total() == pytest.approx(100)


# --------------------------------------------------------------------------- #
#  Har bir omil alohida
# --------------------------------------------------------------------------- #


def test_btc_dominance_keskin_ozgarsa_ball_tushadi(calculator) -> None:  # noqa: ANN001
    barqaror = calculator.compute(kirish(btc_dominance_change_24h=0.1))
    keskin = calculator.compute(kirish(btc_dominance_change_24h=3.0))

    assert barqaror.value > keskin.value


def test_dominance_ikki_tomonga_ham_xavfli(calculator) -> None:  # noqa: ANN001
    """Keskin o'sish ham, keskin tushish ham kapital oqimi almashuvini bildiradi."""
    osish = calculator.compute(kirish(btc_dominance_change_24h=3.0))
    tushish = calculator.compute(kirish(btc_dominance_change_24h=-3.0))

    assert osish.value == pytest.approx(tushish.value)


def test_trend_kengligi_ulushga_mos(calculator) -> None:  # noqa: ANN001
    """Bir nechta coin ko'tarilib, qolgani tushayotgan bo'lsa — bu ko'tarilish emas."""
    keng = {f"C{i}": TrendDirection.UP for i in range(30)}
    tor = {f"C{i}": (TrendDirection.UP if i < 6 else TrendDirection.DOWN) for i in range(30)}

    assert (
        calculator.compute(kirish(universe_structures=keng)).value
        > calculator.compute(kirish(universe_structures=tor)).value
    )


def test_tekis_bozorda_volatillik_bali_nol(calculator, config) -> None:  # noqa: ANN001
    past_adx = calculator.compute(
        kirish(universe_adx={f"C{i}": 10.0 for i in range(30)})
    )
    omil = next(f for f in past_adx.factors if f.name == "volatility_regime")

    assert omil.score == 0.0
    assert "tekis" in omil.explanation


def test_foydalanuvchilar_band_bolsa_indeks_tushadi(calculator) -> None:  # noqa: ANN001
    """5.2-band: "odamlar allaqachon band, yana signal keraksiz"."""
    bosh = calculator.compute(kirish(capacity=AggregateCapacity(10, 10, 1000.0, 1000.0)))
    band = calculator.compute(kirish(capacity=AggregateCapacity(10, 2, 200.0, 1000.0)))

    assert bosh.value > band.value


def test_signallar_toyinganda_indeks_tushadi(calculator) -> None:  # noqa: ANN001
    bosh = calculator.compute(kirish(open_signals=0))
    tolgan = calculator.compute(kirish(open_signals=5))

    assert bosh.value > tolgan.value


# --------------------------------------------------------------------------- #
#  Ma'lumot yo'q bo'lganda (0.3-band)
# --------------------------------------------------------------------------- #


def test_malumotsiz_indeks_past_boladi(calculator) -> None:  # noqa: ANN001
    """Ma'lumot yo'q -> indeks 40 dan past -> yangi signal berilmaydi."""
    salomatlik = calculator.compute(
        HealthInputs(computed_at=HOZIR, max_open_signals=5)
    )

    assert salomatlik.band is HealthBand.LOW
    assert salomatlik.value < 40


def test_foydalanuvchi_yoq_bolsa_sigim_toliq(calculator) -> None:  # noqa: ANN001
    """Foydalanuvchi yo'qligi tizimni o'zini cheklashiga sabab bo'lmasin."""
    salomatlik = calculator.compute(kirish(capacity=None))
    omil = next(f for f in salomatlik.factors if f.name == "aggregate_user_capacity")

    assert omil.score == 1.0


@pytest.mark.parametrize(
    "yoq",
    ["btc_dominance_change_24h", "universe_structures", "universe_adx"],
)
def test_har_bir_bozor_omili_yoq_bolsa_ball_nol(calculator, yoq: str) -> None:  # noqa: ANN001
    bosh = {"universe_structures": {}, "universe_adx": {}}.get(yoq)
    salomatlik = calculator.compute(kirish(**{yoq: bosh}))

    tegishli = {
        "btc_dominance_change_24h": "btc_dominance_stability",
        "universe_structures": "halal_structure_breadth",
        "universe_adx": "volatility_regime",
    }[yoq]
    omil = next(f for f in salomatlik.factors if f.name == tegishli)
    assert omil.score == 0.0


# --------------------------------------------------------------------------- #
#  Kunlik oldindan tahlil
# --------------------------------------------------------------------------- #


def test_kunlik_tahlil_STRUKTURAGA_tayanadi(calculator) -> None:  # noqa: ANN001
    """Manba o'zgardi: BTC Dominance emas, SMC struktura kengligi.

    Dominance foydali, lekin ko'pchilik treyder uchun qaror mezoni
    emas — 57-bo'lim. Endi kun boshidagi taxmin "nechta coin HH/HL
    strukturasida" degan savolga tayanadi.
    """
    yaxshi = calculator.daily_preview(
        kirish(universe_structures={f"C{i}": TrendDirection.UP for i in range(30)})
    )
    yomon = calculator.daily_preview(
        kirish(universe_structures={f"C{i}": TrendDirection.DOWN for i in range(30)})
    )

    assert yaxshi.value > yomon.value


def test_kunlik_tahlilda_dominance_endi_hal_qilmaydi(calculator) -> None:  # noqa: ANN001
    """Dominance kun boshida neytral — u endi taxminni boshqarmaydi."""
    yaxshi = calculator.daily_preview(kirish(btc_dominance_change_24h=0.1))
    yomon = calculator.daily_preview(kirish(btc_dominance_change_24h=3.0))

    assert yaxshi.value == pytest.approx(yomon.value)


def test_kunlik_tahlilda_boshqa_omillar_neytral(calculator) -> None:  # noqa: ANN001
    """Nol qo'yilsa kun boshida tizim har doim "qizil" bo'lardi."""
    tahlil = calculator.daily_preview(kirish())

    olchanadigan = {"halal_structure_breadth", "quarterly_phase"}
    boshqalar = [f for f in tahlil.factors if f.name not in olchanadigan]
    assert all(f.score == 0.5 for f in boshqalar)
    assert tahlil.band is not HealthBand.LOW


# --------------------------------------------------------------------------- #
#  Indeks tizimning boshqa qismlarini boshqaradi
# --------------------------------------------------------------------------- #


def test_indeks_ball_chegarasini_boshqaradi(calculator, config) -> None:  # noqa: ANN001
    """3.5-band: chegara statik EMAS."""
    engine = RiskEngine(config)

    yuqori = calculator.compute(kirish())
    past = calculator.compute(
        kirish(
            btc_dominance_change_24h=-3.0,
            universe_structures={f"C{i}": TrendDirection.DOWN for i in range(30)},
            universe_adx={f"C{i}": 10.0 for i in range(30)},
            capacity=AggregateCapacity(10, 0, 0.0, 1000.0),
            open_signals=5,
        )
    )

    assert engine.score_threshold(yuqori.value) is not None
    # Past indeks endi to'xtatmaydi, chegarani QATTIQLASHTIRADI:
    # o'sha payt narxlar arzonlashgan bo'ladi va "arzon ol"
    # strategiyasi uchun ko'zni yumish mantiqqa zid edi.
    past_chegara = engine.score_threshold(past.value)
    assert past_chegara is not None
    assert past_chegara > engine.score_threshold(yuqori.value)


def test_indeks_diapazon_chegaralari(calculator) -> None:  # noqa: ANN001
    """80 va 40 — spetsifikatsiyada belgilangan chegaralar."""
    from core.domain.models import MarketHealth

    assert MarketHealth(80.0, [], HOZIR).band is HealthBand.HIGH
    assert MarketHealth(79.9, [], HOZIR).band is HealthBand.MID
    assert MarketHealth(40.0, [], HOZIR).band is HealthBand.MID
    assert MarketHealth(39.9, [], HOZIR).band is HealthBand.LOW


# --------------------------------------------------------------------------- #
#  Admin dashboardi (3.7-band)
# --------------------------------------------------------------------------- #


def test_dashboard_matni_sababni_korsatadi(calculator) -> None:  # noqa: ANN001
    """"Tizim nega sokin?" — bitta raqam javob beradi, omillar sababni."""
    matn = describe(calculator.compute(kirish(open_signals=5)))

    assert "Bozor Salomatligi" in matn
    assert "Faol signallar" in matn
    assert "BTC Dominance" in matn


def test_dashboard_omillarni_ahamiyat_boyicha_tartiblaydi(calculator) -> None:  # noqa: ANN001
    matn = describe(calculator.compute(kirish()))
    qatorlar = [q for q in matn.splitlines() if "▰" in q or "▱" in q]
    assert len(qatorlar) == 6  # EMA kengligi omili olib tashlandi (59-bo'lim)


# --------------------------------------------------------------------------- #
#  Volatillik omili — o'lchov birligi (32-bo'lim)
# --------------------------------------------------------------------------- #


def test_ideal_bozor_toliq_ball_oladi() -> None:
    """Indeks o'z shkalasini to'liq ishlata olishi kerak.

    Regressiya: to'liq ball uchun 30 ta coinning O'RTACHA ADX'i 40 ga
    yetishi talab qilinardi. Bitta coinda ADX 40 — kuchli trend, lekin
    o'rtacha 40 ga deyarli chiqmaydi (coinlar har xil vaqtda trendga
    kiradi). Natijada eng ideal bozor ham 90/100 dan oshmasdi va
    volatillik omili amalda hech qachon to'liq ball bermasdi.
    """
    from core.analysis.market_health import HealthInputs, MarketHealthCalculator
    from core.config import load_config
    from core.domain.enums import TrendDirection

    config = load_config()
    natija = MarketHealthCalculator(config).compute(
        HealthInputs(
            computed_at=datetime(2026, 8, 21, 20, tzinfo=UTC),
            # X davri — QT omili to'liq ball beradi. Davr endi SOATDAN
            # emas, sham strukturasidan o'qiladi: buzilish bo'lgan va
            # narx undan keyin ham ushlab turibdi.
            reference_candles=_zigzag([100, 112, 106, 124, 116, 138]),
            btc_dominance=54.0,
            btc_dominance_change_24h=0.2,
            universe_structures={f"C{i}": TrendDirection.UP for i in range(30)},
            universe_adx={f"C{i}": config.market_health.strong_trend_adx for i in range(30)},
            capacity=None,
            open_signals=0,
            max_open_signals=5,
        )
    )

    assert natija.value == pytest.approx(100.0)


def test_volatillik_chegarasi_sozlanadi() -> None:
    """6.4-band: kodda sehrli raqam bo'lmasin."""
    from core.analysis.market_health.factors import volatility_regime_factor
    from core.analysis.market_health.inputs import HealthInputs

    kirish = HealthInputs(
        computed_at=datetime(2026, 8, 21, tzinfo=UTC),
        universe_adx={f"C{i}": 30.0 for i in range(30)},
    )

    past = volatility_regime_factor(kirish, 20.0, 20.0, strong_trend_adx=30.0)
    baland = volatility_regime_factor(kirish, 20.0, 20.0, strong_trend_adx=40.0)

    assert past.score == 1.0
    assert baland.score < 1.0


def test_tekis_bozorda_volatillik_nol() -> None:
    """Chegaradan past — S/R zonalari ishonchsiz, ball berilmaydi."""
    from core.analysis.market_health.factors import volatility_regime_factor
    from core.analysis.market_health.inputs import HealthInputs

    kirish = HealthInputs(
        computed_at=datetime(2026, 8, 21, tzinfo=UTC),
        universe_adx={f"C{i}": 15.0 for i in range(30)},
    )

    assert volatility_regime_factor(kirish, 20.0, 20.0).score == 0.0


# --------------------------------------------------------------------------- #
#  Sinov davri: indeks FAQAT bozor ma'lumotidan
# --------------------------------------------------------------------------- #

SINOV_ICHIDA = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
SINOV_TUGAGACH = datetime(2027, 3, 1, 12, 0, tzinfo=UTC)


def _omil(salomatlik, nom: str):  # noqa: ANN001, ANN202
    return next(o for o in salomatlik.factors if o.name == nom)


def test_sinov_davrida_sigim_indeksga_qoshilmaydi(calculator) -> None:  # noqa: ANN001
    """Sig'im bozorni emas, BIZNING holatimizni o'lchaydi.

    Sinov paytida obunachi yo'q — bu omil bozor haqida hech narsa
    aytmaydi. Ommaga ko'rsatiladigan natijaga obunachilar soni
    aralashmasligi kerak.
    """
    salomatlik = calculator.compute(kirish(computed_at=SINOV_ICHIDA))

    sigim = _omil(salomatlik, "aggregate_user_capacity")
    assert sigim.weight == 0.0
    assert sigim.weighted == 0.0
    assert "Sinov davri" in sigim.explanation


def test_sinov_davrida_ham_shkala_0_100_qoladi(calculator) -> None:  # noqa: ANN001
    """1-naqsh: "shkala mos kelmasligi".

    Omil shunchaki olib tashlansa, indeksning yuqori chegarasi 100 dan
    80 ga tushardi va 55 va 70 chegaralari jimgina boshqa ma'no olardi.
    Shuning uchun vazn qolgan omillarga taqsimlanadi.
    """
    salomatlik = calculator.compute(kirish(computed_at=SINOV_ICHIDA))

    jami_vazn = sum(o.weight for o in salomatlik.factors)
    assert jami_vazn == pytest.approx(100.0)
    # Ideal bozorda indeks avvalgidek yuqori bandga chiqa oladi
    assert salomatlik.value >= 95.0
    assert salomatlik.band is HealthBand.HIGH


def test_sinov_davrida_bosh_sigim_indeksni_tushirmaydi(calculator) -> None:  # noqa: ANN001
    """Aynan shu holat uchun qilindi: bitta test foydalanuvchisi
    limitiga yaqinlashsa, indeks tushib ketardi — bozor esa
    o'zgarmagan bo'lardi."""
    tolgan = kirish(
        computed_at=SINOV_ICHIDA, capacity=AggregateCapacity(10, 0, 0.0, 1000.0)
    )
    bosh = kirish(
        computed_at=SINOV_ICHIDA, capacity=AggregateCapacity(10, 10, 1000.0, 1000.0)
    )

    assert calculator.compute(tolgan).value == pytest.approx(
        calculator.compute(bosh).value
    )


def test_sinov_tugagach_omil_ozi_qaytadi(calculator) -> None:  # noqa: ANN001
    """Muddat tugagach hech kim hech narsani yoqishi shart emas."""
    salomatlik = calculator.compute(kirish(computed_at=SINOV_TUGAGACH))

    sigim = _omil(salomatlik, "aggregate_user_capacity")
    assert sigim.weight == 20.0
    assert "Sinov davri" not in sigim.explanation


def test_sinov_tugagach_sigim_yana_tasir_qiladi(calculator) -> None:  # noqa: ANN001
    tolgan = kirish(
        computed_at=SINOV_TUGAGACH, capacity=AggregateCapacity(10, 0, 0.0, 1000.0)
    )
    bosh = kirish(
        computed_at=SINOV_TUGAGACH, capacity=AggregateCapacity(10, 10, 1000.0, 1000.0)
    )

    assert calculator.compute(tolgan).value < calculator.compute(bosh).value


def test_kunlik_oldindan_tahlilda_ham_qollanadi(calculator) -> None:  # noqa: ANN001
    """Kun boshidagi tahlil ham xuddi shu indeks — ikkalasi bir xil
    qoidaga bo'ysunishi kerak, aks holda kun davomida shkala o'zgarardi."""
    salomatlik = calculator.daily_preview(kirish(computed_at=SINOV_ICHIDA))

    assert _omil(salomatlik, "aggregate_user_capacity").weight == 0.0
    assert sum(o.weight for o in salomatlik.factors) == pytest.approx(100.0)


def test_qolgan_kun_sanogi_kamayib_boradi(config) -> None:  # noqa: ANN001
    sinov = config.sinov
    assert sinov.qolgan_kun(SINOV_ICHIDA) > sinov.qolgan_kun(
        datetime(2026, 11, 1, tzinfo=UTC)
    )
    assert sinov.qolgan_kun(SINOV_TUGAGACH) == 0
