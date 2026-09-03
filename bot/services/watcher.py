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
from core.domain.portfolio import PositionOutcome
from core.market_data import PriceCache, PriceStream, SpikeDetector
from core.services import compute_outcome
from core.signals import (
    SignalEvent,
    SignalEventKind,
    SignalTracker,
    kuzatuvchi_qur,
)
from core.storage import Database
from core.storage.repositories import (
    SignalRepository,
    SubscriptionRepository,
    UserPositionRepository,
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

        self._tracker = kuzatuvchi_qur(config)
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

    async def sync_untracked(self) -> int:
        """Bazadagi, lekin kuzatuvda BO'LMAGAN ochiq signallarni qo'shadi.

        Nima uchun kerak: `add_signal()` — jarayon ICHIDAGI chaqiruv. Signal
        veb-panelda yaratilsa, u boshqa jarayonda bo'ladi va bot bu haqda
        hech narsa bilmaydi — signal bazada "ochiq" bo'lib turadi-yu,
        narxi kuzatilmaydi: na TP, na Stop aniqlanadi. Tashqaridan hammasi
        joyida ko'rinadi.

        `restore_from_database()` dan farqi: bu metod FAQAT notanish
        signallarni qo'shadi. Tanishlarini qayta yuklamaydi, chunki
        xotiradagi holat bazadagidan yangiroq bo'lishi mumkin.

        Returns:
            Nechta yangi signal kuzatuvga olingani.
        """
        async with self._db.session() as session:
            yozuvlar = await SignalRepository(session).open_signals()
            yangilar = [
                SignalRepository.to_domain(y)
                for y in yozuvlar
                if self._tracker.get(y.id) is None
            ]

        for signal in yangilar:
            self._tracker.track(signal)

        if yangilar:
            logger.info(
                "Kuzatuvga qo'shildi: %d ta yangi signal (%s)",
                len(yangilar),
                ", ".join(s.symbol for s in yangilar),
            )
            self._sync_subscription()
        return len(yangilar)

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

    async def cancel_signal(self, signal_id: int, reason: str) -> str | None:
        """Yuborilgan signalni admin qarori bilan bekor qiladi.

        Nima uchun kerak edi: signal yuborilgach uni to'xtatishning hech
        qanday yo'li yo'q edi — noto'g'ri kiritilgan yoki sinov uchun
        berilgan signal TP/Stop'gacha yoki 24 soat eskirgunicha "faol"
        bo'lib turardi.

        Bu bitta yo'l HAMMA joyni yangilaydi: kuzatuv, baza, ochiq
        pozitsiyalar va obunachilar. Ularning birortasi qolib ketsa,
        signal bir joyda yopiq, boshqasida ochiq ko'rinardi.

        Signal o'chirilmaydi, `CANCELLED` deb belgilanadi (3.8-band):
        tarix saqlanadi, lekin natija statistikasiga kirmaydi.

        Args:
            signal_id: bazadagi signal id.
            reason: sabab — obunachilarga shu matn boradi.

        Returns:
            Coin belgisi, yoki `None` — signal topilmadi yoxud
            allaqachon yopilgan.
        """
        async with self._db.session() as session:
            yozuv = await SignalRepository(session).get(signal_id)
            if yozuv is None or SignalStatus(yozuv.status).is_closed:
                return None
            symbol = yozuv.symbol
            kirish_narxi = yozuv.entry

        hozir = utc_now()
        narx = self._cache.price_of(symbol) or kirish_narxi

        hodisa = self._tracker.cancel(signal_id, hozir, reason, price=narx)
        if hodisa is None:
            # Kuzatuvda yo'q (masalan kuzatuv hali tiklanmagan) — baza va
            # xabarlar baribir yangilanishi kerak, shuning uchun hodisani
            # o'zimiz yasaymiz.
            hodisa = SignalEvent(
                signal_id=signal_id,
                symbol=symbol,
                kind=SignalEventKind.CANCELLED,
                price=narx,
                at=hozir,
                new_status=SignalStatus.CANCELLED,
                detail=reason,
            )

        await self._persist([hodisa])
        # Pozitsiyalar kuzatuvdan chiqarilishidan OLDIN yopiladi: TP1
        # olingan-olinmagani `_tracker` dagi holatdan aniqlanadi.
        await self._close_positions([hodisa])
        await self._notify([hodisa])
        self._tracker.untrack(signal_id)
        self._sync_subscription()

        logger.info("Signal admin tomonidan bekor qilindi: id=%s symbol=%s", signal_id, symbol)
        return symbol

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
            # Narx manbai KESHDAN: ushlash muddati tugagan pozitsiya
            # bozor narxida yopiladi, ya'ni raqam o'ylab topilmaydi.
            hodisalar.extend(
                self._tracker.check_expiry(tick.timestamp, self._cache.price_of)
            )

        if not hodisalar:
            return

        await self._persist(hodisalar)
        await self._close_positions(hodisalar)
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
                    # Qismli yopish hisobga olinsin: TP1 da pozitsiyaning
                    # bir qismi allaqachon sotilgan.
                    tp1_close_pct=self._config.portfolio.tp1_close_pct,
                )

    async def _close_positions(self, events: list[SignalEvent]) -> None:
        """5.4-band: signal yopilganda foydalanuvchilar natijasini hisoblaydi.

        TP1 ga yetilgan bo'lsa qismli yopish hisobga olinadi — ansiz
        "TP1 oldi, keyin Stop" holati sof zarar ko'rinardi.
        """
        yopilganlar = [h for h in events if h.closes_signal and h.signal_id is not None]
        if not yopilganlar:
            return

        for hodisa in yopilganlar:
            signal = next(
                (s for s in self._tracker._signals.values() if s.signal_id == hodisa.signal_id),
                None,
            )
            tp1_narxi = (
                signal.levels.tp1
                if signal is not None and self._reached_tp1(signal)
                else None
            )

            async with self._db.session() as session:
                repo = UserPositionRepository(session)
                pozitsiyalar = await repo.open_for_signal(hodisa.signal_id)
                natijalar: list[tuple[int, PositionOutcome]] = []

                for pozitsiya in pozitsiyalar:
                    natija = compute_outcome(
                        amount_usd=pozitsiya.amount_usd,
                        entry_price=pozitsiya.entry_price,
                        exit_price=hodisa.price,
                        config=self._config.portfolio,
                        tp1_price=tp1_narxi,
                    )
                    await repo.close(pozitsiya, hodisa.price, natija, hodisa.at)
                    natijalar.append((pozitsiya.user_id, natija))

                telegram_id_lar = {
                    user_id: tg_id
                    for user_id, tg_id in await self._telegram_ids(
                        session, [uid for uid, _ in natijalar]
                    )
                }

            await self._notify_results(hodisa, natijalar, telegram_id_lar, tp1_narxi)

    @staticmethod
    def _reached_tp1(signal) -> bool:  # noqa: ANN001
        """Signal yopilishdan oldin TP1 ga yetganmi.

        `status` ga qarash yetarli emas edi: TP1 dan keyin Stop ishlasa
        holat STOPPED bo'lib qolardi va qismli sotish hisobga olinmasdan,
        "TP1 oldi, keyin Stop" sof zarar ko'rinardi.
        """
        return signal.tp1_reached or signal.status in {
            SignalStatus.TP1_HIT,
            SignalStatus.TP2_HIT,
        }

    @staticmethod
    async def _telegram_ids(session, user_ids: list[int]):  # noqa: ANN001, ANN205
        if not user_ids:
            return []
        from sqlalchemy import select

        from core.storage.models import User

        stmt = select(User.id, User.telegram_id).where(User.id.in_(user_ids))
        return list((await session.execute(stmt)).all())

    async def _notify_results(
        self,
        event: SignalEvent,
        results: list[tuple[int, PositionOutcome]],
        telegram_ids: dict[int, int],
        tp1_price: float | None,
    ) -> None:
        """Har bir ishtirokchiga SHAXSIY natijasini yuboradi."""
        for user_id, natija in results:
            telegram_id = telegram_ids.get(user_id)
            if telegram_id is None:
                continue

            matn = t(
                "signal.natija_xabari",
                DEFAULT_LANGUAGE,
                emoji="🟢" if natija.is_profit else "🔴",
                symbol=event.symbol,
                pnl_pct=f"{natija.pnl_pct:+.2f}%",
                pnl_usd=f"${natija.pnl_usd:+,.2f}",
            )
            if natija.partial_close_pct:
                matn += t(
                    "signal.natija_qismli",
                    DEFAULT_LANGUAGE,
                    share=f"{natija.partial_close_pct:.0f}",
                )

            try:
                await self._bot.send_message(telegram_id, matn, protect_content=True)
            except Exception:  # noqa: BLE001
                logger.warning("Natija yetkazilmadi: telegram_id=%s", telegram_id)

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
        #
        # Ilgari BUTUN Stop xabarining tafsiloti yashirilardi. Endi u
        # kerak: TP1 dan keyingi chiqish "zarar" emas, "kirish narxida
        # yopildi, TP1 dagi foyda saqlandi" — foydalanuvchi buni bilishi
        # shart, aks holda foydali savdoni zarar deb o'qiydi.
        if event.detail and event.kind is not SignalEventKind.FALSE_SIGNAL:
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
