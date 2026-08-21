"""3.1 va 3.3-band: Stop/TP darajalarini S/R va ATR asosida qurish.

3.3-band tuzatilgan: Stop endi 1%..5% oralig'ida ERKIN joylashadi —
qat'iy 1% chegara emas. Asosiy shart NISBAT: TP2/Stop kamida 1:3.

Daraja hech qachon MAJBURLAB qurilmaydi: support zonasi oraliqdan
tashqarida bo'lsa signal berilmaydi va sababi qaytariladi.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.analysis.scoring import build_levels
from core.analysis.support_resistance import ZoneMap
from core.config.schema import TradeRulesConfig
from core.domain.enums import ZoneKind
from core.domain.models import SRZone

QOIDALAR = TradeRulesConfig(
    min_stop_distance_pct=1.0,
    max_stop_distance_pct=5.0,
    min_tp_distance_pct=3.0,
    max_tp_distance_pct=20.0,
    min_risk_reward=3.0,
    tp1_min_risk_reward=1.5,
)


def xarita(
    price: float = 100.0,
    atr: float = 0.5,
    support_low: float = 98.7,
    support_high: float = 99.2,
    resistance_low: float = 103.5,
    resistance_high: float = 104.0,
) -> ZoneMap:
    return ZoneMap(
        zones=[
            SRZone(ZoneKind.SUPPORT, support_low, support_high, touches=4),
            SRZone(ZoneKind.RESISTANCE, resistance_low, resistance_high, touches=3),
        ],
        price=price,
        atr=atr,
    )


# --------------------------------------------------------------------------- #
#  Asosiy yo'l
# --------------------------------------------------------------------------- #


def test_darajalar_sr_asosida_quriladi() -> None:
    natija = build_levels(xarita(), QOIDALAR)

    assert natija.ok, natija.reason
    darajalar = natija.levels
    assert darajalar.entry == 100.0
    assert darajalar.stop < 98.7, "Stop support zonasidan PASTDA bo'lishi kerak"
    assert darajalar.tp1 == 103.5, "TP1 — eng yaqin resistance zonasining pasti"
    assert (
        QOIDALAR.min_stop_distance_pct
        <= darajalar.stop_distance_pct
        <= QOIDALAR.max_stop_distance_pct
    )
    assert darajalar.risk_reward_tp2 == pytest.approx(QOIDALAR.min_risk_reward, rel=1e-6)


def test_stop_zonaning_ichiga_qoyilmaydi() -> None:
    """Zonaga tegib qaytish ham Stop'ni ishga tushirmasligi kerak."""
    natija = build_levels(xarita(support_low=98.0, support_high=98.6), QOIDALAR)

    assert natija.ok, natija.reason
    assert natija.levels.stop < 98.0


def test_tp_oraligi_hurmat_qilinadi() -> None:
    natija = build_levels(xarita(), QOIDALAR)
    darajalar = natija.levels

    for masofa in (darajalar.tp1_distance_pct, darajalar.tp2_distance_pct):
        assert QOIDALAR.min_tp_distance_pct <= masofa <= QOIDALAR.max_tp_distance_pct


# --------------------------------------------------------------------------- #
#  Ziddiyat holatlari — signal berilmaydi, sabab qaytariladi
# --------------------------------------------------------------------------- #


def test_support_juda_uzoq_bolsa_signal_yoq() -> None:
    """Support 5% dan uzoqda — pozitsiya ma'nosiz kichrayardi."""
    natija = build_levels(xarita(support_low=94.0, support_high=94.5), QOIDALAR)

    assert not natija.ok
    assert "juda uzoq" in natija.reason


def test_support_juda_yaqin_bolsa_signal_yoq() -> None:
    """Support 1% dan yaqin — bozor shovqini Stop'ni yeb qo'yardi."""
    natija = build_levels(xarita(support_low=99.4, support_high=99.8), QOIDALAR)

    assert not natija.ok
    assert "juda yaqin" in natija.reason


