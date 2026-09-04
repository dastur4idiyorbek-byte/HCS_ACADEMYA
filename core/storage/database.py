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

from sqlalchemy import event, inspect, text
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


def ensure_sqlite_directory(url: str) -> None:
    """SQLite fayli uchun papka mavjudligini ta'minlaydi.

    Ochiq funksiya, chunki uni `create_engine` dan tashqarida ham chaqirish
    kerak: Alembic o'z engine'ini quradi va bu yerga yetib kelmaydi. Papka
    yaratilmasa SQLite "unable to open database file" deb yiqiladi.
    """
    if not url.startswith("sqlite"):
        return
    _, _, path_part = url.partition(":///")
    if not path_part or path_part == ":memory:":
        return
    Path(path_part).parent.mkdir(parents=True, exist_ok=True)


def create_engine(url: str | None = None, echo: bool = False) -> AsyncEngine:
    """Async engine yaratadi."""
    resolved = resolve_database_url(url)
    ensure_sqlite_directory(resolved)
    engine = create_async_engine(resolved, echo=echo, future=True)

    if resolved.startswith("sqlite"):
        # WAL — bot va tahlil sikli bir vaqtda yozganda bloklanishni kamaytiradi.
        # foreign_keys — SQLite'da standart o'chirilgan, yoqish SHART.
        #
        # busy_timeout — endi bazaga IKKINCHI JARAYON ham tegadi: veb-sayt
        # (`web/`) bot bilan bitta serverda, bitta faylni o'qiydi va admin
        # paneli orqali yozadi ham. Busiz SQLite qulf band bo'lsa darhol
        # "database is locked" xatosini beradi; 5 soniya kutish esa oddiy
        # to'qnashuvlarni butunlay yo'q qiladi.
        @event.listens_for(engine.sync_engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _alembic_head() -> str | None:
    """Migratsiyalarning oxirgi versiyasi (`head`), yoki `None`.

    Alembic o'rnatilmagan yoki `migrations/` papkasi yo'q bo'lsa `None` —
    bu xato emas, testlarda migratsiyalar kerak emas.
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ImportError:
        return None

    ildiz = Path(__file__).resolve().parents[2]
    ini = ildiz / "alembic.ini"
    if not ini.is_file() or not (ildiz / "migrations" / "versions").is_dir():
        return None

    try:
        sozlama = Config(str(ini))
        sozlama.set_main_option("script_location", str(ildiz / "migrations"))
        return ScriptDirectory.from_config(sozlama).get_current_head()
    except Exception:  # noqa: BLE001 — belgilamaslik ishga tushirishni to'smaydi
        logger.debug("Alembic `head` versiyasi aniqlanmadi", exc_info=True)
        return None


def _stamp_if_fresh(connection, head: str) -> None:  # noqa: ANN001
    """Yangi yaratilgan bazani `head` versiyasi bilan belgilaydi.

    Nima uchun kerak: `create_all` jadvallarni yaratadi, lekin
    `alembic_version` ni to'ldirmaydi. Keyin serverda `alembic upgrade
    head` ishga tushirilsa, u noldan boshlashga urinadi va "jadval
    allaqachon mavjud" xatosini beradi.

    Faqat BO'SH `alembic_version` to'ldiriladi — mavjud versiya hech
    qachon o'zgartirilmaydi, aks holda qo'llanilmagan migratsiya
    qo'llanilgan deb belgilanib qolardi.
    """
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS alembic_version "
        "(version_num VARCHAR(32) NOT NULL, "
        "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
    )
    mavjud = connection.exec_driver_sql("SELECT version_num FROM alembic_version").first()
    if mavjud is None:
        connection.exec_driver_sql(
            "INSERT INTO alembic_version (version_num) VALUES (?)"
            if connection.dialect.paramstyle == "qmark"
            else "INSERT INTO alembic_version (version_num) VALUES (%s)",
            (head,),
        )


#: Eski tahlil moduli qoldirgan jadvallar.
#:
#: Kod 2026-09-03 da, jadval ta'riflari esa 2026-09-04 da o'chirildi.
#: Lekin `create_all` faqat YARATADI — mavjud jadvalni olib tashlamaydi.
#: Ya'ni serverdagi bazada ular ma'lumoti bilan birga qolib ketardi va
#: sayt statistikasi ESKI modulning raqamlarini ko'rsatishda davom
#: etardi.
#:
#: Shuning uchun ular ishga tushishda o'zi olib tashlanadi. Admin
#: uchun qo'shimcha buyruq yo'q: deploy qilinsa — tozalanadi.
ESKI_MODUL_JADVALLARI = (
    "pipeline_events",
    "risk_blocks",
    "daily_stats",
    "market_health_log",
    "audit_reports",
)


def _eski_jadvallarni_olib_tashla(connection) -> list[str]:  # noqa: ANN001
    """Eski modul jadvallarini bazadan chiqaradi.

    Jadval yo'q bo'lsa jim o'tadi — ya'ni ikkinchi marta ishga
    tushirilganda hech narsa qilmaydi.
    """
    mavjud = set(inspect(connection).get_table_names())
    natija = []
    for nom in ESKI_MODUL_JADVALLARI:
        if nom not in mavjud:
            continue
        connection.exec_driver_sql(f'DROP TABLE IF EXISTS "{nom}"')
        natija.append(nom)
    return natija


async def init_models(engine: AsyncEngine) -> None:
    """Jadvallarni yaratadi (dastlabki ishga tushirish uchun).

    Ishlab chiqarishda sxema o'zgarishlari Alembic orqali boshqariladi:
    `alembic upgrade head`. Bu funksiya yangi bazani o'sha `head` bilan
    belgilaydi, shunda keyingi yangilanish to'g'ri joydan davom etadi.
    """
    head = _alembic_head()

    async with engine.begin() as connection:
        olib_tashlandi = await connection.run_sync(_eski_jadvallarni_olib_tashla)
        await connection.run_sync(Base.metadata.create_all)
        if head is not None:
            await connection.run_sync(_stamp_if_fresh, head)

    if olib_tashlandi:
        logger.warning(
            "Eski tahlil moduli jadvallari bazadan chiqarildi: %s",
            ", ".join(olib_tashlandi),
        )
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
