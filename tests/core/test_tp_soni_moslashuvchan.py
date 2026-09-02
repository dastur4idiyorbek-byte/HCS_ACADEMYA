"""TP soni QAT'IY EMAS — 1, 2 yoki 3, sharoitga qarab.

MUAMMO. `SignalLevels` da `tp1` va `tp2` maydonlari turardi, ya'ni
"har doim aynan ikkita" degan qoida MODELGA yozib qo'yilgan edi.
Bozor esa unday emas:

    toza ko'tarilish  -> ustda bitta ham qarshilik yo'q
    odatiy holat      -> ikkita
    keng diapazon     -> uchta ketma-ket zona

Qoida modelga yozilganda uni sozlama bilan o'zgartirib bo'lmaydi va
har bir o'quvchi (kartochka, sayt, backtest, kuzatuvchi) uni
qaytadan takrorlaydi.

YECHIM. `SignalLevels.takes` — 1 dan 3 tagacha `TakeProfit`.
`max_take_profits` esa YUQORI CHEGARA, majburiy miqdor emas:
bozorda nechta haqiqiy nishon bo'lsa, shuncha TP quriladi.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.analysis.scoring import build_levels
from core.analysis.support_resistance import ZoneMap
from core.config import load_config
from core.domain.enums import ZoneKind
from core.domain.models import SignalLevels, SRZone, TakeProfit, signal_levels


def zona(kind: ZoneKind, low: float, high: float) -> SRZone:
    return SRZone(kind=kind, low=low, high=high, touches=3)


def xarita(zonalar: list[SRZone], price: float = 100.0, atr: float = 1.0) -> ZoneMap:
    return ZoneMap(price=price, atr=atr, zones=zonalar)


@pytest.fixture
def qoidalar():  # noqa: ANN201
    return load_config().trade_rules


# --------------------------------------------------------------------------- #
#  Model
# --------------------------------------------------------------------------- #


def test_bitta_tp_ham_toliq_signal() -> None:
    lv = signal_levels(100.0, 99.0, 105.0)

    assert lv.tp_count == 1
    assert lv.tp1 == lv.final_tp == 105.0
    assert lv.takes[0].close_pct == 100.0


def test_uchta_tp_quriladi() -> None:
    lv = signal_levels(100.0, 99.0, 102.0, 104.0, 107.0)

    assert lv.tp_count == 3
    assert lv.tp_prices == (102.0, 104.0, 107.0)
    assert lv.tp1 == 102.0
    assert lv.final_tp == 107.0


def test_nisbat_YAKUNIY_nishon_boyicha_olchanadi() -> None:
    """R/R — TP nechta bo'lishidan qat'i nazar oxirgisidan.

    Ilgari u `tp2` maydonidan olinardi. Uchta TP bo'lganda o'sha
    maydon o'rtadagi nishonni bildirardi va nisbat past ko'rinardi.
    """
    lv = signal_levels(100.0, 99.0, 101.0, 102.0, 104.0)

    assert lv.risk_reward == pytest.approx(4.0)


def test_tp_tartibi_buzilsa_xato() -> None:
    with pytest.raises(ValueError, match="tartibi noto'g'ri"):
        signal_levels(100.0, 99.0, 104.0, 102.0)


def test_ulushlar_yigindisi_100_bolishi_shart() -> None:
    with pytest.raises(ValueError, match="100%"):
        SignalLevels(
            entry=100.0,
            stop=99.0,
            takes=(TakeProfit(102.0, 30.0), TakeProfit(104.0, 30.0)),
        )


def test_tpsiz_daraja_bolmaydi() -> None:
    with pytest.raises(ValueError, match="Kamida bitta TP"):
        SignalLevels(entry=100.0, stop=99.0, takes=())


# --------------------------------------------------------------------------- #
#  Qurish — sharoitga qarab
# --------------------------------------------------------------------------- #


def sinov_xaritasi() -> ZoneMap:
    """Narx 100, support 95-96, uchta resistance: 104, 112, 130."""
    return xarita(
        [
            zona(ZoneKind.SUPPORT, 95.0, 96.0),
            zona(ZoneKind.RESISTANCE, 104.0, 105.0),
            zona(ZoneKind.RESISTANCE, 112.0, 113.0),
            zona(ZoneKind.RESISTANCE, 130.0, 131.0),
        ]
    )


def test_standart_holatda_ikkita(qoidalar) -> None:  # noqa: ANN001
    natija = build_levels(sinov_xaritasi(), qoidalar)

    assert natija.ok, natija.reason
    assert natija.levels.tp_count == 2


def test_bittaga_cheklansa_YAKUNIY_nishon_qoladi(qoidalar) -> None:  # noqa: ANN001
    """Bitta TP bo'lsa TP1 emas, YAKUNIY nishon olinadi.

    Bu muhim: qismli sotish yo'q, ya'ni butun pozitsiya bitta
    joyda yopiladi. TP1 olinsa savdo 1:3 o'rniga 1:1.5 da tugardi.
    """
    bitta = dataclasses.replace(qoidalar, max_take_profits=1)

    natija = build_levels(sinov_xaritasi(), bitta)

    assert natija.ok, natija.reason
    assert natija.levels.tp_count == 1
    assert natija.levels.risk_reward >= qoidalar.min_risk_reward
    assert natija.levels.takes[0].close_pct == 100.0


def test_uchtaga_ruxsat_berilsa_oraliq_zona_qoshiladi(qoidalar) -> None:  # noqa: ANN001
    uchta = dataclasses.replace(qoidalar, max_take_profits=3)

    natija = build_levels(sinov_xaritasi(), uchta)

    assert natija.ok, natija.reason
    assert natija.levels.tp_count == 3
    # O'rtadagi TP haqiqiy zonaning pastki chekkasi
    assert natija.levels.takes[1].price in {104.0, 112.0, 130.0}


def test_oraliqda_zona_bolmasa_ikkitasi_qoladi(qoidalar) -> None:  # noqa: ANN001
    """Uchinchi TP O'YLAB TOPILMAYDI.

    `max_take_profits: 3` — ruxsat, majburiyat emas. Oraliqda
    haqiqiy qarshilik bo'lmasa, ikkita TP qoladi.
    """
    uchta = dataclasses.replace(qoidalar, max_take_profits=3)
    bosh_oraliq = xarita(
        [
            zona(ZoneKind.SUPPORT, 95.0, 96.0),
            zona(ZoneKind.RESISTANCE, 104.0, 105.0),
        ]
    )

    natija = build_levels(bosh_oraliq, uchta)

    assert natija.ok, natija.reason
    assert natija.levels.tp_count == 2


def test_ulushlar_sozlamadan_olinadi(qoidalar) -> None:  # noqa: ANN001
    """Ulush kartochkada hisoblanmaydi — darajalarning o'zida turadi."""
    config = load_config()
    uchta = dataclasses.replace(qoidalar, max_take_profits=3)

    natija = build_levels(
        sinov_xaritasi(), uchta, shares=config.portfolio.shares_for(3)
    )

    assert natija.ok, natija.reason
    ulushlar = tuple(tp.close_pct for tp in natija.levels.takes)
    assert ulushlar == config.portfolio.shares_for(3)
    assert sum(ulushlar) == pytest.approx(100.0)
