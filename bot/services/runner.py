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

from bot.formatting import render_signal_card
from bot.i18n import DEFAULT_LANGUAGE, t
from bot.keyboards import signal_actions
from core.analysis import decide_entry_plan
from core.analysis.indicators import adx, atr_pct, timeframe_trend
from core.analysis.market_health import HealthInputs, MarketHealthCalculator
from core.analysis.scoring import breakdown_to_json
from core.analysis.strategies import build_strategies, required_timeframes
from core.config.schema import AppConfig
from core.domain.enums import HalalStatus, SubscriptionTier
from core.domain.models import Candle, HalalVerdict, MarketHealth
from core.halal_screening import HalalScreener, StaticRulingRegistry
from core.market_data import CandleProvider, RankingProvider
from core.market_data.ranking import RankingUnavailableError
from core.pipeline import CycleInput, CycleResult, SignalCycle, SignalMonitor, SymbolData
from core.position_sizing import compute_aggregate_capacity
from core.storage import Database
from core.storage.repositories import (
    CoinRulingRepository,
    MarketHealthRepository,
    RiskBlockRepository,
    SignalRepository,
    SubscriptionRepository,
    UserRepository,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)


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
    ) -> None:
        self._bot = bot
        self._db = database
        self._config = config
        self._candles = candles
        self._ranking = ranking
        self._watcher = watcher

        self._strategies = build_strategies(config)
        self._cycle = SignalCycle(config, self._strategies)
        self._monitor = SignalMonitor(config.risk_engine)
        self._health = MarketHealthCalculator(config)
        self._universe = UniverseCache(symbols=[], verdicts={})

    # ------------------------------------------------------------------ #
    #  3.4 — Halol ro'yxatni yangilash
    # ------------------------------------------------------------------ #

    async def refresh_universe(self) -> UniverseCache:
        """Top 30 Halal ro'yxatini qayta hisoblaydi."""
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
        """Barcha coinlar uchun kerakli timeframelarni PARALLEL yuklaydi."""
        timeframelar = sorted(required_timeframes(self._strategies))
        limit = self._config.analysis.candles_lookback

        async def coin_uchun(symbol: str) -> tuple[str, dict[str, list[Candle]]]:
            natijalar = await asyncio.gather(
                *(self._candles.fetch_candles(symbol, tf, limit) for tf in timeframelar),
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
        kunlik = "1d"

        trendlar = {}
        adx_qiymatlari = {}
        for symbol, tf_shamlar in candles.items():
            seriya = tf_shamlar.get(kunlik) or tf_shamlar.get(
                self._config.analysis.entry_timeframe, []
            )
            if not seriya:
                continue
            trendlar[symbol] = timeframe_trend(
                seriya,
                indicators.ema_fast,
                indicators.ema_slow,
                indicators.trend_requires_price_above_fast,
            )
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

        return self._health.compute(
            HealthInputs(
                computed_at=utc_now(),
                btc_dominance=None,  # TODO(17): dominance manbai ulanadi
                btc_dominance_change_24h=None,
                universe_trends=trendlar,
                universe_adx=adx_qiymatlari,
                capacity=sigim,
                open_signals=open_signals,
                max_open_signals=limitlar.high,
            )
        )

    async def _user_budgets(self, session, users):  # noqa: ANN001, ANN202
        """5.2-band: foydalanuvchilarning kunlik xavf byudjetlari."""
        from core.position_sizing import PositionSizer

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
        if self._universe.is_empty:
            await self.refresh_universe()
        if self._universe.is_empty:
            logger.warning("Halol ro'yxat bo'sh — sikl o'tkazib yuborildi")
            return None

        shamlar = await self._load_candles(self._universe.symbols)

        async with self._db.session() as session:
            repo = SignalRepository(session)
            ochiq_yozuvlar = await repo.open_signals()
            ochiq_signallar = [SignalRepository.to_domain(y) for y in ochiq_yozuvlar]
            ketma_ket_stop = await repo.consecutive_stops()

        salomatlik = await self.compute_health(shamlar, len(ochiq_signallar))
        async with self._db.session() as session:
            await MarketHealthRepository(session).record(salomatlik)

        kirish = self._build_input(shamlar, salomatlik, ochiq_signallar, ketma_ket_stop)
        natija = self._cycle.run(kirish)

        await self._record_rejections(natija, salomatlik)

        for nomzod in natija.emitted:
            await self._emit(nomzod, salomatlik)

        return natija

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
            (None if rad.symbol == "*" else rad.symbol, rad.stage, rad.detail)
            for rad in result.rejected
        ]
        try:
            async with self._db.session() as session:
                await RiskBlockRepository(session).record_many(qatorlar, health.value)
        except Exception:  # noqa: BLE001 — kuzatuv yozuvi siklni to'xtatmaydi
            logger.exception("Rad etish sabablarini yozib bo'lmadi")

    def _build_input(
        self,
        candles: dict[str, dict[str, list[Candle]]],
        health: MarketHealth,
        open_signals: list,  # noqa: ANN001
        consecutive_stops: int,
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
            yosh = self._watcher.prices.age_seconds(symbol)
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
            consecutive_stops=consecutive_stops,
            kill_switch_active=self._watcher.kill_switch_active,
            kill_switch_reason=self._watcher.kill_switch_reason,
        )

    async def _emit(self, candidate, health: MarketHealth) -> None:  # noqa: ANN001
        """Nomzodni bazaga yozadi, kuzatuvga qo'shadi va tarqatadi."""
        reja = decide_entry_plan(
            candidate.levels.entry, candidate.levels, self._config.analysis.entry_order
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
            qabul_qiluvchilar = await self._subscribers(session)

        self._watcher.add_signal(signal_id)

        kartochka = render_signal_card(
            candidate.symbol,
            candidate.levels,
            reja,
            quote_asset=self._config.halal_screening.quote_asset,
        )
        for telegram_id in qabul_qiluvchilar:
            try:
                await self._bot.send_message(
                    telegram_id,
                    kartochka,
                    protect_content=True,
                    reply_markup=signal_actions(signal_id, DEFAULT_LANGUAGE),
                )
            except Exception:  # noqa: BLE001
                logger.warning("Signal yetkazilmadi: telegram_id=%s", telegram_id)

        logger.info("Avtomatik signal yuborildi: %s (ball %.0f)", candidate.symbol, candidate.score)

    async def _subscribers(self, session) -> list[int]:  # noqa: ANN001
        users = UserRepository(session)
        obunalar = SubscriptionRepository(session)
        natija = []
        for user in await users.active_users(since_days=90):
            tarif = await obunalar.tier_for(user.id)
            if tarif is not None and tarif.covers(SubscriptionTier.LITE):
                natija.append(user.telegram_id)
        return natija

    # ------------------------------------------------------------------ #
    #  4.1 / 4.2 — Faol signallarni qayta baholash
    # ------------------------------------------------------------------ #

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
            qabul_qiluvchilar = await self._subscribers(session)
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
