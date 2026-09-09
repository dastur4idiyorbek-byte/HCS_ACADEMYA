"""Bosh sahifa: vidjet tanlovi va avtomatik post manbasi

IKKI QISM.

1. `homepage_posts` ga uchta ustun: post qayerdan kelgani
   (`source_kind`), qaysi yozuv haqida (`source_id`) va tugma qayerga
   olib borishi (`link`).

   `source_kind` + `source_id` juftligi TAKRORLANMAYDI. Ansiz admin
   darsni har tahrirlaganda oqimda yangi post paydo bo'lardi. Bu
   shart bazada turadi, kodda emas: kod unutishi mumkin.

   Mavjud postlar `qolda` deb belgilanadi va ularning `source_id` si
   NULL bo'lgani uchun cheklovga tushmaydi (SQLite da NULL hech
   narsaga teng emas, shuning uchun ular istalgancha bo'lishi mumkin).

2. `user_widgets` — kimning bosh sahifasida qaysi vidjet turishi.
   Bazada, brauzerda emas: odam telefonda ham, kompyuterda ham
   kiradi va tanlovi ikkalasida bir xil bo'lishi kerak.

Revision ID: b7e392a5c184
Revises: a4c81f2b7d63
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e392a5c184"
down_revision: str | None = "a4c81f2b7d63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "homepage_posts",
        sa.Column(
            "source_kind",
            sa.String(16),
            nullable=False,
            server_default="qolda",
        ),
    )
    op.add_column("homepage_posts", sa.Column("source_id", sa.Integer(), nullable=True))
    op.add_column("homepage_posts", sa.Column("link", sa.String(256), nullable=True))
    # NEGA CHEKLOV EMAS, UNIQUE INDEKS. SQLite mavjud jadvalga
    # cheklov qo'sha olmaydi — jadvalni nusxalab qayta qurish kerak
    # bo'lardi, postlar esa allaqachon yozilgan. Indeks aynan shu
    # kafolatni beradi va jadvalga tegmaydi.
    op.create_index(
        "uq_post_manba", "homepage_posts", ["source_kind", "source_id"], unique=True
    )

    op.create_table(
        "user_widgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("widget", sa.String(32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "widget", name="uq_widget_user_widget"),
    )
    op.create_index("ix_user_widgets_user_id", "user_widgets", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_widgets_user_id", table_name="user_widgets")
    op.drop_table("user_widgets")
    op.drop_index("uq_post_manba", table_name="homepage_posts")
    op.drop_column("homepage_posts", "link")
    op.drop_column("homepage_posts", "source_id")
    op.drop_column("homepage_posts", "source_kind")
