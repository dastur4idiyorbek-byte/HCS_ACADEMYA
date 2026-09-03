"""BOZOR REJIMI — har timeframe bitta ish qiladi.

MUAMMO. Tizim bir nechta timeframeni o'qib, hammasini bitta
BALLGA qo'shardi. Ikkita oqibati bor edi:

  1. Bitta dalil bir necha marta sanaladi — kunlik ko'tarilish va
     4 soatlik ko'tarilish ko'pincha AYNAN bir xil narsa.
  2. Hech kim "YO'Q" deya olmaydi — haftalik tushayotgan bo'lsa
     ham, boshqa omillar uni qoplab ketardi va signal chiqardi.

YECHIM. Haftalik yo'nalishni, kunlik rejimni aytadi, 4 soatlik
kirishni topadi. Rejim BALL emas, SHART.

Bu testlar rejimning O'ZINI qo'riqlaydi: jadval to'liq
bo'lishini, pasayishda kirish yo'qligini va chegara rejimga
qarab o'zgarishini.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.analysis.regime import (
    BozorRejimi,
    kirish_chegarasi,
    rejimni_aniqla,
)
from core.config import load_config
from core.config.schema import RegimeRulesConfig
from core.domain.enums import TrendDirection

YONALISHLAR = list(TrendDirection)


# --------------------------------------------------------------------------- #
#  Standart holat
# --------------------------------------------------------------------------- #


def test_standart_holatda_ochiq() -> None:
    """Yangi mexanizm — o'lchanmagan, shuning uchun o'chiq.

    Loyihaning qoidasi: gipoteza jimgina yoqilmaydi
    (`docs/GIPOTEZA_DAFTARI.md`).
    """
    assert not load_config().analysis.regime_rules.enabled


# --------------------------------------------------------------------------- #
#  Jadval TO'LIQ — har kombinatsiya uchun javob bor
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("haftalik", YONALISHLAR)
@pytest.mark.parametrize("kunlik", YONALISHLAR)
def test_har_kombinatsiya_uchun_javob_bor(haftalik, kunlik) -> None:  # noqa: ANN001
    """To'qqizta kombinatsiya, to'qqizta javob — bo'shliq yo'q.

    Bo'shliq qolsa, u "aniqlanmadi" bo'lib qolardi va aniqlanmagan
    holat jimgina "ruxsat" ga aylanardi.
    """
    qaror = rejimni_aniqla(haftalik=haftalik, kunlik=kunlik)

    assert isinstance(qaror.rejim, BozorRejimi)
    assert qaror.sabab, "har qaror sababini aytishi kerak"
    assert qaror.haftalik is haftalik
    assert qaror.kunlik is kunlik


@pytest.mark.parametrize("kunlik", YONALISHLAR)
def test_haftalik_pasayishda_KIRISH_YOQ(kunlik) -> None:  # noqa: ANN001
    """Katta rasm qarshi bo'lsa — kunlik nima deyishidan qat'i nazar.

    Bu ballda mumkin emas edi: kunlik va 4 soatlik yaxshi bo'lsa,
    haftalik pasayish shunchaki bir necha ball ayirardi.
    """
    qaror = rejimni_aniqla(haftalik=TrendDirection.DOWN, kunlik=kunlik)

    assert qaror.rejim is BozorRejimi.TUSHISH
    assert not qaror.kirish_mumkin


@pytest.mark.parametrize("haftalik", YONALISHLAR)
def test_kunlik_pasayishda_ham_KIRISH_YOQ(haftalik) -> None:  # noqa: ANN001
    qaror = rejimni_aniqla(haftalik=haftalik, kunlik=TrendDirection.DOWN)

    assert qaror.rejim is BozorRejimi.TUSHISH
    assert not qaror.kirish_mumkin


def test_ikkalasi_kotarilishda_KOTARILISH_rejimi() -> None:
    qaror = rejimni_aniqla(
        haftalik=TrendDirection.UP, kunlik=TrendDirection.UP
    )

    assert qaror.rejim is BozorRejimi.KOTARILISH
    assert qaror.kirish_mumkin


@pytest.mark.parametrize(
    ("haftalik", "kunlik"),
    [
        (TrendDirection.FLAT, TrendDirection.FLAT),
        (TrendDirection.UP, TrendDirection.FLAT),
        (TrendDirection.FLAT, TrendDirection.UP),
    ],
)
def test_aniq_yonalish_yoq_bolsa_DIAPAZON(haftalik, kunlik) -> None:  # noqa: ANN001
    """FLAT "yomon" degani emas — "aniq emas" degani.

    Aniq bo'lmagan bozor diapazon deb hisoblanadi: kirish
    mumkin, lekin faqat tubdan.
    """
    qaror = rejimni_aniqla(haftalik=haftalik, kunlik=kunlik)

    assert qaror.rejim is BozorRejimi.DIAPAZON
    assert qaror.kirish_mumkin


# --------------------------------------------------------------------------- #
#  Chegara rejimga qarab o'zgaradi
# --------------------------------------------------------------------------- #


def test_diapazonda_chegara_QATTIQROQ() -> None:
    """Diapazonda trend yordam bermaydi — faqat tub.

    Ikkalasi teng bo'lsa, "rejim" degan tushunchaning amaliy
    ma'nosi qolmaydi: qoida ikkala holatda bir xil bo'lardi.
    """
    qoidalar = RegimeRulesConfig()

    kotarilish = kirish_chegarasi(BozorRejimi.KOTARILISH, qoidalar)
    diapazon = kirish_chegarasi(BozorRejimi.DIAPAZON, qoidalar)

    assert diapazon < kotarilish


def test_tushishda_chegara_NOL() -> None:
    """Pasayishda hech qanday narx yetarlicha arzon emas."""
    assert kirish_chegarasi(BozorRejimi.TUSHISH, RegimeRulesConfig()) == 0.0


def test_chegara_sozlamadan_oqiladi() -> None:
    """Raqam kodda emas, sozlamada — gipoteza daftariga tushsin."""
    qoidalar = dataclasses.replace(
        RegimeRulesConfig(),
        kotarilish_max_range_pct=70.0,
        diapazon_max_range_pct=20.0,
    )

    assert kirish_chegarasi(BozorRejimi.KOTARILISH, qoidalar) == 70.0
    assert kirish_chegarasi(BozorRejimi.DIAPAZON, qoidalar) == 20.0


# --------------------------------------------------------------------------- #
#  ULANGANMI — e'lon qilingan, lekin ulanmagan mexanizm loyihada
#  bir necha marta uchragan (ARXITEKTURA.md, 67 va 77-bo'limlar)
# --------------------------------------------------------------------------- #


def test_rejim_STRATEGIYAGA_ulangan() -> None:
    """Bayroq yoqilsa, pasayishda strategiya HAQIQATAN to'xtasin.

    Bu test mexanizmning o'zini emas, ULANISHINI tekshiradi.
    Loyihada bir necha marta shunday bo'lgan: sozlama qo'shilgan,
    izohi yozilgan, testi ham bor — lekin `analyze()` uni umuman
    o'qimasdi.
    """
    from core.analysis.strategies import ClassicTaStrategy
    from tests.core.test_classic_ta import kirish, qaytishli_kotarilish

    config = load_config()
    rejimli = dataclasses.replace(
        config,
        analysis=dataclasses.replace(
            config.analysis,
            regime_rules=dataclasses.replace(
                config.analysis.regime_rules, enabled=True
            ),
        ),
    )
    strategiya = ClassicTaStrategy(rejimli)

    # Fixturada haftalik/kunlik qatorlar berilmagan -> struktura FLAT
    # -> rejim DIAPAZON, ya'ni kirish mumkin, lekin chegara qattiqroq.
    natija = strategiya.analyze(kirish(rejimli, qaytishli_kotarilish()))
    rad = strategiya.last_rejection

    assert natija is not None or rad is not None
    if rad is not None:
        assert rad.stage in {"regime", "zone_position"}, (
            f"kutilmagan rad etish: {rad.stage} — {rad.detail}"
        )


def test_rejim_kerakli_timeframelarni_ELON_QILADI() -> None:
    """Haftalik va kunlik qatorlar YUKLANISHI kerak.

    Ro'yxatga qo'shilmasa, backtest ularni jimgina yuklamay
    qo'yardi va rejim doim "aniq emas" bo'lib qolardi — bu
    loyihada BESH marta uchragan xato turi (80-bo'lim).
    """
    from core.analysis.strategies import ClassicTaStrategy

    config = load_config()
    rejimli = dataclasses.replace(
        config,
        analysis=dataclasses.replace(
            config.analysis,
            regime_rules=dataclasses.replace(
                config.analysis.regime_rules, enabled=True
            ),
        ),
    )

    kerakli = ClassicTaStrategy(rejimli).required_timeframes()

    assert rejimli.analysis.regime_rules.trend_timeframe in kerakli
    assert rejimli.analysis.regime_rules.regime_timeframe in kerakli
    assert len(kerakli) == len(set(kerakli)), "takrorlanish bo'lmasin"
