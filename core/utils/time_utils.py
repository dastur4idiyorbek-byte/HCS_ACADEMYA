"""Vaqt bilan ishlash — timezone-aware, xato qilmaydigan (6.3-band).

Server odatda UTC'da ishlaydi, lekin Juma filtri (4.8-band) mahalliy vaqtga
bog'liq. Shuning uchun bu yerdagi hamma narsa aniq vaqt zonasi bilan
hisoblanadi, `datetime.now()` (naive) hech qachon ishlatilmaydi.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

_HHMM_RE = re.compile(r"^(?P<h>\d{1,2}):(?P<m>\d{2})$")


def utc_now() -> datetime:
    """Hozirgi vaqt, doim timezone-aware UTC."""
    return datetime.now(UTC)


class Clock(ABC):
    """Vaqt manbai abstraksiyasi.

    Testda vaqtni "muzlatish" uchun kerak — Juma filtri kabi vaqtga bog'liq
    mantiqni haqiqiy soatga bog'lamasdan sinash mumkin bo'lsin.
    """

    @abstractmethod
    def now(self) -> datetime:
        """Hozirgi timezone-aware UTC vaqt."""

    def now_in(self, tz_name: str) -> datetime:
        """Hozirgi vaqt berilgan vaqt zonasida."""
        return self.now().astimezone(ZoneInfo(tz_name))


class SystemClock(Clock):
    """Haqiqiy tizim soati."""

    def now(self) -> datetime:
        return utc_now()


class FrozenClock(Clock):
    """Test uchun qotirilgan soat."""

    def __init__(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            raise ValueError("FrozenClock faqat timezone-aware vaqt qabul qiladi")
        self._moment = moment

    def now(self) -> datetime:
        return self._moment.astimezone(UTC)

    def set(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            raise ValueError("FrozenClock faqat timezone-aware vaqt qabul qiladi")
        self._moment = moment


def parse_hhmm(value: str) -> time:
    """`"11:00"` ko'rinishidagi matnni `time` obyektiga aylantiradi."""
    match = _HHMM_RE.match(value.strip())
    if not match:
        raise ValueError(f"Vaqt formati noto'g'ri: {value!r} (kutilgan format: 'HH:MM')")
    hour, minute = int(match["h"]), int(match["m"])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Vaqt qiymati oralig'dan tashqarida: {value!r}")
    return time(hour=hour, minute=minute)


def is_within_daily_window(
    moment: datetime,
    tz_name: str,
    start: time,
    end: time,
    weekday: int | None = None,
) -> bool:
    """`moment` berilgan vaqt zonasidagi kunlik oynaga tushadimi?

    Args:
        moment: tekshiriladigan vaqt (timezone-aware bo'lishi SHART).
        tz_name: mahalliy vaqt zonasi, masalan ``"Asia/Tashkent"``.
        start: oyna boshlanishi (mahalliy vaqt).
        end: oyna tugashi (mahalliy vaqt).
        weekday: agar berilsa, faqat shu hafta kunida (Monday=0 ... Sunday=6).

    Chegara: `start <= t < end` — boshlanish kiradi, tugash kirmaydi.
    Yarim tundan o'tuvchi oyna (start > end) ham qo'llab-quvvatlanadi.
    """
    if moment.tzinfo is None:
        raise ValueError("is_within_daily_window faqat timezone-aware vaqt qabul qiladi")

    local = moment.astimezone(ZoneInfo(tz_name))
    local_time = local.time()

    if start <= end:
        in_window = start <= local_time < end
        day_of_window = local.weekday()
    else:
        # Yarim tundan o'tadi: [start, 24:00) yoki [00:00, end)
        if local_time >= start:
            in_window = True
            day_of_window = local.weekday()
        elif local_time < end:
            in_window = True
            # Oyna kechagi kunga tegishli
            day_of_window = (local.weekday() - 1) % 7
        else:
            in_window = False
            day_of_window = local.weekday()

    if not in_window:
        return False
    return weekday is None or day_of_window == weekday
