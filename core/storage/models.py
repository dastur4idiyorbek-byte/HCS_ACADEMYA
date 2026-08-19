"""Ma'lumotlar bazasi sxemasi (7-bo'lim, 2-bosqich).

Jadvallar: users, subscriptions, payments, signals, signal_events, content,
violations, price_config, risk_config, coin_rulings (haram/mashbooh),
user_positions, daily_stats, market_health_log, risk_blocks.

MUHIM: bu modul `aiogram` ga bog'liq emas — `core/` qoidasi (0.1-band).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.storage.base import Base, TimestampMixin

# --------------------------------------------------------------------------- #
#  Foydalanuvchilar va obuna (1-bo'lim)
# --------------------------------------------------------------------------- #


class User(Base, TimestampMixin):
    """1.1-band: bitta bot, rol Telegram ID asosida aniqlanadi."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="uz", nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 5.1-band: foydalanuvchi O'ZI kiritgan balans (haqiqiy hisobga ulanmagan)
    declared_balance_usd: Mapped[float | None] = mapped_column(Float)
    balance_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    positions: Mapped[list[UserPosition]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    violations: Mapped[list[Violation]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Subscription(Base, TimestampMixin):
    """1.2-band: uch tarif × ikki muddat."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 1.2-band: muddat tugashiga 1-2 kun qolganda eslatma (takror yubormaslik uchun)
    reminders_sent: Mapped[str | None] = mapped_column(String(32))
    # 1.3-band: qoidabuzarlik uchun vaqtincha to'xtatish
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspend_reason: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="subscriptions")
    payment: Mapped[Payment | None] = relationship(back_populates="subscription")

    __table_args__ = (Index("ix_subscriptions_status_expires", "status", "expires_at"),)


class Payment(Base, TimestampMixin):
    """1.2-band: to'lov avtomatik EMAS — chek yuboriladi, admin qo'lda tasdiqlaydi."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True, nullable=False)
    # Telegram file_id — chek/skrinshot
    receipt_file_id: Mapped[str | None] = mapped_column(String(256))
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reject_reason: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="payments")
    subscription: Mapped[Subscription | None] = relationship(back_populates="payment")


class PriceConfig(Base, TimestampMixin):
    """1.2-band: narx va to'lov rekvizitlari — admin panel orqali dinamik."""

    __tablename__ = "price_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tier: Mapped[str] = mapped_column(String(16), nullable=False)
    period: Mapped[str] = mapped_column(String(16), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_details: Mapped[str | None] = mapped_column(Text)  # karta raqami / hamyon manzili
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("tier", "period", "currency", name="tier_period_currency"),
    )


class Content(Base, TimestampMixin):
    """1.5-band: video/strategiya kontent, minimal tarif belgilangan holda."""

    __tablename__ = "content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(String(256))
    min_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Violation(Base, TimestampMixin):
    """1.3-band: qoidabuzarlik — ogohlantirish va tarifni vaqtincha to'xtatish."""

    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reported_by: Mapped[int | None] = mapped_column(BigInteger)
    suspended_days: Mapped[int | None] = mapped_column(Integer)

    user: Mapped[User] = relationship(back_populates="violations")


# --------------------------------------------------------------------------- #
#  3.4 / 1.4 — Halol coin ro'yxati
# --------------------------------------------------------------------------- #


class CoinRuling(Base, TimestampMixin):
    """1.4-band: harom / shubhali (mashbooh) ro'yxati, admin tahrirlaydi.

    Bitta jadval, `status` ustuni bilan — chunki mantiq bir xil ("savdodan
    chetlatish"), farq faqat sababda. Shubhali ham harom kabi chetlab
    o'tiladi.
    """

    __tablename__ = "coin_rulings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # halal|mashbooh|haram
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(64))  # qo'lda / tashqi manba nomi
    set_by: Mapped[int | None] = mapped_column(BigInteger)


class HalalUniverseSnapshot(Base, TimestampMixin):
    """3.4-band: hisoblangan "Top 30 Halal" ro'yxatining qaydi.

    Nima uchun saqlanadi: postmortem (3.8) "o'sha paytda ro'yxat qanday edi"
    degan savolga javob bera olishi kerak.
    """

    __tablename__ = "halal_universe_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbols: Mapped[str] = mapped_column(Text, nullable=False)  # vergul bilan ajratilgan
    scanned_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# --------------------------------------------------------------------------- #
#  Signallar (2-bo'lim)
# --------------------------------------------------------------------------- #


