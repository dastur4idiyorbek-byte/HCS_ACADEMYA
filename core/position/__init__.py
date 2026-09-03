"""Pozitsiya qurish — kirish, chiqish, masshtablab sotish.

    entry_stop_tp.py — 5-qism: darajalar STRUKTURA asosida
    scaling_out.py   — chiqish rejasi, trailing, vaqt chegarasi

QAT'IY FOIZ YO'Q (2-prompt, "NIMA QILINMAYDI"): Stop zona chetidan,
TP qarshi struktura nuqtasidan olinadi. Foiz faqat XAVFSIZLIK
CHEGARASI sifatida ishlatiladi — "bundan uzoq bo'lsa signal rad
etiladi", "shuncha bo'lsin" emas.
"""

from core.position.entry_stop_tp import Darajalar, darajalar_qur
from core.position.scaling_out import ChiqishRejasi, chiqish_rejasi

__all__ = ["ChiqishRejasi", "Darajalar", "chiqish_rejasi", "darajalar_qur"]
