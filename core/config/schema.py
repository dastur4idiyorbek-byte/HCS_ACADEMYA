"""Konfiguratsiya sxemasi — `config/default.yaml` ning tiplashtirilgan aksi.

6.4-band: barcha "sehrli raqamlar" shu yerdagi maydonlar orqali o'qiladi.
Kodning hech bir joyida raqam qattiq yozilmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time

from core.utils.time_utils import parse_hhmm

# --------------------------------------------------------------------------- #
#  Loyiha
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    name: str = "HALOL CRYPTO SAVDO"
    default_language: str = "uz"
    supported_languages: list[str] = field(default_factory=lambda: ["uz"])


# --------------------------------------------------------------------------- #
#  3.4 — Halol skrining
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class HalalScreeningConfig:
    target_count: int = 150
    max_scan_depth: int = 500
    min_daily_volume_usd: float = 50_000_000
    quote_asset: str = "USDT"
    exclude_stablecoins: bool = True
    stablecoin_symbols: list[str] = field(default_factory=list)
    refresh_interval_hours: int = 12
    seed_haram_symbols: list[str] = field(default_factory=list)
    seed_mashbooh_symbols: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  3.1 / 3.2 — Tahlil
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SupportResistanceConfig:
    swing_lookback: int = 5
    zone_merge_atr_mult: float = 0.5
    min_touches: int = 2
    proximity_atr_mult: float = 1.0
    #: Kirish uchun ruxsat etilgan eng yuqori diapazon foizi.
    #:
    #: Ilgari chegara qat'iy 50% (muvozanat chizig'i) edi va bu JAR
    #: yaratardi: 49.9% — ruxsat, 50.1% — butunlay rad. Jonli
    #: ma'lumotda rad etishlarning 60% i shu bosqichda edi, tafsilotlar
    #: esa "Premium zonada (51%)" deb ko'rsatardi — ya'ni chegaradan
    #: bir foiz narida.
    #:
    #: Ball allaqachon CHUQURLIKNI darajali baholaydi (`depth`): 50% da
    #: 0 ball, Support'da to'liq ball. Ya'ni chuqurroq qaytish baribir
    #: yuqoriroq o'ringa chiqadi. Qat'iy jar esa shunchaki chetdagi
    #: nomzodlarni butunlay yo'q qilardi.
    entry_max_range_pct: float = 55.0
    fibonacci_levels: list[float] = field(default_factory=lambda: [0.382, 0.5, 0.618])


@dataclass(frozen=True, slots=True)
class IndicatorConfig:
    ema_fast: int = 50
    ema_slow: int = 200
    trend_requires_price_above_fast: bool = True
    #: 3.2-band: yuqori timeframelarni tasniflashda ham "narx EMA50 dan
    #: yuqori" talab qilinsinmi. Standart `False` — sabab
    #: `docs/ARXITEKTURA.md` 27-bo'limda o'lchov bilan.
    htf_trend_requires_price_above_fast: bool = False
    #: Trend "kuchi" uchun EMA50—EMA200 ajralishi necha ATR bo'lsa to'liq ball.
    #: ATR birligida — chunki foizda o'lchash timeframega bog'liq bo'lib qoladi
    #: (o'lchov: `docs/ARXITEKTURA.md` 28-bo'lim).
    ema_separation_full_atr: float = 1.5
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    volume_ma_period: int = 20
    atr_period: int = 14
    adx_period: int = 14
    adx_trend_threshold: float = 20.0
    #: Nechta indikator tasdiqlasa "tasdiqlangan" deb hisoblanadi. Endi bu
    #: faqat KO'RSATISH uchun — `require_confirmation` `False` bo'lgani
    #: uchun signalni to'xtatmaydi.
    min_confirmations: int = 2
    #: Indikator tasdig'i signal uchun MAJBURIYmi.
    #:
    #: `False` — indikatorlar faqat ballga ta'sir qiladi, ya'ni ko'p coin
    #: ichidan TANLASH uchun ishlatiladi, "mumkin/mumkin emas" degan
    #: qaror uchun emas.
    #:
    #: Sabab: indikatorlar tabiatan KECHIKADI. Ular narx harakatidan
    #: keyin tasdiqlaydi, o'sha paytda narx allaqachon Discount zonasidan
    #: chiqib ketgan bo'ladi. Ya'ni "indikator tasdiqlasin" talabi
    #: "arzon paytda olma, qimmatlashgach ol" degani bilan barobar —
    #: strategiyaning o'z maqsadiga zid.
    #:
    #: Qaror strukturaga (S/R zonasi) va risk qoidasiga (3.3-band)
    #: qoldiriladi; indikatorlar reytingni belgilaydi.
    require_confirmation: bool = False


@dataclass(frozen=True, slots=True)
class EntryOrderConfig:
    """5.1.0-band: kirish buyurtmasi turi avtomatik tanlanadi.

    - Narx hali Entry zonasiga yetib bormagan  -> LIMIT
    - Narx allaqachon Entry zonasida           -> MARKET
    """

    market_threshold_pct: float = 0.15
    zone_broken_threshold_pct: float = 0.30


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """3.2-band: asosiy klassik strategiya uchun standart timeframe to'plami."""

    timeframes: list[str] = field(
        default_factory=lambda: ["4h", "1d", "1w"]
    )
    #: Kirish timeframei. 15m dan 1h ga ko'chirildi — sabab
    #: `docs/ARXITEKTURA.md` 42-bo'limda: 15m da ATR narxning ~0.5% i
    #: bo'ladi, ya'ni support zonasigacha masofa ham shuncha. Stop esa
    #: kamida 1% bo'lishi kerak (3.3-band), shuning uchun darajalar
    #: tez-tez "Stop juda yaqin" deb rad etilardi. 1h da ATR ~1-2%,
    #: ya'ni tuzilma va risk qoidasi bir shkalaga tushadi.
    entry_timeframe: str = "4h"
    htf_confirmation: list[str] = field(
        default_factory=lambda: ["1d"]
    )
    #: Bozor Salomatligi kengligi (3.7-band, 2-omil) qaysi timeframeda
    #: o'lchanadi. Alohida e'lon qilinadi, chunki u `htf_confirmation`
    #: dan MUSTAQIL: tasdiq timeframelari qisqarganda ham kenglik kunlik
    #: o'lchovda qolishi kerak — soatlik kenglik kun bo'yi tebranib,
    #: indeksni ma'nosiz qilib qo'yardi.
    market_health_timeframe: str = "1w"
    candles_lookback: int = 500
    #: Yuqori timeframelar muvofiqligi signal uchun MAJBURIYmi (3.2-band).
    #:
    #: `False` — muvofiqlik ball ichida hisobga olinadi, lekin signalni
    #: to'xtatmaydi. Sabab `require_confirmation` bilan bir xil, faqat
    #: kuchliroq: kunlik EMA200 — 200 kunlik o'rtacha, ya'ni eng sekin
    #: kechikuvchi o'lchov. Uni majburiy qilish burilish nuqtasidagi har
    #: qanday kirishni to'sadi.
    require_htf_alignment: bool = False
    #: Kelajakdagi pozitsion strategiya uchun zaxira — asosiy strategiya
    #: ishlatmaydi (u o'z timeframelarini `required_timeframes()` da e'lon qiladi).
    positional_timeframes: list[str] = field(
        default_factory=lambda: ["1d", "1w", "1M"]
    )
    entry_order: EntryOrderConfig = field(default_factory=EntryOrderConfig)
    support_resistance: SupportResistanceConfig = field(default_factory=SupportResistanceConfig)
    indicators: IndicatorConfig = field(default_factory=IndicatorConfig)


