"""Kuzatuv paneli — Top 20 uchun jonli bozor yig'masi.

FAQAT YIG'MA SAQLANADI. Stakan va savdo lentasi bu yerga
yozilmaydi: ular sekundiga o'nlab marta o'zgaradi va brauzer
ularni o'zi, to'g'ridan-to'g'ri birjadan oladi. Bu yerda esa
vaqt ichida to'planadigan narsa turadi — xarid bosimi va yirik
savdolar, ularni brauzer bera olmaydi.

Revision ID: e8a3c15f6b92
Revises: d5b71e4c9a28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "e8a3c15f6b92"
down_revision: str | None = "d5b71e4c9a28"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "kuzatuv_bozor",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("narx", sa.Float(), nullable=True),
        sa.Column("xarid_bosimi", sa.Float(), nullable=True),
        sa.Column("hajm_usd", sa.Float(), nullable=True),
        sa.Column("yirik_savdo", sa.Integer(), server_default="0", nullable=False),
        sa.Column("yiriklar_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("market_cap", sa.Float(), nullable=True),
        sa.Column("hajm_24s", sa.Float(), nullable=True),
        sa.Column("ozgarish_1s", sa.Float(), nullable=True),
        sa.Column("ozgarish_24s", sa.Float(), nullable=True),
        sa.Column("ozgarish_7k", sa.Float(), nullable=True),
        sa.Column("yangilangan", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_kuzatuv_bozor_symbol"), "kuzatuv_bozor", ["symbol"], unique=True
    )
    op.create_index(
        op.f("ix_kuzatuv_bozor_yangilangan"),
        "kuzatuv_bozor",
        ["yangilangan"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_kuzatuv_bozor_yangilangan"), table_name="kuzatuv_bozor")
    op.drop_index(op.f("ix_kuzatuv_bozor_symbol"), table_name="kuzatuv_bozor")
    op.drop_table("kuzatuv_bozor")
