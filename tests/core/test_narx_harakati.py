"""NARX HARAKATI — kitobning yadrosi.

MANBA: `docs/NARX_HARAKATI_STRATEGIYALARI.md`.

Kitobdagi to'qqizta XARID strategiyasidan oltitasi aynan bir xil
uch qadamni takrorlaydi:

    1. daraja YORIB o'tiladi
    2. narx unga QAYTA SINOVGA keladi
    3. o'sha yerda BUQASIMON sham  ->  kirish

Bu testlar shamlarni QO'LDA quradi, ya'ni to'g'ri javob oldindan
ma'lum. Har bir test bitta shartni buzadi va naqsh
TOPILMASLIGINI tekshiradi — aks holda "naqsh" degan tushuncha
bo'sh so'z bo'lardi.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

from core.analysis.narx_harakati import (
    ikkita_pastlik_topilsinmi,
    qayta_sinov_topilsinmi,
)
from core.config import load_config
from core.config.schema import NarxHarakatiConfig
from core.domain.models import Candle

BOSH = datetime(2025, 1, 1, tzinfo=UTC)
DARAJA = 100.0
ATR = 1.0


def sham(i: int, o: float, h: float, low: float, c: float) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(hours=4 * i),
        open=o,
        high=h,
        low=low,
        close=c,
        volume=100.0,
        closed=True,
    )


def naqsh_qatori(
    *,
    yorish: bool = True,
    qayta_sinov: bool = True,
    buqasimon: bool = True,
) -> list[Candle]:
    """Kitobdagi naqsh — qismlarini o'chirib ham qurish mumkin.

    Shakl:
        0-2   narx daraja OSTIDA
        3     YORISH (daraja ustida yopiladi)
        4-5   yuqorida qoladi
        6     QAYTA SINOV (quyi nuqta darajaga qaytadi)
        7     TASDIQ (buqasimon, daraja ustida yopiladi)
    """
    shamlar = [
        sham(0, 96.0, 97.0, 95.5, 96.5),
        sham(1, 96.5, 98.0, 96.0, 97.5),
        sham(2, 97.5, 99.0, 97.0, 98.5),
    ]
    if not yorish:
        # Narx daraja OSTIDA qoladi — faqat soyalar tegib o'tadi.
        # Bunday holatda "yorish" degan narsa yo'q.
        shamlar.extend([
            sham(3, 98.5, 100.4, 98.0, 99.0),
            sham(4, 99.0, 100.3, 98.2, 99.5),
            sham(5, 99.5, 100.2, 98.8, 99.2),
            sham(6, 99.2, 100.4, 98.9, 99.8),
        ])
    else:
        # 3) YORISH — daraja USTIDA yopiladi
        shamlar.append(sham(3, 98.5, 103.0, 98.0, 102.5))
        shamlar.append(sham(4, 102.5, 104.0, 102.0, 103.5))
        shamlar.append(sham(5, 103.5, 104.5, 102.5, 103.0))
        # 6) QAYTA SINOV
        if qayta_sinov:
            shamlar.append(sham(6, 103.0, 103.5, 100.2, 101.0))
        else:
            # darajaga umuman qaytmaydi
            shamlar.append(sham(6, 103.0, 104.0, 102.8, 103.2))
    # 7) TASDIQ
    if buqasimon:
        shamlar.append(sham(7, 101.0, 105.0, 100.8, 104.5))
    else:
        # qizil sham — yopilish ochilishdan past
        shamlar.append(sham(7, 105.0, 105.2, 100.8, 101.5))
    return shamlar


def qoidalar() -> NarxHarakatiConfig:
    return NarxHarakatiConfig()


# --------------------------------------------------------------------------- #
#  Standart holat
# --------------------------------------------------------------------------- #


def test_standart_holatda_ochiq() -> None:
    """Yangi strategiya — o'lchanmagan, shuning uchun o'chiq."""
    assert not load_config().strategies.narx_harakati.enabled


# --------------------------------------------------------------------------- #
#  To'liq naqsh topiladi
# --------------------------------------------------------------------------- #


def test_toliq_naqsh_topiladi() -> None:
    natija = qayta_sinov_topilsinmi(naqsh_qatori(), DARAJA, qoidalar(), ATR)

    assert natija is not None, "kitobdagi naqshning o'zi topilmadi"
    assert natija.yorish_index == 3
    assert natija.sinov_index == 6
    assert natija.tasdiq_index == 7


def test_stop_uchun_eng_past_nuqta_olinadi() -> None:
    """Kitob: "stoploss oldingi pastki nuqtadan pastroqda"."""
    natija = qayta_sinov_topilsinmi(naqsh_qatori(), DARAJA, qoidalar(), ATR)

    assert natija is not None
    # Qayta sinov va tasdiq shamlarining eng pasti
    assert natija.eng_past == 100.2


# --------------------------------------------------------------------------- #
#  Har bir shart MAJBURIY — bittasi yo'q bo'lsa naqsh ham yo'q
# --------------------------------------------------------------------------- #


def test_yorish_bolmasa_naqsh_yoq() -> None:
    """Soya bilan tegib o'tish yorish emas.

    Kitob "yorib o'tish" deydi — ya'ni sham daraja USTIDA
    yopilishi kerak.
    """
    qator = naqsh_qatori(yorish=False)

    assert qayta_sinov_topilsinmi(qator, DARAJA, qoidalar(), ATR) is None


def test_qayta_sinov_bolmasa_naqsh_yoq() -> None:
    """Bu — butun g'oyaning o'zi.

    Yorishdan keyin darhol kirish kitobda ATAYLAB xato deb
    ko'rsatilgan: "narx kritik zonaga yaqin bo'lganda savdoga
    kiramiz va stoploss tezda uriladi".
    """
    qator = naqsh_qatori(qayta_sinov=False)

    assert qayta_sinov_topilsinmi(qator, DARAJA, qoidalar(), ATR) is None


def test_tasdiq_shami_qizil_bolsa_naqsh_yoq() -> None:
    """Kitob: qayta sinovdan keyin BUQASIMON sham kerak."""
    qator = naqsh_qatori(buqasimon=False)

    assert qayta_sinov_topilsinmi(qator, DARAJA, qoidalar(), ATR) is None


def test_tasdiq_sharti_ochirilsa_qizil_sham_ham_otadi() -> None:
    """Shart sozlamada — o'lchanadigan qilib qo'yilgan."""
    qator = naqsh_qatori(buqasimon=False)
    tasdiqsiz = dataclasses.replace(qoidalar(), tasdiq_shami_shart=False)

    # Qizil sham daraja USTIDA yopilgan (101.5 > 100) — o'tishi kerak
    assert qayta_sinov_topilsinmi(qator, DARAJA, tasdiqsiz, ATR) is not None


def test_narx_allaqachon_tepada_bolsa_yorish_hisoblanmaydi() -> None:
    """"Yorish" — pastdan tepaga o'tish.

    Narx butun tarix davomida daraja ustida bo'lsa, hech narsa
    yorilmagan va naqsh ham yo'q.
    """
    qator = [
        sham(i, 102.0 + i, 104.0 + i, 101.0 + i, 103.0 + i) for i in range(6)
    ]
    qator.append(sham(6, 108.0, 109.0, 100.2, 101.0))
    qator.append(sham(7, 101.0, 106.0, 100.8, 105.0))

    assert qayta_sinov_topilsinmi(qator, DARAJA, qoidalar(), ATR) is None


def test_naqsh_OXIRGI_shamda_tugashi_shart() -> None:
    """Eski naqsh signal emas.

    Aks holda bot allaqachon o'tib ketgan imkoniyatga kirardi —
    kitob buni "kech kirish" deb ogohlantiradi.
    """
    qator = naqsh_qatori()
    # Naqshdan keyin narx uzoqqa ketdi
    qator.extend([
        sham(8, 104.5, 112.0, 104.0, 111.0),
        sham(9, 111.0, 118.0, 110.5, 117.0),
    ])

    natija = qayta_sinov_topilsinmi(qator, DARAJA, qoidalar(), ATR)

    # Oxirgi sham buqasimon va daraja ustida, lekin qayta sinov
    # oynasi ichida darajaga qaytish yo'q
    assert natija is None or natija.tasdiq_index == len(qator) - 1


def test_qayta_sinov_juda_kech_bolsa_naqsh_yoq() -> None:
    """Yorishdan uzoq vaqt keyingi "qayta sinov" — qayta sinov emas.

    Fixturada qaytish yorishdan uch sham keyin. Oyna bittaga
    tushirilsa naqsh yo'qolishi kerak.
    """
    qator = naqsh_qatori()
    tor = dataclasses.replace(qoidalar(), qayta_sinov_oynasi=1)

    assert qayta_sinov_topilsinmi(qator, DARAJA, tor, ATR) is None


def test_yorish_juda_eski_bolsa_naqsh_yoq() -> None:
    """Yorish tasdiqdan juda uzoqda bo'lsa, naqsh bir butun emas."""
    qator = naqsh_qatori()
    tor = dataclasses.replace(qoidalar(), yorish_oynasi=2)

    assert qayta_sinov_topilsinmi(qator, DARAJA, tor, ATR) is None


