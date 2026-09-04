"""3-qism: Realized va Unrealized PNL.

Eng muhim qoida (3-prompt): raqam TAXMIN qilinmaydi, har safar
haqiqiy savdolardan hisoblanadi. Testlar shuni tekshiradi:
yozuv bo'lmasa — nol, "kutilayotgan foyda" emas.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.portfolio.pnl_calculator import (
    OchiqPozitsiya,
    YopilganQism,
    realized_hisobla,
    xulosa_qur,
)

HOZIR = datetime(2026, 9, 4, 15, 0, tzinfo=UTC)


def qism(kun_oldin: float, natija: float, signal_id: int = 1) -> YopilganQism:
    return YopilganQism(
        signal_id=signal_id,
        symbol="BTC",
        yopilgan_vaqt=HOZIR - timedelta(days=kun_oldin),
        miqdor_usd=100.0,
        natija_usd=natija,
    )


def test_savdo_yoq_bolsa_HAMMASI_nol() -> None:
    """Taxminiy raqam chiqmasin — bo'sh tarix nol beradi."""
    xulosa = xulosa_qur([], [], balans_usd=1000.0, hozir=HOZIR)

    for davr in xulosa.davrlar:
        assert davr.realized_usd == 0.0
        assert davr.realized_pct == 0.0
        assert davr.savdo_soni == 0
    assert xulosa.unrealized_usd == 0.0


def test_bugungi_natija_KALENDAR_kundan_hisoblanadi() -> None:
    """"Bugun" — ertalabdan beri, oxirgi 24 soat EMAS.

    Kecha kechqurun yopilgan savdo "bugungi" natijaga tushmasligi
    kerak: foydalanuvchi ertalab ochib, tushunarsiz raqam ko'rardi.
    """
    qismlar = [
        qism(0.2, +20.0),   # bugun ertalab
        qism(0.9, +50.0),   # kecha kechqurun (24 soat ichida!)
    ]
    davrlar = {d.nom: d for d in realized_hisobla(qismlar, 1000.0, HOZIR)}

    assert davrlar["bugun"].realized_usd == pytest.approx(20.0)
    assert davrlar["hafta"].realized_usd == pytest.approx(70.0)


def test_davrlar_bir_biriga_ichma_ich() -> None:
    qismlar = [qism(0.1, +10.0), qism(3, +20.0), qism(20, +30.0), qism(200, +40.0)]
    d = {x.nom: x for x in realized_hisobla(qismlar, 1000.0, HOZIR)}

    assert d["bugun"].realized_usd == pytest.approx(10.0)
    assert d["hafta"].realized_usd == pytest.approx(30.0)
    assert d["oy"].realized_usd == pytest.approx(60.0)
    assert d["boshidan"].realized_usd == pytest.approx(100.0)


def test_zarar_ham_hisoblanadi() -> None:
    d = {x.nom: x for x in realized_hisobla([qism(1, -35.0)], 1000.0, HOZIR)}
    assert d["hafta"].realized_usd == pytest.approx(-35.0)
    assert d["hafta"].realized_pct == pytest.approx(-3.5)


def test_bitta_signalning_bir_necha_qismi_BITTA_savdo_sanaladi() -> None:
    """TP1 va TP2 — ikki yozuv, lekin bitta savdo."""
    qismlar = [qism(1, +10.0, signal_id=7), qism(1, +15.0, signal_id=7)]
    d = {x.nom: x for x in realized_hisobla(qismlar, 1000.0, HOZIR)}

    assert d["hafta"].realized_usd == pytest.approx(25.0)
    assert d["hafta"].savdo_soni == 1


def test_foiz_balansga_nisbatan() -> None:
    d = {x.nom: x for x in realized_hisobla([qism(1, +80.0)], 1000.0, HOZIR)}
    assert d["hafta"].realized_pct == pytest.approx(8.0)


def test_balans_nol_bolsa_foiz_nol_qaytadi() -> None:
    """Nolga bo'lish bilan yiqilmasin."""
    d = {x.nom: x for x in realized_hisobla([qism(1, +80.0)], 0.0, HOZIR)}
    assert d["hafta"].realized_pct == 0.0


# --------------------------------------------------------------------- #
#  Unrealized
# --------------------------------------------------------------------- #


def test_ochiq_pozitsiya_joriy_narxda_baholanadi() -> None:
    ochiq = OchiqPozitsiya(
        signal_id=1, symbol="BTC", entry=100.0, ochiq_miqdor_usd=200.0, joriy_narx=110.0
    )
    assert ochiq.unrealized_usd == pytest.approx(20.0)


def test_ochiq_pozitsiya_zarari_ham_korinadi() -> None:
    ochiq = OchiqPozitsiya(
        signal_id=1, symbol="BTC", entry=100.0, ochiq_miqdor_usd=200.0, joriy_narx=95.0
    )
    assert ochiq.unrealized_usd == pytest.approx(-10.0)


def test_unrealized_realized_bilan_ARALASHMAYDI() -> None:
    """3-promptning qat'iy talabi: ikkalasi alohida ko'rsatiladi."""
    xulosa = xulosa_qur(
        [qism(1, +40.0)],
        [OchiqPozitsiya(2, "ETH", 100.0, 300.0, 120.0)],
        balans_usd=1000.0,
        hozir=HOZIR,
    )

    assert xulosa.davr("hafta").realized_usd == pytest.approx(40.0)
    assert xulosa.unrealized_usd == pytest.approx(60.0)
    # Realized raqamiga unrealized QO'SHILMAGAN.
    assert xulosa.davr("hafta").realized_usd != pytest.approx(100.0)
    assert xulosa.ochiq_soni == 1


def test_narxi_YOQ_pozitsiya_nol_deb_korsatilmaydi() -> None:
    """"Narx olinmadi" va "savdo nolda" — ikki boshqa narsa.

    Ilgari narx yo'q bo'lganda kirish narxi qo'yilardi va ekranda
    "+$0.00" chiqardi — ya'ni MA'LUMOT ko'rinishida. Aslida bu
    "biz bilmaymiz" edi.
    """
    baholangan = OchiqPozitsiya(1, "BTC", 100.0, 200.0, joriy_narx=110.0)
    narxsiz = OchiqPozitsiya(2, "ETH", 100.0, 500.0)

    xulosa = xulosa_qur([], [baholangan, narxsiz], balans_usd=1000.0, hozir=HOZIR)

    assert baholangan.baholandimi
    assert not narxsiz.baholandimi
    assert xulosa.unrealized_usd == pytest.approx(20.0)  # faqat baholangani
    assert xulosa.ochiq_soni == 2
    assert xulosa.baholanmagan_soni == 1
