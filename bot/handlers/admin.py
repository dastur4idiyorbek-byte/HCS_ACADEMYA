"""Admin handlerlari (1.5-band).

Router `AdminOnlyMiddleware` bilan himoyalangan — oddiy foydalanuvchi uchun
yangilanish jimgina to'xtatiladi, admin panelning mavjudligi bildirilmaydi.

Handlerlar yupqa: qarorlarni `core/services/` va repository'lar qabul qiladi.
"""

from __future__ import annotations

from datetime import timedelta
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.i18n import t
from bot.keyboards import (
    admin_panel,
    back_button,
    cancel_button,
    halal_status_menu,
    payment_review,
    tier_choice,
)
from bot.middlewares import AdminOnlyMiddleware
from bot.states import (
    BroadcastFlow,
    CoinRulingFlow,
    ContentFlow,
    PaymentReviewFlow,
    PriceFlow,
    ViolationFlow,
)
from bot.ui import show_screen
from core.analysis.postmortem import build_report, render_report
from core.config.schema import AppConfig
from core.domain.enums import HalalStatus, SubscriptionTier
from core.pipeline import is_routine_stage, stage_label
from core.risk_engine import RiskEngine
from core.services import SubscriptionService
from core.storage import Database
from core.storage.models import User
from core.storage.repositories import (
    CoinRulingRepository,
    ContentRepository,
    MarketHealthRepository,
    PaymentRepository,
    PriceRepository,
    RiskBlockRepository,
    SignalRepository,
    SubscriptionRepository,
    UserRepository,
    ViolationRepository,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)


def _xavfsiz(matn: str) -> str:
    """Telegram HTML rejimi uchun matnni xavfsizlaydi.

    Xabarlar `parse_mode=HTML` bilan yuboriladi: matndagi ochiq `<`
    teg boshlanishi deb o'qiladi va Telegram BUTUN xabarni rad etadi
    (`can't parse entities`). Handler xato bilan tugaydi, tugma esa
    foydalanuvchi uchun shunchaki "javob bermaydi" — ekranda hech
    qanday xato ko'rinmaydi. Shuning uchun bazadan yoki tahlildan
    kelgan har bir qiymat shu yerdan o'tadi.

    `quote=False` — apostrof ATAYLAB qochirilmaydi. O'zbek matnida u
    har qadamda uchraydi ("sig'madi", "to'xtagan") va `&#x27;` ga
    aylansa ekranni o'qib bo'lmaydi. Matn tanasida uni qochirish
    shart emas: faqat `< > &` maxsus ma'noga ega.
    """
    return escape(matn, quote=False)

router = Router(name="admin")
router.message.middleware(AdminOnlyMiddleware())
router.callback_query.middleware(AdminOnlyMiddleware())


def _service(session, config: AppConfig) -> SubscriptionService:  # noqa: ANN001
    return SubscriptionService(
        config.subscriptions,
        UserRepository(session),
        SubscriptionRepository(session),
        PaymentRepository(session),
    )


# --------------------------------------------------------------------------- #
#  Panel
# --------------------------------------------------------------------------- #


@router.message(Command("panel"))
async def show_panel(
    message: Message, state: FSMContext, database: Database, language: str, **_: object
) -> None:
    await state.clear()
    async with database.session() as session:
        kutilayotgan = await PaymentRepository(session).pending_count()
    await show_screen(
        message,
        state,
        t("admin.salom", language, pending=kutilayotgan),
        reply_markup=admin_panel(language),
    )


