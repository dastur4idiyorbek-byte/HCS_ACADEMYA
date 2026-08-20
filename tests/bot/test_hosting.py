"""Joylashtirish muhiti — Railway kabi vaqtinchalik diskli platformalar.

Eng muhim test: doimiy disk ulanmasa OGOHLANTIRISH berilishi kerak.
Aks holda baza har yangilanishda jimgina o'chadi va buni faqat mijoz
"men to'lagandim" deganda bilib qolasiz.
"""

from __future__ import annotations

import logging
import os

from bot.hosting import (
    RAILWAY_ENV,
    RAILWAY_VOLUME,
    apply_platform_defaults,
    database_url_for_platform,
    is_ephemeral_platform,
    volume_path,
    warn_if_data_is_temporary,
)

SQLITE = "sqlite+aiosqlite:///data/hcs.db"


def test_oddiy_serverda_ogohlantirish_yoq(monkeypatch) -> None:  # noqa: ANN001
    """O'z serveringizda disk doimiy — ogohlantirish o'rinsiz."""
    monkeypatch.delenv(RAILWAY_ENV, raising=False)
    monkeypatch.delenv(RAILWAY_VOLUME, raising=False)

    assert not is_ephemeral_platform()
    assert not warn_if_data_is_temporary(SQLITE)


def test_disksiz_railwayda_ogohlantiriladi(monkeypatch, caplog) -> None:  # noqa: ANN001
    """ENG MUHIM: disk ulanmagan bo'lsa e'tibordan qochmasligi kerak."""
    monkeypatch.setenv(RAILWAY_ENV, "production")
    monkeypatch.delenv(RAILWAY_VOLUME, raising=False)

    with caplog.at_level(logging.WARNING):
        assert warn_if_data_is_temporary(SQLITE)

    matn = caplog.text
    assert "DOIMIY DISK ULANMAGAN" in matn
    assert "to'lovlar" in matn, "nima yo'qolishi aytilishi kerak"
    assert "New Volume" in matn, "qanday tuzatish aytilishi kerak"


def test_disk_ulangan_railwayda_ogohlantirish_yoq(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv(RAILWAY_ENV, "production")
    monkeypatch.setenv(RAILWAY_VOLUME, "/data")

    assert not warn_if_data_is_temporary(SQLITE)


def test_postgresql_uchun_ogohlantirish_yoq(monkeypatch) -> None:  # noqa: ANN001
    """PostgreSQL alohida xizmat — konteyner diski bilan bog'liq emas."""
    monkeypatch.setenv(RAILWAY_ENV, "production")
    monkeypatch.delenv(RAILWAY_VOLUME, raising=False)

    assert not warn_if_data_is_temporary("postgresql+asyncpg://u:p@host/db")


# --------------------------------------------------------------------------- #
#  Baza yo'lini doimiy diskka ko'chirish
# --------------------------------------------------------------------------- #


def test_disk_ulansa_baza_osha_yerda_joylashadi(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv(RAILWAY_VOLUME, "/data")

    assert volume_path().as_posix() == "/data"
    assert database_url_for_platform(None) == "sqlite+aiosqlite:////data/hcs.db"


def test_ochiq_berilgan_url_bekor_qilinmaydi(monkeypatch) -> None:  # noqa: ANN001
    """Foydalanuvchi o'zi yozgan sozlama har doim ustun turadi."""
    monkeypatch.setenv(RAILWAY_VOLUME, "/data")

    assert database_url_for_platform("postgresql+asyncpg://u:p@host/db") is None


def test_disk_yoq_bolsa_ozgartirilmaydi(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv(RAILWAY_VOLUME, raising=False)

    assert volume_path() is None
    assert database_url_for_platform(None) is None


def test_bosh_disk_qiymati_etiborsiz_qoldiriladi(monkeypatch) -> None:  # noqa: ANN001
    """Bo'sh satr — disk ulanmagani bilan bir xil."""
    monkeypatch.setenv(RAILWAY_VOLUME, "   ")

    assert volume_path() is None
    assert database_url_for_platform(None) is None


# --------------------------------------------------------------------------- #
#  Barcha kirish nuqtalari bitta bazaga qarashi
# --------------------------------------------------------------------------- #


def test_sozlama_muhitga_yoziladi(monkeypatch) -> None:  # noqa: ANN001
    """Bot, seed va Alembic BITTA bazaga ishlashi shart.

    Yo'l muhit o'zgaruvchisiga yoziladi, chunki har bir kirish nuqtasi uni
    o'zicha hisoblasa, migratsiya bir faylga, bot esa boshqasiga yozadi.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(RAILWAY_VOLUME, "/data")

    natija = apply_platform_defaults()

    assert natija == "sqlite+aiosqlite:////data/hcs.db"
    assert os.environ["DATABASE_URL"] == natija


def test_ochiq_sozlama_muhitda_ham_saqlanadi(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host/db")
    monkeypatch.setenv(RAILWAY_VOLUME, "/data")

    assert apply_platform_defaults() is None
    assert os.environ["DATABASE_URL"] == "postgresql+asyncpg://u:p@host/db"


def test_disksiz_muhit_ozgartirilmaydi(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv(RAILWAY_VOLUME, raising=False)

    assert apply_platform_defaults() is None
    assert "DATABASE_URL" not in os.environ
