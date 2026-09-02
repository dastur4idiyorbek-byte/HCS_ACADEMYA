"""4-bo'lim: Risk Engine qoidalari.

Asosiy tamoyil sinovlari:
  - "VA" mantig'i: bitta qoida rad etsa, signal chiqmaydi
  - fail-safe: ma'lumot yetishmasa, signal BERILMAYDI (xato signal berilmaydi)
  - Juma filtri faqat YANGI signalga taalluqli
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.config.schema import AppConfig
from core.domain.enums import (
    BlockReason,
    HalalStatus,
    SignalSource,
    SignalStatus,
)
from core.domain.models import (
    HalalVerdict,
    MarketHealth,
    ScoreBreakdown,
    ScoreComponent,
    Signal,
    SignalCandidate,
    SignalLevels,
)
from core.risk_engine import RiskContext, RiskEngine

TOSHKENT_JUMA_NAMOZ = datetime(2026, 8, 21, 7, 30, tzinfo=UTC)  # Toshkentda 12:30
ODDIY_VAQT = datetime(2026, 8, 19, 10, 0, tzinfo=UTC)  # chorshanba


def salomatlik(qiymat: float) -> MarketHealth:
    return MarketHealth(value=qiymat, factors=[], computed_at=ODDIY_VAQT)


def nomzod(
    symbol: str = "ETH",
    stop_pct: float = 1.5,
    tp2_pct: float = 5.0,
    tp1_pct: float | None = None,
) -> SignalCandidate:
    """Sinov nomzodi.

    `tp1_pct` berilmasa TP2 gacha bo'lgan masofaning 70% ida turadi —
    shunda Stop qanday bo'lishidan qat'i nazar tartib (Stop < Entry <
    TP1 < TP2) buzilmaydi.
    """
    entry = 100.0
    if tp1_pct is None:
        tp1_pct = max(3.0, tp2_pct * 0.7)
    levels = SignalLevels(
        entry=entry,
        stop=entry * (1 - stop_pct / 100),
        tp1=entry * (1 + tp1_pct / 100),
        tp2=entry * (1 + tp2_pct / 100),
    )
    return SignalCandidate(
        symbol=symbol,
        levels=levels,
        source=SignalSource.CLASSIC_TA,
        breakdown=ScoreBreakdown(symbol, [ScoreComponent("s_r", 25, 25, "zonada")]),
        halal_verdict=HalalVerdict(symbol, HalalStatus.HALAL, "halol"),
    )


def sog_kontekst(now: datetime = ODDIY_VAQT, **kwargs) -> RiskContext:
    """Barcha qoidalar ruxsat beradigan "sog'lom" kontekst."""
    asosiy = {
        "now": now,
        "market_health": salomatlik(85),
        "btc_change_24h_pct": 1.5,
        "adx": 28.0,
        "atr_pct": 1.8,
        "price_age_seconds": 5.0,
    }
    return RiskContext(**{**asosiy, **kwargs})


@pytest.fixture
def engine(config: AppConfig) -> RiskEngine:
    return RiskEngine(config)


# --------------------------------------------------------------------------- #
#  Asosiy yo'l
# --------------------------------------------------------------------------- #


def test_soglom_sharoitda_signal_otadi(engine: RiskEngine) -> None:
    qaror = engine.evaluate(nomzod(), sog_kontekst())
    assert qaror.allowed, qaror.details


# --------------------------------------------------------------------------- #
#  4.8 — Juma namozi filtri
# --------------------------------------------------------------------------- #


def test_juma_namozi_vaqtida_yangi_signal_toxtaydi(engine: RiskEngine) -> None:
    qaror = engine.evaluate(nomzod(), sog_kontekst(now=TOSHKENT_JUMA_NAMOZ))
    assert not qaror.allowed
    assert BlockReason.FRIDAY_PRAYER in qaror.reasons


def test_juma_namozidan_keyin_signal_qaytadi(engine: RiskEngine) -> None:
    keyin = datetime(2026, 8, 21, 10, 30, tzinfo=UTC)  # Toshkentda 15:30
    assert engine.evaluate(nomzod(), sog_kontekst(now=keyin)).allowed


def test_juma_filtri_ochirilishi_mumkin(config: AppConfig) -> None:
    """Vaqt zonasi va oyna config qilinadigan bo'lishi kerak (4.8-band)."""
    import dataclasses

    friday = dataclasses.replace(config.risk_engine.friday_filter, enabled=False)
    risk = dataclasses.replace(config.risk_engine, friday_filter=friday)
    engine = RiskEngine(dataclasses.replace(config, risk_engine=risk))

    assert engine.evaluate(nomzod(), sog_kontekst(now=TOSHKENT_JUMA_NAMOZ)).allowed


