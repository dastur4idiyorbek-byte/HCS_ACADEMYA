"""Boshlang'ich ma'lumotlarni bazaga yozadi.

Ishga tushirish:
    python -m scripts.seed

Yoziladigan ma'lumot:
  - Narxlar (1.2-band) — admin keyinchalik panel orqali o'zgartiradi
  - Harom/shubhali coin ro'yxati (1.4-band) — konfiguratsiyadagi urug'lardan

DIQQAT: coin ro'yxati DINIY qaror. Bu yerdagi qiymatlar — boshlang'ich
taxmin, yakuniy hukm emas. Ishlab chiqarishga chiqishdan oldin bilimdon
kishi bilan ko'rib chiqilishi kerak.
"""

from __future__ import annotations

import asyncio

from bot.hosting import apply_platform_defaults
from core.config import load_config
from core.domain.enums import HalalStatus, SubscriptionTier
from core.halal_screening.rulings import DEFAULT_HARAM_REASON, DEFAULT_MASHBOOH_REASON
from core.storage import Database
from core.storage.repositories import CoinRulingRepository, PriceRepository
from core.utils.logging_setup import get_logger, setup_logging

logger = get_logger(__name__)

#: Boshlang'ich narxlar: (tarif, muddat, valyuta, summa)
DEFAULT_PRICES: list[tuple[SubscriptionTier, str, str, float]] = [
    (SubscriptionTier.LITE, "daily", "KGS", 100),
    (SubscriptionTier.LITE, "monthly", "KGS", 1500),
    (SubscriptionTier.PRO, "daily", "KGS", 200),
    (SubscriptionTier.PRO, "monthly", "KGS", 3000),
    (SubscriptionTier.PREMIUM, "daily", "KGS", 300),
    (SubscriptionTier.PREMIUM, "monthly", "KGS", 5000),
]


async def seed() -> None:
    setup_logging()
    # Bot bilan bir xil bazaga yozishimiz shart (doimiy disk ulangan bo'lsa).
    apply_platform_defaults()
    config = load_config()
    database = Database()
    await database.init_models()

    async with database.session() as session:
        narxlar = PriceRepository(session)
        for tier, period, currency, amount in DEFAULT_PRICES:
            await narxlar.upsert(tier, period, currency, amount)
        logger.info("Narxlar yozildi: %d ta", len(DEFAULT_PRICES))

        qarorlar = CoinRulingRepository(session)
        mavjud = await qarorlar.all_verdicts()
        yangi = 0

        for symbol in config.halal_screening.seed_haram_symbols:
            if symbol.upper() not in mavjud:
                await qarorlar.set_ruling(symbol, HalalStatus.HARAM, DEFAULT_HARAM_REASON)
                yangi += 1
        for symbol in config.halal_screening.seed_mashbooh_symbols:
            if symbol.upper() not in mavjud:
                await qarorlar.set_ruling(symbol, HalalStatus.MASHBOOH, DEFAULT_MASHBOOH_REASON)
                yangi += 1

        logger.info("Coin qarorlari yozildi: %d ta yangi", yangi)

    await database.dispose()
    logger.warning(
        "ESLATMA: coin ro'yxati boshlang'ich taxmin. Ishlab chiqarishdan oldin "
        "bilimdon kishi bilan ko'rib chiqing."
    )


if __name__ == "__main__":
    asyncio.run(seed())
