"""Bot ishga tushishga tayyorligi — routerlar va handlerlar to'g'ri ulanganmi.

Eslatma: aiogram routerlari modul darajasidagi yagona obyektlar va bitta
Dispatcher'ga faqat BIR MARTA biriktiriladi. Bu — jarayon uchun cheklov
emas (bitta jarayonda bitta bot ishlaydi), lekin testda dispatcher bir
marta quriladi.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from bot.main import build_dispatcher
from bot.settings import BotSettings
from core.config import load_config
from core.domain.enums import SubscriptionTier
from core.domain.models import signal_levels
from core.storage import Database
from core.storage.repositories import PriceRepository

#: Testda ishlatiladigan baza — dispatcher shunga bog'lanadi
TEST_DB = Database("sqlite+aiosqlite:///:memory:")


@pytest.fixture(scope="module")
def dispatcher():
    settings = BotSettings(token="123:abc", admin_ids=frozenset({777}))
    return build_dispatcher(TEST_DB, settings, load_config())


def test_dispatcher_quriladi(dispatcher) -> None:  # noqa: ANN001
    assert dispatcher is not None


def test_admin_routeri_birinchi_turadi(dispatcher) -> None:  # noqa: ANN001
    """`/panel` oddiy foydalanuvchi handlerlariga tushib ketmasligi kerak."""
    nomlar = [r.name for r in dispatcher.sub_routers]
    assert nomlar.index("admin") < nomlar.index("user")


def test_konfiguratsiya_handlerlarga_uzatiladi(dispatcher) -> None:  # noqa: ANN001
    assert dispatcher["config"].project.name == "HALOL CRYPTO SAVDO"


def test_barcha_handlerlar_royxatdan_otgan(dispatcher) -> None:  # noqa: ANN001
    jami = sum(
        len(observer.handlers)
        for router in dispatcher.sub_routers
        for observer in (router.message, router.callback_query)
    )
    assert jami > 20, f"handlerlar soni kutilganidan kam: {jami}"


def test_admin_routeri_ozining_himoyasiga_ega() -> None:
    """Admin router `AdminOnlyMiddleware` bilan o'ralganmi."""
    from bot.handlers import admin as admin_handlers
    from bot.middlewares import AdminOnlyMiddleware

    for observer in (admin_handlers.router.message, admin_handlers.router.callback_query):
        turlar = [type(m) for m in observer.outer_middleware._middlewares]
        turlar += [type(m) for m in observer.middleware._middlewares]
        assert AdminOnlyMiddleware in turlar


# --------------------------------------------------------------------------- #
#  Uchidan uchiga: yangi foydalanuvchi obuna zanjiri
# --------------------------------------------------------------------------- #

YANGI_FOYDALANUVCHI = User(id=999888777, is_bot=False, first_name="Yangi", full_name="Yangi")
SUHBAT = Chat(id=999888777, type="private")


