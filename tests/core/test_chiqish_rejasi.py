"""2-qism: N ta TP ga moslashuvchi chiqish rejasi.

3-prompt talab qiladi: N = 2, 3, 5 — HAMMASI bir xil formula
bilan ishlashi kerak. Shuning uchun testlar parametrlangan:
agar kodda "agar 2 ta bo'lsa..." degan yashirin shart paydo
bo'lsa, N = 5 da darrov yiqiladi.
"""

from __future__ import annotations

import pytest

from core.portfolio.exit_manager import (
    chiqish_rejasi_qur,
    holat_boshla,
    natija_pct,
    stop_urildi,
    tp_bajarildi,
)


def tplar_yasa(n: int) -> list[float]:
    """100 dan boshlab teng qadamli N ta TP."""
    return [100.0 + 5.0 * k for k in range(1, n + 1)]


# --------------------------------------------------------------------- #
#  Reja qurilishi
# --------------------------------------------------------------------- #


@pytest.mark.parametrize("n", [1, 2, 3, 5, 8])
def test_ulushlar_teng_va_yigindisi_100(n: int) -> None:
    reja = chiqish_rejasi_qur(100.0, 95.0, tplar_yasa(n))

    assert reja.tp_soni == n
    assert sum(b.ulush_pct for b in reja.bosqichlar) == pytest.approx(100.0)


@pytest.mark.parametrize("n", [2, 3, 5])
def test_stop_HAR_BOSQICHDA_oldingi_TP_ga_kochadi(n: int) -> None:
    """Asosiy qoida: TP[k] dan keyin Stop = TP[k-1]."""
    tplar = tplar_yasa(n)
    reja = chiqish_rejasi_qur(100.0, 95.0, tplar)

    # Birinchi bosqich — breakeven.
    assert reja.bosqichlar[0].yangi_stop == 100.0
    for k in range(2, n + 1):
        assert reja.bosqichlar[k - 1].yangi_stop == tplar[k - 2]


def test_uchta_TP_uchun_aniq_raqamlar() -> None:
    """Qo'lda hisoblab tekshirish — formulaga ishonib qolmaslik uchun."""
    reja = chiqish_rejasi_qur(100.0, 95.0, [110.0, 120.0, 130.0])

    assert [b.ulush_pct for b in reja.bosqichlar] == pytest.approx([100 / 3, 100 / 3, 100 / 3])
    assert [b.yangi_stop for b in reja.bosqichlar] == [100.0, 110.0, 120.0]


def test_config_ulushlari_qabul_qilinadi() -> None:
    reja = chiqish_rejasi_qur(100.0, 95.0, [110.0, 120.0], ulushlar=[70.0, 30.0])
    assert [b.ulush_pct for b in reja.bosqichlar] == [70.0, 30.0]


def test_oxirgi_bosqich_QOLDIQNI_yopadi() -> None:
    """Yaxlitlash qoldig'i abadiy ochiq qolmasin.

    N=3 da 33.33 x 3 = 99.99 — bir tiyin ochiq qolardi.
    """
    reja = chiqish_rejasi_qur(100.0, 95.0, [110.0, 120.0, 130.0], ulushlar=[33.33, 33.33, 33.33])
    assert sum(b.ulush_pct for b in reja.bosqichlar) == pytest.approx(100.0)
    assert reja.bosqichlar[-1].ulush_pct == pytest.approx(33.34)


def test_notogri_darajalar_rad_etiladi() -> None:
    with pytest.raises(ValueError):
        chiqish_rejasi_qur(100.0, 105.0, [110.0])  # Stop > Entry
    with pytest.raises(ValueError):
        chiqish_rejasi_qur(100.0, 95.0, [110.0, 105.0])  # TP2 < TP1
    with pytest.raises(ValueError):
        chiqish_rejasi_qur(100.0, 95.0, [])  # TP yo'q
    with pytest.raises(ValueError):
        chiqish_rejasi_qur(100.0, 95.0, [110.0], ulushlar=[50.0, 50.0])


# --------------------------------------------------------------------- #
#  Bosqichma-bosqich yurish
# --------------------------------------------------------------------- #


@pytest.mark.parametrize("n", [2, 3, 5])
def test_hamma_TP_bajarilsa_savdo_yopiladi(n: int) -> None:
    holat = holat_boshla(chiqish_rejasi_qur(100.0, 95.0, tplar_yasa(n)))

    for _ in range(n):
        holat = tp_bajarildi(holat)

    assert holat.yopilgan
    assert holat.bajarilgan == n
    assert holat.ochiq_ulush_pct == 0.0
    assert holat.yopilish_sababi == "oxirgi TP"


def test_TP1_dan_keyin_stop_breakevenga_kochadi() -> None:
    holat = holat_boshla(chiqish_rejasi_qur(100.0, 95.0, [110.0, 120.0]))
    assert holat.joriy_stop == 95.0
    assert not holat.xavfsizmi

    holat = tp_bajarildi(holat)

    assert holat.joriy_stop == 100.0
    assert holat.xavfsizmi
    assert holat.ochiq_ulush_pct == pytest.approx(50.0)


def test_TP2_dan_keyin_stop_TP1_da_foydani_KAFOLATLAYDI() -> None:
    holat = holat_boshla(chiqish_rejasi_qur(100.0, 95.0, [110.0, 120.0, 130.0]))
    holat = tp_bajarildi(holat)
    holat = tp_bajarildi(holat)

    assert holat.joriy_stop == 110.0  # TP1 narxi
    assert holat.joriy_stop > holat.reja.entry


def test_yopilgandan_keyin_TP_hech_narsa_qilmaydi() -> None:
    holat = holat_boshla(chiqish_rejasi_qur(100.0, 95.0, [110.0]))
    holat = tp_bajarildi(holat)
    keyin = tp_bajarildi(holat)
    assert keyin == holat


def test_stop_qolgan_ulushni_yopadi() -> None:
    holat = holat_boshla(chiqish_rejasi_qur(100.0, 95.0, [110.0, 120.0]))
    holat = tp_bajarildi(holat)
    holat = stop_urildi(holat)

    assert holat.yopilgan
    assert holat.ochiq_ulush_pct == 0.0
    assert "TP1" in holat.yopilish_sababi


# --------------------------------------------------------------------- #
#  Natija hisobi
# --------------------------------------------------------------------- #


def test_hamma_TP_olingan_savdoning_natijasi() -> None:
    """TP: 110 va 120, ulush 50/50 -> (10% + 20%) / 2 = 15%."""
    holat = holat_boshla(chiqish_rejasi_qur(100.0, 95.0, [110.0, 120.0]))
    holat = tp_bajarildi(holat)
    holat = tp_bajarildi(holat)

    assert natija_pct(holat, 120.0) == pytest.approx(15.0)


def test_TP1_dan_keyin_breakevenda_yopilgan_savdo() -> None:
    """Yarmi +10% da sotilgan, yarmi kirish narxida -> +5%."""
    holat = holat_boshla(chiqish_rejasi_qur(100.0, 95.0, [110.0, 120.0]))
    holat = tp_bajarildi(holat)
    holat = stop_urildi(holat)

    assert natija_pct(holat, 100.0) == pytest.approx(5.0)


def test_TPsiz_stop_toliq_zarar() -> None:
    holat = holat_boshla(chiqish_rejasi_qur(100.0, 95.0, [110.0, 120.0]))
    holat = stop_urildi(holat)

    assert natija_pct(holat, 95.0) == pytest.approx(-5.0)
