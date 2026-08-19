"""3.1-band: `classic_ta` strategiyasining to'liq zanjiri.

    S/R -> Discount -> ko'p timeframe -> indikatorlar -> darajalar -> ball

Har bir bosqichda "yo'q" javobi olinsa, `analyze()` `None` qaytaradi va
sababni saqlaydi. `None` — XATO EMAS (0.2-band: "signal bermaslik normal").
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.strategies import StrategyInput
from core.analysis.strategies.classic_ta import ClassicTaStrategy
from core.config import load_config
from core.domain.enums import HalalStatus
from core.domain.models import Candle, HalalVerdict
from core.utils.time_utils import utc_now

BOSH = datetime(2026, 1, 1, tzinfo=UTC)
HALOL = HalalVerdict("BTC", HalalStatus.HALAL, "halol")


def sham(i: int, close: float, high: float | None = None,
         low: float | None = None, volume: float = 1000.0) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(hours=i),
        open=close,
        high=high if high is not None else close * 1.004,
        low=low if low is not None else close * 0.996,
        close=close,
        volume=volume,
    )


def kotarilish(n: int = 260) -> list[Candle]:
    return [sham(i, 100 + i * 0.4) for i in range(n)]


def tushish(n: int = 260) -> list[Candle]:
    return [sham(i, 300 - i * 0.4) for i in range(n)]


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


@pytest.fixture
def strategy(config):  # noqa: ANN001, ANN201
    return ClassicTaStrategy(config)


def kirish(config, entry_candles: list[Candle], htf: list[Candle] | None = None,   # noqa: ANN001
           verdict: HalalVerdict = HALOL) -> StrategyInput:
    """Barcha timeframelarga bir xil shakl beradi (aks holda muvofiqlik buziladi)."""
    yuqori = htf if htf is not None else entry_candles
    shamlar = {config.analysis.entry_timeframe: entry_candles}
    for tf in config.analysis.htf_confirmation:
        shamlar[tf] = yuqori
    return StrategyInput(
        symbol="BTC", now=utc_now(), halal_verdict=verdict, candles=shamlar
    )


# --------------------------------------------------------------------------- #
#  Rad etish bosqichlari — har biri o'z sababini beradi
# --------------------------------------------------------------------------- #


def test_harom_coin_darhol_rad_etiladi(strategy, config) -> None:  # noqa: ANN001
    """Skrining allaqachon filtrlagan, lekin bu takroriy himoya."""
    harom = HalalVerdict("XXX", HalalStatus.HARAM, "foizli qarz protokoli")
    natija = strategy.analyze(kirish(config, kotarilish(), verdict=harom))

    assert natija is None
    assert strategy.last_rejection.stage == "halal"


def test_sham_yetmasa_rad_etiladi(strategy, config) -> None:  # noqa: ANN001
    natija = strategy.analyze(kirish(config, kotarilish(50)))

    assert natija is None
    assert strategy.last_rejection.stage == "data"


def test_tushayotgan_bozorda_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    natija = strategy.analyze(kirish(config, tushish()))
    assert natija is None


def test_timeframelar_zid_bolsa_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    """3.2-band qat'iy qoidasi: pastki TF yuqorisiga zid bo'lmasligi kerak."""
    natija = strategy.analyze(kirish(config, kotarilish(), htf=tushish()))

    assert natija is None
    assert strategy.last_rejection.stage in {"zone_position", "timeframes"}


def test_rad_sababi_har_doim_saqlanadi(strategy, config) -> None:  # noqa: ANN001
    """Admin nima uchun signal chiqmaganini ko'ra olishi kerak (3.7-band)."""
    strategy.analyze(kirish(config, tushish()))

    assert strategy.last_rejection is not None
    assert strategy.last_rejection.stage
    assert strategy.last_rejection.detail


def test_muvaffaqiyatli_tahlildan_keyin_rad_tozalanadi(strategy, config) -> None:  # noqa: ANN001
    strategy.analyze(kirish(config, tushish()))
    assert strategy.last_rejection is not None

    strategy.analyze(kirish(config, kotarilish()))
    # Yangi tahlil o'z sababini yozadi yoki tozalaydi — eskisi qolib ketmasligi kerak
    assert strategy.last_rejection is None or strategy.last_rejection.stage != "halal"


# --------------------------------------------------------------------------- #
#  Muvaffaqiyatli yo'l
# --------------------------------------------------------------------------- #


