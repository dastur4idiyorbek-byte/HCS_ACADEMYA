"""Akademiya: maqola maydonlari va o'qish holati

Uchta yangi ustun `content` jadvaliga va bitta yangi jadval.

NEGA KERAK. Akademiya sahifasida uchta narsa ko'rsatiladi va ular
uchun bazada joy yo'q edi:

  1. Maqolalar ("Bilimlar") — `body` va `category`
  2. Video uzunligi / o'qish vaqti — `duration_seconds`
  3. "Davom ettirish" — kim qayerda to'xtagani

Uchala ustun ham NULL bo'lishi mumkin: mavjud yozuvlarda ular yo'q
va ularni to'ldirish shart emas. Video uchun `body` bo'sh qoladi,
maqola uchun `video_path` bo'sh qoladi.

Revision ID: a4c81f2b7d63
Revises: f8a2d64c091b
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4c81f2b7d63"
down_revision: str | None = "f8a2d64c091b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("content", sa.Column("body", sa.Text(), nullable=True))
    op.add_column(
        "content", sa.Column("duration_seconds", sa.Integer(), nullable=True)
    )
    op.add_column("content", sa.Column("category", sa.String(64), nullable=True))

    op.create_table(
        "content_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Bitta foydalanuvchi bitta darsda BIR MARTA turadi. Ansiz
        # tarix yig'ilib, "oxirgisi qaysi?" degan savol tug'ilardi.
        sa.UniqueConstraint("user_id", "content_id", name="uq_progress_user_content"),
    )
    op.create_index(
        "ix_content_progress_user_id", "content_progress", ["user_id"]
    )
    op.create_index(
        "ix_content_progress_content_id", "content_progress", ["content_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_content_progress_content_id", table_name="content_progress")
    op.drop_index("ix_content_progress_user_id", table_name="content_progress")
    op.drop_table("content_progress")
    op.drop_column("content", "category")
    op.drop_column("content", "duration_seconds")
    op.drop_column("content", "body")
