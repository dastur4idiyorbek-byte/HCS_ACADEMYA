"""TP soni qat'iy emas: tp2 ixtiyoriy, tp3 qo'shildi

TP har doim aynan ikkita degan qoida SXEMAGA yozib qo'yilgan edi:
`tp2` NOT NULL turardi. Bozor esa unday emas — toza ko'tarilishda
ustda bitta ham qarshilik bo'lmasligi, keng diapazonda esa uchtasi
bo'lishi mumkin.

`reached_tps` — nechta TP ga yetilgan. Eski `tp1_reached` bayrog'i
saqlanadi: u "kamida bittasi" degan savolga javob beradi va
hisobotlar unga tayanadi. Migratsiya uni yangi ustunga ko'chiradi.

Revision ID: a2f9d43c6b17
Revises: f3a7c15d8e29
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a2f9d43c6b17'
down_revision: Union[str, None] = 'f3a7c15d8e29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('signals', sa.Column('tp3', sa.Float(), nullable=True))
    op.add_column(
        'signals',
        sa.Column('reached_tps', sa.Integer(), nullable=False, server_default='0'),
    )
    with op.batch_alter_table('signals') as batch:
        batch.alter_column('tp2', existing_type=sa.Float(), nullable=True)

    # Eski yozuvlar: TP1 olingan bo'lsa kamida bittasiga yetilgan.
    op.execute('update signals set reached_tps = 1 where tp1_reached = 1')
    op.execute("update signals set reached_tps = 2 where status = 'tp2_hit'")


def downgrade() -> None:
    op.execute('update signals set tp2 = tp1 where tp2 is null')
    with op.batch_alter_table('signals') as batch:
        batch.alter_column('tp2', existing_type=sa.Float(), nullable=False)
    op.drop_column('signals', 'reached_tps')
    op.drop_column('signals', 'tp3')
