"""Middleware'lar — har bir yangilanishdan oldin bajariladigan tayyorgarlik.

Nima uchun kerak: har bir handlerda "foydalanuvchini topish, rolini
aniqlash, tarifini olish" kodini takrorlamaslik uchun. Handler tayyor
kontekstni oladi va faqat o'z ishini qiladi (yupqa qatlam tamoyili).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as TgUser

from bot.settings import BotSettings
from core.storage import Database
from core.storage.repositories import SubscriptionRepository, UserRepository
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


def _extract_user(event: TelegramObject) -> TgUser | None:
    if isinstance(event, Message | CallbackQuery):
        return event.from_user
    return getattr(event, "from_user", None)


class UserContextMiddleware(BaseMiddleware):
    """Foydalanuvchini bazadan topadi/yaratadi va kontekstga qo'yadi.

    Handlerlarga uzatiladigan kalitlar:
        `db_user`  — `core.storage.models.User`
        `tier`     — hozirgi obuna tarifi yoki `None`
        `is_admin` — 1.1-band: rol Telegram ID asosida
        `language` — foydalanuvchi tili
    """

    def __init__(self, database: Database, settings: BotSettings) -> None:
        self._db = database
        self._settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = _extract_user(event)
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        is_admin = self._settings.is_admin(tg_user.id)

        async with self._db.session() as session:
            users = UserRepository(session)
            db_user = await users.get_or_create(
                telegram_id=tg_user.id,
                username=tg_user.username,
                full_name=tg_user.full_name,
                is_admin=is_admin,
            )
            tier = await SubscriptionRepository(session).tier_for(db_user.id)
            data["db_user_id"] = db_user.id
            data["db_user"] = db_user

        data["tier"] = tier
        data["is_admin"] = is_admin
        data["language"] = db_user.language
        data["settings"] = self._settings
        data["database"] = self._db
        return await handler(event, data)


class AdminOnlyMiddleware(BaseMiddleware):
    """Admin routerga biriktiriladi — boshqalar uchun yangilanish to'xtatiladi.

    Javob berilmaydi (jim e'tiborsiz qoldiriladi): admin panelning mavjudligi
    oddiy foydalanuvchiga bildirilmasligi kerak.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not data.get("is_admin", False):
            tg_user = _extract_user(event)
            logger.warning(
                "Admin bo'limiga ruxsatsiz urinish: telegram_id=%s",
                tg_user.id if tg_user else "nomalum",
            )
            return None
        return await handler(event, data)
