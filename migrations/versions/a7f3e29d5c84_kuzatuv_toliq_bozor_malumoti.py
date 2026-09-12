"""Kuzatuv paneli — CoinGecko ning TO'LIQ asosiy ma'lumoti.

Ilgari beshta maydon olinardi (narx, kapitalizatsiya, hajm va
uchta o'zgarish), qolgani esa o'sha javobda kelib, bekorga tashlab
yuborilardi. Loyiha egasi buni sezdi: "ma'lumotlar yuzaki".

Qo'shimcha so'rov KERAK EMAS — hammasi `/coins/markets` ning
o'sha javobida bor.

Likvidlik ko'rsatkichi (promptning talabi) alohida ustun EMAS:
u hajm / kapitalizatsiya, ya'ni ikkita mavjud ustundan
hisoblanadi. Uchinchi nusxa saqlash — ular ajralib ketishining
eng oson yo'li.

Revision ID: a7f3e29d5c84
Revises: f2d94b78c3a1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "a7f3e29d5c84"
down_revision: str | None = "f2d94b78c3a1"
branch_labels: str | None = None
depends_on: str | None = None

USTUNLAR = (
    ("orin_cg", sa.Integer()),
    ("fdv", sa.Float()),
    ("muomalada", sa.Float()),
    ("jami_token", sa.Float()),
    ("eng_kop_token", sa.Float()),
    ("ath", sa.Float()),
    ("ath_farq", sa.Float()),
    ("atl", sa.Float()),
    ("atl_farq", sa.Float()),
    ("yuqori_24s", sa.Float()),
    ("past_24s", sa.Float()),
)


def upgrade() -> None:
    for nom, tur in USTUNLAR:
        op.add_column("kuzatuv_bozor", sa.Column(nom, tur, nullable=True))


def downgrade() -> None:
    for nom, _ in reversed(USTUNLAR):
        op.drop_column("kuzatuv_bozor", nom)
