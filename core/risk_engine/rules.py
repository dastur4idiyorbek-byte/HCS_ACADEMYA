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
    """Indeks past bo'lganda FAQAT korreksiya strategiyasi o'tadi (3.7-band).

    ILGARI BU QOIDA HAMMASINI TO'XTATARDI. Bu strategiyaning o'z
    falsafasiga zid edi: past indeks — narxlar ARZONLASHGAN payt,
    ya'ni "arzon ol" uchun eng qulay lahza. Tizim shunda ko'zini
    yumib, indeks qayta ko'tarilgach — narx allaqachon o'sgach —
    signal berardi. Natijada doim KECH kirardi.

    Endi past bandda `correction_entry` o'tadi: u tushayotgan bozorga
    emas, KO'TARILISHDAGI korreksiyaga mo'ljallangan va o'zining
    qat'iy yo'nalish darvozasi bor.

    Qolgan strategiyalar past bandda baribir to'xtatiladi — ular
    korreksiya uchun mo'ljallanmagan.
    """

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
            if candidate.source is SignalSource.CORRECTION_ENTRY:
                return RiskDecision.allow()
            return RiskDecision.block(
                BlockReason.MARKET_HEALTH_LOW,
                f"Bozor Salomatligi Indeksi past ({health.value:.0f}/100) — "
                "bu bandda faqat korreksiya kirishi ko'riladi.",
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


# 4.4 — BOZOR REJIMI QOIDASI OLIB TASHLANDI.
#
# `MarketRegimeRule` mavjud edi, lekin u FAQAT `adx is None` ni
# tekshirardi: `adx_trend_threshold` (20) bilan taqqoslash umuman
# yo'q edi. Ya'ni docstring "tekis bozorda signal berilmaydi"
# derdi, kod esa boshqa narsa qilardi — yarim holat.
#
# Ikki yo'ldan BIRI tanlandi: chegarani ulash yoki qoidani
# o'chirish.
#
# CHEGARA ULANMADI, sababi ikkita va ikkalasi ham o'lchovga
# tayanadi:
#
#   1. Ablation (2026-09-03): trend omili — uning ichida ADX ham
#      bor — ballga hech narsa qo'shmadi. PF 0.84 -> 0.83. ADX
#      keyingi harakat haqida ma'lumot bermayapti, shuning uchun
#      unga tayanib SIGNALNI TO'XTATISH asossiz.
#   2. Loyihaning o'z tarixi: qat'iy filtr ko'paytirish signal
#      voronkasini allaqachon nolga tushirgan (40 va 44-bo'lim).
#
# ADX YO'QOLMADI: u ball omilining bir qismi bo'lib qoladi
# (`factors.py`, `adx_trend_threshold` o'sha yerda o'qiladi).
# O'zgargan narsa — u endi TO'SIQ emas, faqat baho.
#
# `adx is None` fail-safe'i ham yo'qolmadi: nomzod bu yergacha
# yetib kelishi uchun `classic_ta` ning "indicators" bosqichidan
# o'tishi shart, u esa to'liq bo'lmagan indikatorlarni allaqachon
# rad etadi.


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
#  0.3 — Kirish zonasi buzilganmi (fail-safe)
# --------------------------------------------------------------------------- #


class ZoneIntegrityRule(_BaseRule):
    """Narx kirish zonasidan PASTGA tushib ketgan bo'lsa signal berilmaydi.

    NIMA UCHUN QOIDA, NEGA `entry_order.py` DA EMAS.
    `plan_entry()` bu holatni allaqachon aniqlar va `is_valid=False`
    qaytarardi — lekin bu maydonni HECH KIM O'QIMASDI. Runner baribir
    signalni bazaga yozib tarqatardi, backtest esa `plan_entry()` ni
    umuman chaqirmaydi. Ya'ni `zone_broken_threshold_pct` sozlamasi
    yozilgan, hisoblangan va e'tiborsiz qoldirilgan edi.

    Endi tekshiruv Risk Engine'da: jonli tizim ham, backtest ham
    ayni bir qarordan o'tadi va voronkada ko'rinadi.

    MANTIQ. Signal "narx shu support zonasiga qaytdi" degan taxminga
    quriladi. Narx zonadan sezilarli pastga tushgan bo'lsa, taxmin
    allaqachon buzilgan: Stop yaqin, zona esa endi tayanch emas.
    Bu bashorat emas, ASOSNING yo'qolgani.

    `current_price` yo'q bo'lsa tekshiruv o'tkazib yuboriladi —
    narxning umuman yo'qligini `FreshDataRule` ushlaydi.
    """

    name = "zone_integrity"

    def __init__(self, config: RiskEngineConfig, threshold_pct: float) -> None:
        super().__init__(config)
        self._threshold_pct = threshold_pct

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        narx = context.current_price
        if narx is None or narx <= 0:
            return RiskDecision.allow()

        entry = candidate.levels.entry
        if entry <= 0:
            return RiskDecision.allow()

        masofa_pct = (narx - entry) / entry * 100
        if masofa_pct >= -self._threshold_pct:
            return RiskDecision.allow()

        return RiskDecision.block(
            BlockReason.ZONE_BROKEN,
            f"Narx kirish nuqtasidan {abs(masofa_pct):.2f}% pastda "
            f"(ruxsat {self._threshold_pct:.2f}%) — zona buzilgan, "
            "savdoning asosi yo'qolgan.",
        )


# --------------------------------------------------------------------------- #
#  3.3 — Universal risk qoidasi (darajalar mantiqiyligi)
# --------------------------------------------------------------------------- #


class TradeRulesRule:
    """3.3-band: Stop ruxsat etilgan oraliqda, TP2 minimal NISBATNI ta'minlasin.

    ASOSIY SHART — NISBAT, masofa emas. Stop 1%..5% oralig'ida erkin
    joylashadi (S/R zonasi qayerda ekaniga qarab), lekin TP2/Stop nisbati
    kamida 1:3 bo'lishi SHART.

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
        overrides: dict[SignalSource, tuple[float, float, float, float]] | None = None,
        min_stop_pct: float = 0.0,
        enforce_bands: bool = False,
    ) -> None:
        self._enforce_bands = enforce_bands
        self._min_stop_pct = min_stop_pct
        self._max_stop_pct = max_stop_pct
        self._min_tp_pct = min_tp_pct
        self._max_tp_pct = max_tp_pct
        self._min_rr = min_rr
        #: Strategiya -> (min_tp_pct, max_tp_pct, min_rr, min_stop_pct)
        self._overrides = overrides or {}

    def _bounds_for(self, source: SignalSource) -> tuple[float, float, float, float]:
        return self._overrides.get(
            source,
            (self._min_tp_pct, self._max_tp_pct, self._min_rr, self._min_stop_pct),
        )

    def check(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        levels = candidate.levels
        min_tp, max_tp, min_rr, min_stop = self._bounds_for(candidate.source)
        muammolar: list[str] = []

        # FOIZ ORALIQLARI — MAJBURIY EMAS.
        #
        # Loyiha egasining qarori (2026-09-02): "TP STOP FOIZLARI
        # MAJBURIY EMAS — RISK 1/3". Ular `enforce_distance_bands`
        # yoqilgandagina to'sadi.
        #
        # MUHIM: bu tekshiruv `build_levels` bilan BIR XIL qoidaga
        # bo'ysunishi shart. Aks holda darajalar qurilib, keyin shu
        # yerda darhol yo'q qilinardi — 67-bo'limdagi xatoning aynan
        # o'zi.
        if self._enforce_bands:
            # Stop IKKI tomonlama tekshiriladi: juda yaqin bo'lsa bozor
            # shovqini uni yeb qo'yadi, juda uzoq bo'lsa pozitsiya
            # ma'nosiz kichrayadi.
            if levels.stop_distance_pct < min_stop - _EPSILON:
                muammolar.append(
                    f"Stop juda yaqin: {levels.stop_distance_pct:.2f}% < "
                    f"{min_stop}% — bozor shovqini yeb qo'yadi"
                )
            if levels.stop_distance_pct > self._max_stop_pct + _EPSILON:
                muammolar.append(
                    f"Stop juda uzoq: {levels.stop_distance_pct:.2f}% > {self._max_stop_pct}%"
                )
            for index, tp in enumerate(levels.takes, start=1):
                masofa = (tp.price - levels.entry) / levels.entry * 100
                if not min_tp - _EPSILON <= masofa <= max_tp + _EPSILON:
                    muammolar.append(
                        f"TP{index} masofasi {masofa:.2f}% "
                        f"{min_tp}–{max_tp}% oralig'idan tashqarida"
                    )

        # ASOSIY SHART. Stop foizi kichik yoki katta bo'lishidan qat'i
        # nazar, nisbat ta'minlanmasa signal berilmaydi. Nisbat YAKUNIY
        # nishon bo'yicha o'lchanadi — TP nechta bo'lishidan qat'i nazar.
        if levels.risk_reward < min_rr - _EPSILON:
            muammolar.append(
                f"Nisbat yetarli emas: 1:{levels.risk_reward:.1f} < "
                f"1:{min_rr:.0f} (Stop {levels.stop_distance_pct:.2f}% bo'lsa "
                f"yakuniy nishon kamida {levels.stop_distance_pct * min_rr:.2f}% "
                "bo'lishi kerak)"
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
