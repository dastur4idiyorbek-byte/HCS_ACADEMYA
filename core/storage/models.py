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
    text,
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

    #: Maqola matni (`kind="maqola"`). Video uchun bo'sh qoladi.
    #:
    #: NEGA ALOHIDA MAYDON, `description` EMAS: `description` — qisqa
    #: tavsif va u ro'yxatda ko'rinadi. Maqolaning tanasi esa uzun va
    #: faqat ochilganda kerak. Ikkalasini bitta maydonga tiqsak,
    #: ro'yxatda butun maqola chiqib ketardi.
    body: Mapped[str | None] = mapped_column(Text)

    #: Video uzunligi yoki maqolani o'qish vaqti — SONIYADA.
    #:
    #: Nima uchun soniya, "12:45" emas: matn ko'rinishi tildan va
    #: joydan bog'liq, saralash esa songa muhtoj. Formatlash — chetda.
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    #: Toifa yorlig'i ("Risk Management", "Bozor strukturasi").
    #: ERKIN MATN va bu ataylab: qat'iy ro'yxat qilinsa, yangi mavzu
    #: qo'shish uchun har safar kod o'zgartirish kerak bo'lardi.
    category: Mapped[str | None] = mapped_column(String(64))


class ContentProgress(Base, TimestampMixin):
    """Foydalanuvchi qaysi darsda qayerda to'xtagani.

    NEGA KERAK. "Davom ettirish" tugmasi ishlashi uchun tizim kimning
    qayerda qolganini bilishi shart. Ansiz har safar boshidan
    boshlanadi va uzun kursni tugatib bo'lmaydi.

    NEGA FOIZ, VAQT EMAS. Vaqt (sekund) aniqroq, lekin u faqat
    videoga to'g'ri keladi. Maqolada esa "qayergacha o'qildi" degan
    o'lchov — sahifaning necha foizi. Foiz ikkalasiga ham yaraydi.

    HAR JUFTLIK BITTA QATOR: bitta foydalanuvchi bitta darsda bir
    marta turadi. Aks holda tarix yig'ilib, "oxirgisi qaysi?" degan
    savol tug'ilardi — u esa bu yerda kerak emas.
    """

    __tablename__ = "content_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "content_id", name="uq_progress_user_content"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content_id: Mapped[int] = mapped_column(
        ForeignKey("content.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: 0 dan 100 gacha.
    percent: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )


