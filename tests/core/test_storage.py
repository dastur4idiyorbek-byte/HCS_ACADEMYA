"""2-bosqich: ma'lumotlar bazasi sxemasi."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from core.storage import CoinRuling, Database, SignalRecord, Subscription, User, UserPosition

KUTILGAN_JADVALLAR = {
    "users",
    "subscriptions",
    "payments",
    "signals",
    "signal_events",
    "content",
    "violations",
    "price_config",
    "risk_config",
    "coin_rulings",
    "halal_universe_snapshots",
    "user_positions",
    "daily_stats",
    "market_health_log",
    "risk_blocks",
}


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


async def test_barcha_jadvallar_yaratiladi(db: Database) -> None:
    """7-bo'lim 2-bosqichda sanab o'tilgan jadvallar mavjudmi."""
    from core.storage.base import Base

    assert set(Base.metadata.tables) >= KUTILGAN_JADVALLAR


async def test_foydalanuvchi_va_obuna_saqlanadi(db: Database) -> None:
    hozir = datetime.now(UTC)
    async with db.session() as session:
        user = User(telegram_id=555, username="test", full_name="Test User")
        user.subscriptions.append(
            Subscription(
                tier="premium",
                period="monthly",
                status="active",
                starts_at=hozir,
                expires_at=hozir + timedelta(days=30),
            )
        )
        session.add(user)

    async with db.session() as session:
        topilgan = (await session.execute(select(User).where(User.telegram_id == 555))).scalar_one()
        assert topilgan.role == "user"
        assert topilgan.language == "uz"


async def test_telegram_id_takrorlanmaydi(db: Database) -> None:
    async with db.session() as session:
        session.add(User(telegram_id=777))

    with pytest.raises(Exception):  # noqa: B017 — dialektga xos IntegrityError
        async with db.session() as session:
            session.add(User(telegram_id=777))


async def test_bitta_signalga_bitta_pozitsiya(db: Database) -> None:
    """5.4-band: foydalanuvchi bir signalga ikki marta "kirdim" deya olmaydi."""
    async with db.session() as session:
        user = User(telegram_id=1)
        signal = SignalRecord(
            symbol="BTC", source="manual", status="active", entry=100, stop=99, tp1=103, tp2=105
        )
        session.add_all([user, signal])
        await session.flush()
        session.add(
            UserPosition(
                user_id=user.id,
                signal_id=signal.id,
                amount_usd=100,
                entry_price=100,
                trade_date=date.today(),
            )
        )
        saqlangan = (user.id, signal.id)

    with pytest.raises(Exception):  # noqa: B017
        async with db.session() as session:
            session.add(
                UserPosition(
                    user_id=saqlangan[0],
                    signal_id=saqlangan[1],
                    amount_usd=50,
                    entry_price=100,
                    trade_date=date.today(),
                )
            )


async def test_coin_qarori_saqlanadi(db: Database) -> None:
    """1.4-band: admin qo'lda harom/shubhali deb belgilaydi."""
    async with db.session() as session:
        session.add(
            CoinRuling(symbol="XYZ", status="mashbooh", reason="noaniq tabiat", set_by=123)
        )

    async with db.session() as session:
        qaror = (
            await session.execute(select(CoinRuling).where(CoinRuling.symbol == "XYZ"))
        ).scalar_one()
        assert qaror.status == "mashbooh"


async def test_healthcheck_ishlaydi(db: Database) -> None:
    assert await db.healthcheck()


async def test_vaqt_doim_timezone_aware_qaytadi(db: Database) -> None:
    """SQLite vaqt zonasini saqlamaydi — `UtcDateTime` uni tiklaydi.

    Ansiz naive va aware vaqtni taqqoslash TypeError berardi, va bundan ham
    yomoni — Juma filtri (4.8-band) jimgina noto'g'ri ishlashi mumkin edi.
    """
    hozir = datetime.now(UTC)
    async with db.session() as session:
        user = User(telegram_id=4242)
        user.subscriptions.append(
            Subscription(
                tier="lite",
                period="monthly",
                status="active",
                starts_at=hozir,
                expires_at=hozir + timedelta(days=30),
            )
        )
        session.add(user)

    async with db.session() as session:
        obuna = (await session.execute(select(Subscription))).scalars().first()
        assert obuna.expires_at.tzinfo is not None, "vaqt zonasi yo'qolmasligi kerak"
        assert obuna.created_at.tzinfo is not None
        # Aware vaqt bilan taqqoslash xatosiz ishlashi kerak
        assert obuna.expires_at > datetime.now(UTC)


async def test_naive_vaqt_saqlashga_ruxsat_yoq(db: Database) -> None:
    """Timezone-siz vaqt jim qabul qilinsa, xato manbai bo'lardi."""
    with pytest.raises(Exception, match="naive|Timezone"):
        async with db.session() as session:
            session.add(
                Subscription(
                    user_id=1,
                    tier="lite",
                    period="monthly",
                    status="active",
                    starts_at=datetime(2026, 8, 19, 12, 0),  # naive
                    expires_at=datetime(2026, 9, 19, 12, 0),
                )
            )
