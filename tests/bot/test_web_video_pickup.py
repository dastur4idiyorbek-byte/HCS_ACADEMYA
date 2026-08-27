"""Saytga yuklangan video darslik botga qanday yetib boradi.

Xavf signallardagi bilan bir xil turdagi: sayt faylni diskka yozadi va
uni o'zi o'ynatadi, bot esa bu haqda hech narsa bilmaydi. O'shanda dars
SAYTDA bor, BOTDA yo'q bo'lib qoladi — bitta ro'yxat ikki joyda ikki
xil. Foydalanuvchi uchun bu "sayt boshqa, bot boshqa" degan taassurot
qoldiradi.

Yechim: `pending_upload()` "diskda bor, Telegramda yo'q" darslarni
topadi, fon vazifasi ularni Telegramga chiqaradi va `file_id` ni
saqlaydi.
"""

from __future__ import annotations

import pytest

from core.domain.enums import SubscriptionTier
from core.storage import Database
from core.storage.repositories import ContentRepository


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


async def dars_yarat(
    db: Database,
    title: str = "1-dars",
    *,
    file_id: str | None = None,
    video_path: str | None = None,
) -> int:
    async with db.session() as session:
        yozuv = await ContentRepository(session).add(
            kind="video",
            title=title,
            file_id=file_id,
            min_tier=SubscriptionTier.PRO,
        )
        yozuv.video_path = video_path
        await session.flush()
        return yozuv.id


async def test_saytga_yuklangan_dars_navbatga_tushadi(db: Database) -> None:
    dars_id = await dars_yarat(db, video_path="abc.mp4")
    async with db.session() as session:
        kutayotganlar = await ContentRepository(session).pending_upload()
    assert [k.id for k in kutayotganlar] == [dars_id]


async def test_telegramga_chiqqach_navbatdan_chiqadi(db: Database) -> None:
    """Ikkinchi marta yuborilmasligi kerak: har urinish yuz megabaytlik
    yuklash va adminning chatida takroriy video demak."""
    dars_id = await dars_yarat(db, video_path="abc.mp4")
    async with db.session() as session:
        await ContentRepository(session).set_file_id(dars_id, "TG-123")

    async with db.session() as session:
        repo = ContentRepository(session)
        assert await repo.pending_upload() == []


async def test_faqat_botdagi_eski_dars_tegilmaydi(db: Database) -> None:
    """Eski darslarda `file_id` bor, `video_path` yo'q. Ular saytga
    yuklanmagan — fon vazifasi ularga umuman tegmasligi kerak."""
    await dars_yarat(db, file_id="TG-eski")
    async with db.session() as session:
        assert await ContentRepository(session).pending_upload() == []


async def test_videosiz_dars_ham_tegilmaydi(db: Database) -> None:
    """Sarlavhasi yozilgan, videosi hali yo'q dars — bo'sh yuborishga
    urinmaslik kerak."""
    await dars_yarat(db)
    async with db.session() as session:
        assert await ContentRepository(session).pending_upload() == []


async def test_bir_nechta_dars_id_tartibida(db: Database) -> None:
    birinchi = await dars_yarat(db, "1-dars", video_path="a.mp4")
    ikkinchi = await dars_yarat(db, "2-dars", video_path="b.mp4")
    async with db.session() as session:
        kutayotganlar = await ContentRepository(session).pending_upload()
    assert [k.id for k in kutayotganlar] == [birinchi, ikkinchi]
