"""Fon vazifalari — takrorlanuvchi ishlar.

    signal sikli        — har `entry_timeframe` sham yopilganda
    halol ro'yxat       — 12 soatda bir (3.4-band)
    obuna muddati       — soatda bir (1.2-band)
    kunlik oldindan tahlil — UTC 00:00 atrofida (3.7-band)
    haftalik hisobot    — dushanba ertalab (3.8-band)

Har bir vazifa MUSTAQIL: bittasining nosozligi boshqalarni to'xtatmaydi
(0.3-band). Shu sababli har biri o'z siklida, o'z `try/except` i bilan
ishlaydi.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta

from aiogram import Bot

from bot.i18n import DEFAULT_LANGUAGE, t
from bot.services.runner import PipelineRunner, cycle_interval
from core.analysis.postmortem import build_report, render_report
from core.config.schema import AppConfig
from core.services import SubscriptionService
from core.storage import Database
from core.storage.repositories import (
    PaymentRepository,
    SignalRepository,
    SubscriptionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)


async def _repeat(
    name: str,
    interval: timedelta,
    action: Callable[[], Awaitable[None]],
    initial_delay: timedelta | None = None,
) -> None:
    """Vazifani takrorlab turadi, xatolikda to'xtamaydi (0.3-band)."""
    if initial_delay is not None:
        await asyncio.sleep(initial_delay.total_seconds())

    while True:
        try:
            await action()
        except asyncio.CancelledError:
            logger.info("Fon vazifasi to'xtatildi: %s", name)
            raise
        except Exception:  # noqa: BLE001
            logger.exception("Fon vazifasi xato berdi: %s", name)
        await asyncio.sleep(interval.total_seconds())


class Scheduler:
    """Barcha fon vazifalarini boshqaradi."""

    def __init__(
        self,
        bot: Bot,
        database: Database,
        config: AppConfig,
        runner: PipelineRunner,
        admin_ids: frozenset[int],
    ) -> None:
        self._bot = bot
        self._db = database
        self._config = config
        self._runner = runner
        self._admin_ids = admin_ids
        self._tasks: list[asyncio.Task] = []

    def start(self) -> None:
        """Barcha vazifalarni fon rejimida ishga tushiradi."""
        vazifalar = [
            ("signal-cycle", cycle_interval(self._config), self._run_cycle, timedelta(seconds=30)),
            (
                "halal-universe",
                timedelta(hours=self._config.halal_screening.refresh_interval_hours),
                self._refresh_universe,
                None,
            ),
            ("subscriptions", timedelta(hours=1), self._check_subscriptions, timedelta(minutes=2)),
            ("weekly-report", timedelta(hours=24), self._weekly_report, timedelta(minutes=5)),
        ]

        for nom, oraliq, harakat, kechikish in vazifalar:
            vazifa = asyncio.create_task(
                _repeat(nom, oraliq, harakat, kechikish), name=nom
            )
            self._tasks.append(vazifa)

        logger.info("Fon vazifalari ishga tushdi: %d ta", len(self._tasks))

    async def stop(self) -> None:
        for vazifa in self._tasks:
            vazifa.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    # ------------------------------------------------------------------ #

    async def _run_cycle(self) -> None:
        """15-bosqich: avtomatik signal sikli."""
        natija = await self._runner.run_once()
        if natija is not None:
            await self._runner.review_open_signals(natija)

    async def _refresh_universe(self) -> None:
        """3.4-band: Top 30 Halal ro'yxatini yangilash."""
        await self._runner.refresh_universe()

    async def _check_subscriptions(self) -> None:
        """1.2-band: muddati tugaganlarni yopish va eslatma yuborish."""
        async with self._db.session() as session:
            xizmat = SubscriptionService(
                self._config.subscriptions,
                UserRepository(session),
                SubscriptionRepository(session),
                PaymentRepository(session),
            )
            await xizmat.expire_overdue()

            eslatmalar = await xizmat.due_reminders()
            yuboriladiganlar = []
            for obuna, qolgan_kun in eslatmalar:
                from core.storage.models import User

                egasi = await session.get(User, obuna.user_id)
                if egasi is not None:
                    yuboriladiganlar.append((egasi.telegram_id, qolgan_kun))
                xizmat.mark_reminder_sent(obuna, qolgan_kun)

        for telegram_id, qolgan_kun in yuboriladiganlar:
            try:
                await self._bot.send_message(
                    telegram_id,
                    t("obuna.eslatma", DEFAULT_LANGUAGE, days=qolgan_kun),
                )
            except Exception:  # noqa: BLE001
                logger.warning("Eslatma yetkazilmadi: telegram_id=%s", telegram_id)

    async def _weekly_report(self) -> None:
        """3.8-band: haftalik o'z-o'zini tekshirish hisoboti (faqat admin)."""
        hozir = utc_now()
        postmortem = self._config.postmortem
        if hozir.weekday() != postmortem.report_weekday:
            return
        if hozir.hour != postmortem.report_hour_utc:
            return

        boshlanish = hozir - timedelta(days=postmortem.lookback_days)
        async with self._db.session() as session:
            signallar = await SignalRepository(session).closed_since(boshlanish)

        matn = render_report(build_report(signallar, postmortem, hozir))
        for admin_id in self._admin_ids:
            try:
                await self._bot.send_message(admin_id, matn)
            except Exception:  # noqa: BLE001
                logger.warning("Hisobot yetkazilmadi: admin=%s", admin_id)
