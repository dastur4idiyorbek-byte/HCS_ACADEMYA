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
    _, dataset, symbols = await malumot_tayyorla(argumentlar)

    print(f"Kesh tayyor: {len(symbols)} coin")
    for symbol in sorted(dataset.series):
        seriya = dataset.series[symbol]
        qismlar = ", ".join(
            f"{tf}={len(shamlar)}" for tf, shamlar in sorted(seriya.candles.items())
        )
        print(f"  {symbol:<6} {qismlar}")


if __name__ == "__main__":
    asyncio.run(main())
