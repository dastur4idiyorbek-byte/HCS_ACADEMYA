"""CryptoSpot3% qatlami voronkaga qanday ta'sir qildi — o'lchov.

Metodika hujjati har bir qismdan keyin ALOHIDA o'lchovni talab qiladi.
To'liq bozor backtesti tarixiy narx talab qiladi (`scripts/backtest.py`,
tarmoq kerak). Bu skript esa TARMOQSIZ ishlaydi: u `scripts/kalibrlash`
dagi sun'iy, lekin nazorat qilinadigan sozlamalar to'plamida ballarni
o'lchaydi — chegaralar (50/55) aynan shu to'plamda tanlangan edi.

Uchta savolga javob beradi:

    1. Nomzodlar SONI o'zgardimi?  (o'zgarmasligi SHART: dalil
       hech kimni yo'ldan qaytarmaydi)
    2. Chegaradan o'tganlar soni o'zgardimi?  (O'ZGARISHI KUTILADI:
       dalil bazaviy ball ichida, ya'ni u signal soniga ta'sir qiladi)
    3. REYTING o'zgardimi?  (o'zgarishi KUTILADI: bir xil sifatdagi
       nomzodlardan strukturasi va sweep'i borini yuqoriga chiqarish)

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


def dalilsiz(config: AppConfig) -> AppConfig:
    """CryptoSpot3% dalillari o'chirilgan nusxa — "oldingi modul"."""
    return dataclasses.replace(
        config,
        scoring=dataclasses.replace(
            config.scoring,
            uplift=dataclasses.replace(config.scoring.uplift, support_resistance=0.0),
            bonuses=dataclasses.replace(config.scoring.bonuses, session_overlap=0),
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
    eski = dalilsiz(config)

    bilan = nomzodlar(config)
    siz = nomzodlar(eski)
    if not bilan:
        print("Nomzod chiqmadi — o'lchov qurilmasi buzuq bo'lishi mumkin")
        return

    chegara = config.scoring.thresholds.threshold_mid_health
    reyting = Scorer(config).rank(bilan, chegara)
    eski_reyting = Scorer(eski).rank(siz, chegara)

    bazaviy = [n.breakdown.base_total for n in bilan]
    eski_bazaviy = [n.breakdown.base_total for n in siz]
    otgan = sum(1 for r in reyting if r.passed_threshold)
    eski_otgan = sum(1 for r in eski_reyting if r.passed_threshold)
    toliq = sum(1 for r in reyting if r.setup_complete)

    print("CryptoSpot3% qatlami — o'lchov (kalibrlash to'plami)")
    print("=" * 62)
    print(f"Nomzodlar soni:        {len(siz)} -> {len(bilan)}")
    print(f"Chegaradan o'tganlar:  {eski_otgan} -> {otgan}"
          f"   <- SIGNAL SONI shu yerda o'zgaradi")
    print(f"To'liq shartnomali:    {toliq}/{len(bilan)}")
    print()
    print("Bazaviy ball (chegara AYNAN shuni o'qiydi):")
    print(f"  dalilsiz:     {min(eski_bazaviy):5.1f} .. {max(eski_bazaviy):5.1f}"
          f"   (o'rtacha {sum(eski_bazaviy) / len(eski_bazaviy):5.1f})")
    print(f"  dalil bilan:  {min(bazaviy):5.1f} .. {max(bazaviy):5.1f}"
          f"   (o'rtacha {sum(bazaviy) / len(bazaviy):5.1f})")
    print()
    print(f"Chegara: {chegara:.0f}")
    print("Reyting (bazaviy -> to'liq ball):")
    for r in reyting[:10]:
        belgi = "o'tdi" if r.passed_threshold else "—"
        yorliq = " ✓shartnoma" if r.setup_complete else ""
        print(f"  {r.rank:2d}. {r.base_score:5.1f} -> {r.score:5.1f}   {belgi}{yorliq}")

    # CHEGARA BO'YLAB SUPURISH — eng muhim jadval.
    #
    # Bitta chegarada natija tasodifga bog'liq bo'lishi mumkin: 15 ta
    # sun'iy nomzod chiziqning qay tomonida turgani muhim. Butun
    # diapazon bo'ylab qarasak, dalilning signal SONIGA ta'siri aniq
    # ko'rinadi.
    print()
    print("Chegara bo'ylab o'tganlar soni:")
    print(f"  {'chegara':>8}  {'dalilsiz':>8}  {'dalilli':>8}")
    for ch in (45, 50, 52, 55, 58, 60, 62, 65):
        a = sum(1 for x in eski_bazaviy if x >= ch)
        b = sum(1 for x in bazaviy if x >= ch)
        belgi = "  <-- joriy" if abs(ch - chegara) < 0.5 else ""
        print(f"  {ch:8d}  {a:8d}  {b:8d}{belgi}")

    bazaviy_tartib = sorted(reyting, key=lambda r: r.base_score, reverse=True)
    ozgardi = [r.rank for r in bazaviy_tartib] != [r.rank for r in reyting]
    kop = sum(
        1
        for ch in (45, 50, 52, 55, 58, 60, 62, 65)
        if sum(1 for x in bazaviy if x >= ch) > sum(1 for x in eski_bazaviy if x >= ch)
    )
    print()
    print(f"Joriy chegarada signal soni o'zgardimi: "
          f"{'HA' if otgan != eski_otgan else 'yoq (tasodif)'}")
    print(f"Sinalgan 8 chegaradan {kop} tasida dalil signal sonini OSHIRDI")
    print(f"Reyting TARTIBI o'zgardimi: {'HA' if ozgardi else 'yoq'}")


if __name__ == "__main__":
    main()
