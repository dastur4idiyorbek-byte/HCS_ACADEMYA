"""Alternativ zanjirni tarixiy ma'lumotda o'lchash.

Asosiy `zanjir_backtest.py` bilan solishtirish uchun: bu yerda
`zanjir_yur_alternativ` ishlatiladi — zaif (1/N) blok alternativ
yo'llar bilan qutqariladi (2A trend+flag, 2B qo'sh tub, 3A qo'sh
tub zona, 3B oldingi swing, 4A hajm, 4B tezlik, 4C retest).

Ikkala zanjir bir xil ma'lumotda yuritilib, natijalari yonma-yon
solishtiriladi. Bu skript o'lchov skripti — strategiyani
o'zgartirmaydi.

Ishlatish:
    python -m scripts.zanjir_alternativ --days 730 --offline

Ikkita variant yonma-yon o'lchanadi: "TP1 joriy narxdan yuqorimi"
qoidasi BILAN (jonli tizim) va YO'Q (solishtirish uchun).
    python -m scripts.zanjir_alternativ --days 365 --symbols BTC,ETH,SOL
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


async def main() -> None:
    argumentlar = umumiy_argumentlar(__doc__ or "").parse_args()
    config, dataset, symbols = await malumot_tayyorla(argumentlar)

    # IKKI VARIANT YONMA-YON — 2026-09-10.
    #
    # "TP1 joriy narxdan yuqorimi" qoidasi qo'shilganda savdo soni
    # keskin kamaydi. Qoida sababmi yoki boshqa narsami — buni
    # TAXMIN qilib bo'lmaydi, o'lchash kerak. Ikkalasi bitta
    # yugurishda, bitta ma'lumotda o'lchanadi: farq faqat shu
    # qoidadan bo'ladi.
    #
    # "qoidasiz" varianti JONLI TIZIM EMAS — u faqat solishtirish
    # uchun. Jonli sikl doim qoida bilan ishlaydi.
    print("  ishlamoqda: alternativ zanjir — nishon qoidasi BILAN ...")
    yangi_natija = ZanjirBacktest(
        config, "nishon qoidasi BILAN", alternativ=True
    ).yur(dataset, symbols, argumentlar.max_steps)

    print("  ishlamoqda: alternativ zanjir — nishon qoidasi YO'Q ...")
    eski_natija = ZanjirBacktest(
        config, "nishon qoidasi YO'Q", alternativ=True, nishon_tekshiruvi=False
    ).yur(dataset, symbols, argumentlar.max_steps)

    olchovlar = [olchov_qur(eski_natija), olchov_qur(yangi_natija)]

    print()
    print(f"Coinlar: {', '.join(symbols)} | {argumentlar.days} kun")
    print()
    print(jadval(olchovlar))
    print()
    for natija in (eski_natija, yangi_natija):
        print(f"{natija.nom}: {natija.qadamlar} qadam, {natija.signal_soni} savdo")
        print(voronka_matni(natija))
        print()
    natija = yangi_natija

    yol = csv_saqla("zanjir_alternativ.csv", olchovlar)
    print(f"Natija saqlandi: {yol}")


if __name__ == "__main__":
    asyncio.run(main())
