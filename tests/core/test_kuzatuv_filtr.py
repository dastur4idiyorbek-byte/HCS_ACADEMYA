"""Kuzatuv paneli 3-qism filtri — faqat yuqoriga yurish potensiali.

BU TESTLARNING VAZIFASI: Downtrend coin ro'yxatga KIRMASLIGINI
qulflash. Prompt buni "hech qachon buzilmaydigan qoida" deb
belgilagan, ya'ni uni tasodifiy o'zgartirish mumkin bo'lmasligi
kerak.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.analysis.structure.swing_detector import swinglar
from core.domain.models import Candle
from core.watch_panel.uptrend_filter import (
    YANGI_OYNA,
    Yonalish,
    yonalish_aniqla,
)

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(i: int, high: float, low: float, close: float | None = None) -> Candle:
    ochilish = close if close is not None else (high + low) / 2
    return Candle(
        open_time=BOSH + timedelta(days=i),
        open=ochilish,
        high=high,
        low=low,
        close=close if close is not None else (high + low) / 2,
        volume=1000.0,
    )


def _cho_qqi(i: int, high: float) -> list[Candle]:
    """5 shamli fraktal cho'qqi — o'rtasi eng baland."""
    past = high - 20
    return [
        sham(i, high - 15, past),
        sham(i + 1, high - 10, past + 2),
        sham(i + 2, high, past + 5),
        sham(i + 3, high - 10, past + 2),
        sham(i + 4, high - 15, past),
    ]


def _tub(i: int, low: float) -> list[Candle]:
    """5 shamli fraktal tub — o'rtasi eng past."""
    yuqori = low + 20
    return [
        sham(i, yuqori, low + 15),
        sham(i + 1, yuqori - 2, low + 10),
        sham(i + 2, yuqori - 5, low),
        sham(i + 3, yuqori - 2, low + 10),
        sham(i + 4, yuqori, low + 15),
    ]


def _aniqla(shamlar: list[Candle]):  # noqa: ANN202
    return yonalish_aniqla(shamlar, swinglar(shamlar))


# --------------------------------------------------------------------------- #
#  (a) UPTREND
# --------------------------------------------------------------------------- #


def test_hh_hl_uptrend_deb_oqiladi() -> None:
    """Ko'tarilayotgan cho'qqi va tublar — Uptrend."""
    shamlar = (
        _tub(0, 100) + _cho_qqi(5, 150) + _tub(10, 120) + _cho_qqi(15, 180)
    )
    natija = _aniqla(shamlar)
    assert natija.yonalish is Yonalish.UPTREND
    assert natija.otadi


# --------------------------------------------------------------------------- #
#  (b) YANGI BURILISH
# --------------------------------------------------------------------------- #


def _tushish_keyin_burilish(kesish_ofset: int) -> list[Candle]:
    """LH/LL struktura, keyin oxirgi swing yuqori YOPILISH bilan kesiladi.

    `kesish_ofset` — kesishdan keyin nechta sham qo'shiladi, ya'ni
    burilish qanchalik "eski" bo'lishini boshqaradi.
    """
    shamlar = (
        _cho_qqi(0, 200)  # yuqori[0] = 200
        + _tub(5, 150)  # past[0]   = 150
        + _cho_qqi(10, 180)  # yuqori[1] = 180  (LH)
        + _tub(15, 130)  # past[1]   = 130  (LL)
    )
    # Oxirgi swing yuqori 180 ni yopilish bilan kesib o'tamiz.
    shamlar.append(sham(20, 195, 170, close=190))
    for j in range(kesish_ofset):
        shamlar.append(sham(21 + j, 196, 188, close=192))
    return shamlar


def test_tushishdan_yangi_chiqqan_otadi() -> None:
    natija = _aniqla(_tushish_keyin_burilish(0))
    assert natija.yonalish is Yonalish.YANGI_BURILISH
    assert natija.otadi
    assert natija.burilish_narx == 180.0
    assert natija.burilish_yosh == 0


