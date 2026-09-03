"""Mean reversion strategiyasini o'ziga xos qiymatlarga qaytarish (44-bo'lim).

Bir hafta jonli ishlagan bot 0 ta signal berdi. Sabab: `classic_ta` —
mean reversion strategiyasi, lekin unga qo'yilgan qoidalar
(1 soatlik timeframe, qat'iy % stop, majburiy 1:3 nisbat)
trend/breakout strategiyalariga xos edi.

Bu testlar uchta tuzatishning HAR BIRINI alohida qulflaydi.
"""

from __future__ import annotations

import pytest

from core.analysis.strategies.classic_ta import classic_ta_rules
from core.config import load_config
from core.config.schema import AppConfig
from core.domain.enums import SignalSource
from core.domain.models import signal_levels
from core.risk_engine import RiskEngine
from core.utils.time_utils import timeframe_minutes

# --------------------------------------------------------------------------- #
#  TUZATISH 1 — timeframe
# --------------------------------------------------------------------------- #


def test_kirish_timeframei_mean_reversion_uchun_yetarli_sekin(config: AppConfig) -> None:
    """1 soatlik grafik mean reversion uchun shovqinli.

    Kirish kamida 4 soatlik bo'lishi kerak; tasdiq undan yuqori.
    """
    kirish = timeframe_minutes(config.analysis.entry_timeframe)
    assert kirish >= timeframe_minutes("4h")

    for tf in config.analysis.htf_confirmation:
        assert timeframe_minutes(tf) > kirish, f"{tf} kirishdan yuqori bo'lishi kerak"


def test_salomatlik_timeframei_tasdiqdan_yuqori(config: AppConfig) -> None:
    """Bozor kengligi eng katta rasmda o'lchanadi."""
    eng_yuqori_tasdiq = max(timeframe_minutes(tf) for tf in config.analysis.htf_confirmation)
    assert timeframe_minutes(config.analysis.market_health_timeframe) > eng_yuqori_tasdiq


def test_skalping_timeframei_ozgarmagan(config: AppConfig) -> None:
    """`opening_range_scalp` alohida: kunlik ochilish mantig'i bilan ishlaydi."""
    assert config.strategies.opening_range_scalp.timeframe == "15m"


# --------------------------------------------------------------------------- #
#  TUZATISH 2 — ATR asosli Stop
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("atr_pct", [0.4, 1.0, 3.0])
def test_stop_atr_bilan_masshtablanadi(config: AppConfig, atr_pct: float) -> None:
    """Stop masofasi coin volatilligiga ergashishi kerak.

    Qat'iy foiz barcha coinlarga bir xil qo'llanardi: barqarorida
    keraksiz keng, volatilida juda tor bo'lib shovqin uni yeb qo'yardi.
    """
    from core.analysis.scoring.levels import _stop_narxi

    qoidalar = classic_ta_rules(config)
    entry = 100.0
    atr = entry * atr_pct / 100
    # Support juda yaqin — ya'ni tuzilma emas, ATR hal qiladi
    stop = _stop_narxi(entry, support_low=entry * 0.999, atr=atr, rules=qoidalar)

    masofa_pct = (entry - stop) / entry * 100
    kutilgan = atr_pct * qoidalar.stop_atr_mult
    assert masofa_pct == pytest.approx(kutilgan, rel=0.01)


def test_stop_support_zonasidan_past_qoladi(config: AppConfig) -> None:
    """ATR tor bo'lsa ham Stop zona ICHIDA qolmasligi kerak.

    Zona ichidagi Stop strategiyaning o'z asosini buzardi: narx
    support'ga tegib qaytganda ham Stop ishlardi.
    """
    from core.analysis.scoring.levels import _stop_narxi

    qoidalar = classic_ta_rules(config)
    entry = 100.0
    atr = 0.1  # juda tor ATR
    support_low = 97.0

    stop = _stop_narxi(entry, support_low=support_low, atr=atr, rules=qoidalar)
    assert stop < support_low, "Stop support zonasidan past bo'lishi shart"


def test_foiz_oraligi_ikkinchi_darajali_cheklov_sifatida_qoladi(
    config: AppConfig,
) -> None:
    """Oraliq YOQILGANDA ATR asosidagi Stop undan chiqsa rad etiladi.

    Standart holatda oraliq MAJBURIY EMAS (loyiha egasining qarori:
    "TP STOP FOIZLARI MAJBURIY EMAS — RISK 1/3"), shuning uchun test
    uni ataylab yoqadi. Ya'ni imkoniyat yo'qolmagani tekshiriladi,
    majburiyligi emas.
    """
    import dataclasses as _dc

    from core.analysis.scoring.levels import _build_stop

    qoidalar = _dc.replace(classic_ta_rules(config), enforce_distance_bands=True)
    entry = 100.0

    # Juda katta ATR -> Stop 5% dan keng
    keng = _build_stop(entry, support_low=99.9, atr=entry * 0.10, rules=qoidalar)
    assert keng is None, "juda keng Stop rad etilishi kerak"

    # Juda kichik ATR va support deyarli entry'da -> Stop 1% dan tor
    tor = _build_stop(entry, support_low=99.99, atr=entry * 0.0005, rules=qoidalar)
    assert tor is None, "juda tor Stop rad etilishi kerak"


