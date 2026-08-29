"""3.5-band: ball hisoblash, darajali baholash va reytinglash."""

from __future__ import annotations

import json

import pytest

from core.analysis.indicators import Confirmation, ConfirmationFactor, build_snapshot
from core.analysis.scoring import Scorer, breakdown_to_json, breakdown_to_text
from core.analysis.scoring.factors import (
    score_risk_reward,
    score_support_resistance,
)
from core.analysis.support_resistance import ZoneMap, compute_range_position
from core.config import load_config
from core.config.schema import TradeRulesConfig
from core.domain.enums import HalalStatus, SignalSource, ZoneKind
from core.domain.models import (
    HalalVerdict,
    ScoreBreakdown,
    ScoreComponent,
    SignalCandidate,
    SignalLevels,
    SRZone,
)
from tests.core.test_indicators import sham

SUPPORT = SRZone(ZoneKind.SUPPORT, 99.4, 99.8, touches=4)
RESISTANCE = SRZone(ZoneKind.RESISTANCE, 103.5, 104.0, touches=3)


def xarita(price: float = 100.0, atr: float = 0.5) -> ZoneMap:
    return ZoneMap(zones=[SUPPORT, RESISTANCE], price=price, atr=atr)


def darajalar(rr: float = 4.0) -> SignalLevels:
    """TP2 nisbati `rr` bo'lgan darajalar. TP1 doim TP2 dan past qoladi."""
    entry, stop = 100.0, 99.2
    masofa = entry - stop
    return SignalLevels(
        entry=entry,
        stop=stop,
        tp1=entry + masofa * rr * 0.6,
        tp2=entry + masofa * rr,
    )


# --------------------------------------------------------------------------- #
#  S/R omili — eng og'ir (25 ball)
# --------------------------------------------------------------------------- #


def test_yaqin_zona_uzoqdan_yuqori_ball_oladi() -> None:
    yaqin = score_support_resistance(xarita(price=99.6), SUPPORT, None, weight=25)
    uzoq = score_support_resistance(xarita(price=102.0), SUPPORT, None, weight=25)
    assert yaqin.earned > uzoq.earned


def test_kop_sinalgan_zona_yuqori_ball_oladi() -> None:
    kop = SRZone(ZoneKind.SUPPORT, 99.4, 99.8, touches=8)
    kam = SRZone(ZoneKind.SUPPORT, 99.4, 99.8, touches=1)

    assert (
        score_support_resistance(xarita(), kop, None, 25).earned
        > score_support_resistance(xarita(), kam, None, 25).earned
    )


def test_chuqurroq_discount_yuqori_ball_beradi() -> None:
    """3.1-band davomi: chuqurroq Discount — yuqoriroq ball."""
    chuqur = compute_range_position(99.6, SUPPORT, RESISTANCE)
    sayoz = compute_range_position(101.3, SUPPORT, RESISTANCE)

    assert chuqur.is_discount and sayoz.is_discount
    assert (
        score_support_resistance(xarita(), SUPPORT, chuqur, 25).earned
        > score_support_resistance(xarita(), SUPPORT, sayoz, 25).earned
    )


def test_faqat_fibonacci_zonasi_pastroq_baholanadi() -> None:
    """Pivot tasdiqlamagan daraja — zaif dalil."""
    pivot = SRZone(ZoneKind.SUPPORT, 99.4, 99.8, touches=4)
    fib = SRZone(ZoneKind.SUPPORT, 99.4, 99.8, touches=4, from_fibonacci=True)

    assert (
        score_support_resistance(xarita(), fib, None, 25).earned
        < score_support_resistance(xarita(), pivot, None, 25).earned
    )


def test_ball_vazndan_oshmaydi() -> None:
    eng_yaxshi = SRZone(ZoneKind.SUPPORT, 99.9, 100.1, touches=20)
    joy = compute_range_position(99.95, SUPPORT, RESISTANCE)
    komponent = score_support_resistance(xarita(price=100.0), eng_yaxshi, joy, weight=25)

    assert 0 <= komponent.earned <= 25


# --------------------------------------------------------------------------- #
#  R/R omili
# --------------------------------------------------------------------------- #


def test_minimal_rr_yarim_ball_beradi() -> None:
    qoidalar = TradeRulesConfig(min_risk_reward=3.0)
    komponent = score_risk_reward(darajalar(rr=3.0), qoidalar, weight=15)
    assert komponent.earned == pytest.approx(7.5)


def test_yuqori_rr_kop_ball_beradi() -> None:
    qoidalar = TradeRulesConfig(min_risk_reward=3.0)
    past = score_risk_reward(darajalar(rr=3.5), qoidalar, 15)
    baland = score_risk_reward(darajalar(rr=6.0), qoidalar, 15)
    assert baland.earned > past.earned


def test_minimal_rr_dan_past_nol_ball() -> None:
    qoidalar = TradeRulesConfig(min_risk_reward=3.0)
    assert score_risk_reward(darajalar(rr=2.0), qoidalar, 15).earned == 0.0


