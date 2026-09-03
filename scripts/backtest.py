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

TAQQOSLASH REJIMI eng qimmatli qism. U har safar BITTA ochiq
savolga raqam bilan javob beradi.

Javob berilgan savollar (`docs/BACKTEST_NATIJA_*.md`):

    1. Past bandda Correction Entry yordam beradimi?  -> YO'Q
    2. TP2 tuzilmadan olinsa yaxshiroqmi?             -> YO'Q

Hozirgi savol: muammo TP da emas, KIRISHDA emasmi? Ikkala rad
etilgan gipoteza ham TP haqida edi, win-rate esa barcha variantda
37.5-38.4% bo'lib qoldi — ya'ni kirishlarning ~62% i TP ga
yaqinlashmay stopga boradi.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path

from core.backtest import Backtester, Dataset, compare, render
from core.backtest.warmup import warmup_days, warmup_steps
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


def _kesh_yoli(symbol: str, timeframe: str, until: str | None = None) -> Path:
    """Kesh fayli yo'li.

    OYNA NOMGA KIRADI. Aks holda 2025-yilgi oyna uchun yuklangan
    shamlar 2026-yilgi yugurishda jimgina qayta ishlatilardi va
    ikkita "mustaqil" o'lchov aslida BIR XIL ma'lumotda bo'lardi —
    ya'ni takroriy tekshiruvning butun ma'nosi yo'qolardi.
    """
    oyna = f"_{until}" if until else ""
    return KESH / f"{symbol}_{timeframe}{oyna}.json"


def _keshdan_oqish(
    symbol: str, timeframe: str, until: str | None = None
) -> list[Candle] | None:
    yol = _kesh_yoli(symbol, timeframe, until)
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


