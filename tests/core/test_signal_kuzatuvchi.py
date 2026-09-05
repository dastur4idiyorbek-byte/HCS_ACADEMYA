"""Signal kuzatuvchisi — narxni kuzatib holatni yangilaydi.

Bu kod REAL PUL bilan bog'liq: u savdo qachon ochilgani, TP olingani
va Stop urilganini qayd etadi. Statistika ham, "Mening natijam" ham
shu yozuvlardan chiqadi.

Uchta narsa kafolatlanishi kerak:

  1. Kutayotgan limit narx TUSHGANDA faollashadi, TP ga
     KIRILMASDAN yetganda BEKOR bo'ladi (loyiha egasining qoidasi).
  2. Bitta sham ichida ham TP, ham Stop bo'lsa — STOP (backtest
     bilan bir xil ehtiyotkor taxmin).
  3. Bitta signaldagi xato qolganlarini to'xtatmaydi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.config.loader import load_config
from core.domain.enums import SignalStatus
from core.domain.models import Candle
from core.services.signal_kuzatuvchi import SignalKuzatuvchi

BOSH = datetime(2026, 9, 1, tzinfo=UTC)


def sham(low: float, high: float, close: float | None = None, siljish: int = 0) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(minutes=15 * siljish),
        open=(low + high) / 2,
        high=high,
        low=low,
        close=close if close is not None else (low + high) / 2,
        volume=100.0,
    )


class SoxtaYozuv:
    """`SignalRecord` o'rniga — bazasiz sinash uchun."""

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        self.id = kwargs.get("id", 1)
        self.symbol = kwargs.get("symbol", "LTC")
        self.status = kwargs.get("status", SignalStatus.PENDING.value)
        self.entry = kwargs.get("entry", 49.02)
        self.stop = kwargs.get("stop", 47.99)
        self.tp1 = kwargs.get("tp1", 52.78)
        self.tp2 = kwargs.get("tp2", 54.70)
        self.tp3 = kwargs.get("tp3")
        self.tp1_reached = kwargs.get("tp1_reached", False)
        self.reached_tps = kwargs.get("reached_tps", 0)
        self.created_at = kwargs.get("created_at", BOSH)
        self.activated_at = kwargs.get("activated_at")


class SoxtaProvayder:
    def __init__(self, shamlar: list[Candle]) -> None:
        self._shamlar = shamlar

    async def fetch_candles(self, symbol, timeframe, limit, until=None):  # noqa: ANN001, ANN201
        return self._shamlar


class SoxtaSessiya:
    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *_):  # noqa: ANN002, ANN204
        return False


class SoxtaBaza:
    def session(self):  # noqa: ANN201
        return SoxtaSessiya()


def kuzatuvchi(shamlar: list[Candle]) -> SignalKuzatuvchi:
    return SignalKuzatuvchi(load_config(), SoxtaProvayder(shamlar), SoxtaBaza())


async def natijani_ol(k: SignalKuzatuvchi, yozuv) -> tuple:  # noqa: ANN001
    """`_bitta_signal` ni yozuvsiz chaqiradi va yozilgan holatni tutadi."""
    tutilgan = []

    async def yozishni_kuzat(y, holat, natija):  # noqa: ANN001, ANN202
        tutilgan.append(holat)

    k._yoz = yozishni_kuzat  # type: ignore[method-assign]

    from core.services.signal_kuzatuvchi import KuzatuvNatijasi

    await k._bitta_signal(yozuv, KuzatuvNatijasi())
    return tutilgan[0] if tutilgan else None


# --------------------------------------------------------------------- #
#  Kutayotgan limit
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_narx_limitga_tushsa_FAOL_boladi() -> None:
    holat = await natijani_ol(
        kuzatuvchi([sham(48.5, 50.0)]), SoxtaYozuv()
    )
    assert holat is not None
    assert holat.status is SignalStatus.ACTIVE


@pytest.mark.asyncio
async def test_limitga_KELMASDAN_TP1_ga_yetsa_BEKOR() -> None:
    """2026-09-05, LTC: narx 49.02 ga tushmay 52.78 ga chiqdi.

    Bu savdo UMUMAN BO'LMAGAN. Uni "foydali" deb ko'rsatish yolg'on,
    "kutilmoqda" deb qoldirish esa chalg'ituvchi bo'lardi — sahifada
    hech qachon bajarilmaydigan buyurtma abadiy turardi.
    """
    holat = await natijani_ol(
        kuzatuvchi([sham(49.5, 53.0)]), SoxtaYozuv()
    )
    assert holat is not None
    assert holat.status is SignalStatus.CANCELLED
    assert "kirilmasdan" in holat.sabab


