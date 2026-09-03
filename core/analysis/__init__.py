"""Tahlil moduli — TO'RT BLOKLI ZANJIR (2026-09-03 dan, noldan qurilgan).

Eski 100 balllik tizim o'chirildi: 16 o'lchov to'plamida u foyda
bermagani isbotlandi (`docs/OLCHOVLAR_XULOSASI.md`). Yangi tizimning
asosiy farqi — BALL EMAS, ZANJIR:

    BLOK 1 Fundamental  -> BLOK 2 Struktura -> BLOK 3 Zona -> BLOK 4 Tasdiq

Har bir blok 4 ta ichki tekshiruvdan iborat. Blok BUTUNLAY bo'sh
bo'lsa (0/4) zanjir shu yerda uziladi va keyingi bloklar UMUMAN
hisoblanmaydi. Signal faqat to'rtala blok ham o'tganda chiqadi.

Eski tizimdan asosiy farq: u 6 omilni QO'SHIB, yig'indini chegara
bilan solishtirardi — ya'ni bitta kuchli omil qolgan beshtasining
yo'qligini yopib ketardi. Zanjirda bunday almashtirish mumkin emas.
"""

from core.analysis.turlar import (
    Blok,
    Holat,
    Tekshiruv,
    Zanjir,
    blok,
    ha,
    malumot_yoq,
    yoq,
)

__all__ = [
    "Blok",
    "Holat",
    "Tekshiruv",
    "Zanjir",
    "blok",
    "ha",
    "malumot_yoq",
    "yoq",
]
