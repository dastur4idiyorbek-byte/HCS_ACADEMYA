"""Retseptning 3-qadami: BALL FAQAT TARTIBLAYDI.

MUAMMO. Yagona darvoza — ball chegarasi. Ball esa nomzodlarni
bir-biriga NISBATAN o'lchaydi: u "eng yaxshisi qaysi" deydi,
"shu yetarlimi" demaydi. Natijada tizim uyumning eng yuqorisini
oladi — uyumning O'ZI yomon bo'lsa ham.

O'lchov shuni tasdiqladi: to'rtta mustaqil kirish filtri sinaldi,
signal soni 610 dan 884 gacha o'zgardi, win-rate esa 36.9-39.1%
bo'lib qoldi (`docs/BACKTEST_NATIJA_2026-09-02_6.md`). Filtrlar
uyumga KIM kirishini o'zgartirdi, uyum baribir tartiblanib eng
yuqorisi olinaverdi.

YECHIM. `scoring.quality_gate` yoqilganda ruxsatni DALIL beradi:
CryptoSpot3% shartnomasi bajarilishi shart. Ball esa tartiblaydi
va xavfsizlik poli bo'lib qoladi.

Shartnoma allaqachon hisoblanardi (`setup_route.py`) va
`SignalCandidate.setup_qualified` da yotardi — lekin BUGUNGACHA U
FAQAT YORLIQ EDI. Ya'ni bu yerda yangi mantiq yozilmadi, mavjud
dalilga ovoz berildi.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.analysis.scoring import Scorer
from core.config import load_config
from core.domain.enums import HalalStatus, SignalSource
from core.domain.models import (
    HalalVerdict,
    ScoreBreakdown,
    ScoreComponent,
    SignalCandidate,
    SignalLevels,
)


class SoxtaShartnoma:
    """`SetupVerdict` o'rniga — faqat `qualified` o'qiladi."""

    def __init__(self, qualified: bool) -> None:
        self.qualified = qualified


def darajalar() -> SignalLevels:
    return SignalLevels(entry=100.0, stop=99.2, tp1=101.6, tp2=103.2)


def nomzod(symbol: str, ball: float, *, shartnoma: bool) -> SignalCandidate:
    return SignalCandidate(
        symbol=symbol,
        levels=darajalar(),
        source=SignalSource.CLASSIC_TA,
        breakdown=ScoreBreakdown(symbol, [ScoreComponent("jami", ball, 100, "sinov")]),
        halal_verdict=HalalVerdict(symbol, HalalStatus.HALAL, "halol"),
        setup=SoxtaShartnoma(shartnoma),
    )


def sozlama(**ozgarishlar: object):  # noqa: ANN201
    asos = load_config()
    return dataclasses.replace(
        asos,
        scoring=dataclasses.replace(
            asos.scoring,
            quality_gate=dataclasses.replace(asos.scoring.quality_gate, **ozgarishlar),
        ),
    )


# --------------------------------------------------------------------------- #
#  O'chiq holat — eski mexanizm o'zgarmasin
# --------------------------------------------------------------------------- #


def test_standart_holatda_ochiq() -> None:
    """Gipoteza standart holatda YOQILMAYDI.

    Rad etilgan oltita gipoteza aynan "yaxshi g'oyaga o'xshadi,
    shuning uchun yoqildi" tarzida tug'ilgan.
    """
    assert not load_config().scoring.quality_gate.enabled


def test_ochiq_bolsa_faqat_ball_qaror_qiladi() -> None:
    config = sozlama(enabled=False)
    reyting = Scorer(config).rank(
        [
            nomzod("BTC", 60, shartnoma=False),   # ball yuqori, shartnoma yo'q
            nomzod("ETH", 40, shartnoma=True),    # shartnoma bor, ball past
        ],
        threshold=50,
    )
    holat = {r.candidate.symbol: r.admitted for r in reyting}

    assert holat == {"BTC": True, "ETH": False}


# --------------------------------------------------------------------------- #
#  Yoqilgan holat — dalil qaror qiladi
# --------------------------------------------------------------------------- #


def test_shartnomasiz_nomzod_balli_yuqori_bolsa_ham_otmaydi() -> None:
    """ASOSIY o'zgarish: yuqori ball endi o'z-o'zicha yetarli emas."""
    config = sozlama(enabled=True)
    reyting = Scorer(config).rank(
        [nomzod("BTC", 99, shartnoma=False)], threshold=50
    )

    assert not reyting[0].admitted
    assert reyting[0].rejection == "setup_contract"


