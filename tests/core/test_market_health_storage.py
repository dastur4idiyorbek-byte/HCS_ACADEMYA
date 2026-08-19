"""3.7-band: indeks tarixi — postmortem (3.8) uchun zarur."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.market_health import HealthInputs, MarketHealthCalculator
from core.config import load_config
from core.domain.enums import TrendDirection
from core.storage import Database
from core.storage.repositories import MarketHealthRepository

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


def salomatlik(uptrend: int = 30):  # noqa: ANN201
    config = load_config()
    return MarketHealthCalculator(config).compute(
        HealthInputs(
            computed_at=HOZIR,
            btc_dominance=54.0,
            btc_dominance_change_24h=0.1,
            universe_trends={
                f"C{i}": (TrendDirection.UP if i < uptrend else TrendDirection.DOWN)
                for i in range(30)
            },
            universe_adx={f"C{i}": 40.0 for i in range(30)},
            open_signals=1,
            max_open_signals=5,
        )
    )


async def test_indeks_saqlanadi_va_oqiladi(db: Database) -> None:
    async with db.session() as session:
        await MarketHealthRepository(session).record(salomatlik())

    async with db.session() as session:
        yozuv = await MarketHealthRepository(session).latest()
        assert yozuv is not None
        assert yozuv.value > 0
        assert yozuv.band in {"high", "mid", "low"}
        assert yozuv.detail, "omillar izohi saqlanishi kerak"


async def test_omil_ballari_alohida_saqlanadi(db: Database) -> None:
    """Postmortem qaysi omil aybdor ekanini aniqlay olishi kerak."""
    async with db.session() as session:
        await MarketHealthRepository(session).record(salomatlik())

    async with db.session() as session:
        yozuv = await MarketHealthRepository(session).latest()
        assert yozuv.btc_dominance_score is not None
        assert yozuv.trend_breadth_score is not None
        assert yozuv.volatility_score is not None
        assert yozuv.saturation_score is not None


async def test_tarix_yangisidan_eskisiga_qaytadi(db: Database) -> None:
    async with db.session() as session:
        repo = MarketHealthRepository(session)
        for uptrend in (5, 15, 30):
            await repo.record(salomatlik(uptrend))

    async with db.session() as session:
        tarix = await MarketHealthRepository(session).history(limit=3)
        assert len(tarix) == 3
        assert tarix[0].value > tarix[-1].value, "eng yangisi birinchi bo'lishi kerak"


async def test_kunlik_tahlil_alohida_belgilanadi(db: Database) -> None:
    async with db.session() as session:
        await MarketHealthRepository(session).record(salomatlik(), is_daily_preview=True)

    async with db.session() as session:
        assert (await MarketHealthRepository(session).latest()).is_daily_preview


async def test_ortacha_kunlik_tahlilni_hisobga_olmaydi(db: Database) -> None:
    """Kunlik oldindan tahlil — taxmin, o'lchov emas. O'rtachaga kirmasligi kerak."""
    haqiqiy = salomatlik(30)
    taxmin = salomatlik(0)
    assert haqiqiy.value != taxmin.value, "sinov uchun qiymatlar farq qilishi kerak"

    async with db.session() as session:
        repo = MarketHealthRepository(session)
        await repo.record(haqiqiy)
        await repo.record(taxmin, is_daily_preview=True)

    async with db.session() as session:
        ortacha = await MarketHealthRepository(session).average_since(
            HOZIR - timedelta(days=1)
        )

    assert ortacha == pytest.approx(haqiqiy.value), (
        "faqat haqiqiy o'lchov hisobga olinishi kerak"
    )


async def test_tarix_bosh_bolsa_none(db: Database) -> None:
    async with db.session() as session:
        assert await MarketHealthRepository(session).latest() is None
        assert await MarketHealthRepository(session).history() == []