# --------------------------------------------------------------------------- #
#  TUZATISH 3 — nisbat strategiya darajasida
# --------------------------------------------------------------------------- #


def test_mean_reversion_nisbati_globaldan_past(config: AppConfig) -> None:
    """1:3 mean reversion uchun deyarli hech qachon bajarilmaydigan shart edi."""
    assert config.strategies.classic_ta.min_risk_reward < config.trade_rules.min_risk_reward


def test_qurish_va_tekshirish_bir_xil_nisbatga_tayanadi(config: AppConfig) -> None:
    """YAGONA MANBA sinovi.

    Darajalarni QURISH (`build_levels`) va ularni TEKSHIRISH
    (`TradeRulesRule`) ajralib qolsa, TP2 bir qiymat bo'yicha quriladi,
    boshqasi bo'yicha rad etiladi — signal hech qachon chiqmaydi.
    """
    qoida = next(r for r in RiskEngine(config).rules if r.name == "trade_rules")
    _, _, tekshiruv_nisbati, _ = qoida._bounds_for(SignalSource.CLASSIC_TA)

    assert tekshiruv_nisbati == classic_ta_rules(config).min_risk_reward


def test_har_strategiya_oz_nisbatini_saqlaydi(config: AppConfig) -> None:
    """Skalping va mean reversion bir-biriga ta'sir qilmaydi."""
    qoida = next(r for r in RiskEngine(config).rules if r.name == "trade_rules")

    klassik = qoida._bounds_for(SignalSource.CLASSIC_TA)
    skalp = qoida._bounds_for(SignalSource.OPENING_RANGE_SCALP)
    assert klassik != skalp


def test_past_nisbat_bilan_darajalar_quriladi(config: AppConfig) -> None:
    """1:1.5 nisbat bilan TP2 erishiladigan masofada bo'lishi kerak.

    1:3 talab qilinganda Stop 4% bo'lsa TP2 12% da qolardi — 4 soatlik
    grafikda bunday harakat kam uchraydi.
    """
    qoidalar = classic_ta_rules(config)
    stop_pct = 3.0
    kerakli_tp2 = stop_pct * qoidalar.min_risk_reward

    assert kerakli_tp2 <= qoidalar.max_tp_distance_pct
    # Global qiymat bilan solishtirish: u qanchalik uzoq bo'lardi
    global_tp2 = stop_pct * config.trade_rules.min_risk_reward
    assert global_tp2 > kerakli_tp2


# --------------------------------------------------------------------------- #
#  Yo'l-yo'lakay: haftalik salomatlik tuzog'i
# --------------------------------------------------------------------------- #


def test_tarixi_yetmagan_coin_kenglikka_qoshilmaydi() -> None:
    """Aniqlab bo'lmagan coin kenglik hisobiga KIRMAYDI (0.3-band).

    Ilgari chegara EMA200 edi: haftalik timeframeda 200 sham ~3.8 yil
    tarix degani va ko'p altcoinlar jimgina "ko'tarilishda emas" deb
    sanalardi — kenglik sun'iy tushib, indeks signalni to'xtatardi.

    EMA olib tashlangach chegara `min_candles` ga tushdi, lekin
    QOIDANING O'ZI qoladi: tarixi yetmagan coin hisobga kirmasligi
    kerak, "ko'tarilishda emas" deb sanalmasligi kerak.
    """
    ind = load_config().analysis.indicators
    assert ind.min_candles < 200, "EMA200 chegarasi qolib ketmasin"

    # Qoida `compute_health` da: tarixi yetmagan coin hisobga UMUMAN
    # kirmaydi. Uni "ko'tarilishda emas" deb sanash kenglikni sun'iy
    # tushirardi (33-bo'lim) — pastdagi test manbani tekshiradi.
    assert len(_shamlar(ind.min_candles - 5)) < ind.min_candles

def _shamlar(n: int):  # noqa: ANN202
    from datetime import UTC, datetime, timedelta

    from core.domain.models import Candle

    bosh = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(bosh + timedelta(days=i), 100 + i, 101 + i, 99 + i, 100 + i, 1000.0)
        for i in range(n)
    ]