def test_burilish_oyna_ichida_hali_yangi() -> None:
    natija = _aniqla(_tushish_keyin_burilish(YANGI_OYNA - 1))
    assert natija.yonalish is Yonalish.YANGI_BURILISH
    assert natija.burilish_yosh == YANGI_OYNA - 1


def test_eskirgan_burilish_otmaydi() -> None:
    """Burilish oynadan tashqarida VA HH/HL yig'ilmagan — nomzod emas.

    Bu aynan "yarim yo'lda qolgan" holat: narx bir marta yuqoriga
    chiqdi, lekin ko'tarilish strukturasi tasdiqlanmadi.
    """
    natija = _aniqla(_tushish_keyin_burilish(YANGI_OYNA + 5))
    assert natija.yonalish is Yonalish.ANIQ_EMAS
    assert not natija.otadi
    assert natija.burilish_yosh == YANGI_OYNA + 5


def test_kesish_yopilish_bilan_boladi_wick_bilan_emas() -> None:
    """Soya bilan tegib o'tish burilish HISOBLANMAYDI.

    `bos_choch.py` dagi bilan bir xil tamoyil: yopilish "bozor bu
    darajani qabul qildi" degani, soya esa faqat urinish.
    """
    shamlar = (
        _cho_qqi(0, 200) + _tub(5, 150) + _cho_qqi(10, 180) + _tub(15, 130)
    )
    # High 180 dan yuqori, LEKIN close pastda qoladi.
    shamlar.append(sham(20, 195, 170, close=175))
    natija = _aniqla(shamlar)
    assert natija.yonalish is not Yonalish.YANGI_BURILISH


def test_tushish_bolmagan_holat_burilish_emas() -> None:
    """Oldin tushish bo'lmagan bo'lsa, yuqoriga kesish — burilish emas.

    Yassi diapazonda narx yuqori chegarani kesib o'tishi oddiy
    hodisa. Uni "tushishdan chiqdi" deb o'qish yolg'on bo'lardi.
    """
    shamlar = (
        _cho_qqi(0, 150) + _tub(5, 100) + _cho_qqi(10, 150) + _tub(15, 100)
    )
    shamlar.append(sham(20, 160, 140, close=155))
    natija = _aniqla(shamlar)
    assert natija.yonalish is not Yonalish.YANGI_BURILISH


# --------------------------------------------------------------------------- #
#  DOWNTREND — eng muhim qulf
# --------------------------------------------------------------------------- #


def test_downtrend_otmaydi() -> None:
    shamlar = (
        _cho_qqi(0, 200) + _tub(5, 150) + _cho_qqi(10, 180) + _tub(15, 130)
    )
    natija = _aniqla(shamlar)
    assert natija.yonalish is Yonalish.DOWNTREND
    assert not natija.otadi


def test_downtrend_hech_qachon_otmaydi_qulf() -> None:
    """QAT'IY QOIDA: `Yonalish.DOWNTREND.otadi` — HAR DOIM False.

    Bu test filtrni chetlab o'tuvchi har qanday kelajakdagi
    o'zgarishni ushlaydi.
    """
    assert not Yonalish.DOWNTREND.otadi
    assert not Yonalish.ANIQ_EMAS.otadi
    assert Yonalish.UPTREND.otadi
    assert Yonalish.YANGI_BURILISH.otadi


# --------------------------------------------------------------------------- #
#  Yetarsiz ma'lumot
# --------------------------------------------------------------------------- #


def test_tarix_yetmasa_aniq_emas() -> None:
    """Ma'lumot yo'qligi "tushyapti" deb o'qilmaydi.

    `turlar.py` dagi MALUMOT_YOQ tamoyili bilan bir xil: bilmaslik
    — salbiy javob emas. Lekin nomzod ham emas.
    """
    natija = _aniqla(_cho_qqi(0, 150))
    assert natija.yonalish is Yonalish.ANIQ_EMAS
    assert not natija.otadi


def test_bosh_royxat_yiqilmaydi() -> None:
    natija = yonalish_aniqla([], [])
    assert natija.yonalish is Yonalish.ANIQ_EMAS
