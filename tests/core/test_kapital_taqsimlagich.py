"""1-qism: balansni bo'laklarga bo'lish va kapital ajratish.

Bu kod REAL PUL miqdorini belgilaydi. Shuning uchun har bir qoida
alohida sinaladi va raqamlar qo'lda hisoblab tekshiriladi.
"""

from __future__ import annotations

import pytest

from core.portfolio.capital_allocator import (
    ENG_KAM_MIQDOR_USD,
    Bolak,
    band_qil,
    bolaklarni_yarat,
    bosat,
    joylashtir,
    umumiy_xavf_pct,
)


def test_balans_teng_bolinadi() -> None:
    bolaklar = bolaklarni_yarat(900.0, 3)
    assert [b.hajm for b in bolaklar] == [300.0, 300.0, 300.0]
    assert [b.raqam for b in bolaklar] == [1, 2, 3]


def test_bolak_soni_configdan() -> None:
    """3 — boshlang'ich qiymat, qat'iy emas (3-prompt, 1-qism)."""
    assert len(bolaklarni_yarat(1000.0, 5)) == 5
    assert len(bolaklarni_yarat(1000.0, 1)) == 1


def test_notogri_kirish_rad_etiladi() -> None:
    with pytest.raises(ValueError):
        bolaklarni_yarat(0.0, 3)
    with pytest.raises(ValueError):
        bolaklarni_yarat(1000.0, 0)


# --------------------------------------------------------------------- #
#  Miqdor hisobi
# --------------------------------------------------------------------- #


def test_stop_chegaradan_kichik_bolsa_bolak_toliq_ishlatiladi() -> None:
    """Stop 5% < chegara 10% -> bo'lakning HAMMASI."""
    bolaklar = bolaklarni_yarat(900.0, 3)
    t = joylashtir(bolaklar, stop_masofa_pct=5.0)

    assert t is not None
    assert t.miqdor_usd == 300.0
    assert t.toliq_bolak
    # Xavf = 300 x 5% = 15$, ya'ni bo'lakning 5% i — chegaradan past.
    assert t.xavf_usd == pytest.approx(15.0)


def test_stop_chegaradan_katta_bolsa_ulush_kamayadi() -> None:
    """Stop 20% -> ulush = 10/20 = 50% (3-promptdagi misol)."""
    bolaklar = bolaklarni_yarat(900.0, 3)
    t = joylashtir(bolaklar, stop_masofa_pct=20.0)

    assert t is not None
    assert t.miqdor_usd == pytest.approx(150.0)
    assert not t.toliq_bolak
    # ENG MUHIM TEKSHIRUV: xavf AYNAN bo'lakning 10% i.
    assert t.xavf_usd == pytest.approx(30.0)


@pytest.mark.parametrize("stop_pct", [10.5, 15.0, 20.0, 33.0, 50.0])
def test_katta_stopda_xavf_HAR_DOIM_chegarada_qoladi(stop_pct: float) -> None:
    """Stop qanchalik uzoq bo'lmasin, xavf bo'lakning 10% idan oshmasin.

    Formulaning butun ma'nosi shu. Agar bu buzilsa, uzoq Stopli
    signal bo'lakni bir zarbada yo'q qilardi.
    """
    bolaklar = bolaklarni_yarat(900.0, 3)
    t = joylashtir(bolaklar, stop_masofa_pct=stop_pct)

    assert t is not None
    assert t.xavf_usd == pytest.approx(30.0)  # 300$ ning 10% i


def test_stop_musbat_bolishi_shart() -> None:
    with pytest.raises(ValueError):
        joylashtir(bolaklarni_yarat(900.0, 3), stop_masofa_pct=0.0)


# --------------------------------------------------------------------- #
#  Band qilish va bo'shatish
# --------------------------------------------------------------------- #


def test_band_qilingan_bolak_ikkinchi_signalga_qolganini_beradi() -> None:
    """Yarim ishlatilgan bo'lak — qolgan yarmini keyingisiga beradi.

    3-prompt: "QOLGAN QISM ... SHU BO'LAK ICHIDA, band bo'lmagan
    holda qoladi, va KEYINGI signal shu qolgan qismni ishlatishi
    mumkin".
    """
    bolaklar = bolaklarni_yarat(900.0, 3)
    birinchi = joylashtir(bolaklar, 20.0)
    assert birinchi is not None
    bolaklar = band_qil(bolaklar, birinchi)

    assert bolaklar[0].bosh_kapital == pytest.approx(150.0)

    ikkinchi = joylashtir(bolaklar, 20.0)
    assert ikkinchi is not None
    # Yana o'sha bo'lak, chunki unda hali 150$ bo'sh.
    assert ikkinchi.bolak_raqami == 1
    assert ikkinchi.miqdor_usd == pytest.approx(150.0)


