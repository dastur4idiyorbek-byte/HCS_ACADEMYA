"""TP/STOP FOIZLARI MAJBURIY EMAS — bog'lovchi shart R/R 1:3.

Loyiha egasining qarori (2026-09-02): "TP STOP FOIZLARI MAJBURIY
EMAS   RISK 1/3".

NIMA UCHUN. Foizlar MASOFA haqida, nisbat haqida emas. Haqiqiy
support 5% dan uzoqroqda, haqiqiy resistance esa 3% dan yaqinroqda
bo'lishi butunlay normal — bozor bizning oraliqlarimizga qarab
harakat qilmaydi. Ularni majburiy qilish tuzilmani e'tiborsiz
qoldirish demakdir.

Nisbat esa har qanday masofada ma'noga ega: Stop kattalashsa
pozitsiya hajmi (xavf puli / Stop%) avtomatik kichrayadi, ya'ni
xavf oshmaydi (5.1-band).

DIQQAT — NIMA YO'QOLDI. `min_stop_distance_pct` himoya vazifasini
ham bajarardi: juda tor Stop bozor shovqinida bekorga ishlaydi. Bu
himoya endi `stop_atr_mult` ga qoladi — Stop ATR ning ko'paytmasi
bilan qo'yiladi, ya'ni shovqin O'Z BIRLIGIDA o'lchanadi. Bu qat'iy
foizdan to'g'riroq, lekin O'LCHANMAGAN (`GIPOTEZA_DAFTARI.md`).
"""

from __future__ import annotations

import dataclasses

import pytest

from core.analysis.scoring import build_levels
from core.analysis.support_resistance import ZoneMap
from core.config import load_config
from core.domain.enums import ZoneKind
from core.domain.models import SRZone
from core.risk_engine import RiskEngine


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


def zona(kind: ZoneKind, low: float, high: float) -> SRZone:
    return SRZone(kind=kind, low=low, high=high, touches=3)


def test_standart_holatda_oraliqlar_ochiq(config) -> None:  # noqa: ANN001
    assert not config.trade_rules.enforce_distance_bands


def test_juda_yaqin_resistance_endi_TP_bola_oladi(config) -> None:  # noqa: ANN001
    """Qarshilik 3% dan yaqin bo'lsa ham u HAQIQIY nishon.

    Ilgari `min_tp_distance_pct` uni rad etardi va TP o'lchangan
    masofa bo'yicha, ya'ni bozorda hech narsa yo'q joyga qo'yilardi.
    """
    xarita = ZoneMap(
        price=100.0,
        atr=1.0,
        zones=[
            zona(ZoneKind.SUPPORT, 95.0, 96.0),
            zona(ZoneKind.RESISTANCE, 101.5, 102.0),  # atigi +1.5%
            zona(ZoneKind.RESISTANCE, 130.0, 131.0),
        ],
    )

    natija = build_levels(xarita, config.trade_rules)

    assert natija.ok, natija.reason
    assert natija.levels.tp1 == 101.5
    assert natija.tp_from_structure


def test_keng_stop_endi_toslamaydi(config) -> None:  # noqa: ANN001
    """Support uzoqda bo'lsa Stop ham uzoq — bu rad etish sababi emas."""
    xarita = ZoneMap(
        price=100.0,
        atr=1.0,
        zones=[
            zona(ZoneKind.SUPPORT, 88.0, 89.0),   # Stop ~11%
            zona(ZoneKind.RESISTANCE, 145.0, 146.0),
        ],
    )

    natija = build_levels(xarita, config.trade_rules)

    assert natija.ok, natija.reason
    assert natija.levels.stop_distance_pct > config.trade_rules.max_stop_distance_pct


def test_NISBAT_hali_ham_bogliq_shart(config) -> None:  # noqa: ANN001
    """Oraliqlar ochilgani nisbatni ham ochib yubormasin.

    Bu eng muhim tekshiruv: bayroq "hamma narsa mumkin" degani
    emas, "boshqa qoida qoladi" degani.
    """
    xarita = ZoneMap(
        price=100.0,
        atr=1.0,
        zones=[
            zona(ZoneKind.SUPPORT, 85.0, 86.0),   # Stop ~14%
            zona(ZoneKind.RESISTANCE, 101.0, 102.0),
        ],
    )
    # Yakuniy nishon 1:3 uchun ~142 bo'lishi kerak; formulaviy yo'l
    # uni o'zi quradi, ya'ni nisbat ta'minlanadi.
    natija = build_levels(xarita, config.trade_rules)

    assert natija.ok, natija.reason
    assert natija.levels.risk_reward >= config.trade_rules.min_risk_reward


def test_risk_engine_ham_SHU_bayroqqa_qaraydi(config) -> None:  # noqa: ANN001
    """Daraja qurilib, keyin tekshiruvda o'lmasin.

    67-bo'limdagi xatoning aynan o'zi: `build_levels` bir qoida
    bo'yicha quradi, Risk Engine boshqasi bo'yicha rad etadi va
    signal jimgina yo'qoladi.
    """
    import inspect

    from core.risk_engine import engine as motor

    manba = inspect.getsource(motor)

    assert "enforce_bands=config.trade_rules.enforce_distance_bands" in manba


def test_oraliqlarni_qayta_yoqish_mumkin(config) -> None:  # noqa: ANN001
    """Imkoniyat YO'QOLMADI — u bayroq ostiga ko'chdi."""
    bandli = dataclasses.replace(
        config.trade_rules, enforce_distance_bands=True
    )
    xarita = ZoneMap(
        price=100.0,
        atr=1.0,
        zones=[
            zona(ZoneKind.SUPPORT, 88.0, 89.0),
            zona(ZoneKind.RESISTANCE, 145.0, 146.0),
        ],
    )

    assert not build_levels(xarita, bandli).ok
    assert build_levels(xarita, config.trade_rules).ok


def test_engine_quriladi(config) -> None:  # noqa: ANN001
    """Bayroq Risk Engine'ni buzmasin — u har siklda quriladi."""
    assert RiskEngine(config) is not None
