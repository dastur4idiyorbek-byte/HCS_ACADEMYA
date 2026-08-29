"""pipeline_events jadvali — jonli tahlil monitori

Admin tizimning orqa fonda nima qilayotganini ko'zi bilan ko'rishi
uchun: qaysi coin qaysi bosqichda, nima uchun to'xtadi.

Bu DOIMIY ARXIV EMAS — yozuvlar bir necha soatdan keyin tozalanadi.
Doimiy statistika `risk_blocks` va Signal Xotirasi modulida qoladi.

Revision ID: c7d2f5a91e40
Revises: b4e1a7c30d92
Create Date: 2026-08-29 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7d2f5a91e40'
down_revision: Union[str, None] = 'b4e1a7c30d92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pipeline_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('stage', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=8), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('cycle_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pipeline_events_symbol', 'pipeline_events', ['symbol'])
    op.create_index('ix_pipeline_events_stage', 'pipeline_events', ['stage'])
    op.create_index('ix_pipeline_events_cycle_at', 'pipeline_events', ['cycle_at'])
    op.create_index('ix_pipeline_events_cycle', 'pipeline_events', ['cycle_at', 'symbol'])


def downgrade() -> None:
    op.drop_index('ix_pipeline_events_cycle', table_name='pipeline_events')
    op.drop_index('ix_pipeline_events_cycle_at', table_name='pipeline_events')
    op.drop_index('ix_pipeline_events_stage', table_name='pipeline_events')
    op.drop_index('ix_pipeline_events_symbol', table_name='pipeline_events')
    op.drop_table('pipeline_events')
