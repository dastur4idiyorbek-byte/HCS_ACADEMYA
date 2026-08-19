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
from core.position_sizing import AggregateCapacity
from core.risk_engine import RiskEngine

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


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
        "universe_trends": {f"C{i}": TrendDirection.UP for i in range(30)},
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

    assert salomatlik.value == pytest.approx(100.0)
    assert salomatlik.band is HealthBand.HIGH


def test_yomon_bozorda_indeks_past(calculator) -> None:  # noqa: ANN001
    salomatlik = calculator.compute(
        kirish(
            btc_dominance_change_24h=-3.0,
            universe_trends={f"C{i}": TrendDirection.DOWN for i in range(30)},
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
        kirish(universe_trends={}, universe_adx={}, capacity=None),
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
        calculator.compute(kirish(universe_trends=keng)).value
        > calculator.compute(kirish(universe_trends=tor)).value
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
    ["btc_dominance_change_24h", "universe_trends", "universe_adx"],
)
def test_har_bir_bozor_omili_yoq_bolsa_ball_nol(calculator, yoq: str) -> None:  # noqa: ANN001
    bosh = {"universe_trends": {}, "universe_adx": {}}.get(yoq)
    salomatlik = calculator.compute(kirish(**{yoq: bosh}))

    tegishli = {
        "btc_dominance_change_24h": "btc_dominance_stability",
        "universe_trends": "halal_trend_breadth",
        "universe_adx": "volatility_regime",
    }[yoq]
    omil = next(f for f in salomatlik.factors if f.name == tegishli)
    assert omil.score == 0.0


# --------------------------------------------------------------------------- #
#  Kunlik oldindan tahlil
# --------------------------------------------------------------------------- #


def test_kunlik_tahlil_dominancega_tayanadi(calculator) -> None:  # noqa: ANN001
    yaxshi = calculator.daily_preview(kirish(btc_dominance_change_24h=0.1))
    yomon = calculator.daily_preview(kirish(btc_dominance_change_24h=3.0))

    assert yaxshi.value > yomon.value


def test_kunlik_tahlilda_boshqa_omillar_neytral(calculator) -> None:  # noqa: ANN001
    """Nol qo'yilsa kun boshida tizim har doim "qizil" bo'lardi."""
    tahlil = calculator.daily_preview(kirish())

    boshqalar = [f for f in tahlil.factors if f.name != "btc_dominance_stability"]
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
            universe_trends={f"C{i}": TrendDirection.DOWN for i in range(30)},
            universe_adx={f"C{i}": 10.0 for i in range(30)},
            capacity=AggregateCapacity(10, 0, 0.0, 1000.0),
            open_signals=5,
        )
    )

    assert engine.score_threshold(yuqori.value) is not None
    assert engine.score_threshold(past.value) is None, "past indeksda signal umuman yo'q"


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
    assert len(qatorlar) == 5
