"""Kuzatuv paneli — ANIQ NARX darajalari (5.3-qism).

Prompt uch marta "ANIQ NARX" so'raydi: BOS qaysi darajada
tasdiqlangan, zona qayerda, Liquidity Sweep qaysi darajada
bo'lgan. Blok tekshiruvlarining izohida bu raqamlar YO'Q — ular
faqat "bor/yo'q" deydi, chunki bloklar ball hisoblash uchun
yozilgan, ko'rsatish uchun emas.

Zona oralig'i allaqachon saqlanardi; BOS va sweep darajalari
shu migratsiyada qo'shiladi.

Revision ID: c9e15b3f8a42
Revises: b4c8d21a9e37
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "c9e15b3f8a42"
down_revision: str | None = "b4c8d21a9e37"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("kuzatuv_holatlari", sa.Column("bos_narx", sa.Float(), nullable=True))
    op.add_column("kuzatuv_holatlari", sa.Column("sweep_narx", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("kuzatuv_holatlari", "sweep_narx")
    op.drop_column("kuzatuv_holatlari", "bos_narx")