@router.callback_query(F.data == "menu:panel")
async def open_panel_from_menu(
    callback: CallbackQuery,
    state: FSMContext,
    database: Database,
    language: str,
    **_: object,
) -> None:
    """Asosiy menyudagi «🛠 Admin panel» tugmasi.

    `/panel` buyrug'i bilan bir xil, faqat yozish shart emas. Router
    `AdminOnlyMiddleware` ostida, shuning uchun admin bo'lmagan bosishlar
    shu yerga umuman yetib kelmaydi.
    """
    await state.clear()
    async with database.session() as session:
        kutilayotgan = await PaymentRepository(session).pending_count()
    await callback.message.edit_text(
        t("admin.salom", language, pending=kutilayotgan),
        reply_markup=admin_panel(language),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:home")
async def panel_home(
    callback: CallbackQuery, state: FSMContext, database: Database, language: str, **_: object
) -> None:
    await state.clear()
    async with database.session() as session:
        kutilayotgan = await PaymentRepository(session).pending_count()
    await callback.message.edit_text(
        t("admin.salom", language, pending=kutilayotgan), reply_markup=admin_panel(language)
    )
    await callback.answer()


# --------------------------------------------------------------------------- #
#  1.2 — To'lovlarni ko'rib chiqish
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "admin:tolovlar")
async def list_payments(
    callback: CallbackQuery, database: Database, language: str, **_: object
) -> None:
    async with database.session() as session:
        tolovlar = await PaymentRepository(session).pending()
        kartochkalar = [
            (
                tolov.id,
                t(
                    "admin.tolov_kartochka",
                    language,
                    id=tolov.id,
                    user=tolov.user_id,
                    tier=tolov.tier,
                    period=tolov.period,
                    amount=f"{tolov.amount:,.0f}",
                    currency=tolov.currency,
                ),
                tolov.receipt_file_id,
            )
            for tolov in tolovlar
        ]

    if not kartochkalar:
        await callback.answer(t("admin.tolov_yoq", language), show_alert=True)
        return

    await callback.answer()
    for tolov_id, matn, chek in kartochkalar:
        klaviatura = payment_review(tolov_id, language)
        if chek:
            await callback.message.answer_photo(chek, caption=matn, reply_markup=klaviatura)
        else:
            await callback.message.answer(matn, reply_markup=klaviatura)


@router.callback_query(F.data.startswith("pay:approve:"))
async def approve_payment(
    callback: CallbackQuery, database: Database, config: AppConfig, language: str, **_: object
) -> None:
    tolov_id = int(callback.data.rsplit(":", 1)[1])

    async with database.session() as session:
        tolov = await PaymentRepository(session).get(tolov_id)
        if tolov is None:
            await callback.answer(t("umumiy.xato", language), show_alert=True)
            return
        natija = await _service(session, config).approve_payment(tolov, callback.from_user.id)
        egasi = await session.get(User, tolov.user_id)
        egasi_tg = egasi.telegram_id if egasi else None
        muddat = natija.subscription.expires_at if natija.subscription else None

    if not natija.approved:
        await callback.answer(t(natija.message_key, language), show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(t("admin.tolov_tasdiqlandi", language, id=tolov_id))

    if egasi_tg:
        await callback.bot.send_message(
            egasi_tg,
            t("obuna.tasdiqlandi", language, expires=muddat.strftime("%Y-%m-%d %H:%M")),
        )


@router.callback_query(F.data.startswith("pay:reject:"))
async def ask_reject_reason(
    callback: CallbackQuery, state: FSMContext, language: str, **_: object
) -> None:
    await state.set_state(PaymentReviewFlow.waiting_reject_reason)
    await state.update_data(payment_id=int(callback.data.rsplit(":", 1)[1]))
    await callback.message.answer(
        t("admin.rad_sababi", language), reply_markup=cancel_button(language)
    )
    await callback.answer()


@router.message(PaymentReviewFlow.waiting_reject_reason)
async def reject_payment(
    message: Message,
    state: FSMContext,
    database: Database,
    config: AppConfig,
    language: str,
    **_: object,
) -> None:
    data = await state.get_data()
    sabab = (message.text or "").strip()

    async with database.session() as session:
        tolov = await PaymentRepository(session).get(data["payment_id"])
        if tolov is None:
            await message.answer(t("umumiy.xato", language))
            await state.clear()
            return
        await _service(session, config).reject_payment(tolov, message.from_user.id, sabab)
        egasi = await session.get(User, tolov.user_id)
        egasi_tg = egasi.telegram_id if egasi else None

    await state.clear()
    await message.answer(t("admin.tolov_rad_etildi", language, id=data["payment_id"]))
    if egasi_tg:
        await message.bot.send_message(egasi_tg, t("obuna.rad_etildi", language, reason=sabab))


# --------------------------------------------------------------------------- #
#  1.2 — Narxlarni sozlash
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "admin:narxlar")
async def price_choose_tier(callback: CallbackQuery, language: str, **_: object) -> None:
    await callback.message.edit_text(
        t("admin.narx_tarif_tanlang", language), reply_markup=tier_choice("price", language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("price:"))
async def price_ask_amount(
    callback: CallbackQuery, state: FSMContext, config: AppConfig, language: str, **_: object
) -> None:
    tier = SubscriptionTier(callback.data.split(":", 1)[1])
    await state.set_state(PriceFlow.waiting_amount)
    await state.update_data(
        tier=tier.value, period="monthly", currency=config.subscriptions.currencies[0]
    )
    await callback.message.edit_text(t("admin.narx_summa", language))
    await callback.answer()


@router.message(PriceFlow.waiting_amount)
async def price_ask_details(
    message: Message, state: FSMContext, language: str, **_: object
) -> None:
    try:
        summa = float(message.text.replace(",", ".").replace(" ", ""))
    except (ValueError, AttributeError):
        await message.answer(t("umumiy.raqam_kiriting", language))
        return
    if summa <= 0:
        await message.answer(t("umumiy.musbat_raqam_kiriting", language))
        return

    await state.update_data(amount=summa)
    await state.set_state(PriceFlow.waiting_details)
    await message.answer(t("admin.narx_rekvizit", language))


@router.message(PriceFlow.waiting_details)
async def price_save(
    message: Message, state: FSMContext, database: Database, language: str, **_: object
) -> None:
    data = await state.get_data()
    rekvizit = None if (message.text or "").strip() == "/skip" else message.text

    async with database.session() as session:
        await PriceRepository(session).upsert(
            SubscriptionTier(data["tier"]),
            data["period"],
            data["currency"],
            data["amount"],
            rekvizit,
        )

    await state.clear()
    await message.answer(
        t(
            "admin.narx_saqlandi",
            language,
            tier=data["tier"],
            period=data["period"],
            amount=f"{data['amount']:,.0f}",
            currency=data["currency"],
        ),
        reply_markup=admin_panel(language),
    )


# --------------------------------------------------------------------------- #
#  1.4 — Halol coin ro'yxati
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "admin:halol_royxat")
async def halal_list(
    callback: CallbackQuery, state: FSMContext, database: Database, language: str, **_: object
) -> None:
    async with database.session() as session:
        qarorlar = CoinRulingRepository(session)
        haram = [q.symbol for q in await qarorlar.list_by_status(HalalStatus.HARAM)]
        mashbooh = [q.symbol for q in await qarorlar.list_by_status(HalalStatus.MASHBOOH)]

    await state.set_state(CoinRulingFlow.waiting_symbol)
    await callback.message.edit_text(
        t("admin.coin_royxat", language, haram=", ".join(haram) or "—",
          mashbooh=", ".join(mashbooh) or "—")
        + "\n\n"
        + t("admin.coin_soralmoqda", language)
    )
    await callback.answer()


