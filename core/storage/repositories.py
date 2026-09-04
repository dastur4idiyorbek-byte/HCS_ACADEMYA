"""Ma'lumotlarga kirish qatlami (repository).

Nima uchun `bot/` da emas, `core/` da: bir xil so'rovlarni Telegram
handlerlari ham, fon tahlil sikli ham, kelajakdagi REST API ham ishlatadi.
Handlerlarda SQL yozilsa, mobil ilovaga o'tishda hammasi qayta yozilardi
(0.1-band).

Har bir repository sessiyani TASHQARIDAN oladi — tranzaksiya chegarasini
chaqiruvchi belgilaydi.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.domain.enums import (
    HalalStatus,
    OrderType,
    PaymentStatus,
    SignalSource,
    SignalStatus,
    SubscriptionStatus,
    SubscriptionTier,
    UserRole,
)
from core.domain.models import (
    ClosedSignal,
    EntryPlan,
    HalalVerdict,
    Signal,
    SignalLevels,
    outcome_from_status,
    signal_levels,
)
from core.domain.portfolio import (
    PositionOutcome,
    PositionSnapshot,
    blended_result_pct,
)
from core.storage.models import (
    BozorKesimi,
    CoinRuling,
    Content,
    Payment,
    PriceConfig,
    SignalRecord,
    Subscription,
    User,
    UserPosition,
    Violation,
)
from core.storage.models import BozorKorinishi as BozorKorinishiRecord
from core.storage.models import (
    SignalEvent as SignalEventRow,
)
from core.utils.time_utils import utc_now


class UserRepository:
    """Foydalanuvchilar."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
        is_admin: bool = False,
    ) -> User:
        """Foydalanuvchini topadi yoki yaratadi va faollik vaqtini yangilaydi.

        `is_admin` har safar qayta qo'llaniladi: admin ro'yxati `.env` da
        boshqariladi, shuning uchun u yerdan olib tashlangan odam bazada
        admin bo'lib qolmasligi kerak.
        """
        user = await self.get_by_telegram_id(telegram_id)
        rol = UserRole.ADMIN.value if is_admin else UserRole.USER.value

        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                role=rol,
                last_active_at=utc_now(),
            )
            self._session.add(user)
            await self._session.flush()
            return user

        user.username = username or user.username
        user.full_name = full_name or user.full_name
        user.role = rol
        user.last_active_at = utc_now()
        return user

    async def set_balance(self, user: User, balance: float) -> None:
        """5.1-band: foydalanuvchi o'zi kiritgan balans (hisobga ulanmagan)."""
        if balance < 0:
            raise ValueError("Balans manfiy bo'lishi mumkin emas")
        user.declared_balance_usd = balance
        user.balance_updated_at = utc_now()

    async def active_users(self, since_days: int) -> list[User]:
        """5.2-band: agregat sig'im hisobi uchun faol foydalanuvchilar."""
        chegara = utc_now() - timedelta(days=since_days)
        stmt = select(User).where(
            User.last_active_at.is_not(None),
            User.last_active_at >= chegara,
            User.is_blocked.is_(False),
        )
        return list((await self._session.execute(stmt)).scalars())

    async def all_telegram_ids(self) -> list[int]:
        """Broadcast uchun (1.5-band)."""
        stmt = select(User.telegram_id).where(User.is_blocked.is_(False))
        return list((await self._session.execute(stmt)).scalars())


