"""Botning kirish nuqtasi.

Ishga tushirish:
    python -m bot.main

6.2-band: polling rejimi (webhook emas — domen/SSL shart emas).
"""

from __future__ import annotations

import asyncio
import contextlib

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from bot.handlers import admin as admin_handlers
from bot.handlers import portfolio as portfolio_handlers
from bot.handlers import signals as signal_handlers
from bot.handlers import user as user_handlers
from bot.hosting import apply_platform_defaults, warn_if_data_is_temporary
from bot.middlewares import UserContextMiddleware
from bot.services import PipelineRunner, Scheduler, SignalWatcher
from bot.settings import BotSettings, SettingsError, load_env_file, load_settings
from core.config import AppConfig, load_config
from core.market_data import (
    BinanceCandleProvider,
    BinancePriceStream,
    CoinMarketCapDominance,
)
from core.market_data.ranking import build_ranking_provider
from core.risk_engine import RiskEngine
from core.storage import Database
from core.utils.logging_setup import get_logger, setup_logging

logger = get_logger(__name__)


def build_dispatcher(database: Database, settings: BotSettings, config: AppConfig) -> Dispatcher:
    """Dispatcher quradi: middleware'lar, routerlar va umumiy kontekst."""
    dispatcher = Dispatcher(storage=MemoryStorage())

    # Kontekst middleware BARCHA yangilanishlarga — handlerlar tayyor
    # ma'lumot oladi (foydalanuvchi, tarif, rol).
    context = UserContextMiddleware(database, settings)
    dispatcher.message.middleware(context)
    dispatcher.callback_query.middleware(context)

    # Admin routerlari BIRINCHI: `/panel` va `admin:*` callback'lari oddiy
    # foydalanuvchi handlerlariga tushib ketmasligi kerak.
    dispatcher.include_router(signal_handlers.admin_router)
    dispatcher.include_router(admin_handlers.router)
    dispatcher.include_router(signal_handlers.user_router)
    dispatcher.include_router(portfolio_handlers.router)
    dispatcher.include_router(user_handlers.router)

    # Konfiguratsiya barcha handlerlarga uzatiladi
    dispatcher["config"] = config
    return dispatcher


#: Telegram'da "/" bosilganda ko'rinadigan buyruqlar
UMUMIY_BUYRUQLAR = [
    BotCommand(command="start", description="Botni ishga tushirish"),
]
#: Adminlar qo'shimcha ko'radigan buyruqlar
ADMIN_BUYRUQLARI = [
    *UMUMIY_BUYRUQLAR,
    BotCommand(command="panel", description="Admin panel"),
]


async def register_commands(bot: Bot, admin_ids: frozenset[int]) -> None:
    """Buyruqlarni Telegram menyusiga yozadi.

    Busiz "/" bosilganda ro'yxat bo'sh chiqadi va foydalanuvchi
    `/start` dan boshqa nima borligini bilmaydi.

    `/panel` FAQAT adminlarga ko'rsatiladi — oddiy foydalanuvchida
    admin panelning mavjudligi bilinmaydi (1.1-band).

    Yozib bo'lmasa bot to'xtamaydi: bu qulaylik, majburiy shart emas
    (0.3-band).
    """
    try:
        await bot.set_my_commands(UMUMIY_BUYRUQLAR, scope=BotCommandScopeDefault())
        for admin_id in admin_ids:
            await bot.set_my_commands(
                ADMIN_BUYRUQLARI, scope=BotCommandScopeChat(chat_id=admin_id)
            )
        logger.info("Telegram buyruqlari yozildi (adminlarga /panel ham)")
    except Exception:  # noqa: BLE001 — qulaylik, ishga tushirishni to'smaydi
        logger.warning("Buyruqlar menyusini yozib bo'lmadi", exc_info=True)


