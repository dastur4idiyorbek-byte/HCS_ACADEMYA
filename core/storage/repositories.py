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

from core.analysis.postmortem import ClosedSignal, outcome_from_status
from core.analysis.postmortem.report import SelfAuditReport
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
    EntryPlan,
    HalalVerdict,
    MarketHealth,
    Signal,
    SignalLevels,
)
from core.domain.portfolio import PositionOutcome, PositionSnapshot, PublicStats
from core.storage.models import (
    AuditReport,
    CoinRuling,
    Content,
    DailyStat,
    MarketHealthLog,
    Payment,
    PriceConfig,
    RiskBlock,
    SignalRecord,
    Subscription,
    User,
    UserPosition,
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
                SignalRecord.status.in_(
                    [s.value for s in SignalStatus if s.is_open]
                ),
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
        yopiq = [
            SignalStatus.TP2_HIT.value,
            SignalStatus.STOPPED.value,
            SignalStatus.CANCELLED.value,
        ]
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
            tp1_reached=SignalStatus(record.status)
            in {SignalStatus.TP1_HIT, SignalStatus.TP2_HIT},
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


class DailyStatsRepository:
    """3.6 / 5.4-band: hammaga ochiq shaffoflik raqamlari."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def aggregate(self, since: date, label: str) -> PublicStats:
        """Davr bo'yicha agregat. Shaxsiy ma'lumot oshkor qilinmaydi."""
        signal_stmt = select(SignalRecord).where(
            func.date(SignalRecord.created_at) >= since
        )
        signallar = list((await self._session.execute(signal_stmt)).scalars())

        pozitsiya_stmt = (
            select(
                func.count(func.distinct(UserPosition.user_id)),
                func.coalesce(func.sum(UserPosition.amount_usd), 0.0),
            )
            .where(UserPosition.trade_date >= since)
        )
        ishtirokchilar, hajm = (await self._session.execute(pozitsiya_stmt)).one()

        ballar = [s.score for s in signallar if s.score is not None]
        rr_lar = [
            (s.tp2 - s.entry) / (s.entry - s.stop)
            for s in signallar
            if s.entry > s.stop
        ]

        return PublicStats(
            period_label=label,
            signals_created=len(signallar),
            signals_activated=sum(1 for s in signallar if s.activated_at is not None),
            tp1_count=sum(1 for s in signallar if s.status == SignalStatus.TP1_HIT.value),
            tp2_count=sum(1 for s in signallar if s.status == SignalStatus.TP2_HIT.value),
            stop_count=sum(1 for s in signallar if s.status == SignalStatus.STOPPED.value),
            participants=int(ishtirokchilar or 0),
            total_volume_usd=float(hajm or 0.0),
            average_score=sum(ballar) / len(ballar) if ballar else None,
            average_risk_reward=sum(rr_lar) / len(rr_lar) if rr_lar else None,
        )

    async def upsert_daily(self, stat_date: date, **values: object) -> DailyStat:
        """Kunlik agregatni yozadi yoki yangilaydi."""
        stmt = select(DailyStat).where(DailyStat.stat_date == stat_date)
        mavjud = (await self._session.execute(stmt)).scalar_one_or_none()

        if mavjud is None:
            mavjud = DailyStat(stat_date=stat_date)
            self._session.add(mavjud)

        for kalit, qiymat in values.items():
            setattr(mavjud, kalit, qiymat)
        await self._session.flush()
        return mavjud


class MarketHealthRepository:
    """3.7-band: indeks tarixi.

    Nima uchun saqlanadi: postmortem (3.8) "Indeks 60dan past bo'lganda
    berilgan signallarning necha foizi Stop yegan?" degan savolga javob
    berishi kerak. Bu javob faqat tarix bo'lsa mumkin.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self, health: MarketHealth, is_daily_preview: bool = False
    ) -> MarketHealthLog:
        ballar = {omil.name: omil.score for omil in health.factors}
        yozuv = MarketHealthLog(
            value=health.value,
            band=health.band.value,
            structure_breadth_score=ballar.get("halal_structure_breadth"),
            trend_breadth_score=ballar.get("halal_trend_breadth"),
            btc_dominance_score=ballar.get("btc_dominance_stability"),
            quarterly_phase_score=ballar.get("quarterly_phase"),
            volatility_score=ballar.get("volatility_regime"),
            user_capacity_score=ballar.get("aggregate_user_capacity"),
            saturation_score=ballar.get("signal_saturation"),
            is_daily_preview=is_daily_preview,
            detail="\n".join(omil.explanation for omil in health.factors),
        )
        self._session.add(yozuv)
        await self._session.flush()
        return yozuv

    async def latest(self) -> MarketHealthLog | None:
        stmt = select(MarketHealthLog).order_by(MarketHealthLog.created_at.desc()).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def history(self, limit: int = 24) -> list[MarketHealthLog]:
        stmt = (
            select(MarketHealthLog)
            .order_by(MarketHealthLog.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def average_since(self, since: datetime) -> float | None:
        stmt = select(func.avg(MarketHealthLog.value)).where(
            MarketHealthLog.created_at >= since,
            MarketHealthLog.is_daily_preview.is_(False),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()


class RiskBlockRepository:
    """3.7-band: "tizim nega sokin?" savoliga aniq javob.

    Signal chiqmasligi XATO EMAS (0.2-band), lekin admin SABABINI ko'ra
    olishi kerak — aks holda ishlayotgan tizimni buzuq tizimdan ajratib
    bo'lmaydi. Sikl har bir rad etishni shu yerga yozadi.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_many(
        self,
        rejections: list[tuple[str | None, str, str | None, float | None]],
        market_health: float | None = None,
    ) -> int:
        """Bir siklning barcha rad etishlarini yozadi.

        Args:
            rejections: `(symbol, reason, detail, score)` to'rtliklari.
                `score` — nomzod olgan ball (bo'lsa). Ilgari u yozilmasdi:
                `RejectedCandidate` uni tashib yurardi, lekin bu yerda
                tashlab ketilardi. Natijada dashboard "chegaradan past"
                deb yozardi-yu, QANCHALIK past ekanini ko'rsatolmasdi.
            market_health: o'sha paytdagi indeks — sabablarni keyinroq
                "past salomatlikda" va "normal bozorda" deb ajratish uchun.

        Returns:
            Yozilgan qatorlar soni.
        """
        if not rejections:
            return 0

        for symbol, reason, detail, score in rejections:
            self._session.add(
                RiskBlock(
                    symbol=symbol,
                    reason=reason[:48],
                    detail=detail,
                    market_health=market_health,
                    score=score,
                )
            )
        await self._session.flush()
        return len(rejections)

    async def score_stats_since(
        self, since: datetime, reason: str
    ) -> tuple[int, float, float] | None:
        """Bitta sabab bo'yicha ball statistikasi: `(soni, eng yuqori, o'rtacha)`.

        Nima uchun kerak: "chegaradan past" degan xabar o'zi hech narsa
        aytmaydi. Nomzodlar 78 ball olib 80 chegaradan qaytayotgan
        bo'lsa — chegara bir oz baland. 55 ball olib qaytayotgan
        bo'lsa — chegara umuman erishib bo'lmas. Ikkovi butunlay
        boshqa muammo, lekin dashboardda bir xil ko'rinardi.

        `None` — bu sabab bo'yicha ballli yozuv yo'q.
        """
        stmt = select(
            func.count(RiskBlock.id),
            func.max(RiskBlock.score),
            func.avg(RiskBlock.score),
        ).where(
            RiskBlock.created_at >= since,
            RiskBlock.reason == reason,
            RiskBlock.score.is_not(None),
        )
        soni, eng_yuqori, ortacha = (await self._session.execute(stmt)).one()
        if not soni:
            return None
        return int(soni), float(eng_yuqori), float(ortacha)

    async def summary_since(
        self, since: datetime, limit: int = 10
    ) -> list[tuple[str, int, bool]]:
        """Sabab -> `(nechta marta, sikl darajasidami)`, eng ko'pidan boshlab.

        Aynan shu ro'yxat "nega signal yo'q" savoliga javob beradi: bitta
        sabab hukmronlik qilsa, sozlama noto'g'ri qo'yilgan bo'lishi
        mumkin.

        Uchinchi element nima uchun kerak: yozuvlar IKKI XIL o'lchovda
        yoziladi. Sikl darajasidagi to'xtash (`symbol` yo'q, masalan
        Bozor Salomatligi past) bitta yozuv bo'lsa ham O'SHA SIKLDAGI
        BARCHA coinlarni to'xtatadi; coin darajasidagi yozuv esa faqat
        bittasini. Ikkalasini bitta ustunga qo'shib foizlash — 30 ta
        coinni to'xtatgan sababni bitta coinni to'xtatgani bilan teng
        deb hisoblash demakdir.
        """
        daraja = RiskBlock.symbol.is_(None).label("cycle_level")
        stmt = (
            select(RiskBlock.reason, func.count(RiskBlock.id), daraja)
            .where(RiskBlock.created_at >= since)
            .group_by(RiskBlock.reason, daraja)
            .order_by(func.count(RiskBlock.id).desc())
            .limit(limit)
        )
        return [
            (qator[0], qator[1], bool(qator[2]))
            for qator in (await self._session.execute(stmt)).all()
        ]

    async def latest(self, limit: int = 5) -> list[RiskBlock]:
        """Eng oxirgi rad etishlar — tafsiloti bilan."""
        stmt = select(RiskBlock).order_by(RiskBlock.created_at.desc()).limit(limit)
        return list((await self._session.execute(stmt)).scalars())

    async def purge_before(self, cutoff: datetime) -> int:
        """Eski yozuvlarni o'chiradi.

        Har siklda o'nlab qator yoziladi — cheklanmasa jadval yillar
        davomida o'sib ketadi. Tarixiy tahlil uchun bir necha kun yetarli.
        """
        eskilar = (
            await self._session.execute(
                select(RiskBlock).where(RiskBlock.created_at < cutoff)
            )
        ).scalars()
        soni = 0
        for yozuv in eskilar:
            await self._session.delete(yozuv)
            soni += 1
        return soni


def today_utc() -> date:
    return utc_now().date()


class AuditReportRepository:
    """3.8-band: haftalik hisobotning qaydi.

    Nima uchun kerak: hisobot faqat Telegramga yuborilardi va shu bilan
    yo'qolardi. Endi u veb-panelda ham ko'rinadi va tarix bo'lib qoladi.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: SelfAuditReport, rendered: str) -> AuditReport:
        """Hisobotni yozadi. BIR KUNDA BITTA qayd (davr uzunligi bo'yicha).

        Nima uchun upsert: admin panelda tugmani necha marta bossa,
        shuncha bir xil qator paydo bo'lardi. Har safar YANGILAB borish
        esa ikki foyda beradi — jadval toza qoladi va veb-panel doim eng
        so'nggi holatni ko'rsatadi.
        """
        sana = report.generated_at.date()
        stmt = select(AuditReport).where(
            AuditReport.report_date == sana,
            AuditReport.period_days == report.period_days,
        )
        yozuv = (await self._session.execute(stmt)).scalar_one_or_none()
        if yozuv is None:
            yozuv = AuditReport(report_date=sana, period_days=report.period_days)
            self._session.add(yozuv)

        s = report.stats
        yozuv.generated_at = report.generated_at
        yozuv.rendered = rendered
        yozuv.total = s.total
        yozuv.traded = s.traded
        yozuv.tp2 = s.tp2
        yozuv.tp1_then_stop = s.tp1_then_stop
        yozuv.stop = s.stop
        yozuv.cancelled = s.cancelled
        yozuv.false_signals = s.false_signals
        yozuv.average_score = s.average_score
        yozuv.average_holding_hours = s.average_holding_hours
        yozuv.pattern_count = len(report.patterns)
        yozuv.sample_warning = report.sample_warning

        await self._session.flush()
        return yozuv

    async def latest(self, limit: int = 8) -> list[AuditReport]:
        stmt = (
            select(AuditReport)
            .order_by(AuditReport.generated_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars())
