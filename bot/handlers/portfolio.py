"""5.4-band: shaxsiy portfel va umumiy statistika.

Shaxsiy tomon: "Men kirdim" tugmasi -> miqdor -> avtomatik foyda/zarar.
Umumiy tomon: hammaga ochiq shaffoflik raqamlari (3.6-band).

MUHIM: shaxsiy ma'lumot umumiy statistikada OSHKOR QILINMAYDI — faqat
agregat (nechta ishtirokchi, jami hajm).
"""

from __future__ import annotations

from datetime import timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.i18n import t
from bot.keyboards import back_button, main_menu
from bot.services.broadcast import hajm_taklifi
from bot.states import PositionFlow
from core.config.schema import AppConfig
from core.domain.enums import SignalStatus, SubscriptionTier
from core.domain.models import SignalLevels
from core.services import summarize
from core.storage import Database
from core.storage.repositories import (
    DailyStatsRepository,
    SignalRepository,
    UserPositionRepository,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)
router = Router(name="portfolio")


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:+.2f}%"


def _usd(value: float | None) -> str:
    return "—" if value is None else f"${value:+,.2f}"


def _hajm_taklifi(yozuv, balans: float | None, config: AppConfig) -> float | None:  # noqa: ANN001
    """Shu signal uchun tavsiya etilgan hajm, yoki `None`.

    Kartochkadagi "Miqdor" bilan AYNAN BIR XIL hisob (`hajm_taklifi`),
    shuning uchun foydalanuvchi ikki xil raqam ko'rmaydi.

    Xato bo'lsa `None` — taklifsiz ham savol berilaveradi (0.3-band).
    """
    if not balans or balans <= 0:
        return None
    try:
        taklif = hajm_taklifi(
            yozuv.symbol,
            SignalLevels(yozuv.entry, yozuv.stop, yozuv.tp1, yozuv.tp2),
            balans,
            config,
        )
    except Exception:  # noqa: BLE001 — taklif majburiy emas
        return None
    return taklif.position_size_usd if taklif and taklif.position_size_usd > 0 else None


# --------------------------------------------------------------------------- #
#  "Men kirdim" (5.4-band)
# --------------------------------------------------------------------------- #


@router.callback_query(F.data.startswith("sig:enter:"))
async def ask_position_amount(  # noqa: PLR0913
    callback: CallbackQuery,
    state,  # noqa: ANN001
    database: Database,
    config: AppConfig,
    db_user_id: int,
    language: str,
    db_user=None,  # noqa: ANN001
    is_admin: bool = False,
    **_: object,
) -> None:
    signal_id = int(callback.data.rsplit(":", 1)[1])

    async with database.session() as session:
        yozuv = await SignalRepository(session).get(signal_id)
        if yozuv is None or SignalStatus(yozuv.status).is_closed:
            await callback.answer(t("signal.kirdim_signal_yopiq", language), show_alert=True)
            return

        balans = getattr(db_user, "declared_balance_usd", None)
        mavjud = await UserPositionRepository(session).get(db_user_id, signal_id)
        if mavjud is not None:
            await callback.answer(
                t("signal.kirdim_allaqachon", language, amount=f"{mavjud.amount_usd:,.2f}"),
                show_alert=True,
            )
            return

    await state.set_state(PositionFlow.waiting_amount)
    await state.update_data(signal_id=signal_id, entry_price=yozuv.entry, symbol=yozuv.symbol)

    # BIZ TAKLIF QILAMIZ, FOYDALANUVCHI HAQIQATNI AYTADI. Taklifsiz
    # savol "qancha oldingiz?" bo'lib qolardi va odam qaysi raqamni
    # yozishni bilmasdi — kartochkadagi "Miqdor" bilan bog'liqlik
    # ko'rinmasdi.
    taklif = _hajm_taklifi(yozuv, balans, config)
    savol = t("signal.kirdim_soralmoqda", language)
    if taklif is not None:
        savol += "\n\n" + t(
            "signal.kirdim_taklif", language, amount=f"{taklif:,.2f}"
        )
    await callback.message.answer(savol)
    await callback.answer()


