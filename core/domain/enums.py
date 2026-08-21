"""Butun tizim bo'ylab umumiy sanoq turlari."""

from __future__ import annotations

from enum import Enum


class SignalStatus(str, Enum):
    """2-bo'lim: signal holati (to'liq avtomatik kuzatiladi)."""

    PENDING = "pending"          # ⏳ Kutilmoqda — narx Entry'ga yetmagan
    ACTIVE = "active"            # 🟢 Faol — narx Entry'ga yetgan
    TP1_HIT = "tp1_hit"          # 🎯 TP1 olindi
    TP2_HIT = "tp2_hit"          # 🏁 TP2 olindi — yopiladi
    STOPPED = "stopped"          # 🛑 Stop bo'ldi — yopiladi
    WEAKENING = "weakening"      # ⚠️ Zaiflashmoqda (4.1-band)
    CANCELLED = "cancelled"      # bekor qilingan (Entry'ga yetmasdan eskirgan)

    @property
    def is_closed(self) -> bool:
        return self in {SignalStatus.TP2_HIT, SignalStatus.STOPPED, SignalStatus.CANCELLED}

    @property
    def is_open(self) -> bool:
        return not self.is_closed

    @property
    def emoji(self) -> str:
        return _STATUS_EMOJI[self]


#: Har bir belgi BITTA ma'noda. Avval ✅ ham "faol", ham "tasdiqlandi",
#: ham "saqlandi" degani edi; 🎯 esa ham TP, ham Limit buyurtma edi —
#: shu sababli kartochkani ko'z bilan o'qib bo'lmasdi.
_STATUS_EMOJI: dict[SignalStatus, str] = {
    SignalStatus.PENDING: "⏳",     # kutilmoqda
    SignalStatus.ACTIVE: "🟢",      # ochiq va ishlayapti
    SignalStatus.TP1_HIT: "🎯",     # foyda nuqtasi
    SignalStatus.TP2_HIT: "🏁",     # yakuniy maqsad — tugadi
    SignalStatus.STOPPED: "🛑",     # zarar bilan yopildi
    SignalStatus.WEAKENING: "⚠️",   # ogohlantirish
    SignalStatus.CANCELLED: "⛔",   # umuman ochilmadi
}


class OrderType(str, Enum):
    """5.1.0-band: kirish buyurtmasi turi — avtomatik tanlanadi.

    LIMIT  — narx hali kutilgan Entry zonasiga yetib bormagan; buyurtma
             narx zonaga kelganda avtomatik bajariladi.
    MARKET — narx allaqachon Entry zonasida, signal aynan shu daqiqada
             shakllanmoqda; kutish shart emas.
    """

    LIMIT = "limit"
    MARKET = "market"

    @property
    def emoji(self) -> str:
        """📌 — narx belgilangan joyga kelishini kutamiz; ⚡ — hozir.

        🎯 ATAYLAB ishlatilmaydi: u faqat foyda nuqtasi (TP) uchun.
        Bitta belgi ikki ma'noda ishlatilsa, kartochka o'qilmay qoladi.
        """
        return "📌" if self is OrderType.LIMIT else "⚡"

    @property
    def label_uz(self) -> str:
        """Nima qilish kerakligini AYTADI, turini nomlab qo'ymaydi."""
        if self is OrderType.LIMIT:
            return "Buyurtma qoldiring — narx shu yerga kelganda ochiladi"
        return "Hozir oling — narx allaqachon kerakli joyda"


class ExitOrderType(str, Enum):
    """Chiqish har doim OCO: TP va Stop birgalikda, biri bajarilsa
    ikkinchisi avtomatik bekor bo'ladi."""

    OCO = "oco"


class SignalSource(str, Enum):
    """Signal qayerdan keldi."""

    MANUAL = "manual"                      # 2-bo'lim: admin qo'lda kiritgan
    CLASSIC_TA = "classic_ta"              # 3.1 — S/R + indikatorlar
    OPENING_RANGE_SCALP = "opening_range_scalp"  # 3.9 — kunlik sham ochilishi


