"""CryptoSpot3% ball bonuslari, ICT Kill Zone va QT (AMDX) davri.

Asosiy tekshiriladigan xatti-harakat: bu omillar ball BERADI, lekin
hech qachon YO'LNI YOPMAYDI. Metodika hujjatining o'zi ham shuni talab
qiladi — bu loyihada qat'iy "VA" filtrlarini ko'paytirish signal
voronkasini allaqachon nolga tushirgan.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.analysis.level_types import LevelType
from core.analysis.market_health.quarterly import (
    QuarterPhase,
    describe_phase,
    quarterly_phase,
)
from core.analysis.market_structure import MarketStructure, StructureBreak
from core.analysis.scoring.bonuses import (
    build_bonus_components,
    in_session_overlap,
    score_liquidity_sweep,
    score_session_overlap,
    score_structure,
)
from core.analysis.support_resistance.liquidity import LiquiditySweep
from core.config.schema import ScoreBonuses, SessionOverlapConfig
from core.domain.enums import TrendDirection

OYNA = SessionOverlapConfig(enabled=True, start_hour_utc=13, end_hour_utc=16)


def kotarilish() -> MarketStructure:
    return MarketStructure(
        swings=[],
        direction=TrendDirection.UP,
        last_bos=StructureBreak("bos", 100.0, 5, TrendDirection.UP),
    )


def pasayish() -> MarketStructure:
    return MarketStructure(swings=[], direction=TrendDirection.DOWN)


def yalash(bars_since: int = 0) -> LiquiditySweep:
    return LiquiditySweep(
        swept_price=98.5,
        index=20,
        depth_pct=0.5,
        reclaim_index=21,
        bars_since=bars_since,
    )


# --------------------------------------------------------------------------- #
#  Struktura bonusi
# --------------------------------------------------------------------------- #


def test_kotarilish_strukturasi_toliq_bonus_beradi() -> None:
    omil = score_structure(kotarilish(), LevelType.QUASIMODO, 10.0)
    assert omil.earned == pytest.approx(10.0)
    assert omil.bonus is True


def test_pasayish_strukturasi_bonus_bermaydi_lekin_manfiy_ham_emas() -> None:
    """Nol — bu JAZO emas. Nomzod bazaviy ballini to'liq saqlaydi."""
    omil = score_structure(pasayish(), LevelType.PLAIN, 10.0)
    assert omil.earned == 0.0


def test_hisoblanmagan_struktura_xato_bermaydi() -> None:
    omil = score_structure(None, LevelType.PLAIN, 10.0)
    assert omil.earned == 0.0
    assert "hisoblanmadi" in omil.explanation


def test_kuchli_daraja_turi_bonusni_oshiradi() -> None:
    oddiy = score_structure(kotarilish(), LevelType.PLAIN, 10.0)
    kuchli = score_structure(kotarilish(), LevelType.STRONG_OB, 10.0)
    assert kuchli.earned > oddiy.earned


def test_daraja_turi_izohga_qoshiladi() -> None:
    omil = score_structure(kotarilish(), LevelType.RBS, 10.0)
    assert "RBS" in omil.explanation


# --------------------------------------------------------------------------- #
#  Liquidity Sweep bonusi
# --------------------------------------------------------------------------- #


def test_topilmagan_sweep_nol_beradi() -> None:
    omil = score_liquidity_sweep(None, 10.0)
    assert omil.earned == 0.0
    assert omil.bonus is True


def test_yangi_sweep_eskisidan_kop_ball_oladi() -> None:
    """Qaytishdan ko'p vaqt o'tgan bo'lsa, naqsh o'z ishini qilib bo'lgan."""
    yangi = score_liquidity_sweep(yalash(bars_since=0), 10.0)
    eski = score_liquidity_sweep(yalash(bars_since=9), 10.0)
    assert yangi.earned > eski.earned


def test_juda_eski_sweep_ham_manfiy_bermaydi() -> None:
    omil = score_liquidity_sweep(yalash(bars_since=100), 10.0)
    assert omil.earned >= 0.0


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


def test_barcha_bonuslar_bonus_deb_belgilanadi() -> None:
    """Bu belgi darvozani himoya qiladi: chegara faqat bazaviy ballda."""
    komponentlar = build_bonus_components(
        structure=kotarilish(),
        level_type=LevelType.RBS,
        sweep=yalash(),
        moment=datetime(2026, 8, 21, 14, tzinfo=UTC),
        bonuses=ScoreBonuses(),
        session=OYNA,
    )
    assert len(komponentlar) == 3
    assert all(k.bonus for k in komponentlar)


def test_hech_narsa_topilmasa_ham_uch_komponent_qaytadi() -> None:
    """Ro'yxat uzunligi o'zgarmasin: shkala (maximum) barqaror qolishi kerak."""
    komponentlar = build_bonus_components(
        structure=None,
        level_type=LevelType.PLAIN,
        sweep=None,
        moment=None,
        bonuses=ScoreBonuses(),
        session=OYNA,
    )
    assert len(komponentlar) == 3
    assert sum(k.earned for k in komponentlar) == 0.0
    assert sum(k.maximum for k in komponentlar) == ScoreBonuses().total()
