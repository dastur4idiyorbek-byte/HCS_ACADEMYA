"""Kunlik coin qidiruvi chegarasi — obunaga qarab (7-qism).

CHEGARA KODDA QATTIQ YOZILMAGAN. Raqamlar `KuzatuvConfig` da va
admin panelda o'zgartiriladi — prompt shuni talab qiladi.

SANA BO'YICHA, TOZALOVCHI VAZIFA BILAN EMAS. "Har kuni 00:00 da
nolga tushirish" vazifasi yiqilsa yoki bot o'chirilgan bo'lsa,
chegara mangu qolib ketardi. Sana bilan esa hech narsa yugurishi
shart emas: yangi kun kelsa, o'sha sana uchun qator hali yo'q va
hisob noldan boshlanadi.

UTC BO'YICHA. Foydalanuvchi vaqt mintaqasi bo'yicha hisoblash
chiroyliroq ko'rinardi, lekin uni bilish uchun brauzerdan so'rash
kerak — va o'sha javobni foydalanuvchi o'zgartirib, chegarani
chetlab o'tishi mumkin bo'lardi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.schema import KuzatuvConfig
from core.domain.enums import SubscriptionTier
from core.storage.models import KunlikQidiruv


@dataclass(frozen=True, slots=True)
class QidiruvHolati:
    """Foydalanuvchi bugun nechta qidiruv qila oladi."""

    ishlatildi: int
    chegara: int

    @property
    def qoldi(self) -> int:
        return max(0, self.chegara - self.ishlatildi)

    @property
    def mumkin(self) -> bool:
        return self.qoldi > 0


def chegara_ol(config: KuzatuvConfig, tarif: SubscriptionTier | None) -> int:
    """Tarifga mos kunlik chegara.

    Tarif `None` yoki noma'lum bo'lsa — obunasiz chegara. Noma'lum
    tarifni "cheksiz" deb o'qish teshik ochardi.
    """
    if tarif is SubscriptionTier.PREMIUM:
        return config.qidiruv_premium
    if tarif is SubscriptionTier.PRO:
        return config.qidiruv_pro
    if tarif is SubscriptionTier.LITE:
        return config.qidiruv_lite
    return config.qidiruv_obunasiz


def bugun() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


class QidiruvChegarasi:
    """Qidiruvlarni sanaydi va chegarani qo'llaydi."""

    def __init__(self, session: AsyncSession, config: KuzatuvConfig) -> None:
        self._session = session
        self._config = config

    async def holat(
        self, user_id: int, tarif: SubscriptionTier | None
    ) -> QidiruvHolati:
        """Bugungi holat — hech narsa o'zgartirmaydi."""
        return QidiruvHolati(
            ishlatildi=await self._soni(user_id),
            chegara=chegara_ol(self._config, tarif),
        )

    async def ishlat(
        self, user_id: int, tarif: SubscriptionTier | None
    ) -> QidiruvHolati:
        """Bitta qidiruvni hisobga oladi.

        Chegara tugagan bo'lsa hisob OSHIRILMAYDI: aks holda
        foydalanuvchi rad javobini olgan sari qarzi ko'payardi va
        ertaga ham chegarada qolardi.

        Qaytadi: YANGI holat (`mumkin` — qidiruv ruxsat etildimi).
        """
        chegara = chegara_ol(self._config, tarif)
        joriy = await self._qator(user_id)

        if joriy.soni >= chegara:
            return QidiruvHolati(ishlatildi=joriy.soni, chegara=chegara)

        joriy.soni += 1
        return QidiruvHolati(ishlatildi=joriy.soni, chegara=chegara)

    async def _soni(self, user_id: int) -> int:
        stmt = select(KunlikQidiruv.soni).where(
            KunlikQidiruv.user_id == user_id, KunlikQidiruv.sana == bugun()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() or 0

    async def _qator(self, user_id: int) -> KunlikQidiruv:
        stmt = select(KunlikQidiruv).where(
            KunlikQidiruv.user_id == user_id, KunlikQidiruv.sana == bugun()
        )
        qator = (await self._session.execute(stmt)).scalar_one_or_none()
        if qator is None:
            qator = KunlikQidiruv(user_id=user_id, sana=bugun(), soni=0)
            self._session.add(qator)
            await self._session.flush()
        return qator
