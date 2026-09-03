"""BLOK 3 — Zona Sifati.

    3.1 Fibonacci      38.2/50/61.8% korreksiya zonasi
    3.2 Order Block    reversaldan oldingi qarama-qarshi sham
    3.3 FVG            uch shamli bo'shliq
    3.4 Volume Profile POC / yuqori hajmli tugun

DARAJALI BIRLASHTIRISH (2-prompt, 4-qism, BLOK 3 oxiri) — bu
blokning boshqalaridan asosiy farqi. Fib/OB/FVG alohida ovoz EMAS,
bir-birini KUCHAYTIRUVCHI qatlamlar:

    faqat Fib          ZAIF
    Fib + OB           O'RTA
    Fib + OB + FVG     KUCHLI

Volume Profile — ulardan MUSTAQIL, alohida ✅/❌.
"""

from core.analysis.zone_quality.fibonacci import Zona, fib_zona
from core.analysis.zone_quality.fvg import FVG, fvg_topish
from core.analysis.zone_quality.order_block import OrderBlock, ob_topish
from core.analysis.zone_quality.volume_profile import poc_narx, poc_yaqinmi
from core.analysis.zone_quality.zone_block import (
    ZonaDarajasi,
    ZonaKirish,
    ZonaNatija,
    zona_blok,
)

__all__ = [
    "FVG",
    "OrderBlock",
    "Zona",
    "ZonaDarajasi",
    "ZonaKirish",
    "ZonaNatija",
    "fib_zona",
    "fvg_topish",
    "ob_topish",
    "poc_narx",
    "poc_yaqinmi",
    "zona_blok",
]
