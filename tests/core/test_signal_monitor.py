"""4.1 va 4.2-band: dinamik chiqish va signal rotatsiyasi."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.config import load_config
from core.domain.enums import HalalStatus, SignalSource, SignalStatus
from core.domain.models import (
    HalalVerdict,
    ScoreBreakdown,
    ScoreComponent,
    Signal,
    SignalCandidate,
    SignalLevels,
)
from core.pipeline import SignalMonitor

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def darajalar() -> SignalLevels:
    return SignalLevels(entry=100, stop=99.2, tp1=103.5, tp2=104.5)


def signal(symbol: str = "BTC", score: float | None = 85.0) -> Signal:
    return Signal(
        symbol=symbol,
        levels=darajalar(),
        source=SignalSource.CLASSIC_TA,
        status=SignalStatus.ACTIVE,
        score=score,
    )


def nomzod(symbol: str, ball: float) -> SignalCandidate:
    return SignalCandidate(
        symbol=symbol,
        levels=darajalar(),
        source=SignalSource.CLASSIC_TA,
        breakdown=ScoreBreakdown(symbol, [ScoreComponent("jami", ball, 100, "sinov")]),
        halal_verdict=HalalVerdict(symbol, HalalStatus.HALAL, "halol"),
    )


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


@pytest.fixture
def monitor(config):  # noqa: ANN001, ANN201
    return SignalMonitor(config.risk_engine)


# --------------------------------------------------------------------------- #
#  4.1 — Dinamik chiqish
# --------------------------------------------------------------------------- #


def test_ball_keskin_pasaysa_ogohlantirish(monitor, config) -> None:  # noqa: ANN001
    pasayish = config.risk_engine.weakening.score_drop_points
    ogohlantirish = monitor.check_weakening(signal(score=85.0), current_score=85.0 - pasayish)

    assert ogohlantirish is not None
    assert ogohlantirish.drop == pytest.approx(pasayish)


def test_kichik_pasayish_ogohlantirmaydi(monitor) -> None:  # noqa: ANN001
    """Har kichik tebranishda ogohlantirish foydalanuvchini charchatardi."""
    assert monitor.check_weakening(signal(score=85.0), current_score=80.0) is None


def test_ball_yoq_signal_taqqoslanmaydi(monitor) -> None:  # noqa: ANN001
    """Qo'lda kiritilgan signalning boshlang'ich balli yo'q."""
    assert monitor.check_weakening(signal(score=None), current_score=30.0) is None


def test_ball_oshsa_ogohlantirish_yoq(monitor) -> None:  # noqa: ANN001
    assert monitor.check_weakening(signal(score=70.0), current_score=90.0) is None


# --------------------------------------------------------------------------- #
#  4.2 — Rotatsiya
# --------------------------------------------------------------------------- #


def test_sezilarli_farqda_almashtirish_tavsiya_etiladi(monitor, config) -> None:  # noqa: ANN001
    farq = config.risk_engine.rotation.min_score_gap
    tavsiya = monitor.suggest_rotation(
        weak_signals=[(signal("SOL"), 50.0)],
        candidates=[nomzod("AVAX", 50.0 + farq)],
        now=HOZIR,
    )

    assert tavsiya is not None
    assert tavsiya.weak_signal.symbol == "SOL"
    assert tavsiya.replacement.symbol == "AVAX"
    assert "zaiflashmoqda" in tavsiya.describe()
    assert "Almashtirish tavsiya etiladi" in tavsiya.describe()


def test_kichik_farqda_almashtirilmaydi(monitor) -> None:  # noqa: ANN001
    """Whipsaw himoyasi: kichik farq uchun pozitsiya almashtirilmaydi."""
    tavsiya = monitor.suggest_rotation(
        weak_signals=[(signal("SOL"), 70.0)],
        candidates=[nomzod("AVAX", 85.0)],
        now=HOZIR,
    )
    assert tavsiya is None


def test_faqat_eng_zaif_signal_almashtiriladi(monitor) -> None:  # noqa: ANN001
    """Bir vaqtda bir nechta almashtirish taklifi foydalanuvchini chalg'itardi."""
    tavsiya = monitor.suggest_rotation(
        weak_signals=[(signal("SOL"), 60.0), (signal("ADA"), 40.0), (signal("DOT"), 55.0)],
        candidates=[nomzod("AVAX", 95.0)],
        now=HOZIR,
    )

    assert tavsiya is not None
    assert tavsiya.weak_signal.symbol == "ADA", "eng past ballli signal tanlanishi kerak"


def test_eng_yuqori_ballli_nomzod_taklif_etiladi(monitor) -> None:  # noqa: ANN001
    tavsiya = monitor.suggest_rotation(
        weak_signals=[(signal("SOL"), 40.0)],
        candidates=[nomzod("AVAX", 80.0), nomzod("LINK", 95.0)],
        now=HOZIR,
    )
    assert tavsiya.replacement.symbol == "LINK"


def test_sovutish_davri_takroriy_tavsiyani_toxtatadi(monitor, config) -> None:  # noqa: ANN001
    """Ansiz tizim har sham yopilganda foydalanuvchini charchatardi."""
    zaif = [(signal("SOL"), 40.0)]
    yangi = [nomzod("AVAX", 95.0)]

    assert monitor.suggest_rotation(zaif, yangi, HOZIR) is not None
    assert monitor.suggest_rotation(zaif, yangi, HOZIR + timedelta(minutes=10)) is None


def test_sovutish_davridan_keyin_qayta_tavsiya(monitor, config) -> None:  # noqa: ANN001
    sovutish = config.risk_engine.rotation.cooldown_minutes
    zaif = [(signal("SOL"), 40.0)]
    yangi = [nomzod("AVAX", 95.0)]

    monitor.suggest_rotation(zaif, yangi, HOZIR)
    keyin = HOZIR + timedelta(minutes=sovutish + 1)
    assert monitor.suggest_rotation(zaif, yangi, keyin) is not None


def test_signal_yopilganda_sovutish_tozalanadi(monitor) -> None:  # noqa: ANN001
    zaif = [(signal("SOL"), 40.0)]
    yangi = [nomzod("AVAX", 95.0)]

    monitor.suggest_rotation(zaif, yangi, HOZIR)
    monitor.reset_cooldown("SOL")

    assert monitor.suggest_rotation(zaif, yangi, HOZIR + timedelta(minutes=1)) is not None


@pytest.mark.parametrize(
    ("zaiflar", "nomzodlar"),
    [([], [("AVAX", 95.0)]), ([("SOL", 40.0)], []), ([], [])],
)
def test_bosh_royxatlarda_tavsiya_yoq(monitor, zaiflar, nomzodlar) -> None:  # noqa: ANN001
    tavsiya = monitor.suggest_rotation(
        weak_signals=[(signal(s), b) for s, b in zaiflar],
        candidates=[nomzod(s, b) for s, b in nomzodlar],
        now=HOZIR,
    )
    assert tavsiya is None
