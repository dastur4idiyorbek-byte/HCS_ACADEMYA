"""content.video_path — saytga yuklangan video fayl nomi

Nima uchun kerak: video Telegramda `file_id` sifatida yotardi va uni
saytda ko'rsatib bo'lmasdi. Telegram Bot API `getFile` orqali bot
faqat 20 MB gacha faylni yuklab olishi mumkin, darslar esa odatda
bundan katta.

Ustunda TO'LIQ YO'L emas, faqat FAYL NOMI saqlanadi. Jild baza fayli
yonidan hisoblanadi (`web/src/lib/media.ts`), ya'ni doimiy disk
boshqa joyga ulansa ham yozuvlar buzilmaydi.

Revision ID: 7b21e4c05d18
Revises: 3f599fdf0f4f
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7b21e4c05d18"
down_revision: Union[str, None] = "3f599fdf0f4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("content", sa.Column("video_path", sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column("content", "video_path")
