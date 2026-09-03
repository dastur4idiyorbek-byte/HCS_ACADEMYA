"""ULANMAGAN BAYROQLAR — e'lon qilingan, lekin ishlamagan sozlamalar (audit, 2-bosqich).

Loyihaning ikkinchi takrorlanuvchi xato naqshi: sozlama `default.yaml`
da bor, `schema.py` da bor, hisoblanadi ham — lekin natijaga HECH
QANDAY ta'sir qilmaydi. Bunday bayroq eng xavflisi: hujjat "yoqilgan"
deydi, tizim esa uni ko'rmaydi.

Bu fayl har birini xatti-harakat orqali qulflaydi.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.indicators.confirmation import confirm
from core.analysis.scoring.bonuses import in_session_overlap, score_session_overlap
from core.config import load_config
from core.domain.enums import BlockReason, SignalSource, ZoneKind
from core.domain.models import SignalCandidate, SRZone, signal_levels
from core.risk_engine import RiskContext, RiskEngine
from core.risk_engine.rules import ZoneIntegrityRule
from core.signals.tracker import DEFAULT_FALSE_SIGNAL_WINDOW, kuzatuvchi_qur
from core.utils.time_utils import timeframe_minutes


@pytest.fixture
def config():
    return load_config()


# --------------------------------------------------------------------------- #
#  2.1 — Kill Zone 4 soatlik panjarada ishlaydimi
# --------------------------------------------------------------------------- #


def _4h_panjara() -> list[datetime]:
    return [datetime(2026, 1, 5, soat, tzinfo=UTC) for soat in range(0, 24, 4)]


def test_kill_zone_4h_panjarada_ishlaydi(config):
    """ENG MUHIM TEST. Bonus AMALDA hech qachon berilmasdi.

        4 soatlik ochilishlar:  00 04 08 12 16 20 UTC
        Kill Zone oynasi:       13 <= soat < 16
        kesishma nuqta bo'yicha: BO'SH

    Ya'ni sozlama yoqilgan, kod yozilgan, natija nol edi.
    """
    session = config.analysis.session_overlap
    davomiylik = timeframe_minutes(config.analysis.entry_timeframe)

    ichida = [
        moment for moment in _4h_panjara() if in_session_overlap(moment, session, davomiylik)
    ]
    assert ichida, (
        "Kill Zone 4 soatlik panjarada hech qachon ishlamayapti — "
        "bonus o'lik bayroq"
    )
    # Kuniga aynan bitta sham: 12:00-16:00 oynani qamraydi.
    assert len(ichida) == 1
    assert ichida[0].hour == 12


def test_kill_zone_nuqta_bolib_qolmaydi(config):
    """Bir soatlik oyna bilan tekshirilganda eski xatti-harakat qaytadi."""
    session = config.analysis.session_overlap
    assert not any(in_session_overlap(m, session, 60) for m in _4h_panjara())


def test_kill_zone_oynadan_tashqaridagi_sham_bonus_olmaydi(config):
    session = config.analysis.session_overlap
    davomiylik = timeframe_minutes(config.analysis.entry_timeframe)
    tashqarida = datetime(2026, 1, 5, 0, tzinfo=UTC)
    omil = score_session_overlap(tashqarida, session, 5.0, davomiylik)
    assert omil.earned == 0.0
    assert omil.bonus is True


def test_kill_zone_ichidagi_sham_toliq_bonus_oladi(config):
    session = config.analysis.session_overlap
    davomiylik = timeframe_minutes(config.analysis.entry_timeframe)
    omil = score_session_overlap(datetime(2026, 1, 5, 12, tzinfo=UTC), session, 5.0, davomiylik)
    assert omil.earned == 5.0


def test_yarim_tundan_otuvchi_oyna(config):
    """22:00-02:00 kabi oyna ham to'g'ri hisoblansin."""
    session = dataclasses.replace(
        config.analysis.session_overlap, start_hour_utc=22, end_hour_utc=2
    )
    assert in_session_overlap(datetime(2026, 1, 5, 20, tzinfo=UTC), session, 240)
    assert in_session_overlap(datetime(2026, 1, 5, 0, tzinfo=UTC), session, 240)
    assert not in_session_overlap(datetime(2026, 1, 5, 4, tzinfo=UTC), session, 240)


def test_bonus_chegaraga_tasir_qilmaydi(config):
    """Kill Zone bonusi TARTIBGA ta'sir qiladi, signal soniga emas.

    Chegara `base_total` bo'yicha tekshiriladi (`scorer.py`), bonus esa
    100 ning USTIGA qo'shiladi.
    """
    manba = (
        __import__("pathlib").Path("core/analysis/scoring/scorer.py")
        .read_text(encoding="utf-8")
    )
    assert "ball = nomzod.breakdown.base_total" in manba


# --------------------------------------------------------------------------- #
#  2.2 — zona buzilgani Risk Engine'da tekshiriladi
# --------------------------------------------------------------------------- #


def _nomzod(entry: float = 100.0) -> SignalCandidate:
    darajalar = signal_levels(entry, entry * 0.97, entry * 1.09)
    return SignalCandidate(
        symbol="BTC",
        levels=darajalar,
        source=SignalSource.CLASSIC_TA,
        breakdown=None,
        halal_verdict=None,
    )


def _qoida(config) -> ZoneIntegrityRule:  # noqa: ANN001
    return ZoneIntegrityRule(
        config.risk_engine, config.analysis.entry_order.zone_broken_threshold_pct
    )


def _kontekst(narx: float | None) -> RiskContext:
    return RiskContext(now=datetime(2026, 1, 5, tzinfo=UTC), current_price=narx)


def test_zona_buzilgan_bolsa_signal_toxtaydi(config):
    chegara = config.analysis.entry_order.zone_broken_threshold_pct
    narx = 100.0 * (1 - (chegara + 0.5) / 100)
    qaror = _qoida(config).check(_nomzod(), _kontekst(narx))
    assert not qaror.allowed
    assert BlockReason.ZONE_BROKEN in qaror.reasons


def test_zona_ichida_bolsa_otadi(config):
    chegara = config.analysis.entry_order.zone_broken_threshold_pct
    narx = 100.0 * (1 - (chegara / 2) / 100)
    assert _qoida(config).check(_nomzod(), _kontekst(narx)).allowed


def test_narx_yuqorida_bolsa_otadi(config):
    """Narx kirishdan YUQORIDA — zona buzilmagan, faqat kech kirish."""
    assert _qoida(config).check(_nomzod(), _kontekst(105.0)).allowed


def test_narx_nomalum_bolsa_toxtatmaydi(config):
    """Narx yo'qligini `FreshDataRule` ushlaydi — bu yerda jazo yo'q."""
    assert _qoida(config).check(_nomzod(), _kontekst(None)).allowed


def test_qoida_engine_royxatida_bor(config):
    nomlar = [qoida.name for qoida in RiskEngine(config)._rules]
    assert "zone_integrity" in nomlar


def test_backtest_narxni_uzatadi():
    """Qoida FAQAT jonlida ishlab qolmasin — backtest ham narx bersin."""
    from pathlib import Path

    manba = Path("core/backtest/engine.py").read_text(encoding="utf-8")
    assert "prices=narxlar" in manba


# --------------------------------------------------------------------------- #
#  2.3 — yarim holat qolmadi
# --------------------------------------------------------------------------- #


def test_bozor_rejimi_qoidasi_yoq(config):
    """`MarketRegimeRule` olib tashlandi — sabab `rules.py` da yozilgan."""
    nomlar = [qoida.name for qoida in RiskEngine(config)._rules]
    assert "market_regime" not in nomlar


def test_adx_chegarasi_hamon_ballda_ishlatiladi(config):
    """ADX yo'qolmadi: u to'siq emas, BAHO bo'lib qoldi."""
    from pathlib import Path

    manba = Path("core/analysis/scoring/factors.py").read_text(encoding="utf-8")
    assert "adx_trend_threshold" in manba


