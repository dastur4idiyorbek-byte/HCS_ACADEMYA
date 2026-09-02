"""TP2 formuladan emas, TUZILMADAN (`tp2_from_structure`).

MUAMMO (2026-09-02 backtesti, `docs/BACKTEST_NATIJA_2026-09-02.md`).
TP1 haqiqiy resistance zonasidan olinadi, TP2 esa FORMULADAN: stop
masofasi x `min_risk_reward`. Ya'ni TP2 bozorda nima borligiga
umuman qaramaydi.

O'lchangan oqibat: TP2 gacha savdolarning atigi 29.9% i yetadi,
stop esa to'liq ishlaydi. 1:1.5 nisbatda foydali bo'lish uchun 40%
kerak edi — ana shu farq butun tizimni zararga olib boradi.

Bu testlar YANGI YO'LNI tekshiradi, uni to'g'ri deb e'lon qilmaydi.
Qaysi yo'l yaxshiroq — buni faqat backtest aytadi.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.analysis.scoring.levels import build_levels
from core.analysis.support_resistance import ZoneMap
from core.config import load_config
from core.domain.enums import ZoneKind
from core.domain.models import SRZone


@pytest.fixture
def qoidalar():  # noqa: ANN201
    return load_config().trade_rules


def zona(kind: ZoneKind, low: float, high: float) -> SRZone:
    return SRZone(kind=kind, low=low, high=high, touches=2)


def xarita(price: float, zonalar: list[SRZone], atr: float = 1.0) -> ZoneMap:
    return ZoneMap(price=price, atr=atr, zones=zonalar)


def sinov_xaritasi() -> ZoneMap:
    """Narx 100, support 95-96, ikkita resistance: 104-105 va 112-113.

    Formulaviy TP2 (stop ~4.2%, nisbat 1.5) ~106.3 da bo'lardi —
    ya'ni HECH QANDAY zonada emas, ikki zona orasidagi bo'shliqda.
    Tuzilmaviy TP2 esa 112 — haqiqiy qarshilik.
    """
    return xarita(
        100.0,
        [
            zona(ZoneKind.SUPPORT, 95.0, 96.0),
            zona(ZoneKind.RESISTANCE, 104.0, 105.0),
            zona(ZoneKind.RESISTANCE, 112.0, 113.0),
        ],
    )


# --------------------------------------------------------------------------- #
#  Asosiy farq
# --------------------------------------------------------------------------- #


def test_tuzilmaviy_tp2_haqiqiy_zonaga_qoyiladi(qoidalar) -> None:  # noqa: ANN001
    """TP2 ikkinchi resistance zonasining PASTKI chekkasida."""
    tuzilmaviy = dataclasses.replace(qoidalar, tp2_from_structure=True)

    natija = build_levels(sinov_xaritasi(), tuzilmaviy)

    assert natija.ok, natija.reason
    assert natija.levels.tp1 == 104.0, "TP1 — eng yaqin resistance"
    assert natija.levels.tp2 == 112.0, "TP2 — keyingi resistance"


def test_formulaviy_tp2_zonaga_qaramaydi(qoidalar) -> None:  # noqa: ANN001
    """Eski yo'l: TP2 stopdan hisoblanadi, bozordan emas.

    Bu test eski xatti-harakatni QAYD ETADI — u xato deb
    belgilanmagan, faqat boshqacha. Farq ko'rinib tursin.
    """
    natija = build_levels(sinov_xaritasi(), qoidalar)

    assert natija.ok, natija.reason
    assert natija.levels.tp1 == 104.0
    assert natija.levels.tp2 != 112.0, "formula zonaga tushishi shart emas"


def test_zona_yoq_bolsa_signal_berilmaydi(qoidalar) -> None:  # noqa: ANN001
    """TP1 dan yuqorida qarshilik bo'lmasa — TP2 O'YLAB TOPILMAYDI.

    Eski yo'lda formula baribir raqam qaytarardi. Yangi yo'lning
    butun ma'nosi shunda: TP2 bozorda bor joyga qo'yiladi, yo'q
    bo'lsa — signal yo'q (0.2-band).
    """
    tuzilmaviy = dataclasses.replace(qoidalar, tp2_from_structure=True)
    bitta_zona = xarita(
        100.0,
        [
            zona(ZoneKind.SUPPORT, 95.0, 96.0),
            zona(ZoneKind.RESISTANCE, 104.0, 105.0),
        ],
    )

    natija = build_levels(bitta_zona, tuzilmaviy)

    assert not natija.ok
    assert natija.stage == "levels:tp2_no_structure"


def test_juda_uzoq_zona_olinmaydi(qoidalar) -> None:  # noqa: ANN001
    """`max_tp_distance_pct` dan narida bo'lgan zona TP2 bo'la olmaydi."""
    tuzilmaviy = dataclasses.replace(qoidalar, tp2_from_structure=True)
    uzoq = xarita(
        100.0,
        [
            zona(ZoneKind.SUPPORT, 95.0, 96.0),
            zona(ZoneKind.RESISTANCE, 104.0, 105.0),
            zona(ZoneKind.RESISTANCE, 500.0, 510.0),
        ],
    )

    natija = build_levels(uzoq, tuzilmaviy)

    assert not natija.ok
    assert natija.stage == "levels:tp2_no_structure"


def test_nisbati_juda_past_zona_otkazib_yuboriladi(qoidalar) -> None:  # noqa: ANN001
    """1:1 dan past nisbatli zona TP2 bo'lmaydi — keyingisi qidiriladi."""
    tuzilmaviy = dataclasses.replace(
        qoidalar, tp2_from_structure=True, tp2_structural_min_rr=1.5
    )

    natija = build_levels(sinov_xaritasi(), tuzilmaviy)

    assert natija.ok, natija.reason
    stop_pct = (natija.levels.entry - natija.levels.stop) / natija.levels.entry * 100
    tp2_pct = (natija.levels.tp2 - natija.levels.entry) / natija.levels.entry * 100
    assert tp2_pct / stop_pct >= 1.5


