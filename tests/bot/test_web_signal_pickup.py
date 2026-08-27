"""Veb-panelda yaratilgan signal botga qanday yetib boradi.

Bu yerdagi xavf jimgina yuzaga keladi: sayt signalni bazaga yozadi, bot
esa bu haqda hech narsa bilmaydi. O'shanda signal bazada "ochiq" bo'lib
turadi-yu, narxi kuzatilmaydi — na TP, na Stop aniqlanadi. Tashqaridan
hammasi joyida ko'rinadi.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.domain.enums import SignalSource, SignalStatus
from core.domain.models import SignalLevels
from core.storage import Database
from core.storage.repositories import SignalRepository

HOZIR = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


async def signal_yarat(db: Database, symbol: str = "BTC") -> int:
    """Veb-panel qiladigan ish: FAQAT bazaga yozish, tarqatishsiz."""
    async with db.session() as session:
        yozuv = await SignalRepository(session).create(
            symbol=symbol,
            levels=SignalLevels(entry=100, stop=97, tp1=104, tp2=108),
            source=SignalSource.MANUAL,
        )
        return yozuv.id


async def test_yangi_signal_tarqatilmagan_deb_topiladi(db: Database) -> None:
    signal_id = await signal_yarat(db)
    async with db.session() as session:
        kutayotganlar = await SignalRepository(session).pending_broadcast()
    assert [y.id for y in kutayotganlar] == [signal_id]


async def test_tarqatilgach_royxatdan_chiqadi(db: Database) -> None:
    """Ikkinchi marta yuborilmasligi kerak — obunachi bir xil signalni
    ikki marta olsa, qaysi biriga ishonishni bilmaydi."""
    signal_id = await signal_yarat(db)
    async with db.session() as session:
        await SignalRepository(session).mark_broadcast(signal_id, HOZIR)

    async with db.session() as session:
        repo = SignalRepository(session)
        assert await repo.pending_broadcast() == []
        yozuv = await repo.get(signal_id)
        assert yozuv.broadcast_at == HOZIR


async def test_yopilgan_signal_tarqatilmaydi(db: Database) -> None:
    """Bekor qilingan signal tarqatilmasligi kerak: admin uni ataylab
    to'xtatgan, fon vazifasi esa uni "yangi" deb yuborib yubormasin."""
    signal_id = await signal_yarat(db)
    async with db.session() as session:
        yozuv = await SignalRepository(session).get(signal_id)
        yozuv.status = SignalStatus.CANCELLED.value

    async with db.session() as session:
        assert await SignalRepository(session).pending_broadcast() == []


async def test_bir_nechta_signal_yaratilish_tartibida(db: Database) -> None:
    birinchi = await signal_yarat(db, "BTC")
    ikkinchi = await signal_yarat(db, "ETH")
    async with db.session() as session:
        kutayotganlar = await SignalRepository(session).pending_broadcast()
    assert [y.id for y in kutayotganlar] == [birinchi, ikkinchi]
