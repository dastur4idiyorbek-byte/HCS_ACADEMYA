"""6.3-band: backtestni ishga tushirish.

Ishlatish:
    python -m scripts.backtest                  # standart sozlama
    python -m scripts.backtest --compare        # ochiq savollarni taqqoslash
    python -m scripts.backtest --days 730       # 2 yillik ma'lumot
    python -m scripts.backtest --symbols BTC,ETH,SOL

Ma'lumot Binance public REST orqali yuklanadi (kalitsiz) va `data/candles/`
ga keshlanadi — takroriy ishga tushirishda qayta yuklanmaydi.

TAQQOSLASH REJIMI eng qimmatli qism. U qurish jarayonida ochiq qolgan
uchta savolga RAQAM bilan javob beradi:

    1. Qat'iy EMA talabimi yoki yumshoq?  (docs/ARXITEKTURA.md 20-bo'lim)
    2. Nechta indikator tasdig'i kerak?    (21.3-bo'lim)
    3. O'lchangan TP foydalimi?            (21.1-bo'lim)
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
from pathlib import Path

from core.backtest import Backtester, Dataset, compare, render
from core.config import AppConfig, load_config
from core.domain.models import Candle
from core.market_data import BinanceCandleProvider
from core.utils.logging_setup import get_logger, setup_logging

logger = get_logger(__name__)

KESH = Path("data/candles")
STANDART_COINLAR = ["BTC", "ETH", "SOL", "BNB", "XRP"]


# --------------------------------------------------------------------------- #
#  Ma'lumot yuklash va keshlash
# --------------------------------------------------------------------------- #


def _kesh_yoli(symbol: str, timeframe: str) -> Path:
    return KESH / f"{symbol}_{timeframe}.json"


def _keshdan_oqish(symbol: str, timeframe: str) -> list[Candle] | None:
    yol = _kesh_yoli(symbol, timeframe)
    if not yol.exists():
        return None
    from datetime import datetime

    xom = json.loads(yol.read_text(encoding="utf-8"))
    return [
        Candle(
            open_time=datetime.fromisoformat(q["t"]),
            open=q["o"],
            high=q["h"],
            low=q["l"],
            close=q["c"],
            volume=q["v"],
        )
        for q in xom
    ]


def _keshga_yozish(symbol: str, timeframe: str, candles: list[Candle]) -> None:
    KESH.mkdir(parents=True, exist_ok=True)
    _kesh_yoli(symbol, timeframe).write_text(
        json.dumps(
            [
                {
                    "t": c.open_time.isoformat(),
                    "o": c.open,
                    "h": c.high,
                    "l": c.low,
                    "c": c.close,
                    "v": c.volume,
                }
                for c in candles
            ]
        ),
        encoding="utf-8",
    )


async def _yukla(
    config: AppConfig, symbols: list[str], days: int, refresh: bool
) -> Dataset:
    """Kerakli barcha timeframelarni yuklaydi (yoki keshdan oladi)."""
    from core.analysis.strategies import build_strategies, required_timeframes

    timeframelar = sorted(required_timeframes(build_strategies(config)))
    provider = BinanceCandleProvider(config.market_data, config.halal_screening.quote_asset)
    dataset = Dataset()

    # Binance bir so'rovda 1000 sham beradi — kerakli sonini hisoblaymiz
    daqiqalar = {"15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}

    try:
        for symbol in symbols:
            for tf in timeframelar:
                shamlar = None if refresh else _keshdan_oqish(symbol, tf)
                if shamlar is None:
                    kerak = min(1000, int(days * 1440 / daqiqalar.get(tf, 15)))
                    logger.info("Yuklanmoqda: %s %s (%d sham)", symbol, tf, kerak)
                    shamlar = await provider.fetch_candles(symbol, tf, kerak)
                    _keshga_yozish(symbol, tf, shamlar)
                dataset.add(symbol, tf, shamlar)
    finally:
        await provider.close()

    return dataset


# --------------------------------------------------------------------------- #
#  Taqqoslanadigan konfiguratsiyalar
# --------------------------------------------------------------------------- #


def _variantlar(asos: AppConfig) -> list[tuple[str, AppConfig]]:
    """Qurish jarayonida ochiq qolgan savollarni variantlarga aylantiradi."""

    def bilan(nom: str, **indikator_ozgarishlari) -> tuple[str, AppConfig]:
        ind = dataclasses.replace(asos.analysis.indicators, **indikator_ozgarishlari)
        return nom, dataclasses.replace(
            asos, analysis=dataclasses.replace(asos.analysis, indicators=ind)
        )

    tuzilmaviy_tp = dataclasses.replace(asos.trade_rules, allow_measured_tp=False)

    return [
        ("standart", asos),
        bilan("EMA qat'iy", trend_requires_price_above_fast=True),
        bilan("EMA yumshoq", trend_requires_price_above_fast=False),
        bilan("tasdiq 1/4", min_confirmations=1),
        bilan("tasdiq 3/4", min_confirmations=3),
        bilan("tasdiq 4/4 (qat'iy)", min_confirmations=4),
        (
            "faqat tuzilmaviy TP",
            dataclasses.replace(asos, trade_rules=tuzilmaviy_tp),
        ),
    ]


# --------------------------------------------------------------------------- #
#  Asosiy
# --------------------------------------------------------------------------- #


async def main() -> None:
    parser = argparse.ArgumentParser(description="HALOL CRYPTO SAVDO — backtest")
    parser.add_argument("--symbols", default=",".join(STANDART_COINLAR))
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--compare", action="store_true", help="variantlarni taqqoslash")
    parser.add_argument("--refresh", action="store_true", help="keshni yangilash")
    parser.add_argument("--max-steps", type=int, default=None)
    argumentlar = parser.parse_args()

    setup_logging(level="INFO")
    config = load_config()
    coinlar = [s.strip().upper() for s in argumentlar.symbols.split(",") if s.strip()]

    print(f"Ma'lumot tayyorlanmoqda: {', '.join(coinlar)} ({argumentlar.days} kun)\n")
    dataset = await _yukla(config, coinlar, argumentlar.days, argumentlar.refresh)

    qadamlar = len(dataset.timeline(config.analysis.entry_timeframe))
    print(f"Yuklandi: {len(dataset.symbols)} coin, {qadamlar:,} qadam\n")

    if not argumentlar.compare:
        natija = Backtester(config).run(dataset, max_steps=argumentlar.max_steps)
        print(render(natija))
        return

    natijalar = []
    for nom, variant in _variantlar(config):
        print(f"  ishlamoqda: {nom} ...")
        natijalar.append(
            Backtester(variant, label=nom).run(dataset, max_steps=argumentlar.max_steps)
        )

    print()
    print(compare(natijalar))
    print()
    for natija in natijalar:
        if natija.closed:
            print(render(natija))
            print()


if __name__ == "__main__":
    asyncio.run(main())
