"""3.7-band: "tizim nega sokin?" — rad etish sabablari saqlanadi.

Signal chiqmasligi XATO EMAS (0.2-band). Lekin sababi ko'rinmasa, admin
ishlayotgan tizimni buzuq tizimdan ajrata olmaydi. Jurnal yetarli emas:
u aylanadi va Telegram'dan ochib bo'lmaydi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.storage import Database
from core.storage.repositories import RiskBlockRepository

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


async def test_sabablar_yoziladi_va_guruhlanadi(db) -> None:  # noqa: ANN001
    """Eng ko'p uchragan sabab birinchi turishi kerak."""
    async with db.session() as session:
        yozilgan = await RiskBlockRepository(session).record_many(
            [
                ("BTC", "classic_ta:zone_position", "Narx Premium zonada", None),
                ("ETH", "classic_ta:zone_position", "Narx Premium zonada", None),
                ("SOL", "classic_ta:zone_position", "Narx Premium zonada", None),
                ("BTC", "threshold", "Ball 62 < chegara 70", None),
            ],
            market_health=71.0,
        )

    assert yozilgan == 4

    async with db.session() as session:
        xulosa = await RiskBlockRepository(session).summary_since(HOZIR - timedelta(days=1))

    assert xulosa[0] == ("classic_ta:zone_position", 3, False)
    assert ("threshold", 1, False) in xulosa


async def test_bosh_royxat_yozilmaydi(db) -> None:  # noqa: ANN001
    """Rad etish bo'lmasa, bazaga tegilmaydi."""
    async with db.session() as session:
        assert await RiskBlockRepository(session).record_many([]) == 0


async def test_coinsiz_sabab_saqlanadi(db) -> None:  # noqa: ANN001
    """Bozor Salomatligi past bo'lsa, sabab bitta coinga tegishli emas."""
    async with db.session() as session:
        await RiskBlockRepository(session).record_many(
            [(None, "market_health", "Bozor Salomatligi past (32/100)", None)],
            market_health=32.0,
        )

    async with db.session() as session:
        oxirgilar = await RiskBlockRepository(session).latest()

    assert len(oxirgilar) == 1
    assert oxirgilar[0].symbol is None
    assert oxirgilar[0].market_health == 32.0


async def test_uzun_sabab_qisqartiriladi(db) -> None:  # noqa: ANN001
    """`reason` ustuni 48 belgi — uzunroq matn bazani buzmasligi kerak."""
    uzun = "x" * 100

    async with db.session() as session:
        await RiskBlockRepository(session).record_many([("BTC", uzun, "tafsilot", None)])

    async with db.session() as session:
        oxirgilar = await RiskBlockRepository(session).latest()

    assert len(oxirgilar[0].reason) == 48


async def test_eski_yozuvlar_ochiriladi(db) -> None:  # noqa: ANN001
    """Har siklda o'nlab qator yoziladi — cheklanmasa jadval o'sib ketadi."""
    async with db.session() as session:
        await RiskBlockRepository(session).record_many(
            [("BTC", "threshold", "eski", None), ("ETH", "threshold", "eski", None)]
        )

    # Kelajakdagi kesim -> hamma yozuv "eski" hisoblanadi
    async with db.session() as session:
        ochirildi = await RiskBlockRepository(session).purge_before(
            datetime.now(UTC) + timedelta(days=1)
        )

    assert ochirildi == 2

    async with db.session() as session:
        assert await RiskBlockRepository(session).latest() == []


async def test_kesimdan_oldingi_sabablar_hisoblanmaydi(db) -> None:  # noqa: ANN001
    """`summary_since` faqat so'ralgan oynani qamrashi kerak."""
    async with db.session() as session:
        await RiskBlockRepository(session).record_many([("BTC", "threshold", "hozir", None)])

    async with db.session() as session:
        kelajak = datetime.now(UTC) + timedelta(hours=1)
        assert await RiskBlockRepository(session).summary_since(kelajak) == []


# --------------------------------------------------------------------------- #
#  Ball statistikasi
# --------------------------------------------------------------------------- #


async def test_ball_saqlanadi_va_hisoblanadi(db) -> None:  # noqa: ANN001
    """"Chegaradan past" o'zi hech narsa aytmaydi.

    78 ball olib 80 chegaradan qaytish — chegara bir oz baland.
    55 ball olib qaytish — chegara umuman erishib bo'lmas. Ikkovi
    butunlay boshqa muammo, lekin ball saqlanmagani uchun dashboardda
    bir xil ko'rinardi.
    """
    async with db.session() as session:
        await RiskBlockRepository(session).record_many(
            [
                ("BTC", "threshold", "Ball 55 < chegara 80", 55.0),
                ("ETH", "threshold", "Ball 47 < chegara 80", 47.0),
                ("SOL", "threshold", "Ball 60 < chegara 80", 60.0),
                ("XRP", "classic_ta:zones", "zona yo'q", None),
            ]
        )

    async with db.session() as session:
        stat = await RiskBlockRepository(session).score_stats_since(
            HOZIR - timedelta(days=1), "threshold"
        )

    assert stat is not None
    soni, eng_yuqori, ortacha = stat
    assert soni == 3, "ballsiz yozuv hisobga kirmasligi kerak"
    assert eng_yuqori == 60.0
    assert ortacha == pytest.approx(54.0)


async def test_ballsiz_sabab_uchun_statistika_yoq(db) -> None:  # noqa: ANN001
    """0.3-band: ball yo'q bo'lsa dashboard shunchaki qatorni ko'rsatmaydi."""
    async with db.session() as session:
        await RiskBlockRepository(session).record_many(
            [("BTC", "classic_ta:zones", "zona yo'q", None)]
        )

    async with db.session() as session:
        stat = await RiskBlockRepository(session).score_stats_since(
            HOZIR - timedelta(days=1), "classic_ta:zones"
        )

    assert stat is None
