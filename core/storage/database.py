"""Ma'lumotlar bazasi ulanishi va sessiya boshqaruvi.

6.2-band: SQLite -> PostgreSQL ko'chishi faqat `DATABASE_URL` o'zgarishi
bilan amalga oshishi kerak. Shuning uchun bu yerda dialektga xos hech narsa
yo'q, faqat SQLite uchun zarur PRAGMA sozlamalari bundan mustasno.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.storage.base import Base
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///data/hcs.db"


def resolve_database_url(url: str | None = None) -> str:
    return url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


def _ensure_sqlite_directory(url: str) -> None:
    """SQLite fayli uchun papka mavjudligini ta'minlaydi."""
    if not url.startswith("sqlite"):
        return
    _, _, path_part = url.partition(":///")
    if not path_part or path_part == ":memory:":
        return
    Path(path_part).parent.mkdir(parents=True, exist_ok=True)


def create_engine(url: str | None = None, echo: bool = False) -> AsyncEngine:
    """Async engine yaratadi."""
    resolved = resolve_database_url(url)
    _ensure_sqlite_directory(resolved)
    engine = create_async_engine(resolved, echo=echo, future=True)

    if resolved.startswith("sqlite"):
        # WAL — bot va tahlil sikli bir vaqtda yozganda bloklanishni kamaytiradi.
        # foreign_keys — SQLite'da standart o'chirilgan, yoqish SHART.
        @event.listens_for(engine.sync_engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_models(engine: AsyncEngine) -> None:
    """Jadvallarni yaratadi (dastlabki ishga tushirish uchun).

    Ishlab chiqarishda sxema o'zgarishlari Alembic orqali boshqariladi.
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    logger.info("Ma'lumotlar bazasi sxemasi tayyor (%d jadval)", len(Base.metadata.tables))


async def healthcheck(engine: AsyncEngine) -> bool:
    """Baza javob beryaptimi (0.3-band: fail-safe tekshiruvi)."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — sabab log qilinadi, tizim to'xtamaydi
        logger.exception("Ma'lumotlar bazasi javob bermayapti")
        return False


class Database:
    """Engine + sessiya fabrikasining qulay o'ramchisi."""

    def __init__(self, url: str | None = None, echo: bool = False) -> None:
        self.engine = create_engine(url, echo=echo)
        self.session_factory = create_session_factory(self.engine)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Tranzaksiyali sessiya: xato bo'lsa avtomatik rollback."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def init_models(self) -> None:
        await init_models(self.engine)

    async def healthcheck(self) -> bool:
        return await healthcheck(self.engine)

    async def dispose(self) -> None:
        await self.engine.dispose()