# --------------------------------------------------------------------------- #
#  3.5 — Ball tizimi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    support_resistance: float = 25
    trend: float = 20
    rsi: float = 15
    volume: float = 15
    macd: float = 10
    risk_reward: float = 15

    def total(self) -> float:
        return (
            self.support_resistance
            + self.trend
            + self.rsi
            + self.volume
            + self.macd
            + self.risk_reward
        )


@dataclass(frozen=True, slots=True)
class ScoreThresholds:
    #: YUQORI band chegarasi. 80 dan 70 ga tushirildi — O'LCHOV asosida.
    #:
    #: Salomatlik indeksining shifti bozor KENGLIGIGA bog'liq: kenglik
    #: omili 25 ball turadi, ya'ni kenglik 5% bo'lsa indeks 76 dan
    #: yuqoriga chiqa OLMAYDI (qolgan omillar mukammal bo'lsa ham).
    #: Jonli botda kenglik 5% edi va indeks 70-77 oralig'ida yurdi —
    #: ya'ni o'z shiftida.
    #:
    #: Natijada 80 lik chegara bir marta ham ishlamadi:
    #: `threshold_high_health` (50) hech qachon qo'llanilmadi va
    #: "moslashuvchi chegara" amalda doim 55 bo'lib qoldi.
    #:
    #: 70 qo'yilgan edi, lekin haftalik timeframega o'tgach indeks
    #: 69 ga tushdi — band yana bir ball bilan yopiq qoldi. Kuzatilgan
    #: oraliq: 69..77. 65 — pastki chetdan zaxira bilan.
    health_high_min: float = 65
    health_mid_min: float = 40
    #: Chegaralar O'LCHAB tanlangan — `scripts/kalibrlash.py` ga qarang.
    #: 70/80 qiymatlari 100 ballik shkalaga mo'ljallangan edi, lekin ball
    #: funksiyasi amalda 60 dan oshmaydi (omillar bir vaqtda to'liq bo'la
    #: olmaydi). Natijada birorta signal chiqmasdi.
    threshold_high_health: float = 50
    threshold_mid_health: float = 55


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    thresholds: ScoreThresholds = field(default_factory=ScoreThresholds)


