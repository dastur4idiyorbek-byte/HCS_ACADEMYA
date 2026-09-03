"""BLOK 4 — Tasdiqlash: sweep, pastki TF, RSI, fundamental qayta tekshiruv."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.confirmation import (
    divergensiya,
    fundamental_hamon_mos,
    pastki_tf_tasdigi,
    rsi,
    sweep_bormi,
)
from core.analysis.confirmation.rsi_divergence import past_zonadan_qaytish
from core.analysis.structure.swing_detector import Swing, SwingTuri, swinglar
from core.analysis.turlar import blok, ha, malumot_yoq, yoq
from core.analysis.zone_quality.fibonacci import Zona
from core.domain.models import Candle

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(i: int, o: float, h: float, low: float, c: float) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(hours=i), open=o, high=h, low=low, close=c, volume=1000.0
    )


# --------------------------------------------------------------------------- #
#  4.1 Liquidity Sweep
# --------------------------------------------------------------------------- #


def test_sweep_yalash_va_qaytish() -> None:
    """Swing past 95 yalandi (low 94) va o'sha shamda qaytib yopildi."""
    shamlar = [
        sham(0, 100.0, 101.0, 100.0, 100.5),
        sham(1, 100.5, 102.0, 99.0, 101.0),
        sham(2, 101.0, 103.0, 95.0, 96.0),    # SWING PAST — 5 shamda eng past
        sham(3, 96.0, 104.0, 98.0, 103.0),
        sham(4, 103.0, 105.0, 99.0, 104.0),
        sham(5, 104.0, 106.0, 94.0, 105.0),   # 95 ni yaladi VA qaytdi
    ]
    nuqtalar = swinglar(shamlar)
    assert any(s.turi is SwingTuri.PAST and s.narx == 95.0 for s in nuqtalar)
    assert sweep_bormi(shamlar, nuqtalar)


def test_yalab_qaytmasa_sweep_emas() -> None:
    """Faqat "o'tdi" — bu oddiy tushish, zona buzilgan."""
    nuqtalar = [Swing(SwingTuri.PAST, 95.0, BOSH, 2)]
    shamlar = [sham(i, 100, 102, 98, 100) for i in range(3)]
    shamlar += [sham(3, 96, 97, 90, 91), sham(4, 91, 92, 88, 89)]
    assert not sweep_bormi(shamlar, nuqtalar)


def test_swing_yoq_bolsa_sweep_yoq() -> None:
    assert not sweep_bormi([sham(0, 100, 102, 98, 100)], [])


# --------------------------------------------------------------------------- #
#  4.3 RSI
# --------------------------------------------------------------------------- #


def test_rsi_royxati_uzunligi() -> None:
    """Birinchi `davr` ta qiymat yo'q — bu xato emas, ma'lumot yetishmasligi."""
    shamlar = [sham(i, 100, 101, 99, 100 + i * 0.5) for i in range(30)]
    qiymatlar = rsi(shamlar, davr=14)
    assert len(qiymatlar) == len(shamlar) - 14


def test_rsi_tarix_yetmasa_bosh() -> None:
    assert rsi([sham(i, 100, 101, 99, 100) for i in range(5)], davr=14) == []


def test_faqat_osishda_rsi_100() -> None:
    shamlar = [sham(i, 100, 101, 99, 100 + i) for i in range(30)]
    assert rsi(shamlar)[-1] == pytest.approx(100.0)


def test_rsi_oraliqda_qoladi() -> None:
    import random

    random.seed(3)
    narx = 100.0
    shamlar = []
    for i in range(60):
        narx *= 1 + random.uniform(-0.02, 0.02)
        shamlar.append(sham(i, narx, narx * 1.01, narx * 0.99, narx))
    assert all(0 <= q <= 100 for q in rsi(shamlar))


def test_past_zonadan_qaytish_chiqishni_talab_qiladi() -> None:
    """"Hozir past zonada" YETARLI EMAS — tushayotgan pichoqni ushlamaymiz."""
    assert past_zonadan_qaytish([25.0, 28.0, 40.0], chegara=35.0)
    assert not past_zonadan_qaytish([25.0, 28.0, 30.0], chegara=35.0)


def test_divergensiya_narx_pasaydi_rsi_pasaymadi() -> None:
    qiymatlar = [30.0] * 10 + [40.0] * 10
    shamlar = [sham(i, 100, 101, 100 - i, 100) for i in range(34)]
    assert divergensiya(shamlar, qiymatlar, oyna=20)


def test_divergensiya_yoq_bolsa_false() -> None:
    qiymatlar = [40.0] * 10 + [30.0] * 10
    shamlar = [sham(i, 100, 101, 100 - i, 100) for i in range(34)]
    assert not divergensiya(shamlar, qiymatlar, oyna=20)


# --------------------------------------------------------------------------- #
#  4.2 Pastki TF
# --------------------------------------------------------------------------- #


def test_zona_yoq_bolsa_tasdiq_yoq() -> None:
    assert not pastki_tf_tasdigi([sham(0, 100, 101, 99, 100)], None)


def test_zonadan_tashqaridagi_shamlar_hisoblanmaydi() -> None:
    """Tasdiq zonadan uzoqda topilsa, kirish narxi boshqa joyda bo'lardi."""
    uzoq = [sham(i, 500, 505, 495, 500) for i in range(20)]
    assert not pastki_tf_tasdigi(uzoq, Zona(100, 110, "fib"))


def test_kam_sham_bilan_tasdiq_yoq() -> None:
    """5 shamli fraktal uchun minimum — ansiz swing umuman topilmaydi."""
    oz = [sham(i, 105, 106, 104, 105) for i in range(3)]
    assert not pastki_tf_tasdigi(oz, Zona(100, 110, "fib"))


# --------------------------------------------------------------------------- #
#  4.4 Fundamental qayta tekshiruv
# --------------------------------------------------------------------------- #


def test_qattiq_tosiq_paydo_bolsa_mos_emas() -> None:
    eski = blok("F", [ha("a"), ha("b")])
    yangi = blok("F", [ha("a"), ha("b")], qattiq_tosiq="unlock")
    assert fundamental_hamon_mos(eski, yangi) is False


def test_kuch_bitta_pasayishi_normal() -> None:
    """Bitta tekshiruvning tebranishi — normal, holat o'zgargani emas."""
    eski = blok("F", [ha("a"), ha("b"), ha("c"), yoq("d")])
    yangi = blok("F", [ha("a"), ha("b"), yoq("c"), yoq("d")])
    assert fundamental_hamon_mos(eski, yangi) is True


def test_kuch_ikkita_pasaysa_buzilgan() -> None:
    eski = blok("F", [ha("a"), ha("b"), ha("c"), yoq("d")])
    yangi = blok("F", [ha("a"), yoq("b"), yoq("c"), yoq("d")])
    assert fundamental_hamon_mos(eski, yangi) is False


def test_olchanmagan_blok_solishtirilmaydi() -> None:
    olchanmagan = blok("F", [malumot_yoq("a")])
    assert fundamental_hamon_mos(olchanmagan, olchanmagan) is None


def test_blok_yoq_bolsa_none() -> None:
    assert fundamental_hamon_mos(None, None) is None