class HalalStatus(str, Enum):
    """1.4 / 3.4-band: coin halollik holati.

    Shubhali (mashbooh) ham HAROM kabi chetlab o'tiladi — "shubhali narsadan
    yiroqlashish" tamoyili.
    """

    HALAL = "halal"
    MASHBOOH = "mashbooh"   # shubhali
    HARAM = "haram"

    @property
    def is_tradable(self) -> bool:
        return self is HalalStatus.HALAL


class HealthBand(str, Enum):
    """3.7-band: Bozor Salomatligi Indeksi diapazoni."""

    HIGH = "high"   # 🟢 80-100 — chegara past, erkin
    MID = "mid"     # 🟡 40-79  — ehtiyotkorroq
    LOW = "low"     # 🔴 0-39   — yangi signal to'xtatiladi

    @property
    def emoji(self) -> str:
        return {"high": "🟢", "mid": "🟡", "low": "🔴"}[self.value]


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class ZoneKind(str, Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"


class SubscriptionTier(str, Enum):
    """1.2-band: uch tarif."""

    LITE = "lite"        # faqat signal
    PRO = "pro"          # video darslar + signal
    PREMIUM = "premium"  # barchasi

    @property
    def rank(self) -> int:
        return {"lite": 1, "pro": 2, "premium": 3}[self.value]

    def covers(self, required: SubscriptionTier) -> bool:
        """Shu tarif `required` darajadagi kontentni ocha oladimi?"""
        return self.rank >= required.rank


class SubscriptionPeriod(str, Enum):
    DAILY = "daily"      # sinov muddati
    MONTHLY = "monthly"


class SubscriptionStatus(str, Enum):
    PENDING = "pending"      # to'lov tasdiqlanishini kutmoqda
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"  # 1.3-band: qoidabuzarlik uchun to'xtatilgan


class PaymentStatus(str, Enum):
    """1.2-band: to'lov avtomatik EMAS — admin qo'lda tasdiqlaydi."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Currency(str, Enum):
    KGS = "KGS"
    USDT = "USDT"


class UserRole(str, Enum):
    """1.1-band: bitta bot, ikkita rol (Telegram ID asosida)."""

    USER = "user"
    ADMIN = "admin"


class ContentKind(str, Enum):
    VIDEO = "video"
    STRATEGY = "strategy"
    DOCUMENT = "document"


class BlockReason(str, Enum):
    """4-bo'lim: Risk Engine signalni nima uchun to'xtatdi.

    Har bir to'xtatish log qilinadi va admin dashboardida ko'rinadi —
    "tizim nega sokin?" degan savolga aniq javob.
    """

    DAILY_LOSS_LIMIT = "daily_loss_limit"                # 4.1
    MAX_OPEN_SIGNALS = "max_open_signals"                # 4.2
    CORRELATION = "correlation"                          # 4.3
    SIDEWAYS_MARKET = "sideways_market"                  # 4.4
    BTC_MARKET_FILTER = "btc_market_filter"              # 4.5
    LOW_VOLATILITY = "low_volatility"                    # 4.6
    KILL_SWITCH = "kill_switch"                          # 4.7
    FRIDAY_PRAYER = "friday_prayer"                      # 4.8
    MARKET_HEALTH_LOW = "market_health_low"              # 4.9
    CONSECUTIVE_LOSSES = "consecutive_losses"            # 4.10
    SCORE_BELOW_THRESHOLD = "score_below_threshold"      # 3.5
    NOT_HALAL = "not_halal"                              # 3.4
    RISK_RULES_VIOLATED = "risk_rules_violated"          # 3.3
    STALE_MARKET_DATA = "stale_market_data"              # 0.3 fail-safe
    INTERNAL_ERROR = "internal_error"                    # 0.3 fail-safe


class AllocationMethod(str, Enum):
    """5.1.1-band: kunlik byudjetni taqsimlash usuli."""

    SEQUENTIAL_DECAY = "sequential_decay"  # tavsiya etiladi
    EQUAL_SPLIT = "equal_split"