# --------------------------------------------------------------------------- #
#  4.9 / 3.7 — Bozor Salomatligi
# --------------------------------------------------------------------------- #


def test_past_salomatlikda_signal_berilmaydi(engine: RiskEngine) -> None:
    qaror = engine.evaluate(nomzod(), sog_kontekst(market_health=salomatlik(25)))
    assert not qaror.allowed
    assert BlockReason.MARKET_HEALTH_LOW in qaror.reasons


def test_salomatlik_hisoblanmagan_bolsa_signal_berilmaydi(engine: RiskEngine) -> None:
    """Fail-safe: noaniqlikda signal BERMASLIKKA moyillik."""
    qaror = engine.evaluate(nomzod(), sog_kontekst(market_health=None))
    assert not qaror.allowed
    assert BlockReason.MARKET_HEALTH_LOW in qaror.reasons


def test_ball_chegarasi_salomatlikka_qarab_moslashadi(
    engine: RiskEngine, config
) -> None:  # noqa: ANN001
    """3.5-band: chegara statik EMAS.

    Aniq raqamlar konfiguratsiyadan olinadi, testga yozib qo'yilmaydi:
    ilgari bu yerda 70 va 80 turardi va aynan shu raqamlar erishib
    bo'lmas darajada baland ekani hech qanday testda ko'rinmasdi
    (`test_chegara_erishiladi.py` ga qarang).
    """
    chegaralar = config.scoring.thresholds

    assert engine.score_threshold(90) == chegaralar.threshold_high_health
    assert engine.score_threshold(60) == chegaralar.threshold_mid_health
    # Past band endi TO'XTATMAYDI — rejimni almashtiradi va talabni
    # qattiqlashtiradi. Ilgari bu yerda `None` kutilardi va aynan shu
    # tizimni doim KECH kirishga majburlagan edi.
    assert engine.score_threshold(20) == chegaralar.threshold_low_health
    assert engine.score_threshold(None) is None, "0.3-band: hisoblanmasa — yo'q"

    assert engine.score_threshold(60) >= engine.score_threshold(90), (
        "bozor zaiflashsa talab oshishi kerak"
    )
    assert engine.score_threshold(20) >= engine.score_threshold(60), (
        "pasayishdagi kirish eng ko'p dalil talab qiladi"
    )


# --------------------------------------------------------------------------- #
#  4.7 — Kill switch
# --------------------------------------------------------------------------- #


def test_kill_switch_hamma_narsani_toxtatadi(engine: RiskEngine) -> None:
    kontekst = sog_kontekst(kill_switch_active=True, kill_switch_reason="1 daqiqada -7%")
    qaror = engine.evaluate(nomzod(), kontekst)
    assert not qaror.allowed
    assert BlockReason.KILL_SWITCH in qaror.reasons
    assert "-7%" in " ".join(qaror.details)


# --------------------------------------------------------------------------- #
#  4.3 — Korrelyatsiya
# --------------------------------------------------------------------------- #


def test_korrelyatsiyalangan_coin_bloklanadi(engine: RiskEngine) -> None:
    """BTC ochiq bo'lsa, ETH uchun yangi signal berilmaydi (bir guruh)."""
    ochiq = Signal(
        symbol="BTC",
        levels=SignalLevels(100, 99, 103, 105),
        source=SignalSource.CLASSIC_TA,
        status=SignalStatus.ACTIVE,
    )
    qaror = engine.evaluate(nomzod("ETH"), sog_kontekst(open_signals=[ochiq]))
    assert not qaror.allowed
    assert BlockReason.CORRELATION in qaror.reasons


