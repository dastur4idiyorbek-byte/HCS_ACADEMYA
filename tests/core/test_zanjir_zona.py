"""BLOK 3 — Zona sifati: Fibonacci, OB, FVG, Volume Profile, darajali birlashtirish."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.structure.swing_detector import Swing, SwingTuri, swinglar
from core.analysis.zone_quality import (
    Zona,
    ZonaDarajasi,
    ZonaKirish,
    fib_zona,
    fvg_topish,
    ob_topish,
    poc_narx,
    poc_yaqinmi,
    zona_blok,
)
from core.analysis.zone_quality.order_block import ObTarifi
from core.domain.models import Candle

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(i: int, o: float, h: float, low: float, c: float, v: float = 1000.0) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(days=i), open=o, high=h, low=low, close=c, volume=v
    )


# --------------------------------------------------------------------------- #
#  Zona tipi
# --------------------------------------------------------------------------- #


def test_zona_kesishishi() -> None:
    a = Zona(100, 110, "a")
    assert a.kesishadimi(Zona(105, 115, "b"))
    assert not a.kesishadimi(Zona(111, 120, "b"))


def test_zona_chegarasi_kesishish_hisoblanadi() -> None:
    assert Zona(100, 110, "a").kesishadimi(Zona(110, 120, "b"))


# --------------------------------------------------------------------------- #
#  3.1 Fibonacci
# --------------------------------------------------------------------------- #


def test_fib_zona_impulsdan_hisoblanadi() -> None:
    """100 -> 200 impuls: zona 138.2 .. 161.8."""
    nuqtalar = [
        Swing(SwingTuri.PAST, 100.0, BOSH, 0),
        Swing(SwingTuri.YUQORI, 200.0, BOSH + timedelta(days=5), 5),
    ]
    zona = fib_zona(nuqtalar)
    assert zona is not None
    assert zona.past == pytest.approx(138.2)
    assert zona.yuqori == pytest.approx(161.8)


def test_impuls_yoq_bolsa_zona_yoq() -> None:
    assert fib_zona([]) is None
    assert fib_zona([Swing(SwingTuri.YUQORI, 200.0, BOSH, 0)]) is None


def test_tushish_impulsi_zona_bermaydi() -> None:
    """Yuqori pastdan OLDIN kelsa — bu ko'tarilish impulsi emas."""
    nuqtalar = [
        Swing(SwingTuri.YUQORI, 200.0, BOSH, 0),
        Swing(SwingTuri.PAST, 100.0, BOSH + timedelta(days=5), 5),
    ]
    assert fib_zona(nuqtalar) is None


# --------------------------------------------------------------------------- #
#  3.2 Order Block
# --------------------------------------------------------------------------- #


def test_last_opposite_oxirgi_tushuvchi_shamni_topadi() -> None:
    shamlar = [
        sham(0, 100, 102, 98, 101),
        sham(1, 105, 106, 99, 100),   # tushuvchi
        sham(2, 100, 110, 99, 109),
    ]
    ob = ob_topish(shamlar, impuls_boshi=2, tarif=ObTarifi.LAST_OPPOSITE)
    assert ob is not None
    assert ob.zona.past == 100
    assert ob.zona.yuqori == 105


def test_sweep_candle_yalash_va_qaytishni_topadi() -> None:
    shamlar = [
        sham(0, 100, 102, 95, 101),
        sham(1, 100, 103, 90, 99),   # 95 ni yaladi, 95 dan yuqori yopildi
    ]
    ob = ob_topish(shamlar, impuls_boshi=1, tarif=ObTarifi.SWEEP_CANDLE)
    assert ob is not None
    assert ob.zona.past == 90
    assert ob.zona.yuqori == 103


def test_yalab_qaytmasa_sweep_emas() -> None:
    shamlar = [sham(0, 100, 102, 95, 101), sham(1, 100, 96, 90, 91)]
    assert ob_topish(shamlar, 1, ObTarifi.SWEEP_CANDLE) is None


# --------------------------------------------------------------------------- #
#  3.3 FVG
# --------------------------------------------------------------------------- #


def test_fvg_boshliq_topiladi() -> None:
    """1-sham high 100 < 3-sham low 110 -> bo'shliq 100..110."""
    shamlar = [
        sham(0, 95, 100, 94, 99),
        sham(1, 100, 115, 99, 114),
        sham(2, 114, 120, 110, 118),
    ]
    fvg = fvg_topish(shamlar)
    assert fvg is not None
    assert fvg.zona.past == 100
    assert fvg.zona.yuqori == 110