async def run() -> None:
    # README `cp .env.example .env` deydi — demak bu fayl o'qilishi shart.
    # Tizim muhit o'zgaruvchilari ustun turadi (systemd, Docker).
    load_env_file()

    settings = load_settings()
    setup_logging(level=settings.log_level, log_dir=settings.log_dir)

    config = load_config(settings.config_file)
    logger.info("Konfiguratsiya yuklandi: %s", config.project.name)

    # Doimiy disk ulangan bo'lsa (Railway va sh.k.), baza o'sha yerda
    # joylashsin. Ochiq berilgan DATABASE_URL hech qachon bekor qilinmaydi.
    baza_url = apply_platform_defaults() or settings.database_url
    warn_if_data_is_temporary(baza_url)

    database = Database(baza_url)
    await database.init_models()
    if not await database.healthcheck():
        raise RuntimeError("Ma'lumotlar bazasi javob bermayapti — ishga tushirish to'xtatildi")

    engine = RiskEngine(config)
    logger.info("Risk Engine tayyor: %d ta qoida", len(engine.rules))
    # ID'lar ataylab to'liq yoziladi: `/panel` admin bo'lmaganga JIMGINA
    # javob bermaydi (panel borligi oshkor qilinmasligi kerak). Shu sababli
    # ADMIN_IDS xato yozilsa hech qanday belgi qolmasdi — sozlangan ID'ni
    # jurnalda ko'rish yagona yo'l.
    logger.info(
        "Adminlar: %d ta -> %s",
        len(settings.admin_ids),
        ", ".join(str(i) for i in sorted(settings.admin_ids)) or "yo'q",
    )

    bot = Bot(
        token=settings.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = build_dispatcher(database, settings, config)

    # 2-bo'lim: narx oqimi kuzatuvchisi fon vazifasi sifatida.
    stream = BinancePriceStream(config.market_data, config.halal_screening.quote_asset)
    watcher = SignalWatcher(bot, database, config, stream, settings.admin_ids)
    dispatcher["watcher"] = watcher
    watcher_task = asyncio.create_task(watcher.run(), name="signal-watcher")

    # 15-bosqich: avtomatik signal sikli va takrorlanuvchi vazifalar.
    candle_provider = BinanceCandleProvider(
        config.market_data, config.halal_screening.quote_asset
    )
    ranking_provider = build_ranking_provider(config.market_data)
    # 3.7-band, 1-omil: BTC dominance. Kalit yo'q bo'lsa omil nol ball
    # oladi va buni admin `/panel` -> 💓 da ko'radi.
    dominance = CoinMarketCapDominance(config.market_data)
    if not dominance.is_configured:
        logger.warning(
            "CMC_API_KEY yo'q — BTC Dominance omili nol ball oladi "
            "(indeksning 20 bali ishlatilmaydi)"
        )
    runner = PipelineRunner(
        bot, database, config, candle_provider, ranking_provider, watcher, dominance
    )
    scheduler = Scheduler(bot, database, config, runner, settings.admin_ids)
    scheduler.start()

    await register_commands(bot, settings.admin_ids)

    try:
        logger.info("Bot polling rejimida ishga tushdi")
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await scheduler.stop()
        watcher_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watcher_task
        await stream.close()
        await candle_provider.close()
        await ranking_provider.close()
        await dominance.close()
        await bot.session.close()
        await database.dispose()
        logger.info("Bot to'xtatildi")


#: Ishga tushirishdagi tipik xatolar -> foydalanuvchi tushunadigan izoh.
#: Xom traceback o'rniga aniq ko'rsatma beriladi: birinchi ishga tushirishda
#: eng ko'p uchraydigan uchta muammo shular.
def _tushuntir(xato: BaseException) -> str:
    if isinstance(xato, SettingsError):
        return str(xato)
    if isinstance(xato, TelegramUnauthorizedError):
        return (
            "BOT_TOKEN Telegram tomonidan qabul qilinmadi. Tokenni BotFather'da "
            "tekshiring (/mybots -> API Token) va `.env` fayliga to'liq nusxalang."
        )
    if isinstance(xato, TelegramNetworkError):
        return (
            "api.telegram.org ga ulanib bo'lmadi. Internet aloqasini tekshiring. "
            "Telegram to'silgan tarmoqda bo'lsangiz, serverdan (masalan Oracle "
            "Cloud) ishga tushiring."
        )
    return ""


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Foydalanuvchi tomonidan to'xtatildi")
    except (SettingsError, TelegramNetworkError, TelegramUnauthorizedError) as xato:
        # Bu uchtasi — sozlash muammosi, dastur xatosi emas. Foydalanuvchiga
        # 40 qatorli traceback emas, bitta aniq jumla kerak.
        logger.error("Ishga tushirib bo'lmadi: %s", _tushuntir(xato))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
