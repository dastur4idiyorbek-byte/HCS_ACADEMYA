"""Ma'lumotlarga kirish qatlami va obuna hayot-sikli (1.2 / 1.3 / 1.4-band)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.config.schema import SubscriptionsConfig
from core.domain.enums import (
    HalalStatus,
    PaymentStatus,
    SubscriptionPeriod,
    SubscriptionStatus,
    SubscriptionTier,
)
from core.services import SubscriptionService
from core.storage import Database
from core.storage.repositories import (
    CoinRulingRepository,
    ContentRepository,
    PaymentRepository,
    PriceRepository,
    SubscriptionRepository,
    UserRepository,
    ViolationRepository,
)

HOZIR = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


# --------------------------------------------------------------------------- #
#  Foydalanuvchilar
# --------------------------------------------------------------------------- #


async def test_foydalanuvchi_yaratiladi_va_topiladi(db: Database) -> None:
    async with db.session() as session:
        repo = UserRepository(session)
        user = await repo.get_or_create(111, username="diyor", full_name="Diyorbek")
        assert user.role == "user"
        assert user.language == "uz"

    async with db.session() as session:
        yana = await UserRepository(session).get_or_create(111)
        assert yana.username == "diyor", "mavjud ma'lumot o'chib ketmasligi kerak"


async def test_admin_roli_env_dan_qayta_qollaniladi(db: Database) -> None:
    """Admin ro'yxatidan olib tashlangan odam bazada admin bo'lib qolmasligi kerak."""
    async with db.session() as session:
        await UserRepository(session).get_or_create(222, is_admin=True)

    async with db.session() as session:
        user = await UserRepository(session).get_or_create(222, is_admin=False)
        assert user.role == "user"


async def test_balans_saqlanadi(db: Database) -> None:
    async with db.session() as session:
        repo = UserRepository(session)
        user = await repo.get_or_create(333)
        await repo.set_balance(user, 1500.0)
        assert user.declared_balance_usd == 1500.0
        assert user.balance_updated_at is not None


async def test_manfiy_balans_rad_etiladi(db: Database) -> None:
    async with db.session() as session:
        repo = UserRepository(session)
        user = await repo.get_or_create(444)
        with pytest.raises(ValueError, match="manfiy"):
            await repo.set_balance(user, -10)


# --------------------------------------------------------------------------- #
#  Obuna va to'lov (1.2-band)
# --------------------------------------------------------------------------- #


async def test_tolov_tasdiqlanguncha_obuna_yoq(db: Database) -> None:
    """To'lov avtomatik EMAS — chek yuborilishi obuna bermaydi."""
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(555)
        xizmat = SubscriptionService(
            SubscriptionsConfig(),
            UserRepository(session),
            SubscriptionRepository(session),
            PaymentRepository(session),
        )
        await xizmat.submit_payment(
            user.id, SubscriptionTier.PRO, SubscriptionPeriod.MONTHLY, 300, "KGS", "file123"
        )
        assert await xizmat.tier_for(user.id) is None


async def test_admin_tasdiqlagach_obuna_faollashadi(db: Database) -> None:
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(666)
        xizmat = SubscriptionService(
            SubscriptionsConfig(),
            UserRepository(session),
            SubscriptionRepository(session),
            PaymentRepository(session),
        )
        tolov = await xizmat.submit_payment(
            user.id, SubscriptionTier.PREMIUM, SubscriptionPeriod.MONTHLY, 500, "KGS", None
        )
        natija = await xizmat.approve_payment(tolov, admin_telegram_id=1, now=HOZIR)

        assert natija.approved
        assert tolov.status == PaymentStatus.APPROVED.value
        assert natija.subscription.expires_at == HOZIR + timedelta(days=30)
        assert await xizmat.tier_for(user.id) is SubscriptionTier.PREMIUM


async def test_kunlik_tarif_sinov_deb_belgilanadi(db: Database) -> None:
    """1.2-band: kunlik tarif = sinov muddati."""
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(777)
        xizmat = SubscriptionService(
            SubscriptionsConfig(),
            UserRepository(session),
            SubscriptionRepository(session),
            PaymentRepository(session),
        )
        tolov = await xizmat.submit_payment(
            user.id, SubscriptionTier.LITE, SubscriptionPeriod.DAILY, 50, "KGS", None
        )
        natija = await xizmat.approve_payment(tolov, admin_telegram_id=1, now=HOZIR)

        assert natija.subscription.is_trial
        assert natija.subscription.expires_at == HOZIR + timedelta(days=1)


