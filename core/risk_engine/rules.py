"""4-bo'lim: Risk Engine qoidalari.

Har bir qoida — mustaqil, sof, test qilinadigan sinf. Barchasi "VA" (AND)
mantig'i bilan birlashtiriladi: signal chiqishi uchun HAMMASI ruxsat berishi
kerak.

0.3-band (fail-safe): ma'lumot yetishmasa yoki noaniq bo'lsa, qoida signal
BERMASLIKKA moyil bo'ladi.
"""

from __future__ import annotations

from typing import Protocol

from core.config.schema import RiskEngineConfig
from core.domain.enums import BlockReason, HealthBand, SignalSource
from core.domain.models import RiskDecision, SignalCandidate
from core.risk_engine.context import RiskContext
from core.utils.time_utils import is_within_daily_window

#: Suzuvchi nuqta xatosiga bardoshlilik. Ansiz aynan chegarada qurilgan
#: daraja (masalan TP2 = 2.00%) hisobda 2.0000000000000018 chiqib, o'z
#: chegarasidan "tashqarida" deb rad etilardi.
_EPSILON = 1e-9


class RiskRule(Protocol):
    """Bitta risk qoidasi."""

    name: str

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        ...


class _BaseRule:
    name: str = "rule"

    def __init__(self, config: RiskEngineConfig) -> None:
        self._config = config


# --------------------------------------------------------------------------- #
#  4.7 — Favqulodda to'xtash (kill switch) — eng birinchi tekshiriladi
# --------------------------------------------------------------------------- #


