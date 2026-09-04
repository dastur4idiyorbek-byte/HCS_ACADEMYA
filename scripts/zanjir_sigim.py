"""Portfel chegaralari zanjirdan NECHTASINI kesadi (2-prompt, 10-qism).

Zanjir backtesti ATAYLAB sig'imsiz o'lchanadi — u strategiyaning O'Z
sifatini ko'rsatishi kerak. Lekin jonli tizimda pul cheklangan:
`max_open_signals = 5` va bitta korrelyatsiya guruhidan bitta signal.

Eski loyihaning eng katta yo'qotishi aynan shu yerda edi: 4 668
nomzoddan 593 tasi o'tgan va sababning 87% i `max_open_signals`
bo'lgan (`OLCHOVLAR_XULOSASI.md`). Ya'ni strategiya emas, portfel
chegarasi natijani belgilagan — buni BILMASDAN qolish mumkin emas.

Bu skript ikkita bir xil yugurishni solishtiradi:

    sig'imsiz    zanjir nima berardi
    sig'im bilan real hisobda nima qoladi

Ishlatish:
    python -m scripts.zanjir_sigim --days 730 --offline
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
    risk = config.risk_engine

    variantlar = [
        ("sig'imsiz (zanjirning o'zi)", False),
        (
            f"sig'im bilan (max {risk.max_open_signals}, "
            f"guruhdan {risk.max_signals_per_correlation_group})",
            True,
        ),
    ]

    olchovlar = []
    natijalar = []
    for nom, sigim in variantlar:
        print(f"  ishlamoqda: {nom} ...")
        natija = ZanjirBacktest(config, nom, sigim=sigim).yur(
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

    yol = csv_saqla("zanjir_sigim.csv", olchovlar)
    print(f"Natija saqlandi: {yol}")
    _xulosa(olchovlar)


def _xulosa(olchovlar) -> None:  # noqa: ANN001
    """Sig'im NARXI — foizda emas, aniq raqamda."""
    ochiq, yopiq = olchovlar[0], olchovlar[1]
    if ochiq.signal == 0:
        print("\n⚠️ Sig'imsiz variantda ham savdo yo'q — solishtirish ma'nosiz.")
        return

    qoldi = yopiq.signal / ochiq.signal * 100
    print(f"\nSig'im {ochiq.signal} savdodan {yopiq.signal} tasini qoldirdi ({qoldi:.0f}%).")
    print(f"PF: {ochiq.profit_factor:.2f} → {yopiq.profit_factor:.2f}")

    if yopiq.signal < 30:
        print("⚠️ Sig'im bilan 30 tadan kam savdo qoldi — bu natijadan xulosa chiqarilmaydi.")
        return

    farq = yopiq.profit_factor - ochiq.profit_factor
    if farq >= 0.1:
        print("🟢 Sig'im natijani YAXSHILADI — kuchsiz nomzodlar kesilgan.")
    elif farq <= -0.1:
        print("🔴 Sig'im natijani YOMONLASHTIRDI. Bu — jiddiy belgi:")
        print("   o'rin cheklangani uchun eng yaxshi savdolar o'tkazib yuborilgan.")
        print("   Sabab voronkadagi qaysi chegara ko'proq to'sganidan ko'rinadi.")
    else:
        print("⚪ Sig'im PF ni sezilarli o'zgartirmadi — faqat savdo sonini kamaytirdi.")


if __name__ == "__main__":
    asyncio.run(main())
