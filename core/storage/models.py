"""Ma'lumotlar bazasi sxemasi (7-bo'lim, 2-bosqich).

Jadvallar: users, subscriptions, payments, signals, signal_events, content,
violations, price_config, risk_config, coin_rulings (haram/mashbooh),
user_positions, daily_stats, market_health_log, risk_blocks, audit_reports,
social_links.

MUHIM: bu modul `aiogram` ga bog'liq emas — `core/` qoidasi (0.1-band).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.storage.base import Base, TimestampMixin, UtcDateTime

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
    balance_updated_at: Mapped[datetime | None] = mapped_column(UtcDateTime)

    last_active_at: Mapped[datetime | None] = mapped_column(UtcDateTime)

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
    starts_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        UtcDateTime, index=True, nullable=False
    )
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 1.2-band: muddat tugashiga 1-2 kun qolganda eslatma (takror yubormaslik uchun)
    reminders_sent: Mapped[str | None] = mapped_column(String(32))
    # 1.3-band: qoidabuzarlik uchun vaqtincha to'xtatish
    suspended_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
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
    reviewed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
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
    # Saytga yuklangan fayl NOMI (to'liq yo'l emas). Jild doimiy diskda,
    # baza fayli yonida — shuning uchun disk ko'chsa yozuv buzilmaydi.
    video_path: Mapped[str | None] = mapped_column(String(256))
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
    """3.4-band: hisoblangan halol ro'yxatning qaydi.

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

    activated_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    close_price: Mapped[float | None] = mapped_column(Float)
    result_pct: Mapped[float | None] = mapped_column(Float)

    # 3.8-band: "yolg'on signal" — faol bo'lgach 1 soat ichida Stop
    is_false_signal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    postmortem_notes: Mapped[str | None] = mapped_column(Text)

    # Telegram xabar id — holat o'zgarganda tahrirlash uchun
    broadcast_message_ids: Mapped[str | None] = mapped_column(Text)

    #: Obunachilarga QACHON tarqatilgani. `None` — hali tarqatilmagan.
    #:
    #: Nima uchun kerak: signal endi IKKI JOYDA yaratilishi mumkin —
    #: botda va veb-panelda. Veb Telegramga xabar yubora olmaydi (kartochka
    #: `render_signal_card` bilan, har bir obunachi uchun alohida yasaladi),
    #: shuning uchun u signalni faqat bazaga yozadi. Bot esa fon vazifasida
    #: `broadcast_at IS NULL` bo'lganlarni topib tarqatadi.
    #:
    #: Mavjud `broadcast_message_ids` ustuni ishlatilmadi: uning nomi
    #: "xabar id lari" degani, "tarqatildimi" degani emas. Bitta ustunni
    #: ikki ma'noda ishlatish — bu loyihada allaqachon uchragan xato.
    broadcast_at: Mapped[datetime | None] = mapped_column(UtcDateTime, index=True)

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
    #: Nomzod olgan ball (bo'lsa). Bu ustunsiz "chegara juda balandmi yoki
    #: nomzodlar haqiqatan zaifmi" degan savolga javob berib bo'lmasdi:
    #: dashboard faqat "chegaradan past" deb yozardi, qanchalik past
    #: ekanini esa hech kim ko'rmasdi. Aynan shu ko'rlik sababli chegara
    #: 48 soat davomida erishib bo'lmas darajada balandligi sezilmadi.
    score: Mapped[float | None] = mapped_column(Float)


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

    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    exit_price: Mapped[float | None] = mapped_column(Float)
    # TP1 ga yetilganda pozitsiyaning bir qismi shu narxda yopiladi.
    # Ansiz "TP1 oldi, keyin Stop" holati sof zarar ko'rinardi.
    partial_exit_price: Mapped[float | None] = mapped_column(Float)
    partial_close_pct: Mapped[float | None] = mapped_column(Float)
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


class SocialLink(Base, TimestampMixin):
    """Saytning pastki qismidagi ijtimoiy tarmoq havolalari.

    Nima uchun bazada, koddagi ro'yxatda emas: yangi kanal qo'shish yoki
    havolani almashtirish uchun har safar kod o'zgartirib, qayta
    joylashtirish kerak bo'lardi. Admin panelda esa bu bir daqiqalik ish.

    `icon` — belgilangan ro'yxatdan tanlanadi (`telegram`, `instagram`,
    `youtube`, `web`). Ixtiyoriy matn emas: noma'lum qiymat kelsa sayt
    bo'sh joy ko'rsatardi va sabab ko'rinmasdi.
    """

    __tablename__ = "social_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    icon: Mapped[str] = mapped_column(String(32), default="web", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditReport(Base, TimestampMixin):
    """3.8-band: haftalik o'z-o'zini tekshirish hisobotining QAYDI.

    Nima uchun saqlanadi: hisobot faqat Telegramga yuborilardi. Admin uni
    o'qimay qolsa yoki chat tozalansa — hisobot butunlay yo'qolardi, ya'ni
    "o'tgan oy tizim qanday ishlagan" degan savolga javob bermasdi. Endi
    veb-panel ham xuddi shu qaydni ko'rsatadi.

    `rendered` — tayyor matn. Nima uchun raqamlar bilan birga to'liq matn
    ham: naqshlar (`patterns`) tuzilmasi kelajakda o'zgarishi mumkin, matn
    esa o'sha paytda admin AYNAN NIMANI ko'rgani. Bu — audit izi.
    """

    __tablename__ = "audit_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True, nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    rendered: Mapped[str] = mapped_column(Text, nullable=False)

    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    traded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tp2: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tp1_then_stop: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stop: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancelled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    false_signals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_score: Mapped[float | None] = mapped_column(Float)
    average_holding_hours: Mapped[float | None] = mapped_column(Float)
    pattern_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sample_warning: Mapped[str | None] = mapped_column(Text)

    #: Bir kunda bitta qayd: admin tugmani o'n marta bossa ham jadval
    #: to'lib ketmasligi kerak, oxirgi holat esa doim yangi bo'lishi kerak.
    report_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("report_date", "period_days", name="report_date_period"),
    )


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