@router.message(CoinRulingFlow.waiting_symbol)
async def coin_choose_status(
    message: Message, state: FSMContext, language: str, **_: object
) -> None:
    symbol = (message.text or "").strip().upper()
    if not symbol.isalnum():
        await message.answer(t("admin.coin_soralmoqda", language))
        return
    await state.update_data(symbol=symbol)
    await message.answer(
        t("admin.coin_holat_tanlang", language, symbol=symbol),
        reply_markup=halal_status_menu(symbol, language),
    )


@router.callback_query(F.data.startswith("coin:"))
async def coin_ask_reason(
    callback: CallbackQuery, state: FSMContext, language: str, **_: object
) -> None:
    _, symbol, status = callback.data.split(":")
    await state.set_state(CoinRulingFlow.waiting_reason)
    await state.update_data(symbol=symbol, status=status)
    await callback.message.edit_text(t("admin.coin_sabab", language))
    await callback.answer()


@router.message(CoinRulingFlow.waiting_reason)
async def coin_save(
    message: Message, state: FSMContext, database: Database, language: str, **_: object
) -> None:
    data = await state.get_data()
    async with database.session() as session:
        await CoinRulingRepository(session).set_ruling(
            data["symbol"],
            HalalStatus(data["status"]),
            (message.text or "").strip(),
            set_by=message.from_user.id,
        )

    await state.clear()
    logger.info("Coin qarori o'zgardi: %s -> %s", data["symbol"], data["status"])
    await message.answer(
        t("admin.coin_saqlandi", language, symbol=data["symbol"], status=data["status"]),
        reply_markup=admin_panel(language),
    )


# --------------------------------------------------------------------------- #
#  1.3 — Qoidabuzarlik
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "admin:qoidabuzarlik")
async def violation_ask_user(
    callback: CallbackQuery, state: FSMContext, language: str, **_: object
) -> None:
    await state.set_state(ViolationFlow.waiting_user_id)
    await callback.message.edit_text(t("admin.qoidabuzarlik_id", language))
    await callback.answer()