# --------------------------------------------------------------------------- #
#  Ikkita pastlik (kitobning 2 va 10-strategiyasi)
# --------------------------------------------------------------------------- #


def test_ikkita_pastlik_topiladi() -> None:
    """Ikki marta bir xil darajadan qaytish, orada aniq cho'qqi."""
    qator = [
        sham(0, 110, 111, 109, 110),
        sham(1, 110, 110.5, 100.0, 101),   # 1-TUB
        sham(2, 101, 106, 100.8, 105),
        sham(3, 105, 108.0, 104, 107),     # CHO'QQI (bo'yin chizig'i)
        sham(4, 107, 107.5, 103, 104),
        sham(5, 104, 104.5, 100.3, 101),   # 2-TUB
        sham(6, 101, 105, 100.9, 104),
    ]

    natija = ikkita_pastlik_topilsinmi(qator, qoidalar(), ATR)

    assert natija is not None, "aniq ikkita pastlik topilmadi"
    assert natija.boyin_chizigi == 108.0
    assert natija.tub_narxi == 100.0


def test_tublar_uzoq_bolsa_ikkita_pastlik_emas() -> None:
    """Ikki tub bir-biridan uzoq bo'lsa, bu figura emas."""
    qator = [
        sham(0, 110, 111, 109, 110),
        sham(1, 110, 110.5, 100.0, 101),   # 1-TUB
        sham(2, 101, 106, 100.8, 105),
        sham(3, 105, 108.0, 104, 107),
        sham(4, 107, 107.5, 95, 96),
        sham(5, 96, 96.5, 90.0, 91),       # 2-TUB — 10 birlik pastda
        sham(6, 91, 95, 90.9, 94),
    ]

    assert ikkita_pastlik_topilsinmi(qator, qoidalar(), ATR) is None