class SubscriptionRepository:
    """Obunalar (1.2-band)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_for(self, user_id: int, now: datetime | None = None) -> Subscription | None:
        """Foydalanuvchining hozir amal qilayotgan obunasi.

        Bir nechta bo'lsa eng yuqori tarif qaytariladi — foydalanuvchi
        to'lagan eng katta imkoniyatni ko'rishi kerak.
        """
        hozir = now or utc_now()
        stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.expires_at > hozir,
        )
        obunalar = list((await self._session.execute(stmt)).scalars())
        if not obunalar:
            return None
        return max(obunalar, key=lambda s: SubscriptionTier(s.tier).rank)

    async def tier_for(self, user_id: int, now: datetime | None = None) -> SubscriptionTier | None:
        obuna = await self.active_for(user_id, now)
        return SubscriptionTier(obuna.tier) if obuna else None

    async def create(
        self,
        user_id: int,
        tier: SubscriptionTier,
        period_days: int,
        is_trial: bool,
        now: datetime | None = None,
    ) -> Subscription:
        boshlanish = now or utc_now()
        obuna = Subscription(
            user_id=user_id,
            tier=tier.value,
            period="daily" if is_trial else "monthly",
            status=SubscriptionStatus.ACTIVE.value,
            starts_at=boshlanish,
            expires_at=boshlanish + timedelta(days=period_days),
            is_trial=is_trial,
        )
        self._session.add(obuna)
        await self._session.flush()
        return obuna

    async def expiring_soon(self, days: int, now: datetime | None = None) -> list[Subscription]:
        """1.2-band: muddat tugashiga 1-2 kun qolganda eslatma.

        Kunlik (sinov) tarif chiqarib tashlanadi — 1 kun juda qisqa, eslatma
        mantiqiy emas (spetsifikatsiya talabi).
        """
        hozir = now or utc_now()
        stmt = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.is_trial.is_(False),
            Subscription.expires_at > hozir,
            Subscription.expires_at <= hozir + timedelta(days=days),
        )
        return list((await self._session.execute(stmt)).scalars())

    async def expire_overdue(self, now: datetime | None = None) -> int:
        """Muddati tugaganlarni yopadi. Qaytaradi: nechta obuna yopildi."""
        hozir = now or utc_now()
        stmt = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.expires_at <= hozir,
        )
        muddati_tugagan = list((await self._session.execute(stmt)).scalars())
        for obuna in muddati_tugagan:
            obuna.status = SubscriptionStatus.EXPIRED.value
        return len(muddati_tugagan)

    async def suspend(self, subscription: Subscription, reason: str) -> None:
        """1.3-band: qoidabuzarlik uchun vaqtincha to'xtatish."""
        subscription.status = SubscriptionStatus.SUSPENDED.value
        subscription.suspended_at = utc_now()
        subscription.suspend_reason = reason

    async def restore(self, subscription: Subscription) -> None:
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.suspended_at = None
        subscription.suspend_reason = None


