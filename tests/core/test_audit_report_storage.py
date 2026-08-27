"""3.8-band: haftalik hisobotning qaydi.

Nima uchun bu qayd kerak: hisobot faqat Telegramga yuborilardi. Admin uni
o'qimay qolsa yoki chat tozalansa, "o'tgan oy tizim qanday ishlagan" degan
savolga javob bermasdi — hisobot butunlay yo'qolardi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.postmortem.report import PeriodStats, SelfAuditReport
from core.storage import Database
from core.storage.repositories import AuditReportRepository

HOZIR = datetime(2026, 8, 27, 6, 0, tzinfo=UTC)


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


def hisobot(
    hozir: datetime = HOZIR,
    *,
    total: int = 12,
    stop: int = 4,
    cancelled: int = 2,
    ogohlantirish: str | None = None,
    naqshlar: list | None = None,
) -> SelfAuditReport:
    return SelfAuditReport(
        generated_at=hozir,
        period_days=30,
        stats=PeriodStats(
            total=total,
            tp2=5,
            tp1_then_stop=1,
            stop=stop,
            cancelled=cancelled,
            false_signals=1,
            average_score=57.3,
            average_holding_hours=18.4,
        ),
        patterns=naqshlar or [],
        sample_warning=ogohlantirish,
    )


async def test_hisobot_saqlanadi(db: Database) -> None:
    async with db.session() as session:
        await AuditReportRepository(session).save(hisobot(), "matn")

    async with db.session() as session:
        qaydlar = await AuditReportRepository(session).latest()

    assert len(qaydlar) == 1
    qayd = qaydlar[0]
    assert qayd.total == 12
    assert qayd.stop == 4
    assert qayd.cancelled == 2
    # `traded` — hisoblanadigan qiymat: jami minus bekor qilinganlar
    assert qayd.traded == 10
    assert qayd.average_score == pytest.approx(57.3)
    assert qayd.rendered == "matn"
    assert qayd.period_days == 30


async def test_bir_kunda_bitta_qayd(db: Database) -> None:
    """Admin tugmani necha marta bossa ham jadval to'lib ketmasligi kerak."""
    async with db.session() as session:
        repo = AuditReportRepository(session)
        await repo.save(hisobot(), "birinchi")
        await repo.save(hisobot(HOZIR + timedelta(hours=5), total=20), "ikkinchi")

    async with db.session() as session:
        qaydlar = await AuditReportRepository(session).latest()

    assert len(qaydlar) == 1, "bir kunda bitta qator bo'lishi kerak"
    # Eng so'nggi holat saqlanadi — veb-panel eskisini ko'rsatmasligi kerak
    assert qaydlar[0].rendered == "ikkinchi"
    assert qaydlar[0].total == 20


async def test_boshqa_kun_alohida_qayd(db: Database) -> None:
    async with db.session() as session:
        repo = AuditReportRepository(session)
        await repo.save(hisobot(HOZIR - timedelta(days=7)), "o'tgan hafta")
        await repo.save(hisobot(HOZIR), "bu hafta")

    async with db.session() as session:
        qaydlar = await AuditReportRepository(session).latest()

    assert len(qaydlar) == 2
    # Eng yangisi birinchi — veb-panel ro'yxatni shu tartibda ko'rsatadi
    assert qaydlar[0].rendered == "bu hafta"


async def test_turli_davr_uzunligi_aralashmaydi(db: Database) -> None:
    """30 kunlik va 7 kunlik hisobot bir xil kunda bo'lsa ham alohida."""
    yetti = hisobot()
    object.__setattr__(yetti, "period_days", 7)

    async with db.session() as session:
        repo = AuditReportRepository(session)
        await repo.save(hisobot(), "30 kun")
        await repo.save(yetti, "7 kun")

    async with db.session() as session:
        qaydlar = await AuditReportRepository(session).latest()

    assert {q.period_days for q in qaydlar} == {7, 30}


async def test_namuna_kichik_ogohlantirishi_saqlanadi(db: Database) -> None:
    """\"Naqsh topilmadi\" bilan \"ma'lumot yetarli emas\" bir xil emas.

    Veb-panel bu farqni ko'rsatishi kerak, aks holda admin kam
    ma'lumotni \"hammasi joyida\" deb o'qib qo'yadi.
    """
    matn = "Namuna kichik (3 ta savdo, kamida 10 kerak)"
    async with db.session() as session:
        await AuditReportRepository(session).save(hisobot(ogohlantirish=matn), "m")

    async with db.session() as session:
        qayd = (await AuditReportRepository(session).latest())[0]

    assert qayd.sample_warning == matn
    assert qayd.pattern_count == 0
