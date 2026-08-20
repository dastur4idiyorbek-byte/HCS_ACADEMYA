"""Muhit sozlamalari — yarim ishlaydigan bot bilan ishga tushmaslik kerak."""

from __future__ import annotations

import os

import pytest

from bot.settings import SettingsError, load_env_file, load_settings


def test_token_yoq_bolsa_ishga_tushmaydi(monkeypatch) -> None:
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("ADMIN_IDS", "123")
    with pytest.raises(SettingsError, match="BOT_TOKEN"):
        load_settings()


def test_admin_yoq_bolsa_ishga_tushmaydi(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.delenv("ADMIN_IDS", raising=False)
    with pytest.raises(SettingsError, match="ADMIN_IDS"):
        load_settings()


def test_adminlar_royxati_oqiladi(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ADMIN_IDS", "111, 222 ;333")
    settings = load_settings()
    assert settings.admin_ids == frozenset({111, 222, 333})
    assert settings.is_admin(222)
    assert not settings.is_admin(999)


def test_notogri_admin_id_rad_etiladi(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ADMIN_IDS", "111,abc")
    with pytest.raises(SettingsError, match="noto'g'ri"):
        load_settings()


# --------------------------------------------------------------------------- #
#  `.env` faylini o'qish
# --------------------------------------------------------------------------- #


def test_env_fayli_muhitga_yuklanadi(tmp_path, monkeypatch) -> None:
    """README `cp .env.example .env` deydi — demak bu fayl o'qilishi shart.

    Bu regressiya testi: `python-dotenv` bog'liqlikda bor edi, lekin hech
    qayerda chaqirilmagandi. Foydalanuvchi README'ga amal qilib `.env`
    yaratardi va bot baribir "BOT_TOKEN o'rnatilmagan" derdi.
    """
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("ADMIN_IDS", raising=False)
    fayl = tmp_path / ".env"
    fayl.write_text(
        "# izoh qatori\n"
        "\n"
        "BOT_TOKEN=123:abc\n"
        'ADMIN_IDS="111,222"\n'
        "BOSH_QATOR\n",
        encoding="utf-8",
    )

    load_env_file(fayl)

    settings = load_settings()
    assert settings.token == "123:abc"
    assert settings.admin_ids == frozenset({111, 222})


def test_mavjud_muhit_ozgaruvchisi_ustun_turadi(tmp_path, monkeypatch) -> None:
    """Serverda `.env` emas, tizim o'zgaruvchilari ishlatiladi (systemd, Docker)."""
    monkeypatch.setenv("BOT_TOKEN", "tizim:token")
    fayl = tmp_path / ".env"
    fayl.write_text("BOT_TOKEN=fayl:token\n", encoding="utf-8")

    load_env_file(fayl)

    assert os.environ["BOT_TOKEN"] == "tizim:token"


def test_env_fayli_yoq_bolsa_xato_bermaydi(tmp_path) -> None:
    """Fayl ixtiyoriy — yo'qligi xato emas."""
    load_env_file(tmp_path / "yoq.env")