# --------------------------------------------------------------------------- #
#  Umumiy ball
# --------------------------------------------------------------------------- #


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


def _hukm(hammasi_tasdiq: bool = True) -> Confirmation:
    return Confirmation(
        zone_ready=True,
        factors=[
            ConfirmationFactor("trend", hammasi_tasdiq, 1.0 if hammasi_tasdiq else 0.0, "trend"),
            ConfirmationFactor("rsi", hammasi_tasdiq, 1.0 if hammasi_tasdiq else 0.0, "rsi"),
            ConfirmationFactor("macd", hammasi_tasdiq, 1.0 if hammasi_tasdiq else 0.0, "macd"),
            ConfirmationFactor("volume", hammasi_tasdiq, 1.0 if hammasi_tasdiq else 0.0, "hajm"),
        ],
    )


def test_bazaviy_ball_yuzdan_oshmaydi(config) -> None:  # noqa: ANN001
    """Bazaviy shkala 100 da qoladi — chegara aynan shunda o'lchangan.

    CryptoSpot3% bonuslari shkalani 125 ga kengaytirdi, lekin BAZAVIY
    qism o'zgarmasligi shart: chegaralar (50/55) `scripts.kalibrlash`
    bilan shu shkalada o'lchangan.
    """
    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    holat = build_snapshot(shamlar, config.analysis.indicators)

    tafsilot = Scorer(config).score(
        "BTC", xarita(), SUPPORT, holat, _hukm(True), darajalar(rr=6.0)
    )
    bazaviy_shift = sum(k.maximum for k in tafsilot.components if not k.bonus)
    assert 0 <= tafsilot.base_total <= 100
    assert bazaviy_shift == pytest.approx(100)
    assert tafsilot.maximum == pytest.approx(100 + config.scoring.bonuses.total())


def test_barcha_omillar_hisobga_olinadi(config) -> None:  # noqa: ANN001
    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    holat = build_snapshot(shamlar, config.analysis.indicators)
    tafsilot = Scorer(config).score("BTC", xarita(), SUPPORT, holat, _hukm(), darajalar())

    bazaviy = {k.name for k in tafsilot.components if not k.bonus}
    bonuslar = {k.name for k in tafsilot.components if k.bonus}
    assert bazaviy == {"support_resistance", "trend", "rsi", "volume", "macd", "risk_reward"}
    assert bonuslar == {"structure", "liquidity_sweep", "session_overlap"}


def test_sr_eng_katta_vaznga_ega(config) -> None:  # noqa: ANN001
    """3.1/3.5-band: S/R birlamchi omil."""
    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    holat = build_snapshot(shamlar, config.analysis.indicators)
    tafsilot = Scorer(config).score("BTC", xarita(), SUPPORT, holat, _hukm(), darajalar())

    sr = tafsilot.component("support_resistance")
    assert sr.maximum == max(k.maximum for k in tafsilot.components if not k.bonus)


def test_tasdiqlanmagan_omillar_ball_bermaydi(config) -> None:  # noqa: ANN001
    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    holat = build_snapshot(shamlar, config.analysis.indicators)

    yaxshi = Scorer(config).score("BTC", xarita(), SUPPORT, holat, _hukm(True), darajalar())
    yomon = Scorer(config).score("BTC", xarita(), SUPPORT, holat, _hukm(False), darajalar())
    assert yaxshi.total > yomon.total


# --------------------------------------------------------------------------- #
#  Reytinglash va chegara
# --------------------------------------------------------------------------- #


def nomzod(symbol: str, ball: float) -> SignalCandidate:
    return SignalCandidate(
        symbol=symbol,
        levels=darajalar(),
        source=SignalSource.CLASSIC_TA,
        breakdown=ScoreBreakdown(symbol, [ScoreComponent("jami", ball, 100, "sinov")]),
        halal_verdict=HalalVerdict(symbol, HalalStatus.HALAL, "halol"),
    )


def test_nomzodlar_ballga_qarab_saralanadi(config) -> None:  # noqa: ANN001
    reyting = Scorer(config).rank(
        [nomzod("BTC", 72), nomzod("ETH", 88), nomzod("SOL", 65)], threshold=70
    )

    assert [r.candidate.symbol for r in reyting] == ["ETH", "BTC", "SOL"]
    assert [r.rank for r in reyting] == [1, 2, 3]


def test_chegaradan_otganlar_ajratiladi(config) -> None:  # noqa: ANN001
    scorer = Scorer(config)
    reyting = scorer.rank([nomzod("BTC", 72), nomzod("ETH", 88), nomzod("SOL", 65)], threshold=70)

    assert [c.symbol for c in scorer.passed(reyting)] == ["ETH", "BTC"]


def test_chegara_yopiq_bolsa_hech_kim_otmaydi(config) -> None:  # noqa: ANN001
    """3.5-band: Bozor Salomatligi past -> yangi signal umuman berilmaydi."""
    scorer = Scorer(config)
    reyting = scorer.rank([nomzod("BTC", 99)], threshold=None)

    assert not reyting[0].passed_threshold
    assert scorer.passed(reyting) == []