# --------------------------------------------------------------------------- #
#  3.3 — Universal savdo qoidalari
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class TradeRulesConfig:
    """3.3-band: universal risk qoidasi.

    ASOSIY SHART — NISBAT, masofa emas. Stop 1% dan 5% gacha erkin
    joylashishi mumkin (S/R zonasi qayerda ekaniga qarab), lekin
    TP/Stop nisbati kamida `min_risk_reward` bo'lishi SHART.

    Nima uchun shunday: qat'iy 1% chegara narxni majburlab siqardi —
    aynan 1% masofada mos S/R zonasi bo'ladigan holat kam uchraydi,
    natijada signal deyarli chiqmasdi. Nisbat esa har qanday masofada
    ma'noga ega.

    Stop kattalashsa xavf oshmaydi: pozitsiya hajmi
    (xavf puli / Stop%) avtomatik kichrayadi — 5.1-band.
    """

    #: Stop shu masofadan yaqin bo'lsa — bozor shovqini uni yeb qo'yadi
    #: Stop masofasi = ATR × shu ko'paytma.
    #:
    #: Qat'iy foiz BARCHA coinlarga bir xil qo'llanardi, holbuki Stopning
    #: maqsadi bozor shovqinidan himoya — shovqin esa ATR bilan
    #: o'lchanadi. 1% stop BTC uchun ~1.2 ATR (mantiqiy), volatil
    #: altcoin uchun ~0.3 ATR (shovqin yeb qo'yadi), barqaror coin
    #: uchun ~3 ATR (keraksiz keng, yaxshi setuplarni rad etadi).
    stop_atr_mult: float = 1.75
    #: Ikkinchi darajali xavfsizlik chegarasi. ATR asosidagi Stop shu
    #: oraliqdan chiqsa signal rad etiladi — juda tor yoki juda keng
    #: bo'lib qolmasin.
    min_stop_distance_pct: float = 1.0
    #: Stop shu masofadan uzoq bo'lsa — pozitsiya juda kichrayib ketadi
    max_stop_distance_pct: float = 5.0
    #: TP Stop bilan bog'liq: `min_risk_reward` orqali hisoblanadi
    min_tp_distance_pct: float = 3.0
    max_tp_distance_pct: float = 20.0
    #: QAT'IY SHART: TP2/Stop nisbati shundan past bo'lsa signal yo'q
    min_risk_reward: float = 3.0
    #: TP1 uchun eng past nisbat. TP1 da pozitsiyaning yarmi yopiladi —
    #: agar u 1:1 dan past bo'lsa, o'sha yarim savdo o'rtacha zarar keltiradi.
    tp1_min_risk_reward: float = 1.5
    allow_measured_tp: bool = True


# --------------------------------------------------------------------------- #
#  4 — Risk Engine
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class OpenSignalLimits:
    high: int = 5
    mid: int = 3
    low: int = 0