class PaymentRepository:
    """To'lovlar — avtomatik EMAS, admin qo'lda tasdiqlaydi (1.2-band)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: int,
        tier: SubscriptionTier,
        period: str,
        amount: float,
        currency: str,
        receipt_file_id: str | None,
    ) -> Payment:
        tolov = Payment(
            user_id=user_id,
            tier=tier.value,
            period=period,
            amount=amount,
            currency=currency,
            receipt_file_id=receipt_file_id,
            status=PaymentStatus.PENDING.value,
        )
        self._session.add(tolov)
        await self._session.flush()
        return tolov

    async def get(self, payment_id: int) -> Payment | None:
        return await self._session.get(Payment, payment_id)

    async def pending(self, limit: int = 20) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.status == PaymentStatus.PENDING.value)
            .order_by(Payment.created_at)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def pending_count(self) -> int:
        stmt = select(func.count()).select_from(Payment).where(
            Payment.status == PaymentStatus.PENDING.value
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def has_pending(self, user_id: int) -> bool:
        """Bir foydalanuvchi ketma-ket bir nechta chek yubormasligi uchun."""
        stmt = select(Payment.id).where(
            Payment.user_id == user_id,
            Payment.status == PaymentStatus.PENDING.value,
        )
        return (await self._session.execute(stmt)).first() is not None


class PriceRepository:
    """1.2-band: narxlarni admin panel orqali dinamik belgilash."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, tier: SubscriptionTier, period: str, currency: str
    ) -> PriceConfig | None:
        stmt = select(PriceConfig).where(
            PriceConfig.tier == tier.value,
            PriceConfig.period == period,
            PriceConfig.currency == currency,
            PriceConfig.is_active.is_(True),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_active(self) -> list[PriceConfig]:
        stmt = select(PriceConfig).where(PriceConfig.is_active.is_(True))
        return list((await self._session.execute(stmt)).scalars())

    async def upsert(
        self,
        tier: SubscriptionTier,
        period: str,
        currency: str,
        amount: float,
        payment_details: str | None = None,
    ) -> PriceConfig:
        if amount <= 0:
            raise ValueError("Narx musbat bo'lishi kerak")
        mavjud = await self.get(tier, period, currency)
        if mavjud is not None:
            mavjud.amount = amount
            if payment_details is not None:
                mavjud.payment_details = payment_details
            return mavjud

        narx = PriceConfig(
            tier=tier.value,
            period=period,
            currency=currency,
            amount=amount,
            payment_details=payment_details,
        )
        self._session.add(narx)
        await self._session.flush()
        return narx


class ContentRepository:
    """Video/strategiya kontent, minimal tarif bilan (1.5-band)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def available_for(self, tier: SubscriptionTier | None) -> list[Content]:
        """Foydalanuvchi ocha oladigan kontent.

        Obunasi yo'q bo'lsa bo'sh ro'yxat — pullik bo'lim umuman ko'rinmaydi
        (1.3-band).
        """
        if tier is None:
            return []
        ruxsat = [t.value for t in SubscriptionTier if tier.covers(t)]
        stmt = (
            select(Content)
            .where(Content.is_published.is_(True), Content.min_tier.in_(ruxsat))
            .order_by(Content.position, Content.id)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def pending_upload(self, limit: int = 5) -> list[Content]:
        """Saytga yuklangan, lekin Telegramga hali chiqmagan darslar.

        Sayt video faylni doimiy diskka yozadi va `video_path` ni
        to'ldiradi. Telegram `file_id` esa faqat fayl BOTGA yuborilganda
        paydo bo'ladi — bu Telegram cheklovi. Shu so'rov o'sha "diskda
        bor, Telegramda yo'q" darslarni topadi.

        Usiz saytdan qo'shilgan dars botda ko'rinmay qolardi: ikki
        joyda ikki xil ro'yxat — foydalanuvchi uchun eng chalkash holat.
        """
        stmt = (
            select(Content)
            .where(Content.video_path.is_not(None), Content.file_id.is_(None))
            .order_by(Content.id)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def set_file_id(self, content_id: int, file_id: str) -> None:
        """Telegramga chiqqan darsning `file_id` sini saqlaydi."""
        yozuv = await self._session.get(Content, content_id)
        if yozuv is not None:
            yozuv.file_id = file_id

    async def add(
        self,
        kind: str,
        title: str,
        file_id: str | None,
        min_tier: SubscriptionTier,
        description: str | None = None,
    ) -> Content:
        kontent = Content(
            kind=kind,
            title=title,
            file_id=file_id,
            min_tier=min_tier.value,
            description=description,
        )
        self._session.add(kontent)
        await self._session.flush()
        return kontent


class ViolationRepository:
    """1.3-band: qoidabuzarlik qaydi."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        user_id: int,
        reason: str,
        reported_by: int | None,
        suspended_days: int | None = None,
    ) -> Violation:
        qayd = Violation(
            user_id=user_id,
            reason=reason,
            reported_by=reported_by,
            suspended_days=suspended_days,
        )
        self._session.add(qayd)
        await self._session.flush()
        return qayd

    async def count_for(self, user_id: int) -> int:
        stmt = select(func.count()).select_from(Violation).where(Violation.user_id == user_id)
        return (await self._session.execute(stmt)).scalar_one()