class UserWidget(Base, TimestampMixin):
    """Foydalanuvchi bosh sahifasida qaysi vidjet, qaysi tartibda.

    NEGA BAZADA, BRAUZERDA EMAS. Odam telefonda ham, kompyuterda ham
    kiradi va tanlovi ikkalasida bir xil bo'lishi kerak. Brauzer
    xotirasi qurilmaga bog'langan — u yerda saqlansa, telefonda
    qilingan tartib kompyuterda yo'q bo'lardi.

    NEGA HAR VIDJET ALOHIDA QATOR, JSON EMAS. Tartibni o'zgartirish
    va bittasini o'chirish — oddiy SQL. JSON bo'lsa, butun ro'yxatni
    o'qib, o'zgartirib, qayta yozish kerak bo'lardi va ikki qurilma
    bir vaqtda yozsa biri ikkinchisini yo'qotardi.

    RO'YXATI BO'SH FOYDALANUVCHI — yangi kelgan odam. Unga sukut
    bo'yicha to'plam ko'rsatiladi (`web/src/lib/vidjetlar.ts`), bazaga
    esa hech narsa yozilmaydi: u hali hech narsa tanlamagan.
    """

    __tablename__ = "user_widgets"
    __table_args__ = (
        UniqueConstraint("user_id", "widget", name="uq_widget_user_widget"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: Vidjet kodi — `web/src/lib/vidjetlar.ts` dagi ro'yxatdan.
    widget: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Kichik raqam tepada turadi.
    position: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )


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
    #: TP SONI QAT'IY EMAS — 1, 2 yoki 3. Faqat `tp1` majburiy:
    #: bitta nishon ham to'liq signal (toza ko'tarilishda ustda
    #: qarshilik bo'lmasligi mumkin).
    tp1: Mapped[float] = mapped_column(Float, nullable=False)
    tp2: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp3: Mapped[float | None] = mapped_column(Float, nullable=True)

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

    #: TP1 ga bir marta yetganmi.
    #:
    #: Nima uchun `status` yetarli emas: TP1 dan keyin narx qaytsa
    #: `status` STOPPED bo'ladi, "zaiflashmoqda" belgisi esa uni
    #: WEAKENING ga o'zgartiradi — ikkala holatda ham "TP1 olingan edi"
    #: fakti YO'QOLADI. U esa natijani hisoblashda kerak: TP1 da
    #: pozitsiyaning bir qismi allaqachon sotilgan.
    tp1_reached: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    #: Nechta TP ga yetilgan. `tp1_reached` "kamida bittasi" degan
    #: savolga javob beradi va u saqlanadi — eski yozuvlar va
    #: hisobotlar unga tayanadi.
    reached_tps: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

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

    # 4-prompt, 4-qism: admin QO'LDA yuklaydigan ikkita grafik rasmi.
    #
    # NIMA UCHUN QO'LDA. Tizim o'zi ham grafik chizadi (Pillow), lekin
    # u faqat darajalarni ko'rsatadi. Admin TradingView'da chizgan
    # rasm esa STRUKTURANI ko'rsatadi — nega aynan shu joy tanlangani.
    # Ikkalasi boshqa savolga javob beradi, shuning uchun biri
    # ikkinchisining o'rnini bosmaydi.
    #
    # FAQAT FAYL NOMI saqlanadi (to'liq yo'l emas) — video va bosh
    # sahifa postlari bilan bir xil sabab.
    #: Signal berilgan paytdagi grafik
    entry_chart_image: Mapped[str | None] = mapped_column(String(256))
    #: Signal YOPILGANDA — yakuniy natija grafigi
    result_chart_image: Mapped[str | None] = mapped_column(String(256))

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



class BozorKesimi(Base, TimestampMixin):
    """Sayt uchun bozor kesimlari — BTC.D, USDT.D, TOTAL, TOTAL2/3, OTHERS.

    NIMA UCHUN SAQLANADI. Bu qiymatlar birjadan SHAM sifatida
    kelmaydi: manba faqat HOZIRGI holatni beradi. Yo'nalish esa
    tarixsiz aniqlanmaydi. Shuning uchun har kuni bir marta
    yozib boramiz va tarix shundan yig'iladi.

    SIGNALGA BOG'LANMAYDI. Loyiha egasining sharti: haftalik va
    kunlik qarash faqat sayt uchun, asosiy tahlil 4 soatlikda
    qoladi.
    """

    __tablename__ = "bozor_kesimlari"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: `BTC.D`, `USDT.D`, `TOTAL`, `TOTAL2`, `TOTAL3`, `OTHERS`
    kod: Mapped[str] = mapped_column(String(16), nullable=False)
    qiymat: Mapped[float] = mapped_column(Float, nullable=False)
    olingan: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)

    __table_args__ = (
        Index("ix_bozor_kesim_kod_vaqt", "kod", "olingan"),
    )


class BozorKorinishi(Base, TimestampMixin):
    """Tayyor POST — hafta boshida va kun boshida.

    NIMA UCHUN TAYYOR HOLDA SAQLANADI. Postni bot quradi: unda
    BTC va ETH shamlari bor, saytda esa yo'q. Sayt uni qayta
    hisoblasa, ikkita joyda ikkita javob paydo bo'lardi — bu
    loyihada besh marta uchragan xato turi.

    Sayt faqat O'QIYDI va ko'rsatadi.
    """

    __tablename__ = "bozor_korinishlari"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: `haftalik` yoki `kunlik`
    turi: Mapped[str] = mapped_column(String(16), nullable=False)
    sana: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    #: Qatorlar JSON ko'rinishida: kod, nom, qiymat, o'zgarish, yo'nalish
    asboblar_json: Mapped[str] = mapped_column(Text, nullable=False)
    xulosa: Mapped[str] = mapped_column(Text, nullable=False)
    #: An'anaviy o'qish — KAFOLAT EMAS, matnda ham shunday yozilgan
    kutilma: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (Index("ix_bozor_korinish_turi_sana", "turi", "sana"),)


# --------------------------------------------------------------------------- #
#  Portfel va xavf boshqaruvi moduli (3-prompt)
# --------------------------------------------------------------------------- #


