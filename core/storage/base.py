"""SQLAlchemy asosiy sinflari va umumiy ustunlar.

6.2-band: boshida SQLite, keyin PostgreSQL. Shuning uchun:
  - faqat portativ tiplar ishlatiladi (dialektga xos tiplar yo'q)
  - `DateTime(timezone=True)` — vaqt doim UTC saqlanadi
  - Enum'lar matn (VARCHAR) sifatida saqlanadi, native ENUM emas
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class UtcDateTime(TypeDecorator):
    """Vaqt DOIM timezone-aware UTC bo'lishini kafolatlaydigan ustun turi.

    Nima uchun kerak: SQLite vaqt zonasini SAQLAMAYDI — `DateTime(timezone=True)`
    bo'lsa ham o'qishda naive `datetime` qaytadi. Naive va aware vaqtni
    taqqoslash `TypeError` beradi, va bundan ham yomoni — mahalliy vaqt
    zonasiga bog'liq mantiq (4.8-band Juma filtri) jimgina noto'g'ri
    ishlashi mumkin.

    Shuning uchun:
      - yozishda: naive vaqt rad etiladi, aware vaqt UTC'ga keltiriladi
      - o'qishda: naive vaqtga UTC belgisi qo'yiladi

    PostgreSQL'ga o'tilganda ham xatti-harakat o'zgarmaydi.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"datetime kutilgan, {type(value).__name__} keldi")
        if value.tzinfo is None:
            raise ValueError(
                "Timezone-siz (naive) vaqtni saqlash taqiqlangan — "
                "`core.utils.time_utils.utc_now()` dan foydalaning"
            )
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            # SQLite vaqt zonasini saqlamaydi — biz doim UTC yozamiz,
            # shuning uchun belgini qaytarish xavfsiz.
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

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
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
