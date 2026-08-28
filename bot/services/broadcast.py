"""Signalni obunachilarga tarqatish — YAGONA joy.

Nima uchun alohida modul: bu ish uch joydan chaqiriladi (qo'lda kiritilgan
signal, avtomatik sikl, veb-panelda yaratilgan signal). Har birida
kartochka yasash + yuborish sikli qaytarilsa, biri o'zgarib ikkitasi
qolib ketardi — masalan `protect_content` bir joyda unutilsa, o'sha
yo'ldan ketgan signal himoyasiz tarqalardi va buni hech kim sezmasdi.
"""

from __future__ import annotations

from aiogram import Bot

from bot.formatting import render_signal_card
from bot.i18n import DEFAULT_LANGUAGE
from bot.keyboards import signal_actions
from core.config.schema import AppConfig
from core.domain.enums import SubscriptionTier
from core.domain.models import EntryPlan, SignalLevels
from core.position_sizing import PositionSizer
from core.storage.repositories import SubscriptionRepository, UserRepository
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: `(telegram_id, e'lon qilingan balans)`
Qabul = tuple[int, float | None]


def hajm_taklifi(
    symbol: str, levels: SignalLevels, balance: float | None, config: AppConfig
):
    """5.1-band: shu foydalanuvchi uchun pozitsiya hajmi.

    `commit=False` — bu FAQAT ko'rsatish uchun, xavf byudjetidan hech
    narsa ajratilmaydi. Byudjet foydalanuvchi "Men kirdim" deganda band
    qilinadi (5.4-band).

    Hisoblab bo'lmasa `None` — miqdor yo'qligi signalni to'sib qo'ymaydi
    (0.3-band).
    """
    if balance is None or balance <= 0:
        return None
    try:
        sizer = PositionSizer(config.position_sizing)
        return sizer.suggest(symbol, levels, sizer.budget_for(balance), commit=False)
    except Exception:  # noqa: BLE001 — miqdorsiz bo'lsa ham signal ketsin
        logger.warning("Pozitsiya hajmi hisoblanmadi: %s", symbol, exc_info=True)
        return None


async def broadcast_signal(  # noqa: PLR0913
    bot: Bot,
    recipients: list[Qabul],
    symbol: str,
    levels: SignalLevels,
    entry_plan: EntryPlan,
    signal_id: int,
    config: AppConfig,
    language: str = DEFAULT_LANGUAGE,
) -> int:
    """1.3-band: `protect_content=True` — forward/saqlash bloklanadi.

    Kartochka HAR BIR qabul qiluvchi uchun alohida yasaladi: miqdor
    ularning o'z balansidan hisoblanadi (5.1-band).

    Bitta qabul qiluvchiga yetkazilmasa, qolganlariga yuborish davom
    etadi (0.3-band).

    Returns:
        Nechtasiga yetkazilgani.
    """
    yuborildi = 0
    for telegram_id, balans in recipients:
        kartochka = render_signal_card(
            symbol,
            levels,
            entry_plan,
            suggestion=hajm_taklifi(symbol, levels, balans, config),
            quote_asset=config.halal_screening.quote_asset,
            language=language,
            tp1_close_pct=config.portfolio.tp1_close_pct,
        )
        # Balanssiz foydalanuvchiga ENG AVVAL balans tugmasi ko'rinadi.
        tugmalar = signal_actions(
            signal_id, language, balans_yoq=not balans or balans <= 0
        )

        try:
            await bot.send_message(
                telegram_id, kartochka,
                protect_content=True, reply_markup=tugmalar,
            )
            yuborildi += 1
        except Exception:  # noqa: BLE001 — bitta xato tarqatishni to'xtatmasin
            logger.warning("Signal yetkazilmadi: telegram_id=%s", telegram_id)
    return yuborildi


async def obunachilar(session) -> list[Qabul]:  # noqa: ANN001
    """Signal oladigan foydalanuvchilar: `(telegram_id, balans)`.

    Balans ham qaytariladi, chunki pozitsiya hajmi HAR KIM UCHUN
    boshqacha (5.1-band) — kartochka har bir qabul qiluvchi uchun alohida
    yasaladi. Balans kiritilmagan bo'lsa `None`: kartochkada miqdor
    o'rniga taklif matni chiqadi.

    Bu yerda turishining sababi: ro'yxatni endi ikki joy so'raydi —
    avtomatik sikl va veb-paneldagi signallarni tarqatuvchi fon vazifasi.
    """
    users = UserRepository(session)
    obunalar = SubscriptionRepository(session)
    natija: list[Qabul] = []
    for user in await users.active_users(since_days=90):
        tarif = await obunalar.tier_for(user.id)
        if tarif is not None and tarif.covers(SubscriptionTier.LITE):
            natija.append((user.telegram_id, user.declared_balance_usd))
    return natija
