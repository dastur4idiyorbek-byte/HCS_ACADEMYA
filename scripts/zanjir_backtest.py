"""Yangi zanjirning BOSQICHMA-BOSQICH backtesti (2-prompt, 10-qism).

Promptdagi tartib: har bir blok qurilgandan keyin ALOHIDA o'lchash —
"qo'shilgan sari natija qanday o'zgarishini kuzatish".

Bu skript aynan shuni qiladi: zanjirni turli chuqurlikda yuritadi.

    faqat 1-2 blok    Fundamental + Struktura
    +3-blok           ... + Zona Sifati
    to'liq zanjir     ... + Tasdiqlash

Chuqurlik ABLATSIYA mexanizmi bilan amalga oshiriladi: keyingi
bloklarning barcha ichki tekshiruvlari o'chiriladi, ya'ni ular
`MALUMOT_YOQ` bo'lib qoladi va blok "o'lchanmadi" holatiga tushadi
— zanjirni UZMAYDI, lekin ishonchga ham ta'sir qilmaydi.

Ishlatish:
    python -m scripts.zanjir_backtest --days 730 --offline
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

#: Blok nomlari -> o'sha blokning barcha ichki tekshiruvlari
BLOK_TEKSHIRUVLARI = {
    "Fundamental": frozenset({"bozor_holati", "pul_oqimi", "katalizator", "kayfiyat"}),
    "Struktura": frozenset({
        "swing_ketma_ketligi", "bos_tasdiqlangan", "qarshi_choch_yoq",
        "nisbiy_kuch", "yangi_coin_naqshi",
    }),
    "Zona Sifati": frozenset({"fibonacci", "order_block", "fvg", "volume_profile"}),
    "Tasdiqlash": frozenset({
        "liquidity_sweep", "pastki_tf", "rsi_divergensiya", "fundamental_mos",
    }),
}


def _variantlar() -> list[tuple[str, frozenset[str]]]:
    """Zanjirning turli chuqurliklari."""
    zona = BLOK_TEKSHIRUVLARI["Zona Sifati"]
    tasdiq = BLOK_TEKSHIRUVLARI["Tasdiqlash"]
    return [
        ("to'liq zanjir (4 blok)", frozenset()),
        ("tasdiqlashsiz (3 blok)", tasdiq),
        ("faqat fundamental+struktura", zona | tasdiq),
    ]


async def main() -> None:
    argumentlar = umumiy_argumentlar(__doc__ or "").parse_args()
    config, dataset, symbols = await malumot_tayyorla(argumentlar)

    olchovlar = []
    natijalar = []
    for nom, ochirilgan in _variantlar():
        print(f"  ishlamoqda: {nom} ...")
        natija = ZanjirBacktest(config, nom, ochirilgan_tekshiruvlar=ochirilgan).yur(
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
        print(f"📉 {natija.nom}: {natija.qadamlar} qadam, {natija.signal_soni} savdo")
        print(voronka_matni(natija))
        print()

    yol = csv_saqla("zanjir_backtest.csv", olchovlar)
    print(f"Natija saqlandi: {yol}")
    _xulosa(olchovlar)


def _xulosa(olchovlar) -> None:  # noqa: ANN001
    """TO'XTASH QOIDASI (2-prompt, 8-qism, 5-band)."""
    yetarli = [o for o in olchovlar if o.signal >= 30]
    if not yetarli:
        print("\n⚠️ Hech bir variantda 30 ta savdo ham yo'q — xulosa chiqarib bo'lmaydi.")
        print("   Zanjir juda qattiq: voronkaga qarab qaysi blok to'sayotganini toping.")
        return

    eng = max(yetarli, key=lambda o: o.profit_factor)
    if eng.profit_factor >= 1.0:
        print(f"\n🟢 «{eng.nom}» PF {eng.profit_factor:.2f} — 1.0 dan yuqori.")
        print("   KEYINGI QADAM: walk-forward bilan IKKINCHI oynada takrorlash.")
    else:
        print(f"\n⚫ Eng yaxshi PF {eng.profit_factor:.2f} («{eng.nom}») — 1.0 dan past.")
        print("   TO'XTASH QOIDASI: natija admin bilan muhokama qilinadi,")
        print("   keyingi qadam BIRGA hal qilinadi (2-prompt, 8-qism, 5-band).")


if __name__ == "__main__":
    asyncio.run(main())
