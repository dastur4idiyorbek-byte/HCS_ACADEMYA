"""risk_blocks ball ustuni

Nomzod olgan ball saqlanmasdi. `RejectedCandidate` uni allaqachon
tashib yurardi, lekin `record_many()` yozishda tashlab ketardi — ya'ni
ma'lumot bor edi, faqat hech qayerga bormasdi.

Oqibati: sokinlik dashboardi "Ball chegaradan past" deb yozardi, lekin
QANCHALIK past ekanini ko'rsatolmasdi. Shu ko'rlik sababli chegara
erishib bo'lmas darajada baland qo'yilgani 48 soat davomida sezilmadi.

Revision ID: a1c4f7d92b03
Revises: 9adb13e4b0ec
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1c4f7d92b03'
down_revision: Union[str, None] = '9adb13e4b0ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('risk_blocks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('score', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('risk_blocks', schema=None) as batch_op:
        batch_op.drop_column('score')
