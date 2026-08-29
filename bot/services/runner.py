"""Jonli ma'lumotni signal sikliga ulaydigan qatlam.

Sikl (`core/pipeline/cycle.py`) sof: u tayyor `CycleInput` ni oladi. Bu
modul esa uni jonli manbalardan YIG'ADI:

    halol skrining  ->  OHLCV yuklash  ->  Bozor Salomatligi
    ->  sikl  ->  bazaga yozish  ->  Telegram

Xuddi shu sababli backtest (16-bosqich) shu qatlamning o'rniga tarixiy
ma'lumot yig'uvchi qo'yadi va sikl kodi o'zgarmaydi.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from aiogram import Bot

from bot.i18n import DEFAULT_LANGUAGE, t
from bot.services.broadcast import broadcast_signal, obunachilar
from core.analysis import decide_entry_plan
from core.analysis.indicators import adx, atr_pct
from core.analysis.market_health import HealthInputs, MarketHealthCalculator
from core.analysis.market_structure import analyze_structure
from core.analysis.scoring import breakdown_to_json
from core.analysis.strategies import build_strategies, required_timeframes
from core.config.schema import AppConfig
from core.domain.enums import HalalStatus, SubscriptionTier
from core.domain.models import Candle, HalalVerdict, MarketHealth
from core.halal_screening import HalalScreener, StaticRulingRegistry
from core.market_data import CandleProvider, CoinMarketCapDominance, RankingProvider
from core.market_data.ranking import RankingUnavailableError
from core.pipeline import CycleInput, CycleResult, SignalCycle, SignalMonitor, SymbolData
from core.pipeline.events import derive_events
from core.position_sizing import PositionSizer, compute_aggregate_capacity
from core.storage import Database
from core.storage.repositories import (
    CoinRulingRepository,
    MarketHealthRepository,
    PipelineEventRepository,
    RiskBlockRepository,
    SignalRepository,
    SubscriptionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import timeframe_minutes, utc_now

logger = get_logger(__name__)

#: Bir kundagi daqiqalar — 24 soatlik o'zgarishni hisoblash uchun
MINUTES_PER_DAY = 1440


@dataclass(slots=True)
class UniverseCache:
    """Halol ro'yxat va uning yangilanish vaqti.

    0.3-band: reyting olinmasa ro'yxat YANGILANMAYDI, eski tasdiqlangan
    ro'yxat kuchda qoladi. Bo'sh ro'yxat qaytarish xavfli bo'lardi —
    tizim "halol coin yo'q" deb o'ylab qolardi.
    """

    symbols: list[str]
    verdicts: dict[str, HalalVerdict]
    refreshed_at: object | None = None

    @property
    def is_empty(self) -> bool:
        return not self.symbols


class PipelineRunner:
    """Signal siklini jonli ma'lumot bilan ishga tushiradi."""

    def __init__(
        self,
        bot: Bot,
        database: Database,
        config: AppConfig,
        candles: CandleProvider,
        ranking: RankingProvider,
        watcher,  # noqa: ANN001 — bot.services.watcher.SignalWatcher
        dominance: CoinMarketCapDominance | None = None,
    ) -> None:
        self._bot = bot
        self._db = database
        self._config = config
        self._candles = candles
        self._ranking = ranking
        self._watcher = watcher
        self._dominance = dominance

        self._strategies = build_strategies(config)
        self._cycle = SignalCycle(config, self._strategies)
        self._monitor = SignalMonitor(config.risk_engine)
        self._health = MarketHealthCalculator(config)
        self._universe = UniverseCache(symbols=[], verdicts={})

    @property
    def watcher(self):  # noqa: ANN201 — turi `SignalWatcher`, aylanma import bo'lmasin
        """Kuzatuvchi — fon vazifalari unga murojaat qiladi.

        Ochiq qilingani sabab: rejalashtiruvchi veb-panelda yaratilgan
        signallarni kuzatuvga qo'shishi kerak. `self._runner._watcher`
        kabi yashirin maydonga tegish bog'liqlikni yashirardi.
        """
        return self._watcher

    # ------------------------------------------------------------------ #
    #  3.4 — Halol ro'yxatni yangilash
    # ------------------------------------------------------------------ #

    async def refresh_universe(self) -> UniverseCache:
        """Halol coinlar ro'yxatini qayta hisoblaydi."""
        async with self._db.session() as session:
            admin_qarorlari = await CoinRulingRepository(session).all_verdicts()

        reyestr = StaticRulingRegistry.from_config(self._config.halal_screening)
        reyestr.merge_overrides(admin_qarorlari)
        skrener = HalalScreener(self._config.halal_screening, reyestr)

        try:
            natija = await skrener.build_universe(self._ranking)
        except (RankingUnavailableError, Exception) as exc:  # noqa: BLE001
            logger.warning(
                "Halol ro'yxat yangilanmadi (%s) — oldingi ro'yxat kuchda qoladi", exc
            )
            return self._universe

        if not natija.symbols:
            logger.warning("Skrining bo'sh ro'yxat qaytardi — oldingisi saqlanadi")
            return self._universe

        self._universe = UniverseCache(
            symbols=natija.symbols,
            verdicts={v.symbol: v for v in natija.verdicts},
            refreshed_at=natija.generated_at,
        )
        logger.info(
            "Halol ro'yxat yangilandi: %d ta coin (to'liq: %s)",
            natija.count,
            natija.complete,
        )
        return self._universe

    # ------------------------------------------------------------------ #
    #  Ma'lumot yig'ish
    # ------------------------------------------------------------------ #

    async def _load_candles(self, symbols: list[str]) -> dict[str, dict[str, list[Candle]]]:
        """Barcha coinlar uchun kerakli timeframelarni parallel yuklaydi.

        Parallellik CHEGARALANGAN. Ilgari chegara yo'q edi: sikl barcha
        coin × barcha timeframe so'rovini bir zumda yuborardi. 30 ta
        coinda bu 90 ta so'rov — birja chidardi. 150 ta coinda 450 ta
        bo'ladi va Binance avval 429, keyin 418 (IP ban) qaytaradi.

        Ya'ni ro'yxatni kengaytirish chegarasiz ishlamasdi: coinlar soni
        ortishi bilan tizim ko'proq ma'lumot emas, KAMROQ ma'lumot
        olardi — barcha so'rov birdaniga rad etilardi.
        """
        # Salomatlik kengligi o'z timeframeini talab qiladi va u
        # strategiyalarnikidan MUSTAQIL. Ansiz `compute_health()` kirish
        # timeframeiga tushib ketardi: 3.2-band timeframelari qisqarganda
        # bozor kengligi soatlik o'lchovga aylanib, kun bo'yi tebranardi.
        timeframelar = sorted(
            required_timeframes(self._strategies)
            | {self._config.analysis.market_health_timeframe}
        )
        limit = self._config.analysis.candles_lookback
        darvoza = asyncio.Semaphore(self._config.market_data.max_concurrent_candle_requests)

        async def bitta(symbol: str, timeframe: str) -> list[Candle]:
            async with darvoza:
                return await self._candles.fetch_candles(symbol, timeframe, limit)

        async def coin_uchun(symbol: str) -> tuple[str, dict[str, list[Candle]]]:
            natijalar = await asyncio.gather(
                *(bitta(symbol, tf) for tf in timeframelar),
                return_exceptions=True,
            )
            shamlar: dict[str, list[Candle]] = {}
            for tf, natija in zip(timeframelar, natijalar, strict=True):
                if isinstance(natija, Exception):
                    logger.warning("OHLCV yuklanmadi: %s %s (%s)", symbol, tf, natija)
                    continue
                shamlar[tf] = natija
            return symbol, shamlar

        juftlar = await asyncio.gather(*(coin_uchun(s) for s in symbols))
        return dict(juftlar)

    async def compute_health(
        self,
        candles: dict[str, dict[str, list[Candle]]],
        open_signals: int,
    ) -> MarketHealth:
        """3.7-band: Bozor Salomatligi Indeksini hisoblaydi."""
        indicators = self._config.analysis.indicators
        kunlik = self._config.analysis.market_health_timeframe

        strukturalar = {}
        adx_qiymatlari = {}
        for symbol, tf_shamlar in candles.items():
            seriya = tf_shamlar.get(kunlik) or tf_shamlar.get(
                self._config.analysis.entry_timeframe, []
            )
            if not seriya:
                continue
            # Tarix YETARLIMI. Aniqlab bo'lmagan coin hisobga umuman
            # kirmaydi (0.3-band: noaniqlik dalil emas).
            #
            # Chegara 200 dan `min_candles` ga tushdi: u EMA200 uchun
            # kerak edi, EMA esa olib tashlandi. Haftalik timeframeda
            # 200 sham ~3.8 yil tarix degani va ko'p altcoinlar jimgina
            # "ko'tarilishda emas" deb sanalardi — bozor kengligi
            # sun'iy tushib, indeks signalni to'xtatardi (33-bo'lim).
            if len(seriya) < indicators.min_candles:
                continue

            # 3.7-band, ASOSIY omil: SMC strukturasi. Bu "katta rasm
            # ko'tarilishdami" degan REJIM savoli, kirish qarori emas.
            struktura = analyze_structure(
                seriya,
                self._config.analysis.market_structure.swing_lookback,
                self._config.analysis.market_structure.min_swings,
                self._config.analysis.market_structure.fallback_min_pct,
            )
            strukturalar[symbol] = struktura.direction

            qiymat = adx(seriya, indicators.adx_period)
            if qiymat is not None:
                adx_qiymatlari[symbol] = qiymat

        async with self._db.session() as session:
            foydalanuvchilar = await UserRepository(session).active_users(
                self._config.position_sizing.aggregate.active_user_days
            )
            byudjetlar = await self._user_budgets(session, foydalanuvchilar)

        sigim = compute_aggregate_capacity(
            byudjetlar, self._config.position_sizing.aggregate
        )
        limitlar = self._config.risk_engine.max_open_signals_by_health

        # 3.7-band, 1-omil. Olinmasa `None` — omil nol ball oladi, lekin
        # sikl to'xtamaydi (0.3-band).
        dominance = await self._dominance.fetch() if self._dominance else None

        return self._health.compute(
            HealthInputs(
                computed_at=utc_now(),
                btc_dominance=dominance.value if dominance else None,
                btc_dominance_change_24h=dominance.change_24h if dominance else None,
                universe_structures=strukturalar,
                universe_adx=adx_qiymatlari,
                capacity=sigim,
                open_signals=open_signals,
                max_open_signals=limitlar.high,
            )
        )

    async def _user_budgets(self, session, users):  # noqa: ANN001, ANN202
        """5.2-band: foydalanuvchilarning kunlik xavf byudjetlari."""
        sizer = PositionSizer(self._config.position_sizing)
        obunalar = SubscriptionRepository(session)
        byudjetlar = []

        for user in users:
            if user.declared_balance_usd is None or user.declared_balance_usd <= 0:
                continue
            tarif = await obunalar.tier_for(user.id)
            if tarif is None or not tarif.covers(SubscriptionTier.LITE):
                continue
            byudjetlar.append(sizer.budget_for(user.declared_balance_usd))
        return byudjetlar

    # ------------------------------------------------------------------ #
    #  Asosiy sikl
    # ------------------------------------------------------------------ #

    async def run_once(self) -> CycleResult | None:
        """Signal siklini bir marta ishga tushiradi."""
        self._sinovni_ogohlantir()
        if self._universe.is_empty:
            await self.refresh_universe()
        if self._universe.is_empty:
            logger.warning("Halol ro'yxat bo'sh — sikl o'tkazib yuborildi")
            return None

        # BTC halol ro'yxatda bo'lmasligi mumkin (masalan likvidlik
        # filtri yoki admin qarori bilan), lekin 4.5-band filtri unga
        # tayanadi. Shamlari yuklanmasa filtr "BTC holati noma'lum" deb
        # HAMMA NARSANI bloklaydi — shuning uchun u alohida qo'shiladi.
        etalon = self._config.risk_engine.btc_filter.reference_symbol.upper()
        yuklanadigan = list(dict.fromkeys([*self._universe.symbols, etalon]))
        shamlar = await self._load_candles(yuklanadigan)

        async with self._db.session() as session:
            repo = SignalRepository(session)
            ochiq_yozuvlar = await repo.open_signals()
            ochiq_signallar = [SignalRepository.to_domain(y) for y in ochiq_yozuvlar]
            ketma_ket_stop = await repo.consecutive_stops()
            zararlar = await self._zarar_ulushlari(repo)

        salomatlik = await self.compute_health(shamlar, len(ochiq_signallar))
        async with self._db.session() as session:
            await MarketHealthRepository(session).record(salomatlik)

        kirish = self._build_input(
            shamlar, salomatlik, ochiq_signallar, ketma_ket_stop, zararlar
        )
        natija = self._cycle.run(kirish)

        await self._record_rejections(natija, salomatlik)
        await self._record_pipeline_events(natija)

        for nomzod in natija.emitted:
            await self._emit(nomzod, salomatlik, self._joriy_narx(shamlar, nomzod.symbol))

        return natija

    def _sinovni_ogohlantir(self) -> None:
        """Sinov davri kuchda ekanini LOGDA takrorlaydi (60-bo'lim).

        Vaqtincha to'xtatilgan qoida — jimgina o'chirilgan qoidaga
        aylanmasligi kerak. Har siklda bir qatorlik ogohlantirish
        muddat tugaganini ham, hali kuchda ekanini ham ko'rsatib
        turadi.
        """
        sinov = self._config.sinov
        hozir = utc_now()
        if not sinov.faolmi(hozir):
            return
        logger.warning(
            "SINOV DAVRI kuchda (%d kun qoldi): indeksdan chiqarilgan omillar %s, "
            "vaqtincha to'xtatilgan risk qoidalari %s",
            sinov.qolgan_kun(hozir),
            ", ".join(sinov.exclude_health_factors) or "yo'q",
            ", ".join(sinov.suspend_risk_rules) or "yo'q",
        )

    async def _record_rejections(self, result: CycleResult, health: MarketHealth) -> None:
        """3.7-band: nima uchun signal chiqmagani bazaga yoziladi.

        Signal chiqmasligi xato emas (0.2-band), lekin admin sababini
        ko'ra olishi kerak — aks holda ishlayotgan tizimni buzuq tizimdan
        ajratib bo'lmaydi. Jurnal yetarli emas: u aylanadi va Telegram'dan
        ochib bo'lmaydi.

        Yozib bo'lmasa — sikl to'xtamaydi (0.3-band).
        """
        if not result.rejected:
            return

        qatorlar = [
            (None if rad.symbol == "*" else rad.symbol, rad.stage, rad.detail, rad.score)
            for rad in result.rejected
        ]
        try:
            async with self._db.session() as session:
                await RiskBlockRepository(session).record_many(qatorlar, health.value)
        except Exception:  # noqa: BLE001 — kuzatuv yozuvi siklni to'xtatmaydi
            logger.exception("Rad etish sabablarini yozib bo'lmadi")

    async def _record_pipeline_events(self, result: CycleResult) -> None:
        """Jonli tahlil monitori uchun bosqich hodisalarini yozadi (59-bo'lim).

        `derive_events()` butun ketma-ketlikni `CycleResult` dan QAYTA
        TIKLAYDI — strategiya ichiga hech qanday "hodisa yozish"
        chaqiruvi qo'shilmagan. Sabab: tahlil yo'li o'zgarmasligi kerak.

        ESKI YOZUVLAR SHU YERDA TOZALANADI. Alohida fon vazifasi
        qo'yilmadi: sikl allaqachon muntazam ishlaydi, ya'ni tozalash
        uchun ikkinchi jadval kerak emas. Tozalanmasa jadval cheksiz
        o'sardi — har sikl har coin uchun 9-11 qator.

        Yozib bo'lmasa — sikl to'xtamaydi (0.3-band): monitor qulaylik,
        savdo qarori emas.
        """
        hozir = utc_now()
        hodisalar = derive_events(result, hozir)
        if not hodisalar:
            return

        saqlash = self._config.monitoring.pipeline_events
        if not saqlash.enabled:
            return

        try:
            async with self._db.session() as session:
                ombor = PipelineEventRepository(session)
                await ombor.record_many(hodisalar)
                await ombor.purge_older_than(
                    hozir - timedelta(hours=saqlash.retention_hours)
                )
        except Exception:  # noqa: BLE001 — monitor siklni to'xtatmaydi
            logger.exception("Jonli monitor hodisalarini yozib bo'lmadi")

    def _build_input(
        self,
        candles: dict[str, dict[str, list[Candle]]],
        health: MarketHealth,
        open_signals: list,  # noqa: ANN001
        consecutive_stops: int,
        losses: tuple[float, float] = (0.0, 0.0),
    ) -> CycleInput:
        indicators = self._config.analysis.indicators
        entry_tf = self._config.analysis.entry_timeframe

        coinlar = []
        adx_qiymatlari = {}
        atr_qiymatlari = {}
        narx_yoshlari = {}

        for symbol in self._universe.symbols:
            tf_shamlar = candles.get(symbol, {})
            if not tf_shamlar:
                continue
            coinlar.append(
                SymbolData(
                    symbol=symbol,
                    halal_verdict=self._universe.verdicts.get(
                        symbol, HalalVerdict(symbol, HalalStatus.HALAL, "ro'yxatda")
                    ),
                    candles=tf_shamlar,
                )
            )
            seriya = tf_shamlar.get(entry_tf, [])
            if seriya:
                qiymat = adx(seriya, indicators.adx_period)
                if qiymat is not None:
                    adx_qiymatlari[symbol] = qiymat
                atr = atr_pct(seriya, indicators.atr_period)
                if atr is not None:
                    atr_qiymatlari[symbol] = atr
            yosh = self._narx_yoshi(symbol, seriya)
            if yosh is not None:
                narx_yoshlari[symbol] = yosh

        return CycleInput(
            now=utc_now(),
            symbols=coinlar,
            market_health=health,
            open_signals=open_signals,
            adx_values=adx_qiymatlari,
            atr_values=atr_qiymatlari,
            price_ages=narx_yoshlari,
            btc_change_24h_pct=self._btc_ozgarishi(candles),
            daily_loss_pct=losses[0],
            weekly_loss_pct=losses[1],
            consecutive_stops=consecutive_stops,
            kill_switch_active=self._watcher.kill_switch_active,
            kill_switch_reason=self._watcher.kill_switch_reason,
        )

    def _narx_yoshi(self, symbol: str, series: list[Candle]) -> float | None:
        """Shu coin uchun eng so'nggi narx kuzatuvining yoshi (soniyada).

        DEADLOCK TUZATILDI. Ilgari bu faqat tik keshidan olinardi:

            yosh = self._watcher.prices.age_seconds(symbol)

        Tik keshini esa `SignalWatcher` to'ldiradi va u FAQAT OCHIQ
        SIGNALLAR coinlariga obuna bo'ladi. Ya'ni:

            0 ta ochiq signal -> obuna bo'sh -> kesh bo'sh -> yosh None
            -> `FreshDataRule` bloklaydi -> yangi signal yo'q
            -> 0 ta ochiq signal

        Tizim birinchi signalini HECH QACHON chiqara olmasdi. Jonli
        o'lchovda bu 72 soat davomida "Risk Engine to'xtatdi" bo'lib
        ko'rinardi.

        To'g'ri manba — SHAM. Signal qarori shamdan olingan narxga
        tayanadi (`_joriy_narx()`), tik oqimi esa kuzatuvchining ishi:
        u yerda signal ochiq bo'lgani uchun obuna ham bor va tekshiruv
        haqiqatan ishlaydi. Har qatlam O'ZI ISHLATADIGAN ma'lumotni
        tekshiradi.

        Tik mavjud bo'lsa u afzal — u aniqroq.
        """
        tik = self._watcher.prices.age_seconds(symbol)
        if tik is not None:
            return tik
        if not series:
            return None
        return max(0.0, (utc_now() - series[-1].open_time).total_seconds())

    @staticmethod
    async def _zarar_ulushlari(repo: SignalRepository) -> tuple[float, float]:
        """4.1-band: `(kunlik zarar %, haftalik zarar %)`.

        E'LON QILINGAN, LEKIN ULANMAGAN edi: `DailyLossLimitRule` bor,
        `daily_loss_limit_pct: 3.0` sozlamasi bor, lekin qiymat hech
        qachon hisoblanmasdi va standart `0.0` bo'lib qolardi. Ya'ni
        chegara HECH QACHON to'lmasdi — strategiya qancha zarar
        keltirsa ham signal berishda davom etardi.

        Zarar MUSBAT son sifatida qaytariladi (qoida shunday kutadi).
        Kun foyda bilan tugagan bo'lsa — nol.
        """
        hozir = utc_now()
        kun_boshi = hozir.replace(hour=0, minute=0, second=0, microsecond=0)
        hafta_boshi = hozir - timedelta(days=7)

        kunlik = await repo.net_result_pct_since(kun_boshi)
        haftalik = await repo.net_result_pct_since(hafta_boshi)
        return max(0.0, -kunlik), max(0.0, -haftalik)

    def _btc_ozgarishi(self, candles: dict) -> float | None:  # noqa: ANN001
        """BTC ning 24 soatlik o'zgarishi, foizda (4.5-band filtri uchun).

        E'LON QILINGAN, LEKIN ULANMAGAN edi. `BtcMarketRule` bor,
        `BtcFilterConfig` bor, `CycleInput.btc_change_24h_pct` maydoni
        ham bor — lekin uni HECH KIM to'ldirmasdi. Qiymat doim `None`
        bo'lib qolardi va qoida fail-safe tarmog'iga tushardi:

            "BTC holati noma'lum — umumiy bozor filtri tekshirilmadi."

        Ya'ni ball chegarasidan o'tgan HAR BIR nomzod shu yerda
        to'xtardi. Jonli o'lchovda: 119 tadan 119 tasi.

        Timeframe konfiguratsiyadan olinadi, lekin u yuklanmagan bo'lsa
        kirish timeframeiga tushiladi — aks holda sozlama o'zgarganda
        filtr yana jimgina "noma'lum" holatiga qaytardi.
        """
        filtr = self._config.risk_engine.btc_filter
        tf_shamlar = candles.get(filtr.reference_symbol.upper(), {})
        if not tf_shamlar:
            return None

        timeframe = (
            filtr.timeframe
            if filtr.timeframe in tf_shamlar
            else self._config.analysis.entry_timeframe
        )
        seriya = tf_shamlar.get(timeframe, [])
        kerak = max(1, MINUTES_PER_DAY // timeframe_minutes(timeframe))
        if len(seriya) <= kerak:
            return None

        avvalgi = seriya[-1 - kerak].close
        if avvalgi <= 0:
            return None
        return (seriya[-1].close - avvalgi) / avvalgi * 100

    def _joriy_narx(self, candles: dict, symbol: str) -> float | None:  # noqa: ANN001
        """Kirish timeframedagi oxirgi yopilish narxi."""
        seriya = candles.get(symbol, {}).get(self._config.analysis.entry_timeframe, [])
        return seriya[-1].close if seriya else None

    async def _emit(
        self,
        candidate,  # noqa: ANN001
        health: MarketHealth,
        current_price: float | None = None,
    ) -> None:
        """Nomzodni bazaga yozadi, kuzatuvga qo'shadi va tarqatadi.

        `current_price` — BOZORDAGI haqiqiy narx. Avval bu yerga
        `levels.entry` uzatilardi, ya'ni "joriy narx = kirish narxi" deb
        hisoblanardi. Natijada buyurtma turi HAR DOIM Market chiqardi,
        kuzatuvchi esa haqiqiy narxni ko'rib "Kutilmoqda" derdi — bitta
        xabarda ikkita qarama-qarshi gap.
        """
        reja = decide_entry_plan(
            current_price if current_price else candidate.levels.entry,
            candidate.levels,
            self._config.analysis.entry_order,
        )

        async with self._db.session() as session:
            yozuv = await SignalRepository(session).create(
                symbol=candidate.symbol,
                levels=candidate.levels,
                source=candidate.source,
                entry_plan=reja,
                score=candidate.score,
                score_breakdown=breakdown_to_json(candidate.breakdown),
                halal_reason=candidate.halal_verdict.reason,
                market_health=health.value,
                correlation_group=self._config.risk_engine.correlation_group_of(
                    candidate.symbol
                ),
            )
            signal_id = yozuv.id
            qabul_qiluvchilar = await obunachilar(session)

        self._watcher.add_signal(signal_id)

        yuborildi = await broadcast_signal(
            self._bot,
            qabul_qiluvchilar,
            candidate.symbol,
            candidate.levels,
            reja,
            signal_id,
            self._config,
        )

        # Tarqatilgani belgilanadi, aks holda fon vazifasi uni "hali
        # yuborilmagan" deb topib IKKINCHI MARTA yuborardi.
        async with self._db.session() as session:
            await SignalRepository(session).mark_broadcast(signal_id)

        logger.info(
            "Avtomatik signal yuborildi: %s (ball %.0f) -> %d ta",
            candidate.symbol, candidate.score, yuborildi,
        )

    async def review_open_signals(self, result: CycleResult | None) -> None:
        """Faol signallarni qayta baholab, zaiflashish va rotatsiyani tekshiradi."""
        if result is None:
            return

        async with self._db.session() as session:
            ochiqlar = await SignalRepository(session).open_signals()

        zaiflar: list[tuple] = []
        for yozuv in ochiqlar:
            yangi_ball = self._current_score(yozuv.symbol, result)
            if yangi_ball is None:
                continue

            signal = SignalRepository.to_domain(yozuv)
            ogohlantirish = self._monitor.check_weakening(signal, yangi_ball)
            if ogohlantirish is not None:
                zaiflar.append((signal, yangi_ball))
                await self._notify_weakening(signal)

        tavsiya = self._monitor.suggest_rotation(zaiflar, result.emitted, utc_now())
        if tavsiya is not None:
            await self._broadcast(tavsiya.describe())

    @staticmethod
    def _current_score(symbol: str, result: CycleResult) -> float | None:
        tafsilot = result.breakdowns.get(symbol)
        return tafsilot.total if tafsilot else None

    async def _notify_weakening(self, signal) -> None:  # noqa: ANN001
        matn = t(
            "signal.yangilandi",
            DEFAULT_LANGUAGE,
            emoji="⚠️",
            symbol=signal.symbol,
            status=t("signal.holat_weakening", DEFAULT_LANGUAGE),
        )
        await self._broadcast(matn)

    async def _broadcast(self, text: str) -> None:
        async with self._db.session() as session:
            qabul_qiluvchilar = await obunachilar(session)
        for telegram_id in qabul_qiluvchilar:
            try:
                await self._bot.send_message(telegram_id, text, protect_content=True)
            except Exception:  # noqa: BLE001
                logger.warning("Xabar yetkazilmadi: telegram_id=%s", telegram_id)


def cycle_interval(config: AppConfig) -> timedelta:
    """Sikl qanchalik tez-tez ishga tushadi.

    Kirish timeframega bog'liq: 15 daqiqalik shamda har 15 daqiqada
    tekshirish yetarli. Tez-tez ishga tushirish foyda bermaydi — sham
    yopilmaguncha tahlil natijasi o'zgarmaydi.
    """
    xarita = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
    daqiqa = xarita.get(config.analysis.entry_timeframe, 15)
    return timedelta(minutes=daqiqa)