def test_boshqa_guruhdagi_coin_otadi(engine: RiskEngine) -> None:
    ochiq = Signal(
        symbol="BTC",
        levels=SignalLevels(100, 99, 103, 105),
        source=SignalSource.CLASSIC_TA,
        status=SignalStatus.ACTIVE,
    )
    assert engine.evaluate(nomzod("SOL"), sog_kontekst(open_signals=[ochiq])).allowed


# --------------------------------------------------------------------------- #
#  4.2 — Ochiq signallar chegarasi
# --------------------------------------------------------------------------- #


def test_ochiq_signallar_chegarasi(engine: RiskEngine, config: AppConfig) -> None:
    limit = config.risk_engine.max_open_signals_by_health.high
    ochiq = [
        Signal(
            symbol=f"C{i}",
            levels=SignalLevels(100, 99, 103, 105),
            source=SignalSource.CLASSIC_TA,
            status=SignalStatus.ACTIVE,
        )
        for i in range(limit)
    ]
    qaror = engine.evaluate(nomzod("ARB"), sog_kontekst(open_signals=ochiq))
    assert not qaror.allowed
    assert BlockReason.MAX_OPEN_SIGNALS in qaror.reasons


def test_ortacha_salomatlikda_chegara_qattiqroq(engine: RiskEngine, config: AppConfig) -> None:
    """Indeks pastroq bo'lsa, bir vaqtda kamroq signal ochiladi."""
    mid_limit = config.risk_engine.max_open_signals_by_health.mid
    ochiq = [
        Signal(
            symbol=f"C{i}",
            levels=SignalLevels(100, 99, 103, 105),
            source=SignalSource.CLASSIC_TA,
            status=SignalStatus.ACTIVE,
        )
        for i in range(mid_limit)
    ]
    kontekst = sog_kontekst(market_health=salomatlik(55), open_signals=ochiq)
    assert BlockReason.MAX_OPEN_SIGNALS in engine.evaluate(nomzod("ARB"), kontekst).reasons


# --------------------------------------------------------------------------- #
#  4.1 — Zarar chegarasi
# --------------------------------------------------------------------------- #


def test_kunlik_zarar_chegarasi(engine: RiskEngine, config: AppConfig) -> None:
    limit = config.risk_engine.daily_loss_limit_pct
    qaror = engine.evaluate(nomzod(), sog_kontekst(daily_loss_pct=limit))
    assert BlockReason.DAILY_LOSS_LIMIT in qaror.reasons


# --------------------------------------------------------------------------- #
#  4.10 / 3.8 — Ketma-ket zarar
# --------------------------------------------------------------------------- #


def test_ketma_ket_stop_signalni_toxtatadi(engine: RiskEngine, config: AppConfig) -> None:
    chegara = config.risk_engine.consecutive_loss.max_consecutive_stops
    qaror = engine.evaluate(nomzod(), sog_kontekst(consecutive_stops=chegara))
    assert BlockReason.CONSECUTIVE_LOSSES in qaror.reasons


def test_sovutish_davri_hurmat_qilinadi(engine: RiskEngine) -> None:
    kontekst = sog_kontekst(consecutive_stop_until=ODDIY_VAQT + timedelta(hours=5))
    assert BlockReason.CONSECUTIVE_LOSSES in engine.evaluate(nomzod(), kontekst).reasons


# --------------------------------------------------------------------------- #
#  4.5 / 4.6 / 6.2 — Bozor filtrlari va fail-safe
# --------------------------------------------------------------------------- #


def test_btc_keskin_tushganda_signal_yoq(engine: RiskEngine) -> None:
    qaror = engine.evaluate(nomzod(), sog_kontekst(btc_change_24h_pct=-8.0))
    assert BlockReason.BTC_MARKET_FILTER in qaror.reasons


def test_past_volatillikda_signal_yoq(engine: RiskEngine) -> None:
    qaror = engine.evaluate(nomzod(), sog_kontekst(atr_pct=0.2))
    assert BlockReason.LOW_VOLATILITY in qaror.reasons