def test_hech_kim_otmasa_bosh_royxat(config) -> None:  # noqa: ANN001
    """Bu XATO EMAS — 0.2-band bo'yicha normal holat."""
    scorer = Scorer(config)
    assert scorer.passed(scorer.rank([nomzod("BTC", 50)], threshold=80)) == []


def test_bosh_royxat_xato_bermaydi(config) -> None:  # noqa: ANN001
    assert Scorer(config).rank([], threshold=70) == []


# --------------------------------------------------------------------------- #
#  3.6-band: shaffoflik
# --------------------------------------------------------------------------- #


def test_tafsilot_json_ga_aylanadi(config) -> None:  # noqa: ANN001
    """Ball signal bilan BIRGA saqlanishi kerak — keyin qayta hisoblab bo'lmaydi."""
    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    holat = build_snapshot(shamlar, config.analysis.indicators)
    tafsilot = Scorer(config).score("BTC", xarita(), SUPPORT, holat, _hukm(), darajalar())

    xom = json.loads(breakdown_to_json(tafsilot))
    assert xom["symbol"] == "BTC"
    assert len(xom["components"]) == 9  # 6 bazaviy + 3 bonus
    assert xom["maximum"] == 100 + config.scoring.bonuses.total()
    # Chegara bazaviy shkalada tekshiriladi — postmortem uchun ham kerak
    assert xom["base_total"] <= 100


def test_tafsilot_oqiladigan_matn_beradi(config) -> None:  # noqa: ANN001
    """3.6-band: "Nega bu signal?" tugmasi shu matndan to'ladi."""
    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    holat = build_snapshot(shamlar, config.analysis.indicators)
    tafsilot = Scorer(config).score("BTC", xarita(), SUPPORT, holat, _hukm(), darajalar())

    matn = breakdown_to_text(tafsilot)
    assert "BTC" in matn
    assert "ball" in matn
    assert "▰" in matn or "▱" in matn, "vizual ko'rsatkich bo'lishi kerak"


# --------------------------------------------------------------------------- #
#  Bazadan qaytib o'qish — "Nega bu signal?" ekrani shu yo'l bilan to'ladi
# --------------------------------------------------------------------------- #


def test_json_dan_qaytib_oqiladi(config) -> None:  # noqa: ANN001
    """Regressiya: `breakdown_to_text()` yozilgan, lekin ULANMAGAN edi.

    Bot "Nega bu signal?" tugmasida bazadagi XOM JSON ni ko'rsatardi —
    foydalanuvchi ekranida `{"symbol": "BTC", "components": [...]}`
    chiqardi. Bu loyihaning 2-naqshi: "e'lon qilingan, lekin ulanmagan".
    """
    from core.analysis.scoring import breakdown_from_json

    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    holat = build_snapshot(shamlar, config.analysis.indicators)
    asl = Scorer(config).score("BTC", xarita(), SUPPORT, holat, _hukm(), darajalar())

    tiklangan = breakdown_from_json(breakdown_to_json(asl))

    assert tiklangan is not None
    assert tiklangan.symbol == "BTC"
    assert tiklangan.total == pytest.approx(asl.total, abs=0.02)
    assert tiklangan.base_total == pytest.approx(asl.base_total, abs=0.02)
    # Bonus belgisi ham saqlanishi SHART: usiz chegara shkalasi buziladi
    assert {k.name for k in tiklangan.components if k.bonus} == {
        "structure", "liquidity_sweep", "session_overlap"
    }


def test_eski_yozuvda_bonus_kaliti_yoq_bolsa_ham_oqiladi() -> None:
    """Bu o'zgarishdan OLDIN yozilgan signallar ham ochilishi kerak."""
    from core.analysis.scoring import breakdown_from_json

    eski = json.dumps(
        {
            "symbol": "ETH",
            "total": 55.0,
            "maximum": 100.0,
            "components": [
                {"name": "trend", "earned": 20.0, "maximum": 20.0, "explanation": "Trend"}
            ],
        }
    )
    tiklangan = breakdown_from_json(eski)

    assert tiklangan is not None
    assert tiklangan.components[0].bonus is False


def test_buzuq_matn_xato_bermaydi() -> None:
    """Qo'lda kiritilgan signalda JSON emas, oddiy izoh turadi."""
    from core.analysis.scoring import breakdown_from_json

    assert breakdown_from_json("admin qo'lda kiritdi") is None
    assert breakdown_from_json("{}") is None


def test_matnda_topilmagan_bonus_korsatilmaydi(config) -> None:  # noqa: ANN001
    """Bo'sh "Sweep topilmadi" qatori foydalanuvchini chalkashtiradi."""
    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    holat = build_snapshot(shamlar, config.analysis.indicators)
    tafsilot = Scorer(config).score("BTC", xarita(), SUPPORT, holat, _hukm(), darajalar())

    matn = breakdown_to_text(tafsilot)

    assert "Liquidity Sweep topilmadi" not in matn
    # Bazaviy omillar esa DOIM ko'rinadi
    assert "S/R" in matn
