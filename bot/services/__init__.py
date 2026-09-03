"""Fon xizmatlari — botning uzluksiz ishlaydigan qismlari.

    scheduler.py  — takrorlanuvchi vazifalar

2026-09-03 — eski tahlil moduli olib tashlandi. U bilan birga
`runner.py` (jonli ma'lumotni eski signal sikliga ulardi),
`watcher.py` (eski holat mashinasiga tayanardi) va
`bozor_korinishi.py` ham ketdi. Yangi modul o'z fon xizmatini olib
keladi; hozircha signal faqat QO'LDA kiritiladi.
"""

from bot.services.scheduler import Scheduler

__all__ = ["Scheduler"]
