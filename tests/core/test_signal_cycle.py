"""15-bosqich: avtomatik signal sikli.

Sikl barcha modullarni bog'laydi, shuning uchun testlar aynan BOG'LANISHNI
tekshiradi: chegara qo'llanadimi, Risk Engine chetlab o'tilmaydimi, bir
siklda korrelyatsiya qoidasi buzilmaydimi.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.analysis.strategies import Strategy, StrategyInput
from core.config import load_config
from core.domain.enums import HalalStatus, SignalSource, SignalStatus
from core.domain.models import (
    HalalVerdict,
    MarketHealth,
    ScoreBreakdown,
    ScoreComponent,
    Signal,
    SignalCandidate,
    SignalLevels,
    signal_levels,
)
from core.pipeline import CycleInput, SignalCycle, SymbolData

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)  # chorshanba, Juma emas


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


def salomatlik(qiymat: float) -> MarketHealth:
    """Aniq indeks qiymati bilan holat quradi.

    Sikl faqat QIYMATGA qaraydi (chegara va limitlar shundan kelib chiqadi),
    shuning uchun omillarni qayta hisoblashning hojati yo'q. Omillar
    mantig'i `test_market_health.py` da alohida sinaladi.
    """
    return MarketHealth(value=qiymat, factors=[], computed_at=HOZIR)


def darajalar(entry: float = 100.0) -> SignalLevels:
    # Stop 1.5% (1..5% oralig'ida), TP1 3.5% (1:2.3), TP2 5% (1:3.3)
    return signal_levels(entry=entry, stop=entry * 0.985, tp1=entry * 1.035, tp2=entry * 1.05)


class SoxtaStrategiya(Strategy):
    """Oldindan belgilangan nomzodlarni qaytaradigan strategiya."""

    name = "soxta"

    def __init__(self, scores: dict[str, float], fail_on: set[str] | None = None) -> None:
        self._scores = scores
        self._fail_on = fail_on or set()
        self.last_rejection = None

    @property
    def enabled(self) -> bool:
        return True

    def required_timeframes(self) -> list[str]:
        return ["15m"]

    def analyze(self, data: StrategyInput) -> SignalCandidate | None:
        if data.symbol in self._fail_on:
            raise RuntimeError("sinov uchun ataylab buzilgan")

        ball = self._scores.get(data.symbol)
        if ball is None:
            from core.analysis.strategies.classic_ta import RejectionReason

            self.last_rejection = RejectionReason("no_setup", "Shart bajarilmadi")
            return None

        return SignalCandidate(
            symbol=data.symbol,
            levels=darajalar(),
            source=SignalSource.CLASSIC_TA,
            breakdown=ScoreBreakdown(
                data.symbol, [ScoreComponent("jami", ball, 100, "sinov")]
            ),
            halal_verdict=data.halal_verdict,
        )


def kirish(config, scores: dict[str, float], **kwargs) -> CycleInput:  # noqa: ANN001
    """Barcha filtrlardan o'tadigan sog'lom kontekst."""
    coinlar = [
        SymbolData(
            symbol=symbol,
            halal_verdict=HalalVerdict(symbol, HalalStatus.HALAL, "halol"),
            candles={"15m": []},
        )
        for symbol in scores
    ]
    asosiy = {
        "now": HOZIR,
        "symbols": coinlar,
        "market_health": salomatlik(90.0),
        "btc_change_24h_pct": 1.5,
        "price_ages": dict.fromkeys(scores, 5.0),
        "adx_values": dict.fromkeys(scores, 30.0),
        "atr_values": dict.fromkeys(scores, 1.8),
    }
    return CycleInput(**{**asosiy, **kwargs})


# --------------------------------------------------------------------------- #
#  Asosiy zanjir
# --------------------------------------------------------------------------- #


def test_yuqori_ballli_nomzod_chiqadi(config) -> None:  # noqa: ANN001
    ballar = {"BTC": 85.0}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    natija = sikl.run(kirish(config, ballar))

    assert natija.emitted_count == 1
    assert natija.emitted[0].symbol == "BTC"
    assert natija.threshold is not None


def test_past_ballli_nomzod_chegaradan_otmaydi(config) -> None:  # noqa: ANN001
    # Ball ikkala chegaradan ham pastroq qilib QURILADI — aniq raqam
    # yozib qo'yilsa, chegara o'zgargach test jimgina ma'nosini
    # yo'qotardi (aynan shu 70/80 bilan sodir bo'lgan edi).
    chegaralar = config.scoring.thresholds
    eng_past = min(chegaralar.threshold_high_health, chegaralar.threshold_mid_health)
    ballar = {"BTC": eng_past - 5}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    natija = sikl.run(kirish(config, ballar))

    assert natija.emitted_count == 0
    assert any(r.stage == "threshold" for r in natija.rejected)


def test_nomzodlar_ballga_qarab_tartiblanadi(config) -> None:  # noqa: ANN001
    ballar = {"SOL": 82.0, "BTC": 95.0, "AVAX": 88.0}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    natija = sikl.run(kirish(config, ballar))

    chiqqanlar = [n.symbol for n in natija.emitted]
    assert chiqqanlar[0] == "BTC", "eng yuqori ball birinchi bo'lishi kerak"


def test_bosh_natija_xato_emas(config) -> None:  # noqa: ANN001
    """0.2-band: "signal bermaslik normal holat"."""
    sikl = SignalCycle(config, [SoxtaStrategiya({})])
    natija = sikl.run(kirish(config, {"BTC": 0.0}))

    assert natija.emitted_count == 0
    assert natija.rejected, "sabab ko'rsatilishi kerak"


# --------------------------------------------------------------------------- #
#  Bozor Salomatligi siklni boshqaradi (3.7 / 4.9-band)
# --------------------------------------------------------------------------- #


def test_past_salomatlikda_faqat_korreksiya_strategiyasi_ishlaydi(config) -> None:  # noqa: ANN001
    """Past indeks endi siklni TO'XTATMAYDI — rejimni almashtiradi.

    Ilgari bu yerda "coinlar umuman tahlil qilinmaydi" kutilardi. Bu
    strategiyaning o'z falsafasiga zid edi: past indeks aynan narxlar
    ARZONLASHGAN payt. Tizim shunda ko'zini yumib, indeks qayta
    ko'tarilgach signal berardi — ya'ni doim KECH kirardi.

    Endi past bandda faqat `correction_entry` ishlaydi: u tushayotgan
    bozorga emas, ko'tarilishdagi KORREKSIYAGA mo'ljallangan.
    """
    ballar = {"BTC": 99.0}
    oddiy = SoxtaStrategiya(ballar)
    sikl = SignalCycle(config, [oddiy])

    natija = sikl.run(kirish(config, ballar, market_health=salomatlik(25.0)))

    # Oddiy strategiya past bandda ishlamaydi
    assert natija.emitted_count == 0
    assert natija.analyzed_count == 0
    assert natija.rejected[0].stage == "market_health"
    # Lekin chegara endi BOR — sikl "yopiq" emas, rejimda
    assert natija.threshold == config.scoring.thresholds.threshold_low_health


def test_past_salomatlikda_korreksiya_strategiyasi_tahlil_qilinadi(config) -> None:  # noqa: ANN001
    """Korreksiya strategiyasi past bandda COINLARNI KO'RADI."""
    from core.domain.enums import SignalSource

    ballar = {"BTC": 99.0}
    korreksiya = SoxtaStrategiya(ballar)
    korreksiya.name = SignalSource.CORRECTION_ENTRY.value
    sikl = SignalCycle(config, [korreksiya])

    natija = sikl.run(kirish(config, ballar, market_health=salomatlik(25.0)))

    assert natija.analyzed_count > 0, "korreksiya rejimida tahlil bo'lishi kerak"


