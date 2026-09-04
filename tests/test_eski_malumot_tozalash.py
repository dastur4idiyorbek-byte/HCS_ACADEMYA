"""Tozalash skripti FAQAT kerakli jadvalga tegsin.

Bu skript ma'lumot O'CHIRADI. Xato ro'yxat foydalanuvchilarni,
to'lovlarni yoki halol hukmlarni yo'q qilishi mumkin — shuning
uchun ro'yxat test bilan qulflangan.
"""

from __future__ import annotations

from core.storage.models import Base
from scripts.eski_malumot_tozalash import OCHIRILADI, SAQLANADI

#: Hech qanday sharoitda o'chirilmaydigan jadvallar.
QIMMATLI = {
    "users",
    "subscriptions",
    "payments",
    "coin_rulings",
    "halal_universe_snapshots",
    "content",
    "price_config",
    "risk_config",
    "bozor_kesimlari",
    "bozor_korinishlari",
}


def test_qimmatli_jadval_ochirilmaydi() -> None:
    ochiriladigan = {jadval for _, jadval, _ in OCHIRILADI}
    assert not (ochiriladigan & QIMMATLI)


def test_ikkala_royxat_kesishmaydi() -> None:
    """Bitta jadval ham o'chiriladigan, ham saqlanadigan bo'lolmaydi."""
    ochiriladigan = {jadval for _, jadval, _ in OCHIRILADI}
    saqlanadigan = {jadval for jadval, _ in SAQLANADI}
    assert not (ochiriladigan & saqlanadigan)


def test_jadval_nomlari_haqiqiy() -> None:
    """Nomi xato yozilgan jadval JIMGINA hech narsa o'chirmasdi."""
    haqiqiy = set(Base.metadata.tables)
    for _, jadval, _ in OCHIRILADI:
        assert jadval in haqiqiy, jadval
    for jadval, _ in SAQLANADI:
        assert jadval in haqiqiy, jadval


def test_har_bir_jadval_royxatda_bor() -> None:
    """Yangi jadval qo'shilsa — u qaysi ro'yxatga tushishi HAL QILINSIN.

    Ansiz yangi jadval jimgina "tozalanmaydigan" bo'lib qolardi
    va keyingi safar kimdir uni qo'lda o'chirishga majbur bo'lardi.
    """
    ochiriladigan = {jadval for _, jadval, _ in OCHIRILADI}
    saqlanadigan = {jadval for jadval, _ in SAQLANADI}
    qolgan = set(Base.metadata.tables) - ochiriladigan - saqlanadigan
    assert not qolgan, f"bu jadvallar hech qaysi ro'yxatda yo'q: {sorted(qolgan)}"


def test_bola_jadval_avval_ochiriladi() -> None:
    """signals dan OLDIN unga bog'liq jadvallar o'chirilsin."""
    tartib = [jadval for _, jadval, _ in OCHIRILADI]
    assert tartib.index("signal_events") < tartib.index("signals")
    assert tartib.index("user_positions") < tartib.index("signals")