class YozibOluvchiSession(BaseSession):
    """Telegram'ga chiqadigan chaqiruvlarni yozib oladi (tarmoqqa chiqmaydi)."""

    def __init__(self) -> None:
        super().__init__()
        self.chaqiruvlar: list[tuple[str, str, list[str]]] = []

    async def close(self) -> None:
        pass

    async def make_request(self, bot, method, timeout=None):  # noqa: ANN001, ANN201
        nom = type(method).__name__
        matn = getattr(method, "text", None) or ""
        markup = getattr(method, "reply_markup", None)
        tugmalar = (
            [t.text for qator in markup.inline_keyboard for t in qator] if markup else []
        )
        self.chaqiruvlar.append((nom, matn, tugmalar))
        if nom in {"SendMessage", "EditMessageText"}:
            return Message(
                message_id=1, date=datetime.now(UTC), chat=SUHBAT, text=matn or "x"
            )
        return True

    async def stream_content(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        yield b""


def _bosish(data: str, update_id: int) -> Update:
    return Update(
        update_id=update_id,
        callback_query=CallbackQuery(
            id=str(update_id),
            from_user=YANGI_FOYDALANUVCHI,
            chat_instance="ci",
            data=data,
            message=Message(
                message_id=2, date=datetime.now(UTC), chat=SUHBAT, text="menyu"
            ),
        ),
    )


@pytest.fixture
async def sinov_boti():
    """Narxlari to'ldirilgan baza + tarmoqqa chiqmaydigan bot."""
    await TEST_DB.init_models()
    async with TEST_DB.session() as session:
        narxlar = PriceRepository(session)
        for tier in SubscriptionTier:
            for period in ("daily", "monthly"):
                await narxlar.upsert(tier, period, "KGS", 100.0)

    session_obj = YozibOluvchiSession()
    bot = Bot(token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", session=session_obj)
    yield bot, session_obj


async def test_yangi_foydalanuvchi_obuna_zanjiridan_otadi(dispatcher, sinov_boti) -> None:  # noqa: ANN001
    """ENG MUHIM oqim: /start -> Tariflar -> tarif -> muddat -> to'lov.

    Bu zanjirning har bir bo'g'ini alohida sinalgan, lekin ULARNI BIRGA
    o'tkazish boshqa gap: middleware yangi foydalanuvchini yaratishi,
    i18n kalitlari to'liq bo'lishi va narx bazadan topilishi kerak.
    Bir bo'g'in uzilsa, foydalanuvchi uchun tugma "ishlamaydi" — hech
    qanday xato ko'rinmaydi.
    """
    bot, yozuv = sinov_boti

    async def yubor(update: Update) -> list[tuple[str, str, list[str]]]:
        yozuv.chaqiruvlar.clear()
        await dispatcher.feed_update(bot, update)
        return list(yozuv.chaqiruvlar)

    # 1) /start — yangi foydalanuvchi bazada yo'q
    javob = await yubor(
        Update(
            update_id=1,
            message=Message(
                message_id=1,
                date=datetime.now(UTC),
                chat=SUHBAT,
                from_user=YANGI_FOYDALANUVCHI,
                text="/start",
            ),
        )
    )
    assert javob, "/start javobsiz qoldi"
    assert any("Tariflar" in t for _, _, tugmalar in javob for t in tugmalar)

    # 2) Tariflar
    javob = await yubor(_bosish("menu:tariflar", 2))
    tugmalar = [t for _, _, tt in javob for t in tt]
    assert any("Lite" in t for t in tugmalar), tugmalar

    # 3) Tarif tanlash -> muddat menyusi (aynan shu joyda yiqilgandi)
    javob = await yubor(_bosish("tier:lite", 3))
    tugmalar = [t for _, _, tt in javob for t in tt]
    assert any("kunlik" in t for t in tugmalar), tugmalar
    assert any("oylik" in t for t in tugmalar), tugmalar

    # 4) Muddat tanlash -> narx va to'lov ko'rsatmasi
    javob = await yubor(_bosish("period:lite:daily", 4))
    matnlar = " ".join(matn for _, matn, _ in javob)
    assert "100" in matnlar and "KGS" in matnlar, matnlar


async def test_admin_bolmagan_panelga_kira_olmaydi(dispatcher, sinov_boti) -> None:  # noqa: ANN001
    """1.1-band: `/panel` begonaga JIMGINA javob bermaydi."""
    bot, yozuv = sinov_boti
    yozuv.chaqiruvlar.clear()

    await dispatcher.feed_update(
        bot,
        Update(
            update_id=99,
            message=Message(
                message_id=9,
                date=datetime.now(UTC),
                chat=SUHBAT,
                from_user=YANGI_FOYDALANUVCHI,
                text="/panel",
            ),
        ),
    )

    assert yozuv.chaqiruvlar == [], "begonaga javob berilmasligi kerak"


# --------------------------------------------------------------------------- #
#  Uchidan uchiga: admin yuborilgan signalni bekor qiladi
# --------------------------------------------------------------------------- #

ADMIN = User(id=777, is_bot=False, first_name="Admin", full_name="Admin")
ADMIN_SUHBAT = Chat(id=777, type="private")


def _admin_bosish(data: str, update_id: int) -> Update:
    return Update(
        update_id=update_id,
        callback_query=CallbackQuery(
            id=str(update_id),
            from_user=ADMIN,
            chat_instance="ci",
            data=data,
            message=Message(
                message_id=2, date=datetime.now(UTC), chat=ADMIN_SUHBAT, text="panel"
            ),
        ),
    )


async def test_admin_yuborilgan_signalni_bekor_qiladi(dispatcher, sinov_boti) -> None:  # noqa: ANN001
    """Signal yuborilgach uni to'xtatishning yo'li bo'lishi kerak.

    Zanjir: panel -> Ochiq signallar -> signalni tanlash -> tasdiqlash.
    Har bir bo'g'in alohida sinalgan, lekin callback_data nomlari bir-biriga
    mos kelmasa tugma jimgina "ishlamaydi" — bu test aynan shuni tutadi.
    """
    from core.domain.enums import SignalSource
    from core.storage.repositories import SignalRepository

    bot, yozuv = sinov_boti

    async with TEST_DB.session() as session:
        yozuv_signal = await SignalRepository(session).create(
            symbol="BTC",
            levels=signal_levels(entry=100.0, stop=97.0, tp1=104.0, tp2=110.0),
            source=SignalSource.MANUAL,
        )
        signal_id = yozuv_signal.id

    async def yubor(update: Update) -> list[tuple[str, str, list[str]]]:
        yozuv.chaqiruvlar.clear()
        await dispatcher.feed_update(bot, update)
        return list(yozuv.chaqiruvlar)

    # 1) Ochiq signallar ro'yxati
    javob = await yubor(_admin_bosish("admin:faol_signallar", 201))
    tugmalar = [t for _, _, tt in javob for t in tt]
    assert any(f"#{signal_id} BTC" in t for t in tugmalar), tugmalar

    # 2) Signalni tanlash -> tasdiq so'raladi
    javob = await yubor(_admin_bosish(f"sigadm:pick:{signal_id}", 202))
    matnlar = " ".join(matn for _, matn, _ in javob)
    assert "bekor qilinsinmi" in matnlar.lower(), matnlar

    # 3) Tasdiqlash -> baza yopiladi
    javob = await yubor(_admin_bosish(f"sigadm:cancel:{signal_id}", 203))
    matnlar = " ".join(matn for _, matn, _ in javob)
    assert "bekor qilindi" in matnlar.lower(), matnlar

    async with TEST_DB.session() as session:
        yangilangan = await SignalRepository(session).get(signal_id)
        assert yangilangan.status == "cancelled"

    # 4) Ro'yxat endi bo'sh — bekor qilingan signal qaytib chiqmaydi
    javob = await yubor(_admin_bosish("admin:faol_signallar", 204))
    matnlar = " ".join(matn for _, matn, _ in javob)
    assert "ochiq signal yo'q" in matnlar.lower(), matnlar


# --------------------------------------------------------------------------- #
#  Uchidan uchiga: foydalanuvchi signallar ro'yxati
# --------------------------------------------------------------------------- #


async def test_signallar_royxati_kech_qolganlarni_ochmaydi(dispatcher, sinov_boti) -> None:  # noqa: ANN001
    """Foydalanuvchiga faqat qo'shilish mumkin bo'lgan signal ochiladi.

    TP1 olingan signal ro'yxatda KO'RINADI (foydalanuvchi bilishi kerak),
    lekin narxlari ochilmaydi: narx allaqachon oldinga ketgan, Stop esa
    o'sha joyda — kech kirish xavfni kamaytirmasdan foydani qisqartiradi.
    """
    from core.domain.enums import SignalSource, SignalStatus, SubscriptionTier
    from core.storage.repositories import (
        SignalRepository,
        SubscriptionRepository,
        UserRepository,
    )

    bot, yozuv = sinov_boti

    async with TEST_DB.session() as session:
        user = await UserRepository(session).get_or_create(YANGI_FOYDALANUVCHI.id)
        await SubscriptionRepository(session).create(
            user.id, SubscriptionTier.PREMIUM, period_days=30, is_trial=False
        )
        repo = SignalRepository(session)
        ochiq = await repo.create(
            symbol="AAA",
            levels=signal_levels(entry=100.0, stop=97.0, tp1=104.0, tp2=110.0),
            source=SignalSource.MANUAL,
        )
        kechikkan = await repo.create(
            symbol="BBB",
            levels=signal_levels(entry=50.0, stop=48.0, tp1=53.0, tp2=56.0),
            source=SignalSource.MANUAL,
        )
        await repo.apply_event(
            kechikkan.id, SignalStatus.TP1_HIT, 53.0, datetime.now(UTC), "tp1_hit"
        )
        ochiq_id, kech_id = ochiq.id, kechikkan.id

    async def yubor(update: Update) -> list[tuple[str, str, list[str]]]:
        yozuv.chaqiruvlar.clear()
        await dispatcher.feed_update(bot, update)
        return list(yozuv.chaqiruvlar)

    # 1) Ro'yxat — bitta ekran, ikkala signal ham tugma sifatida
    javob = await yubor(_bosish("menu:signallar", 301))
    xabarlar = [nom for nom, _, _ in javob if nom in {"SendMessage", "EditMessageText"}]
    assert xabarlar == ["EditMessageText"], f"ro'yxat bitta ekran bo'lishi kerak: {javob}"
    tugmalar = [t for _, _, tt in javob for t in tt]
    assert any("AAA" in t and "faol" not in t for t in tugmalar), tugmalar
    assert any("BBB" in t and "TP1" in t for t in tugmalar), tugmalar

    # 2) Kirish mumkin bo'lgani ochiladi — narxlar ko'rinadi
    javob = await yubor(_bosish(f"sig:open:{ochiq_id}", 302))
    matnlar = " ".join(matn for _, matn, _ in javob)
    assert "100" in matnlar and "97" in matnlar, matnlar

    # 3) Kech qolgani ochilmaydi — faqat ogohlantirish, kartochka yo'q
    javob = await yubor(_bosish(f"sig:open:{kech_id}", 303))
    matnlar = " ".join(matn for _, matn, _ in javob)
    assert "53" not in matnlar, f"kech qolgan signalning narxi ko'rinmasligi kerak: {matnlar}"

    javob = await yubor(_bosish(f"sig:late:{kech_id}", 304))
    assert [nom for nom, _, _ in javob] == ["AnswerCallbackQuery"], javob


async def test_signallar_obunasiz_korinmaydi(dispatcher, sinov_boti) -> None:  # noqa: ANN001
    """1.3-band: signal — pullik kontent, ro'yxat ham ochilmaydi."""
    bot, yozuv = sinov_boti
    begona = User(id=444333222, is_bot=False, first_name="Begona", full_name="Begona")

    yozuv.chaqiruvlar.clear()
    await dispatcher.feed_update(
        bot,
        Update(
            update_id=310,
            callback_query=CallbackQuery(
                id="310",
                from_user=begona,
                chat_instance="ci",
                data="menu:signallar",
                message=Message(
                    message_id=2, date=datetime.now(UTC), chat=SUHBAT, text="menyu"
                ),
            ),
        ),
    )

    nomlar = [nom for nom, _, _ in yozuv.chaqiruvlar]
    assert nomlar == ["AnswerCallbackQuery"], "obunasizga kartochka ko'rsatilmaydi"
