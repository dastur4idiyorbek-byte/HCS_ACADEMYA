"""FSM holatlari — ko'p bosqichli dialoglar."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class PaymentFlow(StatesGroup):
    """1.2-band: tarif → muddat → chek yuborish."""

    waiting_receipt = State()


class BalanceFlow(StatesGroup):
    """5.1-band: foydalanuvchi o'zi kiritadigan balans."""

    waiting_balance = State()


class PositionFlow(StatesGroup):
    """5.4-band: "Men kirdim" → miqdorni so'rash."""

    waiting_amount = State()


class PaymentReviewFlow(StatesGroup):
    """Admin to'lovni rad etganda sabab so'raladi."""

    waiting_reject_reason = State()


class PriceFlow(StatesGroup):
    """1.2-band: narxni admin panel orqali belgilash."""

    waiting_amount = State()
    waiting_details = State()


class BroadcastFlow(StatesGroup):
    waiting_message = State()


class ViolationFlow(StatesGroup):
    """1.3-band: qoidabuzarlik uchun ogohlantirish."""

    waiting_user_id = State()
    waiting_reason = State()


class CoinRulingFlow(StatesGroup):
    """1.4-band: coinni qo'lda harom/shubhali deb belgilash."""

    waiting_symbol = State()
    waiting_reason = State()


class ContentFlow(StatesGroup):
    """1.5-band: video/strategiya kontent qo'shish."""

    waiting_title = State()
    waiting_file = State()


class SignalFlow(StatesGroup):
    """2-bo'lim: admin qo'lda signal kiritadi.

    Coin → Entry → Stop → TP1 → TP2 → izoh → preview → tasdiqlash
    """

    waiting_symbol = State()
    waiting_entry = State()
    waiting_stop = State()
    waiting_tp1 = State()
    waiting_tp2 = State()
    waiting_note = State()
    waiting_confirm = State()
