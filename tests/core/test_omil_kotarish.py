"""CryptoSpot3% dalillari MAVJUD OMILLAR ICHIDA — oralashib ishlash.

Bu qatlamning butun ma'nosi shu yerda sinaladi. Dalillar alohida
omil emas:

    daraja turi + sweep  ->  S/R omilini ko'taradi (25 ball)

SMC strukturasi esa endi "ko'tarish" emas: EMA olib tashlangach u
trend omilining TO'LIQ HUQUQLI qismiga aylandi (59-bo'lim).

Ikki xossa QAT'IY talab qilinadi:
  1. dalil ballni hech qachon PASAYTIRMAYDI;
  2. dalil shkalani buzmaydi (omil o'z vaznidan oshmaydi).

Uchinchisi — eng muhimi: dalil BAZAVIY ballga qo'shilgani uchun u
chegaraga ta'sir qiladi, ya'ni signal SONINI ham o'zgartira oladi.
Ilgari u faqat bonus edi va reytingdan boshqa hech narsaga ta'sir
qilmasdi.
"""

from __future__ import annotations

import pytest

from core.analysis.level_types import LevelType
from core.analysis.market_structure import MarketStructure, StructureBreak
from core.analysis.scoring.factors import (
    _uplift,
    score_support_resistance,
    score_trend,
)
from core.analysis.support_resistance.liquidity import LiquiditySweep
from core.config.schema import IndicatorConfig
from core.domain.enums import TrendDirection, ZoneKind
from core.domain.models import SRZone

ZONA = SRZone(kind=ZoneKind.SUPPORT, low=99.0, high=101.0, touches=3)


def kotarilish(bos: bool = True) -> MarketStructure:
    return MarketStructure(
        swings=[],
        direction=TrendDirection.UP,
        last_bos=StructureBreak("bos", 100.0, 5, TrendDirection.UP) if bos else None,
    )


def pasayish() -> MarketStructure:
    return MarketStructure(swings=[], direction=TrendDirection.DOWN)


def yalash(bars_since: int = 0) -> LiquiditySweep:
    return LiquiditySweep(
        swept_price=98.5, index=20, depth_pct=0.5, reclaim_index=21, bars_since=bars_since
    )


class SoxtaXarita:
    """`ZoneMap` ning eng kichik o'rnini bosuvchisi."""

    atr = 2.0

    def distance_in_atr(self, zone: SRZone) -> float:  # noqa: ARG002
        return 0.5

    def range_position(self):  # noqa: ANN201
        return None


# --------------------------------------------------------------------------- #
#  Ko'tarish formulasi
# --------------------------------------------------------------------------- #


def test_dalil_yoq_bolsa_qiymat_ozgarmaydi() -> None:
    assert _uplift(0.4, evidence=0.0, share=0.5) == pytest.approx(0.4)


def test_dalil_shkalani_buzmaydi() -> None:
    """To'liq dalil, to'liq ulush — natija baribir 1 dan oshmaydi."""
    assert _uplift(0.9, evidence=1.0, share=1.0) == pytest.approx(1.0)
    assert _uplift(1.0, evidence=1.0, share=1.0) == pytest.approx(1.0)


def test_dalil_hech_qachon_pasaytirmaydi() -> None:
    for baza in (0.0, 0.25, 0.5, 0.75, 1.0):
        for dalil in (0.0, 0.3, 1.0):
            assert _uplift(baza, dalil, 0.5) >= baza


def test_past_ball_kop_foyda_koradi() -> None:
    """Mukammal zonaga qo'shadigan narsa kam, o'rtachasiga esa ko'p.

    Bu ataylab: dalilning qiymati aynan "ball tizimi ko'rmagan
    narsani ko'rsatish" da.
    """
    ortacha = _uplift(0.3, 1.0, 0.5) - 0.3
    yaxshi = _uplift(0.9, 1.0, 0.5) - 0.9
    assert ortacha > yaxshi


# --------------------------------------------------------------------------- #
#  S/R omili — daraja turi va sweep
# --------------------------------------------------------------------------- #


def test_sweep_sr_omilini_kotaradi() -> None:
    xarita = SoxtaXarita()
    dalilsiz = score_support_resistance(xarita, ZONA, None, 25.0, uplift=0.5)
    dalilli = score_support_resistance(
        xarita, ZONA, None, 25.0, sweep=yalash(), uplift=0.5
    )

    assert dalilli.earned > dalilsiz.earned
    assert dalilli.earned <= 25.0
    assert "🧲" in dalilli.explanation


def test_daraja_turi_sr_omilini_kotaradi() -> None:
    xarita = SoxtaXarita()
    oddiy = score_support_resistance(
        xarita, ZONA, None, 25.0, level_type=LevelType.PLAIN, uplift=0.5
    )
    kuchli = score_support_resistance(
        xarita, ZONA, None, 25.0, level_type=LevelType.QUASIMODO, uplift=0.5
    )

    assert kuchli.earned > oddiy.earned


