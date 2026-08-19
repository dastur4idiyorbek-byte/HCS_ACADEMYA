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
    target_count: int = 30
    max_scan_depth: int = 300
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
    fibonacci_levels: list[float] = field(default_factory=lambda: [0.382, 0.5, 0.618])


@dataclass(frozen=True, slots=True)
class IndicatorConfig:
    ema_fast: int = 50
    ema_slow: int = 200
    trend_requires_price_above_fast: bool = True
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
    min_confirmations: int = 2


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
        default_factory=lambda: ["15m", "30m", "1h", "4h", "1d"]
    )
    entry_timeframe: str = "15m"
    htf_confirmation: list[str] = field(
        default_factory=lambda: ["30m", "1h", "4h", "1d"]
    )
    candles_lookback: int = 500
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
    health_high_min: float = 80
    health_mid_min: float = 40
    threshold_high_health: float = 70
    threshold_mid_health: float = 80


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    thresholds: ScoreThresholds = field(default_factory=ScoreThresholds)


# --------------------------------------------------------------------------- #
#  3.3 — Universal savdo qoidalari
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class TradeRulesConfig:
    max_stop_distance_pct: float = 1.0
    min_tp_distance_pct: float = 3.0
    max_tp_distance_pct: float = 5.0
    min_risk_reward: float = 3.0
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


@dataclass(frozen=True, slots=True)
class OpeningRangeScalpConfig:
    enabled: bool = True
    session_open_utc: str = "00:00"
    range_minutes: int = 15
    volume_surge_mult: float = 2.0
    min_move_pct: float = 1.0
    max_move_pct: float = 2.0
    daily_risk_share_pct: float = 30.0


@dataclass(frozen=True, slots=True)
class StrategiesConfig:
    classic_ta: ClassicTaConfig = field(default_factory=ClassicTaConfig)
    opening_range_scalp: OpeningRangeScalpConfig = field(default_factory=OpeningRangeScalpConfig)


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
    position_sizing: PositionSizingConfig = field(default_factory=PositionSizingConfig)
    strategies: StrategiesConfig = field(default_factory=StrategiesConfig)
    subscriptions: SubscriptionsConfig = field(default_factory=SubscriptionsConfig)
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
