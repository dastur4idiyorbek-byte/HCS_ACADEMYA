"""3.9-band: Kunlik Sham Ochilishi Skalping.

Bu strategiya HAR KUNI ISHLASHI SHART EMAS — shart bajarilmasa `None`
qaytadi va bu normal holat. Shuning uchun testlarning ko'pi aynan
"nima uchun signal berilmadi" ni tekshiradi.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.strategies import StrategyInput
from core.analysis.strategies.opening_range_scalp import (
    OpeningRangeScalpStrategy,
    scalp_trade_rules,
)
from core.config import load_config
from core.domain.enums import HalalStatus, SignalSource
from core.domain.models import Candle, HalalVerdict
from core.risk_engine import RiskContext, RiskEngine

KUN = datetime(2026, 8, 19, tzinfo=UTC)
HALOL = HalalVerdict("BTC", HalalStatus.HALAL, "halol")


def sham(ochilish: datetime, high: float, low: float, close: float, volume: float) -> Candle:
    return Candle(
        open_time=ochilish,
        open=(high + low) / 2,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def qator(
    *,
    ochilish_high: float = 100.6,
    ochilish_low: float = 100.0,
    ochilish_hajmi: float = 3000.0,
    yorib_otish: float = 100.9,
    oldingi_hajm: float = 1000.0,
    shamlar_soni: int = 30,
) -> list[Candle]:
    """Kechagi shamlar + bugungi ochilish + yorib o'tish shami."""
    natija: list[Candle] = []
    boshlanish = KUN - timedelta(minutes=15 * shamlar_soni)
    for i in range(shamlar_soni):
        vaqt = boshlanish + timedelta(minutes=15 * i)
        natija.append(sham(vaqt, 100.3, 99.7, 100.0, oldingi_hajm))

    natija.append(sham(KUN, ochilish_high, ochilish_low, ochilish_high, ochilish_hajmi))
    natija.append(
        sham(KUN + timedelta(minutes=15), yorib_otish, ochilish_high, yorib_otish, 1500.0)
    )
    return natija


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


@pytest.fixture
def strategy(config):  # noqa: ANN001, ANN201
    return OpeningRangeScalpStrategy(config)


def kirish(config, candles: list[Candle], now: datetime | None = None,  # noqa: ANN001
           verdict: HalalVerdict = HALOL) -> StrategyInput:
    tf = config.strategies.opening_range_scalp.timeframe
    return StrategyInput(
        symbol="BTC",
        now=now if now is not None else KUN + timedelta(minutes=20),
        halal_verdict=verdict,
        candles={tf: candles, "1d": candles},
    )


# --------------------------------------------------------------------------- #
#  Muvaffaqiyatli yo'l
# --------------------------------------------------------------------------- #


def test_shartlar_bajarilganda_nomzod_chiqadi(strategy, config) -> None:  # noqa: ANN001
    natija = strategy.analyze(kirish(config, qator()))

    assert natija is not None, f"rad sababi: {strategy.last_rejection}"
    assert natija.source is SignalSource.OPENING_RANGE_SCALP
    assert natija.symbol == "BTC"
    assert natija.score > 0


def test_stop_diapazon_ortasida(strategy, config) -> None:  # noqa: ANN001
    """Yorib o'tish yolg'on bo'lsa narx diapazon ichiga qaytadi — tez chiqish."""
    natija = strategy.analyze(kirish(config, qator(ochilish_high=100.6, ochilish_low=100.0)))

    assert natija is not None
    assert natija.levels.stop == pytest.approx(100.3), "diapazon o'rtasi"


def test_tp_kutilayotgan_harakat_oraligida(strategy, config) -> None:  # noqa: ANN001
    """3.9-band: 1-2% harakat kutiladi."""
    natija = strategy.analyze(kirish(config, qator()))
    skalp = config.strategies.opening_range_scalp

    assert natija is not None
    assert natija.levels.tp1_distance_pct == pytest.approx(skalp.min_move_pct)
    assert natija.levels.tp2_distance_pct == pytest.approx(skalp.max_move_pct)


def test_ball_yuzdan_oshmaydi(strategy, config) -> None:  # noqa: ANN001
    natija = strategy.analyze(kirish(config, qator(ochilish_hajmi=20000.0, yorib_otish=101.5)))

    assert natija is not None
    assert 0 <= natija.score <= 100
    assert natija.breakdown.maximum == pytest.approx(100)


