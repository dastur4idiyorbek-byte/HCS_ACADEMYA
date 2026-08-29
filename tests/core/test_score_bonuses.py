"""ICT Kill Zone bonusi va QT (AMDX) davri.

Struktura, daraja turi va sweep testlari bu yerda EMAS: ular endi
alohida bonus emas, mavjud omillar ichidagi dalil
(`tests/core/test_omil_kotarish.py`).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.analysis.market_health.quarterly import (
    QuarterPhase,
    describe_phase,
    quarterly_phase,
)
from core.analysis.scoring.bonuses import (
    build_bonus_components,
    in_session_overlap,
    score_session_overlap,
)
from core.config.schema import ScoreBonuses, SessionOverlapConfig

OYNA = SessionOverlapConfig(enabled=True, start_hour_utc=13, end_hour_utc=16)


# --------------------------------------------------------------------------- #
#  ICT Kill Zone
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("soat", [13, 14, 15])
def test_oyna_ichidagi_soatlar(soat: int) -> None:
    assert in_session_overlap(datetime(2026, 8, 21, soat, tzinfo=UTC), OYNA)


@pytest.mark.parametrize("soat", [0, 12, 16, 23])
def test_oyna_tashqarisidagi_soatlar(soat: int) -> None:
    assert not in_session_overlap(datetime(2026, 8, 21, soat, tzinfo=UTC), OYNA)


def test_yarim_tunni_kesib_otuvchi_oyna() -> None:
    """22:00-02:00 kabi oyna oddiy `start <= soat < end` bilan ishlamaydi."""
    kechasi = SessionOverlapConfig(enabled=True, start_hour_utc=22, end_hour_utc=2)
    assert in_session_overlap(datetime(2026, 8, 21, 23, tzinfo=UTC), kechasi)
    assert in_session_overlap(datetime(2026, 8, 21, 1, tzinfo=UTC), kechasi)
    assert not in_session_overlap(datetime(2026, 8, 21, 12, tzinfo=UTC), kechasi)


def test_ochirilgan_oyna_ball_bermaydi() -> None:
    ochiq = SessionOverlapConfig(enabled=False)
    omil = score_session_overlap(datetime(2026, 8, 21, 14, tzinfo=UTC), ochiq, 5.0)
    assert omil.earned == 0.0


def test_oyna_tashqarisida_ball_yoq_lekin_izoh_bor() -> None:
    """Foydalanuvchi nima uchun bonus yo'qligini ko'ra olishi kerak."""
    omil = score_session_overlap(datetime(2026, 8, 21, 3, tzinfo=UTC), OYNA, 5.0)
    assert omil.earned == 0.0
    assert "tashqarida" in omil.explanation


def test_vaqt_nomalum_bolsa_xato_bermaydi() -> None:
    assert score_session_overlap(None, OYNA, 5.0).earned == 0.0


# --------------------------------------------------------------------------- #
#  QT — Quarterly Theory (AMDX)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("soat", "kutilgan"),
    [
        (0, QuarterPhase.ACCUMULATION),
        (5, QuarterPhase.ACCUMULATION),
        (6, QuarterPhase.MANIPULATION),
        (12, QuarterPhase.DISTRIBUTION),
        (18, QuarterPhase.CONTINUATION),
        (23, QuarterPhase.CONTINUATION),
    ],
)
def test_sutka_tort_chorakka_bolinadi(soat: int, kutilgan: QuarterPhase) -> None:
    assert quarterly_phase(datetime(2026, 8, 21, soat, tzinfo=UTC)) is kutilgan


def test_manipulyatsiya_eng_past_ball_oladi() -> None:
    """M davrida yolg'on harakatlar bo'ladi — eng xavfli davr."""
    ballar = {d: d.score for d in QuarterPhase}
    assert min(ballar, key=ballar.get) is QuarterPhase.MANIPULATION
    assert max(ballar, key=ballar.get) is QuarterPhase.CONTINUATION


def test_davrlar_aylanma_tartibda() -> None:
    assert QuarterPhase.CONTINUATION.next_phase is QuarterPhase.ACCUMULATION
    assert QuarterPhase.ACCUMULATION.next_phase is QuarterPhase.MANIPULATION


def test_davr_matni_saytga_tayyor() -> None:
    matn = describe_phase(datetime(2026, 8, 21, 14, tzinfo=UTC))
    assert "Distribution" in matn


# --------------------------------------------------------------------------- #
#  Yaxlit: bonuslar bazaviy ballni buzmaydi
# --------------------------------------------------------------------------- #


def test_bonus_deb_belgilanadi() -> None:
    """Belgi darvozani himoya qiladi: chegara faqat bazaviy ballda."""
    komponentlar = build_bonus_components(
        moment=datetime(2026, 8, 21, 14, tzinfo=UTC),
        bonuses=ScoreBonuses(),
        session=OYNA,
    )
    assert len(komponentlar) == 1
    assert all(k.bonus for k in komponentlar)


def test_vaqt_nomalum_bolsa_ham_komponent_qaytadi() -> None:
    """Ro'yxat uzunligi o'zgarmasin: shkala (maximum) barqaror qolishi kerak."""
    komponentlar = build_bonus_components(
        moment=None, bonuses=ScoreBonuses(), session=OYNA
    )
    assert len(komponentlar) == 1
    assert sum(k.earned for k in komponentlar) == 0.0
    assert sum(k.maximum for k in komponentlar) == ScoreBonuses().total()
