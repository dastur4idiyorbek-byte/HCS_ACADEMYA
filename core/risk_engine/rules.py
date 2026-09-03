"""4-bo'lim: Risk Engine qoidalari.

Har bir qoida — mustaqil, sof, test qilinadigan sinf. Barchasi "VA" (AND)
mantig'i bilan birlashtiriladi: signal chiqishi uchun HAMMASI ruxsat berishi
kerak.

DIQQAT — 2026-09-03 da bu fayl QISQARTIRILDI. Eski tahlil moduli olib
tashlanganda unga bog'liq qoidalar ham ketdi: `MarketHealthRule` (eski
indeks formulasi), `TradeRulesRule` (eski R/R va stop foizlari),
`ZoneIntegrityRule`, `VolatilityRule`, `BtcMarketRule`. Bu yerda faqat
tahlildan MUSTAQIL, sof xavfsizlik qoidalari qoldi — ular yangi modul
bilan ham xuddi shunday ishlaydi.

0.3-band (fail-safe): ma'lumot yetishmasa yoki noaniq bo'lsa, qoida signal
BERMASLIKKA moyil bo'ladi.
"""

from __future__ import annotations

from typing import Protocol

from core.config.schema import RiskEngineConfig
from core.domain.enums import BlockReason, HealthBand
from core.domain.models import RiskDecision, SignalCandidate
from core.risk_engine.context import RiskContext
from core.utils.time_utils import is_within_daily_window


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