@router.message(ViolationFlow.waiting_user_id)
async def violation_ask_reason(
    message: Message, state: FSMContext, database: Database, language: str, **_: object
) -> None:
    try:
        telegram_id = int((message.text or "").strip())
    except ValueError:
        await message.answer(t("umumiy.raqam_kiriting", language))
        return

    async with database.session() as session:
        user = await UserRepository(session).get_by_telegram_id(telegram_id)
        topildi = user is not None
        user_id = user.id if user else None

    if not topildi:
        await message.answer(t("admin.foydalanuvchi_topilmadi", language))
        return

    await state.update_data(user_id=user_id, telegram_id=telegram_id)
    await state.set_state(ViolationFlow.waiting_reason)
    await message.answer(t("admin.qoidabuzarlik_sabab", language))


@router.message(ViolationFlow.waiting_reason)
async def violation_apply(
    message: Message, state: FSMContext, database: Database, language: str, **_: object
) -> None:
    """1.3-band: ogohlantirish yuboriladi va tarif vaqtincha to'xtatiladi."""
    data = await state.get_data()
    sabab = (message.text or "").strip()

    async with database.session() as session:
        await ViolationRepository(session).record(
            data["user_id"], sabab, reported_by=message.from_user.id
        )
        obunalar = SubscriptionRepository(session)
        obuna = await obunalar.active_for(data["user_id"])
        if obuna is not None:
            await obunalar.suspend(obuna, sabab)

    await state.clear()
    logger.warning("Qoidabuzarlik qayd etildi: user=%s sabab=%s", data["telegram_id"], sabab)

    await message.bot.send_message(
        data["telegram_id"], t("qoidabuzarlik.ogohlantirish", language)
    )
    await message.answer(
        t("admin.qoidabuzarlik_bajarildi", language), reply_markup=admin_panel(language)
    )


# --------------------------------------------------------------------------- #
#  1.5 — Broadcast
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "admin:broadcast")
async def broadcast_ask(
    callback: CallbackQuery, state: FSMContext, language: str, **_: object
) -> None:
    await state.set_state(BroadcastFlow.waiting_message)
    await callback.message.edit_text(
        t("admin.broadcast_matn", language), reply_markup=cancel_button(language)
    )
    await callback.answer()


@router.message(BroadcastFlow.waiting_message)
async def broadcast_send(
    message: Message, state: FSMContext, database: Database, language: str, **_: object
) -> None:
    async with database.session() as session:
        qabul_qiluvchilar = await UserRepository(session).all_telegram_ids()

    yuborildi = xato = 0
    for telegram_id in qabul_qiluvchilar:
        try:
            await message.bot.send_message(telegram_id, message.text or "")
            yuborildi += 1
        except Exception:  # noqa: BLE001 — bitta bloklangan foydalanuvchi tarqatishni to'xtatmasin
            xato += 1

    await state.clear()
    logger.info("Broadcast: yuborildi=%d xato=%d", yuborildi, xato)
    await message.answer(
        t("admin.broadcast_natija", language, sent=yuborildi, failed=xato),
        reply_markup=admin_panel(language),
    )


# --------------------------------------------------------------------------- #
#  1.5 — Kontent qo'shish
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "admin:kontent")
async def content_ask_title(
    callback: CallbackQuery, state: FSMContext, language: str, **_: object
) -> None:
    await state.set_state(ContentFlow.waiting_title)
    await callback.message.edit_text(t("admin.kontent_sarlavha", language))
    await callback.answer()


@router.message(ContentFlow.waiting_title)
async def content_ask_tier(
    message: Message, state: FSMContext, language: str, **_: object
) -> None:
    await state.update_data(title=(message.text or "").strip())
    await message.answer(
        t("admin.kontent_tarif", language), reply_markup=tier_choice("ctier", language)
    )


@router.callback_query(F.data.startswith("ctier:"))
async def content_ask_file(
    callback: CallbackQuery, state: FSMContext, language: str, **_: object
) -> None:
    await state.update_data(min_tier=callback.data.split(":", 1)[1])
    await state.set_state(ContentFlow.waiting_file)
    await callback.message.edit_text(t("admin.kontent_fayl", language))
    await callback.answer()


@router.message(ContentFlow.waiting_file)
async def content_save(
    message: Message, state: FSMContext, database: Database, language: str, **_: object
) -> None:
    data = await state.get_data()
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id

    async with database.session() as session:
        await ContentRepository(session).add(
            kind="video" if file_id else "strategy",
            title=data["title"],
            file_id=file_id,
            min_tier=SubscriptionTier(data["min_tier"]),
        )

    await state.clear()
    await message.answer(
        t("admin.kontent_saqlandi", language, title=data["title"]),
        reply_markup=admin_panel(language),
    )


