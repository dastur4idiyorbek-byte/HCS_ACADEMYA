import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# Modellar import qilinishi SHART — aks holda `autogenerate` bo'sh
# migratsiya yasaydi (jadvallar `Base.metadata` ga ro'yxatdan o'tmaydi).
from core.storage import models  # noqa: E402, F401
from core.storage.base import Base  # noqa: E402
from core.storage.database import (  # noqa: E402
    ensure_sqlite_directory,
    resolve_database_url,
)

target_metadata = Base.metadata


def _render_item(type_, obj, autogen_context):  # noqa: ANN001, ANN202
    """Maxsus tiplarni standart SQLAlchemy tipi sifatida yozadi.

    `UtcDateTime` — `DateTime` ustidagi `TypeDecorator`: bazada u oddiy
    DateTime ustuni. Agar migratsiya `core.storage.base.UtcDateTime` deb
    yozsa, u ILOVA KODIGA bog'lanib qoladi va o'sha klass ko'chirilsa yoki
    o'zgartirilsa eski migratsiyalar ishlamay qoladi.

    Migratsiyalar muzlatilgan tarix bo'lishi kerak — shuning uchun ular
    faqat `sqlalchemy` ga tayanadi.
    """
    # `sa` shablonda allaqachon import qilingan — qayta qo'shilmaydi.
    if type_ == "type" and obj.__class__.__name__ == "UtcDateTime":
        return "sa.DateTime(timezone=True)"
    return False


def _database_url() -> str:
    """`DATABASE_URL` muhit o'zgaruvchisidan (yoki standart SQLite).

    URL `alembic.ini` da saqlanmaydi: PostgreSQL paroli git ga tushmasligi
    kerak. `.env` fayli ham o'qiladi — README shuni yaratishni aytadi.
    """
    from bot.hosting import apply_platform_defaults
    from bot.settings import load_env_file

    load_env_file()
    # Doimiy disk ulangan bo'lsa, migratsiya ham O'SHA bazaga tegishi kerak —
    # aks holda bot bilan har xil faylga ishlaymiz.
    apply_platform_defaults()

    url = resolve_database_url()
    # SQLite papkasi bo'lmasa "unable to open database file" chiqadi. Alembic
    # o'z engine'ini quradi, shuning uchun buni shu yerda ta'minlaymiz.
    ensure_sqlite_directory(url)
    return url

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        render_item=_render_item,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # `render_as_batch` — SQLite uchun SHART: u `ALTER TABLE` ni deyarli
    # qo'llab-quvvatlamaydi, shuning uchun alembic jadvalni qayta quradi.
    # PostgreSQL da bu bayroq zarar qilmaydi.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        render_item=_render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    sozlama = config.get_section(config.config_ini_section, {}) or {}
    sozlama["sqlalchemy.url"] = _database_url()

    connectable = async_engine_from_config(
        sozlama,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
