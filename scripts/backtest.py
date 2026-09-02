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

TAQQOSLASH REJIMI eng qimmatli qism. Hozir u BITTA ochiq savolga
raqam bilan javob beradi:

    TP2 ni FORMULADAN (stop x nisbat) emas, TUZILMADAN (keyingi
    resistance zonasi) olsak — natija yaxshilanadimi?

2026-09-02 backtesti asosiy tizim zarar ko'rsatayotganini aniqladi
va sababni ham ko'rsatdi: TP2 gacha savdolarning atigi 29.9% i
yetadi. Tuzilmaviy TP2 nisbatni pasaytiradi, lekin ehtimolni
oshiradi. Qaysi tomon og'irroq — taxmin qilinmaydi, o'lchanadi.
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
    """Backtest uchun kerak bo'ladigan BARCHA timeframelar.

    `enabled_only=False` ataylab: `correction_entry` konfiguratsiyada
    o'chirilgan bo'lsa ham uning 4h/15m/1d ma'lumoti yuklanishi kerak,
    aks holda taqqoslashda yangi variant "ma'lumot yo'q" deb bo'sh
    natija berardi va biz uni "yomon strategiya" deb o'qib qo'yardik.

    Strategiyalar so'raganiga BOZOR SALOMATLIGI timeframei ham
    qo'shiladi. U hech bir strategiyaning ro'yxatida yo'q — indeks
    strategiyadan tashqarida hisoblanadi — lekin aynan u rejimni
    tanlaydi. Yuklanmasa, backtest indeksni boshqa timeframedan
    o'lchardi va javob jonli tizimnikiga to'g'ri kelmasdi.
    """
    from core.analysis.strategies import build_strategies, required_timeframes

    kerakli = required_timeframes(build_strategies(config, enabled_only=False))
    kerakli.add(config.analysis.entry_timeframe)
    kerakli.add(config.analysis.market_health_timeframe)
    kerakli.update(config.analysis.htf_confirmation)
    return sorted(kerakli)


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


def _qoidalar_bilan(
    asos: AppConfig, nom: str, **ozgarishlar: object
) -> tuple[str, AppConfig]:
    """`trade_rules` sozlamasi o'zgartirilgan nusxa."""
    qoidalar = dataclasses.replace(asos.trade_rules, **ozgarishlar)
    return nom, dataclasses.replace(asos, trade_rules=qoidalar)


def _variantlar(asos: AppConfig) -> list[tuple[str, AppConfig]]:
    """Hozirgi ochiq savolni variantlarga aylantiradi.

    OLDINGI SAVOLGA JAVOB BERILDI (2026-09-02,
    `docs/BACKTEST_NATIJA_2026-09-02.md`): Correction Entry atigi 4 ta
    signal qo'shdi va natijani yomonlashtirdi. U `enabled: false`
    holatida qoldi, ya'ni endi o'lchaydigan narsa yo'q.

    O'SHA BACKTEST KATTAROQ MUAMMONI OCHDI: asosiy tizim ham zarar
    ko'rsatyapti (win-rate 37.9%, o'rtacha -0.43% har savdoda). Sabab
    kodda ochiq turibdi — TP1 haqiqiy resistance zonasidan olinadi,
    TP2 esa FORMULADAN. Natijada TP2 gacha savdolarning atigi 29.9%
    i yetadi.

    Yangi savol shu: TP2 ni TUZILMAGA qo'ysak, past nisbat evaziga
    yuqori ehtimol olamizmi?

    Nisbat variantlari ham shu yerda: tuzilmaviy TP2 nisbatni
    pasaytiradi, lekin qay darajaga qadar pasayishiga ruxsat berish
    kerakligi o'lchanmagan.
    """
    return [
        _qoidalar_bilan(asos, "eski: formulaviy TP2", tp2_from_structure=False),
        _qoidalar_bilan(asos, "yangi: tuzilmaviy TP2", tp2_from_structure=True),
        _qoidalar_bilan(
            asos,
            "tuzilmaviy, nisbat >= 1.5",
            tp2_from_structure=True,
            tp2_structural_min_rr=1.5,
        ),
        _qoidalar_bilan(
            asos,
            "tuzilmaviy, nisbat >= 2.0",
            tp2_from_structure=True,
            tp2_structural_min_rr=2.0,
        ),
        _korreksiya_bilan(asos, "nazorat: Correction Entry yoqilgan", enabled=True),
    ]


class Chiqish:
    """Hisobotni bir vaqtda ekranga ham, faylga ham yozadi.

    Nima uchun kerak: backtest terminalsiz — masalan `BACKTEST.bat`
    ustiga bosib yoki GitHub Actions orqali — ishga tushirilganda
    ekrandagi matn oyna yopilishi bilan yo'qoladi. Natijani birov
    bilan bo'lishish uchun esa u FAYLDA turishi kerak.
    """

    def __init__(self, yol: Path | None) -> None:
        self._satrlar: list[str] = []
        self._yol = yol

    def __call__(self, matn: str = "") -> None:
        print(matn)
        if self._yol is not None:
            self._satrlar.append(matn)

    def saqla(self) -> None:
        if self._yol is None:
            return
        self._yol.parent.mkdir(parents=True, exist_ok=True)
        self._yol.write_text("\n".join(self._satrlar) + "\n", encoding="utf-8")
        print(f"\nNatija saqlandi: {self._yol}")


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
    parser.add_argument(
        "--output",
        default=None,
        help="hisobotni shu faylga ham yozadi (masalan natija.txt)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Binance REST manzili. Ba'zi mamlakatlar va bulut serverlaridan "
            "api.binance.com yopiq bo'ladi (451) — o'shanda "
            "https://data-api.binance.vision ni bering"
        ),
    )
    parser.add_argument("--max-steps", type=int, default=None)
    argumentlar = parser.parse_args()

    setup_logging(level="INFO")
    config = load_config()
    if argumentlar.base_url:
        config = dataclasses.replace(
            config,
            market_data=dataclasses.replace(
                config.market_data, rest_base_url=argumentlar.base_url.rstrip("/")
            ),
        )
    yoz = Chiqish(Path(argumentlar.output) if argumentlar.output else None)
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
        yoz(render(natija))
        yoz.saqla()
        return

    natijalar = []
    for nom, variant in _variantlar(config):
        print(f"  ishlamoqda: {nom} ...")
        natijalar.append(
            Backtester(variant, label=nom).run(dataset, max_steps=argumentlar.max_steps)
        )

    yoz(f"Coinlar: {', '.join(coinlar)} | {argumentlar.days} kun | {qadamlar:,} qadam")
    yoz()
    yoz(compare(natijalar))
    yoz()
    for natija in natijalar:
        if natija.closed:
            yoz(render(natija))
            yoz()
    yoz.saqla()


if __name__ == "__main__":
    asyncio.run(main())
