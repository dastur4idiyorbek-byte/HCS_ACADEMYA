"""Modul 4.0.0 — ishchi sikli: qachon nima yuradi."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from core.config.schema import AppConfig
from core.portlash_radari.ishchi import RadarIshchisi
from core.portlash_radari.manba import Juftlik
from core.storage import Database
from core.storage.models import RadarHolati, RadarSessiya


class Soat:
    def __init__(self, t: datetime) -> None:
        self.t = t

    def __call__(self) -> datetime:
        return self.t


class SoxtaBinance:
    def __init__(self) -> None:
        self.juft = [Juftlik("LSKUSDT", "LSK", "LSK", 1, None)]
        self.ortacha_sorovlari = 0

    async def juftliklar(self, jurnal):  # noqa: ANN001, ANN201
        jurnal.yoz("juftliklar", 200 if self.juft else 451)
        return self.juft

    async def kunlik_ortacha(self, symbol, hozir, kun=30):  # noqa: ANN001, ANN201
        self.ortacha_sorovlari += 1
        return (1e6, 30)

    async def shamlar(self, *a, **k):  # noqa: ANN002, ANN003, ANN201
        return []

    async def yop(self) -> None:
        pass


class SoxtaSessiya:
    def __init__(self) -> None:
        self.yurganlar: list[tuple[str, datetime]] = []

    async def yur(self, turi: str, sham: datetime) -> None:
        self.yurganlar.append((turi, sham))


class Bosh:
    async def yop(self) -> None:
        pass

    async def jadval(self) -> dict:
        return {}


@pytest.fixture
async def db(tmp_path):  # noqa: ANN001, ANN201
    baza = Database(f"sqlite+aiosqlite:///{tmp_path / 'i.db'}")
    await baza.init_models()
    yield baza
    await baza.dispose()


def ishchi(config: AppConfig, db: Database, soat: Soat) -> tuple[RadarIshchisi, SoxtaSessiya]:
    b = SoxtaBinance()
    x = RadarIshchisi(config, db, binance=b, coingecko=Bosh(), unlock=Bosh(), soat=soat)  # type: ignore[arg-type]
    sessiya = SoxtaSessiya()
    x._sessiya = sessiya  # type: ignore[assignment]
    return x, sessiya


async def _sessiya_yoz(db: Database, turi: str, sham: datetime) -> None:
    async with db.session() as s:
        s.add(RadarSessiya(turi=turi, sham_vaqti=sham, kun="2026-10-14", tartib=1,
                           boshlandi=sham, holat="tugadi"))


async def test_birinchi_qadam_keshni_quradi_va_sessiyani_yurgizadi(
    config: AppConfig, db: Database
) -> None:
    soat = Soat(datetime(2026, 10, 14, 7, 46, tzinfo=UTC))
    x, sessiya = ishchi(config, db, soat)
    bajarildi = await x.qadam()
    assert bajarildi[0] == "hajm"
    assert "tasdiq" in bajarildi
    assert sessiya.yurganlar == [("tasdiq", datetime(2026, 10, 14, 8, tzinfo=UTC))]
    async with db.session() as s:
        holat = await s.get(RadarHolati, 1)
    assert holat.ishchi_tirik == soat.t
    assert holat.hajm_yangilandi == soat.t


async def test_yurgan_sessiya_qayta_yurmaydi(config: AppConfig, db: Database) -> None:
    soat = Soat(datetime(2026, 10, 14, 7, 46, tzinfo=UTC))
    x, sessiya = ishchi(config, db, soat)
    await _sessiya_yoz(db, "tasdiq", datetime(2026, 10, 14, 8, tzinfo=UTC))
    await x.qadam()
    assert sessiya.yurganlar == []


async def test_qolda_sorov_bir_marta_bajariladi(config: AppConfig, db: Database) -> None:
    soat = Soat(datetime(2026, 10, 14, 9, 10, tzinfo=UTC))
    x, sessiya = ishchi(config, db, soat)
    async with db.session() as s:
        s.add(RadarHolati(id=1, sorov=True))
    await x.qadam()
    await x.qadam()
    assert sessiya.yurganlar == [("qolda", datetime(2026, 10, 14, 12, tzinfo=UTC))]
    async with db.session() as s:
        assert (await s.get(RadarHolati, 1)).sorov is False


async def test_kunlik_hajm_00_05_da_bir_marta(config: AppConfig, db: Database) -> None:
    soat = Soat(datetime(2026, 10, 14, 0, 4, tzinfo=UTC))
    x, _ = ishchi(config, db, soat)
    async with db.session() as s:
        s.add(RadarHolati(id=1, hajm_yangilandi=datetime(2026, 10, 13, 0, 6, tzinfo=UTC)))
    assert "hajm" not in await x.qadam()
    soat.t = datetime(2026, 10, 14, 0, 6, tzinfo=UTC)
    assert "hajm" in await x.qadam()
    soat.t = datetime(2026, 10, 14, 0, 30, tzinfo=UTC)
    assert "hajm" not in await x.qadam()


async def test_binance_javob_bermasa_hajm_har_daqiqada_sorlanmaydi(
    config: AppConfig, db: Database
) -> None:
    soat = Soat(datetime(2026, 10, 14, 9, 0, tzinfo=UTC))
    x, _ = ishchi(config, db, soat)
    x._b.juft = []  # type: ignore[attr-defined]
    assert "hajm" in await x.qadam()
    soat.t += timedelta(minutes=1)
    assert "hajm" not in await x.qadam()
    soat.t += timedelta(minutes=15)
    assert "hajm" in await x.qadam()
    async with db.session() as s:
        holat = await s.get(RadarHolati, 1)
    assert "451" in holat.oxirgi_xato


async def test_baholash_soatiga_bir_marta(config: AppConfig, db: Database) -> None:
    soat = Soat(datetime(2026, 10, 14, 9, 0, tzinfo=UTC))
    x, _ = ishchi(config, db, soat)
    assert "baholash" in await x.qadam()
    soat.t += timedelta(minutes=30)
    assert "baholash" not in await x.qadam()
    soat.t += timedelta(minutes=31)
    assert "baholash" in await x.qadam()


async def test_uyqu_keyingi_sessiyaga_moslashadi(config: AppConfig, db: Database) -> None:
    soat = Soat(datetime(2026, 10, 14, 7, 44, 50, tzinfo=UTC))
    x, _ = ishchi(config, db, soat)
    assert x.uyqu() == timedelta(seconds=10)
    soat.t = datetime(2026, 10, 14, 5, 0, tzinfo=UTC)
    assert x.uyqu() == timedelta(seconds=60)


async def test_yarim_qolgan_sessiya_yopiladi(config: AppConfig, db: Database) -> None:
    from core.portlash_radari.repository import RadarRepository

    t = datetime(2026, 10, 14, 7, 45, tzinfo=UTC)
    async with db.session() as s:
        s.add(RadarSessiya(turi="tasdiq", sham_vaqti=t, kun="2026-10-14", tartib=3,
                           boshlandi=t, holat="yurmoqda"))
    async with db.session() as s:
        assert await RadarRepository(s).yurmoqda_qolganlarni_yop(t) == 1
    async with db.session() as s:
        holat = (await s.execute(select(RadarSessiya.holat))).scalar_one()
    assert holat == "xato"


def test_o_chiq_radar_ishga_tushmaydi(config: AppConfig) -> None:
    import dataclasses

    o_chiq = dataclasses.replace(config, radar=dataclasses.replace(config.radar, yoqilgan=False))
    x = RadarIshchisi(o_chiq, Database("sqlite+aiosqlite:///:memory:"))
    x.start()
    assert x._vazifa is None
