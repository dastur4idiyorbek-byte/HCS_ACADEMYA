"""2-bo'lim: qo'lda signal kiritish va signallarni ko'rsatish.

Admin FSM: Coin → Entry → Stop → TP1 → TP2 → izoh → preview → tasdiqlash

Darajalar tartibi (Stop < Entry < TP1 < TP2) `SignalLevels` ichida avtomatik
tekshiriladi — noto'g'ri tartib bazaga umuman yetib bormaydi.

1.3-band: signallar `protect_content=True` bilan yuboriladi.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.formatting import render_signal_card
from bot.i18n import t
from bot.keyboards import admin_panel, back_button, cancel_button, signal_actions
from bot.middlewares import AdminOnlyMiddleware
from bot.states import SignalFlow
from core.analysis import decide_entry_plan
from core.config.schema import AppConfig
from core.domain.enums import SignalSource, SignalStatus, SubscriptionTier
from core.domain.models import EntryPlan, PositionSuggestion, SignalLevels
from core.market_data import CandleProvider
from core.position_sizing import PositionSizer
from core.storage import Database
from core.storage.repositories import (
    SignalRepository,
    SubscriptionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

admin_router = Router(name="signals_admin")
admin_router.message.middleware(AdminOnlyMiddleware())
admin_router.callback_query.middleware(AdminOnlyMiddleware())

user_router = Router(name="signals_user")


def _parse_price(text: str | None) -> float | None:
    try:
        qiymat = float((text or "").replace(",", ".").replace(" ", ""))
    except ValueError:
        return None
    return qiymat if qiymat > 0 else None


# --------------------------------------------------------------------------- #
#  Admin: qo'lda signal kiritish
# --------------------------------------------------------------------------- #


@admin_router.callback_query(F.data == "admin:yangi_signal")
async def signal_ask_symbol(
    callback: CallbackQuery, state: FSMContext, language: str, **_: object
) -> None:
    await state.set_state(SignalFlow.waiting_symbol)
    await callback.message.edit_text(
        t("admin.signal_coin", language), reply_markup=cancel_button(language)
    )
    await callback.answer()


@admin_router.message(SignalFlow.waiting_symbol)
async def signal_ask_entry(
    message: Message, state: FSMContext, language: str, **_: object
) -> None:
    symbol = (message.text or "").strip().upper()
    if not symbol.isalnum():
        await message.answer(t("admin.signal_coin", language))
        return
    await state.update_data(symbol=symbol)
    await state.set_state(SignalFlow.waiting_entry)
    await message.answer(t("admin.signal_entry", language))


@admin_router.message(SignalFlow.waiting_entry)
async def signal_ask_stop(
    message: Message, state: FSMContext, language: str, **_: object
) -> None:
    narx = _parse_price(message.text)
    if narx is None:
        await message.answer(t("umumiy.musbat_raqam_kiriting", language))
        return
    await state.update_data(entry=narx)
    await state.set_state(SignalFlow.waiting_stop)
    await message.answer(t("admin.signal_stop", language))


@admin_router.message(SignalFlow.waiting_stop)
async def signal_ask_tp1(
    message: Message, state: FSMContext, language: str, **_: object
) -> None:
    narx = _parse_price(message.text)
    if narx is None:
        await message.answer(t("umumiy.musbat_raqam_kiriting", language))
        return
    await state.update_data(stop=narx)
    await state.set_state(SignalFlow.waiting_tp1)
    await message.answer(t("admin.signal_tp1", language))


@admin_router.message(SignalFlow.waiting_tp1)
async def signal_ask_tp2(
    message: Message, state: FSMContext, language: str, **_: object
) -> None:
    narx = _parse_price(message.text)
    if narx is None:
        await message.answer(t("umumiy.musbat_raqam_kiriting", language))
        return
    await state.update_data(tp1=narx)
    await state.set_state(SignalFlow.waiting_tp2)
    await message.answer(t("admin.signal_tp2", language))


@admin_router.message(SignalFlow.waiting_tp2)
async def signal_ask_note(
    message: Message, state: FSMContext, language: str, **_: object
) -> None:
    narx = _parse_price(message.text)
    if narx is None:
        await message.answer(t("umumiy.musbat_raqam_kiriting", language))
        return
    await state.update_data(tp2=narx)
    await state.set_state(SignalFlow.waiting_note)
    await message.answer(t("admin.signal_izoh", language))


@admin_router.message(SignalFlow.waiting_note)
async def signal_preview(
    message: Message,
    state: FSMContext,
    config: AppConfig,
    language: str,
    candles: CandleProvider | None = None,
    **_: object,
) -> None:
    """Darajalar tartibini tekshirib, ko'rib chiqish uchun kartochka chiqaradi."""
    data = await state.get_data()
    izoh = None if (message.text or "").strip() == "/skip" else (message.text or "").strip()

    try:
        levels = SignalLevels(
            entry=data["entry"], stop=data["stop"], tp1=data["tp1"], tp2=data["tp2"]
        )
    except ValueError as exc:
        # Tartib xato — boshidan boshlamasdan, faqat Stop'dan qayta so'raymiz
        await state.set_state(SignalFlow.waiting_stop)
        await message.answer(t("admin.signal_tartib_xato", language, detail=str(exc)))
        return

    narx = await joriy_narx(
        candles, data["symbol"], config.analysis.entry_timeframe, levels.entry
    )
    reja = decide_entry_plan(narx, levels, config.analysis.entry_order)
    kartochka = render_signal_card(
        data["symbol"], levels, reja,
        quote_asset=config.halal_screening.quote_asset,
        language=language,
        tp1_close_pct=config.portfolio.tp1_close_pct,
    )

    # 3.3-band qoidalari qo'lda signalda MAJBURIY emas — admin bilib turib
    # yuborishi mumkin, lekin ogohlantiriladi.
    ogohlantirishlar = _rule_warnings(levels, config)

    await state.update_data(note=izoh)
    await state.set_state(SignalFlow.waiting_confirm)

    builder = InlineKeyboardBuilder()
    builder.button(text=t("umumiy.tasdiqlash", language), callback_data="signal:send")
    builder.button(text=t("umumiy.bekor", language), callback_data="signal:cancel")
    builder.adjust(2)

    await message.answer(
        t("admin.signal_preview", language, card=kartochka, note=izoh or ""),
        reply_markup=builder.as_markup(),
    )
    if ogohlantirishlar:
        await message.answer(
            t("admin.signal_qoida_buzildi", language, reasons="; ".join(ogohlantirishlar))
        )