def test_salomatlik_hisoblanmagan_bolsa_signal_yoq(config) -> None:  # noqa: ANN001
    ballar = {"BTC": 99.0}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    natija = sikl.run(kirish(config, ballar, market_health=None))

    assert natija.emitted_count == 0
    assert natija.threshold is None


def test_chegara_salomatlikka_qarab_ozgaradi(config) -> None:  # noqa: ANN001
    """Ikki chegara ORASIDAGI ball: yuqori salomatlikda o'tadi, o'rtada yo'q."""
    chegaralar = config.scoring.thresholds
    orasida = (chegaralar.threshold_high_health + chegaralar.threshold_mid_health) / 2
    ballar = {"BTC": orasida}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    yuqori = sikl.run(kirish(config, ballar, market_health=salomatlik(90.0)))
    ortacha = sikl.run(kirish(config, ballar, market_health=salomatlik(55.0)))

    assert yuqori.threshold < ortacha.threshold
    assert yuqori.emitted_count == 1, "yuqori salomatlikda bu ball yetarli"
    assert ortacha.emitted_count == 0, "o'rtacha salomatlikda chegara balandroq"


# --------------------------------------------------------------------------- #
#  Risk Engine chetlab o'tilmaydi (4-bo'lim)
# --------------------------------------------------------------------------- #


