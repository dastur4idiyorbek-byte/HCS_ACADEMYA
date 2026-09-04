"""Portfel risk va foyda boshqaruv moduli (3-prompt).

TAHLIL MODULIDAN BUTUNLAY MUSTAQIL. Bu papka `core/analysis/` ga
HECH QANDAY import qilmaydi va undan hech narsa so'ramaydi.

O'xshatish (3-promptdan): tahlil moduli — mahsulot ishlab
chiqaruvchi zavod; bu modul — tayyor mahsulotni taqsimlovchi
logistika. Signal QANDAY yaratilgani bu yerda AHAMIYATSIZ.

Kiruvchi ma'lumot faqat shu:

    {entry, stop, tplar: [...], balans}

Mustaqillik test bilan qulflangan: `tests/core/test_portfel_mustaqil.py`
soxta signal bilan butun modulni tahlil modulisiz yuritadi.
"""

from core.portfolio.capital_allocator import (
    Bolak,
    Taqsimot,
    band_qil,
    bolaklarni_yarat,
    bosat,
    joylashtir,
    umumiy_xavf_pct,
)

__all__ = [
    "Bolak",
    "Taqsimot",
    "band_qil",
    "bolaklarni_yarat",
    "bosat",
    "joylashtir",
    "umumiy_xavf_pct",
]