def _rule_warnings(levels: SignalLevels, config: AppConfig) -> list[str]:
    """3.3-band: universal risk qoidalariga mos kelmasa ogohlantirish."""
    rules = config.trade_rules
    ogohlar: list[str] = []
    if levels.stop_distance_pct > rules.max_stop_distance_pct:
        ogohlar.append(
            f"Stop masofasi {levels.stop_distance_pct:.2f}% "
            f"(chegara {rules.max_stop_distance_pct}%)"
        )
    for nom, masofa in (("TP1", levels.tp1_distance_pct), ("TP2", levels.tp2_distance_pct)):
        if not rules.min_tp_distance_pct <= masofa <= rules.max_tp_distance_pct:
            ogohlar.append(
                f"{nom} masofasi {masofa:.2f}% "
                f"({rules.min_tp_distance_pct}–{rules.max_tp_distance_pct}% oralig'idan tashqarida)"
            )
    if levels.risk_reward_tp2 < rules.min_risk_reward:
        ogohlar.append(f"TP2 R/R {levels.risk_reward_tp2:.2f} < {rules.min_risk_reward}")
    return ogohlar


@admin_router.callback_query(SignalFlow.waiting_confirm, F.data == "signal:cancel")
async def signal_cancel(
    callback: CallbackQuery, state: FSMContext, language: str, **_: object
) -> None:
    await state.clear()
    await callback.message.edit_text(
        t("admin.signal_bekor", language), reply_markup=admin_panel(language)
    )
    await callback.answer()


