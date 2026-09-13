"""Kuzatuv paneli: bosqich darvozasi olib tashlandi

NIMA UCHUN. 12-sentyabrda panelga ikkinchi darvoza qo'shilgan edi:
narx Fibonacci qaytish zonasining tepasida bo'lsa, coin "yurib
bo'lgan" deb ro'yxatdan chiqarilardi.

13-sentyabrda loyiha egasi natijani tekshirdi: darvoza
qo'shilishidan OLDIN ro'yxatda turgan 20 coindan 17 tasi haqiqatan
yuqoriga yurgan. Ya'ni panel to'g'ri ishlagan, darvoza esa yaxshi
nomzodlarni chiqarib tashlagan.

Shuning uchun darvoza butunlay olib tashlandi va u bilan birga
bazadagi ustunlari ham.

OLDINGA QARAB YURILADI, migratsiya O'CHIRILMAYDI. `b4c8d21a9e37`
ustunlarni qo'shgan va undan keyin boshqa migratsiya yozilgan
(`c9e15b3f8a42`). Eski faylni o'chirish zanjirni uzardi va
bazasi allaqachon yangilangan muhitlarni buzardi.

`narx` ustuni QOLADI: u bosqich uchun emas, ekranda joriy narxni
ko'rsatish uchun ishlatiladi (promptning 5.3-qism talabi).

Revision ID: d1a4f76b3e08
Revises: c9e15b3f8a42
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d1a4f76b3e08"
down_revision = "c9e15b3f8a42"
branch_labels = None
depends_on = None

USTUNLAR = (
    "bosqich",
    "bosqich_izoh",
    "bosqich_ulush",
    "impuls_past",
    "impuls_yuqori",
)


def upgrade() -> None:
    with op.batch_alter_table("kuzatuv_holatlari") as batch:
        for ustun in USTUNLAR:
            batch.drop_column(ustun)


def downgrade() -> None:
    with op.batch_alter_table("kuzatuv_holatlari") as batch:
        batch.add_column(
            sa.Column(
                "bosqich",
                sa.String(16),
                server_default="nomalum",
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column("bosqich_izoh", sa.Text(), server_default="", nullable=False)
        )
        batch.add_column(sa.Column("bosqich_ulush", sa.Float(), nullable=True))
        batch.add_column(sa.Column("impuls_past", sa.Float(), nullable=True))
        batch.add_column(sa.Column("impuls_yuqori", sa.Float(), nullable=True))