class KillSwitchRule(_BaseRule):
    """Kill switch faol bo'lsa, hech qanday signal chiqmaydi.

    Inson tekshirib qayta ishga tushirmaguncha o'chmaydi.
    """

    name = "kill_switch"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        if context.kill_switch_active:
            sabab = context.kill_switch_reason or "sabab ko'rsatilmagan"
            return RiskDecision.block(
                BlockReason.KILL_SWITCH,
                f"Favqulodda to'xtash faol: {sabab}. "
                "Admin tekshiruvidan keyin qayta ishga tushadi.",
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  4.8 — Juma namozi vaqti filtri
# --------------------------------------------------------------------------- #


class FridayPrayerRule(_BaseRule):
    """Juma kuni belgilangan oynada YANGI signal generatsiyasi to'xtaydi.

    MUHIM: bu qoida faqat yangi signalga taalluqli. Mavjud faol signallar
    kuzatuvi (WebSocket, TP/Stop tekshiruvi) to'xtamaydi — u boshqa qatlamda,
    Risk Engine'dan o'tmaydi.
    """

    name = "friday_prayer"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        friday = self._config.friday_filter
        if not friday.enabled:
            return RiskDecision.allow()

        if is_within_daily_window(
            context.now,
            friday.timezone,
            friday.start_time,
            friday.end_time,
            weekday=friday.weekday,
        ):
            return RiskDecision.block(
                BlockReason.FRIDAY_PRAYER,
                f"Juma namozi vaqti ({friday.start}–{friday.end}, {friday.timezone}) — "
                "yangi signal berilmaydi. Mavjud signallar kuzatuvda qoladi.",
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  4.9 — Bozor Salomatligi Indeksi filtri
# --------------------------------------------------------------------------- #


class MarketHealthRule(_BaseRule):
    """Indeks 40dan past bo'lsa yangi signal butunlay to'xtaydi (3.7-band)."""

    name = "market_health"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        health = context.market_health
        if health is None:
            # Fail-safe: indeks hisoblanmagan bo'lsa signal berilmaydi.
            return RiskDecision.block(
                BlockReason.MARKET_HEALTH_LOW,
                "Bozor Salomatligi Indeksi hisoblanmagan — noaniqlikda signal berilmaydi.",
            )
        if health.band is HealthBand.LOW:
            return RiskDecision.block(
                BlockReason.MARKET_HEALTH_LOW,
                f"Bozor Salomatligi Indeksi past ({health.value:.0f}/100) — "
                "tizim faqat kuzatuv rejimida.",
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  4.1 — Kunlik / haftalik zarar chegarasi
# --------------------------------------------------------------------------- #


class DailyLossLimitRule(_BaseRule):
    """Kunlik zarar chegaraga yetsa, o'sha kun yangi signal to'xtatiladi.

    5-bo'limdagi kunlik byudjet bilan BITTA manbaga bog'langan — bu yerda
    ikkinchi, mustaqil sozlama yo'q.
    """

    name = "daily_loss_limit"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        kunlik = self._config.daily_loss_limit_pct
        haftalik = self._config.weekly_loss_limit_pct

        if context.daily_loss_pct >= kunlik:
            return RiskDecision.block(
                BlockReason.DAILY_LOSS_LIMIT,
                f"Kunlik zarar chegarasi to'ldi ({context.daily_loss_pct:.2f}% >= {kunlik}%).",
            )
        if context.weekly_loss_pct >= haftalik:
            return RiskDecision.block(
                BlockReason.DAILY_LOSS_LIMIT,
                f"Haftalik zarar chegarasi to'ldi ({context.weekly_loss_pct:.2f}% >= {haftalik}%).",
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  4.2 — Bir vaqtda ochiq signallar soni
# --------------------------------------------------------------------------- #


class MaxOpenSignalsRule(_BaseRule):
    """Ochiq signallar soni chegarasi — Bozor Salomatligiga qarab moslashuvchan."""

    name = "max_open_signals"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        limit = self._limit_for(context.health_band)
        ochiq = len(context.open_signals)

        if ochiq >= limit:
            return RiskDecision.block(
                BlockReason.MAX_OPEN_SIGNALS,
                f"Ochiq signallar chegarasi to'ldi ({ochiq}/{limit}) — "
                f"bozor holati: {context.health_band.value if context.health_band else 'nomalum'}.",
            )
        return RiskDecision.allow()

    def _limit_for(self, band: HealthBand | None) -> int:
        limits = self._config.max_open_signals_by_health
        if band is HealthBand.HIGH:
            return limits.high
        if band is HealthBand.MID:
            return limits.mid
        if band is HealthBand.LOW:
            return limits.low
        return min(limits.mid, self._config.max_open_signals)  # noaniqlikda ehtiyotkor


# --------------------------------------------------------------------------- #
#  4.3 — Korrelyatsiyalangan coinlarni cheklash
# --------------------------------------------------------------------------- #


class CorrelationRule(_BaseRule):
    """Statik guruh asosida: BTC ochiq bo'lsa, unga bog'liq coin uchun signal yo'q.

    Murakkab statistik hisob-kitob emas — konfiguratsiyadagi statik ro'yxat
    (spetsifikatsiya talabi).
    """

    name = "correlation"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        guruh = self._config.correlation_group_of(candidate.symbol)
        if guruh is None:
            return RiskDecision.allow()

        band_coinlar = [
            signal.correlation_symbol
            for signal in context.open_signals
            if self._config.correlation_group_of(signal.correlation_symbol) == guruh
        ]
        if len(band_coinlar) >= self._config.max_signals_per_correlation_group:
            return RiskDecision.block(
                BlockReason.CORRELATION,
                f"'{guruh}' korrelyatsiya guruhida allaqachon ochiq signal bor "
                f"({', '.join(band_coinlar)}) — qo'shimcha signal xavfni jamlaydi.",
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  4.4 — Bozor rejimi (ADX) va 4.6 — volatillik (ATR)
# --------------------------------------------------------------------------- #


class MarketRegimeRule(_BaseRule):
    """Tekis (sideways) bozorda signal berilmaydi."""

    name = "market_regime"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        if context.adx is None:
            return RiskDecision.block(
                BlockReason.SIDEWAYS_MARKET,
                "ADX hisoblanmagan — bozor rejimi noaniq, signal berilmaydi.",
            )
        return RiskDecision.allow()


class VolatilityRule(_BaseRule):
    """3.3-band: volatillik mos kelmasa signal umuman berilmaydi, majburlanmaydi.

    Tekshiruv: Stop masofasi (1% gacha) va TP masofasi (3-5%) shu coinning
    haqiqiy volatilligiga (ATR) sig'adimi. ATR juda kichik bo'lsa, narx TP'ga
    yetishi uchun mantiqiy asos yo'q.
    """

    name = "volatility"

    def __init__(self, config: RiskEngineConfig, min_atr_pct: float) -> None:
        super().__init__(config)
        self._min_atr_pct = min_atr_pct

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        if context.atr_pct is None:
            return RiskDecision.block(
                BlockReason.LOW_VOLATILITY,
                "ATR hisoblanmagan — volatillik noaniq, signal berilmaydi.",
            )
        if context.atr_pct < self._min_atr_pct:
            return RiskDecision.block(
                BlockReason.LOW_VOLATILITY,
                f"Volatillik yetarli emas (ATR {context.atr_pct:.2f}% < "
                f"{self._min_atr_pct:.2f}%) — TP masofasiga yetish ehtimoli past.",
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  4.5 — Umumiy bozor (BTC) filtri
# --------------------------------------------------------------------------- #


class BtcMarketRule(_BaseRule):
    """BTC keskin tushayotgan bo'lsa signal berilmaydi."""

    name = "btc_market"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        if context.btc_change_24h_pct is None:
            return RiskDecision.block(
                BlockReason.BTC_MARKET_FILTER,
                "BTC holati noma'lum — umumiy bozor filtri tekshirilmadi.",
            )
        chegara = self._config.btc_filter.max_drop_pct_24h
        if context.btc_change_24h_pct <= chegara:
            return RiskDecision.block(
                BlockReason.BTC_MARKET_FILTER,
                f"BTC 24 soatda {context.btc_change_24h_pct:.2f}% tushdi "
                f"(chegara {chegara}%) — umumiy bozor bosimi ostida.",
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  4.10 / 3.8 — Ketma-ket zarar kill switch
# --------------------------------------------------------------------------- #


class ConsecutiveLossRule(_BaseRule):
    """Oxirgi N ta signal ketma-ket Stop yesa, signal berish vaqtincha to'xtaydi.

    Bu — bozorga emas, STRATEGIYA samaradorligiga asoslangan qo'shimcha
    himoya (3.8-band).
    """

    name = "consecutive_loss"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        chegara = self._config.consecutive_loss.max_consecutive_stops

        if context.consecutive_stop_until and context.now < context.consecutive_stop_until:
            return RiskDecision.block(
                BlockReason.CONSECUTIVE_LOSSES,
                "Ketma-ket zarar to'xtatishi kuchda "
                f"({context.consecutive_stop_until:%Y-%m-%d %H:%M} gacha) — "
                "strategiya hozirgi bozor sharoitida yaxshi ishlamayapti.",
            )
        if context.consecutive_stops >= chegara:
            return RiskDecision.block(
                BlockReason.CONSECUTIVE_LOSSES,
                f"Oxirgi {context.consecutive_stops} ta signal ketma-ket Stop yedi "
                f"(chegara {chegara}) — admin tekshiruvi talab etiladi.",
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  6.2 — Narx oqimi yangiligi (fail-safe)
# --------------------------------------------------------------------------- #


class FreshDataRule(_BaseRule):
    """Narx oqimi eskirgan bo'lsa signal berilmaydi (0.3-band)."""

    name = "fresh_data"

    def __init__(self, config: RiskEngineConfig, max_age_seconds: float) -> None:
        super().__init__(config)
        self._max_age = max_age_seconds

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        if context.price_age_seconds is None:
            return RiskDecision.block(
                BlockReason.STALE_MARKET_DATA,
                "Narx oqimi holati noma'lum — signal berilmaydi.",
            )
        if context.price_age_seconds > self._max_age:
            return RiskDecision.block(
                BlockReason.STALE_MARKET_DATA,
                "Narx ma'lumoti eskirgan "
                f"({context.price_age_seconds:.0f}s > {self._max_age:.0f}s) — "
                "WebSocket uzilgan bo'lishi mumkin.",
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  3.3 — Universal risk qoidasi (darajalar mantiqiyligi)
# --------------------------------------------------------------------------- #


class TradeRulesRule:
    """3.3-band: Stop 1% dan oshmasin, TP oralig'ida, TP2 minimal R/R ta'minlasin.

    STRATEGIYAGA QARAB moslashadi. Sabab: 3.3-band TP ni 3–5% deb belgilaydi,
    3.9-banddagi skalping esa 1–2% harakatni kutadi. Bir xil chegara bilan
    tekshirilsa, skalping signallari HAR DOIM rad etilardi — ya'ni
    spetsifikatsiyada talab qilingan strategiya hech qachon ishlamasdi.

    Stop chegarasi (1%) esa BARCHA strategiyalar uchun bir xil qoladi — u
    kapital himoyasi, strategiya xususiyati emas.
    """

    name = "trade_rules"

    def __init__(
        self,
        max_stop_pct: float,
        min_tp_pct: float,
        max_tp_pct: float,
        min_rr: float,
        overrides: dict[SignalSource, tuple[float, float, float]] | None = None,
    ) -> None:
        self._max_stop_pct = max_stop_pct
        self._min_tp_pct = min_tp_pct
        self._max_tp_pct = max_tp_pct
        self._min_rr = min_rr
        #: Strategiya -> (min_tp_pct, max_tp_pct, min_rr)
        self._overrides = overrides or {}

    def _bounds_for(self, source: SignalSource) -> tuple[float, float, float]:
        return self._overrides.get(source, (self._min_tp_pct, self._max_tp_pct, self._min_rr))

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        levels = candidate.levels
        min_tp, max_tp, min_rr = self._bounds_for(candidate.source)
        muammolar: list[str] = []

        if levels.stop_distance_pct > self._max_stop_pct + _EPSILON:
            muammolar.append(
                f"Stop masofasi {levels.stop_distance_pct:.2f}% > {self._max_stop_pct}%"
            )
        for nom, masofa in (("TP1", levels.tp1_distance_pct), ("TP2", levels.tp2_distance_pct)):
            if not min_tp - _EPSILON <= masofa <= max_tp + _EPSILON:
                muammolar.append(
                    f"{nom} masofasi {masofa:.2f}% {min_tp}–{max_tp}% oralig'idan tashqarida"
                )
        if levels.risk_reward_tp2 < min_rr - _EPSILON:
            muammolar.append(
                f"TP2 R/R {levels.risk_reward_tp2:.2f} < {min_rr} (1:{min_rr:.0f})"
            )

        if muammolar:
            return RiskDecision.block(
                BlockReason.RISK_RULES_VIOLATED,
                "Universal risk qoidalari buzildi: " + "; ".join(muammolar),
            )
        return RiskDecision.allow()


# --------------------------------------------------------------------------- #
#  3.4 — Halollik (oxirgi himoya chizig'i)
# --------------------------------------------------------------------------- #


class HalalRule:
    """Nomzod haqiqatan halolmi — signal yo'lidagi oxirgi tekshiruv.

    Skrining moduli allaqachon filtrlaydi, lekin bu qatlam takroriy himoya:
    brend va'dasi buzilishi eng jiddiy xato bo'lardi.
    """

    name = "halal"

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        verdict = candidate.halal_verdict
        if not verdict.is_tradable:
            return RiskDecision.block(
                BlockReason.NOT_HALAL,
                f"{verdict.symbol} savdoga yaroqli emas ({verdict.status.value}): {verdict.reason}",
            )
        return RiskDecision.allow()