@dataclass(frozen=True, slots=True)
class CorrelationGroup:
    name: str
    symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BtcFilterConfig:
    reference_symbol: str = "BTC"
    max_drop_pct_24h: float = -5.0
    timeframe: str = "1h"


@dataclass(frozen=True, slots=True)
class KillSwitchConfig:
    price_spike_pct: float = 5.0
    price_spike_window_seconds: int = 60
    requires_manual_reset: bool = True


@dataclass(frozen=True, slots=True)
class ConsecutiveLossConfig:
    max_consecutive_stops: int = 5
    cooldown_hours: int = 24


@dataclass(frozen=True, slots=True)
class FridayFilterConfig:
    """4.8-band — Juma namozi vaqti filtri."""

    enabled: bool = True
    timezone: str = "Asia/Tashkent"
    weekday: int = 4
    start: str = "11:00"
    end: str = "15:00"

    @property
    def start_time(self) -> time:
        return parse_hhmm(self.start)

    @property
    def end_time(self) -> time:
        return parse_hhmm(self.end)


@dataclass(frozen=True, slots=True)
class RotationConfig:
    min_score_gap: float = 30
    cooldown_minutes: int = 120


@dataclass(frozen=True, slots=True)
class WeakeningConfig:
    score_drop_points: float = 25


@dataclass(frozen=True, slots=True)
class RiskEngineConfig:
    daily_loss_limit_pct: float = 3.0
    weekly_loss_limit_pct: float = 8.0
    max_open_signals: int = 5
    max_open_signals_by_health: OpenSignalLimits = field(default_factory=OpenSignalLimits)
    correlation_groups: list[CorrelationGroup] = field(default_factory=list)
    max_signals_per_correlation_group: int = 1
    btc_filter: BtcFilterConfig = field(default_factory=BtcFilterConfig)
    kill_switch: KillSwitchConfig = field(default_factory=KillSwitchConfig)
    consecutive_loss: ConsecutiveLossConfig = field(default_factory=ConsecutiveLossConfig)
    friday_filter: FridayFilterConfig = field(default_factory=FridayFilterConfig)
    rotation: RotationConfig = field(default_factory=RotationConfig)
    weakening: WeakeningConfig = field(default_factory=WeakeningConfig)

    def correlation_group_of(self, symbol: str) -> str | None:
        """Coin qaysi korrelyatsiya guruhiga tegishli (4.3-band, statik ro'yxat)."""
        upper = symbol.upper()
        for group in self.correlation_groups:
            if upper in {s.upper() for s in group.symbols}:
                return group.name
        return None


# --------------------------------------------------------------------------- #
#  3.7 — Bozor Salomatligi Indeksi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class MarketHealthWeights:
    btc_dominance_stability: float = 20
    halal_trend_breadth: float = 25
    volatility_regime: float = 20
    aggregate_user_capacity: float = 20
    signal_saturation: float = 15

    def total(self) -> float:
        return (
            self.btc_dominance_stability
            + self.halal_trend_breadth
            + self.volatility_regime
            + self.aggregate_user_capacity
            + self.signal_saturation
        )


@dataclass(frozen=True, slots=True)
class BtcDominanceConfig:
    stable_change_pct: float = 0.5
    sharp_change_pct: float = 2.0


@dataclass(frozen=True, slots=True)
class MarketHealthConfig:
    #: 3-omil to'liq ball oladigan O'RTACHA ADX (bitta coin emas, 30 ta
    #: coinning o'rtachasi — sabab `docs/ARXITEKTURA.md`, 32-bo'lim)
    strong_trend_adx: float = 30.0
    weights: MarketHealthWeights = field(default_factory=MarketHealthWeights)
    recompute_on_candle_close: bool = True
    daily_preview_utc_hour: int = 0
    btc_dominance: BtcDominanceConfig = field(default_factory=BtcDominanceConfig)


# --------------------------------------------------------------------------- #
#  5 — Pozitsiya hajmi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class RiskTier:
    """Pog'onali kunlik xavf foizi. `max_balance is None` — eng yuqori pog'ona."""

    max_balance: float | None
    daily_risk_pct: float


@dataclass(frozen=True, slots=True)
class AggregateConfig:
    capacity_used_threshold: float = 0.8
    active_user_days: int = 7


