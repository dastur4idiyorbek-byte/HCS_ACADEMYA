"""Muhit sozlamalari — yarim ishlaydigan bot bilan ishga tushmaslik kerak."""

from __future__ import annotations

import pytest

from bot.settings import SettingsError, load_settings


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
