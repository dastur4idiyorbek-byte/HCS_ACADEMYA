"""3.8-band: Signal Xotirasi — naqsh izlash va o'z-o'zini tekshirish.

Eng muhim talab: HALOLLIK. Kichik namuna asosida naqsh e'lon qilinmasligi
kerak — 5 ta signaldan "70% Stop yeydi" degan xulosa statistika emas,
shovqin. Testlarning katta qismi aynan shuni tekshiradi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.postmortem import (
    ClosedSignal,
    Outcome,
    build_report,
    compute_stats,
    find_patterns,
    outcome_from_status,
    render_report,
)
from core.analysis.postmortem.patterns import market_health_pattern, score_pattern
from core.config.schema import PostmortemConfig
from core.domain.enums import SignalSource, SignalStatus

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
KONFIG = PostmortemConfig(min_sample_size=5, min_effect_pct=15.0, lookback_days=30)


def signal(
    outcome: Outcome = Outcome.TP2,
    score: float | None = 80.0,
    health: float | None = 75.0,
    source: SignalSource = SignalSource.CLASSIC_TA,
    false_signal: bool = False,
    holding_hours: float = 6.0,
    signal_id: int = 1,
) -> ClosedSignal:
    yopilish = HOZIR - timedelta(days=1)
    return ClosedSignal(
        signal_id=signal_id,
        symbol="BTC",
        source=source,
        outcome=outcome,
        score=score,
        market_health_at_entry=health,
        result_pct=3.0 if outcome.is_win else -1.0,
        created_at=yopilish - timedelta(hours=holding_hours + 1),
        activated_at=yopilish - timedelta(hours=holding_hours),
        closed_at=yopilish,
        is_false_signal=false_signal,
    )


def guruh(n: int, **kwargs) -> list[ClosedSignal]:
    return [signal(signal_id=i, **kwargs) for i in range(n)]


# --------------------------------------------------------------------------- #
#  Natija turlari
# --------------------------------------------------------------------------- #


def test_tp1_dan_keyin_stop_alohida_natija() -> None:
    """"Stop yedi" va "TP1 oldi, keyin Stop yedi" bir xil natija emas."""
    assert outcome_from_status(SignalStatus.STOPPED, reached_tp1=True) is Outcome.TP1_THEN_STOP
    assert outcome_from_status(SignalStatus.STOPPED, reached_tp1=False) is Outcome.STOP


def test_tp1_dan_keyingi_stop_foyda_hisoblanadi() -> None:
    """Pozitsiyaning bir qismi TP1 da yopilgan."""
    assert Outcome.TP1_THEN_STOP.is_win
    assert not Outcome.TP1_THEN_STOP.is_loss


def test_bekor_qilingan_signal_statistikaga_kirmaydi() -> None:
    """U savdo bo'lmagan — win-rate ni buzmasligi kerak."""
    assert not Outcome.CANCELLED.counts_in_stats
    assert Outcome.STOP.counts_in_stats


def test_yopilmagan_signal_tahlil_qilinmaydi() -> None:
    with pytest.raises(ValueError, match="Yopilmagan"):
        outcome_from_status(SignalStatus.ACTIVE, reached_tp1=False)


# --------------------------------------------------------------------------- #
#  HALOLLIK: kichik namunada naqsh e'lon qilinmaydi
# --------------------------------------------------------------------------- #


def test_kichik_namunada_naqsh_elon_qilinmaydi() -> None:
    """5 ta signaldan "70% Stop yeydi" — statistika emas, shovqin."""
    kichik = [
        *guruh(3, outcome=Outcome.STOP, health=40.0),
        *guruh(3, outcome=Outcome.TP2, health=80.0),
    ]
    assert find_patterns(kichik, KONFIG) == []


def test_yetarli_namunada_naqsh_topiladi() -> None:
    signallar = [
        *guruh(10, outcome=Outcome.STOP, health=40.0),
        *guruh(10, outcome=Outcome.TP2, health=85.0),
    ]
    naqsh = market_health_pattern(signallar, KONFIG)

    assert naqsh is not None
    assert naqsh.effect_pct == pytest.approx(100.0)
    assert "60" in naqsh.recommendation


def test_zaif_tasir_naqsh_hisoblanmaydi() -> None:
    """Farq kichik bo'lsa — bu naqsh emas, tabiiy tarqalish."""
    signallar = [
        *guruh(5, outcome=Outcome.STOP, health=40.0),
        *guruh(5, outcome=Outcome.TP2, health=40.0),
        *guruh(4, outcome=Outcome.STOP, health=85.0),
        *guruh(6, outcome=Outcome.TP2, health=85.0),
    ]
    assert market_health_pattern(signallar, KONFIG) is None


def test_malumot_yoq_signal_naqshni_buzmaydi() -> None:
    """Salomatlik qayd etilmagan signal ikkala guruhga ham kirmasligi kerak."""
    signallar = [
        *guruh(8, outcome=Outcome.STOP, health=None),
        *guruh(6, outcome=Outcome.STOP, health=40.0),
        *guruh(6, outcome=Outcome.TP2, health=85.0),
    ]
    naqsh = market_health_pattern(signallar, KONFIG)

    assert naqsh is not None
    assert naqsh.sample_size == 12, "ma'lumotsiz 8 ta signal hisobga olinmasligi kerak"


# --------------------------------------------------------------------------- #
#  Naqsh turlari
# --------------------------------------------------------------------------- #


