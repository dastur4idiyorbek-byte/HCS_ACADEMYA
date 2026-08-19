"""3.8-band: yopilgan signallarni bazadan yig'ish."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.postmortem import Outcome
from core.domain.enums import SignalSource, SignalStatus
from core.domain.models import SignalLevels
from core.storage import Database
from core.storage.repositories import SignalRepository

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


async def signal_yarat(
    db: Database,
    symbol: str = "BTC",
    score: float = 80.0,
    health: float = 75.0,
    source: SignalSource = SignalSource.CLASSIC_TA,
) -> int:
    async with db.session() as session:
        yozuv = await SignalRepository(session).create(
            symbol=symbol,
            levels=SignalLevels(entry=100, stop=99.2, tp1=103, tp2=104),
            source=source,
            score=score,
            market_health=health,
        )
        return yozuv.id


async def yop(
    db: Database,
    signal_id: int,
    status: SignalStatus,
    price: float,
    tp1_oldi: bool = False,
    false_signal: bool = False,
) -> None:
    async with db.session() as session:
        repo = SignalRepository(session)
        await repo.apply_event(signal_id, SignalStatus.ACTIVE, 100.0, HOZIR, "activated")
        if tp1_oldi:
            await repo.apply_event(signal_id, SignalStatus.TP1_HIT, 103.0, HOZIR, "tp1_hit")
        await repo.apply_event(
            signal_id,
            status,
            price,
            HOZIR,
            "false_signal" if false_signal else status.value,
        )


async def test_yopilgan_signallar_yigiladi(db: Database) -> None:
    signal_id = await signal_yarat(db)
    await yop(db, signal_id, SignalStatus.TP2_HIT, 104.0)

    async with db.session() as session:
        natija = await SignalRepository(session).closed_since(HOZIR - timedelta(days=30))

    assert len(natija) == 1
    assert natija[0].outcome is Outcome.TP2
    assert natija[0].score == 80.0
    assert natija[0].market_health_at_entry == 75.0


async def test_tp1_dan_keyingi_stop_ajratiladi(db: Database) -> None:
    """Bu farq naqsh tahlilida muhim — foyda va zarar aralashib ketmasligi kerak."""
    oddiy = await signal_yarat(db, symbol="ETH")
    tp1_li = await signal_yarat(db, symbol="SOL")

    await yop(db, oddiy, SignalStatus.STOPPED, 99.2)
    await yop(db, tp1_li, SignalStatus.STOPPED, 99.2, tp1_oldi=True)

    async with db.session() as session:
        natija = {
            s.symbol: s.outcome
            for s in await SignalRepository(session).closed_since(HOZIR - timedelta(days=30))
        }

    assert natija["ETH"] is Outcome.STOP
    assert natija["SOL"] is Outcome.TP1_THEN_STOP


async def test_ochiq_signallar_yigilmaydi(db: Database) -> None:
    await signal_yarat(db)

    async with db.session() as session:
        assert await SignalRepository(session).closed_since(HOZIR - timedelta(days=30)) == []


async def test_eski_signallar_davrdan_tashqarida(db: Database) -> None:
    signal_id = await signal_yarat(db)
    await yop(db, signal_id, SignalStatus.TP2_HIT, 104.0)

    async with db.session() as session:
        kelajak = await SignalRepository(session).closed_since(HOZIR + timedelta(days=1))
    assert kelajak == []


async def test_yolgon_signal_bayrogi_yigiladi(db: Database) -> None:
    signal_id = await signal_yarat(db)
    await yop(db, signal_id, SignalStatus.STOPPED, 99.2, false_signal=True)

    async with db.session() as session:
        natija = await SignalRepository(session).closed_since(HOZIR - timedelta(days=30))

    assert natija[0].is_false_signal


async def test_strategiya_manbai_saqlanadi(db: Database) -> None:
    """Strategiyalar naqshini izlash uchun zarur."""
    skalp = await signal_yarat(db, symbol="ADA", source=SignalSource.OPENING_RANGE_SCALP)
    await yop(db, skalp, SignalStatus.TP2_HIT, 104.0)

    async with db.session() as session:
        natija = await SignalRepository(session).closed_since(HOZIR - timedelta(days=30))

    assert natija[0].source is SignalSource.OPENING_RANGE_SCALP


async def test_hisobot_bazadagi_malumotdan_quriladi(db: Database) -> None:
    """Uchdan-uchgacha: baza -> yig'ish -> naqsh -> hisobot."""
    from core.analysis.postmortem import build_report, render_report
    from core.config.schema import PostmortemConfig

    for i in range(6):
        past = await signal_yarat(db, symbol=f"L{i}", score=60.0, health=40.0)
        await yop(db, past, SignalStatus.STOPPED, 99.2)
    for i in range(6):
        baland = await signal_yarat(db, symbol=f"H{i}", score=90.0, health=85.0)
        await yop(db, baland, SignalStatus.TP2_HIT, 104.0)

    async with db.session() as session:
        signallar = await SignalRepository(session).closed_since(HOZIR - timedelta(days=30))

    hisobot = build_report(
        signallar, PostmortemConfig(min_sample_size=5, min_effect_pct=15.0), HOZIR
    )

    assert hisobot.stats.traded == 12
    assert hisobot.has_findings, "aniq naqsh topilishi kerak"
    assert "AVTOMATIK qo'llanilmaydi" in render_report(hisobot)
