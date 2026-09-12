"""Kuzatuv paneli — IKKINCHI DARVOZA: narx harakatning qayerida.

NIMA UCHUN QO'SHILDI. Filtr faqat yo'nalishni tekshirardi, va
HH/HL ketma-ketligi coin ALLAQACHON YURGANDA ham to'g'ri bo'ladi.
Natijada Top 20 ga harakatini tugatgan coinlar chiqardi. Loyiha
egasi buni ekranda ko'rdi.

`narx` ustuni ham shu sababdan: saytda zona joyi (arzon/qimmat)
hisoblanardi, lekin joriy narx saqlanmagani uchun zona MARKAZI
ishlatilgan va natija HAR DOIM "o'rtada" chiqardi.

Revision ID: b4c8d21a9e37
Revises: a7f3e29d5c84
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "b4c8d21a9e37"
down_revision: str | None = "a7f3e29d5c84"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "kuzatuv_holatlari",
        sa.Column("bosqich", sa.String(length=16), server_default="nomalum", nullable=False),
    )
    op.add_column(
        "kuzatuv_holatlari",
        sa.Column("bosqich_izoh", sa.Text(), server_default="", nullable=False),
    )
    for nom in ("bosqich_ulush", "impuls_past", "impuls_yuqori", "narx"):
        op.add_column("kuzatuv_holatlari", sa.Column(nom, sa.Float(), nullable=True))


def downgrade() -> None:
    for nom in ("narx", "impuls_yuqori", "impuls_past", "bosqich_ulush"):
        op.drop_column("kuzatuv_holatlari", nom)
    op.drop_column("kuzatuv_holatlari", "bosqich_izoh")
    op.drop_column("kuzatuv_holatlari", "bosqich")
