"""3.5-band: ball chegarasi ERISHILADIGAN bo'lishi kerak.

Nima uchun bu test bor
----------------------
Chegara `70` (yuqori salomatlik) va `80` (o'rta salomatlik) deb
qo'yilgan edi. 100 ballik shkalada bu mantiqiy ko'rinadi. Lekin ball
funksiyasi amalda 100 ga chiqmaydi: omillarning bir qismi bu
strategiyada BIR VAQTDA to'liq bo'la olmaydi.

  • Support'da xarid -> MACD hali signal chizig'idan pastda (0/10)
  • Support'da xarid -> RSI o'rta zonada bo'lishi mumkin (7.5/15)
  • R/R aynan 1:3 (3.3-banddagi eng kam talab) -> 7.5/15

Ya'ni "ideal" sozlama ham ~55-60 ball oladi. 80 chegarasi bilan
birorta signal chiqishi MUMKIN EMAS edi — va buni hech qanday test
tutmasdi: barcha testlar yashil, bot esa 48 soat jim turdi.

Bu test aynan shu bo'shliqni yopadi: chegara strategiya haqiqatan
chiqara oladigan ball bilan solishtiriladi.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from core.config import load_config
from core.risk_engine import RiskEngine

ILDIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ILDIZ / "scripts"))

from kalibrlash import kirish, shamlar_yasa, sozlamalar  # noqa: E402

from core.analysis.strategies.classic_ta import ClassicTaStrategy  # noqa: E402


@pytest.fixture(scope="module")
def ballar() -> list[float]:
    """Turli sifatdagi sozlamalarda chiqqan haqiqiy ballar."""
    config = load_config()
    strategiya = ClassicTaStrategy(config)
    natija = []
    for s in sozlamalar():
        nomzod = strategiya.analyze(kirish(config, shamlar_yasa(s)))
        if nomzod is not None:
            natija.append(nomzod.score)
    return natija


def test_kalibrlash_nomzod_chiqaradi(ballar: list[float]) -> None:
    """Test qurilmasi buzuq bo'lsa, qolgan tekshiruvlar bo'sh o'tardi."""
    assert len(ballar) >= 5, f"kalibrlash uchun nomzod juda kam: {len(ballar)}"


def test_yuqori_salomatlik_chegarasi_erishiladi(ballar: list[float]) -> None:
    """Bozor kuchli bo'lganda nomzodlarning bir qismi o'tishi SHART."""
    chegara = load_config().scoring.thresholds.threshold_high_health
    otgan = [b for b in ballar if b >= chegara]

    assert otgan, (
        f"chegara {chegara}, lekin eng yuqori ball {max(ballar):.1f} — "
        "birorta signal chiqmaydi. `python -m scripts.kalibrlash` bilan "
        "o'lchab, chegarani taqsimotdan tanlang."
    )


def test_orta_salomatlik_chegarasi_erishiladi(ballar: list[float]) -> None:
    """O'rta bozorda talab qattiqroq, lekin baribir erishiladigan."""
    chegara = load_config().scoring.thresholds.threshold_mid_health
    otgan = [b for b in ballar if b >= chegara]

    assert otgan, (
        f"chegara {chegara}, lekin eng yuqori ball {max(ballar):.1f} — "
        "o'rta salomatlikda signal umuman chiqmaydi."
    )


def test_chegara_hammani_otkazib_yubormaydi(ballar: list[float]) -> None:
    """Teskari xavf: chegara pasayib, filtr ma'nosini yo'qotmasin."""
    chegara = load_config().scoring.thresholds.threshold_mid_health
    otgan = [b for b in ballar if b >= chegara]

    ulush = len(otgan) / len(ballar)
    assert ulush <= 0.6, (
        f"nomzodlarning {ulush:.0%} i o'tyapti — chegara juda past, "
        "saralash ma'nosini yo'qotgan"
    )


def test_orta_chegara_yuqoridan_qattiqroq() -> None:
    """3.5-band: bozor zaiflashsa talab OSHISHI kerak, pasayishi emas."""
    thresholds = load_config().scoring.thresholds
    assert thresholds.threshold_mid_health >= thresholds.threshold_high_health


def test_past_salomatlikda_signal_yoq() -> None:
    """4.9-band: indeks past bo'lsa chegara emas, umuman to'xtash."""
    config = load_config()
    motor = RiskEngine(config)
    past = config.scoring.thresholds.health_mid_min - 1
    assert motor.score_threshold(past) is None
