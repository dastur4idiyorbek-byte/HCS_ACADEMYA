"""Backtest uchun tarixiy sham yuklash va keshlash.

BU — FREYMVORK QISMI, strategiyadan mustaqil. 2026-09-03 da eski tahlil
moduli olib tashlanganda `scripts/backtest.py` ham ketdi; ma'lumot
yuklash mantig'i esa yangi modul uchun ham kerak bo'lgani uchun shu
faylga ko'chirildi.

Eski nusxadan farqi: timeframelar ro'yxati va isinish kunlari endi
CHAQIRUVCHIDAN keladi. Ilgari ular `config.analysis` dan o'qilardi —
ya'ni yuklovchi tahlil moduliga bog'langan edi.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.backtest.dataset import Dataset
from core.config.schema import AppConfig
from core.domain.models import Candle
from core.market_data.binance import BinanceCandleProvider
from core.utils.logging_setup import get_logger
from core.utils.time_utils import TIMEFRAME_MINUTES

logger = get_logger(__name__)

KESH = Path("data/candles")


class KeshYetishmaydi(RuntimeError):
    """`offline` rejimida kerakli kesh fayllari topilmadi."""


def kesh_yoli(symbol: str, timeframe: str, until: str | None = None) -> Path:
    """Kesh fayli yo'li.

    OYNA NOMGA KIRADI. Aks holda 2025-yilgi oyna uchun yuklangan
    shamlar 2026-yilgi yugurishda jimgina qayta ishlatilardi va ikkita
    "mustaqil" o'lchov aslida BIR XIL ma'lumotda bo'lardi — ya'ni
    takroriy tekshiruvning butun ma'nosi yo'qolardi.
    """
    oyna = f"_{until}" if until else ""
    return KESH / f"{symbol}_{timeframe}{oyna}.json"


def keshdan_oqish(symbol: str, timeframe: str, until: str | None = None) -> list[Candle] | None:
    yol = kesh_yoli(symbol, timeframe, until)
    if not yol.exists():
        return None
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


def keshga_yozish(
    symbol: str, timeframe: str, candles: list[Candle], until: str | None = None
) -> None:
    KESH.mkdir(parents=True, exist_ok=True)
    kesh_yoli(symbol, timeframe, until).write_text(
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


def keshdan_yigish(
    symbols: list[str], timeframes: list[str], until: str | None = None
) -> Dataset:
    """Tarmoqqa chiqmasdan, faqat keshdan to'plam quradi."""
    dataset = Dataset()
    for symbol in symbols:
        for tf in timeframes:
            shamlar = keshdan_oqish(symbol, tf, until)
            if shamlar is None:
                raise KeshYetishmaydi(f"kesh yo'q: {symbol} {tf}")
            dataset.add(symbol, tf, shamlar)
    return dataset


async def yukla(
    config: AppConfig,
    symbols: list[str],
    timeframes: list[str],
    days: int,
    *,
    warmup_days: int = 0,
    refresh: bool = False,
    offline: bool = False,
    until: datetime | None = None,
) -> Dataset:
    """Berilgan timeframelarni yuklaydi (yoki keshdan oladi).

    `days` — TAHLIL QILINADIGAN kunlar. `warmup_days` ustiga qo'shiladi:
    isinish qismi tahlil qilinmaydi, u faqat indikatorlarni to'ldiradi.
    Ansiz uzun timeframelar sinovning yarmigacha bo'sh turardi.

    `until` — sinov oynasining OXIRI. Berilmasa eng so'nggi ma'lumot.
    """
    oyna = until.date().isoformat() if until is not None else None
    if offline:
        return keshdan_yigish(symbols, timeframes, oyna)

    provider = BinanceCandleProvider(config.market_data, config.halal_screening.quote_asset)
    dataset = Dataset()
    jami_kun = days + warmup_days

    try:
        for symbol in symbols:
            for tf in timeframes:
                # Provayder 1000 dan ortig'ini SAHIFALAB yuklaydi.
                kerak = max(1, int(jami_kun * 1440 / TIMEFRAME_MINUTES.get(tf, 15)))
                shamlar = None if refresh else keshdan_oqish(symbol, tf, oyna)
                if shamlar is not None and len(shamlar) < kerak:
                    # Kesh eski, KALTA so'rov bilan yig'ilgan. Uni jimgina
                    # ishlatish backtestni isinishsiz qoldirardi.
                    logger.info(
                        "Kesh kalta: %s %s — %d sham bor, %d kerak, qayta yuklanadi",
                        symbol, tf, len(shamlar), kerak,
                    )
                    shamlar = None
                if shamlar is None:
                    logger.info("Yuklanmoqda: %s %s (%d sham)", symbol, tf, kerak)
                    shamlar = await provider.fetch_candles(symbol, tf, kerak, until)
                    keshga_yozish(symbol, tf, shamlar, oyna)
                dataset.add(symbol, tf, shamlar)
    finally:
        await provider.close()

    return dataset
