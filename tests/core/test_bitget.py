"""Bitget mijozi va ikki birja narxini solishtirish (2-prompt, 1-bosqich)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.config.schema import MarketDataConfig
from core.domain.models import Candle
from core.market_data.bitget import (
    BITGET_MAX_KLINES,
    BitgetCandleProvider,
    to_bitget_symbol,
)
from core.market_data.price_reconciliation import (
    qamrov_pct,
    shubhali_vaqtlar,
    solishtir,
)

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(ofset: int, *, high: float = 110, low: float = 90, close: float = 100) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(days=ofset),
        open=100.0,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
    )


# --------------------------------------------------------------------------- #
#  Juftlik nomi
# --------------------------------------------------------------------------- #


def test_juftlik_katta_harf() -> None:
    """Bitget kichik harfni QABUL QILMAYDI — Binance'dan asosiy farq."""
    assert to_bitget_symbol("btc") == "BTCUSDT"
    assert to_bitget_symbol("BTC") == "BTCUSDT"


def test_juftlik_ikki_marta_qoshilmaydi() -> None:
    assert to_bitget_symbol("BTCUSDT") == "BTCUSDT"


# --------------------------------------------------------------------------- #
#  Sahifalash — soxta sessiya bilan
# --------------------------------------------------------------------------- #


class SoxtaJavob:
    def __init__(self, xom: dict) -> None:
        self._xom = xom

    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> dict:
        return self._xom


class SoxtaSessiya:
    """Har chaqiruvda navbatdagi javobni beradi va so'rovlarni yozib boradi."""

    closed = False

    def __init__(self, javoblar: list[dict]) -> None:
        self._javoblar = list(javoblar)
        self.sorovlar: list[dict] = []

    def get(self, url: str, params: dict):  # noqa: ANN201
        self.sorovlar.append(dict(params))
        return SoxtaJavob(self._javoblar.pop(0) if self._javoblar else {"code": "00000", "data": []})


def qator(ofset: int) -> list[str]:
    vaqt = int((BOSH + timedelta(days=ofset)).timestamp() * 1000)
    return [str(vaqt), "100", "110", "90", "105", "1000"]


def provayder(javoblar: list[dict]) -> tuple[BitgetCandleProvider, SoxtaSessiya]:
    config = MarketDataConfig(candle_page_pause_seconds=0.0)
    p = BitgetCandleProvider(config)
    sessiya = SoxtaSessiya(javoblar)
    p._get_session = lambda: _tayyor(sessiya)  # type: ignore[method-assign]
    return p, sessiya


async def _tayyor(qiymat):  # noqa: ANN001, ANN202
    return qiymat


@pytest.mark.asyncio
async def test_shamlar_oqiladi() -> None:
    p, _ = provayder([{"code": "00000", "data": [qator(0), qator(1)]}])
    natija = await p.fetch_candles("BTC", "1d", 2)
    assert len(natija) == 2
    assert natija[0].open_time == BOSH
    assert natija[0].high == 110.0


@pytest.mark.asyncio
async def test_xato_kodi_bosh_royxat_qaytaradi() -> None:
    """Bitget xatoda ham HTTP 200 beradi — `raise_for_status()` ushlamaydi.

    Bu tekshiruvsiz xato javob JIMGINA "shamlar yo'q" bo'lib o'qilardi
    va coin "ma'lumot yo'q" deb chetlab o'tilardi.
    """
    p, _ = provayder([{"code": "40034", "msg": "Parameter does not exist"}])
    assert await p.fetch_candles("YOQ", "1d", 10) == []


@pytest.mark.asyncio
async def test_qisqa_sahifa_tarix_tugadi_deb_oqiladi() -> None:
    """So'ralganidan kam sham kelsa — coin bunchalik eski emas.

    Ikkinchi so'rov YUBORILMAYDI. Ansiz tarixi qisqa har bir coin
    uchun bo'sh sahifa so'rab, cheksiz aylanish xavfi tug'ilardi.
    """
    p, sessiya = provayder([{"code": "00000", "data": [qator(0), qator(1)]}])

    natija = await p.fetch_candles("BTC", "1d", 100)

    assert len(sessiya.sorovlar) == 1
    assert len(natija) == 2


@pytest.mark.asyncio
async def test_sahifalab_yuklaydi(monkeypatch) -> None:  # noqa: ANN001
    """Bitta so'rov chegarasidan ko'p so'ralsa — bir necha so'rov ketadi."""
    monkeypatch.setattr("core.market_data.bitget.BITGET_MAX_KLINES", 2)
    birinchi = {"code": "00000", "data": [qator(1), qator(2)]}
    ikkinchi = {"code": "00000", "data": [qator(-1), qator(0)]}
    p, sessiya = provayder([birinchi, ikkinchi])

    natija = await p.fetch_candles("BTC", "1d", 4)

    assert len(sessiya.sorovlar) == 2
    assert len(natija) == 4
    # Vaqt bo'yicha o'sish tartibida, eski sahifa OLDINGA qo'yiladi
    assert [c.open_time for c in natija] == sorted(c.open_time for c in natija)


