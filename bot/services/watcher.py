"""2-bo'lim: narx oqimi kuzatuvchisi — fon vazifasi.

Vazifasi (juda tor, ataylab):
    narx oqimi  ->  SignalTracker  ->  hodisalar  ->  baza + Telegram

Qaror qabul qilmaydi: barcha mantiq `core/signals/tracker.py` da, u yerda
sof va test qilingan. Bu qatlam faqat ulab turadi.

4.7-band: narx sakrashi aniqlansa (kill switch), adminlarga ogohlantirish
yuboriladi va bayroq ko'tariladi — inson tekshirmaguncha tushmaydi.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

from aiogram import Bot

from bot.i18n import DEFAULT_LANGUAGE, t
from core.config.schema import AppConfig
from core.domain.enums import SignalStatus, SubscriptionTier
from core.market_data import PriceCache, PriceStream, SpikeDetector
from core.signals import SignalEvent, SignalTracker
from core.storage import Database
from core.storage.repositories import (
    SignalRepository,
    SubscriptionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)

#: Eskirgan signallarni tekshirish oralig'i
EXPIRY_CHECK_INTERVAL = timedelta(minutes=15)


class SignalWatcher:
    """Narx oqimini kuzatib, signal holatini yangilab boradi."""

    def __init__(
        self,
        bot: Bot,
        database: Database,
        config: AppConfig,
        stream: PriceStream,
        admin_ids: frozenset[int],
    ) -> None:
        self._bot = bot
        self._db = database
        self._config = config
        self._stream = stream
        self._admin_ids = admin_ids

        self._tracker = SignalTracker()
        self._cache = PriceCache()
        self._spikes = SpikeDetector(
            threshold_pct=config.risk_engine.kill_switch.price_spike_pct,
            window=timedelta(seconds=config.risk_engine.kill_switch.price_spike_window_seconds),
        )
        self._kill_switch_active = False
        self._kill_switch_reason: str | None = None
        self._last_expiry_check = utc_now()

    # ------------------------------------------------------------------ #
    #  Holat (Risk Engine shu yerdan o'qiydi)
    # ------------------------------------------------------------------ #

    @property
    def tracker(self) -> SignalTracker:
        return self._tracker

    @property
    def prices(self) -> PriceCache:
        return self._cache

    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch_active

    @property
    def kill_switch_reason(self) -> str | None:
        return self._kill_switch_reason

    def reset_kill_switch(self) -> None:
        """4.7-band: faqat inson tekshiruvidan keyin chaqiriladi."""
        self._kill_switch_active = False
        self._kill_switch_reason = None
        self._spikes.reset()
        logger.warning("Kill switch admin tomonidan qayta ishga tushirildi")

    # ------------------------------------------------------------------ #
    #  Ishga tushirish
    # ------------------------------------------------------------------ #

    async def restore_from_database(self) -> int:
        """Bot qayta ishga tushganda ochiq signallarni kuzatuvga qaytaradi.

        Ansiz qayta ishga tushirish barcha faol signallarni "yo'qotardi".
        """
        async with self._db.session() as session:
            yozuvlar = await SignalRepository(session).open_signals()
            signallar = [SignalRepository.to_domain(y) for y in yozuvlar]

        for signal in signallar:
            self._tracker.track(signal)

        if signallar:
            logger.info("Kuzatuv tiklandi: %d ta ochiq signal", len(signallar))
        self._sync_subscription()
        return len(signallar)

    def add_signal(self, signal_id: int) -> None:
        """Yangi signal qo'shilganda kuzatuvga oladi (handler chaqiradi)."""
        asyncio.create_task(self._add_signal(signal_id))

    async def _add_signal(self, signal_id: int) -> None:
        async with self._db.session() as session:
            yozuv = await SignalRepository(session).get(signal_id)
            if yozuv is None:
                return
            signal = SignalRepository.to_domain(yozuv)
        self._tracker.track(signal)
        self._sync_subscription()

    def _sync_subscription(self) -> None:
        """Kuzatiladigan coinlar ro'yxatini oqimga yetkazadi."""
        self._stream.subscribe(self._tracker.symbols())

    # ------------------------------------------------------------------ #
    #  Asosiy sikl
    # ------------------------------------------------------------------ #

    async def run(self) -> None:
        """Narx oqimini uzluksiz o'qiydi. Chaqiruvchi buni vazifa sifatida ishga tushiradi."""
        await self.restore_from_database()
        logger.info("Signal kuzatuvchisi ishga tushdi")

        async for tick in self._stream.stream():
            try:
                await self._handle_tick(tick)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                # 0.3-band: bitta narx nuqtasidagi xato kuzatuvni to'xtatmasin
                logger.exception("Narx nuqtasini qayta ishlashda xato: %s", tick.symbol)

    async def _handle_tick(self, tick) -> None:  # noqa: ANN001
        self._cache.update(tick)

        # 4.7 — kill switch
        sakrash = self._spikes.observe(tick.symbol, tick.price, tick.timestamp)
        if sakrash is not None and not self._kill_switch_active:
            await self._trigger_kill_switch(tick.symbol, sakrash)

        hodisalar = self._tracker.on_price(tick.symbol, tick.price, tick.timestamp)

        # Eskirgan signallarni vaqti-vaqti bilan tekshiramiz
        if tick.timestamp - self._last_expiry_check >= EXPIRY_CHECK_INTERVAL:
            self._last_expiry_check = tick.timestamp
            hodisalar.extend(self._tracker.check_expiry(tick.timestamp))

        if not hodisalar:
            return

        await self._persist(hodisalar)
        await self._notify(hodisalar)
        self._sync_subscription()

    async def _persist(self, events: list[SignalEvent]) -> None:
        async with self._db.session() as session:
            repo = SignalRepository(session)
            for hodisa in events:
                if hodisa.signal_id is None:
                    continue
                await repo.apply_event(
                    signal_id=hodisa.signal_id,
                    status=hodisa.new_status,
                    price=hodisa.price,
                    at=hodisa.at,
                    kind=hodisa.kind.value,
                    detail=hodisa.detail,
                )

    async def _notify(self, events: list[SignalEvent]) -> None:
        """Obunachilarga holat o'zgarishini yetkazadi."""
        async with self._db.session() as session:
            qabul_qiluvchilar = await self._subscriber_ids(session)

        for hodisa in events:
            matn = self._format_event(hodisa)
            for telegram_id in qabul_qiluvchilar:
                try:
                    await self._bot.send_message(telegram_id, matn, protect_content=True)
                except Exception:  # noqa: BLE001
                    logger.warning("Xabar yetkazilmadi: telegram_id=%s", telegram_id)

    def _format_event(self, event: SignalEvent) -> str:
        status = event.new_status
        holat = t(f"signal.holat_{status.value}", DEFAULT_LANGUAGE)
        sarlavha = t(
            "signal.yangilandi",
            DEFAULT_LANGUAGE,
            emoji=status.emoji,
            symbol=event.symbol,
            status=holat,
        )
        # "Yolg'on signal" bayrog'i faqat admin uchun — foydalanuvchiga
        # texnik tafsilot ko'rsatilmaydi.
        if event.detail and status is not SignalStatus.STOPPED:
            return f"{sarlavha}\n{event.detail}"
        return sarlavha

    async def _subscriber_ids(self, session) -> list[int]:  # noqa: ANN001
        users = UserRepository(session)
        obunalar = SubscriptionRepository(session)
        natija: list[int] = []
        for user in await users.active_users(since_days=90):
            tier = await obunalar.tier_for(user.id)
            if tier is not None and tier.covers(SubscriptionTier.LITE):
                natija.append(user.telegram_id)
        return natija

    async def _trigger_kill_switch(self, symbol: str, change_pct: float) -> None:
        """4.7-band: g'ayrioddiy sakrash — barcha signal berish to'xtaydi."""
        self._kill_switch_active = True
        oyna = self._config.risk_engine.kill_switch.price_spike_window_seconds
        self._kill_switch_reason = (
            f"{symbol}: {oyna} soniyada {change_pct:+.2f}% harakat"
        )
        logger.critical("KILL SWITCH ishga tushdi: %s", self._kill_switch_reason)

        xabar = (
            f"🚨 FAVQULODDA TO'XTASH\n\n{self._kill_switch_reason}\n\n"
            "Yangi signal berish to'xtatildi. Tekshirib, qo'lda qayta ishga tushiring."
        )
        for admin_id in self._admin_ids:
            try:
                await self._bot.send_message(admin_id, xabar)
            except Exception:  # noqa: BLE001
                logger.warning("Adminga ogohlantirish yetkazilmadi: %s", admin_id)
