"""6.3-band: backtestni ishga tushirish.

Ishlatish:
    python -m scripts.backtest                  # standart sozlama
    python -m scripts.backtest --compare        # variantlarni taqqoslash
    python -m scripts.backtest --days 730       # 2 yillik ma'lumot
    python -m scripts.backtest --symbols BTC,ETH,SOL
    python -m scripts.backtest --offline        # faqat keshdan (tarmoqsiz)

Ma'lumot Binance public REST orqali yuklanadi (kalitsiz) va `data/candles/`
ga keshlanadi — takroriy ishga tushirishda qayta yuklanmaydi. Tarmoq
yopiq muhitda `--offline` bilan FAQAT kesh o'qiladi va yetishmayotgan
fayllar nomma-nom aytiladi.

TAQQOSLASH REJIMI eng qimmatli qism. Hozir u BITTA ochiq savolga —
`docs/ARXITEKTURA.md` 63-bo'limidagi savolga — raqam bilan javob beradi:

    Bozor Salomatligi past bo'lganda TO'XTAGAN yaxshimi (eski tizim),
    yoki tuzilmaviy kirish bilan DAVOM ETGAN (yangi tizim)?

Bu savol taxmin bilan yopilmasligi kerak edi: `correction_entry`
konfiguratsiyada ATAYIN o'chirilgan holda turibdi va aynan shu
taqqoslash natijasi uni yoqadi yoki yopiq qoldiradi.
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


class KeshYetishmaydi(RuntimeError):
    """`--offline` rejimida kerakli kesh fayllari topilmadi."""


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


def _kerakli_timeframelar(config: AppConfig) -> list[str]:
    """Taqqoslashdagi HAR BIR variant uchun kerak bo'ladigan timeframelar.

    `enabled_only=False` ataylab: `correction_entry` konfiguratsiyada
    o'chirilgan bo'lsa ham uning 4h/15m/1d ma'lumoti yuklanishi kerak,
    aks holda taqqoslashda yangi variant "ma'lumot yo'q" deb bo'sh
    natija berardi va biz uni "yomon strategiya" deb o'qib qo'yardik.
    """
    from core.analysis.strategies import build_strategies, required_timeframes

    return sorted(required_timeframes(build_strategies(config, enabled_only=False)))


def _keshdan_yigish(symbols: list[str], timeframelar: list[str]) -> Dataset:
    """Tarmoqqa umuman chiqmaydi. Yetishmagani aniq aytiladi."""
    dataset = Dataset()
    yoq: list[str] = []
    for symbol in symbols:
        for tf in timeframelar:
            shamlar = _keshdan_oqish(symbol, tf)
            if shamlar is None:
                yoq.append(str(_kesh_yoli(symbol, tf)))
                continue
            dataset.add(symbol, tf, shamlar)

    if yoq:
        royxat = "\n  ".join(yoq)
        raise KeshYetishmaydi(
            "Offline rejim: quyidagi kesh fayllari yo'q —\n  "
            f"{royxat}\n"
            "Ularni tarmoqli mashinada bir marta `python -m scripts.backtest` "
            "ishga tushirib yig'ing, so'ng `data/candles/` ni ko'chiring."
        )
    return dataset


async def _yukla(
    config: AppConfig,
    symbols: list[str],
    days: int,
    refresh: bool,
    offline: bool = False,
) -> Dataset:
    """Kerakli barcha timeframelarni yuklaydi (yoki keshdan oladi)."""
    timeframelar = _kerakli_timeframelar(config)

    if offline:
        return _keshdan_yigish(symbols, timeframelar)

    provider = BinanceCandleProvider(config.market_data, config.halal_screening.quote_asset)
    dataset = Dataset()

    # Necha sham kerakligi kunlardan hisoblanadi. Provayder 1000 dan
    # ortig'ini SAHIFALAB yuklaydi — ilgari bu yerda `min(1000, ...)`
    # turardi va `--days 730` 4 soatlik timeframeda jimgina ~166 kunga
    # aylanardi.
    daqiqalar = {"15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}

    try:
        for symbol in symbols:
            for tf in timeframelar:
                shamlar = None if refresh else _keshdan_oqish(symbol, tf)
                if shamlar is None:
                    kerak = max(1, int(days * 1440 / daqiqalar.get(tf, 15)))
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


def _korreksiya_bilan(
    asos: AppConfig, nom: str, **ozgarishlar: object
) -> tuple[str, AppConfig]:
    """`correction_entry` sozlamasi o'zgartirilgan nusxa."""
    ce = dataclasses.replace(asos.strategies.correction_entry, **ozgarishlar)
    return nom, dataclasses.replace(
        asos, strategies=dataclasses.replace(asos.strategies, correction_entry=ce)
    )


def _variantlar(asos: AppConfig) -> list[tuple[str, AppConfig]]:
    """Ochiq qolgan savolni variantlarga aylantiradi.

    ESKI TIZIM aynan `enabled=False` bilan ifodalanadi va bu — taqlid
    emas, haqiqiy eski xatti-harakat: past bandda `_for_regime()`
    bo'sh ro'yxat qaytaradi, sikl o'sha yerda to'xtaydi.

    Qolgan variantlar YANGI tizimning ikki sozlamasini o'lchaydi.
    Ularning boshlang'ich qiymatlari (`min_confluence=2`,
    `min_risk_reward=2.0`) metodikadan olingan taxmin edi — mana shu
    yerda ular raqam bilan tekshiriladi.
    """
    return [
        _korreksiya_bilan(asos, "eski: past bandda to'xtash", enabled=False),
        _korreksiya_bilan(asos, "yangi: Correction Entry", enabled=True),
        _korreksiya_bilan(asos, "CE: confluence 3", enabled=True, min_confluence=3),
        _korreksiya_bilan(asos, "CE: R/R 1.5", enabled=True, min_risk_reward=1.5),
        _korreksiya_bilan(asos, "CE: R/R 2.5", enabled=True, min_risk_reward=2.5),
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
    parser.add_argument(
        "--offline",
        action="store_true",
        help="tarmoqqa chiqmaslik — faqat data/candles/ dagi kesh",
    )
    parser.add_argument("--max-steps", type=int, default=None)
    argumentlar = parser.parse_args()

    setup_logging(level="INFO")
    config = load_config()
    coinlar = [s.strip().upper() for s in argumentlar.symbols.split(",") if s.strip()]

    print(f"Ma'lumot tayyorlanmoqda: {', '.join(coinlar)} ({argumentlar.days} kun)\n")
    try:
        dataset = await _yukla(
            config,
            coinlar,
            argumentlar.days,
            argumentlar.refresh,
            offline=argumentlar.offline,
        )
    except KeshYetishmaydi as xato:
        print(str(xato))
        raise SystemExit(1) from xato

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