def test_toliq_band_bolak_otkaziladi() -> None:
    bolaklar = bolaklarni_yarat(900.0, 3)
    t = joylashtir(bolaklar, 5.0)
    assert t is not None
    bolaklar = band_qil(bolaklar, t)

    keyingi = joylashtir(bolaklar, 5.0)
    assert keyingi is not None
    assert keyingi.bolak_raqami == 2


def test_hamma_bolak_band_bolsa_signal_KUTADI() -> None:
    """`None` — signal kutuv ro'yxatiga tushadi."""
    bolaklar = bolaklarni_yarat(900.0, 3)
    for _ in range(3):
        t = joylashtir(bolaklar, 5.0)
        assert t is not None
        bolaklar = band_qil(bolaklar, t)

    assert joylashtir(bolaklar, 5.0) is None


def test_yopilgan_pozitsiya_bolakni_boshatadi() -> None:
    bolaklar = bolaklarni_yarat(900.0, 3)
    t = joylashtir(bolaklar, 5.0)
    assert t is not None
    bolaklar = band_qil(bolaklar, t)
    assert bolaklar[0].band

    bolaklar = bosat(bolaklar, 1, t.miqdor_usd, t.xavf_usd)
    assert not bolaklar[0].band
    assert bolaklar[0].bosh_kapital == pytest.approx(300.0)


def test_ikki_marta_boshatish_manfiyga_tushirmaydi() -> None:
    """Xabar ikki marta kelsa bo'lak "manfiy band" bo'lib qolmasin."""
    bolaklar = bolaklarni_yarat(900.0, 3)
    t = joylashtir(bolaklar, 5.0)
    assert t is not None
    bolaklar = band_qil(bolaklar, t)
    bolaklar = bosat(bolaklar, 1, t.miqdor_usd, t.xavf_usd)
    bolaklar = bosat(bolaklar, 1, t.miqdor_usd, t.xavf_usd)

    assert bolaklar[0].band_kapital == 0.0
    assert bolaklar[0].band_xavf == 0.0


def test_juda_kichik_qoldiq_ishlatilmaydi() -> None:
    """Birjadagi minimal hajmdan kichik pozitsiya ochilmaydi."""
    bolaklar = [Bolak(raqam=1, hajm=300.0, band_kapital=300.0 - ENG_KAM_MIQDOR_USD / 2)]
    assert joylashtir(bolaklar, 5.0) is None


# --------------------------------------------------------------------- #
#  Umumiy xavf — O'LCHANADI, taxmin qilinmaydi
# --------------------------------------------------------------------- #


def test_har_bolakda_bittadan_pozitsiya_bolsa_umumiy_xavf_10_pct() -> None:
    """3-promptdagi kafolat: hammasi Stop ursa ~10%."""
    bolaklar = bolaklarni_yarat(900.0, 3)
    for _ in range(3):
        t = joylashtir(bolaklar, 20.0)
        assert t is not None
        bolaklar = band_qil(bolaklar, t)

    assert umumiy_xavf_pct(bolaklar) == pytest.approx(10.0)


def test_bolakda_IKKITA_pozitsiya_bolsa_xavf_chegaradan_OSHADI() -> None:
    """⚠️ 3-promptning ikki qoidasi bir-biriga zid.

    Bir tomondan: "hamma bo'lak Stop ursa umumiy zarar ~10%".
    Ikkinchi tomondan: "qolgan qismni keyingi signal ishlatishi
    mumkin".

    Ikkalasi birga bajarilsa, bo'lakda ikkita pozitsiya paydo
    bo'ladi va bo'lakning xavfi 10% emas, 20% bo'ladi.

    Bu test XATO EMAS — u haqiqiy xatti-harakatni QAYD ETADI.
    Raqam yashirilmaydi: `umumiy_xavf_pct()` uni har doim
    ko'rsatib turadi.
    """
    bolaklar = bolaklarni_yarat(900.0, 3)
    for _ in range(6):  # har bo'lakka ikkitadan
        t = joylashtir(bolaklar, 20.0)
        assert t is not None
        bolaklar = band_qil(bolaklar, t)

    assert umumiy_xavf_pct(bolaklar) == pytest.approx(20.0)


def test_bosh_portfelda_xavf_nol() -> None:
    assert umumiy_xavf_pct(bolaklarni_yarat(900.0, 3)) == 0.0
    assert umumiy_xavf_pct([]) == 0.0
