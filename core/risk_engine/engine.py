"""4-bo'lim: Risk Engine — umumiy nazorat qatlami.

Barcha strategiyalar signalni foydalanuvchiga yetkazishdan oldin MAJBURIY
ravishda shu qatlamdan o'tadi. Mantiq — "VA" (AND): barcha qoidalar ruxsat
berishi kerak.

Nima uchun barcha qoidalar tekshiriladi (birinchisida to'xtamasdan): admin
dashboardi "signal nega berilmadi?" savoliga TO'LIQ javob ko'rsatishi kerak
— bitta sabab emas, hammasi. Bu 3.8-banddagi postmortem tahlili uchun ham
zarur.
"""

from __future__ import annotations

from core.analysis.strategies.opening_range_scalp import scalp_trade_rules
from core.config.schema import AppConfig
from core.domain.enums import BlockReason, SignalSource
from core.domain.models import RiskDecision, SignalCandidate
from core.risk_engine.context import RiskContext
from core.risk_engine.rules import (
    BtcMarketRule,
    ConsecutiveLossRule,
    CorrelationRule,
    DailyLossLimitRule,
    FreshDataRule,
    FridayPrayerRule,
    HalalRule,
    KillSwitchRule,
    MarketHealthRule,
    MarketRegimeRule,
    MaxOpenSignalsRule,
    RiskRule,
    TradeRulesRule,
    VolatilityRule,
)
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


def build_default_rules(config: AppConfig) -> list[RiskRule]:
    """4-bo'limdagi barcha qoidalarni standart tartibda quradi.

    Tartib muhim emas (hammasi tekshiriladi), lekin eng "qat'iy" to'xtatishlar
    boshida turadi — loglarni o'qishni osonlashtiradi.
    """
    risk = config.risk_engine
    # Volatillik chegarasi: ATR kamida ENG KICHIK ruxsat etilgan Stop
    # masofasi bilan bir xil tartibda bo'lishi kerak — aks holda narx TP
    # gacha yetib borishi ehtimoli past.
    #
    # ENG KATTA emas: Stop 1%..5% oralig'ida erkin joylashadi (3.3-band
    # tuzatilgan), shuning uchun yuqori chegaraga bog'lash ATR dan 5%
    # talab qilardi va deyarli har bir signalni to'sardi.
    min_atr_pct = config.trade_rules.min_stop_distance_pct

    return [
        KillSwitchRule(risk),
        FridayPrayerRule(risk),
        MarketHealthRule(risk),
        ConsecutiveLossRule(risk),
        DailyLossLimitRule(risk),
        MaxOpenSignalsRule(risk),
        CorrelationRule(risk),
        BtcMarketRule(risk),
        MarketRegimeRule(risk),
        VolatilityRule(risk, min_atr_pct=min_atr_pct),
        FreshDataRule(risk, max_age_seconds=config.market_data.stale_price_seconds),
        HalalRule(),
        TradeRulesRule(
            min_stop_pct=config.trade_rules.min_stop_distance_pct,
            max_stop_pct=config.trade_rules.max_stop_distance_pct,
            min_tp_pct=config.trade_rules.min_tp_distance_pct,
            max_tp_pct=config.trade_rules.max_tp_distance_pct,
            min_rr=config.trade_rules.min_risk_reward,
            # 3.9-band skalpingi 1-2% harakat kutadi, 3.3-banddagi 3-5%
            # oralig'i unga to'g'ri kelmaydi.
            overrides={
                SignalSource.OPENING_RANGE_SCALP: scalp_trade_rules(
                    config.strategies.opening_range_scalp
                )
            },
        ),
    ]


class RiskEngine:
    """Signal nomzodini barcha risk qoidalaridan o'tkazadi."""

    def __init__(self, config: AppConfig, rules: list[RiskRule] | None = None) -> None:
        self._config = config
        self._rules = rules if rules is not None else build_default_rules(config)

    @property
    def rules(self) -> list[RiskRule]:
        return list(self._rules)

    def evaluate(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        """Nomzodni baholaydi. Barcha rad sabablari yig'iladi."""
        qaror = RiskDecision.allow()

        for rule in self._rules:
            try:
                natija = rule.check(candidate, context)
            except Exception:  # noqa: BLE001
                # 0.3-band: bitta qoidaning nosozligi butun tizimni to'xtatmaydi,
                # lekin noaniqlikda signal BERILMAYDI.
                logger.exception("Risk qoidasi xato berdi: %s", rule.name)
                natija = RiskDecision.block(
                    BlockReason.INTERNAL_ERROR,
                    f"'{rule.name}' qoidasi tekshirilmadi (ichki xato) — "
                    "xavfsizlik uchun signal berilmaydi.",
                )
            qaror = qaror.merged_with(natija)

        if not qaror.allowed:
            logger.info(
                "Signal to'xtatildi: %s | sabablar: %s",
                candidate.symbol,
                ", ".join(r.value for r in qaror.reasons),
            )
        return qaror

    def score_threshold(self, market_health_value: float | None) -> float | None:
        """3.5-band: minimal ball chegarasi — statik EMAS, indeksga qarab moslashadi.

        Returns:
            Chegara qiymati, yoki `None` — bu holda signal umuman berilmaydi.
        """
        thresholds = self._config.scoring.thresholds
        if market_health_value is None:
            return None
        if market_health_value >= thresholds.health_high_min:
            return thresholds.threshold_high_health
        if market_health_value >= thresholds.health_mid_min:
            return thresholds.threshold_mid_health
        return None