def test_eskirgan_narx_malumoti_signalni_toxtatadi(engine: RiskEngine, config) -> None:  # noqa: ANN001
    """Chegara KONFIGURATSIYADAN hisoblanadi, testga yozib qo'yilmaydi.

    Ilgari bu yerda `600` turardi — 90 soniyalik tik chegarasiga
    mos edi. Chegara sham timeframeiga bog'lanishi bilan (1 soatlik
    shamda 2 soat) bu qiymat "eskirgan" bo'lishdan to'xtadi va test
    jimgina ma'nosini yo'qotardi.
    """
    from core.risk_engine.engine import _max_candle_age_seconds

    chegara = _max_candle_age_seconds(config)
    qaror = engine.evaluate(nomzod(), sog_kontekst(price_age_seconds=chegara + 1))
    assert BlockReason.STALE_MARKET_DATA in qaror.reasons

    yangi_qaror = engine.evaluate(nomzod(), sog_kontekst(price_age_seconds=chegara - 1))
    assert BlockReason.STALE_MARKET_DATA not in yangi_qaror.reasons


def test_sham_yoshi_chegarasi_timeframega_bogliq(config) -> None:  # noqa: ANN001
    """1 soatlik sham tabiatan 1 soatgacha "eski" bo'ladi.

    Unga 90 soniyalik tik chegarasini qo'llash — har doim "eskirgan"
    degani, ya'ni birorta signal chiqmasligi.
    """
    import dataclasses

    from core.risk_engine.engine import _max_candle_age_seconds
    from core.utils.time_utils import timeframe_minutes

    for tf in ("15m", "1h", "4h"):
        yangi = dataclasses.replace(
            config, analysis=dataclasses.replace(config.analysis, entry_timeframe=tf)
        )
        chegara = _max_candle_age_seconds(yangi)
        assert chegara > timeframe_minutes(tf) * 60, (
            f"{tf} shamiga chegara sham uzunligidan katta bo'lishi kerak"
        )


@pytest.mark.parametrize(
    "yoq",
    ["btc_change_24h_pct", "adx", "atr_pct", "price_age_seconds"],
)
def test_malumot_yetishmasa_signal_berilmaydi(engine: RiskEngine, yoq: str) -> None:
    """0.3-band: noaniqlik — signal bermaslik uchun sabab."""
    qaror = engine.evaluate(nomzod(), sog_kontekst(**{yoq: None}))
    assert not qaror.allowed, f"{yoq} yo'q bo'lsa ham signal o'tib ketdi"


# --------------------------------------------------------------------------- #
#  3.3 — Universal risk qoidalari
# --------------------------------------------------------------------------- #


def test_stop_juda_uzoq_bolsa_rad_etiladi(engine: RiskEngine, config) -> None:  # noqa: ANN001
    """Shiftdan uzoq Stop — pozitsiya ma'nosiz kichrayadi.

    Chegara KONFIGURATSIYADAN olinadi: u ATR ko'paytmasiga bog'liq
    ravishda o'zgaradi (5% -> 8%), testga raqam yozib qo'yilsa jimgina
    eskirardi.
    """
    shift = config.trade_rules.max_stop_distance_pct
    stop_pct = shift + 1.0
    qaror = engine.evaluate(
        nomzod(stop_pct=stop_pct, tp2_pct=stop_pct * 3.0), sog_kontekst()
    )

    assert BlockReason.RISK_RULES_VIOLATED in qaror.reasons
    assert any("juda uzoq" in izoh for izoh in qaror.details), qaror.details


def test_stop_juda_yaqin_bolsa_rad_etiladi(engine: RiskEngine) -> None:
    """1% dan yaqin Stop — bozor shovqini uni bekorga yeb qo'yadi."""
    qaror = engine.evaluate(nomzod(stop_pct=0.4), sog_kontekst())

    assert BlockReason.RISK_RULES_VIOLATED in qaror.reasons
    assert any("juda yaqin" in izoh for izoh in qaror.details), qaror.details