# --------------------------------------------------------------------------- #
#  2.4 — ikkita o'lik sozlama ulandi
# --------------------------------------------------------------------------- #


def test_yolgon_signal_oynasi_sozlamadan_olinadi(config):
    """`postmortem.false_signal_window_minutes` endi o'qiladi."""
    ozgargan = dataclasses.replace(
        config,
        postmortem=dataclasses.replace(config.postmortem, false_signal_window_minutes=15),
    )
    kuzatuvchi = kuzatuvchi_qur(ozgargan)
    assert kuzatuvchi._false_signal_window == timedelta(minutes=15)
    assert kuzatuvchi._false_signal_window != DEFAULT_FALSE_SIGNAL_WINDOW


def test_jonli_va_backtest_bir_xil_kuzatuvchi():
    from pathlib import Path

    for yol in ("bot/services/watcher.py", "core/backtest/engine.py"):
        assert "kuzatuvchi_qur" in Path(yol).read_text(encoding="utf-8"), yol


def test_tp_ulushlari_sozlamadan_olinadi(config):
    """`portfolio.tp_close_shares` endi darajalarga yetib boradi."""
    from core.analysis.scoring.levels import build_levels
    from core.analysis.support_resistance.detector import ZoneMap

    zonalar = [
        SRZone(ZoneKind.SUPPORT, 96.0, 97.0, touches=3),
        SRZone(ZoneKind.RESISTANCE, 112.0, 113.0, touches=2),
    ]
    xarita = ZoneMap(zones=zonalar, price=100.0, atr=1.0, proximity_atr=3.0)

    natija = build_levels(xarita, config.trade_rules, portfolio=config.portfolio)
    assert natija.ok, natija.reason
    ulushlar = tuple(tp.close_pct for tp in natija.levels.takes)
    assert ulushlar == config.portfolio.shares_for(len(ulushlar))
    assert sum(ulushlar) == pytest.approx(100.0)


# --------------------------------------------------------------------------- #
#  2.5 — izoh haqiqatga mos
# --------------------------------------------------------------------------- #


def test_tasdiq_omillari_uchta(config):
    """Izoh "4 tadan" derdi — trend bu ro'yxatda YO'Q va hech qachon bo'lmagan.

    Ya'ni `min_confirmations: 4` erishib bo'lmaydigan qiymat edi:
    uni qo'ygan odam tizimni jimgina butunlay to'xtatib qo'yardi.
    """
    from core.analysis.indicators.snapshot import IndicatorSnapshot

    holat = IndicatorSnapshot(
        price=100.0,
        rsi=45.0,
        rsi_recovering=False,
        macd=None,
        volume_ratio=1.2,
        adx=25.0,
        atr=1.0,
        atr_pct=1.0,
    )
    hukm = confirm(holat, config.analysis.indicators, zone_ready=True)
    nomlar = {omil.name for omil in hukm.factors}
    assert nomlar == {"rsi", "macd", "volume"}
    assert config.analysis.indicators.min_confirmations <= len(nomlar)
