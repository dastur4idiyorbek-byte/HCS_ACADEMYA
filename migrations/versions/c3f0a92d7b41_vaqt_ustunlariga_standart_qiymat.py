"""Vaqt ustunlariga server standart qiymati qaytariladi

MUAMMO. Sxema ikki yo'l bilan qurilishi mumkin: `create_all` (bot
birinchi marta ishga tushganda) va Alembic migratsiyasi (serverda
`alembic upgrade head`). Modelda `created_at`/`updated_at` ustunlari
`server_default=func.now()` bilan e'lon qilingan, keyinroq yozilgan
migratsiyalarda esa bu qiymat tushib qolgan.

Natijasi jimgina yotgan xato edi: SQLAlchemy bu ikki ustunni INSERT
ga umuman qo'shmaydi — qiymatni BAZA qo'yadi deb hisoblaydi. Baza
migratsiya orqali qurilgan bo'lsa esa u yerda standart qiymat yo'q
va yozuv `NOT NULL constraint failed: <jadval>.created_at` bilan
yiqiladi. Ya'ni bozor kesimini yozish, bosh sahifa postini yaratish,
pozitsiyani yopish — hammasi shu jadvallarda to'xtardi.

Bu migratsiya olti jadvalning `created_at`/`updated_at` ustuniga
`DEFAULT CURRENT_TIMESTAMP` ni qo'yadi va shu bilan ikkala yo'lni
bir xil sxemaga olib keladi.

NEGA `recreate="always"`. SQLite mavjud ustunning standart qiymatini
o'zgartira olmaydi — jadvalni nusxalab qayta qurishdan boshqa yo'l
yo'q. `batch_alter_table` aynan shuni qiladi: ma'lumot ko'chiriladi,
indekslar tiklanadi.

Revision ID: c3f0a92d7b41
Revises: b7e392a5c184
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3f0a92d7b41"
down_revision: str | None = "b7e392a5c184"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: `created_at`/`updated_at` ustuni standart qiymatsiz qolgan jadvallar.
JADVALLAR = (
    "bozor_kesimlari",
    "bozor_korinishlari",
    "capital_blocks",
    "homepage_posts",
    "position_exits",
    "zanjir_holatlari",
)

USTUNLAR = ("created_at", "updated_at")


def _qiymat(server_default) -> None:  # noqa: ANN001
    for jadval in JADVALLAR:
        with op.batch_alter_table(jadval, schema=None, recreate="always") as batch_op:
            for ustun in USTUNLAR:
                batch_op.alter_column(
                    ustun,
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False,
                    server_default=server_default,
                )


def upgrade() -> None:
    _qiymat(sa.text("CURRENT_TIMESTAMP"))


def downgrade() -> None:
    _qiymat(None)