def _default_risk_tiers() -> list[RiskTier]:
    """5.1-band standart pog'onalari — konfiguratsiya fayli bo'lmasa ham
    tizim yaroqli holatda ishga tushishi kerak."""
    return [
        RiskTier(max_balance=1000, daily_risk_pct=3.0),
        RiskTier(max_balance=10000, daily_risk_pct=2.0),
        RiskTier(max_balance=None, daily_risk_pct=1.5),
    ]


@dataclass(frozen=True, slots=True)
class PositionSizingConfig:
    risk_tiers: list[RiskTier] = field(default_factory=_default_risk_tiers)
    allocation_method: str = "sequential_decay"
    sequential_decay_fraction: float = 0.34
    equal_split_expected_slots: int = 3
    min_allocation_usd: float = 1.0
    max_position_pct_of_balance: float = 100.0
    aggregate: AggregateConfig = field(default_factory=AggregateConfig)


# --------------------------------------------------------------------------- #
#  3.9 — Strategiyalar
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ClassicTaConfig:
    enabled: bool = True
    #: Mean reversion uchun eng kam TP2/Stop nisbati.
    #:
    #: Global 1:3 qiymati trend/breakout strategiyalariga xos. Mean
    #: reversion tabiiy ravishda diapazon o'rtasiga yoki resistance'ga
    #: qaytganda yopiladi — bu odatda 1:1..1:1.5 beradi. 1:3 talab qilish
    #: bu strategiya uchun deyarli hech qachon bajarilmaydigan shart edi.
    #:
    #: Qiymat STRATEGIYA darajasida: boshqa turdagi strategiya qo'shilsa,
    #: u o'zining tabiiy nisbatini saqlaydi.
    min_risk_reward: float = 1.5


@dataclass(frozen=True, slots=True)
class ScalpWeights:
    """3.9-band strategiyasining ball vaznlari (jami 100).

    Asosiy strategiyanikidan farq qiladi: bu yerda S/R zonasi yo'q, hajm
    sakrashi va yo'nalish aniqligi hal qiluvchi omillar.
    """

    volume_surge: float = 35
    range_quality: float = 25
    direction_clarity: float = 25
    risk_reward: float = 15

    def total(self) -> float:
        return (
            self.volume_surge
            + self.range_quality
            + self.direction_clarity
            + self.risk_reward
        )


@dataclass(frozen=True, slots=True)
class OpeningRangeScalpConfig:
    enabled: bool = True
    session_open_utc: str = "00:00"
    range_minutes: int = 15
    timeframe: str = "15m"
    volume_surge_mult: float = 2.0
    volume_ma_period: int = 20
    min_move_pct: float = 1.0
    max_move_pct: float = 2.0
    #: Ochilishdan keyin signal oynasi necha daqiqa ochiq turadi.
    #:
    #: 45 daqiqadan bir kunga (1440) uzaytirildi. Sabab: 45 daqiqa
    #: kunning 3% i, ya'ni oyna vaqtning 97% ida yopiq turardi va
    #: dashboardda "Skalping oynasi yopiq" yozuvi hamma narsadan ko'p
    #: chiqardi (5114 marta).
    #:
    #: Diqqat: kech kirish yomonroq kirish. Diapazon kun boshida
    #: qurilgani uchun kunning oxirida buzilish "eskirgan" diapazonga
    #: nisbatan o'lchanadi. Buni ball qoplaydi — buzilish kuchi va hajm
    #: baribir talab qilinadi — lekin bu almashuv ONGLI ravishda
    #: qabul qilingan.
    signal_window_minutes: int = 1440
    min_range_pct: float = 0.15
    max_range_pct: float = 1.2
    daily_risk_share_pct: float = 30.0
    weights: ScalpWeights = field(default_factory=ScalpWeights)

    @property
    def session_open_time(self) -> time:
        return parse_hhmm(self.session_open_utc)


@dataclass(frozen=True, slots=True)
class StrategiesConfig:
    classic_ta: ClassicTaConfig = field(default_factory=ClassicTaConfig)
    opening_range_scalp: OpeningRangeScalpConfig = field(default_factory=OpeningRangeScalpConfig)


