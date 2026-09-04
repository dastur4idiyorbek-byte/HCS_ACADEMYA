"""Blok qoidasi: 4 tadan NECHTASI kerak (2026-09-04 savoli).

Zanjirning qoidasi: blok 0/4 bo'lsa uziladi, ya'ni bitta ijobiy
tekshiruv yetadi. 2026-09-04 ablatsiyasi bu qoidaning yon
ta'sirini ko'rsatdi: blok ichida tekshiruvlar VA emas, YOKI bo'lib
ishlaydi, va shuning uchun bitta tekshiruvni o'chirish natijani
deyarli o'zgartirmaydi.

Undan tabiiy savol chiqdi: "unda 2/4 qilsak-chi?"

BU SAVOLGA TAXMIN BILAN JAVOB BERILMAYDI. Yangi qoida — yangi
o'lchov. Skript aynan shuni qiladi va boshqa hech narsani
o'zgartirmaydi.

MUHIM: chegara MAXRAJDAN oshmaydi (`Blok.otdi`). Agar 4 tadan
faqat bittasi o'lchangan bo'lsa, "2 ta kerak" deyish ma'lumot
yo'qligini JAZOGA aylantirardi — bu `MALUMOT_YOQ` ning ma'nosiga
qarshi.

Ishlatish:
    python -m scripts.zanjir_blok_qoidasi --days 730 --offline
"""

from __future__ import annotations

import asyncio

from core.backtest.zanjir_engine import ZanjirBacktest
from scripts.zanjir_umumiy import (
    csv_saqla,
    jadval,
    malumot_tayyorla,
    olchov_qur,
    umumiy_argumentlar,
    voronka_matni,
)

#: Sinaladigan chegaralar. 4 — "hamma tekshiruv ijobiy bo'lsin"
#: degani va u deyarli hech qachon bo'lmaydi; u ATAYLAB bor —
#: qoidaning chekkasi qayerdaligini ko'rsatadi.
CHEGARALAR = (1, 2, 3, 4)


async def main() -> None:
    argumentlar = umumiy_argumentlar(__doc__ or "").parse_args()
    config, dataset, symbols = await malumot_tayyorla(argumentlar)

    olchovlar = []
    natijalar = []
    for chegara in CHEGARALAR:
        nom = f"blok qoidasi {chegara}/4" + (" (hozirgi)" if chegara == 1 else "")
        print(f"  ishlamoqda: {nom} ...")
        natija = ZanjirBacktest(config, nom, eng_kam_kuch=chegara).yur(
            dataset, symbols, argumentlar.max_steps
        )
        natijalar.append(natija)
        olchovlar.append(olchov_qur(natija))

    print()
    print(f"Coinlar: {', '.join(symbols)} | {argumentlar.days} kun")
    print()
    print(jadval(olchovlar))
    print()

    for natija in natijalar:
        print(f"📉 {natija.nom}: {natija.signal_soni} savdo")
        print(voronka_matni(natija))
        print()

    yol = csv_saqla("zanjir_blok_qoidasi.csv", olchovlar)
    print(f"Natija saqlandi: {yol}")
    _xulosa(olchovlar)


def _xulosa(olchovlar) -> None:  # noqa: ANN001
    """Xulosa FAQAT yetarli savdosi bor variantlar ichidan."""
    tayanch = olchovlar[0]
    print(f"\nHozirgi qoida (1/4): {tayanch.signal} savdo, PF {tayanch.profit_factor:.2f}")

    yetarli = [o for o in olchovlar if o.signal >= 100]
    kam = [o for o in olchovlar if o.signal < 100]
    if kam:
        print("\n⚠️ 100 tadan kam savdoli variantlar xulosaga KIRMAYDI:")
        for o in kam:
            print(f"   {o.nom}: {o.signal} savdo, PF {o.profit_factor:.2f}")

    if not yetarli:
        print("\n⚫ Hech bir variantda 100 ta savdo yo'q — xulosa chiqarilmaydi.")
        return

    eng = max(yetarli, key=lambda o: o.profit_factor)
    if eng is tayanch:
        print("\n🟢 Hozirgi qoida (1/4) eng yaxshisi — O'ZGARTIRILMAYDI.")
        return

    print(f"\n🟡 «{eng.nom}» PF {eng.profit_factor:.2f} — tayanchdan yuqori.")
    print(f"   Farq: {eng.profit_factor - tayanch.profit_factor:+.2f} PF, "
          f"{eng.signal - tayanch.signal:+d} savdo, "
          f"pasayish {tayanch.pasayish_pct:.1f}% → {eng.pasayish_pct:.1f}%")
    print("   BU HALI QAROR EMAS: bitta oynada topilgan natija")
    print("   walk-forward bilan IKKINCHI oynada tasdiqlanishi kerak.")


if __name__ == "__main__":
    asyncio.run(main())
