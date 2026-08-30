"""signals.tp1_reached ustuni — qismli yopishni yo'qotmaslik uchun

TP1 ga yetilgani `status` orqali bilinardi, lekin u ISHONCHSIZ:
narx qaytsa status STOPPED bo'ladi, "zaiflashmoqda" belgisi esa uni
WEAKENING ga o'zgartiradi — ikkala holatda ham "TP1 olingan edi"
fakti yo'qoladi. U esa natijani hisoblashda kerak.

Eski yozuvlar uchun qiymat status'dan tiklanadi.

Revision ID: e91b4c7a2d55
Revises: c7d2f5a91e40
Create Date: 2026-08-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e91b4c7a2d55'
down_revision: Union[str, None] = 'c7d2f5a91e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'signals',
        sa.Column('tp1_reached', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    )
    # Eski yozuvlar: TP1/TP2 holatidagilar aniq yetgan.
    op.execute(
        "update signals set tp1_reached = 1 where status in ('tp1_hit', 'tp2_hit')"
    )


def downgrade() -> None:
    op.drop_column('signals', 'tp1_reached')
