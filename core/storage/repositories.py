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
from core.domain.models import EntryPlan, HalalVerdict, Signal, SignalLevels
from core.storage.models import (
    CoinRuling,
    Content,
    Payment,
    PriceConfig,
    SignalRecord,
    Subscription,
    User,
    Violation,
)
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
            tp2=levels.tp2,
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
        yopiq = [
            SignalStatus.TP2_HIT.value,
            SignalStatus.STOPPED.value,
            SignalStatus.CANCELLED.value,
        ]
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
    ) -> SignalRecord | None:
        """Kuzatuvchidan kelgan hodisani bazaga yozadi."""
        yozuv = await self.get(signal_id)
        if yozuv is None:
            return None

        yozuv.status = status.value
        if status is SignalStatus.ACTIVE and yozuv.activated_at is None:
            yozuv.activated_at = at
        if status in {SignalStatus.TP2_HIT, SignalStatus.STOPPED, SignalStatus.CANCELLED}:
            yozuv.closed_at = at
            yozuv.close_price = price
            yozuv.result_pct = (price - yozuv.entry) / yozuv.entry * 100
        if kind == "false_signal":
            yozuv.is_false_signal = True

        self._session.add(
            SignalEventRow(
                signal_id=signal_id, event=kind, price=price, detail=detail
            )
        )
        return yozuv

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

    @staticmethod
    def to_domain(record: SignalRecord) -> Signal:
        """DB yozuvidan domain obyektiga — kuzatuvchi shu tipni kutadi."""
        return Signal(
            symbol=record.symbol,
            levels=SignalLevels(
                entry=record.entry, stop=record.stop, tp1=record.tp1, tp2=record.tp2
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
        )


def today_utc() -> date:
    return utc_now().date()
