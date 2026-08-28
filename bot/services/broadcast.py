"""Signalni obunachilarga tarqatish — YAGONA joy.

Nima uchun alohida modul: bu ish uch joydan chaqiriladi (qo'lda kiritilgan
signal, avtomatik sikl, veb-panelda yaratilgan signal). Har birida
kartochka yasash + yuborish sikli qaytarilsa, biri o'zgarib ikkitasi
qolib ketardi — masalan `protect_content` bir joyda unutilsa, o'sha
yo'ldan ketgan signal himoyasiz tarqalardi va buni hech kim sezmasdi.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import BufferedInputFile

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


#: Grafik uchun nechta sham olinadi. 80 ta 4-soatlik sham ~13 kun —
#: signal atrofidagi harakatni ko'rsatishga yetadi, rasm esa siqilib
#: ketmaydi.
GRAFIK_SHAMLAR = 80


async def signal_grafigi(
    candles,  # noqa: ANN001 — `CandleProvider`, aylanma import bo'lmasin
    symbol: str,
    levels: SignalLevels,
    config: AppConfig,
    created_at=None,  # noqa: ANN001
) -> bytes | None:
    """Signal grafigi rasmi (PNG) yoki `None`.

    HECH QACHON ISTISNO TASHLAMAYDI (0.3-band): rasm — qo'shimcha
    qulaylik, signalning o'zi emas. Binance javob bermasa yoki chizishda
    xato bo'lsa, signal MATN sifatida baribir ketishi kerak. Aks holda
    grafik xizmati bir daqiqa yiqilgani uchun obunachi signalni umuman
    olmasdi.
    """
    if candles is None:
        return None
    timeframe = config.analysis.entry_timeframe
    try:
        # Import ICHKARIDA: `bot/chart.py` Pillow'ni talab qiladi. Uni
        # modul boshida import qilsak va Pillow o'rnatilmagan bo'lsa
        # (masalan serverda `pip install` yiqilsa), BUTUN BOT ishga
        # tushmasdi — grafik esa atigi qo'shimcha qulaylik. Bu yerda
        # xato oddiy "rasm yo'q" holatiga aylanadi.
        from bot.chart import render_signal_chart

        shamlar = await candles.fetch_candles(symbol, timeframe, GRAFIK_SHAMLAR)
        if not shamlar:
            return None
        return render_signal_chart(
            symbol,
            shamlar,
            levels,
            quote_asset=config.halal_screening.quote_asset,
            timeframe=timeframe,
            created_at=created_at,
        )
    except Exception:  # noqa: BLE001 — rasm signalni to'sib qo'ymasin
        logger.warning("Signal grafigi chizilmadi: %s", symbol, exc_info=True)
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
    chart: bytes | None = None,
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
    # Rasm BIR MARTA yuklanadi: birinchi yuborishdan keyin Telegram
    # bergan `file_id` qolganlariga qayta ishlatiladi. Aks holda har
    # bir obunachi uchun bir xil rasm qaytadan yuklanardi — yuzta
    # obunachida yuz marta.
    rasm_id: str | None = None

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

        # RASM YIQILSA SIGNAL MATN BO'LIB KETADI. Bu — 0.3-bandning
        # aynan o'zi: rasm qulaylik, signal esa mahsulotning o'zi.
        # Telegram rasmni rad etsa (o'lcham, format, tarmoq), obunachi
        # HECH NARSA olmay qolardi.
        if chart is not None:
            try:
                fayl = rasm_id or BufferedInputFile(chart, filename=f"{symbol}.png")
                xabar = await bot.send_photo(
                    telegram_id, fayl, caption=kartochka,
                    protect_content=True, reply_markup=tugmalar,
                )
                # `file_id` ni bir marta olib, qolganlariga qayta
                # ishlatamiz — aks holda har obunachi uchun bir xil rasm
                # qaytadan yuklanardi.
                if rasm_id is None and xabar.photo:
                    rasm_id = xabar.photo[-1].file_id
                yuborildi += 1
                continue
            except Exception:  # noqa: BLE001 — matnga tushib ko'ramiz
                logger.warning(
                    "Signal rasmi yuborilmadi, matn bilan urinamiz: telegram_id=%s",
                    telegram_id, exc_info=True,
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
