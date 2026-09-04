"""zanjir_holatlari jadvali

4-prompt, 3-qism: "Jonli Blok Zanjiri" ekrani uchun. Zanjir sikli
natijasini faqat LOGGA yozardi, ya'ni "hozir qaysi coin qaysi blokda
to'xtadi" degan savolga javob berish uchun serverdagi matn faylni
o'qish kerak edi.

FAQAT OXIRGI HOLAT saqlanadi (`symbol` takrorlanmas). Tarix
saqlansa, jadval har kuni o'nlab qator bilan o'sardi va u hech
qayerda ishlatilmasdi.

MUHIM: bu jadval FAQAT KO'RSATISH uchun. Undan hech narsa modulga
qaytib kirmaydi va signal qaroriga ta'sir qilmaydi.

Revision ID: f8a2d64c091b
Revises: e7b3c9d15a24
Create Date: 2026-09-04

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f8a2d64c091b"
down_revision: str | None = "e7b3c9d15a24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "zanjir_holatlari",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("bloklar_json", sa.Text(), nullable=False),
        sa.Column("toliq", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("uzildi_blokda", sa.String(length=64), nullable=True),
        sa.Column("ishonch", sa.Float(), nullable=False, server_default="0"),
        sa.Column("natija", sa.String(length=32), nullable=False),
        sa.Column("izoh", sa.Text(), nullable=False, server_default=""),
        sa.Column("signal_id", sa.Integer(), nullable=True),
        sa.Column("tekshirilgan", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_zanjir_holatlari_symbol", "zanjir_holatlari", ["symbol"], unique=True)
    op.create_index("ix_zanjir_holatlari_tekshirilgan", "zanjir_holatlari", ["tekshirilgan"])


def downgrade() -> None:
    op.drop_index("ix_zanjir_holatlari_tekshirilgan", table_name="zanjir_holatlari")
    op.drop_index("ix_zanjir_holatlari_symbol", table_name="zanjir_holatlari")
    op.drop_table("zanjir_holatlari")
