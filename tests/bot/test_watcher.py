"""2-bo'lim: signal kuzatuvchisi — narx oqimidan bazagacha to'liq yo'l.

Soxta narx oqimi va soxta bot bilan sinaladi: haqiqiy tarmoq va Telegram
kerak emas, chunki barcha qatlamlar abstraksiya orqali ulangan.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest

from bot.services import SignalWatcher
from core.config import load_config
from core.domain.enums import SignalSource, SignalStatus, SubscriptionTier
from core.domain.models import PriceTick, signal_levels
from core.market_data import PriceStream
from core.storage import Database
from core.storage.repositories import (
    SignalRepository,
    SubscriptionRepository,
    UserPositionRepository,
    UserRepository,
)

BOSH = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


class SoxtaStream(PriceStream):
    """Oldindan belgilangan narxlarni uzatadigan oqim."""

    def __init__(self, ticks: list[PriceTick]) -> None:
        self._ticks = ticks
        self.subscribed: set[str] = set()

    def subscribe(self, symbols: set[str]) -> None:
        self.subscribed = set(symbols)

    async def stream(self) -> AsyncIterator[PriceTick]:
        for tick in self._ticks:
            yield tick

    async def close(self) -> None:
        pass


class SoxtaBot:
    """Yuborilgan xabarlarni yig'ib boradigan bot."""

    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, **_: object) -> None:
        self.messages.append((chat_id, text))


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


async def _obunachi_yarat(db: Database, telegram_id: int = 555) -> None:
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(telegram_id)
        await SubscriptionRepository(session).create(
            user.id, SubscriptionTier.PREMIUM, period_days=30, is_trial=False
        )


async def _signal_yarat(db: Database, symbol: str = "BTC", entry: float = 100.0) -> int:
    async with db.session() as session:
        yozuv = await SignalRepository(session).create(
            symbol=symbol,
            levels=signal_levels(
                entry=entry, stop=entry * 0.99, tp1=entry * 1.03, tp2=entry * 1.05
            ),
            source=SignalSource.MANUAL,
        )
        return yozuv.id


def _watcher(bot, db: Database, stream: PriceStream, admins=frozenset({1})) -> SignalWatcher:  # noqa: ANN001
    return SignalWatcher(bot, db, load_config(), stream, admins)


# --------------------------------------------------------------------------- #
#  Kuzatuvni tiklash
# --------------------------------------------------------------------------- #


async def test_qayta_ishga_tushganda_kuzatuv_tiklanadi(db: Database) -> None:
    """Ansiz qayta ishga tushirish barcha faol signallarni yo'qotardi."""
    await _signal_yarat(db, "BTC")
    await _signal_yarat(db, "ETH", entry=50)

    stream = SoxtaStream([])
    watcher = _watcher(SoxtaBot(), db, stream)
    soni = await watcher.restore_from_database()

    assert soni == 2
    assert stream.subscribed == {"BTC", "ETH"}, "oqim obunasi ham tiklanishi kerak"


async def test_yopilgan_signal_tiklanmaydi(db: Database) -> None:
    signal_id = await _signal_yarat(db, "BTC")
    async with db.session() as session:
        await SignalRepository(session).apply_event(
            signal_id, SignalStatus.STOPPED, 99.0, BOSH, "stopped"
        )

    watcher = _watcher(SoxtaBot(), db, SoxtaStream([]))
    assert await watcher.restore_from_database() == 0


# --------------------------------------------------------------------------- #
#  Narx oqimidan bazagacha
# --------------------------------------------------------------------------- #


