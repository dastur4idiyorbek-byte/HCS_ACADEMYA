"""Eski tahlil moduli qoldirgan MA'LUMOTNI tozalaydi.

Kod 2026-09-03 da o'chirilgan edi (`docs/OCHIRISH_ROYXATI.md`),
lekin BAZADAGI ma'lumot qolgan: eski modul bergan signallar,
ularning statistikasi, voronka qaydlari va salomatlik jurnali.

Nima uchun bu ma'lumot ZARARLI:

  1. Sayt va bot statistikani BAZADAN o'qiydi. Eski signallar
     turgan ekan, foydalanuvchi YANGI modulning natijasi deb
     ESKI modulning raqamlarini ko'radi.
  2. Eski modul boshqa mantiq bilan ishlagan. Uning natijasini
     yangisiga qo'shib hisoblash — ikki boshqa mahsulotning
     raqamini aralashtirish.

XAVFSIZLIK: skript sukut bo'yicha HECH NARSA O'CHIRMAYDI. U
faqat sanaydi va ko'rsatadi. O'chirish uchun `--tasdiqla`
kerak.

Ishlatish:
    python -m scripts.eski_malumot_tozalash              # faqat ko'rsatadi
    python -m scripts.eski_malumot_tozalash --tasdiqla   # o'chiradi
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import delete, func, select

from core.storage.database import Database
from core.storage.models import (
    AuditReport,
    DailyStat,
    MarketHealthLog,
    PipelineEventRecord,
    RiskBlock,
    SignalEvent,
    SignalRecord,
    UserPosition,
)

#: O'CHIRILADIGAN jadvallar — hammasi eski tahlil modulining
#: chiqishi. Tartib MUHIM: bolalar avval, ota-ona keyin.
OCHIRILADI = [
    (SignalEvent, "signal_events", "signal hodisalari (TP/Stop qaydlari)"),
    (UserPosition, "user_positions", "foydalanuvchi pozitsiyalari (eski signallarga bog'liq)"),
    (SignalRecord, "signals", "ESKI MODUL BERGAN SIGNALLAR"),
    (PipelineEventRecord, "pipeline_events", "Jonli Oshxona voronkasi"),
    (RiskBlock, "risk_blocks", "Risk Engine rad etishlari"),
    (DailyStat, "daily_stats", "kunlik statistika"),
    (MarketHealthLog, "market_health_log", "Bozor Salomatligi jurnali"),
    (AuditReport, "audit_reports", "haftalik audit hisobotlari"),
]

#: TEGILMAYDIGAN jadvallar. Bu ro'yxat hujjat vazifasini ham
#: bajaradi: kimdir keyinchalik "buni ham o'chiraylikmi?" desa,
#: javob shu yerda.
SAQLANADI = [
    ("users", "foydalanuvchilar"),
    ("subscriptions", "obunalar"),
    ("payments", "to'lovlar va cheklar"),
    ("price_config", "narxlar"),
    ("content", "kontent, darsliklar"),
    ("violations", "qoidabuzarliklar"),
    ("coin_rulings", "HALOL/HAROM hukmlari — qayta yig'ish qimmat"),
    ("halal_universe_snapshots", "halol skrining tarixi"),
    ("risk_config", "sozlamalar (ma'lumot emas)"),
    ("social_links", "ijtimoiy tarmoqlar"),
    ("bozor_kesimlari", "sayt uchun bozor ko'rinishi — tahlil moduliga bog'liq EMAS"),
    ("bozor_korinishlari", "sayt uchun haftalik/kunlik ko'rinish"),
]


async def sanoq(db: Database) -> list[tuple[str, str, int]]:
    natija = []
    async with db.session() as session:
        for model, jadval, izoh in OCHIRILADI:
            soni = await session.scalar(select(func.count()).select_from(model))
            natija.append((jadval, izoh, int(soni or 0)))
    return natija


async def ochir(db: Database) -> list[tuple[str, int]]:
    ochirildi = []
    async with db.session() as session:
        for model, jadval, _ in OCHIRILADI:
            natija = await session.execute(delete(model))
            ochirildi.append((jadval, natija.rowcount or 0))
    return ochirildi


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tasdiqla",
        action="store_true",
        help="HAQIQATAN o'chirish. Ansiz skript faqat ko'rsatadi.",
    )
    argumentlar = parser.parse_args()

    db = Database()
    qatorlar = await sanoq(db)
    jami = sum(soni for _, _, soni in qatorlar)

    print("O'CHIRILADIGAN MA'LUMOT (eski tahlil moduli qoldirgan):")
    print()
    for jadval, izoh, soni in qatorlar:
        belgi = "  " if soni else "· "
        print(f"  {belgi}{jadval:<22}{soni:>8} qator   — {izoh}")
    print()
    print(f"  JAMI: {jami} qator")
    print()
    print("SAQLANADI (tegilmaydi):")
    for jadval, izoh in SAQLANADI:
        print(f"     {jadval:<26} — {izoh}")
    print()

    if not jami:
        print("🟢 O'chiradigan narsa yo'q — baza allaqachon toza.")
        return

    if not argumentlar.tasdiqla:
        print("⚠️ HECH NARSA O'CHIRILMADI.")
        print("   Yuqoridagi ro'yxatni tekshiring. Rozi bo'lsangiz:")
        print("      python -m scripts.eski_malumot_tozalash --tasdiqla")
        return

    print("O'chirilmoqda ...")
    for jadval, soni in await ochir(db):
        print(f"   {jadval:<22} {soni:>8} qator o'chirildi")
    print()
    print("🟢 Tayyor. Endi sayt va bot statistikasi BO'SH ko'rsatadi —")
    print("   bu to'g'ri: yangi modul hali jonli signal bermagan.")


if __name__ == "__main__":
    asyncio.run(main())
