"""Telegram handlerlar — yupqa qatlam.

    user.py   — /start, /menu, obuna, to'lov cheki, signallar, portfel
    admin.py  — /panel, to'lovlarni tasdiqlash, kontent, halol ro'yxat,
                Bozor Salomatligi dashboardi, haftalik hisobot

1.3-band: barcha signal/video/strategiya xabarlari `protect_content=True`
bilan yuboriladi (forward/saqlash bloklanadi).

Ochiq texnik haqiqat: ekran yozib olishning oldini 100% olib bo'lmaydi (OS
darajasidagi imkoniyat). Watermark hozircha QURILMAYDI — real-vaqtli video
generatsiya resurs talab qiladi. Bu kelajakka TODO sifatida qoldirilgan.

HOLAT: 3-bosqichda to'ldiriladi.
"""
