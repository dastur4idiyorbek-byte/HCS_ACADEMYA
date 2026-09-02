"""ICT Kill Zone bonusi va QT (AMDX) davri.

Struktura, daraja turi va sweep testlari bu yerda EMAS: ular endi
alohida bonus emas, mavjud omillar ichidagi dalil
(`tests/core/test_omil_kotarish.py`).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from core.domain.models import Candle

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


def _qt_sham(i: int, h: float, low: float, c: float) -> Candle:
    return Candle(
        open_time=datetime(2026, 8, 21, tzinfo=UTC) + timedelta(hours=i),
        open=c,
        high=h,
        low=low,
        close=c,
        volume=1000.0,
    )


def _tekis(n: int, narx: float, kenglik: float, boshi: int = 0) -> list[Candle]:
    return [
        _qt_sham(boshi + i, narx + kenglik, narx - kenglik, narx) for i in range(n)
    ]


def test_davr_SOATGA_bogliq_emas() -> None:
    """Eng muhim o'zgarish: davr endi soatdan o'qilmaydi.

    Ilgari sutka to'rt olti soatlik chorakka bo'linardi va davr bozor
    holatidan qat'i nazar har kuni bir xil ritmda o'zgarardi. "Soat
    13:00 bo'ldi" degani "hozir asosiy harakat davri" degani emas.
    """
    shamlar = _tekis(20, 100, 1.0)
    ertalab = [
        Candle(
            open_time=datetime(2026, 8, 21, 3, tzinfo=UTC) + timedelta(hours=i),
            open=s.open, high=s.high, low=s.low, close=s.close, volume=s.volume,
        )
        for i, s in enumerate(shamlar)
    ]
    kechqurun = [
        Candle(
            open_time=datetime(2026, 8, 21, 19, tzinfo=UTC) + timedelta(hours=i),
            open=s.open, high=s.high, low=s.low, close=s.close, volume=s.volume,
        )
        for i, s in enumerate(shamlar)
    ]

    assert quarterly_phase(ertalab) == quarterly_phase(kechqurun)


def test_sokinlikda_A_davri() -> None:
    """Keng diapazondan keyin torayish — yig'ish (Accumulation)."""
    shamlar = [*_tekis(14, 100, 5.0), *_tekis(6, 100, 0.5, boshi=14)]
    assert quarterly_phase(shamlar) is QuarterPhase.ACCUMULATION


def test_sweep_bolsa_M_davri() -> None:
    """Oldingi tubdan pastga tushib, ichkariga QAYTGAN — likvidlik
    yig'ib olindi, ya'ni yolg'on harakat."""
    shamlar = [
        *_tekis(14, 100, 2.0),
        # tubdan pastga soya tashlaydi, lekin ichkarida yopiladi
        _qt_sham(14, 101, 94, 99),
        *_tekis(5, 100, 2.0, boshi=15),
    ]
    assert quarterly_phase(shamlar) is QuarterPhase.MANIPULATION


def test_aniqlab_bolmasa_davr_OYLAB_TOPILMAYDI() -> None:
    """Ma'lumot yetmasa `None` — soatdan davr chiqarilmaydi."""
    assert quarterly_phase([]) is None
    assert quarterly_phase(_tekis(4, 100, 1.0)) is None


def test_manipulyatsiya_eng_past_ball_oladi() -> None:
    """M davrida yolg'on harakatlar bo'ladi — eng xavfli davr."""
    ballar = {d: d.score for d in QuarterPhase}
    assert min(ballar, key=ballar.get) is QuarterPhase.MANIPULATION
    assert max(ballar, key=ballar.get) is QuarterPhase.CONTINUATION


def test_davrlar_aylanma_tartibda() -> None:
    assert QuarterPhase.CONTINUATION.next_phase is QuarterPhase.ACCUMULATION
    assert QuarterPhase.ACCUMULATION.next_phase is QuarterPhase.MANIPULATION


def test_davr_matni_saytga_tayyor() -> None:
    matn = describe_phase([*_tekis(14, 100, 5.0), *_tekis(6, 100, 0.5, boshi=14)])
    assert "Accumulation" in matn


def test_davr_aniqlanmasa_matn_ham_rost() -> None:
    """Bo'sh ma'lumotda "davr shu" deb yozib qo'yilmaydi."""
    assert "aniqlanmadi" in describe_phase([])


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
