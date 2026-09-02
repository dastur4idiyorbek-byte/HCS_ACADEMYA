"""Fakt qatlami: struktura BIR MARTA hisoblanadi.

MUAMMO. `analyze_structure()` yettita joyda chaqirilardi — runner,
backtest, ikkala strategiya, salomatlik, QT davri. Har biri o'z
sozlamasi bilan hisoblardi, ya'ni bitta fakt haqida yettita javob
bo'lishi mumkin edi.

Bu mavhum xavf emas: bugun aynan shu turkumdagi uchta farq topildi
va ular backtest bilan jonli tizimni ajratib yubordi
(`docs/ARXITEKTURA.md`, 68 va 69-bo'limlar).

Endi struktura `StrategyInput` da keshlanadi va bitta coin uchun
bitta kirish quriladi.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.strategies.base import StrategyInput
from core.config import load_config
from core.domain.enums import HalalStatus, TrendDirection
from core.domain.models import Candle, HalalVerdict

BOSH = datetime(2026, 9, 1, tzinfo=UTC)
HALOL = HalalVerdict("BTC", HalalStatus.HALAL, "halol")


def kotarilish(n: int = 40) -> list[Candle]:
    shamlar = []
    narx = 100.0
    for i in range(n):
        keyingi = narx + 2.0 if i % 3 else narx + 0.8
        shamlar.append(
            Candle(
                open_time=BOSH + timedelta(hours=4 * i),
                open=narx,
                high=keyingi + 0.5,
                low=narx - 0.5,
                close=keyingi,
                volume=1000.0,
            )
        )
        narx = keyingi
    return shamlar


def kirish(**kwargs) -> StrategyInput:
    asosiy = {
        "symbol": "BTC",
        "now": BOSH + timedelta(days=7),
        "halal_verdict": HALOL,
        "candles": {"4h": kotarilish(), "1d": kotarilish()},
        "structure_config": load_config().analysis.market_structure,
    }
    return StrategyInput(**{**asosiy, **kwargs})


# --------------------------------------------------------------------------- #
#  Bir marta hisoblash
# --------------------------------------------------------------------------- #


def test_ikki_marta_soralganda_bir_xil_obyekt_qaytadi() -> None:
    """Kesh ishlayotganini tekshiradi — nusxa emas, AYNAN o'sha javob."""
    data = kirish()

    birinchi = data.structure("4h")
    ikkinchi = data.structure("4h")

    assert birinchi is ikkinchi


def test_har_bir_timeframe_alohida_keshlanadi() -> None:
    data = kirish()

    assert data.structure("4h") is not data.structure("1d")
    assert data.structure("4h") is data.structure("4h")


def test_malumot_yoq_timeframe_ham_javob_beradi() -> None:
    """Sham bo'lmasa ham hisob to'xtamaydi (0.3-band)."""
    data = kirish()

    natija = data.structure("1w")

    assert natija.direction is not TrendDirection.UP


# --------------------------------------------------------------------------- #
#  Ikki strategiya bitta faktni ko'radi
# --------------------------------------------------------------------------- #


def test_ikki_strategiya_bir_xil_javobni_koradi() -> None:
    """ENG MUHIM SHART.

    Ilgari `classic_ta` va `correction_entry` strukturani alohida
    hisoblardi. Sozlama bir xil bo'lgani uchun javob ham bir xil
    chiqardi — lekin buni HECH NARSA kafolatlamasdi. Bittasining
    sozlamasi o'zgarsa, ikkisi jimgina ajralib ketardi.
    """
    from core.analysis.strategies.classic_ta import ClassicTaStrategy
    from core.analysis.strategies.correction_entry import CorrectionEntryStrategy

    config = load_config()
    data = kirish()

    # Ikkala strategiya ham shu bitta kirishni oladi — sikl aynan
    # shunday beradi (`core/pipeline/cycle.py`).
    ClassicTaStrategy(config).analyze(data)
    CorrectionEntryStrategy(config).analyze(data)

    # Har bir timeframe uchun BITTA javob keshda qoldi
    for tf, natija in data._structures.items():
        assert natija is data.structure(tf)


def test_sozlama_kirishdan_olinadi() -> None:
    """Struktura sozlamasi BITTA joyda turadi.

    Strategiya o'z sozlamasini ishlatsa, ikki strategiya bir xil
    shamlar haqida boshqa-boshqa javob bera olardi.
    """
    boshqacha = dataclasses.replace(
        load_config().analysis.market_structure, fallback_min_pct=99.0
    )
    qattiq = kirish(structure_config=boshqacha)
    oddiy = kirish()

    assert qattiq.structure("4h").direction is not TrendDirection.UP
    assert oddiy.structure("4h").direction is TrendDirection.UP


# --------------------------------------------------------------------------- #
#  Strategiyalar o'zi hisoblamaydi
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "modul",
    [
        "core/analysis/strategies/classic_ta.py",
        "core/analysis/strategies/correction_entry.py",
    ],
)
def test_strategiya_ozi_strukturani_hisoblamaydi(modul: str) -> None:
    """`analyze_structure` strategiya faylida qolmasligi kerak.

    Qoida hujjatda emas, kodda yashasin: yangi strategiya ham fakt
    qatlamidan o'qishi shart.
    """
    from pathlib import Path

    matn = Path(modul).read_text(encoding="utf-8")

    assert "analyze_structure" not in matn, (
        f"{modul}: struktura O'ZIDA hisoblanyapti. "
        "`data.structure(timeframe)` orqali oling — aks holda ikki "
        "strategiya bir xil fakt haqida boshqa javob berishi mumkin."
    )
