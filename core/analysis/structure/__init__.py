"""BLOK 2 — Struktura.

    2.1 Swing ketma-ketligi   5 shamli fraktal, HH/HL yoki LH/LL
    2.2 So'nggi BOS tasdiqlangan
    2.3 Qarshi CHOCH yo'q
    2.4 Nisbiy kuch           coin/BTC nisbati yo'nalishga mos

Butun blok SHAMDAN hisoblanadi — ya'ni 100% backtest qilinadi.
Fundamental blokdagi ma'lumot muammosi bu yerda yo'q.
"""

from core.analysis.structure.bos_choch import BosChoch, bos_choch_topish
from core.analysis.structure.new_coin_pattern import yangi_coin_naqshi
from core.analysis.structure.relative_strength import nisbiy_kuch
from core.analysis.structure.structure_block import StrukturaKirish, struktura_blok
from core.analysis.structure.swing_detector import Swing, SwingTuri, swinglar

__all__ = [
    "BosChoch",
    "StrukturaKirish",
    "Swing",
    "SwingTuri",
    "bos_choch_topish",
    "nisbiy_kuch",
    "struktura_blok",
    "swinglar",
    "yangi_coin_naqshi",
]