async def test_holat_ozgarishi_bazaga_yoziladi(db: Database) -> None:
    signal_id = await _signal_yarat(db, "BTC")
    await _obunachi_yarat(db)

    stream = SoxtaStream(
        [
            PriceTick("BTC", 101.0, BOSH),                             # hali yetmagan
            PriceTick("BTC", 100.0, BOSH + timedelta(minutes=5)),      # Entry
            PriceTick("BTC", 103.0, BOSH + timedelta(hours=2)),        # TP1
            PriceTick("BTC", 105.0, BOSH + timedelta(hours=4)),        # TP2
        ]
    )
    watcher = _watcher(SoxtaBot(), db, stream)
    await watcher.run()

    async with db.session() as session:
        yozuv = await SignalRepository(session).get(signal_id)
        assert yozuv.status == SignalStatus.TP2_HIT.value
        assert yozuv.activated_at is not None
        assert yozuv.closed_at is not None
        assert yozuv.close_price == 105.0
        # 5.0 EMAS: TP1 da pozitsiyaning yarmi 103 da sotilgan
        # (`portfolio.tp1_close_pct`), qolgani 105 da. Ya'ni
        # 50%×3% + 50%×5% = 4%. Ilgari bu yerda 5% yozilardi — butun
        # pozitsiya TP2 narxida sotilgandek, natija esa haqiqiydan
        # yuqori chiqardi.
        assert yozuv.result_pct == pytest.approx(4.0)
        assert yozuv.tp1_reached is True


async def test_obunachiga_xabar_yuboriladi(db: Database) -> None:
    await _signal_yarat(db, "BTC")
    await _obunachi_yarat(db, telegram_id=555)

    bot = SoxtaBot()
    stream = SoxtaStream(
        [
            PriceTick("BTC", 100.0, BOSH),
            PriceTick("BTC", 103.0, BOSH + timedelta(hours=1)),
        ]
    )
    await _watcher(bot, db, stream).run()

    qabul_qiluvchilar = {chat_id for chat_id, _ in bot.messages}
    assert qabul_qiluvchilar == {555}
    assert any("🟢" in matn for _, matn in bot.messages), "faollashish xabari (🟢 = faol)"
    assert any("🎯" in matn for _, matn in bot.messages), "TP1 xabari"


async def test_obunasiz_foydalanuvchiga_xabar_bormaydi(db: Database) -> None:
    """1.3-band: signal — pullik kontent."""
    await _signal_yarat(db, "BTC")
    async with db.session() as session:
        await UserRepository(session).get_or_create(999)  # obunasiz

    bot = SoxtaBot()
    await _watcher(bot, db, SoxtaStream([PriceTick("BTC", 100.0, BOSH)])).run()

    assert bot.messages == []


async def test_yolgon_signal_bazada_belgilanadi(db: Database) -> None:
    """3.8-band: faol bo'lgach 1 soat ichida Stop."""
    signal_id = await _signal_yarat(db, "BTC")
    await _obunachi_yarat(db)

    stream = SoxtaStream(
        [
            PriceTick("BTC", 100.0, BOSH),
            PriceTick("BTC", 99.0, BOSH + timedelta(minutes=20)),
        ]
    )
    await _watcher(SoxtaBot(), db, stream).run()

    async with db.session() as session:
        yozuv = await SignalRepository(session).get(signal_id)
        assert yozuv.status == SignalStatus.STOPPED.value
        assert yozuv.is_false_signal is True


# --------------------------------------------------------------------------- #
#  4.7 — Kill switch
# --------------------------------------------------------------------------- #


async def test_narx_sakrashi_kill_switchni_ishga_tushiradi(db: Database) -> None:
    await _signal_yarat(db, "BTC")

    bot = SoxtaBot()
    stream = SoxtaStream(
        [
            PriceTick("BTC", 200.0, BOSH),
            PriceTick("BTC", 220.0, BOSH + timedelta(seconds=10)),  # +10%
        ]
    )
    watcher = _watcher(bot, db, stream, admins=frozenset({1, 2}))
    await watcher.run()

    assert watcher.kill_switch_active
    assert "BTC" in watcher.kill_switch_reason
    adminlar = {chat_id for chat_id, matn in bot.messages if "FAVQULODDA" in matn}
    assert adminlar == {1, 2}, "barcha adminlar ogohlantirilishi kerak"