class CapitalBlock(Base, TimestampMixin):
    """Foydalanuvchi balansining bitta bo'lagi va uning band qismi.

    NIMA UCHUN BAZADA. `core/portfolio/capital_allocator.py` sof
    funksiyalardan iborat: kirish — bo'laklar ro'yxati, chiqish — yangi
    ro'yxat. U hech narsa eslab qolmaydi. Bot qayta ishga tushganda
    "1-bo'lak band" degan bilim yo'qolsa, o'sha bo'lakka ikkinchi
    pozitsiya ochilib, xavf ikki barobar bo'lardi.

    Shu jadval — o'sha yagona eslab qolinadigan holat.
    """

    __tablename__ = "capital_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: Bo'lak raqami: 1, 2, 3 ... (config'dagi bo'lak soniga qadar)
    raqam: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Bo'lakning hajmi — balans / bo'lak soni
    hajm_usd: Mapped[float] = mapped_column(Float, nullable=False)
    #: Ochiq pozitsiyalarga ketgan pul
    band_kapital_usd: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0", nullable=False
    )
    #: O'sha pozitsiyalarda XAVF ostidagi pul (Stop ursa yo'qoladi)
    band_xavf_usd: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0", nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "raqam", name="user_bolak"),)


class PositionExit(Base, TimestampMixin):
    """Pozitsiyaning BITTA yopilgan qismi — TP bosqichi yoki Stop.

    NIMA UCHUN QISM DARAJASIDA. Signal N ta TP bilan bosqichma-bosqich
    yopiladi va bosqichlar BOSHQA kunlarga tushishi mumkin: TP1 dushanba,
    TP2 payshanba. Agar faqat pozitsiyaning yakuniy natijasi saqlansa,
    "bugungi natija" noto'g'ri chiqardi — payshanbadagi ekranda dushanba
    puli ham ko'rinardi.

    `pnl_records` degan ALOHIDA jadval ATAYLAB yaratilmadi: kunlik/haftalik
    raqamlar shu yozuvlardan HAR SAFAR qayta hisoblanadi
    (`core/portfolio/pnl_calculator.py`). Yig'ilgan raqamni ikkinchi
    joyda saqlash — ikkinchi haqiqat manbai demakdir, va vaqt o'tib
    ikkalasi bir-biridan farq qila boshlaydi.
    """

    __tablename__ = "position_exits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position_id: Mapped[int] = mapped_column(
        ForeignKey("user_positions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: TP bosqichi raqami; Stop bilan yopilganda 0
    bosqich: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Shu qism sotilgan narx
    narx: Mapped[float] = mapped_column(Float, nullable=False)
    #: Pozitsiyaning necha foizi shu bosqichda sotilgani
    ulush_pct: Mapped[float] = mapped_column(Float, nullable=False)
    #: Shu qismga ketgan pul
    miqdor_usd: Mapped[float] = mapped_column(Float, nullable=False)
    #: Foyda (musbat) yoki zarar (manfiy)
    natija_usd: Mapped[float] = mapped_column(Float, nullable=False)
    #: `tp`, `stop`, `stop (TP1 dan keyin)`, `muddat`
    sabab: Mapped[str] = mapped_column(
        String(64), default="", server_default="", nullable=False
    )
    yopilgan_vaqt: Mapped[datetime] = mapped_column(UtcDateTime, index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("position_id", "bosqich", name="pozitsiya_bosqich"),
        Index("ix_position_exits_vaqt", "position_id", "yopilgan_vaqt"),
    )


# --------------------------------------------------------------------------- #
#  Bosh sahifa oqimi (4-prompt, 1-qism)
# --------------------------------------------------------------------------- #


class HomepagePost(Base, TimestampMixin):
    """Bosh sahifadagi bitta post — Telegram kanali uslubida.

    NIMA UCHUN KERAK. Bosh sahifa statik matn edi: bir marta yozilgan,
    yangilanmaydigan, "tugaydigan" sahifa. Endi u XRONOLOGIK OQIM —
    eng yangi post tepada, pastga scroll qilib eskilariga o'tiladi.

    NIMA BU JADVALDA YO'Q. Tanishtiruv, diniy asos va ijtimoiy
    tarmoqlar bu yerga TUSHMAYDI — ular oqimning tepasida, KODDA
    turadi. Sabab: diniy iqtibos joyi olim tasdiqlaguncha placeholder
    bo'lib turishi shart. Uni oddiy postga aylantirsak, admin uni
    tasodifan o'chirib yoki tahrirlab yuborishi mumkin edi va o'sha
    qoida jimgina yo'qolardi.
    """

    __tablename__ = "homepage_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: `text`, `image`, `audio` yoki `mixed` — SAQLASHDA hisoblanadi,
    #: admin tanlamaydi. Aks holda tur bilan tarkib bir-biriga zid
    #: bo'lib qolardi ("audio" deb belgilangan, lekin fayl yo'q).
    content_type: Mapped[str] = mapped_column(String(16), nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text)
    #: FAQAT FAYL NOMI (to'liq yo'l emas) — video bilan bir xil sabab:
    #: Railway diski ko'chganda yo'l o'zgaradi, nom o'zgarmaydi.
    media_url: Mapped[str | None] = mapped_column(String(256))

    #: Post qayerdan kelgan: `qolda` yoki avtomatik (`dars`, `maqola`,
    #: `signal`, `hisobot`).
    source_kind: Mapped[str] = mapped_column(
        String(16), default="qolda", server_default="qolda", nullable=False
    )
    #: Avtomatik post qaysi yozuv haqida. Qo'lda yozilganda `None`.
    source_id: Mapped[int | None] = mapped_column(Integer)
    #: Post ostidagi tugma qayerga olib boradi. Qo'lda yozilganda
    #: `None` — tugma chiqmaydi.
    link: Mapped[str | None] = mapped_column(String(256))
    admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    # BITTA MANBA — BITTA POST.
    #
    # Ansiz admin darsni har tahrirlaganda oqimda yangi post paydo
    # bo'lardi va oqim bir xil xabar bilan to'lib ketardi. Bu shart
    # KODDA emas, BAZADA turadi: kod unutishi mumkin, baza unutmaydi.
    #
    # `source_id` NULL bo'lgan qatorlar (qo'lda yozilganlar) bu
    # shartga tushmaydi — SQLite da NULL hech narsaga teng emas.
    #
    # NEGA `UniqueConstraint` EMAS, INDEKS. SQLite mavjud jadvalga
    # cheklov qo'sha olmaydi — jadvalni nusxalab qayta qurish kerak
    # bo'lardi, postlar esa allaqachon yozilgan. Unique indeks aynan
    # shu kafolatni beradi va ikkala yo'lda ham (yangi baza va
    # migratsiya) bir xil chiqadi.
    __table_args__ = (
        Index("ix_homepage_posts_created", "created_at"),
        Index("uq_post_manba", "source_kind", "source_id", unique=True),
    )


# --------------------------------------------------------------------------- #
#  Zanjir modulining jonli holati (4-prompt, 3-qism)
# --------------------------------------------------------------------------- #


class ZanjirHolati(Base, TimestampMixin):
    """Bitta coin uchun zanjirning ENG OXIRGI tekshiruv natijasi.

    NIMA UCHUN KERAK. Zanjir sikli har necha soatda yuradi va
    natijasini faqat LOGGA yozardi. Ya'ni "hozir qaysi coin qaysi
    blokda to'xtadi" degan savolga javob berish uchun serverdagi
    matn faylni o'qish kerak edi. Admin uchun bu yopiq quti.

    NIMA UCHUN TARIX EMAS, FAQAT OXIRGISI. `symbol` — TAKRORLANMAS:
    har yugurishda o'sha qator yangilanadi. Tarix saqlansa, jadval
    har kuni o'nlab qator bilan o'sardi va u hech qayerda
    ishlatilmasdi. Kerak bo'lsa, tarix uchun alohida qaror qabul
    qilinadi — taxmin qilib qo'shilmaydi.

    MUHIM CHEGARA (4-promptning qat'iy qoidasi): bu jadval FAQAT
    KO'RSATISH uchun. Undan hech narsa modulga QAYTIB kirmaydi va
    signal qaroriga ta'sir qilmaydi. Bir tomonlama oqim:
    modul -> jadval -> ekran.
    """

    __tablename__ = "zanjir_holatlari"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    #: Bloklar JSON ro'yxati: nom, kuch, maxraj, o'tdimi, o'lchanmadimi, to'siq
    bloklar_json: Mapped[str] = mapped_column(Text, nullable=False)
    #: To'rtala blok bog'landimi
    toliq: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    #: Zanjir qaysi blokda uzildi (`None` — uzilmagan)
    uzildi_blokda: Mapped[str | None] = mapped_column(String(64))
    ishonch: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0", nullable=False
    )

    #: `signal`, `zanjir_uzildi`, `ishonch_past`, `daraja_rad`,
    #: `ochiq_signal`, `xato` — yugurishning yakuni
    natija: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Yakunning tafsiloti (masalan qaysi daraja qoidasi rad etdi)
    izoh: Mapped[str] = mapped_column(
        Text, default="", server_default="", nullable=False
    )
    #: Signal chiqqan bo'lsa — uning raqami
    signal_id: Mapped[int | None] = mapped_column(
        ForeignKey("signals.id", ondelete="SET NULL")
    )

    tekshirilgan: Mapped[datetime] = mapped_column(UtcDateTime, index=True, nullable=False)
