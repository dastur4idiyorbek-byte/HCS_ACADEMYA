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

from core.analysis.indicators import atr_pct
from core.analysis.market_health import (
    HealthInputs,
    MarketHealthCalculator,
    universe_facts,
)
from core.analysis.strategies import build_strategies
from core.backtest.dataset import Dataset
from core.backtest.warmup import warmup_steps, warmup_timeframes
from core.config.schema import AppConfig
from core.domain.enums import HalalStatus, SignalStatus
from core.domain.models import Candle, HalalVerdict, Signal
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


#: R/R ni foizdan nisbatga aylantirish uchun shartli birlik — 1% harakat
#: bir "R" deb olinadi, chunki backtest har savdoga teng miqdor qo'yadi.
_RR_BIRLIGI = 1.0


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
    #: TAYANCH: sinov davrida coinni shunchaki olib ushlab turgan
    #: bo'lsak, o'rtacha necha foiz bo'lardi.
    #:
    #: Ansiz "o'rtacha -0.73%" degan raqamning o'lchovi yo'q. Yomonmi?
    #: NIMAGA nisbatan? Agar coinlar o'sgan bo'lsa, strategiya nafaqat
    #: zarar keltirgan, balki HECH NARSA QILMASLIKDAN ham yomon
    #: ishlagan bo'ladi. Agar tushgan bo'lsa — raqam boshqacha
    #: o'qiladi.
    #:
    #: `None` — hisoblab bo'lmadi (ma'lumot yetarli emas).
    buy_and_hold_pct: float | None = None

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

    @property
    def profit_factor(self) -> float | None:
        """Yalpi foyda / yalpi zarar.

        Win-rate o'zi yetarli emas: 80% g'alaba, lekin har zarar
        g'alabadan uch barobar katta bo'lsa strategiya zarar keltiradi.
        Profit factor ikkalasini bitta raqamga jamlaydi (>1 — foydali).

        `None` — zarar umuman bo'lmagan (bo'lishga bo'lish).
        """
        foyda = sum(t.result_pct for t in self.trades if t.result_pct > 0)
        zarar = -sum(t.result_pct for t in self.trades if t.result_pct < 0)
        if zarar <= 0:
            return None
        return foyda / zarar

    @property
    def average_realised_rr(self) -> float | None:
        """HAQIQATDA olingan o'rtacha R/R.

        Rejalashtirilgan nisbat (masalan 1:1.5) va bajarilgani boshqa
        narsa: savdolarning bir qismi Stop bilan yopiladi. Bu raqam
        rejaning amalda nimaga aylanganini ko'rsatadi.
        """
        if not self.trades:
            return None
        return sum(t.result_pct for t in self.trades) / len(self.trades) / _RR_BIRLIGI

    def funnel(self) -> list[tuple[str, int, int, int, float]]:
        """Voronka: `(bosqich, kirdi, rad etildi, o'tdi, o'tish %)`.

        Rad etishlar bosqichma-bosqich yig'ilgani uchun har bosqichga
        kirganlar soni — undan keyingi barcha rad etishlar va chiqqan
        signallar yig'indisi.
        """
        tartib = ["zone_position", "levels", "threshold", "risk_engine"]
        yigilgan: dict[str, int] = {}
        for bosqich, soni in self.rejections.items():
            kalit = next((t for t in tartib if t in bosqich), None)
            if kalit is not None:
                yigilgan[kalit] = yigilgan.get(kalit, 0) + soni

        qolgan = sum(yigilgan.values()) + self.signals_emitted
        qatorlar = []
        for bosqich in tartib:
            rad = yigilgan.get(bosqich, 0)
            if qolgan <= 0:
                break
            otdi = qolgan - rad
            qatorlar.append((bosqich, qolgan, rad, otdi, otdi / qolgan * 100))
            qolgan = otdi
        return qatorlar

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
        # Har qadamda strategiyaga beriladigan tarix oynasi. Jonli
        # tizim birjadan aynan shuncha sham so'raydi (`runner.py`),
        # ya'ni indikatorlar ham shu oynada hisoblanadi. Backtest
        # butun tarixni bersa, ADX va S/R zonalari BOSHQA oynada
        # chiqadi — sinov jonli qarorni emas, boshqa qarorni
        # o'lchagan bo'lardi.
        self._oyna = config.analysis.candles_lookback
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
                "(isinish uchun — %s timeframelarida %d sham). `--days` ni "
                "oshiring: skript sinov oynasidan tashqari isinish tarixini "
                "ham yuklaydi.",
                len(qadamlar),
                eng_kam,
                ", ".join(warmup_timeframes(self._config)),
                self._config.analysis.indicators.min_candles,
            )
            return BacktestResult(label=self._label, steps=0)

        # Isinish davridan KEYINGI qadamlar cheklanadi — `max_steps` haqiqiy
        # tahlil qadamlarini bildiradi, tarixni emas.
        baholanadigan = qadamlar[eng_kam:]
        if max_steps is not None:
            baholanadigan = baholanadigan[:max_steps]

        qarorlar = verdicts or {}
        tracker = SignalTracker()
        natija = BacktestResult(
            label=self._label,
            buy_and_hold_pct=self._buy_and_hold(dataset, baholanadigan, entry_tf),
        )
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

        Hisob `core/backtest/warmup.py` da — u yerda skript ham nechta
        kun ortiqcha yuklashini o'qiydi. Ikki joyda alohida
        hisoblanganda ular ajralib ketardi, va aynan shunday bo'lgan
        edi (`docs/ARXITEKTURA.md`, 80-bo'lim).
        """
        return warmup_steps(self._config)

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
            shamlar = dataset.window(symbol, moment, self._oyna).get(entry_tf, [])
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
        """5.4-banddagi qismli yopish qoidasi bilan bir xil hisob.

        Natijadan KOMISSIYA VA SIRG'ANISH ayriladi. Ilgari ular
        umuman hisobga olinmasdi va bu natijani tizimli ravishda
        chiroyliroq ko'rsatardi: 649 ta savdoda 0.3% lik xarajat
        ~195% ni yeb qo'yadi, ya'ni xulosani o'zgartira oladigan
        hajm. Backtestning butun ma'nosi haqiqatni oldindan ko'rish
        bo'lgani uchun bunday "sovg'a" eng zararli soddalashtirish.
        """
        return self._xom_natija(signal, exit_price, reached_tp1) - (
            self._config.backtest.round_trip_cost_pct
        )

    def _xom_natija(self, signal, exit_price: float, reached_tp1: bool) -> float:  # noqa: ANN001
        """Xarajatsiz, faqat narx harakatidan chiqqan natija."""
        entry = signal.levels.entry
        if not reached_tp1:
            return (exit_price - entry) / entry * 100

        ulush = self._config.portfolio.tp1_close_pct / 100
        tp1_foizi = (signal.levels.tp1 - entry) / entry * 100
        qolgan = (exit_price - entry) / entry * 100
        return tp1_foizi * ulush + qolgan * (1 - ulush)

    def _buy_and_hold(
        self, dataset: Dataset, qadamlar: list[datetime], timeframe: str
    ) -> float | None:
        """Sinov davrida coinlarni shunchaki olib ushlab turish natijasi.

        TAYANCH SIFATIDA KERAK. "O'rtacha -0.73% har savdoda" degan
        raqam o'z-o'zicha hech narsa demaydi: yomonmi, NIMAGA
        nisbatan? Agar shu davrda coinlar o'sgan bo'lsa, strategiya
        nafaqat zarar keltirgan, balki hech narsa qilmaslikdan ham
        yomon ishlagan bo'ladi.

        Hisob sodda va ataylab shunday: har bir coinga teng ulush,
        birinchi qadamda olinadi, oxirgi qadamda sotiladi. Bu
        strategiyaning o'z hisobi bilan (har savdoga teng miqdor)
        bir xil shkalada.
        """
        if len(qadamlar) < 2:
            return None

        boshi, oxiri = qadamlar[0], qadamlar[-1]
        foizlar: list[float] = []
        for symbol in dataset.symbols:
            birinchi = dataset.price_at(symbol, boshi, timeframe)
            songgi = dataset.price_at(symbol, oxiri, timeframe)
            if not birinchi or not songgi or birinchi <= 0:
                continue
            foizlar.append((songgi - birinchi) / birinchi * 100)

        if not foizlar:
            return None
        return sum(foizlar) / len(foizlar)

    def _etalon_shamlar(
        self, dataset: Dataset, moment: datetime, timeframe: str
    ) -> list[Candle]:
        """QT davri uchun etalon coin (BTC) shamlari.

        Jonli tizim ham aynan shu coinni va shu timeframeni ishlatadi
        (`bot/services/runner.py`). Etalon dataset'da bo'lmasa —
        bo'sh ro'yxat: davr aniqlanmaydi va omil neytral qoladi.
        """
        etalon = self._config.risk_engine.btc_filter.reference_symbol.upper()
        if etalon not in dataset.series:
            return []
        return dataset.window(etalon, moment, self._oyna).get(timeframe, [])

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
        atr_qiymatlari = {}
        oynalar: dict[str, dict[str, list[Candle]]] = {}

        for symbol in dataset.symbols:
            oyna = dataset.window(symbol, moment, self._oyna)
            seriya = oyna.get(entry_tf, [])
            if len(seriya) < indicators.min_candles:
                continue

            oynalar[symbol] = oyna
            coinlar.append(
                SymbolData(
                    symbol=symbol,
                    halal_verdict=verdicts.get(
                        symbol, HalalVerdict(symbol, HalalStatus.HALAL, "backtest")
                    ),
                    candles=oyna,
                )
            )

            atr = atr_pct(seriya, indicators.atr_period)
            if atr is not None:
                atr_qiymatlari[symbol] = atr

        # Kenglik va ADX — JONLI TIZIM BILAN BIR XIL funksiyadan.
        # Ilgari bu hisob shu yerda takrorlangan edi va jonli tizim
        # haftalik strukturani, backtest esa 4 soatlikni o'qiyotgan
        # edi (`docs/ARXITEKTURA.md`, 68-bo'lim). Endi ajralish uchun
        # joy yo'q.
        faktlar = universe_facts(oynalar, self._config.analysis)
        strukturalar = faktlar.structures
        adx_qiymatlari = faktlar.adx_values

        limitlar = self._config.risk_engine.max_open_signals_by_health
        ochiqlar = tracker.open_signals

        salomatlik = self._health.compute(
            HealthInputs(
                computed_at=moment,
                # BTC dominance tarixi backtestda mavjud emas — neytral
                # qiymat olinadi. Bu OSHIRIB ko'rsatish emas: dominance
                # ma'lumoti bo'lsa, natija yaxshiroq bo'lishi mumkin.
                btc_dominance_change_24h=0.0,
                universe_structures=strukturalar,
                universe_adx=adx_qiymatlari,
                # QT davri sham strukturasidan o'qiladi. Bu qator
                # yo'q edi va omil backtestda HAR DOIM neytral
                # qolardi — ya'ni jonli tizimda ta'sir qiladigan
                # narsa sinovda umuman o'lchanmasdi.
                reference_candles=self._etalon_shamlar(
                    dataset, moment, self._config.analysis.market_health_timeframe
                ),
                capacity_headroom=None,
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