def _keshga_yozish(
    symbol: str, timeframe: str, candles: list[Candle], until: str | None = None
) -> None:
    KESH.mkdir(parents=True, exist_ok=True)
    _kesh_yoli(symbol, timeframe, until).write_text(
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


def _keshdan_yigish(
    symbols: list[str], timeframelar: list[str], until: str | None = None
) -> Dataset:
    """Tarmoqqa umuman chiqmaydi. Yetishmagani aniq aytiladi."""
    dataset = Dataset()
    yoq: list[str] = []
    for symbol in symbols:
        for tf in timeframelar:
            shamlar = _keshdan_oqish(symbol, tf, until)
            if shamlar is None:
                yoq.append(str(_kesh_yoli(symbol, tf, until)))
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
    until: datetime | None = None,
) -> Dataset:
    """Kerakli barcha timeframelarni yuklaydi (yoki keshdan oladi).

    `until` — sinov oynasining OXIRI. Berilmasa eng so'nggi
    ma'lumot olinadi.
    """
    timeframelar = _kerakli_timeframelar(config)
    oyna = until.date().isoformat() if until is not None else None

    if offline:
        return _keshdan_yigish(symbols, timeframelar, oyna)

    provider = BinanceCandleProvider(config.market_data, config.halal_screening.quote_asset)
    dataset = Dataset()

    # Necha sham kerakligi kunlardan hisoblanadi. Provayder 1000 dan
    # ortig'ini SAHIFALAB yuklaydi — ilgari bu yerda `min(1000, ...)`
    # turardi va `--days 730` 4 soatlik timeframeda jimgina ~166 kunga
    # aylanardi.
    daqiqalar = {"15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}

    # SINOV OYNASIDAN TASHQARI isinish tarixi. `--days 730` "730 kun
    # TAHLIL QILINADI" degani bo'lib qolsin: isinish qismi tahlil
    # qilinmaydi, u faqat indikatorlarni to'ldiradi. Ansiz haftalik
    # qatorda 60 sham sinovning yarmidan keyin yig'ilar, undan oldin
    # esa Bozor Salomatligi indeksining 60 balli qismi erishib
    # bo'lmaydigan bo'lardi (`core/backtest/warmup.py`).
    jami_kun = days + warmup_days(config)

    try:
        for symbol in symbols:
            for tf in timeframelar:
                kerak = max(1, int(jami_kun * 1440 / daqiqalar.get(tf, 15)))
                shamlar = None if refresh else _keshdan_oqish(symbol, tf, oyna)
                if shamlar is not None and len(shamlar) < kerak:
                    # Kesh eski, KALTA so'rov bilan yig'ilgan. Uni jimgina
                    # ishlatish backtestni isinishsiz qoldirardi.
                    logger.info(
                        "Kesh kalta: %s %s — %d sham bor, %d kerak, qayta yuklanadi",
                        symbol,
                        tf,
                        len(shamlar),
                        kerak,
                    )
                    shamlar = None
                if shamlar is None:
                    logger.info("Yuklanmoqda: %s %s (%d sham)", symbol, tf, kerak)
                    shamlar = await provider.fetch_candles(symbol, tf, kerak, until)
                    _keshga_yozish(symbol, tf, shamlar, oyna)
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


def _tahlil_bilan(
    asos: AppConfig, nom: str, indikator: dict | None = None, **ozgarishlar: object
) -> tuple[str, AppConfig]:
    """`analysis` (va kerak bo'lsa `indicators`) o'zgartirilgan nusxa."""
    tahlil = asos.analysis
    if indikator:
        tahlil = dataclasses.replace(
            tahlil, indicators=dataclasses.replace(tahlil.indicators, **indikator)
        )
    if ozgarishlar:
        tahlil = dataclasses.replace(tahlil, **ozgarishlar)
    return nom, dataclasses.replace(asos, analysis=tahlil)


def _sr_bilan(asos: AppConfig, nom: str, **ozgarishlar: object) -> tuple[str, AppConfig]:
    """`analysis.support_resistance` o'zgartirilgan nusxa."""
    sr = dataclasses.replace(asos.analysis.support_resistance, **ozgarishlar)
    return nom, dataclasses.replace(
        asos, analysis=dataclasses.replace(asos.analysis, support_resistance=sr)
    )


#: Bu yugurishda O'LCHANAYOTGAN o'q.
#:
#: Taqqoslashning eng asosiy sharti — bitta o'zgaruvchi. Uni har
#: safar qo'lda tekshirish o'rniga o'q shu yerda nomlanadi va test
#: shu nomni o'qiydi: variant asosdan FAQAT shu qismi bilan farq
#: qilishi mumkin.
OLCHOV_OQI = "audit 3-bosqich (uchta yarim holat)"


def _oqsiz(config: AppConfig) -> AppConfig:
    """Sozlamaning o'lchov o'qi NEYTRALLANGAN nusxasi.

    Ikkita variantni solishtirganda o'q chiqarib tashlanadi — qolgani
    aynan teng bo'lishi kerak. Aks holda taqqoslash bir vaqtda
    ikkita narsani o'lchayotgan bo'ladi va qaysi biri ta'sir
    qilganini hech kim ayta olmaydi.
    """
    qoidalar = dataclasses.replace(
        config.trade_rules, tp1_ratio_tuzilmaviy_zonaga=True
    )
    sr = dataclasses.replace(
        config.analysis.support_resistance,
        chuqurlik_darvozadan=False,
        zona_yagona_manba=False,
    )
    return dataclasses.replace(
        config,
        trade_rules=qoidalar,
        analysis=dataclasses.replace(config.analysis, support_resistance=sr),
    )


def _narx_harakati_bilan(
    asos: AppConfig, nom: str, **ozgarishlar: object
) -> tuple[str, AppConfig]:
    """`strategies.narx_harakati` o'zgartirilgan nusxa."""
    nh = dataclasses.replace(asos.strategies.narx_harakati, **ozgarishlar)
    return nom, dataclasses.replace(
        asos, strategies=dataclasses.replace(asos.strategies, narx_harakati=nh)
    )


def _rejim_bilan(
    asos: AppConfig, nom: str, **ozgarishlar: object
) -> tuple[str, AppConfig]:
    """`analysis.regime_rules` o'zgartirilgan nusxa."""
    rejim = dataclasses.replace(asos.analysis.regime_rules, **ozgarishlar)
    return nom, dataclasses.replace(
        asos, analysis=dataclasses.replace(asos.analysis, regime_rules=rejim)
    )


def _zona_oynasi_bilan(
    asos: AppConfig, nom: str, oyna: int, **rejim_ozgarishlari: object
) -> tuple[str, AppConfig]:
    """Zona qidiruv oynasi (va kerak bo'lsa rejim) o'zgartirilgan nusxa."""
    sr = dataclasses.replace(asos.analysis.support_resistance, zone_lookback=oyna)
    rejim = dataclasses.replace(asos.analysis.regime_rules, **rejim_ozgarishlari)
    return nom, dataclasses.replace(
        asos,
        analysis=dataclasses.replace(
            asos.analysis, support_resistance=sr, regime_rules=rejim
        ),
    )


def _skalp_bilan(
    asos: AppConfig, nom: str, **ozgarishlar: object
) -> tuple[str, AppConfig]:
    """`strategies.opening_range_scalp` o'zgartirilgan nusxa."""
    skalp = dataclasses.replace(asos.strategies.opening_range_scalp, **ozgarishlar)
    return nom, dataclasses.replace(
        asos, strategies=dataclasses.replace(asos.strategies, opening_range_scalp=skalp)
    )


def _classic_ta_bilan(
    asos: AppConfig, nom: str, **ozgarishlar: object
) -> tuple[str, AppConfig]:
    """`strategies.classic_ta` o'zgartirilgan nusxa."""
    strategiya = dataclasses.replace(asos.strategies.classic_ta, **ozgarishlar)
    return nom, dataclasses.replace(
        asos, strategies=dataclasses.replace(asos.strategies, classic_ta=strategiya)
    )


def _darvoza_bilan(
    asos: AppConfig, nom: str, **ozgarishlar: object
) -> tuple[str, AppConfig]:
    """`scoring.quality_gate` o'zgartirilgan nusxa."""
    darvoza = dataclasses.replace(asos.scoring.quality_gate, **ozgarishlar)
    return nom, dataclasses.replace(
        asos, scoring=dataclasses.replace(asos.scoring, quality_gate=darvoza)
    )


def _variantlar(asos: AppConfig) -> list[tuple[str, AppConfig]]:
    """To'qqizinchi to'plam: AUDITNING UCHTA YARIM HOLATI.

    Har biri "kod bir narsa qiladi, izoh boshqa narsa aytadi"
    turkumidan. Ular gipoteza sifatida emas, NOMUVOFIQLIK sifatida
    topilgan — shuning uchun savol "yaxshimi" emas, "tuzatilsa
    natija qanday o'zgaradi".

    3.1  TP1 POLI TUZILMAVIY ZONAGA
         Pol (2.0) yakuniy nishondan (1.5) yuqori, shuning uchun
         signal DOIM bitta TP bilan chiqadi — 189/189 o'lchandi.
         Qismli sotish amalda ishlamaydi. O'chirilganda tuzilmaviy
         TP1 yaqinroq bo'ladi va haqiqiy ikkita TP qaytadi.

    3.2  CHUQURLIK DARVOZADAN
         Darvoza 55%, chuqurlik esa 50% dan o'lchanadi. 50-55%
         oralig'idagi nomzod darvozadan o'tadi-yu, S/R omilidan
         8.75 ball yo'qotadi. Shift ~60, chegara 55 — ya'ni
         darvoza kiritgan nomzodni ball darhol o'ldiradi.

    3.3  ZONA YAGONA MANBA
         Ball bir zonadan, Stop boshqasidan hisoblanadi (saralash
         kalitlari boshqa). Narx ikki zona orasida bo'lsa ular
         ajraladi.

    Oxirgi variant uchalasini birga yoqadi: alohida ta'sirsiz
    bo'lgan narsa birga ta'sir qilishi mumkin (ablation darsi).
    """
    return [
        ("hozirgi holat", asos),
        _qoidalar_bilan(
            asos, "3.1 pol faqat o'lchanganda", tp1_ratio_tuzilmaviy_zonaga=False
        ),
        _sr_bilan(asos, "3.2 chuqurlik darvozadan", chuqurlik_darvozadan=True),
        _sr_bilan(asos, "3.3 zona yagona manba", zona_yagona_manba=True),
        _uchalasi(asos),
    ]


def _uchalasi(asos: AppConfig) -> tuple[str, AppConfig]:
    """Uchala tuzatish birga."""
    qoidalar = dataclasses.replace(
        asos.trade_rules, tp1_ratio_tuzilmaviy_zonaga=False
    )
    sr = dataclasses.replace(
        asos.analysis.support_resistance,
        chuqurlik_darvozadan=True,
        zona_yagona_manba=True,
    )
    return "3.1+3.2+3.3 birga", dataclasses.replace(
        asos,
        trade_rules=qoidalar,
        analysis=dataclasses.replace(asos.analysis, support_resistance=sr),
    )


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
    parser.add_argument(
        "--end-date",
        default=None,
        help=(
            "sinov oynasining OXIRI (YYYY-MM-DD). Berilmasa eng so'nggi "
            "ma'lumot olinadi. Takroriy o'lchov uchun: bir yugurish "
            "2025-09-02 gacha, boshqasi 2026-09-02 gacha — oynalar "
            "kesishmasin uchun `--days` ni ham qisqartiring"
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

    oxiri: datetime | None = None
    if argumentlar.end_date:
        try:
            oxiri = datetime.fromisoformat(argumentlar.end_date).replace(tzinfo=UTC)
        except ValueError:
            print(f"--end-date noto'g'ri: {argumentlar.end_date} (YYYY-MM-DD kutiladi)")
            raise SystemExit(1) from None

    isinish = warmup_days(config)
    oyna_matni = f", {oxiri.date()} gacha" if oxiri else ""
    print(
        f"Ma'lumot tayyorlanmoqda: {', '.join(coinlar)} "
        f"({argumentlar.days} kun tahlil + {isinish} kun isinish{oyna_matni})\n"
    )
    try:
        dataset = await _yukla(
            config,
            coinlar,
            argumentlar.days,
            argumentlar.refresh,
            offline=argumentlar.offline,
            until=oxiri,
        )
    except KeshYetishmaydi as xato:
        print(str(xato))
        raise SystemExit(1) from xato

    qadamlar = len(dataset.timeline(config.analysis.entry_timeframe))
    tahlil_qadam = max(0, qadamlar - warmup_steps(config))
    print(
        f"Yuklandi: {len(dataset.symbols)} coin, {qadamlar:,} qadam "
        f"({tahlil_qadam:,} tahlil qilinadi, qolgani isinish)\n"
    )

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

    yoz(
        f"Coinlar: {', '.join(coinlar)} | {argumentlar.days} kun | "
        f"{tahlil_qadam:,} tahlil qadami (+{isinish} kun isinish)"
        + (f" | oyna {oxiri.date()} gacha" if oxiri else "")
    )
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
