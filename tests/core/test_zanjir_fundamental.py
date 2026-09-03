"""BLOK 1 — Fundamental."""

from __future__ import annotations

from core.analysis.fundamental import (
    BozorHolati,
    FundamentalKirish,
    Katalizator,
    Kayfiyat,
    PulOqimi,
    bozor_holati,
    fundamental_blok,
    katalizator,
    kayfiyat,
    pul_oqimi,
)
from core.analysis.turlar import Holat

# --------------------------------------------------------------------------- #
#  1.1 Bozor holati
# --------------------------------------------------------------------------- #


def test_hech_qanday_manba_yoq_bolsa_malumot_yoq() -> None:
    assert bozor_holati(BozorHolati()).holat is Holat.MALUMOT_YOQ


def test_faqat_funding_bor_bolsa_ham_qaror_chiqadi() -> None:
    """"Kamida 2 ta" sharti MAVJUDLARIGA moslashadi.

    Aks holda faqat funding bor holatda qoida o'lik bo'lardi —
    hech qachon ✅ bermasdi.
    """
    assert bozor_holati(BozorHolati(funding_rate=-0.0005)).ijobiy
    assert not bozor_holati(BozorHolati(funding_rate=0.0005)).ijobiy


def test_uchtadan_ikkitasi_yetarli() -> None:
    natija = bozor_holati(
        BozorHolati(funding_rate=-0.0005, oi_ozgarish_pct=10.0, dxy_ozgarish_pct=1.0)
    )
    assert natija.ijobiy


def test_uchtadan_bittasi_yetarli_emas() -> None:
    natija = bozor_holati(
        BozorHolati(funding_rate=-0.0005, oi_ozgarish_pct=0.0, dxy_ozgarish_pct=1.0)
    )
    assert not natija.ijobiy


def test_ikkitadan_ikkalasi_kerak() -> None:
    yarim = bozor_holati(BozorHolati(funding_rate=-0.0005, oi_ozgarish_pct=0.0))
    assert not yarim.ijobiy


# --------------------------------------------------------------------------- #
#  1.2 Pul oqimi
# --------------------------------------------------------------------------- #


def test_pul_oqimi_bittasi_yetarli() -> None:
    """Promptdagi qoida: "ikkalasi yoki bittasi mos bo'lsa"."""
    assert pul_oqimi(PulOqimi(netflow_usd=-1000.0, stablecoin_ozgarish_pct=0.0)).ijobiy


def test_pul_oqimi_hech_biri_mos_emas() -> None:
    assert not pul_oqimi(PulOqimi(netflow_usd=5000.0, stablecoin_ozgarish_pct=0.0)).ijobiy


def test_pul_oqimi_manbasiz() -> None:
    assert pul_oqimi(PulOqimi()).holat is Holat.MALUMOT_YOQ


# --------------------------------------------------------------------------- #
#  1.3 Katalizator — QATTIQ TO'SIQ
# --------------------------------------------------------------------------- #


def test_katta_va_yaqin_unlock_coinni_chetlashtiradi() -> None:
    _, tosiq = katalizator(Katalizator(unlock_kun=3, unlock_ulush_pct=8.0))
    assert tosiq is not None
    assert "unlock" in tosiq


def test_yaqin_lekin_kichik_unlock_tosmaydi() -> None:
    """Ikkala shart HAM kerak — biri yetarli emas."""
    _, tosiq = katalizator(Katalizator(unlock_kun=3, unlock_ulush_pct=1.0))
    assert tosiq is None


def test_katta_lekin_uzoq_unlock_tosmaydi() -> None:
    _, tosiq = katalizator(Katalizator(unlock_kun=90, unlock_ulush_pct=20.0))
    assert tosiq is None


def test_delisting_mustaqil_tosiq() -> None:
    """Delisting unlock'siz ham to'sadi."""
    _, tosiq = katalizator(Katalizator(delisting_xavfi=True))
    assert tosiq is not None
    assert "delisting" in tosiq


def test_tosiq_butun_blokni_bekor_qiladi() -> None:
    """4/4 bo'lsa ham to'siq g'olib — bu ball emas, xavfsizlik."""
    b = fundamental_blok(
        FundamentalKirish(
            holat=BozorHolati(funding_rate=-0.001),
            oqim=PulOqimi(netflow_usd=-1e6),
            voqea=Katalizator(unlock_kun=1, unlock_ulush_pct=30.0),
            kayf=Kayfiyat(fear_greed=20),
        )
    )
    assert not b.otdi
    assert b.qattiq_tosiq is not None


# --------------------------------------------------------------------------- #
#  1.4 Kayfiyat
# --------------------------------------------------------------------------- #


def test_qorquv_ijobiy_ochkozlik_salbiy() -> None:
    """F&G TESKARI o'qiladi: qo'rquv = arzon narx = xarid imkoni."""
    assert kayfiyat(Kayfiyat(fear_greed=20)).ijobiy
    assert not kayfiyat(Kayfiyat(fear_greed=85)).ijobiy


def test_uchtadan_ikkitasi_kerak() -> None:
    yaxshi = kayfiyat(Kayfiyat(fear_greed=20, sektor_kuchli=True, yangilik_ijobiy=False))
    yomon = kayfiyat(Kayfiyat(fear_greed=85, sektor_kuchli=False, yangilik_ijobiy=True))
    assert yaxshi.ijobiy
    assert not yomon.ijobiy


# --------------------------------------------------------------------------- #
#  Blok yig'ilishi
# --------------------------------------------------------------------------- #


def test_bosh_kirish_blokni_uzmaydi() -> None:
    """Hech qanday fundamental manba yo'q — backtestdagi odatiy holat.

    Blok "o'lchanmadi" bo'ladi va zanjirni UZMAYDI. Aks holda
    backtestda birorta signal chiqmasdi.
    """
    b = fundamental_blok(FundamentalKirish())
    assert b.olchanmadi
    assert b.otdi


def test_ziddiyat_belgilanadi_lekin_toxtatmaydi() -> None:
    """2 ijobiy / 2 salbiy — ziddiyatli, lekin blok o'tadi."""
    b = fundamental_blok(
        FundamentalKirish(
            holat=BozorHolati(funding_rate=-0.001),
            oqim=PulOqimi(netflow_usd=-1e6),
            voqea=Katalizator(unlock_kun=1, unlock_ulush_pct=0.5, yangi_listing=False),
            kayf=Kayfiyat(fear_greed=90),
        )
    )
    assert b.ziddiyatli
    assert b.otdi
    assert "ziddiyatli" in str(b)


def test_toq_sonda_ziddiyat_yoq() -> None:
    """3 ta o'lchangan tekshiruvda ko'pchilik har doim bor."""
    b = fundamental_blok(
        FundamentalKirish(
            holat=BozorHolati(funding_rate=-0.001),
            oqim=PulOqimi(netflow_usd=1e6),
            kayf=Kayfiyat(fear_greed=90),
        )
    )
    assert not b.ziddiyatli
