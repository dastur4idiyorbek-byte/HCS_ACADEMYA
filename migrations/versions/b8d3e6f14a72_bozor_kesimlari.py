"""bozor_kesimlari jadvali

Sayt uchun haftalik/kunlik qarash: BTC.D, USDT.D, TOTAL, TOTAL2,
TOTAL3, OTHERS. Bu qiymatlar birjadan sham sifatida kelmaydi —
manba faqat hozirgi holatni beradi, yo'nalish esa tarixsiz
aniqlanmaydi. Shuning uchun har kuni yozib boriladi.

SIGNALGA BOG'LANMAYDI (loyiha egasining sharti).

Revision ID: b8d3e6f14a72
Revises: a2f9d43c6b17
Create Date: 2026-09-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8d3e6f14a72"
down_revision: str | None = "a2f9d43c6b17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bozor_kesimlari",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kod", sa.String(length=16), nullable=False),
        sa.Column("qiymat", sa.Float(), nullable=False),
        sa.Column("olingan", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bozor_kesim_kod_vaqt", "bozor_kesimlari", ["kod", "olingan"]
    )

    op.create_table(
        "bozor_korinishlari",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("turi", sa.String(length=16), nullable=False),
        sa.Column("sana", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asboblar_json", sa.Text(), nullable=False),
        sa.Column("xulosa", sa.Text(), nullable=False),
        sa.Column("kutilma", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bozor_korinish_turi_sana", "bozor_korinishlari", ["turi", "sana"]
    )


def downgrade() -> None:
    op.drop_index("ix_bozor_korinish_turi_sana", table_name="bozor_korinishlari")
    op.drop_table("bozor_korinishlari")
    op.drop_index("ix_bozor_kesim_kod_vaqt", table_name="bozor_kesimlari")
    op.drop_table("bozor_kesimlari")
