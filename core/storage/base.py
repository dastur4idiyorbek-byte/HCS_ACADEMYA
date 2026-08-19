"""SQLAlchemy asosiy sinflari va umumiy ustunlar.

6.2-band: boshida SQLite, keyin PostgreSQL. Shuning uchun:
  - faqat portativ tiplar ishlatiladi (dialektga xos tiplar yo'q)
  - `DateTime(timezone=True)` — vaqt doim UTC saqlanadi
  - Enum'lar matn (VARCHAR) sifatida saqlanadi, native ENUM emas
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

# Nomlash konvensiyasi — Alembic migratsiyalari barqaror bo'lishi uchun
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Har bir yozuv qachon yaratilgani/o'zgargani — audit uchun."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