@pytest.mark.asyncio
async def test_ikkinchi_sahifa_endtime_bilan_soraydi(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("core.market_data.bitget.BITGET_MAX_KLINES", 1)
    p, sessiya = provayder([
        {"code": "00000", "data": [qator(5)]},
        {"code": "00000", "data": []},
    ])

    await p.fetch_candles("BTC", "1d", 3)

    assert "endTime" not in sessiya.sorovlar[0]
    kutilgan = int((BOSH + timedelta(days=5)).timestamp() * 1000) - 1
    assert sessiya.sorovlar[1]["endTime"] == kutilgan


@pytest.mark.asyncio
async def test_teskari_tartibdagi_javob_saralanadi(monkeypatch) -> None:  # noqa: ANN001
    """Bitget tartibi kafolat emas — noto'g'ri tartib sahifalashni buzardi."""
    monkeypatch.setattr("core.market_data.bitget.BITGET_MAX_KLINES", 3)
    p, sessiya = provayder([
        {"code": "00000", "data": [qator(3), qator(1), qator(2)]},
        {"code": "00000", "data": []},
    ])

    natija = await p.fetch_candles("BTC", "1d", 5)

    assert [c.open_time for c in natija] == sorted(c.open_time for c in natija)
    # `endTime` ENG ESKI shamdan hisoblanadi, javobdagi birinchisidan emas
    kutilgan = int((BOSH + timedelta(days=1)).timestamp() * 1000) - 1
    assert sessiya.sorovlar[1]["endTime"] == kutilgan


@pytest.mark.asyncio
async def test_nomalum_timeframe_xato_beradi() -> None:
    p, _ = provayder([])
    with pytest.raises(ValueError, match="timeframe"):
        await p.fetch_candles("BTC", "7m", 10)


@pytest.mark.asyncio
async def test_limit_chegarasi_hurmat_qilinadi() -> None:
    p, sessiya = provayder([{"code": "00000", "data": [qator(0)]}])
    await p.fetch_candles("BTC", "1d", 5000)
    assert sessiya.sorovlar[0]["limit"] == BITGET_MAX_KLINES


@pytest.mark.asyncio
async def test_tarixiy_sham_yopilgan_deb_belgilanadi() -> None:
    """Solishtirish uchun yopilmagan sham yaroqsiz — ikki birja turli soniya."""
    p, _ = provayder([{"code": "00000", "data": [qator(0)]}])
    natija = await p.fetch_candles("BTC", "1d", 1)
    assert natija[0].closed is True


# --------------------------------------------------------------------------- #
#  Narx solishtirish
# --------------------------------------------------------------------------- #


def test_bir_xil_shamlar_shubhali_emas() -> None:
    a = [sham(0), sham(1)]
    natija = solishtir(a, list(a))
    assert not shubhali_vaqtlar(natija)


def test_uzun_wick_shubhali() -> None:
    """Binance'da low 90, Bitget'da 99 — 10% ajralish, ya'ni yolg'on wick."""
    binance = [sham(0, low=90)]
    bitget = [sham(0, low=99)]

    natija = solishtir(binance, bitget, chegara_pct=1.0)

    assert natija[BOSH].shubhali
    assert "pastki uch" in natija[BOSH].sabab


def test_kichik_farq_shubhali_emas() -> None:
    """Arbitraj oynasi — tabiiy farq, anomaliya emas."""
    natija = solishtir([sham(0, low=100.0)], [sham(0, low=100.5)], chegara_pct=1.0)
    assert not natija[BOSH].shubhali


def test_chegara_aynan_teng_bolsa_otadi() -> None:
    """Chegarada turgan sham RAD ETILMAYDI — `>` ishlatiladi, `>=` emas."""
    natija = solishtir([sham(0, low=100.0)], [sham(0, low=101.0)], chegara_pct=1.0)
    assert not natija[BOSH].shubhali


def test_yuqori_uch_ham_tekshiriladi() -> None:
    natija = solishtir([sham(0, high=120)], [sham(0, high=110)], chegara_pct=1.0)
    assert natija[BOSH].shubhali
    assert "yuqori uch" in natija[BOSH].sabab


def test_juftlashmagan_sham_natijaga_kirmaydi() -> None:
    """Bitget'da yo'q sham — ma'lumot yo'qligi, tasdiq ham emas, rad ham emas."""
    natija = solishtir([sham(0), sham(1)], [sham(0)])
    assert set(natija) == {BOSH}


def test_qamrov_hisoblanadi() -> None:
    """Qamrov past bo'lsa filtr ishlamaydi — buni bilib turish kerak."""
    natija = solishtir([sham(i) for i in range(10)], [sham(0), sham(1)])
    assert qamrov_pct([sham(i) for i in range(10)], natija) == pytest.approx(20.0)


def test_bosh_qatorda_qamrov_nol() -> None:
    assert qamrov_pct([], {}) == 0.0


def test_nol_narx_bolinishni_buzmaydi() -> None:
    """Buzuq ma'lumot (narx 0) ZeroDivisionError bermasin (0.3-band)."""
    buzuq = Candle(open_time=BOSH, open=0, high=0, low=0, close=0, volume=0)
    natija = solishtir([buzuq], [sham(0)])
    assert not natija[BOSH].shubhali
