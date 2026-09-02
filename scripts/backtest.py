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
from pathlib import Path

from core.backtest import Backtester, Dataset, compare, render
from core.backtest.warmup import warmup_days, warmup_steps
from core.config import AppConfig, load_config
from core.config.schema import QualityGateConfig
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
                shamlar = None if refresh else _keshdan_oqish(symbol, tf)
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
OLCHOV_OQI = "scoring.quality_gate + trade_rules"


def _oqsiz(config: AppConfig) -> AppConfig:
    """Sozlamaning o'lchov o'qi NEYTRALLANGAN nusxasi.

    Ikki variantni solishtirganda o'q chiqarib tashlanadi — qolgani
    aynan teng bo'lishi kerak. Aks holda taqqoslash bir vaqtda
    ikkita narsani o'lchayotgan bo'ladi va qaysi biri ta'sir
    qilganini hech kim ayta olmaydi.
    """
    return dataclasses.replace(
        config,
        scoring=dataclasses.replace(
            config.scoring, quality_gate=QualityGateConfig()
        ),
        trade_rules=dataclasses.replace(
            config.trade_rules,
            enforce_distance_bands=False,
            max_take_profits=2,
            max_holding_hours=0.0,
        ),
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
    """To'rtinchi to'plam: QAROR KIMDA.

    OLDINGI UCHTA TO'PLAM JAVOB BERDI, HAMMASI RAD ETILDI:

    1. Correction Entry (natija #1) — signal qo'shdi, natijani
       yomonlashtirdi
    2. Tuzilmaviy TP2 (natija #2) — TP2 gacha yetish PASAYDI
    3. Kirish filtrlari (natija #3 va #6) — to'rtta filtr, signal
       soni 610 dan 884 gacha, win-rate 36.9-39.1% da qotib qoldi

    Uchalasi ham SOZLAMA darajasida edi: chegarani surish, filtr
    yoqish, TP ni ko'chirish. Hech biri ishlamadi.

    Bu to'plam boshqa savol beradi: kirishga KIM ruxsat beradi?

    Hozir yagona darvoza — ball chegarasi. Ball esa nomzodlarni
    bir-biriga NISBATAN o'lchaydi: "eng yaxshisi qaysi" deydi, "shu
    yetarlimi" demaydi. Shuning uchun tizim uyumning eng yuqorisini
    oladi — uyumning o'zi yomon bo'lsa ham. Uchinchi to'plamning
    natijasi aynan shunga o'xshaydi: filtrlar uyumga kim kirishini
    o'zgartirdi, uyum baribir tartiblanib eng yuqorisi olinaverdi.

    Sifat darvozasi qarorni DALILGA beradi: CryptoSpot3%
    shartnomasi (yo'nalish + yalash + daraja turi) bajarilishi
    shart.

    NAZORAT VARIANTI ZARUR. Darvoza ikki narsani bir vaqtda
    qiladi: shartnomani talab qiladi VA ball chegarasini polga
    almashtiradi. "Faqat pol" varianti ikkinchisini alohida
    o'lchaydi — ansiz natija yaxshi chiqsa, uni shartnomaga
    yozib qo'yishimiz mumkin edi, holbuki sabab chegara
    pasaygani bo'lishi mumkin.
    """
    return [
        ("hozirgi holat", asos),
        # ASOSIY GIPOTEZA: dalil qaror qilsin.
        _darvoza_bilan(asos, "sifat darvozasi (pol 35)", enabled=True),
        # Pol balandroq: "tuzilma bor, lekin qolgani zaif" holatini
        # ko'proq kesadi. Signal yana kamayadi.
        _darvoza_bilan(
            asos, "sifat darvozasi (pol 45)", enabled=True, min_base_score=45.0
        ),
        # NAZORAT: shartnomasiz, faqat pol. Ya'ni "chegara 55 dan 35
        # ga tushirildi" degani. Bu variant asosiydan YAXSHI chiqsa,
        # sabab shartnomada emas — signal soni oshganida.
        _darvoza_bilan(
            asos,
            "faqat pol 35 (shartnomasiz)",
            enabled=True,
            require_setup_contract=False,
        ),
        # TP SONI. `max_take_profits` — yuqori chegara, majburiy son
        # emas: uchinchi TP faqat oraliqda haqiqiy zona bo'lganda
        # qo'shiladi. Mexanizm: erta qismli sotish o'rtacha
        # natijani ko'taradimi yoki foydani kesib qo'yadimi?
        _qoidalar_bilan(asos, "bitta TP (yakuniy nishon)", max_take_profits=1),
        _qoidalar_bilan(asos, "uchtagacha TP", max_take_profits=3),
        # FOIZ ORALIQLARI. Standart holatda ular o'chiq (loyiha
        # egasining qarori). Bu variant ularni QAYTA YOQADI — ya'ni
        # eski xatti-harakat. Farq qarorning narxini ko'rsatadi.
        _qoidalar_bilan(asos, "foiz oraliqlari yoqilgan", enforce_distance_bands=True),
        # MUDDAT. Hozir chiqish faqat TP yoki Stop — vaqt bo'yicha
        # chiqish umuman yo'q. Mexanizm: foydasiz pozitsiya kapitalni
        # band qilib turadi, va o'sha vaqtda tizim boshqa hech narsa
        # qila olmaydi (ochiq signal limiti to'ladi).
        #
        # Ikkita muddat sinaladi, chunki "qisqa yaxshimi yoki uzun"
        # degan savolga bitta raqam javob bermaydi. O'rtacha ushlash
        # 45.2 soat, ya'ni 24 soat ko'pchilikni kesadi, 72 esa faqat
        # eng uzoq cho'zilganlarini.
        _qoidalar_bilan(asos, "muddat 24 soat", max_holding_hours=24.0),
        _qoidalar_bilan(asos, "muddat 72 soat", max_holding_hours=72.0),
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

    isinish = warmup_days(config)
    print(
        f"Ma'lumot tayyorlanmoqda: {', '.join(coinlar)} "
        f"({argumentlar.days} kun tahlil + {isinish} kun isinish)\n"
    )
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
