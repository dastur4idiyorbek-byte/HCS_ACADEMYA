"""market_health_log.quarterly_phase — QT davri harfi

Davr endi SOATDAN emas, sham strukturasidan aniqlanadi. Sayt uni
ko'rsatishi kerak, lekin BALLDAN tiklab bo'lmaydi: "aniqlanmadi"
neytral 0.5 ball oladi va bu D davrining balli bilan bir xil.

Shuning uchun harfning o'zi saqlanadi. Eski yozuvlarda `NULL` qoladi —
ular soat asosida hisoblangan edi va endi ma'nosini yo'qotdi.

Revision ID: f3a7c15d8e29
Revises: e91b4c7a2d55
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f3a7c15d8e29'
down_revision: Union[str, None] = 'e91b4c7a2d55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'market_health_log',
        sa.Column('quarterly_phase', sa.String(length=1), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('market_health_log', 'quarterly_phase')
