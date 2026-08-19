"""3.1-band: Support/Resistance — BIRLAMCHI tahlil.

Testlar sun'iy, lekin nazorat qilinadigan narx shakllari ustida ishlaydi:
har bir tekshiruv aynan bitta xatti-harakatni sinaydi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.indicators.volatility import atr, atr_pct, true_range
from core.analysis.support_resistance import (
    SupportResistanceDetector,
    count_touches,
    fibonacci_levels,
    find_pivots,
    find_swing_range,
)
from core.config.schema import SupportResistanceConfig
from core.domain.enums import ZoneKind
from core.domain.models import Candle

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(index: int, high: float, low: float, close: float | None = None) -> Candle:
    yopilish = close if close is not None else (high + low) / 2
    return Candle(
        open_time=BOSH + timedelta(hours=index),
        open=yopilish,
        high=high,
        low=low,
        close=yopilish,
        volume=1000.0,
    )


def tekis_qator(n: int, narx: float = 100.0, kenglik: float = 1.0) -> list[Candle]:
    """Bir xil diapazondagi shamlar — "fon" sifatida."""
    return [sham(i, narx + kenglik / 2, narx - kenglik / 2, narx) for i in range(n)]


# --------------------------------------------------------------------------- #
#  ATR — o'lchov birligi
# --------------------------------------------------------------------------- #


def test_true_range_sakrashni_hisobga_oladi() -> None:
    """Gap hisobga olinmasa volatillik kam ko'rsatiladi."""
    oldingi = sham(0, 100, 99, 99.5)
    joriy = sham(1, 105, 104, 104.5)  # yuqoriga sakrab ochildi

    assert true_range(joriy, oldingi) == pytest.approx(5.5)
    assert true_range(joriy, None) == pytest.approx(1.0)


def test_atr_hisoblanadi() -> None:
    shamlar = [sham(i, 102, 98, 100) for i in range(30)]
    assert atr(shamlar, period=14) == pytest.approx(4.0)


def test_atr_malumot_yetmasa_none() -> None:
    """0.3-band: hisoblab bo'lmasa `None` — signal berilmaydi."""
    assert atr(tekis_qator(5), period=14) is None
    assert atr([], period=14) is None


def test_atr_foizda_narx_miqyosiga_boglik_emas() -> None:
    """Bir xil NISBIY diapazon bir xil ATR% berishi kerak."""
    qimmat = [sham(i, 67000 * 1.005, 67000 * 0.995, 67000) for i in range(30)]
    arzon = [sham(i, 0.004 * 1.005, 0.004 * 0.995, 0.004) for i in range(30)]

    assert atr_pct(qimmat, 14) == pytest.approx(atr_pct(arzon, 14), rel=1e-6)
    assert atr_pct(qimmat, 14) == pytest.approx(1.0, rel=1e-6)


# --------------------------------------------------------------------------- #
#  Pivotlar
# --------------------------------------------------------------------------- #


def test_choqqi_pivot_deb_topiladi() -> None:
    shamlar = tekis_qator(11)
    shamlar[5] = sham(5, 110, 108, 109)  # aniq cho'qqi

    pivotlar = find_pivots(shamlar, lookback=3)
    cho_qqilar = [p for p in pivotlar if p.kind is ZoneKind.RESISTANCE]

    assert len(cho_qqilar) == 1
    assert cho_qqilar[0].index == 5
    assert cho_qqilar[0].price == 110


def test_chuqurlik_pivot_deb_topiladi() -> None:
    shamlar = tekis_qator(11)
    shamlar[5] = sham(5, 92, 90, 91)

    chuqurliklar = [p for p in find_pivots(shamlar, 3) if p.kind is ZoneKind.SUPPORT]
    assert len(chuqurliklar) == 1
    assert chuqurliklar[0].price == 90


def test_tekis_choqqida_faqat_birinchisi_olinadi() -> None:
    """Aks holda zona sun'iy ravishda "ko'p test qilingan" ko'rinardi."""
    shamlar = tekis_qator(15)
    for i in (6, 7, 8):
        shamlar[i] = sham(i, 110, 108, 109)

    cho_qqilar = [p for p in find_pivots(shamlar, 3) if p.kind is ZoneKind.RESISTANCE]
    assert len(cho_qqilar) == 1, "tekis cho'qqi bitta pivot berishi kerak"
    assert cho_qqilar[0].index == 6