def test_stop_oraliq_ichida_bolsa_otadi(engine: RiskEngine) -> None:
    """3.3-band tuzatilgan: Stop 1%..5% oralig'ida ERKIN joylashadi.

    Avval qat'iy 1% chegara bor edi — aynan 1% masofada mos S/R zonasi
    kam uchraydi, shu sababli signal deyarli chiqmasdi.
    """
    for stop_pct in (1.0, 2.0, 3.5, 5.0):
        qaror = engine.evaluate(
            nomzod(stop_pct=stop_pct, tp2_pct=stop_pct * 3.2), sog_kontekst()
        )
        assert qaror.allowed, f"Stop {stop_pct}%: {qaror.details}"


def test_nisbat_asosiy_shart(engine: RiskEngine, config) -> None:  # noqa: ANN001
    """Stop masofasidan QAT'I NAZAR, nisbat chegaradan past bo'lsa signal yo'q.

    Bu — chegara masofa emas, NISBAT ekanining sinovi.

    Kutilgan qiymat KONFIGURATSIYADAN olinadi: nisbat endi STRATEGIYA
    darajasida sozlanadi (mean reversion 1:1.5, skalping 1:1), shuning
    uchun testga raqam yozib qo'yish uni jimgina eskirtirardi.
    """
    kerak = config.strategies.classic_ta.min_risk_reward
    # Stop kattaroq olinadi, aks holda chegaradan past TP2 TP1 dan ham
    # past tushib, darajalar tartibi buzilardi (Stop < Entry < TP1 < TP2).
    stop_pct = 4.0
    past_tp2 = stop_pct * kerak * 0.7  # chegaradan aniq past

    qaror = engine.evaluate(nomzod(stop_pct=stop_pct, tp2_pct=past_tp2), sog_kontekst())

    assert BlockReason.RISK_RULES_VIOLATED in qaror.reasons
    assert any("Nisbat yetarli emas" in izoh for izoh in qaror.details), qaror.details


def test_nisbat_strategiya_darajasida(config) -> None:  # noqa: ANN001
    """Har bir strategiya o'z tabiiy nisbatiga ega bo'lishi kerak.

    Mean reversion diapazon o'rtasiga qaytganda yopiladi (1:1..1:1.5),
    trend/breakout esa uzoqroq yuradi. Global qat'iy 1:3 mean reversion
    uchun deyarli hech qachon bajarilmaydigan shart edi.
    """
    assert config.strategies.classic_ta.min_risk_reward < config.trade_rules.min_risk_reward, (
        "mean reversion global qiymatdan pastroq nisbatga ega bo'lishi kerak"
    )


def test_past_risk_reward_rad_etiladi(engine: RiskEngine, config) -> None:  # noqa: ANN001
    """TP2 strategiyaning eng kam nisbatini ta'minlashi kerak."""
    kerak = config.strategies.classic_ta.min_risk_reward
    entry = 100.0
    # Stop 1%, TP2 kerakli nisbatdan yuqori
    tp2 = entry * (1 + 1.0 * (kerak + 1.0) / 100)
    levels = SignalLevels(entry=entry, stop=99.0, tp1=103.0, tp2=max(tp2, 103.5))
    kandidat = SignalCandidate(
        symbol="ETH",
        levels=levels,
        source=SignalSource.CLASSIC_TA,
        breakdown=ScoreBreakdown("ETH", []),
        halal_verdict=HalalVerdict("ETH", HalalStatus.HALAL, "halol"),
    )
    assert engine.evaluate(kandidat, sog_kontekst()).allowed

    # Nisbat chegaradan past: Stop keng, TP2 esa yaqin.
    tor_stop_pct = 4.0
    tor = SignalLevels(
        entry=entry, stop=entry * (1 - tor_stop_pct / 100), tp1=103.0, tp2=103.5
    )
    assert tor.risk_reward_tp2 < kerak, "test sozlamasi noto'g'ri"
    kandidat_tor = SignalCandidate(
        symbol="ETH",
        levels=tor,
        source=SignalSource.CLASSIC_TA,
        breakdown=ScoreBreakdown("ETH", []),
        halal_verdict=HalalVerdict("ETH", HalalStatus.HALAL, "halol"),
    )
    assert BlockReason.RISK_RULES_VIOLATED in engine.evaluate(kandidat_tor, sog_kontekst()).reasons


