"""ABLATION — har bir ball omilining haqiqiy hissasi.

    python -m scripts.ablation_test --days 730
    python -m scripts.ablation_test --days 730 --offline

SAVOL. Ball tizimida oltita omil bor va ularning vaznlari (25/20/15/15/
10/15) o'ylab qo'yilgan, o'lchab emas. Har biri natijaga QANCHA hissa
qo'shadi? Bittasini olib tashlaganda nima o'zgaradi?

USUL. Har bir omil navbat bilan chiqariladi va to'liq backtest qaytadan
ishga tushadi. Ikki xil chiqarish bor va ular BOSHQA-BOSHQA savolga
javob beradi:

    "nol"          vazn 0 ga qo'yiladi, qolganlari o'zgarmaydi.
                   Umumiy shkala 100 dan pasayadi, ya'ni chegaradan
                   o'tish qiyinlashadi. Bu "omil YO'Q bo'lsa" holati.

    "qayta taqsim" vazn 0 ga qo'yiladi va uning ulushi qolgan
                   omillarga nisbatiga qarab bo'linadi. Shkala 100
                   bo'lib qoladi, chegara ham o'sha. Bu "omilning
                   MA'LUMOTI yo'q bo'lsa" holati — sof ablation.

Ikkalasi kerak: birinchisi signal SONIGA ta'sirni ko'rsatadi,
ikkinchisi omil ma'lumotining o'zi foydalimi yoki yo'qmi.

NIMA O'ZGARMAYDI. Ball hisoblash mantig'i, chegaralar, strategiyalar,
risk qoidalari va yo'l xarajati (komissiya + slippage) — hammasi
joyida. Bu skript faqat vaznlarni vaqtincha almashtirib O'LCHAYDI,
`config/default.yaml` ga hech narsa yozmaydi.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses

from core.backtest import Backtester
from core.config import AppConfig
from core.config.schema import ScoreWeights
from scripts.sinov_umumiy import (
    Olchov,
    csv_saqla,
    jadval,
    malumot_tayyorla,
    matn_saqla,
    olchov_qur,
    umumiy_argumentlar,
)

#: Ball omillari — `ScoreWeights` maydoni -> o'zbekcha nomi.
#: Tartib `config/default.yaml` dagi vaznlar tartibi bilan bir xil.
OMILLAR: dict[str, str] = {
    "support_resistance": "S/R zonasi",
    "trend": "Trend",
    "rsi": "RSI",
    "volume": "Hajm",
    "macd": "MACD",
    "risk_reward": "Risk/Reward",
}


def _vaznlar_bilan(config: AppConfig, vaznlar: ScoreWeights) -> AppConfig:
    return dataclasses.replace(
        config, scoring=dataclasses.replace(config.scoring, weights=vaznlar)
    )


def _nolga(vaznlar: ScoreWeights, omil: str) -> ScoreWeights:
    """Omil vazni 0 — qolganlari o'zgarmaydi (shkala pasayadi)."""
    return dataclasses.replace(vaznlar, **{omil: 0.0})


def _qayta_taqsim(vaznlar: ScoreWeights, omil: str) -> ScoreWeights:
    """Omil vazni qolganlarga NISBATIGA qarab bo'linadi (shkala 100 qoladi)."""
    olingan = getattr(vaznlar, omil)
    qolgan = vaznlar.total() - olingan
    if qolgan <= 0:
        return _nolga(vaznlar, omil)
    yangi: dict[str, float] = {}
    for maydon in OMILLAR:
        joriy = getattr(vaznlar, maydon)
        yangi[maydon] = 0.0 if maydon == omil else joriy + olingan * joriy / qolgan
    return ScoreWeights(**yangi)


def _variantlar(config: AppConfig) -> list[tuple[str, str, AppConfig]]:
    """(nom, izoh, sozlama) uchliklari — birinchisi tayanch."""
    asos = config.scoring.weights
    royxat: list[tuple[str, str, AppConfig]] = [
        ("TAYANCH", "hamma omil joyida", config),
    ]
    for omil, nom in OMILLAR.items():
        vazn = getattr(asos, omil)
        royxat.append(
            (
                nom,
                f"nol (vazn {vazn:g} -> 0, shkala {asos.total() - vazn:g})",
                _vaznlar_bilan(config, _nolga(asos, omil)),
            )
        )
    for omil, nom in OMILLAR.items():
        royxat.append(
            (
                nom,
                "qayta taqsim (shkala 100)",
                _vaznlar_bilan(config, _qayta_taqsim(asos, omil)),
            )
        )
    return royxat


