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


def qaytishdagi_kotarilish(n: int = 260, qaytish: int = 25) -> list[Candle]:
    """Haqiqiy pullback: uzoq ko'tarilish, so'ng EMA50 ostiga tushish.

    Narx EMA50 dan PAST, lekin EMA200 dan YUQORI va EMA50 > EMA200 —
    ya'ni trend tuzilishi buzilmagan, faqat vaqtincha qaytish. Aynan shu
    holat support zonasini yaratadi.
    """
    narxlar = [100 + i * 0.4 for i in range(n - qaytish)]
    narxlar += [narxlar[-1] - 0.9 * (i + 1) for i in range(qaytish)]
    return [sham(i, narx) for i, narx in enumerate(narxlar)]


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
    """Ko'tarilish trendi, oxirida support ustiga qaytish va burilish.

    Shakl ATAYLAB aniq S/R darajalari bilan qurilgan (tsikllardan hosil
    qilish o'rniga) — shunda zonalar aniq shakllanadi va sinov natijasi
    tasodifga bog'liq bo'lmaydi.

    O'lchangan natija: Stop 1.49% (3.3-banddagi 1..5% oralig'ining
    o'rtasi), zona joylashuvi 36% (aniq Discount), nisbat 1:3.0.

    Fitil kengligi (0.8%) muhim: ATR shundan hisoblanadi, ATR esa
    "narx zonaga yaqinmi" va Stop masofasini belgilaydi. Juda tor fitil
    bilan Stop har doim 1% dan yaqin chiqib, signal rad etilardi.
    """
    SUPPORT, RESISTANCE = 8000.0, 8480.0   # 6% diapazon
    FITIL = 0.008                          # ATR ~1.6% -> zonalar mazmunli
    KOTARILISH = 0.005                     # har tsiklda ~0.5% yuqoriga
    OXIRGI_ULUSH = 0.34                    # diapazonning pastki uchdan biri

    shamlar: list[Candle] = []
    i = 0

    def qoshish(narx: float, hajm: float = 1000.0) -> None:
        nonlocal i
        shamlar.append(
            sham(i, narx, narx * (1 + FITIL), narx * (1 - FITIL), volume=hajm)
        )
        i += 1

    for tsikl in range(12):
        siljish = 1 + tsikl * KOTARILISH
        for ulush in (0.05, 0.45, 0.95, 0.60, 0.20, 0.05):
            narx = (SUPPORT + (RESISTANCE - SUPPORT) * ulush) * siljish
            for _ in range(3):
                qoshish(narx)

    # Oxirgi qaytish: narx support ustida to'xtaydi, hajm oshib burilish
    # boshlanadi.
    siljish = 1 + 11 * KOTARILISH
    tayanch = (SUPPORT + (RESISTANCE - SUPPORT) * OXIRGI_ULUSH) * siljish
    for j in range(6):
        qoshish(tayanch, hajm=2700.0 if j >= 4 else 1200.0)

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


def test_tasdiqlanmagan_omil_ballni_tushiradi(config) -> None:  # noqa: ANN001
    """Indikatorlar qattiq to'siq EMAS — ularning yo'qligi ballni tushiradi.

    Bu test ilgari boshqacha yozilgan edi: "MACD tasdiqlamagan nomzod eng
    past chegaradan ham o'tmasligi kerak". Talab mantiqiy eshitilardi,
    lekin u ikkita faktni birga hisobga olmasdi:

      • support zonasida xarid qilinganda MACD deyarli HAR DOIM signal
        chizig'idan pastda bo'ladi (kesish keyinroq keladi);
      • ya'ni bu talab "support'da hech qachon xarid qilinmasin" degani
        bilan barobar edi.

    Chegara 80 bo'lgani uchun test o'tib turardi va muammo ko'rinmasdi.
    Endi u ASL xususiyatni tekshiradi: tasdiq yo'qligi ball tafsilotida
    ochiq ko'rinadi va yig'indini kamaytiradi.
    """
    natija = ClassicTaStrategy(config).analyze(kirish(config, qaytishli_kotarilish()))
    assert natija is not None

    macd = natija.breakdown.component("macd")
    assert macd is not None

    if macd.earned == 0:
        assert "tasdiq yo'q" in macd.explanation, "sabab ko'rinib turishi kerak"
        assert natija.score < natija.breakdown.maximum - macd.maximum + 0.01, (
            "tasdiqlanmagan omil yig'indiga qo'shilib qolmasligi kerak"
        )


