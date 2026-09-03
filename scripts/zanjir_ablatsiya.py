"""ABLATSIYA — 16 ta ichki tekshiruvni BIRMA-BIR o'chirib sinaydi.

2-prompt, 8-qism, 3-band:

    "agar biror ichki tekshiruv natijaga TA'SIR QILMASA (masalan PF
    0.00-0.03 farq qilsa) — U OLIB TASHLANADI, murakkablik
    saqlanmaydi"

NIMA UCHUN BU ENG MUHIM SKRIPT. Eski tizimda aynan shu o'lchov
100 balldan 60 tasi hech nima qilmayotganini ko'rsatgan edi
(`OLCHOVLAR_XULOSASI.md` #13). Agar biz o'sha o'lchovni bir oy
oldinroq qilganimizda, oyning yarmi tejalardi.

O'CHIRISH USULI: tekshiruv `MALUMOT_YOQ` ga aylantiriladi, ya'ni
blok MAXRAJIDAN chiqadi. Vaznni nolga tushirish EMAS — u blokni
sun'iy zaiflashtirardi va biz "tekshiruv yomon" degan yolg'on
xulosa chiqarardik.

Ishlatish:
    python -m scripts.zanjir_ablatsiya --days 730 --offline
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
)

#: 16 ta ichki tekshiruv, blok bo'yicha guruhlangan.
#: `yangi_coin_naqshi` 17-chi — u faqat yangi coinlarda ishlaydi.
TEKSHIRUVLAR = [
    ("1.1 bozor holati", "bozor_holati"),
    ("1.2 pul oqimi", "pul_oqimi"),
    ("1.3 katalizator", "katalizator"),
    ("1.4 kayfiyat", "kayfiyat"),
    ("2.1 swing ketma-ketligi", "swing_ketma_ketligi"),
    ("2.2 BOS tasdiqlangan", "bos_tasdiqlangan"),
    ("2.3 qarshi CHOCH yo'q", "qarshi_choch_yoq"),
    ("2.4 nisbiy kuch", "nisbiy_kuch"),
    ("3.1 fibonacci", "fibonacci"),
    ("3.2 order block", "order_block"),
    ("3.3 FVG", "fvg"),
    ("3.4 volume profile", "volume_profile"),
    ("4.1 liquidity sweep", "liquidity_sweep"),
    ("4.2 pastki TF", "pastki_tf"),
    ("4.3 RSI/divergensiya", "rsi_divergensiya"),
    ("4.4 fundamental mos", "fundamental_mos"),
]

#: PF farqi shundan kichik bo'lsa — tekshiruv HISSA QO'SHMAYDI.
#: Promptdagi "0.00-0.03" chegarasi.
SEZILARSIZ = 0.03


async def main() -> None:
    argumentlar = umumiy_argumentlar(__doc__ or "").parse_args()
    config, dataset, symbols = await malumot_tayyorla(argumentlar)

    print("  ishlamoqda: TAYANCH (hammasi yoqilgan) ...")
    tayanch = ZanjirBacktest(config, "TAYANCH").yur(dataset, symbols, argumentlar.max_steps)
    olchovlar = [olchov_qur(tayanch)]

    for nom, kalit in TEKSHIRUVLAR:
        print(f"  ishlamoqda: {nom} o'chirilgan ...")
        natija = ZanjirBacktest(
            config, f"— {nom}", ochirilgan_tekshiruvlar=frozenset({kalit})
        ).yur(dataset, symbols, argumentlar.max_steps)
        olchovlar.append(olchov_qur(natija))

    print()
    print(jadval(olchovlar))
    print()
    yol = csv_saqla("zanjir_ablatsiya.csv", olchovlar)
    print(f"Natija saqlandi: {yol}")
    _xulosa(olchovlar[0], olchovlar[1:])


def _xulosa(tayanch, variantlar) -> None:  # noqa: ANN001
    """Qaysi tekshiruvlar hissa qo'shmaydi — ular OLIB TASHLANADI."""
    if tayanch.signal < 30:
        print("\n⚠️ Tayanchda 30 ta savdo ham yo'q — ablatsiya xulosasi ishonchsiz.")
        return

    hissasiz = []
    foydali = []
    for o in variantlar:
        farq = o.profit_factor - tayanch.profit_factor
        if abs(farq) < SEZILARSIZ:
            hissasiz.append((o.nom, farq))
        elif farq < 0:
            foydali.append((o.nom, farq))

    print(f"\nTayanch PF: {tayanch.profit_factor:.2f} ({tayanch.signal} savdo)")

    if foydali:
        print("\n🟢 HISSA QO'SHADI (o'chirilsa PF pasayadi):")
        for nom, farq in sorted(foydali, key=lambda x: x[1]):
            print(f"   {nom:<28} PF {farq:+.2f}")

    if hissasiz:
        print(f"\n⚫ HISSA QO'SHMAYDI (|ΔPF| < {SEZILARSIZ}) — OLIB TASHLANADI:")
        for nom, farq in hissasiz:
            print(f"   {nom:<28} PF {farq:+.2f}")
        print("\n   2-prompt, 8-qism, 3-band: murakkablik saqlanmaydi.")


if __name__ == "__main__":
    asyncio.run(main())
