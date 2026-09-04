"""4-qism: bot va sayt uchun BITTA manba bo'lgan dashboard.

Asosiy xavf shu yerda: bot bir raqamni, sayt boshqasini
ko'rsatishi. Testlar dashboard AYNAN `pnl_calculator` va
`capital_allocator` bergan raqamlarni uzatishini tekshiradi —
bu yerda qayta hisob bo'lmasligi kerak.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.portfolio.capital_allocator import Bolak, band_qil, bolaklarni_yarat, joylashtir
from core.portfolio.pnl_calculator import OchiqPozitsiya, YopilganQism, xulosa_qur
from core.portfolio.pnl_dashboard import dashboard_qur, matn

HOZIR = datetime(2026, 9, 4, 15, 0, tzinfo=UTC)


def qism(kun_oldin: float, natija: float, signal_id: int = 1) -> YopilganQism:
    return YopilganQism(
        signal_id=signal_id,
        symbol="BTC",
        yopilgan_vaqt=HOZIR - timedelta(days=kun_oldin),
        miqdor_usd=100.0,
        natija_usd=natija,
    )


# --------------------------------------------------------------------- #
#  Bo'sh holat — eng muhim holat
# --------------------------------------------------------------------- #


def test_savdo_yoq_bolsa_dashboard_BOSH_deb_belgilanadi() -> None:
    """Nolinchi kun: foydalanuvchi raqam emas, rostini ko'rsin."""
    xulosa = xulosa_qur([], [], balans_usd=1000.0, hozir=HOZIR)
    d = dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3))

    assert d.bosh
    assert d.xavf_pct == 0.0
    assert d.band_bolaklar == ()
    assert d.bosh_bolaklar == (1, 2, 3)


def test_bosh_dashboard_matni_RAQAM_korsatmaydi() -> None:
    xulosa = xulosa_qur([], [], balans_usd=1000.0, hozir=HOZIR)
    chiqish = matn(dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3)))

    assert "Hozircha yopilgan savdo yo'q" in chiqish
    assert "$" not in chiqish


def test_ochiq_savdo_bolsa_BOSH_emas() -> None:
    """Savdo yopilmagan, lekin pul bozorda — bu bo'sh ekran emas."""
    xulosa = xulosa_qur(
        [], [OchiqPozitsiya(1, "ETH", 100.0, 300.0, 110.0)], balans_usd=1000.0, hozir=HOZIR
    )
    assert not dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3)).bosh


# --------------------------------------------------------------------- #
#  Raqamlar qayta hisoblanmaydi
# --------------------------------------------------------------------- #


def test_qatorlar_XULOSADAGI_raqamni_ozgartirmaydi() -> None:
    xulosa = xulosa_qur([qism(1, +40.0)], [], balans_usd=1000.0, hozir=HOZIR)
    d = dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3))

    kutilgan = {x.nom: x for x in xulosa.davrlar}
    assert len(d.qatorlar) == len(xulosa.davrlar)
    for qator, nom in zip(d.qatorlar, kutilgan, strict=True):
        assert qator.usd == pytest.approx(kutilgan[nom].realized_usd)
        assert qator.pct == pytest.approx(kutilgan[nom].realized_pct)


def test_davr_nomlari_odam_oqiydigan_holga_keladi() -> None:
    xulosa = xulosa_qur([qism(1, +40.0)], [], balans_usd=1000.0, hozir=HOZIR)
    nomlar = [q.nom for q in dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3)).qatorlar]

    assert nomlar == ["Bugungi", "7 kunlik", "30 kunlik", "Boshidan beri"]


def test_unrealized_ALOHIDA_qoladi() -> None:
    """3-promptning qat'iy talabi — ekranda ham aralashmasin."""
    xulosa = xulosa_qur(
        [qism(1, +40.0)],
        [OchiqPozitsiya(2, "ETH", 100.0, 300.0, 120.0)],
        balans_usd=1000.0,
        hozir=HOZIR,
    )
    d = dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3))

    assert d.qatorlar[1].usd == pytest.approx(40.0)  # 7 kunlik realized
    assert d.unrealized_usd == pytest.approx(60.0)
    assert d.ochiq_soni == 1


# --------------------------------------------------------------------- #
#  Belgilar va matn
# --------------------------------------------------------------------- #


