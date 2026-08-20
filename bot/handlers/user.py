"""Foydalanuvchi handlerlari — yupqa qatlam.

Bu yerda biznes qaror qabul qilinmaydi: handler `core/services/` va
`core/storage/repositories/` ni chaqiradi va natijani ko'rsatadi (0.1-band).

1.3-band: barcha pullik kontent `protect_content=True` bilan yuboriladi.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.i18n import t
from bot.keyboards import back_button, main_menu, period_menu, tier_menu
from bot.states import BalanceFlow, PaymentFlow
from core.config.schema import AppConfig
from core.domain.enums import SubscriptionPeriod, SubscriptionTier
from core.services import SubscriptionService
from core.storage import Database
from core.storage.repositories import (
    ContentRepository,
    PaymentRepository,
    PriceRepository,
    SubscriptionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)
router = Router(name="user")


def _service(session, config: AppConfig) -> SubscriptionService:  # noqa: ANN001
    return SubscriptionService(
        config.subscriptions,
        UserRepository(session),
        SubscriptionRepository(session),
        PaymentRepository(session),
    )


# --------------------------------------------------------------------------- #
#  Asosiy menyu
# --------------------------------------------------------------------------- #


@router.message(CommandStart())
@router.message(Command("menu"))
async def show_menu(
    message: Message,
    state: FSMContext,
    tier: SubscriptionTier | None,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    await state.clear()
    salom = t("umumiy.salom", language, name=message.from_user.full_name)
    await message.answer(
        f"{salom}\n\n{t('umumiy.menyu', language)}",
        reply_markup=main_menu(tier, language, is_admin),
    )


@router.callback_query(F.data == "menu:home")
async def back_home(
    callback: CallbackQuery,
    state: FSMContext,
    tier: SubscriptionTier | None,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    await state.clear()
    await callback.message.edit_text(
        t("umumiy.menyu", language), reply_markup=main_menu(tier, language, is_admin)
    )
    await callback.answer()


@router.callback_query(F.data == "menu:yordam")
async def show_help(callback: CallbackQuery, language: str, **_: object) -> None:
    await callback.message.edit_text(
        t("umumiy.yordam_matni", language), reply_markup=back_button(language=language)
    )
    await callback.answer()


# --------------------------------------------------------------------------- #
#  1.2 — Obuna va to'lov
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "menu:tariflar")
async def show_tiers(callback: CallbackQuery, language: str, **_: object) -> None:
    await callback.message.edit_text(
        t("obuna.sarlavha", language), reply_markup=tier_menu(language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tier:"))
async def choose_period(callback: CallbackQuery, language: str, **_: object) -> None:
    tier = SubscriptionTier(callback.data.split(":", 1)[1])
    await callback.message.edit_text(
        t("obuna.tarif_tanlandi", language, tier=t(f"obuna.{tier.value}", language)),
        reply_markup=period_menu(tier, language),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("period:"))
async def show_payment_details(
    callback: CallbackQuery,
    state: FSMContext,
    database: Database,
    config: AppConfig,
    db_user_id: int,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    """Narx va rekvizitlarni ko'rsatib, chek kutish holatiga o'tadi."""
    _, tier_raw, period_raw = callback.data.split(":")
    tier, period = SubscriptionTier(tier_raw), SubscriptionPeriod(period_raw)
    valyuta = config.subscriptions.currencies[0]

    async with database.session() as session:
        if await PaymentRepository(session).has_pending(db_user_id):
            await callback.answer(t("obuna.chek_kutilmoqda", language), show_alert=True)
            return
        narx = await PriceRepository(session).get(tier, period.value, valyuta)

    if narx is None:
        await callback.answer(t("obuna.narx_belgilanmagan", language), show_alert=True)
        return

    await state.set_state(PaymentFlow.waiting_receipt)
    await state.update_data(
        tier=tier.value, period=period.value, amount=narx.amount, currency=narx.currency
    )
    await callback.message.edit_text(
        t(
            "obuna.tolov_korsatmasi",
            language,
            tier=t(f"obuna.{tier.value}", language),
            period=t(f"obuna.{period.value}", language),
            amount=f"{narx.amount:,.0f}",
            currency=narx.currency,
            details=narx.payment_details or "—",
        ),
        reply_markup=back_button(language=language),
    )
    await callback.answer()


@router.message(PaymentFlow.waiting_receipt, F.photo | F.document)
async def receive_receipt(
    message: Message,
    state: FSMContext,
    database: Database,
    config: AppConfig,
    db_user_id: int,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    """Chek qabul qilinadi — obuna HALI berilmaydi, admin tasdiqlashi kerak."""
    data = await state.get_data()
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id

    async with database.session() as session:
        tolov = await _service(session, config).submit_payment(
            user_id=db_user_id,
            tier=SubscriptionTier(data["tier"]),
            period=SubscriptionPeriod(data["period"]),
            amount=data["amount"],
            currency=data["currency"],
            receipt_file_id=file_id,
        )
        tolov_id = tolov.id

    await state.clear()
    logger.info("Yangi to'lov cheki: payment=%s user=%s", tolov_id, db_user_id)
    await message.answer(t("obuna.chek_qabul_qilindi", language))


@router.message(PaymentFlow.waiting_receipt)
async def receipt_wrong_type(message: Message, language: str, **_: object) -> None:
    await message.answer(t("obuna.faqat_rasm", language))


# --------------------------------------------------------------------------- #
#  5.1 / 5.4 — Portfel va balans
# --------------------------------------------------------------------------- #


@router.callback_query(F.data.in_({"menu:portfel", "menu:portfel:back"}))
async def show_portfolio(
    callback: CallbackQuery,
    database: Database,
    db_user_id: int,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    async with database.session() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        balans = user.declared_balance_usd if user else None

    qatorlar = [t("portfel.sarlavha", language), ""]
    qatorlar.append(
        t("portfel.hozirgi_balans", language, balance=f"{balans:,.2f}")
        if balans
        else t("portfel.balans_yoq", language)
    )
    qatorlar += ["", t("portfel.ogohlantirish", language)]

    builder = InlineKeyboardBuilder()
    builder.button(text=t("portfel.sarlavha", language), callback_data="portfel:pozitsiyalar")
    builder.button(
        text=t("portfel.balans_ozgartirish", language), callback_data="portfel:balans"
    )
    builder.button(text=t("umumiy.orqaga", language), callback_data="menu:home")
    builder.adjust(1)

    await callback.message.edit_text("\n".join(qatorlar), reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "portfel:balans")
async def ask_balance(
    callback: CallbackQuery, state: FSMContext, language: str, **_: object
) -> None:
    await state.set_state(BalanceFlow.waiting_balance)
    await callback.message.edit_text(t("portfel.balans_soralmoqda", language))
    await callback.answer()


@router.message(BalanceFlow.waiting_balance)
async def save_balance(
    message: Message,
    state: FSMContext,
    database: Database,
    tier: SubscriptionTier | None,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    try:
        balans = float(message.text.replace(",", ".").replace(" ", ""))
    except (ValueError, AttributeError):
        await message.answer(t("umumiy.raqam_kiriting", language))
        return
    if balans <= 0:
        await message.answer(t("umumiy.musbat_raqam_kiriting", language))
        return

    async with database.session() as session:
        users = UserRepository(session)
        user = await users.get_by_telegram_id(message.from_user.id)
        await users.set_balance(user, balans)

    await state.clear()
    await message.answer(
        t("portfel.balans_saqlandi", language, balance=f"{balans:,.2f}"),
        reply_markup=main_menu(tier, language, is_admin),
    )


# --------------------------------------------------------------------------- #
#  1.5 — Kontent (protect_content bilan)
# --------------------------------------------------------------------------- #


@router.callback_query(F.data.in_({"menu:video_darslar", "menu:strategiyalar"}))
async def show_content(
    callback: CallbackQuery,
    database: Database,
    tier: SubscriptionTier | None,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    async with database.session() as session:
        kontent = await ContentRepository(session).available_for(tier)

    if not kontent:
        await callback.answer(t("kontent.bosh", language), show_alert=True)
        return

    await callback.answer()
    for element in kontent:
        sarlavha = f"🎬 {element.title}"
        if element.description:
            sarlavha += f"\n\n{element.description}"
        if element.file_id:
            # 1.3-band: forward/saqlash bloklanadi
            await callback.message.answer_video(
                element.file_id, caption=sarlavha, protect_content=True
            )
        else:
            await callback.message.answer(sarlavha, protect_content=True)


@router.callback_query(F.data == "fsm:cancel")
async def cancel_flow(
    callback: CallbackQuery,
    state: FSMContext,
    tier: SubscriptionTier | None,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    await state.clear()
    await callback.message.edit_text(
        t("umumiy.bekor_qilindi", language), reply_markup=main_menu(tier, language, is_admin)
    )
    await callback.answer()
