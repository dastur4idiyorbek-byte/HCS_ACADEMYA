"""Middleware'lar — kontekst tayyorlash va admin himoyasi."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bot.middlewares import AdminOnlyMiddleware, UserContextMiddleware
from bot.settings import BotSettings
from core.domain.enums import SubscriptionTier
from core.storage import Database
from core.storage.repositories import SubscriptionRepository, UserRepository
from core.utils.time_utils import utc_now


class SoxtaMessage:
    """Minimal Telegram xabari — aiogram tipiga bog'lanmasdan sinash uchun."""

    def __init__(self, telegram_id: int, is_bot: bool = False) -> None:
        self.from_user = SimpleNamespace(
            id=telegram_id, is_bot=is_bot, username="test", full_name="Test User"
        )


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


@pytest.fixture
def settings() -> BotSettings:
    return BotSettings(token="123:abc", admin_ids=frozenset({777}))


async def _run(middleware, event, data=None):  # noqa: ANN001
    """Middleware'ni ishga tushirib, handlerga yetib kelgan ma'lumotni qaytaradi."""
    yetib_kelgan = {}

    async def handler(_event, _data):  # noqa: ANN001
        yetib_kelgan.update(_data)
        return "bajarildi"

    natija = await middleware(handler, event, data if data is not None else {})
    return natija, yetib_kelgan


# --------------------------------------------------------------------------- #
#  Kontekst middleware
# --------------------------------------------------------------------------- #


async def test_foydalanuvchi_kontekstga_qoyiladi(db: Database, settings: BotSettings) -> None:
    _, data = await _run(UserContextMiddleware(db, settings), SoxtaMessage(111))

    assert data["is_admin"] is False
    assert data["tier"] is None
    assert data["language"] == "uz"
    assert data["db_user_id"] > 0


async def test_admin_roli_env_dan_aniqlanadi(db: Database, settings: BotSettings) -> None:
    """1.1-band: bitta bot, rol Telegram ID asosida."""
    _, data = await _run(UserContextMiddleware(db, settings), SoxtaMessage(777))
    assert data["is_admin"] is True


async def test_faol_obuna_kontekstga_tushadi(db: Database, settings: BotSettings) -> None:
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(222)
        await SubscriptionRepository(session).create(
            user.id, SubscriptionTier.PRO, period_days=30, is_trial=False, now=utc_now()
        )

    _, data = await _run(UserContextMiddleware(db, settings), SoxtaMessage(222))
    assert data["tier"] is SubscriptionTier.PRO


async def test_bot_xabarlari_otkazib_yuboriladi(db: Database, settings: BotSettings) -> None:
    natija, data = await _run(
        UserContextMiddleware(db, settings), SoxtaMessage(333, is_bot=True)
    )
    assert natija == "bajarildi"
    assert "db_user_id" not in data, "bot uchun foydalanuvchi yaratilmasligi kerak"


# --------------------------------------------------------------------------- #
#  Admin himoyasi
# --------------------------------------------------------------------------- #


async def test_oddiy_foydalanuvchi_admin_bolimiga_kira_olmaydi() -> None:
    natija, data = await _run(AdminOnlyMiddleware(), SoxtaMessage(111), {"is_admin": False})
    assert natija is None, "handler umuman chaqirilmasligi kerak"
    assert data == {}


async def test_admin_otkaziladi() -> None:
    natija, _ = await _run(AdminOnlyMiddleware(), SoxtaMessage(777), {"is_admin": True})
    assert natija == "bajarildi"


async def test_rol_belgilanmagan_bolsa_kirish_yopiq() -> None:
    """Fail-safe: `is_admin` yo'q bo'lsa ruxsat berilmaydi."""
    natija, _ = await _run(AdminOnlyMiddleware(), SoxtaMessage(111), {})
    assert natija is None
