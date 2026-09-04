"""capital_blocks va position_exits jadvallari

3-prompt: Portfel va Xavf Boshqaruvi moduli.

`capital_blocks` — balansning bo'laklari va ularning band qismi.
Bot qayta ishga tushganda "bu bo'lak band" degan bilim yo'qolmasligi
uchun kerak: aks holda bir bo'lakka ikkinchi pozitsiya ochilib, xavf
ikki barobar bo'lardi.

`position_exits` — pozitsiyaning har bir yopilgan QISMI (TP bosqichi
yoki Stop). Bosqichlar boshqa kunlarga tushishi mumkin, shuning uchun
"bugungi natija" faqat shu darajadagi yozuvdan to'g'ri chiqadi.

`pnl_records` ATAYLAB yo'q: kunlik/haftalik/oylik raqamlar shu
yozuvlardan har safar qayta hisoblanadi. Yig'ilgan raqamni alohida
jadvalda saqlash ikkinchi haqiqat manbaini yaratardi.

Revision ID: d5c9b21e73f8
Revises: a1f4e07c9b62
Create Date: 2026-09-04

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5c9b21e73f8"
down_revision: str | None = "a1f4e07c9b62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capital_blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("raqam", sa.Integer(), nullable=False),
        sa.Column("hajm_usd", sa.Float(), nullable=False),
        sa.Column("band_kapital_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("band_xavf_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "raqam", name="user_bolak"),
    )
    op.create_index("ix_capital_blocks_user_id", "capital_blocks", ["user_id"])

    op.create_table(
        "position_exits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("bosqich", sa.Integer(), nullable=False),
        sa.Column("narx", sa.Float(), nullable=False),
        sa.Column("ulush_pct", sa.Float(), nullable=False),
        sa.Column("miqdor_usd", sa.Float(), nullable=False),
        sa.Column("natija_usd", sa.Float(), nullable=False),
        sa.Column("sabab", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("yopilgan_vaqt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["position_id"], ["user_positions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("position_id", "bosqich", name="pozitsiya_bosqich"),
    )
    op.create_index("ix_position_exits_position_id", "position_exits", ["position_id"])
    op.create_index("ix_position_exits_yopilgan_vaqt", "position_exits", ["yopilgan_vaqt"])
    op.create_index(
        "ix_position_exits_vaqt", "position_exits", ["position_id", "yopilgan_vaqt"]
    )


def downgrade() -> None:
    op.drop_index("ix_position_exits_vaqt", table_name="position_exits")
    op.drop_index("ix_position_exits_yopilgan_vaqt", table_name="position_exits")
    op.drop_index("ix_position_exits_position_id", table_name="position_exits")
    op.drop_table("position_exits")
    op.drop_index("ix_capital_blocks_user_id", table_name="capital_blocks")
    op.drop_table("capital_blocks")