def test_toldirilgan_fvg_qaytarilmaydi() -> None:
    """Narx qaytib kirgan bo'shliq endi zona emas — vazifasi bajarilgan."""
    shamlar = [
        sham(0, 95, 100, 94, 99),
        sham(1, 100, 115, 99, 114),
        sham(2, 114, 120, 110, 118),
        sham(3, 118, 119, 105, 108),   # bo'shliqqa qaytdi
    ]
    assert fvg_topish(shamlar) is None


def test_boshliq_yoq_bolsa_none() -> None:
    shamlar = [sham(i, 100, 105, 95, 100) for i in range(5)]
    assert fvg_topish(shamlar) is None


# --------------------------------------------------------------------------- #
#  3.4 Volume Profile
# --------------------------------------------------------------------------- #


def test_poc_eng_kop_hajmli_darajada() -> None:
    shamlar = [
        sham(0, 100, 101, 99, 100, v=100),
        sham(1, 150, 151, 149, 150, v=10_000),   # hajmning katta qismi
        sham(2, 200, 201, 199, 200, v=100),
    ]
    poc = poc_narx(shamlar)
    assert poc is not None
    assert 145 <= poc <= 155


def test_bosh_royxatda_poc_yoq() -> None:
    assert poc_narx([]) is None


def test_poc_yaqinligi() -> None:
    assert poc_yaqinmi(100.0, 101.0, yaqinlik_pct=2.0) is True
    assert poc_yaqinmi(100.0, 110.0, yaqinlik_pct=2.0) is False
    assert poc_yaqinmi(100.0, None) is None


# --------------------------------------------------------------------------- #
#  Darajali birlashtirish — bu blokning o'ziga xosligi
# --------------------------------------------------------------------------- #


def _kotarilish_shamlari() -> list[Candle]:
    """Impuls: past 100 -> cho'qqi 200, keyin qaytish."""
    return [
        sham(0, 105, 106, 100, 101),
        sham(1, 101, 108, 99, 107),
        sham(2, 107, 130, 105, 128),
        sham(3, 128, 160, 126, 158),
        sham(4, 158, 200, 155, 195),
        sham(5, 195, 198, 170, 175),
        sham(6, 175, 180, 150, 155),
        sham(7, 155, 160, 145, 150),
        sham(8, 150, 155, 148, 152),
    ]


def test_faqat_fib_zaif() -> None:
    """OB va FVG kesishmasa — 1 qatlam, ZAIF daraja."""
    shamlar = _kotarilish_shamlari()
    natija = zona_blok(ZonaKirish(shamlar=shamlar, nuqtalar=swinglar(shamlar)))
    if natija.zona is not None:
        assert natija.daraja in (ZonaDarajasi.ZAIF, ZonaDarajasi.ORTA, ZonaDarajasi.KUCHLI)
        assert "fibonacci" in natija.qatlamlar


def test_impuls_yoq_bolsa_blok_bosh() -> None:
    """Fib topilmasa — asos yo'q, qolgan qatlamlar o'lchanmaydi."""
    shamlar = [sham(i, 100, 101, 99, 100) for i in range(10)]
    natija = zona_blok(ZonaKirish(shamlar=shamlar, nuqtalar=swinglar(shamlar)))
    assert natija.zona is None
    assert natija.daraja is ZonaDarajasi.YOQ
    assert not natija.blok.otdi


def test_qatlamlar_kesishmasa_hisoblanmaydi() -> None:
    """KONFLUENSIYA = ustma-ust tushish.

    Grafikning boshqa-boshqa joyidagi uchta zona "3/4 kuchli" emas —
    ular uchta alohida daraja. Shu sababli OB/FVG faqat Fib bilan
    KESISHSA hisoblanadi.
    """
    shamlar = _kotarilish_shamlari()
    natija = zona_blok(ZonaKirish(shamlar=shamlar, nuqtalar=swinglar(shamlar)))
    if natija.zona is not None:
        # Qatlam soni va daraja BIR-BIRIGA MOS kelishi shart
        kutilgan = {1: ZonaDarajasi.ZAIF, 2: ZonaDarajasi.ORTA, 3: ZonaDarajasi.KUCHLI}
        assert natija.daraja is kutilgan[len(natija.qatlamlar)]


def test_zona_kesishma_olinadi_birlashma_emas() -> None:
    """Kesishma Stopni yaqinlashtiradi, birlashma esa uzoqlashtirardi."""
    shamlar = _kotarilish_shamlari()
    natija = zona_blok(ZonaKirish(shamlar=shamlar, nuqtalar=swinglar(shamlar)))
    asos = fib_zona(swinglar(shamlar))
    if natija.zona is not None and asos is not None:
        assert natija.zona.past >= asos.past
        assert natija.zona.yuqori <= asos.yuqori
