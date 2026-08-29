"""CryptoSpot3% qatlami voronkaga qanday ta'sir qildi — o'lchov.

Metodika hujjati har bir qismdan keyin ALOHIDA o'lchovni talab qiladi.
To'liq bozor backtesti tarixiy narx talab qiladi (`scripts/backtest.py`,
tarmoq kerak). Bu skript esa TARMOQSIZ ishlaydi: u `scripts/kalibrlash`
dagi sun'iy, lekin nazorat qilinadigan sozlamalar to'plamida ballarni
o'lchaydi — chegaralar (50/55) aynan shu to'plamda tanlangan edi.

Uchta savolga javob beradi:

    1. Nomzodlar SONI o'zgardimi?  (o'zgarmasligi SHART: hech bir yangi
       omil to'siq emas)
    2. Chegaradan o'tganlar soni o'zgardimi?  (o'zgarmasligi SHART:
       darvoza bazaviy ballda tekshiriladi)
    3. REYTING o'zgardimi?  (o'zgarishi KUTILADI: bonuslarning butun
       ma'nosi shu — bir xil sifatdagi nomzodlardan strukturasi va
       sweep'i borini yuqoriga chiqarish)

Ishga tushirish:  python -m scripts.cryptospot3_olchov
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ILDIZ / "scripts"))

from kalibrlash import kirish, shamlar_yasa, sozlamalar  # noqa: E402

from core.analysis.scoring import Scorer  # noqa: E402
from core.analysis.strategies.classic_ta import ClassicTaStrategy  # noqa: E402
from core.config import load_config  # noqa: E402
from core.config.schema import AppConfig  # noqa: E402


def bonussiz(config: AppConfig) -> AppConfig:
    """Bonus vaznlari nolga tushirilgan nusxa — "oldingi holat"."""
    return dataclasses.replace(
        config,
        scoring=dataclasses.replace(
            config.scoring,
            bonuses=dataclasses.replace(
                config.scoring.bonuses,
                structure=0,
                liquidity_sweep=0,
                session_overlap=0,
            ),
        ),
    )


def nomzodlar(config: AppConfig) -> list:  # noqa: ANN201
    strategiya = ClassicTaStrategy(config)
    natija = []
    for sozlama in sozlamalar():
        nomzod = strategiya.analyze(kirish(config, shamlar_yasa(sozlama)))
        if nomzod is not None:
            natija.append(nomzod)
    return natija


def main() -> None:
    config = load_config()
    eski = bonussiz(config)

    bilan = nomzodlar(config)
    siz = nomzodlar(eski)
    if not bilan:
        print("Nomzod chiqmadi — o'lchov qurilmasi buzuq bo'lishi mumkin")
        return

    chegara = config.scoring.thresholds.threshold_mid_health
    reyting = Scorer(config).rank(bilan, chegara)
    eski_reyting = Scorer(eski).rank(siz, chegara)

    bazaviy = [n.breakdown.base_total for n in bilan]
    bonus = [n.breakdown.bonus_total for n in bilan]
    otgan = sum(1 for r in reyting if r.passed_threshold)
    eski_otgan = sum(1 for r in eski_reyting if r.passed_threshold)

    print("CryptoSpot3% qatlami — o'lchov (kalibrlash to'plami)")
    print("=" * 58)
    print(f"Nomzodlar soni:        {len(siz)} -> {len(bilan)}   (o'zgarmasligi shart)")
    print(f"Chegaradan o'tganlar:  {eski_otgan} -> {otgan}   (o'zgarmasligi shart)")
    print()
    print(f"Bazaviy ball:  {min(bazaviy):.1f} .. {max(bazaviy):.1f}"
          f"  (o'rtacha {sum(bazaviy) / len(bazaviy):.1f})")
    print(f"Bonus:         {min(bonus):.1f} .. {max(bonus):.1f}"
          f"  (o'rtacha {sum(bonus) / len(bonus):.1f}, shift {config.scoring.bonuses.total():.0f})")
    print(f"Bonus olmaganlar: {sum(1 for b in bonus if b == 0)}/{len(bonus)}")
    print()
    print("Reyting (bazaviy -> to'liq):")
    for r in reyting[:8]:
        belgi = "o'tdi" if r.passed_threshold else "—"
        print(f"  {r.rank:2d}. {r.base_score:5.1f} -> {r.score:5.1f}   {belgi}")

    # Tartib O'ZGARDIMI: bonuslar ma'noli bo'lsa, ha
    bazaviy_tartib = sorted(reyting, key=lambda r: r.base_score, reverse=True)
    ozgardi = [r.rank for r in bazaviy_tartib] != [r.rank for r in reyting]
    print()
    javob = "HA" if ozgardi else "yo'q"
    print(f"Reyting tartibi bonusdan o'zgardimi: {javob}")


if __name__ == "__main__":
    main()
