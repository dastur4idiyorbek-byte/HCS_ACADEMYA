"""TP1 ga NISBAT poli — natija #7 dagi tashxisning yechimi.

MUAMMO. `tp1_min_risk_reward` (1.5) faqat "qarshilik topilmadi"
tarmog'ida ishlardi. Zona topilganda TP1 o'sha zonaga qo'yilardi
va hech qanday pol tekshirilmasdi.

Foiz oraliqlari majburiy bo'lganda buni `min_tp_distance_pct`
(3%) yashirib turardi — u TP1 uchun amalda pol vazifasini ham
bajarardi. Oraliqlar o'chirilgach (loyiha egasining qarori) TP1
eng yaqin qarshilikka tushdi:

    TP1 +0.5% da   -> yarmi sotiladi   -> +0.25%
    Stop breakeven -> qolgani nolda    ->  0.00%
    komissiya                          -> -0.30%
                                          -------
                                           -0.05%

Ya'ni "g'alaba" deb yozilgan savdo amalda nolga yaqin, Stop esa
keng qoladi: kichkina yutuqlar, katta zararlar. O'lchovda profit
factor 0.64 dan 0.30 ga tushdi (`BACKTEST_NATIJA_2026-09-02_7.md`).

YECHIM. Foizni qaytarish EMAS — TP1 ga NISBAT poli. Bu loyiha
egasining "TP STOP FOIZLARI MAJBURIY EMAS — RISK 1/3" qoidasiga
zid emas: pol foizda emas, Stop masofasiga NISBATAN o'lchanadi.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.analysis.scoring import build_levels
from core.analysis.support_resistance import ZoneMap
from core.config import load_config
from core.domain.enums import ZoneKind
from core.domain.models import SRZone


def zona(kind: ZoneKind, low: float, high: float) -> SRZone:
    return SRZone(kind=kind, low=low, high=high, touches=3)


@pytest.fixture
def qoidalar():  # noqa: ANN201
    return load_config().trade_rules


def yaqin_qarshilik() -> ZoneMap:
    """Narx 100, Stop ~5% (support 95), qarshilik atigi +0.6% da.

    Nisbat poli 1.5 bo'lsa TP1 kamida +7.5% da bo'lishi kerak,
    ya'ni 100.6 zonasi O'TKAZIB YUBORILADI.
    """
    return ZoneMap(
        price=100.0,
        atr=1.0,
        zones=[
            zona(ZoneKind.SUPPORT, 94.0, 95.0),
            zona(ZoneKind.RESISTANCE, 100.6, 101.0),   # +0.6% — arzimas
            zona(ZoneKind.RESISTANCE, 112.0, 113.0),   # +12% — mazmunli
        ],
    )


# --------------------------------------------------------------------------- #
#  Standart holat
# --------------------------------------------------------------------------- #


def test_standart_holatda_ochiq(qoidalar) -> None:  # noqa: ANN001
    """Gipoteza standart holatda YOQILMAYDI."""
    assert not qoidalar.enforce_tp1_ratio


def test_polsiz_TP1_arzimas_zonaga_tushadi(qoidalar) -> None:  # noqa: ANN001
    """Hozirgi xatti-harakat — natija #7 dagi muammoning o'zi."""
    natija = build_levels(yaqin_qarshilik(), qoidalar)

    assert natija.ok, natija.reason
    assert natija.levels.tp1 == 100.6
    # Nisbat: 0.6% / ~5.6% stop = 0.1 — arzimas
    nisbat = natija.levels.tp1_distance_pct / natija.levels.stop_distance_pct
    assert nisbat < 0.5


# --------------------------------------------------------------------------- #
#  Pol yoqilganda
# --------------------------------------------------------------------------- #


def test_pol_arzimas_zonani_otkazib_yuboradi(qoidalar) -> None:  # noqa: ANN001
    """Zona rad etilsa KEYINGISI qidiriladi, signal yo'qolmaydi.

    Uzoqroqdagi qarshilik ham haqiqiy nishon — uni ham rad etish
    tuzilmani butunlay e'tiborsiz qoldirish bo'lardi.
    """
    polli = dataclasses.replace(qoidalar, enforce_tp1_ratio=True)

    natija = build_levels(yaqin_qarshilik(), polli)

    assert natija.ok, natija.reason
    assert natija.levels.tp1 == 112.0, "keyingi mazmunli zona olinishi kerak"
    assert natija.tp_from_structure


