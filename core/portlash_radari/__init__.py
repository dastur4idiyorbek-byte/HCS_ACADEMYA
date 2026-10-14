"""Modul 4.0.0 — "Portlash xavfi radari" (`docs/MODUL_4_0_0.md`).

Binance Futures'dagi hamma USDT juftligini kuniga 12 marta tekshiradi
va "bu coinda g'ayrioddiy faollik bor, kuzatib boring" deydi.

SIGNAL BERMAYDI. Entry, Stop, TP yo'q — `tests/core/test_radar_chegara.py`
buni kod matnidan tekshiradi.

Modul 3.0.0 (`core/watch_panel`) dan MUSTAQIL: o'z papkasi, o'z
jadvallari (`radar_*`), o'z sikli. Mavjud tizimdan faqat O'QILADI:
halol reestr va unlock kalendari.

Qatlamlar:

    belgi, vaqt, sozlama, tekshiruvlar, tartib, halol   sof mantiq
    manba                                                tarmoq
    repository                                           baza
    sessiya, baholash                                    yig'uvchi
    ishchi                                               asyncio sikli
"""
