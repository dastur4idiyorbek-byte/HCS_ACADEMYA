"""4.4 — Fundamental-texnik mos kelish: 1-blokni QAYTA tekshirish.

NIMA UCHUN KERAK (2-prompt): 1-blok zanjirning boshida hisoblanadi.
To'rt blok o'tguncha vaqt o'tadi — kunlar bo'lishi mumkin, chunki
holat saqlanadi (6-qism) va bloklar bosqichma-bosqich to'ladi.
Shu vaqt ichida fundamental holat o'zgargan bo'lishi mumkin.

BU QAYTA HISOBLASH EMAS, SOLISHTIRISH. Yangi fundamental blok
tashqarida hisoblanadi va bu yerga TAYYOR holda keladi. Funksiya
faqat "eski xulosa hamon kuchdami" degan savolga javob beradi.

QOIDA: eski blok o'tgan bo'lsa, yangisi ham o'tishi kerak. Agar
yangi blok qattiq to'siqqa uchragan bo'lsa (masalan unlock e'lon
qilindi) — mos kelish YO'Q.
"""

from __future__ import annotations

from core.analysis.turlar import Blok


def fundamental_hamon_mos(eski: Blok | None, yangi: Blok | None) -> bool | None:
    """Fundamental xulosa o'zgarmadimi.

    Returns:
        `True` — hamon mos, `False` — buzilgan,
        `None` — solishtirishga ma'lumot yo'q.
    """
    if eski is None or yangi is None:
        return None
    if eski.olchanmadi or yangi.olchanmadi:
        return None
    if yangi.qattiq_tosiq is not None:
        return False
    if not yangi.otdi:
        return False
    # Kuch SEZILARLI pasaymaganmi. Bitta tekshiruvning tebranishi
    # normal; ikkitasi birdan yo'qolsa — holat haqiqatan o'zgargan.
    return yangi.kuch >= eski.kuch - 1
