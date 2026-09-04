"""Shamlarni keshga yuklaydi — o'lchov yuritmaydi.

Nima uchun ALOHIDA qadam. Ilgari yuklashni birinchi o'lchov
(backtest) qilardi, qolganlari esa `--offline` bilan yurardi. Bu
ikkita jimgina xatoni yaratdi:

  1. `olchov: sigim` kabi TANLANGAN o'lchov yuritilganda yuklash
     umuman bo'lmasdi va skript "kesh yo'q" bilan yiqilardi.
  2. Qisqa yugurish yarim keshni saqlab qo'ysa, keyingi yugurish
     "cache hit" olib, yetishmagan coinni HECH QACHON yuklamasdi.

Endi kesh to'ldirish HAR DOIM shu qadamda bo'ladi va o'lchovlar
faqat o'qiydi.

Ishlatish:
    python -m scripts.zanjir_yuklash --days 730 --symbols BTC,ETH
"""

from __future__ import annotations

import asyncio

from scripts.zanjir_umumiy import malumot_tayyorla, umumiy_argumentlar


async def main() -> None:
    argumentlar = umumiy_argumentlar(__doc__ or "").parse_args()
    symbols = [s.strip().upper() for s in argumentlar.symbols.split(",") if s.strip()]

    # HAR BIR COIN ALOHIDA yuklanadi. Sabab: ro'yxatda birjadan
    # olib tashlangan yoki nomi o'zgargan coin bo'lsa, umumiy
    # yuklash BIRINCHI xatoda to'xtardi va qolgan 20 tasi
    # yuklanmasdi. Bir soatlik yugurish shu bitta nom tufayli
    # behuda ketardi.
    #
    # Xato YASHIRILMAYDI: yiqilgan coinlar oxirida ro'yxat bilan
    # chiqadi va skript XATO KODI bilan tugaydi.
    yiqilgan: list[tuple[str, str]] = []
    hisobot: list[str] = []
    for symbol in symbols:
        argumentlar.symbols = symbol
        try:
            _, dataset, _ = await malumot_tayyorla(argumentlar)
        except Exception as xato:  # noqa: BLE001 — sabab chop etiladi
            yiqilgan.append((symbol, f"{type(xato).__name__}: {xato}"))
            print(f"  ❌ {symbol}: {type(xato).__name__}")
            continue
        seriya = dataset.series.get(symbol)
        qismlar = (
            ", ".join(f"{tf}={len(shamlar)}" for tf, shamlar in sorted(seriya.candles.items()))
            if seriya
            else "bo'sh"
        )
        hisobot.append(f"  {symbol:<6} {qismlar}")
        print(f"  ✅ {symbol}")

    print()
    print(f"Kesh tayyor: {len(hisobot)}/{len(symbols)} coin")
    print("\n".join(hisobot))

    if yiqilgan:
        print()
        print(f"❌ {len(yiqilgan)} ta coin yuklanmadi:")
        for symbol, sabab in yiqilgan:
            print(f"   {symbol:<6} {sabab}")
        print()
        print("   Bu coinlar o'lchovga KIRMAYDI. Ro'yxatni tuzating")
        print("   (`scripts/zanjir_umumiy.py`) va qaytadan yuriting.")
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
