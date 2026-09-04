"""Hisob simulyatsiyasi — 1000$ bilan nima bo'lardi.

Backtestning PF raqami hisobda nima bo'lishini AYTMAYDI: bir xil
PF butunlay boshqa daromad berishi mumkin, chunki har savdodagi
pul miqdori Stop masofasiga bog'liq.

Bu testlar simulyatsiyaning o'zi yolg'on gapirmasligini
tekshiradi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.backtest.zanjir_engine import Savdo
from core.config.loader import load_config
from scripts.zanjir_hisob import hisobni_yurit

BOSH = datetime(2024, 1, 1, tzinfo=UTC)


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


def savdo(kun: int, natija_pct: float, ushlash_kun: int = 3) -> Savdo:
    s = Savdo(
        symbol="BTC",
        kirish_vaqti=BOSH + timedelta(days=kun),
        entry=100.0,
        stop=97.0,
        tplar=(106.0,),
    )
    s.chiqish_vaqti = s.kirish_vaqti + timedelta(days=ushlash_kun)
    s.natija_pct = natija_pct
    return s


def test_savdo_yoq_bolsa_balans_ozgarmaydi(config) -> None:  # noqa: ANN001
    natija = hisobni_yurit([], config, 1000.0)
    assert natija.yakuniy == 1000.0
    assert natija.oylik_pct == 0.0


def test_foydali_savdo_balansni_oshiradi(config) -> None:  # noqa: ANN001
    natija = hisobni_yurit([savdo(0, +5.0)], config, 1000.0)
    assert natija.yakuniy > 1000.0
    assert natija.bajarilgan == 1


def test_zararli_savdo_balansni_kamaytiradi(config) -> None:  # noqa: ANN001
    natija = hisobni_yurit([savdo(0, -3.0)], config, 1000.0)
    assert natija.yakuniy < 1000.0


def test_spot_chegarasi_pozitsiya_balansdan_oshmaydi(config) -> None:  # noqa: ANN001
    """Stop 3% da xavf byudjeti balansdan katta hajm berardi.

    Leverage yo'q — natija balans bilan kesilishi SHART. Aks holda
    simulyatsiya mavjud bo'lmagan pul bilan savdo qilardi va
    raqam yolg'on chiqardi.
    """
    natija = hisobni_yurit([savdo(0, +100.0)], config, 1000.0)
    # Bitta savdo balansni IKKI baravardan ko'p oshira olmaydi:
    # pozitsiya balansdan katta bo'lolmaydi.
    assert natija.yakuniy <= 2000.0


def test_kapital_band_bolganda_yangi_savdo_otkaziladi(config) -> None:  # noqa: ANN001
    """Bir vaqtda ochiq savdolar butun balansni band qilsa —
    keyingisi O'TKAZIB YUBORILADI va bu SANALADI.

    Jim tashlab yuborilsa, simulyatsiya real hisobda imkonsiz
    bo'lgan savdolarni ham hisoblab, natijani oshirib ko'rsatardi.
    """
    savdolar = [savdo(0, +2.0, ushlash_kun=60) for _ in range(20)]
    natija = hisobni_yurit(savdolar, config, 1000.0)
    assert natija.otkazilgan > 0
    assert natija.bajarilgan + natija.otkazilgan == 20


def test_oylik_foiz_qoshilib_hisoblanadi(config) -> None:  # noqa: ANN001
    """Oylik foiz — o'rtacha emas, COMPOUND."""
    natija = hisobni_yurit([savdo(k * 30, +4.0) for k in range(12)], config, 1000.0)
    kutilgan = ((natija.yakuniy / 1000.0) ** (1 / natija.oylar) - 1) * 100
    assert abs(natija.oylik_pct - kutilgan) < 1e-6


# --- Signal manbasi kartochkada ko'rinishi ----------------------- #
#
# 2026-09-04: admin signal olib, uni yangi modul berganmi yoki eski
# moduldan qolganmi ajrata olmadi. Kartochkada bu ma'lumot yo'q edi.


def _kartochka(manba=None):  # noqa: ANN001, ANN202
    from bot.formatting import render_signal_card
    from core.domain.models import signal_levels
    from core.services.kirish_rejasi import decide_entry_plan

    lv = signal_levels(entry=100.0, stop=97.0, tp1=106.0)
    return render_signal_card("BTC", lv, decide_entry_plan(100.0, lv), manba=manba)


def test_zanjir_signalida_yorliq_bor() -> None:
    from core.domain.enums import SignalSource

    assert "Zanjir moduli" in _kartochka(SignalSource.ZANJIR)


def test_qolda_kiritilgan_signal_boshqa_yorliq() -> None:
    from core.domain.enums import SignalSource

    matn = _kartochka(SignalSource.MANUAL)
    assert "Qo'lda kiritilgan" in matn
    assert "Zanjir moduli" not in matn


def test_notanish_manba_ISHONCHLI_deb_korsatilmaydi() -> None:
    """Eng muhim test: noma'lum manba "yangi modul" bo'lib chiqmasin.

    Eski modul qoldirgan signalning manbasi ro'yxatda yo'q. Agar u
    jimgina "Zanjir moduli" yorlig'ini olsa, admin eski signalga
    yangisidek ishonardi.
    """
    from core.domain.enums import SignalSource

    matn = _kartochka(SignalSource.CLASSIC_TA)
    assert "Zanjir moduli" not in matn
    assert "Eski modul" in matn


def test_manba_berilmasa_yorliq_umuman_yoq() -> None:
    matn = _kartochka(None)
    assert "Zanjir moduli" not in matn
    assert "Eski modul" not in matn


def test_bazadagi_notanish_qiymat_yiqilmaydi() -> None:
    """Bazada eski/notanish `source` bo'lsa, bot yiqilmasin."""
    from bot.services.scheduler import _manba

    assert _manba("zanjir") is not None
    assert _manba("allaqachon_yoq_manba") is None
    assert _manba(None) is None
    assert _manba("") is None
