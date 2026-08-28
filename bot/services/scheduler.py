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
from aiogram.types import FSInputFile

from bot.hosting import video_dir
from bot.i18n import DEFAULT_LANGUAGE, t
from bot.services.broadcast import broadcast_signal, obunachilar, signal_grafigi
from bot.services.runner import PipelineRunner, cycle_interval
from core.analysis.postmortem import build_report, render_report
from core.config.schema import AppConfig
from core.domain.enums import OrderType
from core.domain.models import EntryPlan, SignalLevels
from core.services import SubscriptionService
from core.storage import Database
from core.storage.repositories import (
    AuditReportRepository,
    ContentRepository,
    PaymentRepository,
    RiskBlockRepository,
    SignalRepository,
    SubscriptionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)

#: Rad etish sabablari shuncha kun saqlanadi. Admin paneli oxirgi 24 soatni
#: ko'rsatadi; bir hafta esa "kecha ham shunday edimi" savoliga yetadi.
RISK_BLOCK_RETENTION_DAYS = 7


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
        self._video_dir = video_dir()
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
            ("cleanup", timedelta(hours=24), self._cleanup, timedelta(minutes=10)),
            # Veb-panelda yaratilgan signallar shu vazifa orqali hayotga
            # kiradi. Oraliq qisqa: signal yozilgandan keyin obunachiga
            # yetguncha o'tgan har bir daqiqa — narx harakatlangan daqiqa.
            (
                "web-signals",
                timedelta(minutes=1),
                self._pickup_web_signals,
                timedelta(seconds=20),
            ),
            # Saytga yuklangan video darsliklarni Telegramga chiqarish.
            # Oraliq uzunroq: dars — kunlar davomida yashaydigan kontent,
            # signal kabi daqiqasiga bog'liq emas. Har yuklash bir necha
            # yuz megabaytlik yuborish demak, tez-tez urinish shart emas.
            (
                "web-videos",
                timedelta(minutes=5),
                self._pickup_web_videos,
                timedelta(minutes=1),
            ),
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
        """3.4-band: Halol coinlar ro'yxatini yangilash."""
        await self._runner.refresh_universe()

    async def _cleanup(self) -> None:
        """Eski kuzatuv yozuvlarini o'chiradi.

        Har siklda o'nlab rad etish sababi yoziladi — cheklanmasa jadval
        yillar davomida o'sib ketadi va bepul serverning diskini to'ldiradi.
        Sabablar faqat "hozir nima bo'lyapti" uchun kerak, uzoq tarix emas.
        """
        kesim = utc_now() - timedelta(days=RISK_BLOCK_RETENTION_DAYS)
        async with self._db.session() as session:
            soni = await RiskBlockRepository(session).purge_before(kesim)
        if soni:
            logger.info("Eski rad etish yozuvlari o'chirildi: %d ta", soni)

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

    async def _pickup_web_signals(self) -> None:
        """Veb-panelda yaratilgan signallarni kuzatuvga oladi va tarqatadi.

        Nima uchun bu ish botda: kartochka HAR BIR obunachi uchun alohida
        yasaladi (miqdor uning balansidan hisoblanadi, 5.1-band) va
        `protect_content=True` bilan yuboriladi. Buni veb tomonda
        takrorlash — kartochka mantig'ining ikkinchi nusxasi demak edi.
        Shuning uchun veb faqat BAZAGA YOZADI, yuborish esa shu yerda.

        Ikki qadam ataylab shu tartibda: avval kuzatuv, keyin tarqatish.
        Teskarisi bo'lsa, tarqatish yiqilganda signal kuzatuvsiz qolardi.
        """
        watcher = self._runner.watcher
        await watcher.sync_untracked()

        async with self._db.session() as session:
            kutayotganlar = await SignalRepository(session).pending_broadcast()
            if not kutayotganlar:
                return
            tayyor = [
                (
                    y.id,
                    y.symbol,
                    SignalLevels(entry=y.entry, stop=y.stop, tp1=y.tp1, tp2=y.tp2),
                    OrderType(y.entry_order_type),
                )
                for y in kutayotganlar
            ]
            qabul_qiluvchilar = await obunachilar(session)

        for signal_id, symbol, levels, buyurtma in tayyor:
            reja = EntryPlan(order_type=buyurtma, reference_price=levels.entry)
            grafik = await signal_grafigi(
                self._runner.candles, symbol, levels, self._config
            )
            yuborildi = await broadcast_signal(
                self._bot, qabul_qiluvchilar, symbol, levels, reja,
                signal_id, self._config, chart=grafik,
            )
            async with self._db.session() as session:
                await SignalRepository(session).mark_broadcast(signal_id)
            logger.info(
                "Veb-paneldagi signal tarqatildi: id=%s symbol=%s -> %d ta",
                signal_id, symbol, yuborildi,
            )

    async def _pickup_web_videos(self) -> None:
        """Saytga yuklangan video darsliklarni Telegramga chiqaradi.

        NIMA UCHUN KERAK: sayt video faylni doimiy diskka yozadi va uni
        o'zi o'ynatadi. Bot esa faylni yo'ldan emas, Telegram `file_id`
        dan yuboradi — `file_id` faqat fayl BIR MARTA Telegramga
        yuborilganda paydo bo'ladi.

        Bu qadam bo'lmasa, saytdan qo'shilgan dars botda ko'rinmay
        qolardi: bitta ro'yxat ikki joyda ikki xil bo'lib qolardi.

        Fayl adminning shaxsiy chatiga yuboriladi — bu texnik yuborish,
        maqsadi faqat `file_id` olish. Admin yo'q bo'lsa qadam
        o'tkazib yuboriladi va dars faqat saytda qoladi (bu — xato
        emas, shunchaki sozlanmagan holat).
        """
        if not self._admin_ids:
            return

        qabul_qiluvchi = min(self._admin_ids)
        async with self._db.session() as session:
            kutayotganlar = await ContentRepository(session).pending_upload()
            tayyor = [(k.id, k.title, k.video_path) for k in kutayotganlar]

        for content_id, sarlavha, nom in tayyor:
            if not nom:
                continue
            yol = self._video_dir / nom
            if not yol.exists():
                logger.warning(
                    "Dars videosi diskda yo'q: id=%s fayl=%s", content_id, nom
                )
                continue
            try:
                xabar = await self._bot.send_video(
                    qabul_qiluvchi,
                    FSInputFile(yol),
                    caption=f"🎬 {sarlavha}\n\n(texnik yuborish — Telegram nusxasi tayyorlanmoqda)",
                    protect_content=True,
                )
            except Exception:  # noqa: BLE001
                # Sabab har xil bo'lishi mumkin: fayl juda katta, tarmoq
                # uzildi, Telegram cheklovi. Keyingi urinishda qayta
                # sinaladi — yozuv o'zgarmagani uchun ro'yxatda qoladi.
                logger.warning(
                    "Dars videosi Telegramga chiqmadi: id=%s", content_id, exc_info=True
                )
                continue

            if xabar.video is None:
                logger.warning("Javobda video yo'q: id=%s", content_id)
                continue

            async with self._db.session() as session:
                await ContentRepository(session).set_file_id(
                    content_id, xabar.video.file_id
                )
            logger.info(
                "Dars videosi Telegramga chiqdi: id=%s sarlavha=%s", content_id, sarlavha
            )

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

        hisobot = build_report(signallar, postmortem, hozir)
        matn = render_report(hisobot)

        # Qaydni SAQLAYMIZ: ilgari hisobot faqat Telegramga ketardi va
        # o'qilmay qolsa butunlay yo'qolardi. Yozib bo'lmasa — yuborish
        # baribir davom etadi (0.3-band: qo'shimcha ish asosiy ishni
        # to'xtatmaydi).
        try:
            async with self._db.session() as session:
                await AuditReportRepository(session).save(hisobot, matn)
        except Exception:  # noqa: BLE001
            logger.exception("Haftalik hisobot qaydini yozib bo'lmadi")

        for admin_id in self._admin_ids:
            try:
                await self._bot.send_message(admin_id, matn)
            except Exception:  # noqa: BLE001
                logger.warning("Hisobot yetkazilmadi: admin=%s", admin_id)
