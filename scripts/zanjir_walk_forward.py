"""WALK-FORWARD — natija VAQT O'TISHI bilan saqlanadimi.

2-prompt, 8-qism, 4-band: "kamida 2 ta kesishmaydigan oyna", "PF
vaqt o'tishi bilan pasayib ketmasligi tekshiriladi".

NIMA UCHUN BU HAL QILUVCHI. Eski tizimda aynan shu o'lchov eng
achchiq javobni bergan edi: PF 1.00 -> 0.84 -> 0.69 (vaqt bo'yicha).
Ya'ni "yaxshi" ko'ringan sozlama o'tmishga moslashgan, kelajakka
emas (`OLCHOVLAR_XULOSASI.md` #13).

USUL: butun tarix N ta teng bo'lakka bo'linadi va har bo'lakda
zanjir ALOHIDA o'lchanadi. Bo'laklar KESISHMAYDI — bitta savdo
ikki bo'lakka tushmaydi.

Ishlatish:
    python -m scripts.zanjir_walk_forward --days 730 --bolaklar 3 --offline
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

from core.backtest.zanjir_engine import ZanjirBacktest
from scripts.zanjir_umumiy import (
    csv_saqla,
    jadval,
    malumot_tayyorla,
    olchov_qur,
    umumiy_argumentlar,
)

#: Bo'lakda shundan kam savdo bo'lsa — xulosa chiqarilmaydi
ENG_KAM_SAVDO = 10


@dataclass(frozen=True, slots=True)
class Bolak:
    nom: str
    boshi: datetime
    oxiri: datetime


def bolaklar(vaqtlar: list[datetime], soni: int) -> list[Bolak]:
    """Vaqt o'qini teng, KESISHMAYDIGAN bo'laklarga bo'ladi."""
    if len(vaqtlar) < soni * 2:
        return []
    kenglik = len(vaqtlar) // soni
    natija = []
    for i in range(soni):
        boshi = i * kenglik
        oxiri = (i + 1) * kenglik - 1 if i < soni - 1 else len(vaqtlar) - 1
        natija.append(
            Bolak(
                nom=f"oyna {i + 1}: {vaqtlar[boshi]:%Y-%m} → {vaqtlar[oxiri]:%Y-%m}",
                boshi=vaqtlar[boshi],
                oxiri=vaqtlar[oxiri],
            )
        )
    return natija


async def main() -> None:
    parser = umumiy_argumentlar(__doc__ or "")
    parser.add_argument("--bolaklar", type=int, default=3)
    argumentlar = parser.parse_args()

    config, dataset, symbols = await malumot_tayyorla(argumentlar)
    asosiy_tf = config.zanjir.timeframelar.asosiy
    vaqtlar = dataset.timeline(asosiy_tf)

    qismlar = bolaklar(vaqtlar, argumentlar.bolaklar)
    if not qismlar:
        print("⚠️ Ma'lumot bo'laklarga bo'linishga yetmaydi.")
        return

    olchovlar = []
    for bolak in qismlar:
        print(f"  ishlamoqda: {bolak.nom} ...")
        kesilgan = _kesim(dataset, bolak, asosiy_tf)
        natija = ZanjirBacktest(config, bolak.nom).yur(kesilgan, symbols)
        olchovlar.append(olchov_qur(natija))

    print()
    print(jadval(olchovlar))
    print()
    yol = csv_saqla("zanjir_walk_forward.csv", olchovlar)
    print(f"Natija saqlandi: {yol}")
    _xulosa(olchovlar)


def _kesim(dataset, bolak: Bolak, asosiy_tf: str):  # noqa: ANN001, ANN202
    """Bo'lak oynasi + undan OLDINGI isinish tarixi.

    Isinish KESILMAYDI: struktura va POC uchun oldingi shamlar
    kerak. Lekin SAVDO faqat bo'lak ichida ochiladi, chunki
    `ZanjirBacktest` timeline ni datasetdan oladi va u kesilgan.
    """
    from core.backtest.dataset import Dataset

    yangi = Dataset()
    for symbol, seriya in dataset.series.items():
        for tf, shamlar in seriya.candles.items():
            # Asosiy TF da faqat bo'lak oynasi; boshqalarida
            # bo'lak oxirigacha bo'lgan hamma narsa (isinish).
            if tf == asosiy_tf:
                kesim = [c for c in shamlar if bolak.boshi <= c.open_time <= bolak.oxiri]
            else:
                kesim = [c for c in shamlar if c.open_time <= bolak.oxiri]
            if kesim:
                yangi.add(symbol, tf, kesim)
    return yangi


def _xulosa(olchovlar) -> None:  # noqa: ANN001
    ishonchli = [o for o in olchovlar if o.signal >= ENG_KAM_SAVDO]
    if len(ishonchli) < 2:
        print(f"\n⚠️ Kamida 2 ta oynada {ENG_KAM_SAVDO} savdo kerak — xulosa yo'q.")
        return

    pflar = [o.profit_factor for o in ishonchli]
    print(f"\nPF vaqt bo'yicha: {' → '.join(f'{p:.2f}' for p in pflar)}")

    if pflar[-1] < pflar[0] - 0.1:
        print("🔴 PF VAQT BILAN PASAYADI — sozlama o'tmishga moslashgan.")
        print("   Bu eski tizimni o'ldirgan naqsh (1.00 → 0.84 → 0.69).")
    elif all(p >= 1.0 for p in pflar):
        print("🟢 Barcha oynada PF ≥ 1.0 — natija VAQT BO'YICHA SAQLANDI.")
    else:
        print("⚫ PF barqaror, lekin 1.0 dan past — foyda yo'q.")


if __name__ == "__main__":
    asyncio.run(main())