# --------------------------------------------------------------------------- #
#  3.4 — Halollik oxirgi himoya chizig'i
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("status", [HalalStatus.HARAM, HalalStatus.MASHBOOH])
def test_halol_bolmagan_coin_oxirgi_qatlamda_ham_toxtatiladi(
    engine: RiskEngine, status: HalalStatus
) -> None:
    kandidat = SignalCandidate(
        symbol="XXX",
        levels=SignalLevels(100, 99.2, 103, 104),
        source=SignalSource.CLASSIC_TA,
        breakdown=ScoreBreakdown("XXX", []),
        halal_verdict=HalalVerdict("XXX", status, "ro'yxatda"),
    )
    qaror = engine.evaluate(kandidat, sog_kontekst())
    assert BlockReason.NOT_HALAL in qaror.reasons


# --------------------------------------------------------------------------- #
#  Umumiy xatti-harakat
# --------------------------------------------------------------------------- #


def test_barcha_sabablar_yigiladi(engine: RiskEngine) -> None:
    """Admin "nega berilmadi?" savoliga TO'LIQ javob ko'rishi kerak."""
    kontekst = sog_kontekst(
        now=TOSHKENT_JUMA_NAMOZ,
        market_health=salomatlik(20),
        btc_change_24h_pct=-9.0,
    )
    qaror = engine.evaluate(nomzod(), kontekst)
    assert not qaror.allowed
    assert {
        BlockReason.FRIDAY_PRAYER,
        BlockReason.MARKET_HEALTH_LOW,
        BlockReason.BTC_MARKET_FILTER,
    } <= set(qaror.reasons)


def test_qoida_xato_bersa_tizim_toxtamaydi_lekin_signal_berilmaydi(config: AppConfig) -> None:
    """0.3-band: bitta modulning nosozligi butun tizimni to'xtatmasligi kerak."""

    class BuzuqQoida:
        name = "buzuq"

        def check(self, candidate, context):  # noqa: ANN001, ARG002
            raise RuntimeError("sinov uchun ataylab buzilgan")

    engine = RiskEngine(config, rules=[BuzuqQoida()])
    qaror = engine.evaluate(nomzod(), sog_kontekst())

    assert not qaror.allowed
    assert BlockReason.INTERNAL_ERROR in qaror.reasons


# --------------------------------------------------------------------------- #
#  Sinov davri: BIZNING holatimizga qarab to'xtatuvchi qoidalar ushlab turmaydi
# --------------------------------------------------------------------------- #

SINOV_VAQTI = datetime(2026, 9, 16, 10, 0, tzinfo=UTC)  # chorshanba, sinov ichida


def test_sinov_davrida_kunlik_zarar_signalni_toxtatmaydi(
    engine: RiskEngine, config: AppConfig
) -> None:
    """100 kunlik kuzatuvning butun maqsadi — strategiyani TO'LIQ ko'rish.

    Kunlik zarar chegarasi ishlaganda yomon ertalakdan keyin tizim
    o'zini o'chiradi va kunning qolgan qismini umuman ko'rmaymiz —
    namuna qiyshayadi.
    """
    limit = config.risk_engine.daily_loss_limit_pct
    qaror = engine.evaluate(
        nomzod(), sog_kontekst(now=SINOV_VAQTI, daily_loss_pct=limit * 2)
    )
    assert BlockReason.DAILY_LOSS_LIMIT not in qaror.reasons
    assert qaror.allowed


def test_sinov_davrida_ochiq_signallar_chegarasi_ushlab_turmaydi(
    engine: RiskEngine, config: AppConfig
) -> None:
    ochiq = [
        Signal(
            symbol=f"C{i}",
            levels=SignalLevels(100, 99, 103, 105),
            source=SignalSource.CLASSIC_TA,
            status=SignalStatus.ACTIVE,
        )
        for i in range(config.risk_engine.max_open_signals_by_health.high + 3)
    ]
    qaror = engine.evaluate(nomzod(), sog_kontekst(now=SINOV_VAQTI, open_signals=ochiq))
    assert BlockReason.MAX_OPEN_SIGNALS not in qaror.reasons