# --------------------------------------------------------------------------- #
#  Risk Engine bilan bir xil raqamga tayanadimi
# --------------------------------------------------------------------------- #


def test_risk_engine_tuzilmaviy_nisbatni_qollaydi() -> None:
    """Bayroq YOQILGANDA tekshiruv ham pasaygan nisbatga o'tishi kerak.

    Aks holda darajalar quriladi-yu, Risk Engine ularni darhol yo'q
    qilardi: bayroq e'lon qilingan, lekin ULANMAGAN bo'lib qolardi.
    Loyihada bu xato allaqachon ikki marta bo'lgan (BTC Dominance,
    Correction Entry R/R).
    """
    from core.domain.enums import SignalSource
    from core.risk_engine.engine import build_default_rules

    asos = load_config()
    tuzilmaviy = dataclasses.replace(
        asos, trade_rules=dataclasses.replace(asos.trade_rules, tp2_from_structure=True)
    )

    qoida = next(q for q in build_default_rules(tuzilmaviy) if q.name == "trade_rules")
    _min_tp, _max_tp, min_rr, _min_stop = qoida._bounds_for(SignalSource.CLASSIC_TA)

    assert min_rr == tuzilmaviy.trade_rules.tp2_structural_min_rr


def test_bayroq_ochiq_bolsa_eski_nisbat_qoladi() -> None:
    """Orqaga moslik: bayroqsiz hech narsa o'zgarmaydi."""
    from core.domain.enums import SignalSource
    from core.risk_engine.engine import build_default_rules

    config = load_config()
    assert not config.trade_rules.tp2_from_structure, "standart holat: o'chiq"

    qoida = next(q for q in build_default_rules(config) if q.name == "trade_rules")
    _min_tp, _max_tp, min_rr, _min_stop = qoida._bounds_for(SignalSource.CLASSIC_TA)

    assert min_rr == config.strategies.classic_ta.min_risk_reward
