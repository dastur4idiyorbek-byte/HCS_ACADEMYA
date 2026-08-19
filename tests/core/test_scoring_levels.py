"""3.1 va 3.3-band: Stop/TP darajalarini S/R va ATR asosida qurish.

Bu ikki band tez-tez ziddiyatga kiradi: haqiqiy support 1% dan uzoqroqda
bo'lishi mumkin. Bunday holatda daraja MAJBURLAB qurilmaydi — signal
berilmaydi va sababi qaytariladi.
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
    max_stop_distance_pct=1.0,
    min_tp_distance_pct=3.0,
    max_tp_distance_pct=5.0,
    min_risk_reward=3.0,
)


def xarita(
    price: float = 100.0,
    atr: float = 0.5,
    support_low: float = 99.4,
    support_high: float = 99.8,
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
    assert darajalar.stop < 99.4, "Stop support zonasidan PASTDA bo'lishi kerak"
    assert darajalar.tp1 == 103.5, "TP1 — eng yaqin resistance zonasining pasti"
    assert darajalar.stop_distance_pct <= QOIDALAR.max_stop_distance_pct
    assert darajalar.risk_reward_tp2 >= QOIDALAR.min_risk_reward


def test_stop_zonaning_ichiga_qoyilmaydi() -> None:
    """Zonaga tegib qaytish ham Stop'ni ishga tushirmasligi kerak."""
    natija = build_levels(xarita(support_low=99.4, support_high=99.8), QOIDALAR)
    assert natija.levels.stop < 99.4


def test_tp_oraligi_hurmat_qilinadi() -> None:
    natija = build_levels(xarita(), QOIDALAR)
    darajalar = natija.levels

    for masofa in (darajalar.tp1_distance_pct, darajalar.tp2_distance_pct):
        assert QOIDALAR.min_tp_distance_pct <= masofa <= QOIDALAR.max_tp_distance_pct


# --------------------------------------------------------------------------- #
#  Ziddiyat holatlari — signal berilmaydi, sabab qaytariladi
# --------------------------------------------------------------------------- #


def test_support_juda_uzoq_bolsa_signal_yoq() -> None:
    """Support 1% dan uzoqda — Stop chegaradan chiqib ketardi."""
    natija = build_levels(xarita(support_low=97.0, support_high=97.5), QOIDALAR)

    assert not natija.ok
    assert "juda uzoq" in natija.reason
    assert "1.0%" in natija.reason


def test_mos_resistance_yoq_bolsa_olchangan_tp() -> None:
    """Toza ko'tarilish trendida ustda qarshilik BO'LMAYDI — trend degani shu.

    Bunday holatda TP1 o'lchangan masofa bo'yicha qo'yiladi va bu ochiq
    belgilanadi (`tp_from_structure=False`), aks holda tizim aynan trend
    filtri talab qiladigan sharoitda hech qachon signal bera olmasdi.
    """
    natija = build_levels(xarita(resistance_low=120.0, resistance_high=121.0), QOIDALAR)

    assert natija.ok
    assert not natija.tp_from_structure
    assert "o'lchangan" in natija.reason
    assert natija.levels.tp1_distance_pct == pytest.approx(QOIDALAR.min_tp_distance_pct)


def test_tuzilmaviy_tp_belgilanadi() -> None:
    """Haqiqiy resistance topilsa, bu ham ochiq belgilanadi."""
    natija = build_levels(xarita(), QOIDALAR)

    assert natija.ok
    assert natija.tp_from_structure
    assert natija.levels.tp1 == 103.5


def test_qatiy_rejimda_resistance_yoq_bolsa_signal_yoq() -> None:
    """`allow_measured_tp: false` — faqat tuzilmaviy TP qabul qilinadi."""
    qatiy = dataclasses.replace(QOIDALAR, allow_measured_tp=False)
    natija = build_levels(xarita(resistance_low=120.0, resistance_high=121.0), qatiy)

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
    """TP1 topiladi, lekin 1:5 R/R uchun TP2 chegaradan chiqib ketadi.

    Stop masofasi ~0.73%, 1:5 uchun TP2 ~3.63% da bo'lishi kerak, lekin
    chegara 3.5%. Daraja majburlab qurilmaydi.
    """
    qatiy = TradeRulesConfig(
        max_stop_distance_pct=1.0,
        min_tp_distance_pct=3.0,
        max_tp_distance_pct=3.5,
        min_risk_reward=5.0,
    )
    natija = build_levels(xarita(resistance_low=103.2, resistance_high=103.6), qatiy)

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