def _xulosa(olchovlar: list[Olchov]) -> str:
    """Qaysi omil PF ga eng ko'p / eng kam ta'sir qildi."""
    tayanch = olchovlar[0]
    if tayanch.profit_factor is None:
        return "Tayanch yugurishda yopilgan savdo yo'q — xulosa chiqarib bo'lmaydi."

    farqlar = [
        (o, o.profit_factor - tayanch.profit_factor)
        for o in olchovlar[1:]
        if o.profit_factor is not None
    ]
    if not farqlar:
        return "Variantlarda yopilgan savdo yo'q — xulosa chiqarib bo'lmaydi."

    # Eng KO'P ta'sir = olib tashlanganda PF eng ko'p PASAYGAN omil.
    eng_kerakli = min(farqlar, key=lambda x: x[1])
    eng_keraksiz = max(farqlar, key=lambda x: x[1])

    satrlar = [
        f"Tayanch: PF {tayanch.profit_factor:.2f}, {tayanch.signal} savdo, "
        f"bitta savdoda {tayanch.ortacha_savdo_pct:+.2f}%",
        "",
        f"ENG KERAKLI omil: {eng_kerakli[0].nom} ({eng_kerakli[0].izoh}) — "
        f"olib tashlanganda PF {eng_kerakli[1]:+.2f} o'zgardi "
        f"({eng_kerakli[0].profit_factor:.2f} ga tushdi).",
        f"ENG KERAKSIZ omil: {eng_keraksiz[0].nom} ({eng_keraksiz[0].izoh}) — "
        f"olib tashlanganda PF {eng_keraksiz[1]:+.2f} o'zgardi "
        f"({eng_keraksiz[0].profit_factor:.2f} bo'ldi).",
        "",
    ]
    if eng_keraksiz[1] > 0:
        satrlar.append(
            "DIQQAT: kamida bitta omil olib tashlanganda natija YAXSHILANDI. "
            "Bu omil ballga foydali ma'lumot qo'shmayapti — u shovqin."
        )
    if all(farq >= 0 for _, farq in farqlar):
        satrlar.append(
            "DIQQAT: HECH BIR omil olib tashlanganda natija yomonlashmadi. "
            "Ya'ni ball tizimining o'zi natijaga hissa qo'shmayapti."
        )
    return "\n".join(satrlar)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="HALOL CRYPTO SAVDO — ball omillari ablation testi"
    )
    umumiy_argumentlar(parser)
    argumentlar = parser.parse_args()

    config, dataset, coinlar, oxiri = await malumot_tayyorla(argumentlar)
    variantlar = _variantlar(config)

    print(
        f"\nAblation: {len(variantlar)} yugurish | {', '.join(coinlar)} | "
        f"{argumentlar.days} kun"
        + (f" | {oxiri.date()} gacha" if oxiri else "")
        + "\n"
    )

    olchovlar: list[Olchov] = []
    for nom, izoh, variant in variantlar:
        yorliq = f"{nom} — {izoh}"
        print(f"  ishlamoqda: {yorliq}")
        natija = Backtester(variant, label=yorliq).run(
            dataset, max_steps=argumentlar.max_steps
        )
        olchovlar.append(olchov_qur(nom, izoh, natija))

    sarlavha = (
        f"ABLATION — ball omillarining hissasi\n"
        f"Coinlar: {', '.join(coinlar)} | {argumentlar.days} kun"
        + (f" | oyna {oxiri.date()} gacha" if oxiri else "")
        + "\nYo'l xarajati (komissiya + slippage) dvigatel ichida hisoblangan."
    )
    matn = "\n\n".join(
        [sarlavha, jadval(olchovlar, "omil", "chiqarish usuli"), "XULOSA", _xulosa(olchovlar)]
    )

    csv_yol = csv_saqla("ablation.csv", olchovlar)
    matn_yol = matn_saqla("ablation.txt", matn)

    print("\n" + matn)
    print(f"\nSaqlandi: {csv_yol}  va  {matn_yol}")


if __name__ == "__main__":
    asyncio.run(main())
