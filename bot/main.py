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
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import admin as admin_handlers
from bot.handlers import signals as signal_handlers
from bot.handlers import user as user_handlers
from bot.middlewares import UserContextMiddleware
from bot.services import SignalWatcher
from bot.settings import BotSettings, load_settings
from core.config import AppConfig, load_config
from core.market_data import BinancePriceStream
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
    dispatcher.include_router(user_handlers.router)

    # Konfiguratsiya barcha handlerlarga uzatiladi
    dispatcher["config"] = config
    return dispatcher


async def run() -> None:
    settings = load_settings()
    setup_logging(level=settings.log_level, log_dir=settings.log_dir)

    config = load_config(settings.config_file)
    logger.info("Konfiguratsiya yuklandi: %s", config.project.name)

    database = Database(settings.database_url)
    await database.init_models()
    if not await database.healthcheck():
        raise RuntimeError("Ma'lumotlar bazasi javob bermayapti — ishga tushirish to'xtatildi")

    engine = RiskEngine(config)
    logger.info("Risk Engine tayyor: %d ta qoida", len(engine.rules))
    logger.info("Adminlar: %d ta", len(settings.admin_ids))

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

    # TODO(15-bosqich): avtomatik signal sikli va obuna muddati tekshiruvi.

    try:
        logger.info("Bot polling rejimida ishga tushdi")
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        watcher_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watcher_task
        await stream.close()
        await bot.session.close()
        await database.dispose()
        logger.info("Bot to'xtatildi")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Foydalanuvchi tomonidan to'xtatildi")


if __name__ == "__main__":
    main()