async def test_rad_etilgan_tolov_obuna_bermaydi(db: Database) -> None:
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(888)
        xizmat = SubscriptionService(
            SubscriptionsConfig(),
            UserRepository(session),
            SubscriptionRepository(session),
            PaymentRepository(session),
        )
        tolov = await xizmat.submit_payment(
            user.id, SubscriptionTier.PRO, SubscriptionPeriod.MONTHLY, 300, "KGS", None
        )
        natija = await xizmat.reject_payment(tolov, 1, "Chek o'qilmadi", now=HOZIR)

        assert not natija.approved
        assert natija.detail == "Chek o'qilmadi"
        assert await xizmat.tier_for(user.id) is None


async def test_tolov_ikki_marta_korilmaydi(db: Database) -> None:
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(999)
        xizmat = SubscriptionService(
            SubscriptionsConfig(),
            UserRepository(session),
            SubscriptionRepository(session),
            PaymentRepository(session),
        )
        tolov = await xizmat.submit_payment(
            user.id, SubscriptionTier.LITE, SubscriptionPeriod.MONTHLY, 100, "KGS", None
        )
        await xizmat.approve_payment(tolov, 1, now=HOZIR)
        ikkinchi = await xizmat.approve_payment(tolov, 1, now=HOZIR)

        assert not ikkinchi.approved
        assert ikkinchi.message_key == "admin.tolov_allaqachon_korilgan"


async def test_notogri_valyuta_rad_etiladi(db: Database) -> None:
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(1010)
        xizmat = SubscriptionService(
            SubscriptionsConfig(),
            UserRepository(session),
            SubscriptionRepository(session),
            PaymentRepository(session),
        )
        with pytest.raises(ValueError, match="valyuta"):
            await xizmat.submit_payment(
                user.id, SubscriptionTier.LITE, SubscriptionPeriod.MONTHLY, 100, "EUR", None
            )


async def test_muddati_tugagan_obuna_avtomatik_yopiladi(db: Database) -> None:
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(1111)
        obunalar = SubscriptionRepository(session)
        await obunalar.create(user.id, SubscriptionTier.LITE, period_days=1, is_trial=True, now=HOZIR)

        keyin = HOZIR + timedelta(days=2)
        assert await obunalar.expire_overdue(keyin) == 1
        assert await obunalar.tier_for(user.id, keyin) is None


async def test_eng_yuqori_tarif_qaytariladi(db: Database) -> None:
    """Bir nechta faol obuna bo'lsa, foydalanuvchi eng kattasini ko'rishi kerak."""
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(1212)
        obunalar = SubscriptionRepository(session)
        await obunalar.create(user.id, SubscriptionTier.LITE, 30, False, now=HOZIR)
        await obunalar.create(user.id, SubscriptionTier.PREMIUM, 30, False, now=HOZIR)

        assert await obunalar.tier_for(user.id, HOZIR) is SubscriptionTier.PREMIUM


async def test_oylik_obuna_uchun_eslatma(db: Database) -> None:
    """1.2-band: tugashiga 1-2 kun qolganda eslatma."""
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(1313)
        xizmat = SubscriptionService(
            SubscriptionsConfig(),
            UserRepository(session),
            SubscriptionRepository(session),
            PaymentRepository(session),
        )
        obunalar = SubscriptionRepository(session)
        await obunalar.create(user.id, SubscriptionTier.PRO, 30, False, now=HOZIR)

        ikki_kun_qolganda = HOZIR + timedelta(days=28)
        eslatmalar = await xizmat.due_reminders(ikki_kun_qolganda)
        assert len(eslatmalar) == 1
        obuna, qolgan = eslatmalar[0]
        assert qolgan == 2

        xizmat.mark_reminder_sent(obuna, qolgan)
        assert await xizmat.due_reminders(ikki_kun_qolganda) == [], "takror yuborilmasligi kerak"


