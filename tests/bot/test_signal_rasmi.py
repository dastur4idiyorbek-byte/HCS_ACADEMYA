"""Signal rasmini tarqatish — rasm bilan VA rasmsiz.

Bu yerdagi asosiy xavf jimgina yuzaga keladi: rasm qo'shilgach yuborish
yo'li `send_message` dan `send_photo` ga o'tdi. Agar Telegram rasmni rad
etsa (o'lcham, format, tarmoq), obunachi HECH NARSA olmay qolardi —
signal yo'qolardi, log esa faqat "yetkazilmadi" derdi.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bot.services.broadcast import broadcast_signal, signal_grafigi
from core.config.loader import load_config
from core.domain.enums import OrderType
from core.domain.models import EntryPlan, SignalLevels

DARAJALAR = SignalLevels(entry=100.0, stop=97.0, tp1=106.0, tp2=112.0)
REJA = EntryPlan(
    order_type=OrderType.LIMIT,
    entry_price=100.0,
    current_price=101.0,
    distance_pct=1.0,
    reason="sinov",
)


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


class BotRasmBilan:
    """Rasmni qabul qiladigan bot."""

    def __init__(self) -> None:
        self.photos: list[tuple[int, object, str]] = []
        self.messages: list[tuple[int, str]] = []

    async def send_photo(self, chat_id: int, photo, caption: str = "", **_: object):  # noqa: ANN001, ANN201
        self.photos.append((chat_id, photo, caption))
        return SimpleNamespace(photo=[SimpleNamespace(file_id="TG-RASM")])

    async def send_message(self, chat_id: int, text: str, **_: object) -> None:
        self.messages.append((chat_id, text))


class BotRasmniRadEtadi(BotRasmBilan):
    async def send_photo(self, *_: object, **__: object):  # noqa: ANN201
        raise RuntimeError("Telegram rasmni rad etdi")


QABUL = [(111, 1000.0), (222, 500.0), (333, None)]


async def test_rasm_bilan_yuboriladi(config) -> None:  # noqa: ANN001
    bot = BotRasmBilan()
    soni = await broadcast_signal(
        bot, QABUL, "BTC", DARAJALAR, REJA, 1, config, chart=b"soxta-png",
    )
    assert soni == 3
    assert len(bot.photos) == 3
    assert not bot.messages, "rasm ketgan bo'lsa matn takrorlanmasligi kerak"
    # Kartochka sarlavha sifatida ketadi — narxlar rasm bilan birga.
    assert "BTC/USDT" in bot.photos[0][2]


async def test_rasm_bir_marta_yuklanadi(config) -> None:  # noqa: ANN001
    """Ikkinchi va keyingi obunachilarga `file_id` ketadi.

    Aks holda bir xil rasm har bir obunachi uchun qaytadan yuklanardi —
    yuzta obunachida yuz marta.
    """
    bot = BotRasmBilan()
    await broadcast_signal(
        bot, QABUL, "BTC", DARAJALAR, REJA, 1, config, chart=b"soxta-png",
    )
    assert bot.photos[0][1] != "TG-RASM", "birinchisi — haqiqiy fayl"
    assert bot.photos[1][1] == "TG-RASM"
    assert bot.photos[2][1] == "TG-RASM"


async def test_rasm_yiqilsa_signal_matn_bilan_ketadi(config) -> None:  # noqa: ANN001
    """ENG MUHIM: rasm — qulaylik, signal — mahsulot."""
    bot = BotRasmniRadEtadi()
    soni = await broadcast_signal(
        bot, QABUL, "BTC", DARAJALAR, REJA, 1, config, chart=b"soxta-png",
    )
    assert soni == 3, "hamma obunachi signalni olishi kerak"
    assert len(bot.messages) == 3
    assert "BTC/USDT" in bot.messages[0][1]


async def test_rasmsiz_avvalgidek_ishlaydi(config) -> None:  # noqa: ANN001
    bot = BotRasmBilan()
    soni = await broadcast_signal(bot, QABUL, "BTC", DARAJALAR, REJA, 1, config)
    assert soni == 3
    assert len(bot.messages) == 3
    assert not bot.photos


# --------------------------------------------------------------------------- #
#  Grafik chizish — hech qachon istisno tashlamaydi
# --------------------------------------------------------------------------- #


class ShamlarYiqiladi:
    async def fetch_candles(self, *_: object, **__: object):  # noqa: ANN201
        raise ConnectionError("Binance javob bermadi")


class ShamlarBosh:
    async def fetch_candles(self, *_: object, **__: object) -> list:
        return []


async def test_shamlar_olinmasa_none(config) -> None:  # noqa: ANN001
    """Binance yiqilsa signal MATN bo'lib ketishi kerak, yo'qolmasligi."""
    assert await signal_grafigi(ShamlarYiqiladi(), "BTC", DARAJALAR, config) is None
    assert await signal_grafigi(ShamlarBosh(), "BTC", DARAJALAR, config) is None
    assert await signal_grafigi(None, "BTC", DARAJALAR, config) is None