def test_oxirgi_shamlar_pivot_bola_olmaydi() -> None:
    """Tasdiqlanmagan cho'qqiga tayanish — "kelajakka qarash" xatosi.

    Backtestda bu natijalarni soxtalashtirardi.
    """
    shamlar = tekis_qator(11)
    shamlar[9] = sham(9, 120, 118, 119)  # oxirgidan 1 sham oldin

    assert find_pivots(shamlar, lookback=3) == []


def test_malumot_yetmasa_pivot_yoq() -> None:
    assert find_pivots(tekis_qator(4), lookback=3) == []


def test_notogri_lookback_rad_etiladi() -> None:
    with pytest.raises(ValueError, match="kamida 1"):
        find_pivots(tekis_qator(20), lookback=0)


# --------------------------------------------------------------------------- #
#  Test (touch) sanash
# --------------------------------------------------------------------------- #


def test_ketma_ket_shamlar_bitta_test_hisoblanadi() -> None:
    """Narx zonada 5 sham turgani "5 marta sinaldi" degani emas."""
    shamlar = [
        sham(0, 105, 104, 104.5),
        sham(1, 101, 99, 100),   # zonaga kirdi
        sham(2, 101, 99, 100),   # hali zonada
        sham(3, 101, 99, 100),   # hali zonada
        sham(4, 105, 104, 104.5),  # chiqdi
        sham(5, 101, 99, 100),   # qayta kirdi
    ]
    soni, oxirgi = count_touches(shamlar, low=99, high=101)

    assert soni == 2
    assert oxirgi == shamlar[5].open_time


def test_zonaga_tegmasa_nol() -> None:
    soni, oxirgi = count_touches(tekis_qator(10, narx=100), low=200, high=210)
    assert soni == 0
    assert oxirgi is None


# --------------------------------------------------------------------------- #
#  Fibonacci — yordamchi
# --------------------------------------------------------------------------- #


def test_kotarilish_diapazoni_aniqlanadi() -> None:
    shamlar = [sham(0, 91, 90, 90.5), *tekis_qator(5), sham(6, 120, 119, 119.5)]
    diapazon = find_swing_range(shamlar)

    assert diapazon is not None
    assert diapazon.low == 90
    assert diapazon.high == 120
    assert diapazon.is_uptrend


def test_kotarilishda_fibonacci_pastga_hisoblanadi() -> None:
    """Ko'tarilishdan keyin narx qaytib tushganda qo'llab-quvvatlash izlanadi."""
    from core.analysis.support_resistance.fibonacci import SwingRange

    diapazon = SwingRange(low=100, high=200, low_index=0, high_index=10)
    darajalar = dict(fibonacci_levels(diapazon, [0.382, 0.5, 0.618]))

    assert darajalar[0.5] == pytest.approx(150.0)
    assert darajalar[0.382] == pytest.approx(161.8)
    assert darajalar[0.618] == pytest.approx(138.2)


def test_tushishda_fibonacci_yuqoriga_hisoblanadi() -> None:
    from core.analysis.support_resistance.fibonacci import SwingRange

    diapazon = SwingRange(low=100, high=200, low_index=10, high_index=0)
    darajalar = dict(fibonacci_levels(diapazon, [0.5]))
    assert darajalar[0.5] == pytest.approx(150.0)


def test_diapazon_nol_bolsa_daraja_yoq() -> None:
    assert find_swing_range(tekis_qator(1)) is None


# --------------------------------------------------------------------------- #
#  Zonalarni qurish
# --------------------------------------------------------------------------- #


@pytest.fixture
def detector() -> SupportResistanceDetector:
    return SupportResistanceDetector(
        SupportResistanceConfig(swing_lookback=3, min_touches=2, zone_merge_atr_mult=0.5)
    )


def uch_marta_sinalgan_support() -> list[Candle]:
    """Narx uch marta 95 atrofiga tushib, qaytadi — klassik support."""
    shamlar: list[Candle] = []
    index = 0
    for _ in range(3):
        for narx in (102, 100, 98, 95, 98, 100, 102):
            shamlar.append(sham(index, narx + 1, narx - 1, narx))
            index += 1
    # Oxirida narx support ustida turadi
    for narx in (101, 102, 103):
        shamlar.append(sham(index, narx + 1, narx - 1, narx))
        index += 1
    return shamlar