class SignalRecord(Base, TimestampMixin):
    """Signal — qo'lda kiritilgan yoki avtomatik yaratilgan."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False)

    entry: Mapped[float] = mapped_column(Float, nullable=False)
    stop: Mapped[float] = mapped_column(Float, nullable=False)
    tp1: Mapped[float] = mapped_column(Float, nullable=False)
    tp2: Mapped[float] = mapped_column(Float, nullable=False)

    # 5.1.0-band: kirish buyurtmasi turi (limit|market) — signal shakllanganda
    # narx va Entry orasidagi masofaga qarab avtomatik tanlanadi.
    entry_order_type: Mapped[str] = mapped_column(String(8), default="limit", nullable=False)
    # Signal shakllangan paytdagi bozor narxi — postmortem (3.8) uchun: kirish
    # nuqtasi zaif bo'lganmi degan savolga javob shu maydondan chiqadi.
    price_at_signal: Mapped[float | None] = mapped_column(Float)
    # Chiqish har doim OCO (TP + Stop birgalikda) — kelajakda o'zgarsa shu yerda.
    exit_order_type: Mapped[str] = mapped_column(String(8), default="oco", nullable=False)

    score: Mapped[float | None] = mapped_column(Float)
    # 3.6-band: "Nega bu signal?" — ball tafsiloti JSON matn sifatida
    score_breakdown: Mapped[str | None] = mapped_column(Text)
    # 3.6-band: "Nega bu coin halol?"
    halal_reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    # Signal berilgan paytdagi bozor konteksti — postmortem (3.8) uchun SHART
    market_health_at_entry: Mapped[float | None] = mapped_column(Float)
    correlation_group: Mapped[str | None] = mapped_column(String(32))

    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_price: Mapped[float | None] = mapped_column(Float)
    result_pct: Mapped[float | None] = mapped_column(Float)

    # 3.8-band: "yolg'on signal" — faol bo'lgach 1 soat ichida Stop
    is_false_signal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    postmortem_notes: Mapped[str | None] = mapped_column(Text)

    # Telegram xabar id — holat o'zgarganda tahrirlash uchun
    broadcast_message_ids: Mapped[str | None] = mapped_column(Text)

    events: Mapped[list[SignalEvent]] = relationship(
        back_populates="signal", cascade="all, delete-orphan"
    )
    positions: Mapped[list[UserPosition]] = relationship(
        back_populates="signal", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_signals_status_created", "status", "created_at"),)


class SignalEvent(Base, TimestampMixin):
    """Signal hayotidagi har bir o'zgarish — to'liq audit izi."""

    __tablename__ = "signal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(
        ForeignKey("signals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event: Mapped[str] = mapped_column(String(32), nullable=False)
    price: Mapped[float | None] = mapped_column(Float)
    score: Mapped[float | None] = mapped_column(Float)
    detail: Mapped[str | None] = mapped_column(Text)

    signal: Mapped[SignalRecord] = relationship(back_populates="events")


class RiskBlock(Base, TimestampMixin):
    """4-bo'lim: Risk Engine nima uchun signalni to'xtatdi.

    Admin dashboardida "tizim nega sokin?" savoliga aniq javob beradi
    (3.7-band bilan birga).
    """

    __tablename__ = "risk_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(32), index=True)
    reason: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    market_health: Mapped[float | None] = mapped_column(Float)


class RiskConfigEntry(Base, TimestampMixin):
    """1.5-band: risk konfiguratsiyasini admin panel orqali sozlash.

    YAML standartlarini bosib o'tuvchi kalit-qiymat qatlami. Kalit — YAML'dagi
    yo'l, masalan `risk_engine.daily_loss_limit_pct`.
    """

    __tablename__ = "risk_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON kodlangan qiymat
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------- #
#  5.4 — Shaxsiy portfel va statistika
# --------------------------------------------------------------------------- #


class UserPosition(Base, TimestampMixin):
    """5.4-band: "Men kirdim" tugmasi orqali qayd etilgan pozitsiya."""

    __tablename__ = "user_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    signal_id: Mapped[int] = mapped_column(
        ForeignKey("signals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    # Pozitsiya ochilganda qancha xavf ajratilgani (5.1.1 byudjet nazorati uchun)
    risk_amount_usd: Mapped[float | None] = mapped_column(Float)
    trade_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit_price: Mapped[float | None] = mapped_column(Float)
    pnl_usd: Mapped[float | None] = mapped_column(Float)
    pnl_pct: Mapped[float | None] = mapped_column(Float)

    user: Mapped[User] = relationship(back_populates="positions")
    signal: Mapped[SignalRecord] = relationship(back_populates="positions")

    __table_args__ = (
        UniqueConstraint("user_id", "signal_id", name="user_signal"),
        Index("ix_user_positions_user_date", "user_id", "trade_date"),
    )


class DailyStat(Base, TimestampMixin):
    """3.6 / 5.4-band: shaffoflik uchun real statistika (kunlik agregat)."""

    __tablename__ = "daily_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stat_date: Mapped[date] = mapped_column(Date, unique=True, index=True, nullable=False)
    signals_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    signals_activated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tp1_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tp2_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stop_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    false_signal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_score: Mapped[float | None] = mapped_column(Float)
    avg_risk_reward: Mapped[float | None] = mapped_column(Float)
    total_participants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_volume_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


# --------------------------------------------------------------------------- #
#  3.7 — Bozor Salomatligi Indeksi tarixi
# --------------------------------------------------------------------------- #


class MarketHealthLog(Base, TimestampMixin):
    """3.7-band: indeks har sham yopilganda qayta hisoblanadi va saqlanadi.

    Tarix postmortem (3.8) uchun zarur: "Indeks 60dan past bo'lganda berilgan
    signallarning necha foizi Stop yegan?" degan savolga javob shu jadvaldan
    chiqadi.
    """

    __tablename__ = "market_health_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    band: Mapped[str] = mapped_column(String(8), nullable=False)
    btc_dominance_score: Mapped[float | None] = mapped_column(Float)
    trend_breadth_score: Mapped[float | None] = mapped_column(Float)
    volatility_score: Mapped[float | None] = mapped_column(Float)
    user_capacity_score: Mapped[float | None] = mapped_column(Float)
    saturation_score: Mapped[float | None] = mapped_column(Float)
    is_daily_preview: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_market_health_created", "created_at"),)
