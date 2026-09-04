"""5.4-band: shaxsiy portfel va umumiy statistika.

Shaxsiy tomon: "Men kirdim" tugmasi -> miqdor -> avtomatik foyda/zarar.
Umumiy tomon: hammaga ochiq shaffoflik raqamlari (3.6-band).

MUHIM: shaxsiy ma'lumot umumiy statistikada OSHKOR QILINMAYDI — faqat
agregat (nechta ishtirokchi, jami hajm).
"""

from __future__ import annotations

from dataclasses import replace

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.i18n import t
from bot.keyboards import back_button, main_menu
from bot.services.broadcast import hajm_taklifi
from bot.states import PositionFlow
from core.config.schema import AppConfig
from core.domain.enums import SignalStatus, SubscriptionTier
from core.domain.models import signal_levels
from core.portfolio.pnl_calculator import xulosa_qur
from core.portfolio.pnl_dashboard import dashboard_qur
from core.portfolio.pnl_dashboard import matn as dashboard_matn
from core.services import summarize
from core.storage import Database
from core.storage.portfel_repository import PortfelRepository
from core.storage.repositories import (
    SignalRepository,
    UserPositionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger

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
            signal_levels(yozuv.entry, yozuv.stop, yozuv.tp1, yozuv.tp2, yozuv.tp3),
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

        # TP1 olingan signalga YANGI kirish qayd etilmaydi: harakatning
        # katta qismi o'tib bo'lgan va Stop endi kirish narxida turadi.
        # Saytdagi qoida bilan bir xil — aks holda botda ruxsat etilgan
        # narsa saytda taqiqlangan bo'lardi.
        if mavjud is None and not SignalStatus(yozuv.status).is_enterable:
            await callback.answer(
                t("signal.kirdim_kech", language), show_alert=True
            )
            return

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
    callback: CallbackQuery, language: str, **_: object
) -> None:
    """Statistika — HOZIRCHA BO'SH.

    2026-09-04: eski tahlil moduli butunlay olib tashlandi va u bilan
    birga `daily_stats` jadvali ham ketdi. O'sha jadvaldagi raqamlar
    ESKI modulning natijasi edi.

    Ularni yangi modul natijasi sifatida ko'rsatish — foydalanuvchini
    aldash bo'lardi: ikki modul boshqa mantiq bilan ishlaydi.

    Yangi statistika yangi modul yetarli signal berganda quriladi.
    Shungacha ekran ROSTINI aytadi.
    """
    await callback.answer(t("statistika.bosh", language), show_alert=True)


# --------------------------------------------------------------------------- #
#  "Mening natijam" — portfel moduli dashboardi (3-prompt, 4-qism)
# --------------------------------------------------------------------------- #


async def _joriy_narxlar(candles: object, symbollar: set[str]) -> dict[str, float]:
    """Ochiq savdolar uchun oxirgi narx.

    Narx olinmasa coin ro'yxatga TUSHMAYDI — dashboard uni
    "narxi olinmadi" deb ko'rsatadi. Kirish narxini qo'yib
    "+$0.00" chiqarish aldash bo'lardi.
    """
    if candles is None:
        return {}
    natija: dict[str, float] = {}
    for symbol in symbollar:
        try:
            shamlar = await candles.fetch_candles(symbol, "15m", 1)
        except Exception:  # noqa: BLE001 — narx majburiy emas
            logger.warning("joriy narx olinmadi", extra={"symbol": symbol})
            continue
        if shamlar:
            natija[symbol] = shamlar[-1].close
    return natija


@router.callback_query(F.data == "portfel:natija")
async def show_dashboard(
    callback: CallbackQuery,
    database: Database,
    db_user_id: int,
    config: AppConfig,
    language: str,
    candles: object = None,
    **_: object,
) -> None:
    """Realized/unrealized natija va bo'laklar holati.

    BOTDAGI VA SAYTDAGI RAQAM BITTA JOYDAN CHIQADI
    (`core/portfolio/pnl_dashboard.py`). Ansiz ikkita hisob-kitob
    paydo bo'lardi va vaqt o'tib ular farq qila boshlardi.
    """
    async with database.session() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        balans = (user.declared_balance_usd if user else None) or 0.0

        repo = PortfelRepository(session)
        bolaklar = (
            await repo.bolaklarni_tayyorla(db_user_id, balans, config.portfolio.bolak_soni)
            if balans > 0
            else []
        )
        qismlar = await repo.yopilgan_qismlar(db_user_id)
        ochiqlar_narxsiz = await repo.ochiq_pozitsiyalar(db_user_id)

    narxlar = await _joriy_narxlar(candles, {p.symbol for p in ochiqlar_narxsiz})
    ochiqlar = [replace(p, joriy_narx=narxlar.get(p.symbol)) for p in ochiqlar_narxsiz]

    xulosa = xulosa_qur(qismlar, ochiqlar, balans_usd=balans)
    await callback.message.edit_text(
        dashboard_matn(dashboard_qur(xulosa, bolaklar)),
        reply_markup=back_button("portfel", language),
    )
    await callback.answer()