@admin_router.callback_query(SignalFlow.waiting_confirm, F.data == "signal:send")
async def signal_send(
    callback: CallbackQuery,
    state: FSMContext,
    database: Database,
    config: AppConfig,
    language: str,
    candles: CandleProvider | None = None,
    watcher=None,  # noqa: ANN001 — `bot/main.py` dispatcher orqali uzatadi
    **_: object,
) -> None:
    """Signalni bazaga yozadi, kuzatuvga qo'shadi va obunachilarga tarqatadi."""
    data = await state.get_data()
    levels = SignalLevels(
        entry=data["entry"], stop=data["stop"], tp1=data["tp1"], tp2=data["tp2"]
    )
    narx = await joriy_narx(
        candles, data["symbol"], config.analysis.entry_timeframe, levels.entry
    )
    reja = decide_entry_plan(narx, levels, config.analysis.entry_order)

    async with database.session() as session:
        yozuv = await SignalRepository(session).create(
            symbol=data["symbol"],
            levels=levels,
            source=SignalSource.MANUAL,
            entry_plan=reja,
            note=data.get("note"),
            correlation_group=config.risk_engine.correlation_group_of(data["symbol"]),
        )
        signal_id = yozuv.id
        qabul_qiluvchilar = await _subscriber_ids(session)

    # Kuzatuvchi darhol xabardor bo'lsin — aks holda signal keyingi qayta
    # ishga tushirishgacha kuzatuvsiz qolardi.
    if watcher is not None:
        watcher.add_signal(signal_id)

    yuborildi = await _broadcast_signal(
        callback.bot, qabul_qiluvchilar, data["symbol"], levels, reja,
        signal_id, config, language,
    )

    await state.clear()
    logger.info("Qo'lda signal yuborildi: id=%s symbol=%s -> %d ta", signal_id,
                data["symbol"], yuborildi)
    await callback.message.edit_text(
        t("admin.signal_yuborildi", language, sent=yuborildi), reply_markup=admin_panel(language)
    )
    await callback.answer()


async def joriy_narx(
    candles: CandleProvider | None, symbol: str, timeframe: str, fallback: float
) -> float:
    """Bozordagi oxirgi narx. Olinmasa `fallback` (kirish narxi).

    Nima uchun kerak: buyurtma turi (Limit/Market) narx Entry zonasiga
    yetganmi-yo'qmi degan savolga bog'liq. Avval bu yerga Entry narxining
    o'zi uzatilardi — ya'ni "narx allaqachon joyida" deb hisoblanardi va
    kartochka HAR DOIM "Hozir oling" derdi, kuzatuvchi esa "Kutilmoqda"
    derdi. Bitta xabarda ikkita qarama-qarshi gap.

    Narx olinmasa signal to'xtamaydi — eski xatti-harakat qoladi
    (0.3-band).
    """
    if candles is None:
        return fallback
    try:
        seriya = await candles.fetch_candles(symbol, timeframe, limit=1)
    except Exception:  # noqa: BLE001 — narxsiz ham signal ketaversin
        logger.warning("Joriy narx olinmadi: %s", symbol, exc_info=True)
        return fallback
    return seriya[-1].close if seriya else fallback


async def _subscriber_ids(session) -> list[tuple[int, float | None]]:  # noqa: ANN001
    """Signal ko'rishga haqli obunachilar: `(telegram_id, balans)`.

    Balans ham kerak, chunki pozitsiya hajmi har kimda boshqacha
    (5.1-band) — kartochka har bir qabul qiluvchi uchun alohida yasaladi.
    """
    users = UserRepository(session)
    obunalar = SubscriptionRepository(session)
    natija: list[tuple[int, float | None]] = []
    for user in await users.active_users(since_days=90):
        tier = await obunalar.tier_for(user.id)
        if tier is not None and tier.covers(SubscriptionTier.LITE):
            natija.append((user.telegram_id, user.declared_balance_usd))
    return natija


def suggest_size(
    symbol: str, levels: SignalLevels, balance: float | None, config: AppConfig
) -> PositionSuggestion | None:
    """5.1-band: shu foydalanuvchi uchun pozitsiya hajmi.

    `commit=False` — bu faqat ko'rsatish uchun hisob; xavf byudjeti
    foydalanuvchi "Men kirdim" deganda band qilinadi (5.4-band).

    Hisoblab bo'lmasa `None`: miqdorsiz bo'lsa ham signal yuboriladi
    (0.3-band).
    """
    if balance is None or balance <= 0:
        return None
    try:
        sizer = PositionSizer(config.position_sizing)
        return sizer.suggest(symbol, levels, sizer.budget_for(balance), commit=False)
    except Exception:  # noqa: BLE001
        logger.warning("Pozitsiya hajmi hisoblanmadi: %s", symbol, exc_info=True)
        return None