def test_foyda_zarar_va_nol_har_xil_belgi_oladi() -> None:
    """Uch holat uch xil ko'rinadi: foyda, zarar va "savdo bo'lmadi"."""
    xulosa = xulosa_qur(
        [qism(0.2, +10.0, signal_id=1), qism(20, -50.0, signal_id=2)],
        [],
        balans_usd=1000.0,
        hozir=HOZIR,
    )
    belgilar = {
        q.nom: q.belgi for q in dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3)).qatorlar
    }

    assert belgilar["Bugungi"] == "🟢"  # +10
    assert belgilar["30 kunlik"] == "🔴"  # +10 - 50 = -40
    assert belgilar["Boshidan beri"] == "🔴"

    # Davrida birorta savdo yopilmagan bo'lsa — na yashil, na qizil.
    eski = xulosa_qur([qism(200, +10.0)], [], balans_usd=1000.0, hozir=HOZIR)
    bosh_belgilar = {
        q.nom: q.belgi for q in dashboard_qur(eski, bolaklarni_yarat(1000.0, 3)).qatorlar
    }
    assert bosh_belgilar["Bugungi"] == "⚪"
    assert bosh_belgilar["7 kunlik"] == "⚪"


def test_zarar_matnida_MINUS_ishorasi() -> None:
    xulosa = xulosa_qur([qism(1, -35.0)], [], balans_usd=1000.0, hozir=HOZIR)
    d = dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3))
    qator = next(q for q in d.qatorlar if q.nom == "7 kunlik")

    assert qator.matn() == "🔴 7 kunlik: −$35.00 (−3.5%)"


def test_matnda_hamma_davr_bor() -> None:
    xulosa = xulosa_qur([qism(1, +40.0)], [], balans_usd=1000.0, hozir=HOZIR)
    chiqish = matn(dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3)))

    for nom in ("Bugungi", "7 kunlik", "30 kunlik", "Boshidan beri"):
        assert nom in chiqish


def test_ochiq_savdo_yoq_bolsa_matnda_unrealized_qatori_YOQ() -> None:
    """Nol dollarlik "ochiq savdo" qatori chalkashtirardi."""
    xulosa = xulosa_qur([qism(1, +40.0)], [], balans_usd=1000.0, hozir=HOZIR)
    chiqish = matn(dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3)))

    assert "Ochiq savdolarda" not in chiqish


def test_ochiq_savdo_matnda_HALI_PUL_EMAS_deb_belgilanadi() -> None:
    xulosa = xulosa_qur(
        [qism(1, +40.0)],
        [OchiqPozitsiya(2, "ETH", 100.0, 300.0, 120.0)],
        balans_usd=1000.0,
        hozir=HOZIR,
    )
    chiqish = matn(dashboard_qur(xulosa, bolaklarni_yarat(1000.0, 3)))

    assert "hali pul emas" in chiqish
    assert "$60.00" in chiqish


# --------------------------------------------------------------------- #
#  Kapital holati
# --------------------------------------------------------------------- #


def test_band_va_bosh_bolaklar_KAPITAL_holatidan_olinadi() -> None:
    bolaklar = bolaklarni_yarat(900.0, 3)
    taqsimot = joylashtir(bolaklar, stop_masofa_pct=5.0)
    assert taqsimot is not None
    bolaklar = band_qil(bolaklar, taqsimot)

    xulosa = xulosa_qur(
        [], [OchiqPozitsiya(1, "BTC", 100.0, 300.0, 100.0)], balans_usd=900.0, hozir=HOZIR
    )
    d = dashboard_qur(xulosa, bolaklar)

    assert d.band_bolaklar == (1,)
    assert d.bosh_bolaklar == (2, 3)
    # 300$ x 5% = 15$ xavf, 900$ balansdan = 1.67%
    assert d.xavf_pct == pytest.approx(15.0 / 900.0 * 100)


def test_xavf_matnda_ochiq_korsatiladi() -> None:
    bolaklar = [Bolak(raqam=1, hajm=300.0, band_kapital=300.0, band_xavf=30.0)]
    xulosa = xulosa_qur(
        [], [OchiqPozitsiya(1, "BTC", 100.0, 300.0, 100.0)], balans_usd=300.0, hozir=HOZIR
    )
    chiqish = matn(dashboard_qur(xulosa, bolaklar))

    assert "10.0%" in chiqish
    assert "Band: 1 ta savdo (bo'lak 1)" in chiqish