def test_qisqa_tarixli_coin_hisobdan_chiqariladi(config: AppConfig) -> None:
    """Yetarli tarixsiz coin kenglikka KIRMAYDI (0.3-band).

    Tekshiruv endi manba matnida emas, XATTI-HARAKATDA: hisob
    `universe_facts()` ga ko'chdi va uni jonli tizim ham, backtest ham
    chaqiradi. Matnni qidirish o'sha ko'chishdan keyin yolg'on
    signal berardi.
    """
    from core.analysis.market_health import universe_facts

    tf = config.analysis.market_health_timeframe
    kerak = config.analysis.indicators.min_candles

    faktlar = universe_facts(
        {
            "UZUN": {tf: _shamlar(kerak + 20)},
            "QISQA": {tf: _shamlar(kerak - 5)},
        },
        config.analysis,
    )

    assert "UZUN" in faktlar.structures
    assert "QISQA" not in faktlar.structures, (
        "tarix yetarliligi tekshiruvi olib tashlangan — haftalik indeks buziladi"
    )


def test_kenglik_jonli_va_backtestda_bir_xil_funksiyadan(config: AppConfig) -> None:
    """Ikki joy hisobni O'ZIDA takrorlamasin.

    Aynan shu takror jonli tizim bilan backtestni ajratib yuborgan
    edi: biri haftalik strukturani, ikkinchisi 4 soatlikni o'qirdi
    (`docs/ARXITEKTURA.md`, 68-bo'lim).
    """
    import inspect

    from bot.services import runner as runner_moduli
    from core.backtest import engine as backtest_moduli

    jonli = inspect.getsource(runner_moduli.PipelineRunner.compute_health)
    sinov = inspect.getsource(backtest_moduli.Backtester._build_input)

    for nom, manba in (("runner", jonli), ("backtest", sinov)):
        assert "universe_facts(" in manba, f"{nom}: umumiy funksiya chaqirilmayapti"
        assert "analyze_structure(" not in manba, (
            f"{nom}: kenglik hisobi yana takrorlanyapti"
        )


def test_ball_ham_strategiya_nisbatiga_tayanadi(config: AppConfig) -> None:
    """UCHINCHI manba: ball hisobi ham bir xil nisbatni ko'rishi kerak.

    Darajalar 1:1.5 bo'yicha quriladi. Agar ball global 1:3 bo'yicha
    hisoblansa, R/R komponenti "minimaldan past" deb 0 qaytaradi —
    15 balldan ayrilish esa chegaradan (55) o'tishni imkonsiz qiladi.
    Ya'ni 3-tuzatish jimgina bekor bo'lardi.
    """
    from core.analysis.scoring.factors import score_risk_reward

    qoidalar = classic_ta_rules(config)
    kerak = qoidalar.min_risk_reward

    entry, stop_pct = 100.0, 3.0
    darajalar = signal_levels(
        entry=entry,
        stop=entry * (1 - stop_pct / 100),
        tp1=entry * (1 + stop_pct * 1.05 / 100),
        tp2=entry * (1 + stop_pct * kerak / 100),
    )
    assert darajalar.risk_reward == pytest.approx(kerak, rel=0.01)

    strategiya_bali = score_risk_reward(darajalar, qoidalar, 15.0)
    global_ball = score_risk_reward(darajalar, config.trade_rules, 15.0)

    assert strategiya_bali.earned > 0, "o'z nisbatida qurilgan daraja ball olishi kerak"
    assert global_ball.earned == 0, "global nisbat bilan u nolga tushardi — tuzoq shu"


def test_zanjir_uchidan_uchiga_bir_xil_nisbat(config: AppConfig) -> None:
    """Qurish, ball va tekshiruv — uchalasi bir manbadan.

    Ular ajralib qolsa signal hech qachon chiqmaydi va sabab
    dashboardda ko'rinmaydi.
    """
    import ast
    import inspect
    import textwrap

    from core.analysis.strategies import classic_ta as modul

    manba = inspect.getsource(modul.ClassicTaStrategy.analyze)
    assert "qoidalar = classic_ta_rules(self._config)" in manba
    assert "rules=qoidalar" in manba, "ball hisobiga ham uzatilishi shart"

    # Matn qidiruvi emas, TUZILMA: qator uzunligi yoki yangi argument
    # qo'shilishi testni buzmasin — muhimi `qoidalar` uzatilgani.
    daraxt = ast.parse(textwrap.dedent(manba))
    chaqiruvlar = [
        tugun
        for tugun in ast.walk(daraxt)
        if isinstance(tugun, ast.Call)
        and isinstance(tugun.func, ast.Name)
        and tugun.func.id == "build_levels"
    ]
    assert len(chaqiruvlar) == 1, "build_levels aynan bir marta chaqirilsin"
    argumentlar = [
        a.id for a in chaqiruvlar[0].args if isinstance(a, ast.Name)
    ]
    assert "qoidalar" in argumentlar, (
        "darajalar `classic_ta_rules()` qaytargan qoidalardan qurilsin"
    )