def test_stop_oraliq_ichida_erkin_joylashadi() -> None:
    """3.3-band tuzatilgan: qat'iy 1% emas, 1..5% oralig'i.

    Avval faqat aynan 1% masofadagi support qabul qilinardi — bunday
    zona kam uchraydi va signal deyarli chiqmasdi.
    """
    for support_low, kutilgan_stop in ((98.7, 1.42), (98.0, 2.12), (97.0, 3.12)):
        natija = build_levels(
            xarita(support_low=support_low, support_high=support_low + 0.5), QOIDALAR
        )

        assert natija.ok, f"support {support_low}: {natija.reason}"
        assert natija.levels.stop_distance_pct == pytest.approx(kutilgan_stop, abs=0.01)
        assert natija.levels.risk_reward_tp2 >= QOIDALAR.min_risk_reward - 1e-9


def test_mos_resistance_yoq_bolsa_olchangan_tp() -> None:
    """Toza ko'tarilish trendida ustda qarshilik BO'LMAYDI — trend degani shu.

    Bunday holatda TP1 o'lchangan masofa bo'yicha qo'yiladi va bu ochiq
    belgilanadi (`tp_from_structure=False`), aks holda tizim aynan trend
    filtri talab qiladigan sharoitda hech qachon signal bera olmasdi.
    """
    natija = build_levels(xarita(resistance_low=150.0, resistance_high=151.0), QOIDALAR)

    assert natija.ok
    assert not natija.tp_from_structure
    assert "o'lchangan" in natija.reason
    # O'lchangan TP1 Stop bilan bog'lanadi: max(min_tp, stop x tp1_nisbati)
    kutilgan = max(
        QOIDALAR.min_tp_distance_pct,
        natija.levels.stop_distance_pct * QOIDALAR.tp1_min_risk_reward,
    )
    assert natija.levels.tp1_distance_pct == pytest.approx(kutilgan)


def test_tuzilmaviy_tp_belgilanadi() -> None:
    """Haqiqiy resistance topilsa, bu ham ochiq belgilanadi."""
    natija = build_levels(xarita(), QOIDALAR)

    assert natija.ok
    assert natija.tp_from_structure
    assert natija.levels.tp1 == 103.5


def test_qatiy_rejimda_resistance_yoq_bolsa_signal_yoq() -> None:
    """`allow_measured_tp: false` — faqat tuzilmaviy TP qabul qilinadi."""
    qatiy = dataclasses.replace(QOIDALAR, allow_measured_tp=False)
    natija = build_levels(xarita(resistance_low=150.0, resistance_high=151.0), qatiy)

    assert not natija.ok
    assert "resistance" in natija.reason.lower()


def test_juda_yaqin_resistance_ham_olchangan_tp_ga_otadi() -> None:
    natija = build_levels(xarita(resistance_low=101.0, resistance_high=101.5), QOIDALAR)

    assert natija.ok
    assert not natija.tp_from_structure


def test_support_umuman_yoq_bolsa_signal_yoq() -> None:
    faqat_resistance = ZoneMap(
        zones=[SRZone(ZoneKind.RESISTANCE, 103.5, 104.0, touches=3)], price=100.0, atr=0.5
    )
    natija = build_levels(faqat_resistance, QOIDALAR)

    assert not natija.ok
    assert "support" in natija.reason.lower()


def test_rr_talabi_bajarilmasa_signal_yoq() -> None:
    """NISBAT — asosiy shart. U bajarilmasa daraja majburlab qurilmaydi.

    Stop ~1.42%, 1:8 uchun TP2 ~11.4% da bo'lishi kerak, lekin chegara
    5%. Signal berilmaydi.
    """
    qatiy = dataclasses.replace(QOIDALAR, max_tp_distance_pct=5.0, min_risk_reward=8.0)
    natija = build_levels(xarita(), qatiy)

    assert not natija.ok
    assert "R/R" in natija.reason


def test_manfiy_narx_rad_etiladi() -> None:
    assert not build_levels(xarita(price=-1), QOIDALAR).ok


def test_sabab_har_doim_beriladi() -> None:
    """Admin nima uchun signal chiqmaganini ko'ra olishi kerak (3.7-band)."""
    for zona_xaritasi in (
        xarita(),
        xarita(support_low=97.0),
        xarita(resistance_low=101.0),
    ):
        assert build_levels(zona_xaritasi, QOIDALAR).reason
