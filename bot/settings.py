"""Bot ishga tushishi uchun muhit sozlamalari (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

#: `.env` fayli loyiha ildizida qidiriladi (bot/settings.py -> bot/ -> ildiz)
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


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


def load_env_file(path: Path | None = None) -> None:
    """`.env` faylini muhitga yuklaydi (mavjud bo'lsa).

    README `cp .env.example .env` deydi, shuning uchun bu fayl haqiqatan
    o'qilishi kerak. Allaqachon o'rnatilgan muhit o'zgaruvchilari USTUN
    turadi (`override=False`) — serverda `.env` emas, tizim o'zgaruvchilari
    ishlatiladi (masalan systemd yoki Docker orqali berilganda).

    Fayl yo'q bo'lsa — xato emas: sozlamalar to'g'ridan-to'g'ri muhitdan
    berilgan bo'lishi mumkin.
    """
    fayl = path or ENV_FILE
    if fayl.is_file():
        load_dotenv(fayl, override=False)


def load_settings() -> BotSettings:
    """Muhitdan sozlamalarni o'qiydi.

    Token yo'q bo'lsa darhol xato beriladi — yarim ishlaydigan bot xavfli.

    Bu funksiya FAQAT muhitni o'qiydi. `.env` faylini yuklash alohida
    qadam (`load_env_file`) — shunda sozlamalar manbai aniq bo'ladi va
    testlar `.env` fayliga bog'lanib qolmaydi.
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