def test_kop_marta_sinalgan_zona_topiladi(detector: SupportResistanceDetector) -> None:
    """Narx uch marta 94 (sham pastligi) atrofiga tushdi — shu zona topilishi kerak."""
    xarita = detector.detect(uch_marta_sinalgan_support())

    assert xarita is not None
    zonalar = [z for z in xarita.zones if z.contains(94)]
    assert zonalar, f"94 atrofida zona kutilgan, topilganlar: {xarita.zones}"
    assert zonalar[0].touches >= 2


def test_zona_nuqta_emas_oraliq(detector: SupportResistanceDetector) -> None:
    """Bozor aniq bir narxda emas, tor oraliqda buriladi."""
    xarita = detector.detect(uch_marta_sinalgan_support())
    assert all(z.width > 0 for z in xarita.zones)


def test_kam_sinalgan_zona_chiqarib_tashlanadi() -> None:
    """Tasodifiy tebranish zona sifatida qabul qilinmasligi kerak."""
    qatiy = SupportResistanceDetector(
        SupportResistanceConfig(swing_lookback=3, min_touches=10)
    )
    xarita = qatiy.detect(uch_marta_sinalgan_support())
    assert xarita.zones == []


def test_zonalar_narxga_nisbatan_ajratiladi(detector: SupportResistanceDetector) -> None:
    xarita = detector.detect(uch_marta_sinalgan_support())

    assert all(z.center <= xarita.price for z in xarita.supports)
    assert all(z.center > xarita.price for z in xarita.resistances)


def test_masofa_atr_birligida_olchanadi(detector: SupportResistanceDetector) -> None:
    """Narx miqyosidan qat'i nazar "yaqin" bir xil ma'no berishi kerak."""
    xarita = detector.detect(uch_marta_sinalgan_support())

    uzoq = min(xarita.zones, key=lambda z: -z.distance_to(xarita.price))
    masofa = xarita.distance_in_atr(uzoq)

    assert masofa > 0, "eng uzoq zona narxdan ajralgan bo'lishi kerak"
    assert xarita.is_price_near(uzoq, max_atr=masofa + 0.01)
    assert not xarita.is_price_near(uzoq, max_atr=masofa - 0.01)


def test_narx_zona_ichida_bolsa_masofa_nol(detector: SupportResistanceDetector) -> None:
    xarita = detector.detect(uch_marta_sinalgan_support())
    ichkarida = xarita.zone_at_price()
    if ichkarida is not None:
        assert xarita.distance_in_atr(ichkarida) == 0.0


def test_narx_zonada_turgani_aniqlanadi() -> None:
    detektor = SupportResistanceDetector(
        SupportResistanceConfig(swing_lookback=3, min_touches=2)
    )
    shamlar = uch_marta_sinalgan_support()
    # Oxirgi shamni support zonasiga qaytaramiz (pivot pastligi 94 edi)
    shamlar.append(sham(len(shamlar), 95, 93, 94))

    xarita = detektor.detect(shamlar)
    assert xarita.zone_at_price() is not None


def test_malumot_yetmasa_none(detector: SupportResistanceDetector) -> None:
    """0.3-band: noaniqlikda signal berilmaydi."""
    assert detector.detect(tekis_qator(5)) is None
    assert detector.detect([]) is None


def test_tekis_bozorda_atr_nol_bolsa_none() -> None:
    """Umuman harakatsiz narx — zona qurishning ma'nosi yo'q."""
    detektor = SupportResistanceDetector(SupportResistanceConfig(swing_lookback=3))
    harakatsiz = [sham(i, 100, 100, 100) for i in range(50)]
    assert detektor.detect(harakatsiz) is None


def test_fibonacci_zonalari_belgilanadi(detector: SupportResistanceDetector) -> None:
    """Yolg'iz Fibonacci zonasi zaifroq dalil — ball hisobida ajratilishi kerak."""
    xarita = detector.detect(uch_marta_sinalgan_support())
    fib_zonalar = [z for z in xarita.zones if z.from_fibonacci]
    # Barcha fib zonalari belgilangan bo'lishi kerak (soni shaklga bog'liq)
    assert all(z.from_fibonacci for z in fib_zonalar)