async def test_kill_switch_qolda_tiklanadi(db: Database) -> None:
    """4.7-band: inson tekshirmaguncha qayta ishga tushmaydi."""
    stream = SoxtaStream(
        [
            PriceTick("BTC", 200.0, BOSH),
            PriceTick("BTC", 220.0, BOSH + timedelta(seconds=10)),
        ]
    )
    watcher = _watcher(SoxtaBot(), db, stream)
    await watcher.run()
    assert watcher.kill_switch_active

    watcher.reset_kill_switch()
    assert not watcher.kill_switch_active
    assert watcher.kill_switch_reason is None


# --------------------------------------------------------------------------- #
#  Chidamlilik
# --------------------------------------------------------------------------- #


async def test_narx_keshi_toldiriladi(db: Database) -> None:
    """Risk Engine `FreshDataRule` shu keshga tayanadi."""
    await _signal_yarat(db, "BTC")
    stream = SoxtaStream([PriceTick("BTC", 100.0, BOSH)])
    watcher = _watcher(SoxtaBot(), db, stream)
    await watcher.run()

    assert watcher.prices.price_of("BTC") == 100.0


async def test_kuzatuv_royxati_yopilgach_qisqaradi(db: Database) -> None:
    await _signal_yarat(db, "BTC")
    await _obunachi_yarat(db)

    stream = SoxtaStream(
        [
            PriceTick("BTC", 100.0, BOSH),
            PriceTick("BTC", 99.0, BOSH + timedelta(hours=5)),
        ]
    )
    watcher = _watcher(SoxtaBot(), db, stream)
    await watcher.run()

    assert watcher.tracker.symbols() == set()
    assert stream.subscribed == set(), "yopilgan signal obunadan chiqadi"


# --------------------------------------------------------------------------- #
#  Yuborilgan signalni bekor qilish (admin)
# --------------------------------------------------------------------------- #


async def test_bekor_qilish_bazani_va_kuzatuvni_yangilaydi(db: Database) -> None:
    """Bitta chaqiruv hamma joyni yopishi kerak — aks holda signal bir
    joyda yopiq, boshqasida ochiq ko'rinardi."""
    signal_id = await _signal_yarat(db, "BTC")
    await _obunachi_yarat(db)

    stream = SoxtaStream([])
    watcher = _watcher(SoxtaBot(), db, stream)
    await watcher.restore_from_database()
    assert stream.subscribed == {"BTC"}

    symbol = await watcher.cancel_signal(signal_id, "Admin bekor qildi")

    assert symbol == "BTC"
    assert watcher.tracker.symbols() == set()
    assert stream.subscribed == set(), "bekor qilingan coin oqim obunasidan chiqadi"
    async with db.session() as session:
        yozuv = await SignalRepository(session).get(signal_id)
        assert yozuv.status == SignalStatus.CANCELLED.value
        assert yozuv.closed_at is not None


async def test_bekor_qilinganda_obunachiga_xabar_boradi(db: Database) -> None:
    signal_id = await _signal_yarat(db, "BTC")
    await _obunachi_yarat(db, telegram_id=555)

    bot = SoxtaBot()
    watcher = _watcher(bot, db, SoxtaStream([]))
    await watcher.restore_from_database()
    await watcher.cancel_signal(signal_id, "Admin bekor qildi")

    assert [chat_id for chat_id, _ in bot.messages] == [555]
    assert "⛔" in bot.messages[0][1]


async def test_yopilgan_signal_qayta_bekor_qilinmaydi(db: Database) -> None:
    signal_id = await _signal_yarat(db, "BTC")
    async with db.session() as session:
        await SignalRepository(session).apply_event(
            signal_id, SignalStatus.TP2_HIT, 105.0, BOSH, "tp2_hit"
        )

    watcher = _watcher(SoxtaBot(), db, SoxtaStream([]))
    assert await watcher.cancel_signal(signal_id, "kech") is None

    async with db.session() as session:
        yozuv = await SignalRepository(session).get(signal_id)
        assert yozuv.status == SignalStatus.TP2_HIT.value, "natija o'zgarmasligi kerak"