# --------------------------------------------------------------------------- #
#  "Har kuni ishlashi shart emas" — rad etish holatlari
# --------------------------------------------------------------------------- #


def test_hajm_sakramasa_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    """Hajmsiz harakat ko'pincha yolg'on chiqadi."""
    natija = strategy.analyze(kirish(config, qator(ochilish_hajmi=1100.0)))

    assert natija is None
    assert strategy.last_rejection.stage == "volume"


def test_diapazon_juda_tor_bolsa_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    natija = strategy.analyze(
        kirish(config, qator(ochilish_high=100.05, ochilish_low=100.0, yorib_otish=100.1))
    )

    assert natija is None
    assert strategy.last_rejection.stage == "range"
    assert "tor" in strategy.last_rejection.detail


def test_diapazon_juda_keng_bolsa_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    """Keng diapazon — Stop juda uzoq qolardi."""
    natija = strategy.analyze(
        kirish(config, qator(ochilish_high=103.0, ochilish_low=100.0, yorib_otish=103.5))
    )

    assert natija is None
    assert strategy.last_rejection.stage == "range"
    assert "keng" in strategy.last_rejection.detail


def test_yorib_otmasa_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    """Spot: faqat yuqoriga yorib o'tish."""
    natija = strategy.analyze(kirish(config, qator(yorib_otish=100.4)))

    assert natija is None
    assert strategy.last_rejection.stage == "breakout"


def test_signal_oynasi_yopilgach_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    """Kech kirish eng yomon kirish."""
    kech = KUN + timedelta(minutes=120)
    natija = strategy.analyze(kirish(config, qator(), now=kech))

    assert natija is None
    assert strategy.last_rejection.stage == "window"


def test_bugungi_ochilish_yoq_bolsa_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    kechagi = [
        sham(KUN - timedelta(minutes=15 * (30 - i)), 100.3, 99.7, 100.0, 1000.0)
        for i in range(30)
    ]
    natija = strategy.analyze(kirish(config, kechagi))

    assert natija is None
    assert strategy.last_rejection.stage == "session"


def test_harom_coin_rad_etiladi(strategy, config) -> None:  # noqa: ANN001
    harom = HalalVerdict("XXX", HalalStatus.HARAM, "foizli qarz")
    natija = strategy.analyze(kirish(config, qator(), verdict=harom))

    assert natija is None
    assert strategy.last_rejection.stage == "halal"


def test_sham_yetmasa_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    natija = strategy.analyze(kirish(config, qator(shamlar_soni=3)))

    assert natija is None
    assert strategy.last_rejection.stage == "data"


def test_rad_sababi_har_doim_tushunarli(strategy, config) -> None:  # noqa: ANN001
    holatlar = [
        qator(ochilish_hajmi=1100.0),
        qator(yorib_otish=100.4),
        qator(ochilish_high=100.05, ochilish_low=100.0, yorib_otish=100.1),
    ]
    for shamlar in holatlar:
        assert strategy.analyze(kirish(config, shamlar)) is None
        assert strategy.last_rejection.detail
        assert len(strategy.last_rejection.detail) > 20, "sabab tushunarli bo'lishi kerak"


# --------------------------------------------------------------------------- #
#  Ball darajali baholanadi
# --------------------------------------------------------------------------- #


def test_kuchli_hajm_kop_ball_beradi(strategy, config) -> None:  # noqa: ANN001
    zaif = strategy.analyze(kirish(config, qator(ochilish_hajmi=2100.0)))
    kuchli = strategy.analyze(kirish(config, qator(ochilish_hajmi=8000.0)))

    assert zaif is not None and kuchli is not None
    assert (
        kuchli.breakdown.component("volume_surge").earned
        > zaif.breakdown.component("volume_surge").earned
    )


def test_aniqroq_yorib_otish_kop_ball_beradi(strategy, config) -> None:  # noqa: ANN001
    zaif = strategy.analyze(kirish(config, qator(yorib_otish=100.65)))
    kuchli = strategy.analyze(kirish(config, qator(yorib_otish=101.0)))

    assert zaif is not None and kuchli is not None
    assert (
        kuchli.breakdown.component("direction_clarity").earned
        > zaif.breakdown.component("direction_clarity").earned
    )


# --------------------------------------------------------------------------- #
#  3.3-band ziddiyati: Risk Engine strategiyaga qarab moslashadi
# --------------------------------------------------------------------------- #