# --------------------------------------------------------------------------- #
#  5.4 — Shaxsiy portfel
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PortfolioConfig:
    """5.4-band: "Men kirdim" va foyda/zarar hisobi."""

    #: TP1 ga yetganda pozitsiyaning necha foizi yopiladi
    tp1_close_pct: float = 50.0
    min_position_usd: float = 1.0


# --------------------------------------------------------------------------- #
#  3.8 — Signal Xotirasi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PostmortemConfig:
    """3.8-band: o'z-o'zini tekshirish sozlamalari."""

    #: Naqsh e'lon qilish uchun minimal namuna — halollik chegarasi
    min_sample_size: int = 12
    #: Naqsh "kuchli" bo'lishi uchun natijalar farqi (foiz punkti)
    min_effect_pct: float = 15.0
    lookback_days: int = 30
    report_weekday: int = 0
    report_hour_utc: int = 6
    false_signal_window_minutes: int = 60


# --------------------------------------------------------------------------- #
#  1.2 — Obuna
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SubscriptionPeriods:
    daily: int = 1
    monthly: int = 30


@dataclass(frozen=True, slots=True)
class SubscriptionsConfig:
    tiers: list[str] = field(default_factory=lambda: ["lite", "pro", "premium"])
    periods: SubscriptionPeriods = field(default_factory=SubscriptionPeriods)
    expiry_reminder_days: list[int] = field(default_factory=lambda: [2, 1])
    currencies: list[str] = field(default_factory=lambda: ["KGS", "USDT"])


# --------------------------------------------------------------------------- #
#  6.2 — Bozor ma'lumotlari
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class MarketDataConfig:
    exchange: str = "binance"
    ws_base_url: str = "wss://stream.binance.com:9443/stream"
    rest_base_url: str = "https://api.binance.com"
    ranking_source: str = "coinmarketcap"
    coinmarketcap_base_url: str = "https://pro-api.coinmarketcap.com/v1"
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    reconnect_backoff_seconds: list[int] = field(default_factory=lambda: [2, 4, 8, 16, 32])
    stale_price_seconds: int = 90
    #: Bir vaqtda nechta OHLCV so'rovi yuborilsin.
    #:
    #: Ilgari chegara umuman yo'q edi: sikl BARCHA coin × BARCHA timeframe
    #: so'rovini bir zumda yuborardi. 30 ta coinda bu 90 ta parallel so'rov
    #: — birja chidadi. 150 ta coinda 450 ta bo'ladi va Binance avval 429,
    #: keyin 418 (IP ban) qaytaradi. Ya'ni ro'yxatni kengaytirish
    #: chegarasiz ishlamaydi.
    max_concurrent_candle_requests: int = 8
    #: Sham ma'lumoti necha "timeframe" gacha eski bo'lishi mumkin.
    #:
    #: `stale_price_seconds` (90s) TIK oqimi uchun — u kuzatuvchida
    #: ishlatiladi va u yerda to'g'ri. Lekin SIGNAL QARORI shamdan
    #: olingan narxga tayanadi (`_joriy_narx()` oxirgi sham yopilishini
    #: qaytaradi), shuning uchun bu yerda sham yoshi o'lchanadi. 1
    #: soatlik sham tabiatan 1 soatgacha "eski" bo'ladi — 90 soniyalik
    #: chegara unga umuman to'g'ri kelmaydi.
    stale_candle_multiplier: float = 2.0


# --------------------------------------------------------------------------- #
#  6.4 — Logging
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str = "INFO"
    dir: str = "logs"
    rotate_mb: int = 20
    backups: int = 5


# --------------------------------------------------------------------------- #
#  Ildiz
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Butun tizimning yagona konfiguratsiya obyekti."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    halal_screening: HalalScreeningConfig = field(default_factory=HalalScreeningConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    trade_rules: TradeRulesConfig = field(default_factory=TradeRulesConfig)
    risk_engine: RiskEngineConfig = field(default_factory=RiskEngineConfig)
    market_health: MarketHealthConfig = field(default_factory=MarketHealthConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    postmortem: PostmortemConfig = field(default_factory=PostmortemConfig)
    position_sizing: PositionSizingConfig = field(default_factory=PositionSizingConfig)
    strategies: StrategiesConfig = field(default_factory=StrategiesConfig)
    subscriptions: SubscriptionsConfig = field(default_factory=SubscriptionsConfig)
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