def test_ikkala_dalil_birgalikda_kop_beradi() -> None:
    xarita = SoxtaXarita()
    bittasi = score_support_resistance(
        xarita, ZONA, None, 25.0, level_type=LevelType.RBS, uplift=0.5
    )
    ikkalasi = score_support_resistance(
        xarita, ZONA, None, 25.0, level_type=LevelType.QUASIMODO, sweep=yalash(), uplift=0.5
    )

    assert ikkalasi.earned > bittasi.earned


def test_kotarish_ochirilsa_eski_qiymat_qoladi() -> None:
    """`uplift=0` — qatlamni butunlay o'chirish yo'li."""
    xarita = SoxtaXarita()
    ochiq = score_support_resistance(
        xarita, ZONA, None, 25.0, level_type=LevelType.QUASIMODO, sweep=yalash(), uplift=0.0
    )
    dalilsiz = score_support_resistance(xarita, ZONA, None, 25.0, uplift=0.0)

    assert ochiq.earned == pytest.approx(dalilsiz.earned)


def test_eski_sweep_yangisidan_kam_beradi() -> None:
    xarita = SoxtaXarita()
    yangi = score_support_resistance(xarita, ZONA, None, 25.0, sweep=yalash(0), uplift=0.5)
    eski = score_support_resistance(xarita, ZONA, None, 25.0, sweep=yalash(9), uplift=0.5)

    assert yangi.earned > eski.earned


def test_sr_omili_bonus_deb_belgilanmaydi() -> None:
    """U bazaviy omil — chegara aynan shuni o'qiydi."""
    omil = score_support_resistance(SoxtaXarita(), ZONA, None, 25.0, sweep=yalash(), uplift=0.5)
    assert omil.bonus is False


# --------------------------------------------------------------------------- #
#  Trend omili — SMC strukturasi EMA ning O'RNIGA
# --------------------------------------------------------------------------- #


class SoxtaHolat:
    adx = 25.0


def test_struktura_trend_omilining_TO_LIQ_qismi() -> None:
    """EMA olib tashlangach struktura "qo'shimcha dalil" bo'lishdan chiqdi.

    U endi trend omilining eng katta ulushiga ega qismi
    (`TREND_ULUSHLARI["struktura"]`) — ya'ni u ballni ko'taruvchi
    bezak emas, o'lchovning o'zi.
    """
    from core.analysis.scoring.factors import TREND_ULUSHLARI

    assert "ema" not in TREND_ULUSHLARI
    assert "struktura" in TREND_ULUSHLARI
    # Yuqori timeframe ham STRUKTURA bilan aniqlanadi (`_timeframe_view`),
    # ya'ni trend omilining katta qismi tuzilmaga tayanadi.
    tuzilma = TREND_ULUSHLARI["struktura"] + TREND_ULUSHLARI["htf"]
    assert tuzilma > TREND_ULUSHLARI["adx"]


def test_kotarilish_strukturasi_koproq_ball_beradi() -> None:
    config = IndicatorConfig()
    pastga = score_trend(SoxtaHolat(), config, 20.0, 0.5, structure=pasayish())
    yuqoriga = score_trend(SoxtaHolat(), config, 20.0, 0.5, structure=kotarilish())

    assert yuqoriga.earned > pastga.earned
    assert yuqoriga.earned <= 20.0
    assert "🔵" in yuqoriga.explanation


def test_pasayish_strukturasi_qolgan_qismlarni_YO_QOTMAYDI() -> None:
    """Nol struktura balli — jazo emas: ADX va yuqori TF o'z ulushini saqlaydi.

    Ilgari `score_trend` trend tasdiqlanmasa DARHOL 0 qaytarardi va
    "yaxshi qaytish" holati 20 balldan 0 olardi (28-bo'lim).
    """
    omil = score_trend(
        SoxtaHolat(), IndicatorConfig(), 20.0, 1.0, structure=pasayish()
    )
    assert omil.earned > 0.0


def test_bos_tasdiqli_struktura_koproq_beradi() -> None:
    config = IndicatorConfig()
    tasdiqsiz = score_trend(
        SoxtaHolat(), config, 20.0, 0.5, structure=kotarilish(bos=False)
    )
    tasdiqli = score_trend(
        SoxtaHolat(), config, 20.0, 0.5, structure=kotarilish(bos=True)
    )

    assert tasdiqli.earned > tasdiqsiz.earned


def test_struktura_hisoblanmasa_xato_bermaydi() -> None:
    omil = score_trend(SoxtaHolat(), IndicatorConfig(), 20.0, 0.5)
    assert omil.earned >= 0.0
    assert "hisoblanmadi" in omil.explanation


def test_trend_omili_bonus_deb_belgilanmaydi() -> None:
    omil = score_trend(
        SoxtaHolat(), IndicatorConfig(), 20.0, 0.5, structure=kotarilish()
    )
    assert omil.bonus is False
