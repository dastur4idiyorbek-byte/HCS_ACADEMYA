"""ZAIFLIK HISOBOTI — blokning qaysi qismi ishlamayapti.

Bu skript ABLATSIYADAN BOSHQA savolga javob beradi va ikkisi
aralashtirilmasligi kerak:

    ablatsiya:  "bu tekshiruvni olib tashlasak natija o'zgaradimi?"
    zaiflik:    "bu tekshiruv qanchalik tez-tez ijobiy chiqadi?"

Nima uchun ikkinchisi kerak. Blok 4 tadan BITTASI bilan o'tadi.
Demak doim YO'Q chiqadigan tekshiruv blokni hech qachon
o'tkazmaydi — u bor, lekin o'lik halqa. Ablatsiya buni ko'rsata
olmaydi (uni o'chirsang ham hech narsa o'zgarmaydi, chunki u
allaqachon hech narsa qilmayapti).

Modulning asl g'oyasi shu edi: katta blokni to'rtga bo'lish —
qaysi biri zaif ekanini KO'RISH uchun. Bu skript o'sha ko'rishni
beradi.

UCHTA USTUN, uchtasi boshqa ma'noda:

    HA              tekshiruv ijobiy chiqdi
    YO'Q            tekshiruv salbiy chiqdi
    ma'lumot yo'q   tekshiruv UMUMAN o'lchanmadi (manba yo'q)

Oxirgisi "yomon" degani EMAS. Masalan backtestda fundamental
bloknining hamma manbasi bo'sh — shuning uchun uning to'rt
tekshiruvi 100% "ma'lumot yo'q" chiqadi. Bu ularning yomonligi
emas, sinalmaganligi.

Ishlatish:
    python -m scripts.zanjir_zaiflik --days 730 --offline
"""

from __future__ import annotations

import asyncio

from core.backtest.zanjir_engine import ZanjirBacktest
from scripts.zanjir_umumiy import (
    jadval,
    malumot_tayyorla,
    olchov_qur,
    umumiy_argumentlar,
    voronka_matni,
    zaiflik_matni,
)


async def main() -> None:
    argumentlar = umumiy_argumentlar(__doc__ or "").parse_args()
    config, dataset, symbols = await malumot_tayyorla(argumentlar)

    print("  ishlamoqda: zaiflik hisoboti ...")
    natija = ZanjirBacktest(config, "zaiflik").yur(dataset, symbols, argumentlar.max_steps)

    print()
    print(f"Coinlar: {', '.join(symbols)} | {argumentlar.days} kun")
    print()
    print(jadval([olchov_qur(natija)]))
    print()
    print(zaiflik_matni(natija))
    print()
    print(voronka_matni(natija))
    print()
    _xulosa(natija)


def _xulosa(natija) -> None:  # noqa: ANN001
    olchanmagan = []
    zaif = []
    for nom, hisob in natija.tekshiruv_holatlari.items():
        olchandi = hisob["ha"] + hisob["yoq"]
        if not olchandi:
            olchanmagan.append(nom)
        elif hisob["ha"] / olchandi < 0.10:
            zaif.append((nom, hisob["ha"] / olchandi))

    if olchanmagan:
        print("⚫ UMUMAN O'LCHANMAGAN (manba yo'q — yomon emas, SINALMAGAN):")
        for nom in sorted(olchanmagan):
            print(f"   {nom}")
        print("   Bular haqida backtest HECH NARSA ayta olmaydi.")
        print()

    if zaif:
        print("⚠️ ZAIF HALQALAR (10% dan kam ijobiy):")
        for nom, ulush in sorted(zaif, key=lambda x: x[1]):
            print(f"   {nom:<22} {ulush * 100:.1f}% ijobiy")
        print()
        print("   Blok 4 tadan bittasi bilan o'tadi, ya'ni bu tekshiruvlar")
        print("   blokni deyarli hech qachon O'TKAZMAYDI. Ikki yo'l bor:")
        print("     1) mantiqini kuchaytirish (nega doim YO'Q chiqyapti?)")
        print("     2) chegarasini bo'shatish")
        print("   Ikkalasi ham O'ZGARISH — ya'ni backtestsiz qilinmaydi.")
        return

    if not olchanmagan:
        print("🟢 Zaif halqa topilmadi — har bir tekshiruv muntazam ijobiy chiqadi.")


if __name__ == "__main__":
    asyncio.run(main())
