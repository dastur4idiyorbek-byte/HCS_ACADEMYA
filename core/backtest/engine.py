"""6.3-band: backtest dvigateli — tarixiy ma'lumotda strategiyani sinash.

Spetsifikatsiya buni MAJBURIY deb belgilaydi: "jonli pulga qo'yishdan
oldin kamida 1-2 yillik tarixiy ma'lumotda sinash".

ASOSIY QARORI: backtest jonli tizim bilan BIR XIL kodni ishlatadi —
`SignalCycle` va `SignalTracker` o'zgarishsiz. Agar backtest o'z nusxasini
ishlatganda, ikki xil kod ikki xil natija berardi va sinovning ma'nosi
qolmasdi.

Bu 15-bosqichdagi ikki qatlamli tuzilma tufayli mumkin: sikl sof, u faqat
`CycleInput` ni oladi. Bu yerda uni jonli manba emas, tarixiy ma'lumot
to'ldiradi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.analysis.indicators import adx, atr_pct, timeframe_trend
from core.analysis.market_health import HealthInputs, MarketHealthCalculator
from core.analysis.strategies import build_strategies
from core.backtest.dataset import Dataset
from core.config.schema import AppConfig
from core.domain.enums import SignalStatus
from core.domain.models import HalalVerdict, Signal
from core.pipeline import CycleInput, SignalCycle, SymbolData
from core.signals import SignalEventKind, SignalTracker
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class BacktestTrade:
    """Backtestda yopilgan bitta savdo."""

    symbol: str
    source: str
    score: float
    market_health: float
    opened_at: datetime
    closed_at: datetime
    entry: float
    exit_price: float
    outcome: str
    reached_tp1: bool
    result_pct: float

    @property
    def is_win(self) -> bool:
        return self.outcome in {"tp2_hit", "tp1_then_stop"}

    @property
    def holding_hours(self) -> float:
        return (self.closed_at - self.opened_at).total_seconds() / 3600


@dataclass(slots=True)
class BacktestResult:
    """Backtest natijasi."""

    label: str
    trades: list[BacktestTrade] = field(default_factory=list)
    signals_emitted: int = 0
    signals_expired: int = 0
    steps: int = 0
    rejections: dict[str, int] = field(default_factory=dict)
    #: Chegaradan o'tmagan nomzodlarning ballari — chegarani sozlash uchun
    #: (3.5-band). Nol signal chiqqanda "umuman nomzod yo'q edi"mi yoki
    #: "nomzod bor edi, lekin ball yetmadi"mi — shuni ajratadi.
    near_miss_scores: list[float] = field(default_factory=list)

    @property
    def closed(self) -> int:
        return len(self.trades)

    @property
    def win_rate(self) -> float | None:
        if not self.trades:
            return None
        return sum(1 for t in self.trades if t.is_win) / len(self.trades)

    @property
    def tp2_rate(self) -> float | None:
        if not self.trades:
            return None
        return sum(1 for t in self.trades if t.outcome == "tp2_hit") / len(self.trades)

    @property
    def total_return_pct(self) -> float:
        """Har bir savdoga teng miqdor qo'yilgan deb hisoblangan yig'indi."""
        return sum(t.result_pct for t in self.trades)

    @property
    def average_result_pct(self) -> float | None:
        if not self.trades:
            return None
        return self.total_return_pct / len(self.trades)

    @property
    def max_drawdown_pct(self) -> float:
        """Eng katta ketma-ket pasayish — risk o'lchovi.

        Win-rate yuqori bo'lsa ham, chuqur pasayish foydalanuvchini
        strategiyadan chiqarib yuboradi. Shuning uchun bu raqam
        win-rate'dan kam ahamiyatli emas.
        """
        cho_qqi = 0.0
        joriy = 0.0
        eng_katta = 0.0
        for savdo in sorted(self.trades, key=lambda t: t.closed_at):
            joriy += savdo.result_pct
            cho_qqi = max(cho_qqi, joriy)
            eng_katta = max(eng_katta, cho_qqi - joriy)
        return eng_katta

    @property
    def max_consecutive_losses(self) -> int:
        eng_uzun = joriy = 0
        for savdo in sorted(self.trades, key=lambda t: t.closed_at):
            joriy = 0 if savdo.is_win else joriy + 1
            eng_uzun = max(eng_uzun, joriy)
        return eng_uzun

    @property
    def average_holding_hours(self) -> float | None:
        if not self.trades:
            return None
        return sum(t.holding_hours for t in self.trades) / len(self.trades)

    def top_rejections(self, limit: int = 5) -> list[tuple[str, int]]:
        return sorted(self.rejections.items(), key=lambda kv: kv[1], reverse=True)[:limit]

    @property
    def best_near_miss(self) -> float | None:
        """Chegaradan o'tmagan nomzodlarning eng yuqori bali.

        Nol savdo chiqqanda eng muhim raqam shu: agar bu 68 bo'lsa,
        chegara (70) deyarli to'g'ri sozlangan; agar 35 bo'lsa, muammo
        chegarada emas — zanjirning oldingi qismida.
        """
        return max(self.near_miss_scores) if self.near_miss_scores else None

    @property
    def average_near_miss(self) -> float | None:
        if not self.near_miss_scores:
            return None
        return sum(self.near_miss_scores) / len(self.near_miss_scores)


class Backtester:
    """Tarixiy ma'lumotda signal siklini qayta o'ynatadi."""

    def __init__(self, config: AppConfig, label: str = "standart") -> None:
        self._config = config
        self._label = label
        self._strategies = build_strategies(config)
        self._cycle = SignalCycle(config, self._strategies)
        self._health = MarketHealthCalculator(config)

    def run(
        self,
        dataset: Dataset,
        verdicts: dict[str, HalalVerdict] | None = None,
        max_steps: int | None = None,
    ) -> BacktestResult:
        """Backtestni bajaradi.

        Har bir qadam — kirish timeframedagi bitta sham. Sikl faqat o'sha
        paytgacha mavjud ma'lumotni ko'radi (lookahead yo'q).
        """
        entry_tf = self._config.analysis.entry_timeframe
        qadamlar = dataset.timeline(entry_tf)

        eng_kam = self._warmup_steps()
        if len(qadamlar) <= eng_kam:
            logger.warning(
                "Backtest uchun ma'lumot yetarli emas: %d qadam, kamida %d kerak "
                "(eng yuqori timeframedagi EMA%d uchun)",
                len(qadamlar),
                eng_kam,
                self._config.analysis.indicators.ema_slow,
            )
            return BacktestResult(label=self._label, steps=0)

        # Isinish davridan KEYINGI qadamlar cheklanadi — `max_steps` haqiqiy
        # tahlil qadamlarini bildiradi, tarixni emas.
        baholanadigan = qadamlar[eng_kam:]
        if max_steps is not None:
            baholanadigan = baholanadigan[:max_steps]

        qarorlar = verdicts or {}
        tracker = SignalTracker()
        natija = BacktestResult(label=self._label)
        signal_id = 0
        #: signal kaliti -> (ochilish vaqti, ball, salomatlik, TP1 olindimi)
        kontekst: dict[int, dict] = {}

        for hozir in baholanadigan:
            natija.steps += 1

            # 1) Narxlarni kuzatuvchiga uzatamiz (holat o'zgarishlari)
            self._advance_tracker(tracker, dataset, hozir, entry_tf, natija, kontekst)

            # 2) Siklni ishga tushiramiz
            kirish = self._build_input(dataset, hozir, tracker, qarorlar, entry_tf)
            if not kirish.symbols:
                continue

            sikl_natijasi = self._cycle.run(kirish)
            for rad in sikl_natijasi.rejected:
                natija.rejections[rad.stage] = natija.rejections.get(rad.stage, 0) + 1
                if rad.stage == "threshold" and rad.score is not None:
                    natija.near_miss_scores.append(rad.score)

            # 3) Chiqqan signallarni kuzatuvga qo'shamiz
            for nomzod in sikl_natijasi.emitted:
                signal_id += 1
                signal = Signal(
                    symbol=nomzod.symbol,
                    levels=nomzod.levels,
                    source=nomzod.source,
                    score=nomzod.score,
                    created_at=hozir,
                    signal_id=signal_id,
                )
                kalit = tracker.track(signal)
                kontekst[kalit] = {
                    "opened_at": hozir,
                    "score": nomzod.score,
                    "health": kirish.market_health.value if kirish.market_health else 0.0,
                    "source": nomzod.source.value,
                    "tp1": False,
                }
                natija.signals_emitted += 1

        logger.info(
            "%s: %d qadam, %d signal, %d savdo yopildi",
            self._label,
            natija.steps,
            natija.signals_emitted,
            natija.closed,
        )
        return natija

    def _warmup_steps(self) -> int:
        """Necha qadam o'tgach tahlil boshlanadi.

        MUHIM: eng yuqori timeframedagi EMA'ga yetarli tarix kerak. Kunlik
        shamda EMA200 uchun 200 KUNLIK ma'lumot kerak — kirish timeframeda
        bu 200 × 96 = 19 200 qadam (15 daqiqalik shamda).

        Buni faqat kirish timeframe bo'yicha hisoblash — jimgina buziladigan
        xato: yuqori timeframelarda EMA hisoblanmaydi, trend `FLAT` qaytadi
        va ko'p timeframe muvofiqligi HECH QACHON bajarilmaydi. Backtest
        "signal yo'q" deb ko'rsatadi, sabab esa strategiyada emas,
        ma'lumot yetishmasligida bo'ladi.
        """
        from core.backtest.dataset import TIMEFRAME_MINUTES

        analysis = self._config.analysis
        kirish_daqiqa = TIMEFRAME_MINUTES.get(analysis.entry_timeframe, 15)
        eng_yuqori = max(
            (TIMEFRAME_MINUTES.get(tf, kirish_daqiqa) for tf in analysis.htf_confirmation),
            default=kirish_daqiqa,
        )
        nisbat = max(1, eng_yuqori // kirish_daqiqa)
        return analysis.indicators.ema_slow * nisbat + 10

    # ------------------------------------------------------------------ #

    def _advance_tracker(
        self,
        tracker: SignalTracker,
        dataset: Dataset,
        moment: datetime,
        entry_tf: str,
        result: BacktestResult,
        context: dict[int, dict],
    ) -> None:
        """Har bir ochiq signalni shu qadamdagi narx bilan yangilaydi.

        Sham ichidagi harakat tartibi noma'lum, shuning uchun ENG YOMON
        talqin olinadi: avval past (Stop), keyin baland (TP). Bu backtest
        natijasini haqiqatdan yomonroq ko'rsatishi mumkin, lekin yaxshiroq
        ko'rsatishidan afzal (0.3 va 3.6-band).
        """
        for symbol in {s.symbol for s in tracker.open_signals}:
            shamlar = dataset.window(symbol, moment).get(entry_tf, [])
            if not shamlar:
                continue
            sham = shamlar[-1]

            for narx in (sham.low, sham.high, sham.close):
                for hodisa in tracker.on_price(symbol, narx, moment):
                    self._record_event(hodisa, tracker, result, context)

        for hodisa in tracker.check_expiry(moment):
            if hodisa.kind is SignalEventKind.CANCELLED:
                result.signals_expired += 1

    def _record_event(self, event, tracker, result, context) -> None:  # noqa: ANN001
        """Hodisani qayd etadi; yopilgan signalni savdoga aylantiradi."""
        kalit = event.signal_id
        if kalit is None or kalit not in context:
            return

        if event.kind is SignalEventKind.TP1_HIT:
            context[kalit]["tp1"] = True
            return

        if not event.closes_signal:
            return
        if event.kind is SignalEventKind.CANCELLED:
            return

        ma_lumot = context.pop(kalit)
        signal = tracker.get(kalit)
        tp1_olindi = ma_lumot["tp1"]

        if event.new_status is SignalStatus.TP2_HIT:
            natija_turi = "tp2_hit"
        elif tp1_olindi:
            natija_turi = "tp1_then_stop"
        else:
            natija_turi = "stop"

        chiqish = self._fill_price(signal, event)

        result.trades.append(
            BacktestTrade(
                symbol=event.symbol,
                source=ma_lumot["source"],
                score=ma_lumot["score"],
                market_health=ma_lumot["health"],
                opened_at=ma_lumot["opened_at"],
                closed_at=event.at,
                entry=signal.levels.entry,
                exit_price=chiqish,
                outcome=natija_turi,
                reached_tp1=tp1_olindi,
                result_pct=self._result_pct(signal, chiqish, tp1_olindi),
            )
        )

    def _fill_price(self, signal, event) -> float:  # noqa: ANN001
        """Buyurtma QAYSI narxda bajarilgan deb hisoblanadi.

        Kuzatuvchiga sham ichidagi eng past va eng baland narx beriladi, va
        aynan shu narx hodisada qaytadi. Lekin chiqish buyurtmasi — OCO
        (5.1.0-band): Stop yoki TP darajaga TEGILGANDA bajariladi, shamning
        eng chekka nuqtasida emas. Sham ichida narx daraja orqali uzluksiz
        o'tadi, shuning uchun to'g'ri to'ldirish narxi — darajaning O'ZI.

        Hodisa narxini olish natijani shamning kattaligiga bog'lab qo'yardi:
        keng sham "yomonroq" stop bergandek ko'rinardi, garchi buyurtma
        o'sha 1% darajada bajarilgan bo'lsa ham. O'lchangan misol: stop
        masofasi 1% bo'lgan savdolar -1.05% dan -1.66% gacha natija berardi.

        Cheklov: bu yerda haqiqiy uzilish (gap) modellashtirilmaydi. Sham
        ochilishi darajadan nariga sakrasa, jonli savdoda to'ldirish
        yomonroq bo'ladi. Kuzatuvchiga faqat low/high/close beriladi,
        shuning uchun bu farq ko'rinmaydi. 15 daqiqalik spot grafikda
        uzilish kam uchraydi, lekin natijalarni o'qiganda esda tutilsin.
        """
        darajalar = signal.levels
        if event.new_status is SignalStatus.TP2_HIT:
            # Narx TP2 orqali YUQORIGA o'tdi -> buyurtma TP2 darajada bajarildi
            return darajalar.tp2
        if event.new_status is SignalStatus.STOPPED:
            # Narx Stop orqali PASTGA o'tdi -> buyurtma Stop darajada bajarildi
            return darajalar.stop
        return event.price

    def _result_pct(self, signal, exit_price: float, reached_tp1: bool) -> float:  # noqa: ANN001
        """5.4-banddagi qismli yopish qoidasi bilan bir xil hisob."""
        entry = signal.levels.entry
        if not reached_tp1:
            return (exit_price - entry) / entry * 100

        ulush = self._config.portfolio.tp1_close_pct / 100
        tp1_foizi = (signal.levels.tp1 - entry) / entry * 100
        qolgan = (exit_price - entry) / entry * 100
        return tp1_foizi * ulush + qolgan * (1 - ulush)

    def _build_input(
        self,
        dataset: Dataset,
        moment: datetime,
        tracker: SignalTracker,
        verdicts: dict[str, HalalVerdict],
        entry_tf: str,
    ) -> CycleInput:
        indicators = self._config.analysis.indicators
        coinlar = []
        adx_qiymatlari = {}
        atr_qiymatlari = {}
        trendlar = {}

        for symbol in dataset.symbols:
            oyna = dataset.window(symbol, moment)
            seriya = oyna.get(entry_tf, [])
            if len(seriya) < indicators.ema_slow:
                continue

            coinlar.append(
                SymbolData(
                    symbol=symbol,
                    halal_verdict=verdicts.get(
                        symbol,
                        HalalVerdict(symbol, __import__(
                            "core.domain.enums", fromlist=["HalalStatus"]
                        ).HalalStatus.HALAL, "backtest"),
                    ),
                    candles=oyna,
                )
            )

            qiymat = adx(seriya, indicators.adx_period)
            if qiymat is not None:
                adx_qiymatlari[symbol] = qiymat
            atr = atr_pct(seriya, indicators.atr_period)
            if atr is not None:
                atr_qiymatlari[symbol] = atr
            trendlar[symbol] = timeframe_trend(
                seriya,
                indicators.ema_fast,
                indicators.ema_slow,
                indicators.trend_requires_price_above_fast,
            )

        limitlar = self._config.risk_engine.max_open_signals_by_health
        ochiqlar = tracker.open_signals

        salomatlik = self._health.compute(
            HealthInputs(
                computed_at=moment,
                # BTC dominance tarixi backtestda mavjud emas — neytral
                # qiymat olinadi. Bu OSHIRIB ko'rsatish emas: dominance
                # ma'lumoti bo'lsa, natija yaxshiroq bo'lishi mumkin.
                btc_dominance_change_24h=0.0,
                universe_trends=trendlar,
                universe_adx=adx_qiymatlari,
                capacity=None,
                open_signals=len(ochiqlar),
                max_open_signals=limitlar.high,
            )
        )

        return CycleInput(
            now=moment,
            symbols=coinlar,
            market_health=salomatlik,
            open_signals=ochiqlar,
            btc_change_24h_pct=0.0,
            adx_values=adx_qiymatlari,
            atr_values=atr_qiymatlari,
            price_ages=dict.fromkeys(adx_qiymatlari, 0.0),
        )
