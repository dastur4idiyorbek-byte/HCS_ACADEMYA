"""market_health_log: struktura kengligi va QT davri ustunlari

Bozor Salomatligi Indeksining ASOSIY omili o'zgardi: ilgari eng og'ir
omillar BTC Dominance (20) va EMA kengligi (25) edi, endi birinchi
o'rinda halol ro'yxatning SMC STRUKTURA kengligi turadi (30).

Jadvalda esa har bir omil uchun alohida ustun bor. Yangi ikki omil
(`halal_structure_breadth` va `quarterly_phase`) uchun joy bo'lmasa,
ular jimgina `detail` matnida qolib ketardi — ya'ni saytdagi
Salomatlik sahifasi ASOSIY omilni ko'rsata olmasdi.

Revision ID: b4e1a7c30d92
Revises: 7b21e4c05d18
Create Date: 2026-08-29 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b4e1a7c30d92'
down_revision: Union[str, None] = '7b21e4c05d18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('market_health_log', schema=None) as batch_op:
        batch_op.add_column(sa.Column('structure_breadth_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('quarterly_phase_score', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('market_health_log', schema=None) as batch_op:
        batch_op.drop_column('quarterly_phase_score')
        batch_op.drop_column('structure_breadth_score')
