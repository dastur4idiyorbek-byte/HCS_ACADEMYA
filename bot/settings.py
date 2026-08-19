"""Bot ishga tushishi uchun muhit sozlamalari (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class SettingsError(RuntimeError):
    """Majburiy muhit o'zgaruvchisi yetishmayapti."""


@dataclass(frozen=True, slots=True)
class BotSettings:
    token: str
    admin_ids: frozenset[int] = field(default_factory=frozenset)
    database_url: str = "sqlite+aiosqlite:///data/hcs.db"
    config_file: str = "config/default.yaml"
    log_level: str = "INFO"
    log_dir: str = "logs"

    def is_admin(self, telegram_id: int) -> bool:
        """1.1-band: rol Telegram ID asosida aniqlanadi."""
        return telegram_id in self.admin_ids


def _parse_admin_ids(raw: str | None) -> frozenset[int]:
    if not raw:
        return frozenset()
    ids: set[int] = set()
    for qism in raw.replace(";", ",").split(","):
        qism = qism.strip()
        if not qism:
            continue
        try:
            ids.add(int(qism))
        except ValueError as exc:
            raise SettingsError(f"ADMIN_IDS noto'g'ri qiymat: {qism!r}") from exc
    return frozenset(ids)


def load_settings() -> BotSettings:
    """Muhitdan sozlamalarni o'qiydi.

    Token yo'q bo'lsa darhol xato beriladi — yarim ishlaydigan bot xavfli.
    """
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SettingsError(
            "BOT_TOKEN o'rnatilmagan. `.env.example` faylidan `.env` yarating va "
            "BotFather'dan olingan tokenni kiriting."
        )

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS"))
    if not admin_ids:
        raise SettingsError(
            "ADMIN_IDS o'rnatilmagan. Kamida bitta admin Telegram ID kerak — "
            "aks holda to'lovlarni tasdiqlash va panelga kirish imkonsiz."
        )

    return BotSettings(
        token=token,
        admin_ids=admin_ids,
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/hcs.db"),
        config_file=os.getenv("HCS_CONFIG_FILE", "config/default.yaml"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir=os.getenv("LOG_DIR", "logs"),
    )