def test_skalp_signali_risk_engine_dan_otadi(strategy, config) -> None:  # noqa: ANN001
    """Universal TP oralig'i (3-5%) skalpingga (1-2%) to'g'ri kelmaydi.

    Moslashuv bo'lmasa, skalping signallari HAR DOIM rad etilardi — ya'ni
    spetsifikatsiyada talab qilingan strategiya hech qachon ishlamasdi.
    """
    from core.analysis.market_health import HealthInputs, MarketHealthCalculator

    nomzod = strategy.analyze(kirish(config, qator()))
    assert nomzod is not None

    salomatlik = MarketHealthCalculator(config).compute(
        HealthInputs(
            computed_at=KUN,
            btc_dominance_change_24h=0.1,
            universe_trends={"BTC": __import__(
                "core.domain.enums", fromlist=["TrendDirection"]
            ).TrendDirection.UP},
            universe_adx={"BTC": 45.0},
            open_signals=0,
            max_open_signals=5,
        )
    )
    kontekst = RiskContext(
        now=KUN + timedelta(minutes=20),
        market_health=salomatlik,
        btc_change_24h_pct=1.0,
        adx=30.0,
        atr_pct=1.5,
        price_age_seconds=5.0,
    )

    qaror = RiskEngine(config).evaluate(nomzod, kontekst)
    assert qaror.allowed, qaror.details


def test_asosiy_strategiya_chegarasi_ozgarmagan(config) -> None:  # noqa: ANN001
    """Skalping uchun yumshatish asosiy strategiyaga ta'sir qilmasligi kerak."""
    qoida = next(r for r in RiskEngine(config).rules if r.name == "trade_rules")

    assert qoida._bounds_for(SignalSource.CLASSIC_TA) == (
        config.trade_rules.min_tp_distance_pct,
        config.trade_rules.max_tp_distance_pct,
        config.trade_rules.min_risk_reward,
        config.trade_rules.min_stop_distance_pct,
    )


def test_skalping_tor_stop_ishlata_oladi(config) -> None:  # noqa: ANN001
    """Skalping TABIATAN tor Stop bilan ishlaydi — universal 1% chegara unga tegmasin.

    3.3-band tuzatilgandan keyin universal minimal Stop 1% bo'ldi. Lekin
    kunlik diapazonning narigi chekkasi odatda 1% dan yaqin — universal
    chegarani qo'llash bu strategiyani imkonsiz qilardi.
    """
    qoida = next(r for r in RiskEngine(config).rules if r.name == "trade_rules")

    _, _, _, skalp_min_stop = qoida._bounds_for(SignalSource.OPENING_RANGE_SCALP)
    _, _, _, asosiy_min_stop = qoida._bounds_for(SignalSource.CLASSIC_TA)

    assert skalp_min_stop < asosiy_min_stop


def test_skalp_chegaralari_konfiguratsiyadan_olinadi(config) -> None:  # noqa: ANN001
    skalp = config.strategies.opening_range_scalp
    min_tp, max_tp, _, min_stop = scalp_trade_rules(skalp)

    assert (min_tp, max_tp) == (skalp.min_move_pct, skalp.max_move_pct)


def test_stop_chegarasi_barcha_strategiyalar_uchun_bir_xil(config) -> None:  # noqa: ANN001
    """Stop 1% — kapital himoyasi, strategiya xususiyati emas."""
    qoida = next(r for r in RiskEngine(config).rules if r.name == "trade_rules")
    assert qoida._max_stop_pct == config.trade_rules.max_stop_distance_pct


# --------------------------------------------------------------------------- #
#  Plug-in interfeysi (6.1-band)
# --------------------------------------------------------------------------- #


def test_strategiya_interfeysga_mos(strategy) -> None:  # noqa: ANN001
    from core.analysis.strategies.base import Strategy

    assert isinstance(strategy, Strategy)
    assert strategy.name == "opening_range_scalp"
    assert strategy.required_timeframes()


def test_ochirilgan_strategiya_belgilanadi(config) -> None:  # noqa: ANN001
    ochiq = dataclasses.replace(config.strategies.opening_range_scalp, enabled=False)
    yangi = dataclasses.replace(
        config, strategies=dataclasses.replace(config.strategies, opening_range_scalp=ochiq)
    )
    assert not OpeningRangeScalpStrategy(yangi).enabled