def test_ball_naqshi_topiladi() -> None:
    signallar = [
        *guruh(8, outcome=Outcome.STOP, score=60.0),
        *guruh(8, outcome=Outcome.TP2, score=90.0),
    ]
    naqsh = score_pattern(signallar, KONFIG)

    assert naqsh is not None
    assert "chegarasini" in naqsh.recommendation


def test_yolgon_signal_naqshi_topiladi() -> None:
    signallar = [
        *guruh(7, outcome=Outcome.STOP, false_signal=True),
        *guruh(7, outcome=Outcome.TP2, false_signal=False),
    ]
    nomlar = {n.name for n in find_patterns(signallar, KONFIG)}
    assert "Zaif kirish nuqtalari" in nomlar


def test_strategiya_naqshi_topiladi() -> None:
    signallar = [
        *guruh(8, outcome=Outcome.STOP, source=SignalSource.OPENING_RANGE_SCALP),
        *guruh(8, outcome=Outcome.TP2, source=SignalSource.CLASSIC_TA),
    ]
    naqshlar = find_patterns(signallar, KONFIG)
    assert any(n.name == "Strategiyalar farqi" for n in naqshlar)


def test_naqshlar_tasir_kuchi_boyicha_tartiblanadi() -> None:
    signallar = [
        *guruh(8, outcome=Outcome.STOP, health=40.0, score=60.0, false_signal=True),
        *guruh(8, outcome=Outcome.TP2, health=85.0, score=90.0, false_signal=False),
    ]
    naqshlar = find_patterns(signallar, KONFIG)

    assert len(naqshlar) >= 2
    tasirlar = [n.effect_pct for n in naqshlar]
    assert tasirlar == sorted(tasirlar, reverse=True)


# --------------------------------------------------------------------------- #
#  Statistika
# --------------------------------------------------------------------------- #


def test_statistika_hisoblanadi() -> None:
    signallar = [
        *guruh(5, outcome=Outcome.TP2),
        *guruh(2, outcome=Outcome.TP1_THEN_STOP),
        *guruh(3, outcome=Outcome.STOP),
        *guruh(2, outcome=Outcome.CANCELLED),
    ]
    s = compute_stats(signallar)

    assert s.total == 12
    assert s.traded == 10, "bekor qilinganlar savdo emas"
    assert s.tp2 == 5
    assert s.win_rate == pytest.approx(0.7)
    assert s.stop_rate == pytest.approx(0.3)


def test_bosh_royxatda_statistika_xato_bermaydi() -> None:
    s = compute_stats([])
    assert s.total == 0
    assert s.win_rate is None
    assert s.stop_rate is None


def test_ortacha_ushlab_turish_vaqti() -> None:
    signallar = [
        signal(holding_hours=4.0, signal_id=1),
        signal(holding_hours=8.0, signal_id=2),
    ]
    assert compute_stats(signallar).average_holding_hours == pytest.approx(6.0)


# --------------------------------------------------------------------------- #
#  Hisobot
# --------------------------------------------------------------------------- #


def test_kichik_namuna_ochiq_aytiladi() -> None:
    """"Naqsh topilmadi" va "ma'lumot yetarli emas" bir xil narsa EMAS."""
    hisobot = build_report(guruh(3, outcome=Outcome.STOP), KONFIG, HOZIR)

    assert hisobot.sample_warning is not None
    assert "yetarli emas" in hisobot.sample_warning
    assert not hisobot.has_findings

    matn = render_report(hisobot)
    assert "Namuna kichik" in matn
    assert "muammo yo'q" in matn.lower() or "EMAS" in matn


def test_naqsh_topilmasa_ochiq_aytiladi() -> None:
    signallar = [
        *guruh(8, outcome=Outcome.TP2, health=85.0),
        *guruh(8, outcome=Outcome.TP2, health=40.0),
    ]
    hisobot = build_report(signallar, KONFIG, HOZIR)

    assert hisobot.sample_warning is None
    assert not hisobot.has_findings
    assert "Sezilarli naqsh topilmadi" in render_report(hisobot)


def test_hisobotda_avtomatik_ozgarmasligi_aytiladi() -> None:
    """3.8-band eng muhim tamoyili — matnda ochiq bo'lishi kerak."""
    matn = render_report(build_report(guruh(20, outcome=Outcome.TP2), KONFIG, HOZIR))

    assert "AVTOMATIK qo'llanilmaydi" in matn
    assert "qarori" in matn


def test_hisobot_naqshlarni_korsatadi() -> None:
    signallar = [
        *guruh(8, outcome=Outcome.STOP, health=40.0),
        *guruh(8, outcome=Outcome.TP2, health=85.0),
    ]
    matn = render_report(build_report(signallar, KONFIG, HOZIR))

    assert "Aniqlangan naqshlar" in matn
    assert "Stop" in matn
    assert "💡" in matn, "tavsiya bo'lishi kerak"


def test_hisobotda_asosiy_raqamlar_bor() -> None:
    signallar = [
        *guruh(6, outcome=Outcome.TP2),
        *guruh(4, outcome=Outcome.STOP),
        *guruh(2, outcome=Outcome.CANCELLED),
        *guruh(2, outcome=Outcome.STOP, false_signal=True),
    ]
    matn = render_report(build_report(signallar, KONFIG, HOZIR))

    assert "Win-rate" in matn
    assert "Bekor bo'lgan" in matn
    assert "Yolg'on signal" in matn
