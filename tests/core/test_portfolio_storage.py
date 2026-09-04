"""5.4-band: pozitsiyalar bazasi va umumiy statistika."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.config.schema import PortfolioConfig
from core.domain.enums import SignalSource
from core.domain.models import signal_levels
from core.services import compute_outcome, summarize
from core.storage import Database
from core.storage.repositories import (
    SignalRepository,
    UserPositionRepository,
    UserRepository,
)

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
KONFIG = PortfolioConfig(tp_close_shares=((100.0,), (50.0, 50.0), (40.0, 30.0, 30.0)))


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


async def tayyorla(db: Database, telegram_id: int = 111) -> tuple[int, int]:
    """Foydalanuvchi va signal yaratadi."""
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(telegram_id)
        signal = await SignalRepository(session).create(
            symbol="BTC",
            levels=signal_levels(entry=100, stop=99, tp1=103, tp2=105),
            source=SignalSource.ZANJIR,
            score=82.0,
        )
        return user.id, signal.id


# --------------------------------------------------------------------------- #
#  Pozitsiya qayd etish
# --------------------------------------------------------------------------- #


async def test_pozitsiya_qayd_etiladi(db: Database) -> None:
    user_id, signal_id = await tayyorla(db)

    async with db.session() as session:
        await UserPositionRepository(session).record_entry(
            user_id=user_id, signal_id=signal_id, amount_usd=250.0, entry_price=100.0
        )

    async with db.session() as session:
        pozitsiya = await UserPositionRepository(session).get(user_id, signal_id)
        assert pozitsiya.amount_usd == 250.0
        assert pozitsiya.closed_at is None


async def test_bir_signalga_ikki_marta_kirib_bolmaydi(db: Database) -> None:
    user_id, signal_id = await tayyorla(db)

    async with db.session() as session:
        await UserPositionRepository(session).record_entry(
            user_id=user_id, signal_id=signal_id, amount_usd=250.0, entry_price=100.0
        )

    with pytest.raises(Exception):  # noqa: B017 — UNIQUE cheklovi
        async with db.session() as session:
            await UserPositionRepository(session).record_entry(
                user_id=user_id, signal_id=signal_id, amount_usd=100.0, entry_price=100.0
            )


async def test_manfiy_miqdor_rad_etiladi(db: Database) -> None:
    user_id, signal_id = await tayyorla(db)

    async with db.session() as session:
        with pytest.raises(ValueError, match="musbat"):
            await UserPositionRepository(session).record_entry(
                user_id=user_id, signal_id=signal_id, amount_usd=-5, entry_price=100.0
            )


# --------------------------------------------------------------------------- #
#  Yopish va natija
# --------------------------------------------------------------------------- #


async def test_pozitsiya_yopilib_natija_saqlanadi(db: Database) -> None:
    user_id, signal_id = await tayyorla(db)

    async with db.session() as session:
        repo = UserPositionRepository(session)
        await repo.record_entry(
            user_id=user_id, signal_id=signal_id, amount_usd=200.0, entry_price=100.0
        )

    async with db.session() as session:
        repo = UserPositionRepository(session)
        pozitsiya = (await repo.open_for_signal(signal_id))[0]
        natija = compute_outcome(200.0, 100.0, 99.0, KONFIG, tp1_price=103.0)
        await repo.close(pozitsiya, 99.0, natija, HOZIR)

    async with db.session() as session:
        yopilgan = await UserPositionRepository(session).get(user_id, signal_id)
        assert yopilgan.closed_at is not None
        assert yopilgan.pnl_pct == pytest.approx(1.0), "qismli yopish hisobga olinishi kerak"
        assert yopilgan.partial_exit_price == 103.0
        assert yopilgan.partial_close_pct == 50.0


async def test_yopilgan_pozitsiya_qayta_yopilmaydi(db: Database) -> None:
    user_id, signal_id = await tayyorla(db)

    async with db.session() as session:
        repo = UserPositionRepository(session)
        await repo.record_entry(
            user_id=user_id, signal_id=signal_id, amount_usd=100.0, entry_price=100.0
        )

    async with db.session() as session:
        repo = UserPositionRepository(session)
        pozitsiya = (await repo.open_for_signal(signal_id))[0]
        await repo.close(pozitsiya, 105.0, compute_outcome(100, 100, 105, KONFIG), HOZIR)

    async with db.session() as session:
        assert await UserPositionRepository(session).open_for_signal(signal_id) == []


async def test_portfel_xulosasi_bazadan_quriladi(db: Database) -> None:
    user_id, birinchi = await tayyorla(db)

    async with db.session() as session:
        ikkinchi = await SignalRepository(session).create(
            symbol="ETH",
            levels=signal_levels(entry=50, stop=49.5, tp1=51.5, tp2=52.5),
            source=SignalSource.ZANJIR,
        )
        repo = UserPositionRepository(session)
        await repo.record_entry(user_id, birinchi, 100.0, 100.0)
        await repo.record_entry(user_id, ikkinchi.id, 200.0, 50.0)

    async with db.session() as session:
        repo = UserPositionRepository(session)
        pozitsiya = (await repo.open_for_signal(birinchi))[0]
        await repo.close(pozitsiya, 105.0, compute_outcome(100, 100, 105, KONFIG), HOZIR)

    async with db.session() as session:
        pozitsiyalar = await UserPositionRepository(session).snapshots_for(user_id)

    xulosa = summarize(pozitsiyalar)
    assert xulosa.total_positions == 2
    assert xulosa.open_positions == 1
    assert xulosa.realized_pnl_usd == pytest.approx(5.0)
    assert {p.symbol for p in pozitsiyalar} == {"BTC", "ETH"}


# --------------------------------------------------------------------------- #
#  Umumiy statistika (3.6-band)
# --------------------------------------------------------------------------- #










async def test_ishtirokchi_soni_signal_boyicha(db: Database) -> None:
    _, signal_id = await tayyorla(db)

    async with db.session() as session:
        users = UserRepository(session)
        repo = UserPositionRepository(session)
        for tg in (111, 222):
            user = await users.get_or_create(tg)
            await repo.record_entry(user.id, signal_id, 50.0, 100.0)

    async with db.session() as session:
        assert await UserPositionRepository(session).participant_count(signal_id) == 2
