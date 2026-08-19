"""1.2-band: obuna hayot-sikli.

To'lov avtomatik EMAS: foydalanuvchi tashqarida to'laydi, chek yuboradi,
admin qo'lda tasdiqlaydi yoki rad etadi. Tasdiqlangach obuna muddati
avtomatik belgilanadi.

Kunlik tarif = sinov muddati. Muddat tugasa obuna avtomatik yopiladi,
alohida eslatma jadvali kerak emas (1 kun juda qisqa). Oylik uchun esa
tugashiga 1-2 kun qolganda eslatma yuboriladi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.config.schema import SubscriptionsConfig
from core.domain.enums import PaymentStatus, SubscriptionPeriod, SubscriptionTier
from core.storage.models import Payment, Subscription
from core.storage.repositories import (
    PaymentRepository,
    SubscriptionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SubscriptionOutcome:
    """To'lovni ko'rib chiqish natijasi."""

    approved: bool
    subscription: Subscription | None
    message_key: str
    detail: str | None = None


class SubscriptionService:
    """Obuna va to'lovlarni boshqaradi."""

    def __init__(
        self,
        config: SubscriptionsConfig,
        users: UserRepository,
        subscriptions: SubscriptionRepository,
        payments: PaymentRepository,
    ) -> None:
        self._config = config
        self._users = users
        self._subscriptions = subscriptions
        self._payments = payments

    def period_days(self, period: SubscriptionPeriod) -> int:
        periods = self._config.periods
        return periods.daily if period is SubscriptionPeriod.DAILY else periods.monthly

    async def submit_payment(
        self,
        user_id: int,
        tier: SubscriptionTier,
        period: SubscriptionPeriod,
        amount: float,
        currency: str,
        receipt_file_id: str | None,
    ) -> Payment:
        """Foydalanuvchi chek yubordi — tasdiqlash navbatiga qo'yiladi."""
        if currency not in self._config.currencies:
            raise ValueError(
                f"Qo'llab-quvvatlanmaydigan valyuta: {currency} "
                f"(ruxsat: {', '.join(self._config.currencies)})"
            )
        return await self._payments.create(
            user_id=user_id,
            tier=tier,
            period=period.value,
            amount=amount,
            currency=currency,
            receipt_file_id=receipt_file_id,
        )

    async def approve_payment(
        self,
        payment: Payment,
        admin_telegram_id: int,
        now: datetime | None = None,
    ) -> SubscriptionOutcome:
        """Admin to'lovni tasdiqladi — obuna avtomatik faollashadi."""
        if payment.status != PaymentStatus.PENDING.value:
            return SubscriptionOutcome(
                approved=False,
                subscription=None,
                message_key="admin.tolov_allaqachon_korilgan",
                detail=f"Hozirgi holat: {payment.status}",
            )

        hozir = now or utc_now()
        period = SubscriptionPeriod(payment.period)
        tier = SubscriptionTier(payment.tier)

        obuna = await self._subscriptions.create(
            user_id=payment.user_id,
            tier=tier,
            period_days=self.period_days(period),
            is_trial=period is SubscriptionPeriod.DAILY,
            now=hozir,
        )

        payment.status = PaymentStatus.APPROVED.value
        payment.reviewed_by = admin_telegram_id
        payment.reviewed_at = hozir
        payment.subscription_id = obuna.id

        logger.info(
            "To'lov tasdiqlandi: payment=%s user=%s tarif=%s muddat=%s",
            payment.id,
            payment.user_id,
            tier.value,
            period.value,
        )
        return SubscriptionOutcome(
            approved=True, subscription=obuna, message_key="obuna.tasdiqlandi"
        )

    async def reject_payment(
        self,
        payment: Payment,
        admin_telegram_id: int,
        reason: str,
        now: datetime | None = None,
    ) -> SubscriptionOutcome:
        """Admin to'lovni rad etdi — sabab foydalanuvchiga yetkaziladi."""
        if payment.status != PaymentStatus.PENDING.value:
            return SubscriptionOutcome(
                approved=False,
                subscription=None,
                message_key="admin.tolov_allaqachon_korilgan",
                detail=f"Hozirgi holat: {payment.status}",
            )

        payment.status = PaymentStatus.REJECTED.value
        payment.reviewed_by = admin_telegram_id
        payment.reviewed_at = now or utc_now()
        payment.reject_reason = reason

        logger.info("To'lov rad etildi: payment=%s sabab=%s", payment.id, reason)
        return SubscriptionOutcome(
            approved=False,
            subscription=None,
            message_key="obuna.rad_etildi",
            detail=reason,
        )

    async def tier_for(self, user_id: int) -> SubscriptionTier | None:
        """Foydalanuvchining hozirgi tarifi (obunasi yo'q bo'lsa `None`)."""
        return await self._subscriptions.tier_for(user_id)

    async def expire_overdue(self, now: datetime | None = None) -> int:
        """Muddati tugagan obunalarni yopadi (fon vazifasi)."""
        soni = await self._subscriptions.expire_overdue(now)
        if soni:
            logger.info("Muddati tugagan obunalar yopildi: %d ta", soni)
        return soni

    async def due_reminders(
        self, now: datetime | None = None
    ) -> list[tuple[Subscription, int]]:
        """Eslatma yuborilishi kerak bo'lgan obunalar.

        Returns:
            `(obuna, qolgan_kun)` juftliklari. Takror yuborilmasligi uchun
            `reminders_sent` maydoni tekshiriladi.
        """
        hozir = now or utc_now()
        eng_uzoq = max(self._config.expiry_reminder_days)
        natija: list[tuple[Subscription, int]] = []

        for obuna in await self._subscriptions.expiring_soon(eng_uzoq, hozir):
            qolgan_kun = max(0, (obuna.expires_at - hozir).days)
            if qolgan_kun not in self._config.expiry_reminder_days:
                continue
            yuborilgan = set((obuna.reminders_sent or "").split(",")) - {""}
            if str(qolgan_kun) in yuborilgan:
                continue
            natija.append((obuna, qolgan_kun))
        return natija

    @staticmethod
    def mark_reminder_sent(subscription: Subscription, days_left: int) -> None:
        """Eslatma yuborilganini qayd etadi — takror yubormaslik uchun."""
        yuborilgan = set((subscription.reminders_sent or "").split(",")) - {""}
        yuborilgan.add(str(days_left))
        subscription.reminders_sent = ",".join(sorted(yuborilgan))
