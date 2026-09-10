"""Daraja CHEGARALARINI o'lchaydi — taxminiy raqamlarni almashtiradi.

NIMA UCHUN BU SKRIPT BOR (2-prompt, 0-qism, 3-tamoyil):

    "Har qanday raqamli chegara (masalan 'min 3% stop') — backtest
    orqali TOPILADI, tasodifiy tanlanmaydi."

Birinchi yugurish aynan shu tamoyilning buzilganini ko'rsatdi.
To'liq zanjir 730 kunda atigi 35 savdo berdi, va voronka sababni
aniq ko'rsatdi:

    1512 × stop juda yaqin                  <- ENG KATTA to'siq
     780 × narx zonadan pastga tushgan
     371 × TP1/Stop nisbati past
       8 × stop juda uzoq

Ya'ni zanjir TO'LIQ BOG'LANGAN holatlarning yarmidan ko'pi
`stop_eng_kam_pct = 3.0` sababli tashlanardi. O'sha 3.0 — men
qo'ygan taxminiy raqam, o'lchov emas.

BU SKRIPT FAQAT `darajalar` BLOKINI O'ZGARTIRADI. Boshqa hech narsa
— na bloklar, na chiqish rejasi — tegilmaydi. Aks holda o'lchov
o'z natijasini yasagan bo'lardi.

Ishlatish:
    python -m scripts.zanjir_chegara --days 730 --offline
"""

from __future__ import annotations

import asyncio
import dataclasses

from core.backtest.zanjir_engine import ZanjirBacktest
from scripts.zanjir_umumiy import (
    csv_saqla,
    jadval,
    malumot_tayyorla,
    olchov_qur,
    umumiy_argumentlar,
    voronka_matni,
)

#: Sinaladigan `stop_eng_kam_pct` qiymatlari.
#:
#: 3.0 — hozirgi (taxminiy) qiymat, tayanch sifatida qoladi.
#: Pastroq qiymatlar: zona tor bo'lsa ham savdoga ruxsat beriladi.
#: Bu XAVFLI tomon — juda yaqin Stop shovqin ichida qoladi va tez
#: yeyiladi. Aynan shuning uchun o'lchanadi, taxmin qilinmaydi.
STOP_CHEGARALARI = [0.5, 1.0, 1.5, 2.0, 3.0]

#: Sinaladigan `tp1_eng_kam_nisbat` qiymatlari.
#:
#: Eski tizimda bu YAGONA ishlagan richag edi (PF 0.30 -> 0.84,
#: `OLCHOVLAR_XULOSASI.md` #8). Uning yangi tizimdagi eng yaxshi
#: qiymati boshqa bo'lishi mumkin — eski raqamni ko'chirib yozish
#: "o'lchandi" degani emas.
#: 2.5 va 3.0 — 2026-09-10 da QO'SHILDI.
#:
#: Sabab MATEMATIK. O'lchovda g'alaba foizi hamma variantda
#: 33-38% chiqdi. 1.2 nisbatda nolga chiqish uchun ~45% kerak,
#: ya'ni 35% bilan tizim yutqazishi SHART. Yuqori nisbat esa
#: past g'alaba foizini qoplashi mumkin — yoki savdoni umuman
#: yo'q qilishi mumkin. Qaysi biri — o'lchanadi.
NISBAT_CHEGARALARI = [1.0, 1.2, 1.5, 2.0, 2.5, 3.0]


def _variantlar(config):  # noqa: ANN001, ANN202
    """Bitta o'lchovda BITTA raqam o'zgaradi.

    Ikkalasini birga surish "qaysi biri ta'sir qildi" savolini
    javobsiz qoldirardi — bu eski tizimda bir necha marta bo'lgan.
    """
    asos = config.zanjir.darajalar
    # Yorliq CONFIG DAN o'qiladi, qo'lda yozilmaydi. Ilgari u
    # "stop 3.0" deb qotib qolgan edi va config 1.5 ga o'zgargach
    # jadval YOLG'ON gapira boshladi — o'lchov o'zi haqida noto'g'ri
    # ma'lumot bergani eng yomon xato turi.
    variantlar = [
        (
            f"TAYANCH (stop {asos.stop_eng_kam_pct}, nisbat {asos.tp1_eng_kam_nisbat})",
            config,
        )
    ]

    for qiymat in STOP_CHEGARALARI:
        if qiymat == asos.stop_eng_kam_pct:
            continue
        variantlar.append((f"stop eng kam {qiymat}%", _daraja(config, stop_eng_kam_pct=qiymat)))

    for qiymat in NISBAT_CHEGARALARI:
        if qiymat == asos.tp1_eng_kam_nisbat:
            continue
        variantlar.append(
            (f"TP1/Stop nisbat {qiymat}", _daraja(config, tp1_eng_kam_nisbat=qiymat))
        )

    return variantlar


