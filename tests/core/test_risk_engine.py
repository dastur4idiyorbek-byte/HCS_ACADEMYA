"""4-bo'lim: Risk Engine qoidalari.

Asosiy tamoyil sinovlari:
  - "VA" mantig'i: bitta qoida rad etsa, signal chiqmaydi
  - fail-safe: ma'lumot yetishmasa, signal BERILMAYDI (xato signal berilmaydi)
  - Juma filtri faqat YANGI signalga taalluqli
"""

from __future__ import annotations

import dataclasses
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
    signal_levels,
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
    levels = signal_levels(
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


def _bandli(config: AppConfig) -> AppConfig:
    """Foiz oraliqlari YOQILGAN nusxa.

    Standart holatda ular majburiy emas: bog'lovchi shart — nisbat
    (1:3). Oraliqlarni sinaydigan testlar ularni o'zi yoqadi.
    """
    return dataclasses.replace(
        config,
        trade_rules=dataclasses.replace(config.trade_rules, enforce_distance_bands=True),
    )


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
        levels=signal_levels(100, 99, 103, 105),
        source=SignalSource.CLASSIC_TA,
        status=SignalStatus.ACTIVE,
    )
    qaror = engine.evaluate(nomzod("ETH"), sog_kontekst(open_signals=[ochiq]))
    assert not qaror.allowed
    assert BlockReason.CORRELATION in qaror.reasons


def test_boshqa_guruhdagi_coin_otadi(engine: RiskEngine) -> None:
    ochiq = Signal(
        symbol="BTC",
        levels=signal_levels(100, 99, 103, 105),
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
            levels=signal_levels(100, 99, 103, 105),
            source=SignalSource.CLASSIC_TA,
            status=SignalStatus.ACTIVE,
        )
        for i in range(limit)
    ]
    qaror = engine.evaluate(nomzod("ARB"), sog_kontekst(open_signals=ochiq))
    assert not qaror.allowed
    assert BlockReason.MAX_OPEN_SIGNALS in qaror.reasons


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


def test_adx_yoq_bolsa_risk_engine_toxtatmaydi(engine: RiskEngine) -> None:
    """ADX ro'yxatdan CHIQARILDI — `MarketRegimeRule` olib tashlandi.

    Qoida faqat `adx is None` ni tekshirar, `adx_trend_threshold`
    bilan taqqoslash umuman yo'q edi — ya'ni docstring va kod
    boshqa-boshqa narsa aytardi. Sabab va o'lchov:
    `core/risk_engine/rules.py` boshidagi izoh.

    Fail-safe yo'qolmadi: nomzod bu yergacha yetib kelishi uchun
    `classic_ta` ning "indicators" bosqichidan o'tishi shart, u esa
    to'liq bo'lmagan indikatorlarni allaqachon rad etadi.
    """
    qaror = engine.evaluate(nomzod(), sog_kontekst(adx=None))
    assert qaror.allowed, qaror.details


# --------------------------------------------------------------------------- #
#  3.3 — Universal risk qoidalari
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("status", [HalalStatus.HARAM, HalalStatus.MASHBOOH])
def test_halol_bolmagan_coin_oxirgi_qatlamda_ham_toxtatiladi(
    engine: RiskEngine, status: HalalStatus
) -> None:
    kandidat = SignalCandidate(
        symbol="XXX",
        levels=signal_levels(100, 99.2, 103, 104),
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
    """Bitta sababda to'xtamaydi — admin TO'LIQ ro'yxatni ko'rishi kerak."""
    qaror = engine.evaluate(
        nomzod(),
        sog_kontekst(
            daily_loss_pct=99.0,
            consecutive_stops=99,
            price_age_seconds=999_999.0,
        ),
    )
    assert not qaror.allowed
    assert BlockReason.DAILY_LOSS_LIMIT in qaror.reasons
    assert BlockReason.CONSECUTIVE_LOSSES in qaror.reasons
    assert BlockReason.STALE_MARKET_DATA in qaror.reasons


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
            levels=signal_levels(100, 99, 103, 105),
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

    2026-09-03 — bozor holatiga qaraydigan qoidalar (salomatlik, BTC
    filtri, volatillik) eski tahlil moduli bilan birga ketdi. Bu yerda
    endi ma'lumot YANGILIGI tekshiriladi: sham eskirgan bo'lsa signal
    baribir berilmaydi, sinov davri bo'lsa ham.
    """
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
        levels=signal_levels(100, 99, 103, 105),
        source=SignalSource.CLASSIC_TA,
        status=SignalStatus.ACTIVE,
    )
    qaror = engine.evaluate(
        nomzod("ETH"), sog_kontekst(now=SINOV_VAQTI, open_signals=[ochiq])
    )
    assert BlockReason.CORRELATION not in qaror.reasons
