"""Botning kirish nuqtasi.

Ishga tushirish:
    python -m bot.main

6.2-band: polling rejimi (webhook emas — domen/SSL shart emas).

HOLAT: 3-bosqichda to'liq ulanadi. Hozircha konfiguratsiya, baza va "miya"
qatlamini tekshirib, tayyorlik holatini ko'rsatadi.
"""

from __future__ import annotations

import asyncio

from core.config import load_config
from core.risk_engine import RiskEngine
from core.storage import Database
from core.utils.logging_setup import get_logger, setup_logging

logger = get_logger(__name__)


async def bootstrap() -> None:
    """Tizim komponentlarini ishga tushiradi va tayyorligini tekshiradi."""
    from bot.settings import load_settings  # muhit talab qilinadi

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

    # TODO(3-bosqich): aiogram Dispatcher, handlerlar va polling shu yerda ulanadi
    logger.warning(
        "Telegram qatlami hali ulanmagan (3-bosqich). "
        "Hozircha faqat 'miya' qatlami va baza tayyor."
    )

    await database.dispose()


def main() -> None:
    asyncio.run(bootstrap())


if __name__ == "__main__":
    main()
