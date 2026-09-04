"""homepage_posts jadvali + signalga ikkita grafik rasmi

4-prompt, 1-qism: bosh sahifa statik matndan XRONOLOGIK OQIMGA
aylanadi (Telegram kanali uslubida). Postlar shu jadvalda.

Tanishtiruv, diniy asos va ijtimoiy tarmoqlar bu jadvalga TUSHMAYDI —
ular oqimning tepasida, kodda qoladi. Sabab: diniy iqtibos joyi olim
tasdiqlaguncha placeholder bo'lib turishi shart, uni oddiy postga
aylantirsak admin tasodifan o'chirib yuborishi mumkin edi.

4-prompt, 4-qism: signalga `entry_chart_image` va `result_chart_image`
— admin TradingView'da chizib, qo'lda yuklaydigan rasmlar.

Revision ID: e7b3c9d15a24
Revises: d5c9b21e73f8
Create Date: 2026-09-04

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7b3c9d15a24"
down_revision: str | None = "d5c9b21e73f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "homepage_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=16), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("media_url", sa.String(length=256), nullable=True),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_homepage_posts_admin_id", "homepage_posts", ["admin_id"])
    op.create_index("ix_homepage_posts_created", "homepage_posts", ["created_at"])

    with op.batch_alter_table("signals") as batch:
        batch.add_column(sa.Column("entry_chart_image", sa.String(length=256), nullable=True))
        batch.add_column(sa.Column("result_chart_image", sa.String(length=256), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("signals") as batch:
        batch.drop_column("result_chart_image")
        batch.drop_column("entry_chart_image")

    op.drop_index("ix_homepage_posts_created", table_name="homepage_posts")
    op.drop_index("ix_homepage_posts_admin_id", table_name="homepage_posts")
    op.drop_table("homepage_posts")
