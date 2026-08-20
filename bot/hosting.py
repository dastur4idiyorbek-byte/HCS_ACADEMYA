"""Joylashtirish muhitini aniqlash — Railway kabi platformalar uchun.

Nima uchun bu `bot/` da, `core/` da emas: bu qatlam joylashtirishga xos
(0.1-band — `core/` sof mantiq bo'lib qolishi kerak).

Hal qiladigan muammo: Railway kabi platformalarda konteyner diski HAR
YANGILANISHDA tozalanadi. Baza esa oddiy fayl — to'lovlar, obunalar va
foydalanuvchi pozitsiyalari o'shanda. Disk (volume) ulanmasa, bu
ma'lumotlar JIMGINA yo'qoladi va buni faqat mijoz "men to'lagandim"
deganda bilib qolasiz.
"""

from __future__ import annotations

import os
from pathlib import Path

from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Railway har bir joylashtirishda o'rnatadi
RAILWAY_ENV = "RAILWAY_ENVIRONMENT"
#: Doimiy disk ulanganda Railway shu o'zgaruvchini beradi
RAILWAY_VOLUME = "RAILWAY_VOLUME_MOUNT_PATH"


def is_ephemeral_platform() -> bool:
    """Konteyner diski yangilanishda tozalanadigan platformadamizmi."""
    return bool(os.getenv(RAILWAY_ENV))


def volume_path() -> Path | None:
    """Ulangan doimiy diskning yo'li, yoki `None` — ulanmagan."""
    yol = os.getenv(RAILWAY_VOLUME, "").strip()
    return Path(yol) if yol else None


def database_url_for_platform(explicit: str | None = None) -> str | None:
    """Doimiy disk ulangan bo'lsa, baza o'sha yerda joylashsin.

    Faqat `DATABASE_URL` ochiq berilmagan holda ishlaydi — ya'ni ochiq
    ko'rsatilgan sozlama hech qachon bekor qilinmaydi.

    Returns:
        Yangi URL, yoki `None` — o'zgartirish kerak emas.
    """
    if explicit:
        return None

    disk = volume_path()
    if disk is None:
        return None

    return f"sqlite+aiosqlite:///{disk / 'hcs.db'}"


def apply_platform_defaults() -> str | None:
    """Doimiy disk ulangan bo'lsa `DATABASE_URL` ni o'shanga yo'naltiradi.

    Nima uchun muhit o'zgaruvchisi orqali: botni, `scripts/seed.py` ni va
    Alembic'ni BITTA bazaga qaratish kerak. Har biri o'zicha yo'l
    hisoblasa, migratsiya bir faylga, bot esa boshqasiga yozadi va buni
    payqash juda qiyin.

    Har bir kirish nuqtasi ishga tushishida shuni chaqiradi.

    Returns:
        O'rnatilgan yangi URL, yoki `None` — o'zgartirish kerak emas.
    """
    yangi = database_url_for_platform(os.getenv("DATABASE_URL"))
    if yangi is not None:
        os.environ["DATABASE_URL"] = yangi
    return yangi


def warn_if_data_is_temporary(database_url: str) -> bool:
    """Baza vaqtinchalik diskda bo'lsa baland ovozda ogohlantiradi.

    Ishga tushirishni TO'XTATMAYDI: sinov uchun ataylab vaqtinchalik
    ishga tushirish ham mumkin. Lekin ogohlantirish e'tibordan
    qochmaydigan qilib yoziladi.

    Returns:
        `True` — ogohlantirish berildi.
    """
    if not is_ephemeral_platform():
        return False
    if not database_url.startswith("sqlite"):
        return False  # PostgreSQL alohida xizmat — disk muammosi yo'q
    if volume_path() is not None:
        return False  # doimiy disk ulangan

    logger.warning(
        "%s\n"
        "  DOIMIY DISK ULANMAGAN — baza har yangilanishda O'CHADI.\n"
        "  Yo'qoladigan ma'lumot: to'lovlar, obunalar, foydalanuvchi\n"
        "  pozitsiyalari va signal tarixi.\n"
        "  Tuzatish: Railway -> loyihangiz -> Variables yonidagi menyu ->\n"
        "  New Volume -> ulash yo'li: /data\n"
        "%s",
        "=" * 64,
        "=" * 64,
    )
    return True
