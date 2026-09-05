"""Signal kuzatuvchisi — narxni kuzatib, holatni yangilaydi.

NIMA UCHUN BU FAYL PAYDO BO'LDI. 2026-09-05 da loyiha egasi
so'radi: "LTC limitga kelmay birinchi TP ini oldi, buni bekor
qilish kerak". Tekshirilganda kattaroq narsa chiqdi:

    KUZATUVCHI UMUMAN YO'Q EDI.

Rejalashtiruvchida to'rt vazifa bor edi — obuna, veb-signal,
veb-video, zanjir sikli — va narxni kuzatadigan birortasi ham
yo'q. Ya'ni:

  * hech bir signal "Faol" bo'lmasdi;
  * TP1 / TP2 / Stop hech qachon qayd etilmasdi;
  * statistika hech qachon to'lmasdi;
  * bekor qilish ham yo'q edi.

Kodning o'zi buni tan olardi: admin qo'lda bekor qilish funksiyasi
ustida "Kuzatuvchisiz zaxira yo'l" deb yozilgandi. Eski kuzatuvchi
eski modul bilan birga ketgan va yangisi qurilmagandi.

QOIDALAR BACKTEST BILAN BIR XIL. `core/backtest/zanjir_engine.py`
dagi `_yangila()` bilan bir xil tartib:

    1. STOP AVVAL. Bitta sham ichida ham TP, ham Stop tegilgan
       bo'lsa, qaysi biri oldin bo'lganini BILMAYMIZ — ehtiyotkor
       taxmin: Stop. Teskarisi natijani chiroyliroq ko'rsatardi.
    2. TP lar tartib bilan; TP1 dan keyin Stop breakevenga.
    3. Hamma TP olinsa — yopiladi.
    4. Muddat: TP olingan bo'lsa `qoldiq_muddat_kun`, aks holda
       `umumiy_muddat_kun`.

Aks holda o'lchangan PF jonli natijaga tegishli bo'lmasdi.

KUTAYOTGAN SIGNAL uchun qo'shimcha qoida (loyiha egasining tanlovi):

    low  <= entry  ->  FAOL (limit bajarildi)
    high >= tp1    ->  BEKOR — narx nishonga kirilmasdan yetdi

Tartib muhim: bitta sham ichida ikkalasi ham bo'lsa, LIMIT
BAJARILGAN deb hisoblanadi (stop < entry bo'lgani kabi mantiq —
narx entry'ga tushgan bo'lsa, savdo ochilgan).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from core.config.schema import AppConfig
from core.domain.enums import SignalStatus
from core.domain.models import Candle
from core.market_data.binance import BinanceCandleProvider
from core.storage import Database
from core.storage.models import SignalRecord
from core.storage.repositories import SignalRepository
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)

#: Kuzatuv qaysi timeframe'da yuradi.
#:
#: 15 daqiqa — backtestning pastki timeframei bilan bir xil. Undan
#: mayda sham bilan yurish "aniqroq" ko'rinardi-yu, o'lchangan
#: natijaga tegishli bo'lmasdi.
KUZATUV_TF = "15m"

#: Bir yugurishda ko'pi bilan shuncha sham o'qiladi (~10 kun).
#: Bot bir necha kun o'chib qolsa ham bo'shliq yopiladi.
ENG_KOP_SHAM = 1000


@dataclass
class KuzatuvNatijasi:
    """Bitta yugurishning hisoboti."""

    tekshirildi: int = 0
    faollashdi: list[str] = field(default_factory=list)
    tp_olindi: list[str] = field(default_factory=list)
    yopildi: list[str] = field(default_factory=list)
    bekor: list[str] = field(default_factory=list)
    xatolar: dict[str, str] = field(default_factory=dict)

    def matn(self) -> str:
        qatorlar = [f"Kuzatildi: {self.tekshirildi} signal"]
        for nom, royxat in (
            ("faollashdi", self.faollashdi),
            ("TP olindi", self.tp_olindi),
            ("yopildi", self.yopildi),
            ("bekor qilindi", self.bekor),
        ):
            if royxat:
                qatorlar.append(f"   {nom}: {', '.join(royxat)}")
        for symbol, sabab in self.xatolar.items():
            qatorlar.append(f"   ⚠️ {symbol}: {sabab}")
        return "\n".join(qatorlar)


@dataclass
class _Holat:
    """Bitta signalning yugurish davomidagi ishchi holati."""

    status: SignalStatus
    stop: float
    olingan_tp: int
    narx: float = 0.0
    vaqt: datetime | None = None
    sabab: str = ""


class SignalKuzatuvchi:
    """Ochiq signallarni sham ma'lumoti bilan oldinga suradi."""

    def __init__(
        self,
        config: AppConfig,
        provider: BinanceCandleProvider,
        database: Database,
    ) -> None:
        self._config = config
        self._provider = provider
        self._db = database

    async def yur(self) -> KuzatuvNatijasi:
        natija = KuzatuvNatijasi()

        async with self._db.session() as session:
            ochiq = await SignalRepository(session).open_signals()

        for yozuv in ochiq:
            natija.tekshirildi += 1
            try:
                await self._bitta_signal(yozuv, natija)
            except Exception as xato:  # noqa: BLE001 — bittasi qolganini to'xtatmasin
                natija.xatolar[yozuv.symbol] = f"{type(xato).__name__}: {xato}"
                logger.exception("Signal kuzatilmadi: id=%s %s", yozuv.id, yozuv.symbol)

        if natija.tekshirildi:
            logger.info("Signal kuzatuvi tugadi:\n%s", natija.matn())
        return natija

    async def _bitta_signal(self, yozuv: SignalRecord, natija: KuzatuvNatijasi) -> None:
        boshlangich = yozuv.activated_at or yozuv.created_at
        shamlar = await self._shamlar(yozuv.symbol, boshlangich)
        if not shamlar:
            return

        holat = _Holat(
            status=SignalStatus(yozuv.status),
            stop=yozuv.stop if not yozuv.tp1_reached else yozuv.entry,
            olingan_tp=yozuv.reached_tps or 0,
        )
        tplar = [t for t in (yozuv.tp1, yozuv.tp2, yozuv.tp3) if t is not None]

        oldingi = holat.status
        for sham in shamlar:
            if not self._sham_qadami(yozuv, holat, tplar, sham, boshlangich):
                break

        if holat.status is oldingi:
            return

        await self._yoz(yozuv, holat, natija)

    def _sham_qadami(  # noqa: PLR0911
        self,
        yozuv: SignalRecord,
        holat: _Holat,
        tplar: list[float],
        sham: Candle,
        boshlangich: datetime,
    ) -> bool:
        """Bitta sham. `False` — signal yopildi, davom etilmaydi."""
        z = self._config.zanjir.chiqish
        holat.vaqt = sham.open_time

        # --- KUTAYOTGAN LIMIT ---------------------------------------
        if holat.status is SignalStatus.PENDING:
            if sham.low <= yozuv.entry:
                # Limit bajarildi. Bir sham ichida TP ham tegilgan
                # bo'lsa, u ENDI ochiq savdoning TP si — quyidagi
                # qoidalar shu shamning o'zida ishlaydi.
                holat.status = SignalStatus.ACTIVE
                holat.narx = yozuv.entry
            elif tplar and sham.high >= tplar[0]:
                # Narx nishonga KIRILMASDAN yetdi. Savdo umuman
                # bo'lmagan — uni "foydali" deb ko'rsatish yolg'on
                # bo'lardi, "kutilmoqda" deb qoldirish esa chalg'itardi.
                holat.status = SignalStatus.CANCELLED
                holat.narx = tplar[0]
                holat.sabab = "narx TP1 ga kirilmasdan yetdi"
                return False
            else:
                return True

        # --- OCHIQ SAVDO — backtest bilan BIR XIL tartib -------------
        if sham.low <= holat.stop:
            holat.status = SignalStatus.STOPPED
            holat.narx = holat.stop
            holat.sabab = "stop"
            return False

        for i, tp in enumerate(tplar):
            if sham.high >= tp and holat.olingan_tp <= i:
                holat.olingan_tp = i + 1
                if i == 0 and z.tp1_breakeven:
                    holat.stop = yozuv.entry

        if holat.olingan_tp >= len(tplar):
            holat.status = SignalStatus.TP2_HIT
            holat.narx = tplar[-1]
            holat.sabab = "barcha TP olindi"
            return False

        if holat.olingan_tp >= 1:
            holat.status = SignalStatus.TP1_HIT

        muddat = timedelta(
            days=z.qoldiq_muddat_kun if holat.olingan_tp > 0 else z.umumiy_muddat_kun
        )
        if sham.open_time - boshlangich >= muddat:
            holat.status = SignalStatus.TIMED_OUT
            holat.narx = sham.close
            holat.sabab = "muddat tugadi"
            return False

        return True

    async def _yoz(
        self, yozuv: SignalRecord, holat: _Holat, natija: KuzatuvNatijasi
    ) -> None:
        """Yangi holatni bazaga yozadi va hisobotga qo'shadi."""
        async with self._db.session() as session:
            await SignalRepository(session).apply_event(
                signal_id=yozuv.id,
                status=holat.status,
                price=holat.narx or yozuv.entry,
                at=holat.vaqt or utc_now(),
                kind=holat.status.value,
                detail=holat.sabab or None,
                tp1_close_pct=self._config.portfolio.tp1_close_pct,
            )

        yorliq = f"{yozuv.symbol}#{yozuv.id}"
        if holat.status is SignalStatus.CANCELLED:
            natija.bekor.append(yorliq)
        elif holat.status is SignalStatus.ACTIVE:
            natija.faollashdi.append(yorliq)
        elif holat.status is SignalStatus.TP1_HIT:
            natija.tp_olindi.append(yorliq)
        else:
            natija.yopildi.append(f"{yorliq} ({holat.sabab})")

        logger.info(
            "Signal holati: %s -> %s (%s)", yorliq, holat.status.value, holat.sabab or "—"
        )

    async def _shamlar(self, symbol: str, boshlangich: datetime) -> list[Candle]:
        """Signal boshlangandan keyingi shamlar.

        Boshlanishdan OLDINGI shamlar tashlanadi: signal berilishidan
        avvalgi harakat bu savdoga tegishli emas.
        """
        shamlar = await self._provider.fetch_candles(symbol, KUZATUV_TF, ENG_KOP_SHAM)
        if boshlangich.tzinfo is None:
            boshlangich = boshlangich.replace(tzinfo=UTC)
        return [s for s in shamlar if s.open_time >= boshlangich]