def test_sinov_davrida_ketma_ket_stop_ham_ushlab_turmaydi(
    engine: RiskEngine, config: AppConfig
) -> None:
    chegara = config.risk_engine.consecutive_loss.max_consecutive_stops
    qaror = engine.evaluate(
        nomzod(), sog_kontekst(now=SINOV_VAQTI, consecutive_stops=chegara + 2)
    )
    assert BlockReason.CONSECUTIVE_LOSSES not in qaror.reasons


def test_sinov_davrida_BOZOR_qoidalari_ishlayveradi(engine: RiskEngine) -> None:
    """Eng muhim chegara: sinov "hamma narsani o'chirish" EMAS.

    Bozor yomon bo'lsa signal baribir berilmaydi — aks holda biz
    strategiyani emas, tasodifni o'lchagan bo'lardik.
    """
    past = engine.evaluate(
        nomzod(), sog_kontekst(now=SINOV_VAQTI, market_health=salomatlik(20))
    )
    assert BlockReason.MARKET_HEALTH_LOW in past.reasons

    btc = engine.evaluate(
        nomzod(), sog_kontekst(now=SINOV_VAQTI, btc_change_24h_pct=-9.0)
    )
    assert not btc.allowed

    past_volatillik = engine.evaluate(
        nomzod(), sog_kontekst(now=SINOV_VAQTI, atr_pct=0.05)
    )
    assert BlockReason.LOW_VOLATILITY in past_volatillik.reasons

    eskirgan = engine.evaluate(
        nomzod(), sog_kontekst(now=SINOV_VAQTI, price_age_seconds=999_999.0)
    )
    assert not eskirgan.allowed


def test_sinov_davrida_HALOL_va_favqulodda_toxtash_ishlaydi(
    engine: RiskEngine, config: AppConfig
) -> None:
    """Diniy qoida va favqulodda tugma hech qachon to'xtatilmaydi."""
    harom = nomzod()
    harom = SignalCandidate(
        symbol=harom.symbol,
        levels=harom.levels,
        source=harom.source,
        breakdown=harom.breakdown,
        halal_verdict=HalalVerdict(harom.symbol, HalalStatus.HARAM, "harom"),
    )
    assert not engine.evaluate(harom, sog_kontekst(now=SINOV_VAQTI)).allowed

    kill = engine.evaluate(
        nomzod(), sog_kontekst(now=SINOV_VAQTI, kill_switch_active=True)
    )
    assert BlockReason.KILL_SWITCH in kill.reasons


def test_sinov_tugagach_tormozlar_ozi_qaytadi(
    engine: RiskEngine, config: AppConfig
) -> None:
    keyin = datetime(2027, 3, 3, 10, 0, tzinfo=UTC)
    limit = config.risk_engine.daily_loss_limit_pct
    qaror = engine.evaluate(nomzod(), sog_kontekst(now=keyin, daily_loss_pct=limit))
    assert BlockReason.DAILY_LOSS_LIMIT in qaror.reasons


def test_toxtatilgan_qoidalar_royxati_ochiq(engine: RiskEngine) -> None:
    """Admin nima o'chirilganini ko'ra olishi kerak — yashirin rejim yo'q."""
    assert engine.suspended_rules(SINOV_VAQTI) == {
        "daily_loss_limit",
        "max_open_signals",
        "correlation",
        "consecutive_loss",
    }
    assert engine.suspended_rules(ODDIY_VAQT) == set()


def test_sinov_davrida_korrelyatsiya_ham_ushlab_turmaydi(engine: RiskEngine) -> None:
    """BTC ochiq bo'lsa ham ETH signali yozib boriladi — sinovda biz
    strategiyaning HAMMA nomzodini ko'rishimiz kerak."""
    ochiq = Signal(
        symbol="BTC",
        levels=SignalLevels(100, 99, 103, 105),
        source=SignalSource.CLASSIC_TA,
        status=SignalStatus.ACTIVE,
    )
    qaror = engine.evaluate(
        nomzod("ETH"), sog_kontekst(now=SINOV_VAQTI, open_signals=[ochiq])
    )
    assert BlockReason.CORRELATION not in qaror.reasons
