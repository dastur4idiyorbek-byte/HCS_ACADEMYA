"""Signal grafigi rasmi — chizishdan oldingi HISOB.

Rasmning o'zini test bilan tekshirib bo'lmaydi (piksel solishtirish
mo'rt), lekin uning ostidagi matematikani — mumkin va shart. Ko'z bilan
topilmaydigan xatolar aynan shu yerda: daraja rasmdan chiqib ketishi,
yorliqlar ustma-ust tushishi, narx-piksel almashinuvining teskari
bo'lishi.
"""

from __future__ import annotations

import datetime as dt
from itertools import pairwise

import pytest

from bot.chart import (
    BOYI,
    PAST_CHET,
    TEPA,
    YORLIQ_ORALIQ,
    _yorliqlarni_joylashtir,
    olcham_hisobla,
    render_signal_chart,
)
from core.domain.models import Candle, SignalLevels

DARAJALAR = SignalLevels(entry=0.869, stop=0.8294, tp1=0.9176, tp2=0.9283)


def shamlar(n: int = 40, narx: float = 0.86) -> list[Candle]:
    boshi = dt.datetime(2026, 8, 25, tzinfo=dt.UTC)
    return [
        Candle(
            open_time=boshi + dt.timedelta(hours=4 * i),
            open=narx, high=narx * 1.01, low=narx * 0.99, close=narx, volume=1.0,
        )
        for i in range(n)
    ]


# --------------------------------------------------------------------------- #
#  Narx <-> piksel
# --------------------------------------------------------------------------- #


def test_yuqori_narx_kichik_y_beradi() -> None:
    """Ekranda y pastga o'sadi, narx esa yuqoriga — teskari bog'lanish."""
    olch = olcham_hisobla(shamlar(), DARAJALAR)
    assert olch.y(DARAJALAR.tp2) < olch.y(DARAJALAR.entry) < olch.y(DARAJALAR.stop)


def test_barcha_darajalar_rasm_ichida() -> None:
    """Stop va TP ko'pincha shamlar oralig'idan TASHQARIDA bo'ladi.

    Oraliq faqat shamlardan hisoblansa, ular rasmdan chiqib ketardi.
    """
    olch = olcham_hisobla(shamlar(), DARAJALAR)
    for narx in (DARAJALAR.stop, DARAJALAR.entry, DARAJALAR.tp1, DARAJALAR.tp2):
        y = olch.y(narx)
        assert TEPA <= y <= BOYI - PAST_CHET, f"{narx} rasmdan chiqdi: y={y}"


def test_shamlar_ham_rasm_ichida() -> None:
    olch = olcham_hisobla(shamlar(), DARAJALAR)
    for sham in shamlar():
        assert TEPA <= olch.y(sham.high) <= BOYI - PAST_CHET
        assert TEPA <= olch.y(sham.low) <= BOYI - PAST_CHET


def test_tekis_narxda_bolinish_yuz_bermaydi() -> None:
    """Barcha narx bir xil bo'lsa oraliq nol — nolga bo'linish xavfi."""
    tekis = SignalLevels(entry=100, stop=99.99, tp1=100.01, tp2=100.02)
    olch = olcham_hisobla(shamlar(5, 100.0), tekis)
    assert olch.eng_yuqori > olch.eng_past
    assert TEPA <= olch.y(100.0) <= BOYI - PAST_CHET


# --------------------------------------------------------------------------- #
#  Yorliqlarni joylashtirish
# --------------------------------------------------------------------------- #


def test_uzoq_yorliqlar_qimirlamaydi() -> None:
    ylar = [100.0, 200.0, 300.0, 400.0]
    assert _yorliqlarni_joylashtir(ylar) == ylar


def test_yaqin_yorliqlar_ajratiladi() -> None:
    """TP1 va TP2 orasi 1-2% bo'lishi ODATIY hol — ustma-ust tushardi."""
    natija = _yorliqlarni_joylashtir([200.0, 205.0, 300.0, 310.0])
    for oldingi, keyingi in pairwise(natija):
        assert keyingi - oldingi >= YORLIQ_ORALIQ - 1e-9


def test_yorliqlar_rasmdan_chiqib_ketmaydi() -> None:
    """Hammasi pastda to'planib qolsa, ustun yuqoriga suriladi."""
    natija = _yorliqlarni_joylashtir([560.0, 562.0, 564.0, 566.0])
    assert natija[0] - 19 >= TEPA - 1e-9
    assert natija[-1] + 19 <= BOYI - PAST_CHET + 1e-9


def test_tartib_saqlanadi() -> None:
    """Yorliq siljisa ham, tartibi o'zgarmasligi kerak: TP2 har doim
    Stop dan yuqorida turadi, aks holda rasm yolg'on gapirardi."""
    natija = _yorliqlarni_joylashtir([300.0, 302.0, 305.0, 307.0])
    assert natija == sorted(natija)


# --------------------------------------------------------------------------- #
#  Rasmning o'zi
# --------------------------------------------------------------------------- #


def test_png_chiqadi() -> None:
    png = render_signal_chart("DOT", shamlar(), DARAJALAR)
    assert png.startswith(b"\x89PNG"), "PNG sarlavhasi kutilgan"
    assert len(png) > 1000


def test_shamsiz_grafik_xato_beradi() -> None:
    """Bo'sh grafik chizishning ma'nosi yo'q — chaqiruvchi bilsin."""
    with pytest.raises(ValueError, match="sham"):
        render_signal_chart("DOT", [], DARAJALAR)


def test_bitta_sham_ham_ishlaydi() -> None:
    """Yangi coinda tarix qisqa bo'lishi mumkin — yiqilmasin."""
    png = render_signal_chart("YANGI", shamlar(1), DARAJALAR)
    assert png.startswith(b"\x89PNG")
