"""Radar jarayoni: `python -m core.portlash_radari`.

BOTDAN ALOHIDA JARAYON (loyiha egasining qarori, 2026-10-14: Modul
4.0.0 faqat sayt uchun). `scripts/start.sh` uni bot va sayt yonida
ishga tushiradi va yiqilsa qayta ko'taradi. Bot kodi bu jarayonga
umuman bog'lanmaydi.

Baza manzili `DATABASE_URL` dan olinadi — `start.sh` uni bot va sayt
bilan BIR XIL qilib eksport qiladi.

Chiqish kodi:
    0  radar sozlamada o'chirilgan (`radar.yoqilgan: false`) — qayta
       ko'tarish shart emas
    1  ishga tushirib bo'lmadi (baza, sozlama) — nazoratchi qayta urinadi
"""

from __future__ import annotations

import asyncio
import os
import sys

from core.config import load_config
from core.config.loader import radar_muammolari
from core.portlash_radari.ishchi import RadarIshchisi
from core.storage import Database
from core.utils.logging_setup import get_logger, setup_logging

logger = get_logger("core.portlash_radari")


async def ishga_tushir() -> int:
    config = load_config(os.getenv("HCS_CONFIG_FILE") or None)
    if not config.radar.yoqilgan:
        logger.warning("Radar o'chiq (radar.yoqilgan = false) — jarayon tugadi")
        return 0
    muammolar = radar_muammolari(config)
    if muammolar:
        logger.error(
            "Radar sozlamasi xato — radar ishga tushmadi:\n  - %s", "\n  - ".join(muammolar)
        )
        return 1

    database = Database()
    # Jadvallarni bot yoki `alembic upgrade head` yaratadi. Radar ulardan
    # OLDIN ko'tarilishi mumkin — shuning uchun o'zi ham ishonch hosil
    # qiladi (`create_all` mavjud jadvalga tegmaydi).
    await database.init_models()
    if not await database.healthcheck():
        logger.error("Baza javob bermayapti — radar ishga tushmadi")
        return 1

    ishchi = RadarIshchisi(config, database)
    try:
        await ishchi.yur()
    finally:
        await ishchi.yop()
        await database.dispose()
    return 0


def main() -> None:
    # O'Z PAPKASI. Bot ham `logs/hcs.log` ga yozadi va ikki jarayon bitta
    # aylanuvchi faylni bo'lisha olmaydi: biri faylni almashtirsa, ikkinchisi
    # eski faylga yozishda davom etadi va zaxira nusxalarni ikki barobar
    # tez yeb qo'yadi.
    log_dir = os.getenv("RADAR_LOG_DIR") or os.path.join(os.getenv("LOG_DIR", "logs"), "radar")
    setup_logging(level=os.getenv("LOG_LEVEL", "INFO"), log_dir=log_dir)
    try:
        sys.exit(asyncio.run(ishga_tushir()))
    except KeyboardInterrupt:
        logger.info("Radar to'xtatildi")


if __name__ == "__main__":
    main()