# --------------------------------------------------------------------------- #
#  3.7 — Bozor Salomatligi dashboardi
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "admin:salomatlik")
async def market_health_dashboard(
    callback: CallbackQuery,
    database: Database,
    config: AppConfig,
    language: str,
    **_: object,
) -> None:
    """3.7-band: "tizim nega sokin/faol" degan savolga bitta raqam bilan javob."""
    async with database.session() as session:
        repo = MarketHealthRepository(session)
        oxirgi = await repo.latest()
        tarix = await repo.history(limit=8)
        qiymatlar = [f"{yozuv.value:.0f}" for yozuv in reversed(tarix)]

    if oxirgi is None:
        await callback.message.edit_text(
            t("admin.salomatlik_yoq", language), reply_markup=back_button("home", language)
        )
        await callback.answer()
        return

    matn = _render_health(oxirgi)

    chegara = RiskEngine(config).score_threshold(oxirgi.value)
    matn += (
        t("admin.salomatlik_chegara", language, threshold=f"{chegara:.0f}")
        if chegara is not None
        else t("admin.salomatlik_chegara_yopiq", language)
    )
    if len(qiymatlar) > 1:
        matn += t("admin.salomatlik_tarix", language, values=" → ".join(qiymatlar))

    await callback.message.edit_text(matn, reply_markup=back_button("home", language))
    await callback.answer()


def _render_health(record) -> str:  # noqa: ANN001
    """Bazadagi yozuvdan dashboard matnini quradi."""
    belgilar = {"high": "🟢", "mid": "🟡", "low": "🔴"}
    izohlar = {
        "high": "signal chegarasi past — erkin rejim",
        "mid": "signal beriladi, lekin ehtiyotkorroq",
        "low": "yangi signal to'xtatilgan — faqat kuzatuv",
    }
    qatorlar = [
        f"{belgilar[record.band]} Bozor Salomatligi: {record.value:.0f}/100",
        f"   {izohlar[record.band]}",
        "",
    ]
    if record.detail:
        qatorlar.extend(f"• {_xavfsiz(qator)}" for qator in record.detail.splitlines())
    if record.is_daily_preview:
        qatorlar.append("\n⏱ Bu — kunlik oldindan tahlil (hali o'lchanmagan)")
    return "\n".join(qatorlar)


# --------------------------------------------------------------------------- #
#  3.7 — "Nega signal yo'q" dashboardi
# --------------------------------------------------------------------------- #

#: Sokinlik hisoboti qancha vaqtni qamrab oladi
SOKINLIK_SOATLARI = 24


@router.callback_query(F.data == "admin:sokinlik")
async def silence_dashboard(
    callback: CallbackQuery,
    database: Database,
    language: str,
    **_: object,
) -> None:
    """3.7-band: signal chiqmaganda SABABI ko'rinishi kerak.

    Signal bermaslik xato emas (0.2-band) — lekin sababi ko'rinmasa,
    ishlayotgan tizimni buzuq tizimdan ajratib bo'lmaydi. Bu ekran aynan
    shu farqni beradi.
    """
    boshlanish = utc_now() - timedelta(hours=SOKINLIK_SOATLARI)

    async with database.session() as session:
        repo = RiskBlockRepository(session)
        xulosa = await repo.summary_since(boshlanish)
        oxirgilar = await repo.latest(limit=3)

    if not xulosa:
        await callback.message.edit_text(
            t("admin.sokinlik_yoq", language, hours=SOKINLIK_SOATLARI),
            reply_markup=back_button("home", language),
        )
        await callback.answer()
        return

    matn = t("admin.sokinlik_sarlavha", language, hours=SOKINLIK_SOATLARI)
    matn += _render_silence(xulosa, language)

    matn += _render_latest(oxirgilar, language)

    await callback.message.edit_text(matn, reply_markup=back_button("home", language))
    await callback.answer()


