"""Eski tahlil moduli jadvallari butunlay olib tashlandi.

2026-09-03 da eski modulning KODI o'chirilgan edi. Lekin uning
jadvallari bazada ma'lumoti bilan birga qolib ketgan edi va sayt
statistikasi o'sha eski raqamlarni ko'rsatishda davom etardi.

Bu migratsiya beshtasini ham butunlay olib tashlaydi:

    pipeline_events     — Jonli Oshxona voronkasi
    risk_blocks         — Risk Engine rad etishlari
    daily_stats         — kunlik statistika
    market_health_log   — Bozor Salomatligi jurnali
    audit_reports       — haftalik audit hisobotlari

QAYTARIB BO'LMAYDI. `downgrade()` jadvallarni BO'SH holda tiklaydi
— ma'lumot qaytmaydi, chunki u yangi modulga tegishli emas va
qaytarilishi ham kerak emas.

Revision ID: a1f4e07c9b62
Revises: b8d3e6f14a72
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "a1f4e07c9b62"
down_revision: str | None = "b8d3e6f14a72"
branch_labels: str | None = None
depends_on: str | None = None

#: Tartib muhim emas — bular orasida tashqi kalit yo'q.
JADVALLAR = (
    "pipeline_events",
    "risk_blocks",
    "daily_stats",
    "market_health_log",
    "audit_reports",
)


def upgrade() -> None:
    mavjud = set(sa.inspect(op.get_bind()).get_table_names())
    for nom in JADVALLAR:
        if nom in mavjud:
            op.drop_table(nom)


def downgrade() -> None:
    """Jadvallarni BO'SH holda tiklaydi.

    Ustunlar ataylab eng sodda ko'rinishda: bu jadvallar boshqa
    hech qachon ishlatilmaydi va ularning to'liq sxemasini
    tiklashning ma'nosi yo'q. Downgrade faqat migratsiya zanjiri
    uzilmasligi uchun bor.
    """
    for nom in JADVALLAR:
        op.create_table(
            nom,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
