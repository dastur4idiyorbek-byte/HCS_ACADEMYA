"""4.8-band: Juma namozi vaqti filtri uchun vaqt hisobi.

Bu testlar ayniqsa muhim: server UTC'da ishlaydi, filtr esa mahalliy vaqtga
bog'liq. Bir soatlik xato — savdo to'xtamasligi yoki noo'rin to'xtashi
demakdir.
"""

from __future__ import annotations

from datetime import UTC, datetime, time

import pytest

from core.utils.time_utils import is_within_daily_window, parse_hhmm

TOSHKENT = "Asia/Tashkent"  # UTC+5
JUMA = 4


def utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


@pytest.mark.parametrize(
    ("moment", "kutilgan", "izoh"),
    [
        (utc(2026, 8, 21, 6, 0), True, "juma 11:00 — oyna boshlanishi (kiradi)"),
        (utc(2026, 8, 21, 7, 30), True, "juma 12:30 — oyna o'rtasi"),
        (utc(2026, 8, 21, 9, 59), True, "juma 14:59 — oyna oxiri"),
        (utc(2026, 8, 21, 10, 0), False, "juma 15:00 — oyna tugadi (kirmaydi)"),
        (utc(2026, 8, 21, 5, 59), False, "juma 10:59 — hali erta"),
        (utc(2026, 8, 20, 7, 30), False, "payshanba 12:30 — boshqa kun"),
        (utc(2026, 8, 22, 7, 30), False, "shanba 12:30 — boshqa kun"),
    ],
)
def test_juma_oynasi(moment: datetime, kutilgan: bool, izoh: str) -> None:
    natija = is_within_daily_window(
        moment, TOSHKENT, parse_hhmm("11:00"), parse_hhmm("15:00"), weekday=JUMA
    )
    assert natija is kutilgan, izoh


def test_utc_kunni_kesib_otganda_juma_saqlanadi() -> None:
    """UTC'da payshanba 20:00 = Toshkentda juma 01:00 — hafta kuni mahalliy bo'yicha."""
    payshanba_kech_utc = utc(2026, 8, 20, 20, 0)
    # 01:00 oynaga kirmaydi, lekin mahalliy kun JUMA ekanini tekshiramiz
    assert is_within_daily_window(
        payshanba_kech_utc, TOSHKENT, time(0, 0), time(2, 0), weekday=JUMA
    )


def test_yarim_tundan_otuvchi_oyna() -> None:
    """22:00–02:00 kabi oyna ham to'g'ri ishlashi kerak."""
    kech = utc(2026, 8, 21, 18, 0)   # Toshkentda 23:00, juma
    erta = utc(2026, 8, 21, 20, 0)   # Toshkentda 01:00, shanba — lekin oyna JUMAniki
    assert is_within_daily_window(kech, TOSHKENT, time(22, 0), time(2, 0), weekday=JUMA)
    assert is_within_daily_window(erta, TOSHKENT, time(22, 0), time(2, 0), weekday=JUMA)


def test_hafta_kuni_berilmasa_har_kuni_ishlaydi() -> None:
    seshanba = utc(2026, 8, 18, 7, 30)
    assert is_within_daily_window(seshanba, TOSHKENT, time(11, 0), time(15, 0))


def test_naive_vaqt_rad_etiladi() -> None:
    """Timezone-siz vaqt jim qabul qilinmasligi kerak — bu xato manbai."""
    with pytest.raises(ValueError, match="timezone-aware"):
        is_within_daily_window(datetime(2026, 8, 21, 7, 30), TOSHKENT, time(11, 0), time(15, 0))


@pytest.mark.parametrize("yomon", ["11", "11:0", "25:00", "11:60", "abc", ""])
def test_notogri_vaqt_formati(yomon: str) -> None:
    with pytest.raises(ValueError):
        parse_hhmm(yomon)