def test_yuqori_timeframe_trendi_alohida_qoida_bilan_tasniflanadi(config) -> None:  # noqa: ANN001
    """3.2-band 3.1-band'dan alohida qoidaga ega — 27-bo'limda o'lchangan.

    Support zonasiga qaytish kunlik grafikda narxni deyarli har doim EMA50
    dan pastga tushiradi. Agar 3.1-band'ning "narx EMA'lardan yuqori"
    sharti yuqori timeframe TRENDINI tasniflashda ham qo'llanilsa, kunlik
    trend hech qachon `UP` bo'lmaydi va birorta signal chiqmaydi.

    Standart sozlamada ikki bayroq FARQ QILISHI kerak — aks holda
    tuzatish yo'qolgan bo'ladi.
    """
    indikatorlar = config.analysis.indicators

    assert indikatorlar.trend_requires_price_above_fast is True, "3.1-band qat'iy qoladi"
    assert indikatorlar.htf_trend_requires_price_above_fast is False, (
        "3.2-band tuzilma bo'yicha tasniflanadi (EMA50 > EMA200)"
    )


def test_qatiy_htf_qoidasi_qaytishda_trendni_yoqotadi(config) -> None:  # noqa: ANN001
    """Bayroq `True` bo'lsa, sog'lom qaytish "trend yo'q" deb o'qiladi.

    Bu test tuzatishning SABABINI qayd etadi. Yuqori timeframe qatori —
    haqiqiy pullback: EMA50 > EMA200 (trend buzilmagan), lekin narx EMA50
    dan past. Qat'iy qoida buni `FLAT` deb tasniflaydi va 3.2-band
    muvofiqligini abadiy buzadi — 27-bo'limdagi o'lchov shuni ko'rsatdi.
    """
    from core.analysis.indicators import timeframe_trend
    from core.domain.enums import TrendDirection

    shamlar = qaytishdagi_kotarilish()
    ind = config.analysis.indicators

    qatiy = timeframe_trend(shamlar, ind.ema_fast, ind.ema_slow, True)
    yumshoq = timeframe_trend(shamlar, ind.ema_fast, ind.ema_slow, False)

    assert qatiy is TrendDirection.FLAT, "qat'iy qoida sog'lom qaytishni ham rad etadi"
    assert yumshoq is TrendDirection.UP, "tuzilma bo'yicha trend hali ham ko'tarilishda"


def test_htf_bayrogi_strategiyada_qollaniladi(config) -> None:  # noqa: ANN001
    """Strategiya HTF trendini aynan `htf_trend_requires_price_above_fast` bilan tasniflaydi.

    Yuqori timeframe qaytishda bo'lganda: standart sozlama o'tkazadi,
    qat'iy sozlama `timeframes` bosqichida to'xtatadi.
    """
    qatiy_ind = dataclasses.replace(
        config.analysis.indicators, htf_trend_requires_price_above_fast=True
    )
    qatiy = dataclasses.replace(
        config, analysis=dataclasses.replace(config.analysis, indicators=qatiy_ind)
    )
    kiruvchi_shamlar = qaytishli_kotarilish()
    yuqori_shamlar = qaytishdagi_kotarilish()

    qatiy_strategiya = ClassicTaStrategy(qatiy)
    qatiy_strategiya.analyze(kirish(qatiy, kiruvchi_shamlar, htf=yuqori_shamlar))
    assert qatiy_strategiya.last_rejection is not None
    assert qatiy_strategiya.last_rejection.stage == "timeframes"

    standart = ClassicTaStrategy(config)
    natija = standart.analyze(kirish(config, kiruvchi_shamlar, htf=yuqori_shamlar))
    sabab = standart.last_rejection
    assert natija is not None or (sabab is not None and sabab.stage != "timeframes"), (
        "standart sozlamada yuqori timeframe to'sig'i chiqmasligi kerak"
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
