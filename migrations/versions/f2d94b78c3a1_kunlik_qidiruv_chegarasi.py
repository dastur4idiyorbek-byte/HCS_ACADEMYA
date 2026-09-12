"""Foydalanuvchining kunlik coin qidiruvi chegarasi.

NIMA UCHUN SANA USTUNI BOR, TOZALOVCHI VAZIFA EMAS. "Har kuni
00:00 da nolga tushirish" vazifasi yiqilsa yoki bot o'chirilgan
bo'lsa, chegara mangu qolib ketardi. Sana bilan esa hech narsa
yugurishi shart emas: yangi kun — yangi qator.

Revision ID: f2d94b78c3a1
Revises: e8a3c15f6b92
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "f2d94b78c3a1"
down_revision: str | None = "e8a3c15f6b92"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "kunlik_qidiruv",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sana", sa.String(length=10), nullable=False),
        sa.Column("soni", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "sana", name="uq_kunlik_qidiruv"),
    )
    op.create_index(
        op.f("ix_kunlik_qidiruv_user_id"), "kunlik_qidiruv", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_kunlik_qidiruv_sana"), "kunlik_qidiruv", ["sana"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_kunlik_qidiruv_sana"), table_name="kunlik_qidiruv")
    op.drop_index(op.f("ix_kunlik_qidiruv_user_id"), table_name="kunlik_qidiruv")
    op.drop_table("kunlik_qidiruv")
