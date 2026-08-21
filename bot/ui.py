"""Ekranlarni ALMASHTIRISH — xabarlar to'planib ketmasligi uchun.

Muammo: har `/start` va `/panel` yangi xabar yaratardi. Bir kunda o'nlab
bir xil menyu to'planib, suhbatni o'qib bo'lmay qolardi.

Yechim: bitta "jonli" ekran. Yangi menyu ochilganda eskisi va buyruqning
o'zi o'chiriladi. Signal xabarlariga TEGILMAYDI — ular tarix, saqlanishi
kerak.
"""

from __future__ import annotations

import contextlib

from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

#: FSM holatida oxirgi menyu xabarining raqami shu kalitda saqlanadi
OXIRGI_EKRAN = "oxirgi_ekran_id"


async def show_screen(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    delete_command: bool = True,
) -> Message:
    """Eski ekranni o'chirib, yangisini ko'rsatadi.

    Args:
        delete_command: foydalanuvchi yozgan buyruq (`/start`, `/panel`) ham
            o'chirilsinmi. Telegram botga buni ruxsat bermasligi mumkin —
            u holda jimgina o'tkazib yuboriladi.

    O'chirish har doim ham ishlamaydi (48 soatdan eski xabar, guruh
    sozlamalari). Shuning uchun har bir o'chirish alohida himoyalangan:
    ekran baribir ko'rsatiladi (0.3-band).
    """
    data = await state.get_data()
    eski_id = data.get(OXIRGI_EKRAN)

    if eski_id:
        with contextlib.suppress(Exception):
            await message.bot.delete_message(message.chat.id, eski_id)

    if delete_command:
        with contextlib.suppress(Exception):
            await message.delete()

    yangi = await message.answer(text, reply_markup=reply_markup)
    await state.update_data(**{OXIRGI_EKRAN: yangi.message_id})
    return yangi