async def test_mavjud_bolmagan_signal_none_qaytaradi(db: Database) -> None:
    watcher = _watcher(SoxtaBot(), db, SoxtaStream([]))
    assert await watcher.cancel_signal(999, "yo'q") is None


async def test_kuzatuvda_bolmagan_signal_ham_bekor_qilinadi(db: Database) -> None:
    """`restore_from_database()` chaqirilmagan bo'lsa ham baza yangilanadi."""
    signal_id = await _signal_yarat(db, "BTC")
    await _obunachi_yarat(db)

    watcher = _watcher(SoxtaBot(), db, SoxtaStream([]))
    assert await watcher.cancel_signal(signal_id, "Admin bekor qildi") == "BTC"

    async with db.session() as session:
        yozuv = await SignalRepository(session).get(signal_id)
        assert yozuv.status == SignalStatus.CANCELLED.value


async def test_bekor_qilinganda_ochiq_pozitsiya_yopiladi(db: Database) -> None:
    """5.4-band: "Men sotib oldim" degan foydalanuvchi natijasiz qolmasin."""
    signal_id = await _signal_yarat(db, "BTC", entry=100.0)
    await _obunachi_yarat(db, telegram_id=555)

    async with db.session() as session:
        user = await UserRepository(session).get_by_telegram_id(555)
        await UserPositionRepository(session).record_entry(
            user_id=user.id, signal_id=signal_id, amount_usd=200.0, entry_price=100.0
        )

    bot = SoxtaBot()
    watcher = _watcher(bot, db, SoxtaStream([]))
    await watcher.restore_from_database()
    watcher.prices.update(PriceTick("BTC", 102.0, BOSH))

    await watcher.cancel_signal(signal_id, "Admin bekor qildi")

    async with db.session() as session:
        user = await UserRepository(session).get_by_telegram_id(555)
        ochiqlar = await UserPositionRepository(session).open_for_signal(signal_id)
        assert ochiqlar == [], "pozitsiya ochiq qolmasligi kerak"

    assert any("+2.00%" in matn for _, matn in bot.messages), (
        "yopilish narxi bozordagi joriy narx bo'lishi kerak"
    )


async def test_kuzatuvda_yoq_signal_qoshiladi(db: Database) -> None:
    """Veb-panelda yaratilgan signal botga shu yo'l bilan yetib boradi.

    `add_signal()` — jarayon ICHIDAGI chaqiruv. Signal boshqa jarayonda
    (saytda) yaratilsa, bot u haqda hech narsa bilmaydi va signal bazada
    "ochiq" bo'lib turadi-yu, narxi kuzatilmaydi.
    """
    await _signal_yarat(db, "BTC")

    stream = SoxtaStream([])
    watcher = _watcher(SoxtaBot(), db, stream)
    await watcher.restore_from_database()
    assert stream.subscribed == {"BTC"}

    # Sayt yangi signal yozdi — bot bu haqda bilmaydi
    await _signal_yarat(db, "ETH", entry=50)
    assert stream.subscribed == {"BTC"}, "hali kuzatuvda bo'lmasligi kerak"

    soni = await watcher.sync_untracked()

    assert soni == 1, "faqat YANGI signal qo'shilishi kerak"
    assert stream.subscribed == {"BTC", "ETH"}


async def test_sinxronlash_tanish_signalni_qayta_yuklamaydi(db: Database) -> None:
    """Xotiradagi holat bazadagidan yangiroq bo'lishi mumkin — masalan
    narx endigina TP ga tegib, hodisa hali yozilmagan bo'lsa."""
    await _signal_yarat(db, "BTC")

    watcher = _watcher(SoxtaBot(), db, SoxtaStream([]))
    await watcher.restore_from_database()

    assert await watcher.sync_untracked() == 0
    assert await watcher.sync_untracked() == 0, "takroriy chaqiruv ham xavfsiz"
