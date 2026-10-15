"""Modul 4.0.0 — calibration: 24 soat va 7 kundan keyingi natija."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.portlash_radari.baholash import RadarBaholash, natijani_hisobla
from core.portlash_radari.manba import Sham
from core.storage import Database
from core.storage.models import RadarNatija, RadarSessiya

BOSHI = datetime(2026, 10, 1, 7, 45, tzinfo=UTC)


def sham(soat: int, yuqori: float, past: float, yopilish: float) -> Sham:
    return Sham(BOSHI + timedelta(minutes=15, hours=soat), yuqori, past, yopilish)


def test_natija_foizda() -> None:
    shamlar = [sham(0, 1.1, 0.9, 1.0), sham(1, 1.8, 1.0, 1.5), sham(2, 1.6, 1.2, 1.2)]
    assert natijani_hisobla(1.0, shamlar, BOSHI) == (20.0, 80.0, -10.0)
    assert natijani_hisobla(1.0, [], BOSHI) is None
    # sessiyadan oldingi sham hisobga kirmaydi
    oldin = Sham(BOSHI - timedelta(hours=1), 99.0, 0.01, 1.0)
    assert natijani_hisobla(1.0, [oldin, *shamlar], BOSHI) == (20.0, 80.0, -10.0)


class SoxtaBinance:
    def __init__(self, javob: list[Sham] | None) -> None:
        self.javob = javob
        self.sorovlar: list[tuple] = []

    async def shamlar(self, symbol, interval, boshi=None, limit=30, jurnal=None):  # noqa: ANN001, ANN201
        self.sorovlar.append((symbol, interval, limit))
        return self.javob


@pytest.fixture
async def db(tmp_path):  # noqa: ANN001, ANN201
    baza = Database(f"sqlite+aiosqlite:///{tmp_path / 'b.db'}")
    await baza.init_models()
    async with baza.session() as s:
        for i, turi in enumerate(("tasdiq", "kashfiyot", "qolda")):
            sess = RadarSessiya(
                turi=turi, sham_vaqti=BOSHI + timedelta(minutes=15), kun="2026-10-01",
                tartib=3, boshlandi=BOSHI, holat="tugadi",
            )
            s.add(sess)
            await s.flush()
            for nom, nturi in (("LSKUSDT", "elak"), ("QUSDT", "namuna"), ("OUTUSDT", "chiqdi")):
                s.add(RadarNatija(
                    sessiya_id=sess.id, symbol=f"{nom}{i}" if i else nom, belgi="X",
                    turi=nturi, narx=1.0,
                ))
    yield baza
    await baza.dispose()


async def test_faqat_rasmiy_elak_va_namuna_baholanadi(db: Database) -> None:
    b = SoxtaBinance([sham(0, 1.5, 0.9, 1.2)])
    hozir = BOSHI + timedelta(days=8)
    yozildi = await RadarBaholash(db, b, lambda: hozir).yur()  # type: ignore[arg-type]
    # tasdiq sessiyasidagi elak + namuna, 24s va 7k = 4
    assert yozildi == 4
    assert {s for s, _, _ in b.sorovlar} == {"LSKUSDT", "QUSDT"}
    async with db.session() as s:
        lsk = (await s.execute(
            RadarNatija.__table__.select().where(RadarNatija.symbol == "LSKUSDT")
        )).first()
    assert (lsk.kel_24s_max, lsk.kel_24s_min, lsk.kel_24s_oxiri) == (50.0, -10.0, 20.0)
    assert lsk.kel_7k_vaqt is not None
    # ikkinchi marta — hech narsa qolmagan
    assert await RadarBaholash(db, b, lambda: hozir).yur() == 0  # type: ignore[arg-type]


async def test_vaqti_kelmagan_baholanmaydi(db: Database) -> None:
    b = SoxtaBinance([sham(0, 1.5, 0.9, 1.2)])
    hozir = BOSHI + timedelta(hours=23)
    assert await RadarBaholash(db, b, lambda: hozir).yur() == 0  # type: ignore[arg-type]
    assert b.sorovlar == []


async def test_sham_kelmasa_kutadi_keyin_voz_kechadi(db: Database) -> None:
    """Delisting: so'rov o'tdi, lekin sham yo'q (bo'sh ro'yxat)."""
    b = SoxtaBinance([])
    hozir = BOSHI + timedelta(days=2)
    assert await RadarBaholash(db, b, lambda: hozir).yur() == 0  # type: ignore[arg-type]
    hozir = BOSHI + timedelta(days=4)
    # 24s davri voz kechadi (bo'sh qiymat bilan yopiladi), 7k hali kutadi
    assert await RadarBaholash(db, b, lambda: hozir).yur() == 2  # type: ignore[arg-type]


async def test_sorov_yiqilsa_hech_qachon_voz_kechilmaydi(db: Database) -> None:
    """Tarmoq/429/451 — "sham yo'q" emas. Bir necha kunlik uzilishdan keyin
    ham yozuv bo'sh yopilmaydi: Binance tiklangach baholanadi."""
    b = SoxtaBinance(None)
    hozir = BOSHI + timedelta(days=20)
    assert await RadarBaholash(db, b, lambda: hozir).yur() == 0  # type: ignore[arg-type]
    b.javob = [sham(0, 1.5, 0.9, 1.2)]
    assert await RadarBaholash(db, b, lambda: hozir).yur() == 4  # type: ignore[arg-type]