def test_risk_engine_signalni_toxtata_oladi(config) -> None:  # noqa: ANN001
    """Ball yuqori bo'lsa ham Risk Engine oxirgi so'zni aytadi."""
    ballar = {"BTC": 95.0}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    natija = sikl.run(
        kirish(config, ballar, kill_switch_active=True, kill_switch_reason="sinov")
    )

    assert natija.emitted_count == 0
    assert any(r.stage.startswith("risk_engine") for r in natija.rejected)


def test_juma_namozi_vaqtida_signal_yoq(config) -> None:  # noqa: ANN001
    juma = datetime(2026, 8, 21, 7, 30, tzinfo=UTC)  # Toshkentda 12:30
    ballar = {"BTC": 95.0}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    natija = sikl.run(kirish(config, ballar, now=juma))

    assert natija.emitted_count == 0
    assert any("Juma" in r.detail for r in natija.rejected)


def test_bir_siklda_korrelyatsiya_qoidasi_buzilmaydi(config) -> None:  # noqa: ANN001
    """Bir siklda ikkita bog'liq coin chiqib ketmasligi kerak.

    Yangi chiqarilgan signal keyingi nomzodlar uchun "ochiq" hisoblanadi —
    ansiz BTC va ETH bir vaqtda chiqib ketardi.
    """
    ballar = {"BTC": 95.0, "ETH": 90.0}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    natija = sikl.run(kirish(config, ballar))

    chiqqanlar = {n.symbol for n in natija.emitted}
    assert len(chiqqanlar) == 1, f"faqat bittasi chiqishi kerak: {chiqqanlar}"
    assert any(r.stage.startswith("risk_engine") for r in natija.rejected)


def test_ochiq_signallar_limiti_hurmat_qilinadi(config) -> None:  # noqa: ANN001
    limit = config.risk_engine.max_open_signals_by_health.high
    ochiqlar = [
        Signal(
            symbol=f"OLD{i}",
            levels=darajalar(),
            source=SignalSource.CLASSIC_TA,
            status=SignalStatus.ACTIVE,
        )
        for i in range(limit)
    ]
    ballar = {"ARB": 95.0}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    natija = sikl.run(kirish(config, ballar, open_signals=ochiqlar))

    assert natija.emitted_count == 0


# --------------------------------------------------------------------------- #
#  Chidamlilik (0.3-band)
# --------------------------------------------------------------------------- #


def test_strategiya_xatosi_siklni_toxtatmaydi(config) -> None:  # noqa: ANN001
    ballar = {"BTC": 95.0, "SOL": 90.0}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar, fail_on={"BTC"})])

    natija = sikl.run(kirish(config, ballar))

    assert natija.emitted_count == 1, "boshqa coinlar tahlil qilinishi kerak"
    assert natija.emitted[0].symbol == "SOL"
    assert any("error" in r.stage for r in natija.rejected)


def test_bir_nechta_strategiya_birga_ishlaydi(config) -> None:  # noqa: ANN001
    """6.1-band: Risk Engine strategiya turini bilmaydi."""
    birinchi = SoxtaStrategiya({"BTC": 95.0})
    ikkinchi = SoxtaStrategiya({"SOL": 92.0})
    sikl = SignalCycle(config, [birinchi, ikkinchi])

    natija = sikl.run(kirish(config, {"BTC": 0.0, "SOL": 0.0}))

    assert {n.symbol for n in natija.emitted} == {"BTC", "SOL"}


# --------------------------------------------------------------------------- #
#  Shaffoflik (3.7-band)
# --------------------------------------------------------------------------- #


def test_har_bir_rad_etish_sababi_qayd_etiladi(config) -> None:  # noqa: ANN001
    """"Tizim nega sokin?" savoliga to'liq javob."""
    ballar = {"BTC": 95.0, "ETH": 90.0, "SOL": 45.0}
    sikl = SignalCycle(config, [SoxtaStrategiya(ballar)])

    natija = sikl.run(kirish(config, ballar))

    bosqichlar = {r.stage for r in natija.rejected}
    assert "threshold" in bosqichlar
    assert all(r.detail for r in natija.rejected), "har bir sabab tushuntirilishi kerak"


def test_xulosa_matni_asosiy_raqamlarni_beradi(config) -> None:  # noqa: ANN001
    ballar = {"BTC": 95.0}
    natija = SignalCycle(config, [SoxtaStrategiya(ballar)]).run(kirish(config, ballar))

    xulosa = natija.summary()
    assert "coin tahlil qilindi" in xulosa
    assert "signal chiqdi" in xulosa
