"""Kuzatuv paneli jadvallari — 80 coin holati va skan boshqaruvi.

9-prompt (`9_prompt_yakuniy_kuzatuv_moduli.md`). Ikki jadval:

    kuzatuv_holatlari — har coinning oxirgi holati (symbol
                        takrorlanmas, tarix saqlanmaydi)
    kuzatuv_skani     — bitta qator: admin skan so'radimi, skan
                        qaysi holatda

NIMA UCHUN `zanjir_holatlari` GA QO'SHILMADI. Ular o'xshash
ko'rinadi, lekin ikki xil savolga javob beradi ("signal chiqdimi?"
va "diqqatga molikmi?"). Bitta jadvalda birlashtirilsa, biri
o'zgarganda ikkinchisi jimgina buzilardi.

Revision ID: d5b71e4c9a28
Revises: c3f0a92d7b41
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "d5b71e4c9a28"
down_revision: str | None = "c3f0a92d7b41"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "kuzatuv_holatlari",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("yonalish", sa.String(length=32), nullable=False),
        sa.Column("yonalish_izoh", sa.Text(), server_default="", nullable=False),
        sa.Column("otdi", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("diqqat", sa.Integer(), server_default="0", nullable=False),
        sa.Column("segmentlar_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("bloklar_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("zona_darajasi", sa.String(length=16), server_default="yoq", nullable=False),
        sa.Column("zona_past", sa.Float(), nullable=True),
        sa.Column("zona_yuqori", sa.Float(), nullable=True),
        sa.Column("ogohlantirish", sa.Text(), nullable=True),
        sa.Column("nisbiy_kuch", sa.Float(), nullable=True),
        sa.Column(
            "royxat",
            sa.String(length=24),
            server_default="royxatdan_tashqari",
            nullable=False,
        ),
        sa.Column("orin", sa.Integer(), nullable=True),
        sa.Column("tekshirilgan", sa.DateTime(timezone=True), nullable=False),
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
        op.f("ix_kuzatuv_holatlari_symbol"),
        "kuzatuv_holatlari",
        ["symbol"],
        unique=True,
    )
    op.create_index(
        op.f("ix_kuzatuv_holatlari_tekshirilgan"),
        "kuzatuv_holatlari",
        ["tekshirilgan"],
        unique=False,
    )

    op.create_table(
        "kuzatuv_skani",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sorov", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("holat", sa.String(length=16), server_default="bosh", nullable=False),
        sa.Column("tekshirildi", sa.Integer(), server_default="0", nullable=False),
        sa.Column("otdi", sa.Integer(), server_default="0", nullable=False),
        sa.Column("izoh", sa.Text(), server_default="", nullable=False),
        sa.Column("boshlandi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tugadi", sa.DateTime(timezone=True), nullable=True),
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


def downgrade() -> None:
    op.drop_table("kuzatuv_skani")
    op.drop_index(op.f("ix_kuzatuv_holatlari_tekshirilgan"), table_name="kuzatuv_holatlari")
    op.drop_index(op.f("ix_kuzatuv_holatlari_symbol"), table_name="kuzatuv_holatlari")
    op.drop_table("kuzatuv_holatlari")