def test_shartnomali_nomzod_ball_chegaradan_past_bolsa_ham_otadi() -> None:
    """Teskari tomoni: dalil bor bo'lsa, chegara endi to'sib qo'ymaydi.

    Bu ataylab. "Support'da xarid qilinganda MACD hali kesmagan,
    RSI o'rta zonada" — klassik ball tizimi aynan shu holatni
    past baholaydi, holbuki tuzilma mukammal bo'lishi mumkin.
    """
    config = sozlama(enabled=True, min_base_score=35)
    reyting = Scorer(config).rank(
        [nomzod("BTC", 42, shartnoma=True)], threshold=55
    )

    assert reyting[0].admitted


def test_xavfsizlik_poli_ishlaydi() -> None:
    """Pol "tuzilma chiroyli, qolgan hammasi yomon" holatini kesadi."""
    config = sozlama(enabled=True, min_base_score=35)
    reyting = Scorer(config).rank(
        [nomzod("BTC", 20, shartnoma=True)], threshold=55
    )

    assert not reyting[0].admitted
    assert reyting[0].rejection == "score_floor"


def test_salomatlik_past_bolsa_darvoza_baribir_yopiq() -> None:
    """3.5-band ustuvor: indeks past bo'lsa hech kim o'tmaydi.

    Sifat darvozasi buni chetlab o'tmasligi kerak — aks holda yangi
    bayroq eski xavfsizlik qoidasini jimgina bekor qilardi.
    """
    config = sozlama(enabled=True)
    reyting = Scorer(config).rank(
        [nomzod("BTC", 99, shartnoma=True)], threshold=None
    )

    assert not reyting[0].admitted
    assert reyting[0].rejection == "threshold"


def test_shartnoma_majburiy_emas_qilinsa_faqat_pol_qoladi() -> None:
    config = sozlama(enabled=True, require_setup_contract=False, min_base_score=35)
    reyting = Scorer(config).rank(
        [nomzod("BTC", 40, shartnoma=False)], threshold=55
    )

    assert reyting[0].admitted


# --------------------------------------------------------------------------- #
#  Ball TARTIBLASHDA qoladi
# --------------------------------------------------------------------------- #


def test_ball_hali_ham_tartiblaydi() -> None:
    """Darvoza o'zgardi, SARALASH o'zgarmadi.

    "Ball faqat tartiblaydi" degani "ball keraksiz" degani emas:
    o'tganlar orasidan kimni birinchi berish kerakligini u hal
    qiladi.
    """
    config = sozlama(enabled=True)
    reyting = Scorer(config).rank(
        [
            nomzod("BTC", 60, shartnoma=True),
            nomzod("ETH", 80, shartnoma=True),
            nomzod("SOL", 70, shartnoma=True),
        ],
        threshold=55,
    )

    assert [r.candidate.symbol for r in reyting] == ["ETH", "SOL", "BTC"]
    assert all(r.admitted for r in reyting)


# --------------------------------------------------------------------------- #
#  Sabab KO'RINSIN
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("sabab", ["threshold", "setup_contract", "score_floor"])
def test_har_bir_sababning_nomi_bor(sabab: str) -> None:
    """Dashboard "ball past" deb noto'g'ri sabab ko'rsatmasin."""
    from core.pipeline import STAGE_LABELS

    assert sabab in STAGE_LABELS


def test_sabablar_royxati_tolik() -> None:
    """`KIRISH_RAD_SABABLARI` haqiqatan chiqadigan sabablarni qamrasin.

    Ro'yxat qo'lda yozilgan, kod esa satrlarni o'zi qaytaradi —
    ikkisi ajralib ketsa, yangi sabab nomsiz qolardi va uni faqat
    dashboardda ko'rib bilardik.
    """
    import re
    from pathlib import Path

    from core.analysis.scoring.scorer import KIRISH_RAD_SABABLARI

    manba = Path(__file__).resolve().parents[2] / "core" / "analysis" / "scoring" / "scorer.py"
    matn = manba.read_text(encoding="utf-8")
    gavda = matn[matn.index("def _kirish_rad_sababi") : matn.index("def passed")]
    qaytadigan = set(re.findall(r'return "([a-z_]+)"', gavda))

    assert qaytadigan <= set(KIRISH_RAD_SABABLARI)
    assert qaytadigan == set(KIRISH_RAD_SABABLARI)
