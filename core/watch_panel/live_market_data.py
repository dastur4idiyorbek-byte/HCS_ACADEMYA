"""Top 20 uchun jonli bozor yig'masi — FAQAT yig'ma, stakan emas.

--------------------------------------------------------------------
NEGA BU YERDA FAQAT YIG'MA BOR
--------------------------------------------------------------------

Prompt Order Book, Trade Tape, xarid bosimi va yirik operatsiyalarni
so'raydi. Ular ikki xil narsa:

    STAKAN va SAVDO LENTASI — "hozir nima bo'lyapti". Sekundiga
        o'nlab marta o'zgaradi. Ularni bazaga yozish ma'nosiz: yozib
        bo'lgan zahoti eskiradi. BRAUZER ularni o'zi, to'g'ridan-
        to'g'ri birjadan oladi — serverga nol yuk, va ma'lumot
        chinakam jonli.

    XARID BOSIMI va YIRIK SAVDOLAR — "so'nggi 15 daqiqada nima
        bo'ldi". Bularni brauzer BERA OLMAYDI: admin sahifani endi
        ochgan va o'tgan 15 daqiqani ko'rmagan. Shuning uchun ularni
        bot UZLUKSIZ yig'adi.

Shu bo'linish loyiha egasining qarori (2026-09-12).

--------------------------------------------------------------------
FAQAT TOP 20
--------------------------------------------------------------------

"+10 kuzatuvda" va qolgan 50 coin uchun oqim ochilmaydi. Coin Top 20
ga ko'tarilsa, keyingi skandan keyin ulanadi. 20 ta oqim — Railway
uchun ko'tarsa bo'ladigan yuk; 80 tasi esa yo'q.

QAT'IY CHEGARA: bu faylda Entry/Stop/TP hisoblanmaydi.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime

import websockets
from websockets.exceptions import ConnectionClosed

from core.config.schema import MarketDataConfig
from core.market_data.binance import to_binance_symbol
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Yig'ma oynasi — prompt "so'nggi 15 daqiqa" deydi.
OYNA_SONIYA = 15 * 60

#: Savdo shundan katta bo'lsa "yirik" (prompt: $50 000+).
YIRIK_USD = 50_000.0

#: Ekranda nechta yirik savdo ko'rsatiladi.
YIRIK_ROYXAT = 15

#: Uzilishdan keyin qayta ulanishgacha kutish.
QAYTA_ULANISH = 5.0


@dataclass(frozen=True, slots=True)
class Savdo:
    vaqt: datetime
    narx: float
    summa_usd: float
    #: `True` — xaridor tashabbuskor (agressiv xarid)
    xarid: bool


@dataclass(frozen=True, slots=True)
class BozorYigmasi:
    """Bitta coinning oyna ichidagi holati."""

    symbol: str
    narx: float | None
    #: Xaridlar ulushi 0..100. `None` — oynada savdo bo'lmagan.
    xarid_bosimi: float | None
    hajm_usd: float
    yirik_savdo: int
    yiriklar: tuple[Savdo, ...]

    def yiriklar_json(self) -> str:
        return json.dumps(
            [
                {
                    "vaqt": s.vaqt.isoformat(),
                    "narx": s.narx,
                    "summa": round(s.summa_usd, 2),
                    "xarid": s.xarid,
                }
                for s in self.yiriklar
            ],
            ensure_ascii=False,
        )


class BozorYigichi:
    """aggTrade oqimini ushlab turadi va oyna yig'masini beradi.

    ULANISH BITTA. Binance "combined stream" 20 ta coinni bitta
    ulanishda beradi; har coin uchun alohida soket ochish 20 ta
    ping/pong va 20 ta qayta ulanish mantig'i demakdir.

    RO'YXAT O'ZGARSA — QAYTA ULANADI. Combined stream manzili
    ulanish paytida belgilanadi, uni keyin o'zgartirib bo'lmaydi
    (`BinancePriceStream` dagi bilan bir xil tamoyil).
    """

    def __init__(self, config: MarketDataConfig, quote: str) -> None:
        self._config = config
        self._quote = quote
        self._symbols: set[str] = set()
        self._savdolar: dict[str, deque[Savdo]] = defaultdict(deque)
        self._yopildi = False
        self._qayta = asyncio.Event()

    def kuzat(self, symbols: list[str]) -> None:
        """Kuzatiladigan coinlar — har skandan keyin yangilanadi."""
        yangi = {s.upper() for s in symbols}
        if yangi == self._symbols:
            return
        chiqdi = self._symbols - yangi
        self._symbols = yangi
        # Ro'yxatdan chiqqan coinning tarixi TASHLANADI: u keyin
        # qaytsa, eski 15 daqiqa allaqachon eskirgan bo'ladi va uni
        # "hozirgi holat" deb ko'rsatish yolg'on bo'lardi.
        for symbol in chiqdi:
            self._savdolar.pop(symbol, None)
        logger.info("Kuzatuv jonli oqimi: %d coin", len(yangi))
        self._qayta.set()

    def yopil(self) -> None:
        self._yopildi = True
        self._qayta.set()

    def _url(self) -> str:
        oqimlar = "/".join(
            f"{to_binance_symbol(s, self._quote)}@aggTrade" for s in sorted(self._symbols)
        )
        return f"{self._config.ws_base_url}?streams={oqimlar}"

    def _tozala(self, symbol: str, hozir: datetime) -> None:
        """Oynadan chiqqan savdolarni tashlaydi.

        Ansiz `deque` cheksiz o'sardi: kuniga o'n minglab savdo
        xotirada qolardi va bot asta shishardi.
        """
        navbat = self._savdolar[symbol]
        while navbat and (hozir - navbat[0].vaqt).total_seconds() > OYNA_SONIYA:
            navbat.popleft()

    def yigma(self, symbol: str) -> BozorYigmasi:
        """Coinning hozirgi oyna yig'masi."""
        hozir = datetime.now(UTC)
        self._tozala(symbol, hozir)
        navbat = self._savdolar[symbol]

        if not navbat:
            return BozorYigmasi(symbol, None, None, 0.0, 0, ())

        xarid = sum(s.summa_usd for s in navbat if s.xarid)
        jami = sum(s.summa_usd for s in navbat)
        yiriklar = sorted(
            (s for s in navbat if s.summa_usd >= YIRIK_USD),
            key=lambda s: s.vaqt,
            reverse=True,
        )
        return BozorYigmasi(
            symbol=symbol,
            narx=navbat[-1].narx,
            xarid_bosimi=round(100.0 * xarid / jami, 1) if jami > 0 else None,
            hajm_usd=jami,
            yirik_savdo=len(yiriklar),
            yiriklar=tuple(yiriklar[:YIRIK_ROYXAT]),
        )

    def barchasi(self) -> list[BozorYigmasi]:
        return [self.yigma(s) for s in sorted(self._symbols)]

    async def yur(self) -> None:
        """Oqimni ushlab turadi. Uzilsa qayta ulanadi."""
        while not self._yopildi:
            if not self._symbols:
                # Bo'sh ro'yxat uchun ulanish ochilmaydi: skan hali
                # yugurmagan bo'lishi mumkin.
                self._qayta.clear()
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._qayta.wait(), timeout=30.0)
                continue

            self._qayta.clear()
            try:
                await self._ulanish()
            except (ConnectionClosed, OSError) as xato:
                logger.warning("Kuzatuv oqimi uzildi: %s", xato)
                await asyncio.sleep(QAYTA_ULANISH)
            except Exception:  # noqa: BLE001 — oqim butun botni yiqitmasin
                logger.exception("Kuzatuv oqimida kutilmagan xato")
                await asyncio.sleep(QAYTA_ULANISH)

    async def _ulanish(self) -> None:
        async with websockets.connect(
            self._url(), ping_interval=20, ping_timeout=20
        ) as ws:
            logger.info("Kuzatuv oqimi ulandi: %d coin", len(self._symbols))
            while not self._yopildi and not self._qayta.is_set():
                try:
                    xom = await asyncio.wait_for(ws.recv(), timeout=30.0)
                except TimeoutError:
                    # Savdo bo'lmasa xabar kelmaydi — bu xato emas.
                    # Sikl davom etadi va `_qayta` bayrog'ini ko'radi.
                    continue
                self._xabar(xom)

    def _xabar(self, xom: str | bytes) -> None:
        try:
            paket = json.loads(xom)
        except (ValueError, TypeError):
            return
        malumot = paket.get("data") if isinstance(paket, dict) else None
        if not isinstance(malumot, dict):
            return

        binance_symbol = str(malumot.get("s", ""))
        symbol = self._symbolni_top(binance_symbol)
        if symbol is None:
            return

        try:
            narx = float(malumot["p"])
            miqdor = float(malumot["q"])
            vaqt = datetime.fromtimestamp(int(malumot["T"]) / 1000, tz=UTC)
        except (KeyError, ValueError, TypeError):
            return

        # `m` — "xaridor MAKER edimi". True bo'lsa tashabbuskor
        # SOTUVCHI, ya'ni agressiv sotish. Shuning uchun teskari.
        xarid = not bool(malumot.get("m"))
        self._savdolar[symbol].append(Savdo(vaqt, narx, narx * miqdor, xarid))
        self._tozala(symbol, vaqt)

    def _symbolni_top(self, binance_symbol: str) -> str | None:
        """`BTCUSDT` -> `BTC`. Noma'lum symbol jimgina tashlanadi."""
        for symbol in self._symbols:
            if to_binance_symbol(symbol, self._quote).upper() == binance_symbol.upper():
                return symbol
        return None
