"""Bot ishga tushishga tayyorligi — routerlar va handlerlar to'g'ri ulanganmi.

Eslatma: aiogram routerlari modul darajasidagi yagona obyektlar va bitta
Dispatcher'ga faqat BIR MARTA biriktiriladi. Bu — jarayon uchun cheklov
emas (bitta jarayonda bitta bot ishlaydi), lekin testda dispatcher bir
marta quriladi.
"""

from __future__ import annotations

import pytest

from bot.main import build_dispatcher
from bot.settings import BotSettings
from core.config import load_config
from core.storage import Database


@pytest.fixture(scope="module")
def dispatcher():
    database = Database("sqlite+aiosqlite:///:memory:")
    settings = BotSettings(token="123:abc", admin_ids=frozenset({777}))
    return build_dispatcher(database, settings, load_config())


def test_dispatcher_quriladi(dispatcher) -> None:  # noqa: ANN001
    assert dispatcher is not None


def test_admin_routeri_birinchi_turadi(dispatcher) -> None:  # noqa: ANN001
    """`/panel` oddiy foydalanuvchi handlerlariga tushib ketmasligi kerak."""
    nomlar = [r.name for r in dispatcher.sub_routers]
    assert nomlar.index("admin") < nomlar.index("user")


def test_konfiguratsiya_handlerlarga_uzatiladi(dispatcher) -> None:  # noqa: ANN001
    assert dispatcher["config"].project.name == "HALOL CRYPTO SAVDO"


def test_barcha_handlerlar_royxatdan_otgan(dispatcher) -> None:  # noqa: ANN001
    jami = sum(
        len(observer.handlers)
        for router in dispatcher.sub_routers
        for observer in (router.message, router.callback_query)
    )
    assert jami > 20, f"handlerlar soni kutilganidan kam: {jami}"


def test_admin_routeri_ozining_himoyasiga_ega() -> None:
    """Admin router `AdminOnlyMiddleware` bilan o'ralganmi."""
    from bot.handlers import admin as admin_handlers
    from bot.middlewares import AdminOnlyMiddleware

    for observer in (admin_handlers.router.message, admin_handlers.router.callback_query):
        turlar = [type(m) for m in observer.outer_middleware._middlewares]
        turlar += [type(m) for m in observer.middleware._middlewares]
        assert AdminOnlyMiddleware in turlar