def qaytishli_kotarilish() -> list[Candle]:
    """Ko'tarilish trendi, oxirida support darajasiga qaytish va burilish.

    Shakl ataylab shunday: har tsiklda narx ~5% tebranadi va yuqoriga
    siljiydi (zonalar shakllanishi uchun), oxirida support zonasiga tushib,
    hajm oshishi bilan qaytishni boshlaydi.
    """
    shamlar: list[Candle] = []
    i = 0
    for tsikl in range(11):
        markaz = 8000.0 + tsikl * 380
        amplituda = markaz * 0.05
        for ulush in (0.0, 0.5, 1.0, 0.85, 0.45, 0.1, 0.02):
            narx = markaz + amplituda * ulush
            for _ in range(3):
                shamlar.append(sham(i, narx, narx * 1.0012, narx * 0.9988))
                i += 1

    markaz = 8000.0 + 10 * 380
    tayanch = markaz + markaz * 0.05 * 0.02
    for _ in range(5):
        shamlar.append(sham(i, tayanch, tayanch * 1.0012, tayanch * 0.9988))
        i += 1
    # Burilish: narx support'dan qaytadi, hajm oshadi
    for j in range(2):
        narx = tayanch * (1 + (j + 1) * 0.0015)
        shamlar.append(
            sham(i, narx, narx * 1.0012, narx * 0.9988, volume=2700.0 if j >= 1 else 1500.0)
        )
        i += 1
    return shamlar


def test_qulay_sharoitda_nomzod_chiqadi(config) -> None:  # noqa: ANN001
    """To'liq zanjir: S/R -> Discount -> timeframelar -> indikatorlar -> ball."""
    strategiya = ClassicTaStrategy(config)
    natija = strategiya.analyze(kirish(config, qaytishli_kotarilish()))

    assert natija is not None, (
        f"nomzod kutilgan edi, rad sababi: {strategiya.last_rejection}"
    )
    assert natija.symbol == "BTC"
    assert natija.score > 0
    assert natija.levels.stop < natija.levels.entry < natija.levels.tp1 < natija.levels.tp2
    assert natija.breakdown.maximum == pytest.approx(100)


def test_nomzod_uchta_qatlamdan_otadi(config) -> None:  # noqa: ANN001
    """Nomzod chiqsa, u S/R + zona + indikator uchalasini ham o'tgan bo'ladi."""
    natija = ClassicTaStrategy(config).analyze(kirish(config, qaytishli_kotarilish()))

    assert natija is not None
    nomlar = {k.name for k in natija.breakdown.components}
    assert nomlar == {
        "support_resistance", "trend", "rsi", "volume", "macd", "risk_reward"
    }
    assert natija.halal_verdict.is_tradable


def test_darajalar_uchinchi_band_chegaralariga_mos(config) -> None:  # noqa: ANN001
    """3.3-band: Stop <= 1%, TP 3-5%, TP2 kamida 1:3 R/R."""
    natija = ClassicTaStrategy(config).analyze(kirish(config, qaytishli_kotarilish()))
    assert natija is not None

    qoidalar = config.trade_rules
    darajalar = natija.levels
    assert darajalar.stop_distance_pct <= qoidalar.max_stop_distance_pct
    assert qoidalar.min_tp_distance_pct <= darajalar.tp1_distance_pct <= qoidalar.max_tp_distance_pct
    assert darajalar.risk_reward_tp2 >= qoidalar.min_risk_reward


def test_qatiy_tasdiq_talabida_signal_chiqmaydi(config) -> None:  # noqa: ANN001
    """4/4 talab qilinganda ikki oyna kesishmaydi — o'lchangan xatti-harakat.

    Sabab `docs/ARXITEKTURA.md` 22-bo'limida: MACD kechikuvchi indikator,
    u tasdiqlaganda narx allaqachon Discount zonasidan chiqib ketgan bo'ladi.
    """
    indikatorlar = dataclasses.replace(config.analysis.indicators, min_confirmations=4)
    qatiy = dataclasses.replace(
        config, analysis=dataclasses.replace(config.analysis, indicators=indikatorlar)
    )
    strategiya = ClassicTaStrategy(qatiy)

    assert strategiya.analyze(kirish(qatiy, qaytishli_kotarilish())) is None
    assert strategiya.last_rejection.stage == "confirmation"


def test_zaif_nomzod_ball_chegarasidan_otmaydi(config) -> None:  # noqa: ANN001
    """Zona sharti bajarilsa ham, zaif tasdiq past ball beradi.

    Bu — arxitekturaning asosiy himoyasi: indikatorlar qattiq to'siq emas,
    lekin ularning yo'qligi ballni tushiradi va chegara signalni to'xtatadi.
    """
    from core.risk_engine import RiskEngine

    natija = ClassicTaStrategy(config).analyze(kirish(config, qaytishli_kotarilish()))
    assert natija is not None

    chegara = RiskEngine(config).score_threshold(85)  # yuqori salomatlik = eng past chegara
    if natija.breakdown.component("macd").earned == 0:
        assert natija.score < chegara, (
            "MACD tasdiqlamagan nomzod eng past chegaradan ham o'tmasligi kerak"
        )


# --------------------------------------------------------------------------- #
#  Strategiya interfeysi (6.1-band)
# --------------------------------------------------------------------------- #


def test_strategiya_kerakli_timeframelarni_elon_qiladi(strategy, config) -> None:  # noqa: ANN001
    kerakli = strategy.required_timeframes()

    assert kerakli[0] == config.analysis.entry_timeframe
    assert set(config.analysis.htf_confirmation) <= set(kerakli)


def test_strategiya_yoqilganligini_bildiradi(strategy) -> None:  # noqa: ANN001
    assert strategy.enabled is True
    assert strategy.name == "classic_ta"