async def _broadcast_signal(  # noqa: PLR0913
    bot,  # noqa: ANN001
    recipients: list[tuple[int, float | None]],
    symbol: str,
    levels: SignalLevels,
    entry_plan: EntryPlan,
    signal_id: int,
    config: AppConfig,
    language: str,
) -> int:
    """1.3-band: `protect_content=True` — forward/saqlash bloklanadi.

    Kartochka HAR BIR qabul qiluvchi uchun alohida yasaladi: miqdor
    ularning o'z balansidan hisoblanadi (5.1-band).
    """
    yuborildi = 0
    for telegram_id, balans in recipients:
        kartochka = render_signal_card(
            symbol,
            levels,
            entry_plan,
            suggestion=suggest_size(symbol, levels, balans, config),
            quote_asset=config.halal_screening.quote_asset,
            language=language,
            tp1_close_pct=config.portfolio.tp1_close_pct,
        )
        try:
            await bot.send_message(
                telegram_id,
                kartochka,
                protect_content=True,
                reply_markup=signal_actions(signal_id, language),
            )
            yuborildi += 1
        except Exception:  # noqa: BLE001 — bitta xato tarqatishni to'xtatmasin
            logger.warning("Signal yetkazilmadi: telegram_id=%s", telegram_id)
    return yuborildi


# --------------------------------------------------------------------------- #
#  Foydalanuvchi: faol signallar ro'yxati
# --------------------------------------------------------------------------- #


@user_router.callback_query(F.data == "menu:signallar")
async def list_signals(
    callback: CallbackQuery,
    database: Database,
    config: AppConfig,
    tier: SubscriptionTier | None,
    language: str,
    **_: object,
) -> None:
    if tier is None:
        await callback.answer(t("umumiy.ruxsat_yoq", language), show_alert=True)
        return

    async with database.session() as session:
        yozuvlar = await SignalRepository(session).open_signals()
        kartochkalar = [
            (
                yozuv.id,
                render_signal_card(
                    yozuv.symbol,
                    SignalLevels(yozuv.entry, yozuv.stop, yozuv.tp1, yozuv.tp2),
                    decide_entry_plan(
                        yozuv.price_at_signal or yozuv.entry,
                        SignalLevels(yozuv.entry, yozuv.stop, yozuv.tp1, yozuv.tp2),
                        config.analysis.entry_order,
                    ),
                    quote_asset=config.halal_screening.quote_asset,
                    language=language,
                    tp1_close_pct=config.portfolio.tp1_close_pct,
                ),
                SignalStatus(yozuv.status),
            )
            for yozuv in yozuvlar
        ]

    if not kartochkalar:
        await callback.answer(t("signal.royxat_bosh", language), show_alert=True)
        return

    await callback.answer()
    for signal_id, kartochka, status in kartochkalar:
        holat = t(f"signal.holat_{status.value}", language)
        await callback.message.answer(
            f"{kartochka}\n\n{holat}",
            protect_content=True,
            reply_markup=signal_actions(signal_id, language),
        )


@user_router.callback_query(F.data.startswith("sig:why:"))
async def explain_signal(
    callback: CallbackQuery, database: Database, language: str, **_: object
) -> None:
    """3.6-band: "Nega bu signal?" — ball tafsiloti."""
    signal_id = int(callback.data.rsplit(":", 1)[1])
    async with database.session() as session:
        yozuv = await SignalRepository(session).get(signal_id)
        tafsilot = yozuv.score_breakdown if yozuv else None
        izoh = yozuv.note if yozuv else None

    matn = tafsilot or izoh or (
        "Bu signal admin tomonidan qo'lda kiritilgan — avtomatik ball tafsiloti yo'q."
    )
    await callback.message.answer(matn, reply_markup=back_button(language=language))
    await callback.answer()


@user_router.callback_query(F.data.startswith("sig:halal:"))
async def explain_halal(
    callback: CallbackQuery, database: Database, language: str, **_: object
) -> None:
    """3.6-band: "Nega bu coin halol?"."""
    signal_id = int(callback.data.rsplit(":", 1)[1])
    async with database.session() as session:
        yozuv = await SignalRepository(session).get(signal_id)
        sabab = yozuv.halal_reason if yozuv else None

    matn = sabab or (
        "Bu coin halol ro'yxatidan tanlangan: harom yoki shubhali toifalarga "
        "kirmaydi (foizli qarz, qimor, an'anaviy moliya derivativlari)."
    )
    await callback.message.answer(matn, reply_markup=back_button(language=language))
    await callback.answer()