@router.message(PositionFlow.waiting_amount)
async def save_position(
    message: Message,
    state,  # noqa: ANN001
    database: Database,
    config: AppConfig,
    db_user_id: int,
    tier: SubscriptionTier | None,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    try:
        miqdor = float((message.text or "").replace(",", ".").replace(" ", ""))
    except ValueError:
        await message.answer(t("umumiy.raqam_kiriting", language))
        return
    if miqdor < config.portfolio.min_position_usd:
        await message.answer(t("umumiy.musbat_raqam_kiriting", language))
        return

    data = await state.get_data()
    async with database.session() as session:
        await UserPositionRepository(session).record_entry(
            user_id=db_user_id,
            signal_id=data["signal_id"],
            amount_usd=miqdor,
            entry_price=data["entry_price"],
        )

    await state.clear()
    logger.info("Pozitsiya qayd etildi: user=%s signal=%s", db_user_id, data["signal_id"])
    await message.answer(
        t("signal.kirdim_qayd_etildi", language, symbol=data["symbol"], amount=f"{miqdor:,.2f}"),
        reply_markup=main_menu(tier, language, is_admin),
    )


# --------------------------------------------------------------------------- #
#  "Mening portfelim"
# --------------------------------------------------------------------------- #


@router.callback_query(F.data == "portfel:pozitsiyalar")
async def show_positions(
    callback: CallbackQuery,
    database: Database,
    db_user_id: int,
    language: str,
    is_admin: bool = False,
    **_: object,
) -> None:
    async with database.session() as session:
        pozitsiyalar = await UserPositionRepository(session).snapshots_for(db_user_id)

    if not pozitsiyalar:
        await callback.message.edit_text(
            t("portfel.bosh", language), reply_markup=back_button("portfel", language)
        )
        await callback.answer()
        return

    xulosa = summarize(pozitsiyalar)
    matn = t(
        "portfel.umumiy",
        language,
        total=xulosa.total_positions,
        open=xulosa.open_positions,
        closed=xulosa.closed_positions,
        win=xulosa.winning,
        loss=xulosa.losing,
        win_rate=f"{xulosa.win_rate:.0%}" if xulosa.win_rate is not None else "—",
        invested=f"{xulosa.total_invested_usd:,.2f}",
        pnl_usd=_usd(xulosa.realized_pnl_usd),
        pnl_pct=_pct(xulosa.realized_pnl_pct),
    )

    if xulosa.best_pnl_pct is not None:
        matn += t(
            "portfel.eng_yaxshi",
            language,
            best=_pct(xulosa.best_pnl_pct),
            worst=_pct(xulosa.worst_pnl_pct),
        )

    ochiqlar = [p for p in pozitsiyalar if p.is_open]
    if ochiqlar:
        qatorlar = "\n".join(f"• {p.symbol} — ${p.amount_usd:,.2f}" for p in ochiqlar[:10])
        matn += t("portfel.ochiq_royxat", language, items=qatorlar)

    matn += "\n\n" + t("portfel.ogohlantirish", language)
    await callback.message.edit_text(matn, reply_markup=back_button("portfel", language))
    await callback.answer()


# --------------------------------------------------------------------------- #
#  Umumiy statistika (3.6-band shaffofligi)
# --------------------------------------------------------------------------- #

PERIODS: dict[str, tuple[str, int]] = {
    "kunlik": ("statistika.kunlik", 1),
    "haftalik": ("statistika.haftalik", 7),
    "oylik": ("statistika.oylik", 30),
}


@router.callback_query(F.data == "menu:statistika")
async def choose_period(callback: CallbackQuery, language: str, **_: object) -> None:
    builder = InlineKeyboardBuilder()
    for kod, (kalit, _kun) in PERIODS.items():
        builder.button(text=t(kalit, language), callback_data=f"stat:{kod}")
    builder.button(text=t("umumiy.orqaga", language), callback_data="menu:home")
    builder.adjust(3)

    await callback.message.edit_text(
        t("statistika.davr_tanlang", language), reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stat:"))
async def show_stats(
    callback: CallbackQuery, database: Database, language: str, **_: object
) -> None:
    kod = callback.data.split(":", 1)[1]
    kalit, kunlar = PERIODS[kod]
    boshlanish = (utc_now() - timedelta(days=kunlar)).date()

    async with database.session() as session:
        statistika = await DailyStatsRepository(session).aggregate(
            boshlanish, t(kalit, language)
        )

    if statistika.signals_created == 0:
        await callback.answer(t("statistika.bosh", language), show_alert=True)
        return

    matn = t(
        "statistika.hisobot",
        language,
        period=statistika.period_label,
        created=statistika.signals_created,
        activated=statistika.signals_activated,
        tp2=statistika.tp2_count,
        stop=statistika.stop_count,
        win_rate=f"{statistika.win_rate:.0%}" if statistika.win_rate is not None else "—",
        participants=statistika.participants,
        volume=f"{statistika.total_volume_usd:,.0f}",
    )
    if statistika.average_score is not None:
        matn += t(
            "statistika.qoshimcha",
            language,
            score=f"{statistika.average_score:.0f}",
            rr=f"{statistika.average_risk_reward:.1f}"
            if statistika.average_risk_reward
            else "—",
        )
    matn += "\n\n" + t("shaffoflik.aniqlik_dagvosi_yoq", language)

    await callback.message.edit_text(matn, reply_markup=back_button("home", language))
    await callback.answer()
