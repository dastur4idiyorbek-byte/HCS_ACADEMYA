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

from core.analysis.scoring import Scorer
from core.config import load_config
from core.risk_engine import RiskEngine

ILDIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ILDIZ / "scripts"))

from kalibrlash import kirish, shamlar_yasa, sozlamalar  # noqa: E402

from core.analysis.strategies.classic_ta import ClassicTaStrategy  # noqa: E402


@pytest.fixture(scope="module")
def nomzodlar() -> list:  # noqa: ANN201
    """Turli sifatdagi sozlamalarda chiqqan haqiqiy nomzodlar."""
    config = load_config()
    strategiya = ClassicTaStrategy(config)
    natija = []
    for s in sozlamalar():
        nomzod = strategiya.analyze(kirish(config, shamlar_yasa(s)))
        if nomzod is not None:
            natija.append(nomzod)
    return natija


@pytest.fixture(scope="module")
def ballar(nomzodlar: list) -> list[float]:  # noqa: ANN001
    """BAZAVIY ballar — chegara aynan shu shkalada o'lchangan.

    CryptoSpot3% bonuslari shkalani 125 ga kengaytiradi, lekin ular
    darvozaga emas, REYTINGGA ta'sir qiladi. Bu yerda to'liq ball
    olinsa, test chegarani noto'g'ri shkalada tekshirardi va "chegara
    juda past" degan ogohlantirish yolg'on chiqardi.
    """
    return [n.breakdown.base_total for n in nomzodlar]


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


def test_bonus_darvozani_yuvib_yubormaydi(nomzodlar: list) -> None:  # noqa: ANN001
    """CryptoSpot3% bonuslari chegarani JIMGINA yumshatmasligi kerak.

    Bonuslar qo'shilganda ballar 100 dan oshadi. Agar chegara to'liq
    ballga qo'llansa, o'lchovda nomzodlarning 80% i o'tib ketardi —
    ya'ni "eng yaxshi 33%" degan tanlov ma'nosini yo'qotardi. Shuning
    uchun `Scorer.rank()` darvozani BAZAVIY ballda tekshiradi.
    """
    chegara = load_config().scoring.thresholds.threshold_mid_health
    reyting = Scorer(load_config()).rank(nomzodlar, chegara)

    otganlar = [r for r in reyting if r.passed_threshold]
    assert all(r.base_score >= chegara for r in otganlar)

    # Bonusi bor, lekin bazaviy balli past nomzod O'TMASLIGI kerak
    bonusli = [r for r in reyting if r.score > r.base_score]
    assert bonusli, "bonus umuman berilmayapti — qatlam ulanmaganmi?"
    for r in bonusli:
        if r.base_score < chegara:
            assert not r.passed_threshold


def test_reyting_toliq_ball_boyicha_saralanadi(nomzodlar: list) -> None:  # noqa: ANN001
    """Darvoza bazaviy ballda, lekin SARALASH to'liq ballda.

    Bonuslarning butun ma'nosi shu: bir xil sifatdagi ikki nomzoddan
    strukturasi va sweep'i borini yuqoriga chiqarish.
    """
    reyting = Scorer(load_config()).rank(nomzodlar, 0.0)
    ballar = [r.score for r in reyting]
    assert ballar == sorted(ballar, reverse=True)


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


# --------------------------------------------------------------------------- #
#  Salomatlik BANDI ham erishiladigan bo'lishi kerak
# --------------------------------------------------------------------------- #
#
# Bu — "erishib bo'lmas chegara" xatosining ikkinchi ko'rinishi, faqat
# bir daraja yuqorida. Ball chegarasi (40-bo'lim) erishib bo'lmas edi;
# keyin ma'lum bo'ldiki, uni TANLAYDIGAN salomatlik bandi ham erishib
# bo'lmas ekan.
#
# Jonli botda indeks 70-77 oralig'ida yurdi, YUQORI band esa 80 talab
# qilardi. Natijada `threshold_high_health` bir marta ham qo'llanilmadi
# va "moslashuvchi chegara" amalda doim bitta qiymat bo'lib qoldi.


def _salomatlik_shifti(config, breadth_ratio: float) -> float:
    """Berilgan bozor kengligida indeks eng ko'pi bilan qancha bo'la oladi.

    Qolgan barcha omillar MUKAMMAL deb hisoblanadi.
    """
    vazn = config.market_health.weights.halal_trend_breadth
    return (100.0 - vazn) + vazn * breadth_ratio


def test_yuqori_band_kengliksiz_ham_erishiladi(config) -> None:  # noqa: ANN001
    """Bitta omil butun bandni qulflab qo'ymasligi kerak.

    Kenglik omili 25 ball turadi. Ya'ni kenglik nolga yaqin bo'lsa,
    indeks 75 dan yuqoriga chiqa OLMAYDI — qolgan hamma narsa mukammal
    bo'lsa ham. 80 lik band shunda butunlay yopiq bo'lardi.
    """
    shift = _salomatlik_shifti(config, breadth_ratio=0.0)
    chegara = config.scoring.thresholds.health_high_min

    assert chegara <= shift, (
        f"YUQORI band {chegara}, lekin kenglik nolga yaqin bo'lganda indeks "
        f"{shift:.0f} dan oshmaydi — band hech qachon ochilmaydi"
    )


def test_kuzatilgan_oraliq_yuqori_bandga_tushadi(config) -> None:  # noqa: ANN001
    """Jonli botda o'lchangan qiymatlar bandga tushishi kerak.

    Bu raqamlar HAQIQIY: bir hafta ishlagan botning `/panel` -> 💓
    ekranidan olingan.
    """
    kuzatilgan = [70, 70, 71, 71, 71, 71, 73, 77]
    chegara = config.scoring.thresholds.health_high_min

    yuqorida = [q for q in kuzatilgan if q >= chegara]
    assert yuqorida, (
        f"kuzatilgan {kuzatilgan} qiymatlarning birortasi ham YUQORI bandga "
        f"({chegara}) tushmayapti — moslashuvchi chegara ishlamaydi"
    )


def test_bandlar_tartibi_saqlanadi(config) -> None:  # noqa: ANN001
    """Yuqori band o'rtadan baland, o'rta esa "signal yo'q" dan baland."""
    t = config.scoring.thresholds
    assert t.health_high_min > t.health_mid_min


def test_yuqori_bandda_chegara_yengilroq(config) -> None:  # noqa: ANN001
    """3.5-band mantig'i: bozor kuchli bo'lsa talab pasayadi."""
    from core.risk_engine import RiskEngine

    motor = RiskEngine(config)
    t = config.scoring.thresholds

    yuqori = motor.score_threshold(t.health_high_min)
    orta = motor.score_threshold(t.health_mid_min)

    assert yuqori is not None and orta is not None
    assert yuqori <= orta, "kuchli bozorda talab qattiqroq bo'lmasligi kerak"