def test_pol_haqiqatan_nisbatga_tayanadi(qoidalar) -> None:  # noqa: ANN001
    """Pol FOIZ emas — Stop masofasiga nisbatan o'lchanadi.

    Bu farq muhim: loyiha egasining qoidasi foizlarni majburiy
    qilmaslikni talab qiladi, nisbatni esa aksincha.
    """
    polli = dataclasses.replace(qoidalar, enforce_tp1_ratio=True)

    natija = build_levels(yaqin_qarshilik(), polli)

    assert natija.ok, natija.reason
    darajalar = natija.levels
    nisbat = darajalar.tp1_distance_pct / darajalar.stop_distance_pct
    assert nisbat >= qoidalar.tp1_min_risk_reward


def test_mazmunli_zona_polsiz_ham_polli_ham_bir_xil(qoidalar) -> None:  # noqa: ANN001
    """Pol faqat ARZIMAS zonani kesadi, boshqasiga tegmaydi."""
    polli = dataclasses.replace(qoidalar, enforce_tp1_ratio=True)
    yaxshi = ZoneMap(
        price=100.0,
        atr=1.0,
        zones=[
            zona(ZoneKind.SUPPORT, 94.0, 95.0),
            zona(ZoneKind.RESISTANCE, 112.0, 113.0),
        ],
    )

    assert build_levels(yaxshi, qoidalar).levels.tp1 == 112.0
    assert build_levels(yaxshi, polli).levels.tp1 == 112.0


def test_mos_zona_yoq_bolsa_olchangan_TP_ga_qaytiladi(qoidalar) -> None:  # noqa: ANN001
    """Signal YO'QOLMAYDI — o'lchangan TP allaqachon polga bo'ysunadi.

    Bu muhim: pol signal sonini kesish uchun emas, TP1 ni
    mazmunli joyga surish uchun qo'yilgan.
    """
    polli = dataclasses.replace(qoidalar, enforce_tp1_ratio=True)
    faqat_yaqin = ZoneMap(
        price=100.0,
        atr=1.0,
        zones=[
            zona(ZoneKind.SUPPORT, 94.0, 95.0),
            zona(ZoneKind.RESISTANCE, 100.6, 101.0),   # yagona, arzimas
        ],
    )

    natija = build_levels(faqat_yaqin, polli)

    assert natija.ok, natija.reason
    assert not natija.tp_from_structure, "tuzilmaviy TP topilmadi"
    nisbat = natija.levels.tp1_distance_pct / natija.levels.stop_distance_pct
    assert nisbat >= qoidalar.tp1_min_risk_reward


def test_yakuniy_nishon_nisbati_saqlanadi(qoidalar) -> None:  # noqa: ANN001
    """TP1 poli 1:3 shartini buzmasin.

    Ikkita pol bir-biriga xalaqit bermasligi kerak: TP1 uzoqlashsa
    yakuniy nishon undan ham uzoqroqda bo'lishi shart.
    """
    polli = dataclasses.replace(qoidalar, enforce_tp1_ratio=True)

    natija = build_levels(yaqin_qarshilik(), polli)

    assert natija.ok, natija.reason
    assert natija.levels.tp1 < natija.levels.final_tp
    assert natija.levels.risk_reward >= qoidalar.min_risk_reward


# --------------------------------------------------------------------------- #
#  Foiz oralig'i bilan aralashmaydi
# --------------------------------------------------------------------------- #


def test_pol_va_foiz_oraligi_mustaqil(qoidalar) -> None:  # noqa: ANN001
    """Ikkita bayroq — ikkita boshqa savol.

    `enforce_distance_bands` MASOFA haqida, `enforce_tp1_ratio`
    NISBAT haqida. Ularni bitta bayroqqa qo'shish loyiha
    egasining qarorini jimgina bekor qilardi.
    """
    faqat_pol = dataclasses.replace(qoidalar, enforce_tp1_ratio=True)

    assert not faqat_pol.enforce_distance_bands
    natija = build_levels(yaqin_qarshilik(), faqat_pol)

    assert natija.ok, natija.reason
    # Stop 5% dan keng bo'lishi mumkin — foiz oralig'i hali ham o'chiq
    assert natija.levels.stop_distance_pct > 0