class CoinRulingRepository:
    """1.4-band: halol/harom/shubhali ro'yxatini admin tahrirlaydi."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def all_verdicts(self) -> dict[str, HalalVerdict]:
        """Barcha qarorlar — skrining reyestriga yuklash uchun."""
        stmt = select(CoinRuling)
        return {
            qaror.symbol.upper(): HalalVerdict(
                symbol=qaror.symbol.upper(),
                status=HalalStatus(qaror.status),
                reason=qaror.reason,
            )
            for qaror in (await self._session.execute(stmt)).scalars()
        }

    async def set_ruling(
        self,
        symbol: str,
        status: HalalStatus,
        reason: str,
        set_by: int | None = None,
    ) -> CoinRuling:
        upper = symbol.upper()
        stmt = select(CoinRuling).where(CoinRuling.symbol == upper)
        mavjud = (await self._session.execute(stmt)).scalar_one_or_none()

        if mavjud is not None:
            mavjud.status = status.value
            mavjud.reason = reason
            mavjud.set_by = set_by
            return mavjud

        qaror = CoinRuling(symbol=upper, status=status.value, reason=reason, set_by=set_by)
        self._session.add(qaror)
        await self._session.flush()
        return qaror

    async def remove(self, symbol: str) -> bool:
        stmt = select(CoinRuling).where(CoinRuling.symbol == symbol.upper())
        qaror = (await self._session.execute(stmt)).scalar_one_or_none()
        if qaror is None:
            return False
        await self._session.delete(qaror)
        return True

    async def list_by_status(self, status: HalalStatus) -> list[CoinRuling]:
        stmt = (
            select(CoinRuling)
            .where(CoinRuling.status == status.value)
            .order_by(CoinRuling.symbol)
        )
        return list((await self._session.execute(stmt)).scalars())


class SignalRepository:
    """Signallar (2-bo'lim)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        symbol: str,
        levels: SignalLevels,
        source: SignalSource,
        entry_plan: EntryPlan | None = None,
        score: float | None = None,
        score_breakdown: str | None = None,
        halal_reason: str | None = None,
        note: str | None = None,
        market_health: float | None = None,
        correlation_group: str | None = None,
    ) -> SignalRecord:
        yozuv = SignalRecord(
            symbol=symbol.upper(),
            source=source.value,
            status=SignalStatus.PENDING.value,
            entry=levels.entry,
            stop=levels.stop,
            tp1=levels.tp1,
            tp2=levels.tp_price(2),
            tp3=levels.tp_price(3),
            entry_order_type=(entry_plan.order_type if entry_plan else OrderType.LIMIT).value,
            price_at_signal=entry_plan.current_price if entry_plan else None,
            score=score,
            score_breakdown=score_breakdown,
            halal_reason=halal_reason,
            note=note,
            market_health_at_entry=market_health,
            correlation_group=correlation_group,
        )
        self._session.add(yozuv)
        await self._session.flush()
        return yozuv

    async def get(self, signal_id: int) -> SignalRecord | None:
        return await self._session.get(SignalRecord, signal_id)

    async def open_signals(self) -> list[SignalRecord]:
        """Hali yopilmagan signallar — kuzatuvni tiklash uchun.

        Bot qayta ishga tushganda kuzatuv nolday boshlanmasligi kerak.
        """
        yopiq = SignalStatus.closed_values()
        stmt = (
            select(SignalRecord)
            .where(SignalRecord.status.not_in(yopiq))
            .order_by(SignalRecord.created_at)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def recent(self, limit: int = 10) -> list[SignalRecord]:
        stmt = select(SignalRecord).order_by(SignalRecord.created_at.desc()).limit(limit)
        return list((await self._session.execute(stmt)).scalars())

    async def apply_event(
        self,
        signal_id: int,
        status: SignalStatus,
        price: float,
        at: datetime,
        kind: str,
        detail: str | None = None,
        tp1_close_pct: float | None = None,
    ) -> SignalRecord | None:
        """Kuzatuvchidan kelgan hodisani bazaga yozadi.

        Args:
            tp1_close_pct: TP1 da pozitsiyaning necha foizi yopilishi
                (`portfolio.tp1_close_pct`). Berilsa, yakuniy natija
                QISMLI YOPISHNI hisobga oladi.

                Ansiz raqam yolg'on chiqardi: TP1 dan keyin narx kirish
                narxiga qaytsa natija "0%" deb yozilardi — holbuki
                yarmi TP1 da foyda bilan sotilgan edi. TP2 da esa
                teskarisi: butun pozitsiya TP2 da sotilgandek
                ko'rinardi.
        """
        yozuv = await self.get(signal_id)
        if yozuv is None:
            return None

        yozuv.status = status.value
        if status is SignalStatus.TP1_HIT:
            yozuv.tp1_reached = True
            yozuv.reached_tps = max(yozuv.reached_tps or 0, 1)
        if status is SignalStatus.ACTIVE and yozuv.activated_at is None:
            yozuv.activated_at = at
        if status.is_closed:
            yozuv.closed_at = at
            yozuv.close_price = price
            tp1_narxi = yozuv.tp1 if (yozuv.tp1_reached and tp1_close_pct is not None) else None
            yozuv.result_pct = blended_result_pct(
                yozuv.entry, price, tp1_narxi, tp1_close_pct or 0.0
            )
        if kind == "false_signal":
            yozuv.is_false_signal = True

        self._session.add(
            SignalEventRow(
                signal_id=signal_id, event=kind, price=price, detail=detail
            )
        )
        return yozuv


    async def pending_broadcast(self, limit: int = 20) -> list[SignalRecord]:
        """Hali obunachilarga tarqatilmagan OCHIQ signallar.

        Veb-panel signalni faqat bazaga yozadi — Telegramga xabar yuborish
        botning ishi. Bu so'rov o'sha "yozilgan, lekin yuborilmagan"
        signallarni topadi.
        """
        stmt = (
            select(SignalRecord)
            .where(
                SignalRecord.broadcast_at.is_(None),
                SignalRecord.status.in_(SignalStatus.open_values()),
            )
            .order_by(SignalRecord.created_at)
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def mark_broadcast(self, signal_id: int, now: datetime | None = None) -> None:
        """Signal tarqatilgani belgilanadi — ikkinchi marta yuborilmasin."""
        yozuv = await self.get(signal_id)
        if yozuv is not None:
            yozuv.broadcast_at = now or utc_now()

    async def consecutive_stops(self, limit: int = 20) -> int:
        """3.8-band: oxirgi nechta signal KETMA-KET Stop yegan."""
        stmt = (
            select(SignalRecord.status)
            .where(
                SignalRecord.status.in_(
                    [SignalStatus.STOPPED.value, SignalStatus.TP1_HIT.value,
                     SignalStatus.TP2_HIT.value]
                ),
                SignalRecord.closed_at.is_not(None),
            )
            .order_by(SignalRecord.closed_at.desc())
            .limit(limit)
        )
        soni = 0
        for status in (await self._session.execute(stmt)).scalars():
            if status != SignalStatus.STOPPED.value:
                break
            soni += 1
        return soni

    async def net_result_pct_since(self, since: datetime) -> float:
        """Shu vaqtdan beri yopilgan signallarning SOF natijasi, foizda.

        4.1-band (kunlik/haftalik zarar chegarasi) shu raqamga tayanadi.
        Ilgari u umuman hisoblanmasdi: `CycleInput.daily_loss_pct`
        standart `0.0` bo'lib qolardi va qoida HECH QACHON ishlamasdi —
        ya'ni strategiya qancha zarar keltirsa ham signal berishda davom
        etardi.

        SOF natija olinadi, faqat zararlar emas: kun +5% va -4% bilan
        o'tgan bo'lsa, kun yomon o'tmagan. Gross zarar bilan hisoblash
        foydali kunni ham to'xtatib qo'yardi.
        """
        stmt = select(func.sum(SignalRecord.result_pct)).where(
            SignalRecord.closed_at.is_not(None),
            SignalRecord.closed_at >= since,
            SignalRecord.result_pct.is_not(None),
        )
        yigindi = (await self._session.execute(stmt)).scalar()
        return float(yigindi or 0.0)

    async def closed_since(self, since: datetime) -> list[ClosedSignal]:
        """3.8-band: postmortem uchun yopilgan signallar va ularning konteksti.

        TP1 ga yetganini `signal_events` dan bilib olamiz — bu farq muhim:
        "Stop yedi" va "TP1 oldi, keyin Stop yedi" bir xil natija emas.
        """
        yopiq = SignalStatus.closed_values()
        stmt = (
            select(SignalRecord)
            .where(
                SignalRecord.status.in_(yopiq),
                SignalRecord.closed_at.is_not(None),
                SignalRecord.closed_at >= since,
            )
            .order_by(SignalRecord.closed_at)
        )
        yozuvlar = list((await self._session.execute(stmt)).scalars())
        if not yozuvlar:
            return []

        tp1_stmt = select(SignalEventRow.signal_id).where(
            SignalEventRow.signal_id.in_([y.id for y in yozuvlar]),
            SignalEventRow.event == "tp1_hit",
        )
        tp1_olganlar = set((await self._session.execute(tp1_stmt)).scalars())

        return [
            ClosedSignal(
                signal_id=yozuv.id,
                symbol=yozuv.symbol,
                source=SignalSource(yozuv.source),
                outcome=outcome_from_status(
                    SignalStatus(yozuv.status), reached_tp1=yozuv.id in tp1_olganlar
                ),
                score=yozuv.score,
                market_health_at_entry=yozuv.market_health_at_entry,
                result_pct=yozuv.result_pct,
                created_at=yozuv.created_at,
                activated_at=yozuv.activated_at,
                closed_at=yozuv.closed_at,
                is_false_signal=yozuv.is_false_signal,
                correlation_group=yozuv.correlation_group,
            )
            for yozuv in yozuvlar
        ]

    @staticmethod
    def to_domain(record: SignalRecord) -> Signal:
        """DB yozuvidan domain obyektiga — kuzatuvchi shu tipni kutadi."""
        return Signal(
            symbol=record.symbol,
            levels=signal_levels(
                entry=record.entry,
                stop=record.stop,
                tp1=record.tp1,
                tp2=record.tp2,
                tp3=record.tp3,
            ),
            source=SignalSource(record.source),
            status=SignalStatus(record.status),
            score=record.score,
            halal_reason=record.halal_reason,
            note=record.note,
            created_at=record.created_at,
            activated_at=record.activated_at,
            closed_at=record.closed_at,
            signal_id=record.id,
            # Ustundan o'qiladi: status TP dan keyin o'zgarishi mumkin
            # (STOPPED, WEAKENING) va fakt yo'qolardi.
            reached_tps=int(record.reached_tps or (1 if record.tp1_reached else 0)),
        )


class UserPositionRepository:
    """5.4-band: "Men kirdim" orqali qayd etilgan pozitsiyalar."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_entry(
        self,
        user_id: int,
        signal_id: int,
        amount_usd: float,
        entry_price: float,
        risk_amount_usd: float | None = None,
        trade_date: date | None = None,
    ) -> UserPosition:
        """Foydalanuvchi signalga kirganini qayd etadi."""
        if amount_usd <= 0:
            raise ValueError("Miqdor musbat bo'lishi kerak")
        pozitsiya = UserPosition(
            user_id=user_id,
            signal_id=signal_id,
            amount_usd=amount_usd,
            entry_price=entry_price,
            risk_amount_usd=risk_amount_usd,
            trade_date=trade_date or utc_now().date(),
        )
        self._session.add(pozitsiya)
        await self._session.flush()
        return pozitsiya

    async def get(self, user_id: int, signal_id: int) -> UserPosition | None:
        stmt = select(UserPosition).where(
            UserPosition.user_id == user_id, UserPosition.signal_id == signal_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def open_for_signal(self, signal_id: int) -> list[UserPosition]:
        """Signal yopilganda barcha ochiq pozitsiyalarni topish uchun."""
        stmt = select(UserPosition).where(
            UserPosition.signal_id == signal_id, UserPosition.closed_at.is_(None)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def close(
        self,
        position: UserPosition,
        exit_price: float,
        outcome: PositionOutcome,
        closed_at: datetime | None = None,
    ) -> None:
        position.closed_at = closed_at or utc_now()
        position.exit_price = exit_price
        position.partial_exit_price = outcome.partial_exit_price
        position.partial_close_pct = outcome.partial_close_pct
        position.pnl_usd = outcome.pnl_usd
        position.pnl_pct = outcome.pnl_pct

    async def snapshots_for(self, user_id: int) -> list[PositionSnapshot]:
        """Portfel hisobi uchun — DB modeliga bog'lanmagan ko'rinish."""
        stmt = (
            select(UserPosition, SignalRecord.symbol)
            .join(SignalRecord, UserPosition.signal_id == SignalRecord.id)
            .where(UserPosition.user_id == user_id)
            .order_by(UserPosition.created_at.desc())
        )
        qatorlar = (await self._session.execute(stmt)).all()
        return [
            PositionSnapshot(
                symbol=symbol,
                amount_usd=pozitsiya.amount_usd,
                entry_price=pozitsiya.entry_price,
                trade_date=pozitsiya.trade_date,
                closed_at=pozitsiya.closed_at,
                pnl_usd=pozitsiya.pnl_usd,
                pnl_pct=pozitsiya.pnl_pct,
            )
            for pozitsiya, symbol in qatorlar
        ]

    async def participant_count(self, signal_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(UserPosition)
            .where(UserPosition.signal_id == signal_id)
        )
        return (await self._session.execute(stmt)).scalar_one()



class BozorKesimiRepository:
    """Sayt uchun bozor kesimlari tarixi.

    NIMA UCHUN KERAK. BTC.D, USDT.D, TOTAL va boshqalar birjadan
    sham sifatida kelmaydi — manba faqat HOZIRGI holatni beradi.
    Yo'nalishni aytish uchun esa tarix kerak, va uni o'zimiz
    yig'amiz.

    SIGNALGA BOG'LANMAYDI: bu ma'lumot faqat sayt postida
    ishlatiladi (loyiha egasining sharti).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def yozish(self, kod: str, qiymat: float, olingan: datetime) -> BozorKesimi:
        yozuv = BozorKesimi(kod=kod, qiymat=qiymat, olingan=olingan)
        self._session.add(yozuv)
        await self._session.flush()
        return yozuv

    async def tarix(self, kod: str, limit: int = 30) -> list[float]:
        """Eng eskisidan eng yangisiga — `korinish_qur()` shunday kutadi."""
        stmt = (
            select(BozorKesimi)
            .where(BozorKesimi.kod == kod)
            .order_by(BozorKesimi.olingan.desc())
            .limit(limit)
        )
        yozuvlar = list((await self._session.execute(stmt)).scalars())
        return [y.qiymat for y in reversed(yozuvlar)]

    async def oxirgi_vaqt(self, kod: str) -> datetime | None:
        """Shu kod uchun oxirgi yozuv vaqti — takror yozmaslik uchun."""
        stmt = (
            select(BozorKesimi.olingan)
            .where(BozorKesimi.kod == kod)
            .order_by(BozorKesimi.olingan.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()


class BozorKorinishiRepository:
    """Tayyor postlar — saytning yagona manbai."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def saqlash(
        self,
        turi: str,
        sana: datetime,
        asboblar_json: str,
        xulosa: str,
        kutilma: str,
    ) -> BozorKorinishiRecord:
        yozuv = BozorKorinishiRecord(
            turi=turi,
            sana=sana,
            asboblar_json=asboblar_json,
            xulosa=xulosa,
            kutilma=kutilma,
        )
        self._session.add(yozuv)
        await self._session.flush()
        return yozuv

    async def oxirgisi(self, turi: str) -> BozorKorinishiRecord | None:
        stmt = (
            select(BozorKorinishiRecord)
            .where(BozorKorinishiRecord.turi == turi)
            .order_by(BozorKorinishiRecord.sana.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()