def _daraja(config, **ozgarishlar):  # noqa: ANN001, ANN202
    """FAQAT `zanjir.darajalar` bloki o'zgargan nusxa."""
    yangi_darajalar = dataclasses.replace(config.zanjir.darajalar, **ozgarishlar)
    return dataclasses.replace(
        config,
        zanjir=dataclasses.replace(config.zanjir, darajalar=yangi_darajalar),
    )


async def main() -> None:
    argumentlar = umumiy_argumentlar(__doc__ or "").parse_args()
    config, dataset, symbols = await malumot_tayyorla(argumentlar)

    olchovlar = []
    natijalar = []
    for nom, variant in _variantlar(config):
        print(f"  ishlamoqda: {nom} ...")
        # `alternativ=True` — JONLI TIZIM aynan shu zanjirni yuritadi
        # (`core/services/zanjir_sikl.py` -> `zanjir_yur_alternativ`).
        #
        # 2026-09-10 gacha bu yerda ASOSIY zanjir o'lchanardi. Ya'ni
        # "eng yaxshi chegara qaysi" degan savolga berilgan javob
        # jonli tizimga TEGISHLI EMAS edi — boshqa zanjirning
        # chegarasi topilardi. O'lchangan farq katta: asosiy zanjir
        # PF 0.83, alternativ 1.03 (730 kun, 12 coin).
        natija = ZanjirBacktest(variant, nom, alternativ=True).yur(
            dataset, symbols, argumentlar.max_steps
        )
        natijalar.append(natija)
        olchovlar.append(olchov_qur(natija))

    print()
    print(f"Coinlar: {', '.join(symbols)} | {argumentlar.days} kun")
    print()
    print(jadval(olchovlar))
    print()
    print("Tayanch voronkasi (nima to'sayotganini ko'rish uchun):")
    print(voronka_matni(natijalar[0]))
    print()

    yol = csv_saqla("zanjir_chegara.csv", olchovlar)
    print(f"Natija saqlandi: {yol}")
    _xulosa(olchovlar)


#: Xulosa uchun kerakli minimal savdo — to'xtash qoidasidan.
ISHONCHLI_SAVDO = 100


def _xulosa(olchovlar) -> None:  # noqa: ANN001
    """Chegarani o'zgartirish signal sonini VA sifatini qanday o'zgartirdi."""
    tayanch = olchovlar[0]
    print(f"\nTayanch: {tayanch.signal} savdo, PF {tayanch.profit_factor:.2f}")

    yetarli = [o for o in olchovlar if o.signal >= ISHONCHLI_SAVDO]
    if not yetarli:
        eng_kop = max(olchovlar, key=lambda o: o.signal)
        print(f"\n🔴 Hech bir variant {ISHONCHLI_SAVDO} savdoga yetmadi.")
        print(f"   Eng ko'pi: «{eng_kop.nom}» — {eng_kop.signal} savdo, "
              f"PF {eng_kop.profit_factor:.2f}")
        print("\n   Bu shuni bildiradi: muammo FAQAT chegarada emas.")
        print("   Voronkaga qarang — zanjir qayerda uzilyapti.")
        return

    eng = max(yetarli, key=lambda o: o.profit_factor)
    print(f"\n{ISHONCHLI_SAVDO}+ savdoli variantlar ichida eng yaxshisi:")
    print(f"   «{eng.nom}» — {eng.signal} savdo, PF {eng.profit_factor:.2f}")
    if eng.profit_factor >= 1.0:
        print("\n🟢 KEYINGI QADAM: walk-forward bilan shu chegarada takrorlash.")
    else:
        print("\n⚫ Savdo yetarli, lekin PF 1.0 dan past — TO'XTASH QOIDASI.")


if __name__ == "__main__":
    asyncio.run(main())