@pytest.mark.asyncio
async def test_bir_shamda_LIMIT_ham_TP_ham_bolsa_LIMIT_ustun() -> None:
    """Narx entry'ga tushgan bo'lsa, savdo OCHILGAN — bekor emas."""
    holat = await natijani_ol(
        kuzatuvchi([sham(48.0, 53.0)]), SoxtaYozuv()
    )
    assert holat is not None
    assert holat.status is not SignalStatus.CANCELLED


@pytest.mark.asyncio
async def test_narx_tegmasa_holat_OZGARMAYDI() -> None:
    holat = await natijani_ol(
        kuzatuvchi([sham(49.5, 51.0)]), SoxtaYozuv()
    )
    assert holat is None, "sababsiz holat o'zgardi"


# --------------------------------------------------------------------- #
#  Ochiq savdo — backtest bilan BIR XIL tartib
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_bir_shamda_TP_ham_STOP_ham_bolsa_STOP() -> None:
    """Ehtiyotkor taxmin — `zanjir_engine._yangila()` bilan bir xil.

    Qaysi biri oldin bo'lganini sham ma'lumotidan BILIB BO'LMAYDI.
    TP ni tanlash natijani chiroyliroq ko'rsatardi va bu — o'zini
    aldash.
    """
    yozuv = SoxtaYozuv(status=SignalStatus.ACTIVE.value, activated_at=BOSH)
    holat = await natijani_ol(kuzatuvchi([sham(47.0, 53.0)]), yozuv)

    assert holat is not None
    assert holat.status is SignalStatus.STOPPED


@pytest.mark.asyncio
async def test_TP1_olingach_stop_BREAKEVENGA_kochadi() -> None:
    yozuv = SoxtaYozuv(status=SignalStatus.ACTIVE.value, activated_at=BOSH)
    k = kuzatuvchi([sham(49.5, 53.0, siljish=0), sham(48.5, 49.6, siljish=1)])
    holat = await natijani_ol(k, yozuv)

    assert holat is not None
    # Ikkinchi sham 48.5 gacha tushdi — eski stop (47.99) urilmasdi,
    # lekin TP1 dan keyingi breakeven (49.02) uriladi.
    assert holat.status is SignalStatus.STOPPED
    assert holat.narx == pytest.approx(49.02)


@pytest.mark.asyncio
async def test_hamma_TP_olinsa_signal_YOPILADI() -> None:
    yozuv = SoxtaYozuv(status=SignalStatus.ACTIVE.value, activated_at=BOSH)
    holat = await natijani_ol(kuzatuvchi([sham(49.5, 55.0)]), yozuv)

    assert holat is not None
    assert holat.status is SignalStatus.TP2_HIT
    assert holat.narx == pytest.approx(54.70)


@pytest.mark.asyncio
async def test_faqat_TP1_olinsa_signal_OCHIQ_qoladi() -> None:
    yozuv = SoxtaYozuv(status=SignalStatus.ACTIVE.value, activated_at=BOSH)
    holat = await natijani_ol(kuzatuvchi([sham(49.5, 53.0)]), yozuv)

    assert holat is not None
    assert holat.status is SignalStatus.TP1_HIT
    assert not holat.status.is_closed


@pytest.mark.asyncio
async def test_muddat_tugasa_bozorda_yopiladi() -> None:
    yozuv = SoxtaYozuv(status=SignalStatus.ACTIVE.value, activated_at=BOSH)
    config = load_config()
    kun = config.zanjir.chiqish.umumiy_muddat_kun
    kech = sham(49.5, 51.0, close=50.0, siljish=int(kun * 96) + 1)

    holat = await natijani_ol(kuzatuvchi([kech]), yozuv)

    assert holat is not None
    assert holat.status is SignalStatus.TIMED_OUT
    assert holat.narx == pytest.approx(50.0)


# --------------------------------------------------------------------- #
#  Chidamlilik
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_signal_boshlanishidan_OLDINGI_shamlar_hisobga_olinmaydi() -> None:
    """Signal berilishidan avvalgi harakat bu savdoga tegishli emas."""
    yozuv = SoxtaYozuv(created_at=BOSH + timedelta(hours=5))
    # Bu sham signal berilishidan OLDIN — TP ga tegsa ham sanalmaydi.
    holat = await natijani_ol(kuzatuvchi([sham(49.5, 53.0, siljish=0)]), yozuv)
    assert holat is None