async def test_sinov_tarifiga_eslatma_yuborilmaydi(db: Database) -> None:
    """1 kun juda qisqa — alohida eslatma mantiqiy emas (spetsifikatsiya)."""
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(1414)
        xizmat = SubscriptionService(
            SubscriptionsConfig(),
            UserRepository(session),
            SubscriptionRepository(session),
            PaymentRepository(session),
        )
        await SubscriptionRepository(session).create(
            user.id, SubscriptionTier.LITE, 1, is_trial=True, now=HOZIR
        )
        assert await xizmat.due_reminders(HOZIR) == []


# --------------------------------------------------------------------------- #
#  1.3 — Qoidabuzarlik
# --------------------------------------------------------------------------- #


async def test_qoidabuzarlik_tarifni_toxtatadi(db: Database) -> None:
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(1515)
        obunalar = SubscriptionRepository(session)
        obuna = await obunalar.create(user.id, SubscriptionTier.PREMIUM, 30, False, now=HOZIR)

        await ViolationRepository(session).record(user.id, "Kontent tarqatildi", reported_by=1)
        await obunalar.suspend(obuna, "Qoidabuzarlik")

        assert obuna.status == SubscriptionStatus.SUSPENDED.value
        assert await obunalar.tier_for(user.id, HOZIR) is None, "to'xtatilgan obuna kirish bermaydi"

        await obunalar.restore(obuna)
        assert await obunalar.tier_for(user.id, HOZIR) is SubscriptionTier.PREMIUM


# --------------------------------------------------------------------------- #
#  1.5 — Narx va kontent
# --------------------------------------------------------------------------- #


async def test_narx_belgilanadi_va_yangilanadi(db: Database) -> None:
    async with db.session() as session:
        narxlar = PriceRepository(session)
        await narxlar.upsert(SubscriptionTier.PRO, "monthly", "KGS", 3000, "Optima 1234")
        await narxlar.upsert(SubscriptionTier.PRO, "monthly", "KGS", 3500)

        narx = await narxlar.get(SubscriptionTier.PRO, "monthly", "KGS")
        assert narx.amount == 3500
        assert narx.payment_details == "Optima 1234", "rekvizit o'chib ketmasligi kerak"


async def test_manfiy_narx_rad_etiladi(db: Database) -> None:
    async with db.session() as session:
        with pytest.raises(ValueError, match="musbat"):
            await PriceRepository(session).upsert(SubscriptionTier.LITE, "daily", "KGS", -5)


async def test_kontent_tarif_boyicha_filtrlanadi(db: Database) -> None:
    """1.3-band: pullik kontent past tarifga ko'rinmasligi kerak."""
    async with db.session() as session:
        kontent = ContentRepository(session)
        await kontent.add("video", "Kirish darsi", "f1", SubscriptionTier.PRO)
        await kontent.add("strategy", "Maxfiy strategiya", "f2", SubscriptionTier.PREMIUM)

        assert await kontent.available_for(None) == []
        assert [c.title for c in await kontent.available_for(SubscriptionTier.LITE)] == []
        assert [c.title for c in await kontent.available_for(SubscriptionTier.PRO)] == ["Kirish darsi"]
        assert len(await kontent.available_for(SubscriptionTier.PREMIUM)) == 2


# --------------------------------------------------------------------------- #
#  1.4 — Halol ro'yxat
# --------------------------------------------------------------------------- #


async def test_admin_coin_qarorini_belgilaydi(db: Database) -> None:
    async with db.session() as session:
        qarorlar = CoinRulingRepository(session)
        await qarorlar.set_ruling("xyz", HalalStatus.HARAM, "Foizli qarz protokoli", set_by=1)

        hammasi = await qarorlar.all_verdicts()
        assert hammasi["XYZ"].status is HalalStatus.HARAM
        assert not hammasi["XYZ"].is_tradable


async def test_coin_qarori_yangilanadi_va_ochiriladi(db: Database) -> None:
    async with db.session() as session:
        qarorlar = CoinRulingRepository(session)
        await qarorlar.set_ruling("ABC", HalalStatus.MASHBOOH, "shubhali")
        await qarorlar.set_ruling("ABC", HalalStatus.HALAL, "qayta ko'rib chiqildi")

        assert (await qarorlar.all_verdicts())["ABC"].status is HalalStatus.HALAL
        assert await qarorlar.remove("ABC")
        assert await qarorlar.all_verdicts() == {}
        assert not await qarorlar.remove("YOQ")