def _render_silence(summary: list[tuple[str, int, bool]], language: str) -> str:
    """Rad etish sabablarini UCH GURUHGA ajratib ko'rsatadi.

    Nima uchun bitta ro'yxat yetarli emas edi: yozuvlar bir xil
    o'lchovda emas.

    1. Coin tahlili — har coin, har sikl uchun bitta yozuv.
    2. Sikl darajasi — bitta yozuv BARCHA coinlarni to'xtatadi
       (`symbol` yo'q). Bittasi 30 tasiga teng.
    3. Vaqt shartlari — skalping oynasi kuniga 45 daqiqa ochiq, ya'ni
       "oyna yopiq" yozuvi vaqtning 96% ida chiqadi. Bu tashxis emas,
       soat ko'rsatkichi.

    Uchalasi bitta ustunda qo'shilganda vaqt sharti birinchi o'rinni
    egallab, haqiqiy sabablarni pastga surib yuborardi.
    """
    tahlil: list[tuple[str, int]] = []
    sikl: list[tuple[str, int]] = []
    vaqt: list[tuple[str, int]] = []

    for sabab, soni, sikl_darajasi in summary:
        if is_routine_stage(sabab):
            vaqt.append((sabab, soni))
        elif sikl_darajasi:
            sikl.append((sabab, soni))
        else:
            tahlil.append((sabab, soni))

    matn = ""
    if tahlil:
        jami = sum(soni for _, soni in tahlil)
        matn += t("admin.sokinlik_tahlil", language, total=jami)
        for sabab, soni in tahlil:
            ulush = _xavfsiz(_ulush(soni, jami))
            matn += f"• {_xavfsiz(stage_label(sabab))} — {soni} marta ({ulush})\n"

    if sikl:
        matn += t("admin.sokinlik_sikl", language)
        for sabab, soni in sikl:
            matn += f"• {_xavfsiz(stage_label(sabab))} — {soni} marta\n"

    if vaqt:
        matn += t("admin.sokinlik_vaqt", language)
        for sabab, soni in vaqt:
            matn += f"• {_xavfsiz(stage_label(sabab))} — {soni} marta\n"

    matn += t("admin.sokinlik_izoh", language)
    return matn


def _render_latest(records: list, language: str) -> str:  # noqa: ANN001
    """Oxirgi rad etishlar — tafsiloti bilan.

    Tafsilot matni TAHLILDAN keladi va unda `<` bo'lishi mumkin
    (masalan "Ball 62 < chegara 70"). Telegram HTML rejimida bu teg
    boshlanishi deb o'qiladi va BUTUN xabar rad etiladi — ya'ni bitta
    qator butun ekranni ochilmas qiladi. Shuning uchun ekranga
    chiqadigan har bir qiymat qalqondan o'tadi.
    """
    if not records:
        return ""

    matn = t("admin.sokinlik_oxirgi", language)
    for yozuv in records:
        coin = yozuv.symbol or "—"
        tafsilot = (yozuv.detail or "")[:120]
        matn += f"• {_xavfsiz(coin)}: {_xavfsiz(tafsilot)}\n"
    return matn


def _ulush(count: int, total: int) -> str:
    """Foiz. Nolga yaxlitlanadigan qiymat `<1%` deb yoziladi.

    Avval `{:.0f}%` ishlatilardi: 5 marta sodir bo'lgan sabab "0%" deb
    ko'rinardi — ya'ni "bo'ldi" va "bo'lmadi" bitta qatorda yozilgan
    edi. Kichik son ham nol emas.
    """
    if total <= 0:
        return "—"
    matn = f"{count / total * 100:.0f}%"
    return "<1%" if matn == "0%" else matn


# --------------------------------------------------------------------------- #
#  3.8 — O'z-o'zini tekshirish hisoboti
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "admin:hisobot")
async def self_audit_report(
    callback: CallbackQuery,
    database: Database,
    config: AppConfig,
    language: str,
    **_: object,
) -> None:
    """3.8-band: haftalik hisobot. Tavsiyalar AVTOMATIK qo'llanilmaydi."""
    hozir = utc_now()
    boshlanish = hozir - timedelta(days=config.postmortem.lookback_days)

    async with database.session() as session:
        signallar = await SignalRepository(session).closed_since(boshlanish)

    hisobot = build_report(signallar, config.postmortem, hozir)
    await callback.message.edit_text(
        render_report(hisobot), reply_markup=back_button("home", language)
    )
    await callback.answer()


# --------------------------------------------------------------------------- #
#  Hali qurilmagan bo'limlar (10, 13 va 9-bosqichlarda ulanadi)
# --------------------------------------------------------------------------- #


@router.callback_query(F.data.in_({"admin:risk"}))
async def not_ready_yet(callback: CallbackQuery, language: str, **_: object) -> None:
    bosqichlar = {
        "admin:risk": "Risk sozlamalari tahriri — 9-bosqich ustiga qo'shiladi.",
    }
    await callback.message.edit_text(
        bosqichlar[callback.data], reply_markup=back_button("home", language)
    )
    await callback.answer()
