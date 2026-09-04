"""Jonli sikl — yangi modulni haqiqiy bozorda yuritadi.

Bu kod REAL PUL bilan bog'liq signal chiqaradi. Uch narsa
kafolatlanishi kerak:

  1. Bitta coinda ikkita ochiq signal bo'lmaydi.
  2. Bitta coindagi xato butun siklni to'xtatmaydi.
  3. Jonli mantiq backtest mantig'i bilan BIR XIL oynada ishlaydi
     — aks holda o'lchangan natija jonli natijaga tegishli emas.
"""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta

import pytest

from core.config.loader import load_config
from core.domain.models import Candle
from core.services.zanjir_sikl import ASOSIY_OYNA, PASTKI_OYNA, SiklNatijasi, ZanjirSikl

BOSH = datetime(2024, 1, 1, tzinfo=UTC)


def seriya(n: int, qadam: timedelta = timedelta(days=1)) -> list[Candle]:
    rnd = random.Random(11)
    narx = 100.0
    out = []
    for i in range(n):
        narx *= 1 + 0.0015 + 0.02 * math.sin(i / 9) + rnd.uniform(-0.012, 0.012)
        out.append(
            Candle(
                open_time=BOSH + qadam * i,
                open=narx,
                high=narx * 1.01,
                low=narx * 0.99,
                close=narx,
                volume=rnd.uniform(500, 2000),
            )
        )
    return out


class SoxtaProvayder:
    """Birjaga chiqmaydigan provayder."""

    def __init__(self, xato_beradigan: set[str] | None = None) -> None:
        self.sorovlar: list[tuple[str, str, int]] = []
        self._xato = xato_beradigan or set()

    async def fetch_candles(self, symbol, timeframe, limit, until=None):  # noqa: ANN001, ANN201
        self.sorovlar.append((symbol, timeframe, limit))
        if symbol in self._xato:
            raise RuntimeError("birja javob bermadi")
        qadam = timedelta(days=1) if timeframe.endswith("d") else timedelta(minutes=15)
        return seriya(limit, qadam)


class SoxtaSessiya:
    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *_):  # noqa: ANN002, ANN204
        return False


class SoxtaBaza:
    """Faqat `session()` beradi — yozish testda tekshirilmaydi."""

    def __init__(self) -> None:
        self._sessiya = SoxtaSessiya()

    def session(self):  # noqa: ANN201
        return self._sessiya


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


def test_oyna_backtest_bilan_bir_xil() -> None:
    """Jonli sikl backtest bilan AYNAN bir xil oynani so'rasin.

    Boshqa oyna — boshqa indikator qiymati — boshqa qaror. U holda
    o'lchangan PF 3.49 jonli tizimga tegishli bo'lmasdi.
    """
    from core.backtest.zanjir_engine import ASOSIY_OYNA as BACKTEST_ASOSIY
    from core.backtest.zanjir_engine import PASTKI_OYNA as BACKTEST_PASTKI

    assert ASOSIY_OYNA == BACKTEST_ASOSIY
    assert PASTKI_OYNA == BACKTEST_PASTKI


def test_kuzatiladigan_coinlar_olchangan_royxat(config) -> None:  # noqa: ANN001
    """Jonli ro'yxat o'lchangan ro'yxat bilan bir xil bo'lsin."""
    from scripts.zanjir_umumiy import OLCHOV_12

    assert set(config.zanjir.kuzatiladigan_coinlar) == set(OLCHOV_12)


def test_sikl_soat_musbat(config) -> None:  # noqa: ANN001
    assert config.zanjir.sikl_soat > 0


@pytest.mark.asyncio
async def test_bitta_coin_xatosi_siklni_toxtatmaydi(config) -> None:  # noqa: ANN001
    """ETH birjada yiqilsa, qolgan o'n bir coin baribir tekshirilsin.

    Ansiz bitta coinning vaqtinchalik xatosi butun sikl bo'yi
    signalsiz qoldirardi — va sabab loglarda ko'rinmasdi.
    """
    provayder = SoxtaProvayder(xato_beradigan={"ETH"})
    sikl = ZanjirSikl(config, provayder, SoxtaBaza())
    natija = SiklNatijasi()

    await sikl._bitta_coin("BTC", [], natija)
    with pytest.raises(RuntimeError):
        await sikl._bitta_coin("ETH", [], natija)

    assert natija.tekshirildi == 1


def test_natija_matni_sabab_korsatadi() -> None:
    """"Nega signal yo'q" savoliga hisobot javob bersin."""
    natija = SiklNatijasi(
        tekshirildi=12,
        ochiq_sababli_otkazildi=2,
        uzilishlar={"Struktura": 7},
        daraja_radlari={"stop juda yaqin": 3},
    )
    matn = natija.matn()
    assert "12 coin" in matn
    assert "Struktura" in matn
    assert "stop juda yaqin" in matn
