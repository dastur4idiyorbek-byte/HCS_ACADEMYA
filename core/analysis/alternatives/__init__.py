"""Alternativ yo'llar — zaif blokni qutqaradigan yangi zanjir.

Asosiy `zanjir_yur` (eski) bilan birga yashaydi: ikkisini yonma-yon
o'lchash va solishtirish uchun alohida funksiya sifatida yozilgan.

    zanjir_yur_alternativ()  — zaif (1/N) blokda alternativlarni
                               ketma-ket sinaydi; hammasi sinsa uziladi.
    blok_tasnifi()           — KUCHLI / ZAIF / BO'SH / OLCHANMADI.
    qutqar()                 — bitta blokni alternativlar bilan qutqarish.

Alternativlar:
    Blok 2: trend_flag (2A), qosh_tub (2B)
    Blok 3: qosh_tub zona (3A), oldingi_swing zona (3B)
    Blok 4: hajm_sakrashi (4A), tez_harakat (4B), qayta_sinov (4C)
"""

from core.analysis.alternatives.alternative_chain import (
    KUCHLI_ENG_KAM,
    ZAIF_KUCH,
    blok_tasnifi,
    qutqar,
    zanjir_yur_alternativ,
)
from core.analysis.alternatives.double_pattern import QoshTub, qosh_tub_topish
from core.analysis.alternatives.natija import AlternativNatija
from core.analysis.alternatives.prior_swing import oldingi_swing_zona
from core.analysis.alternatives.tasdiq import hajm_sakrashi, qayta_sinov, tez_harakat
from core.analysis.alternatives.trend_flag import trend_flag

__all__ = [
    "AlternativNatija",
    "KUCHLI_ENG_KAM",
    "QoshTub",
    "ZAIF_KUCH",
    "blok_tasnifi",
    "hajm_sakrashi",
    "oldingi_swing_zona",
    "qayta_sinov",
    "qosh_tub_topish",
    "qutqar",
    "tez_harakat",
    "trend_flag",
    "zanjir_yur_alternativ",
]
