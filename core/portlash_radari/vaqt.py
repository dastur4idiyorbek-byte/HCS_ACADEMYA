"""Sessiya jadvali — sof hisob, tarmoq va bazasiz.

Binance 4 soatlik shamlari UTC da 00, 04, 08, 12, 16, 20 da ochiladi.
Har sham oldidan ikki sessiya:

    A — kashfiyot   shamdan `kashfiyot_daqiqa` (60) oldin
    B — tasdiq      shamdan `tasdiq_daqiqa` (15) oldin — RASMIY

KUN. 1 kun = 6 ta rasmiy sessiya. Kun — sessiya oldidan turgan
shamning UTC SANASI. 23:45 UTC dagi B sessiyasi keyingi kunning
00:00 shamiga tegishli, ya'ni keyingi kunning 1-sessiyasi.
Qirg'iziston vaqtida bu kun 05:45 da boshlanib, 01:45 da tugaydi —
loyiha egasi so'ragan chegara aynan shu.

Hammasi UTC da. Mahalliy vaqt faqat ekranda.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

SHAM_SOAT = 4
KASHFIYOT = "kashfiyot"
TASDIQ = "tasdiq"
QOLDA = "qolda"
RASMIY_TURLAR = (KASHFIYOT, TASDIQ)


@dataclass(frozen=True, slots=True)
class JadvalSozlamasi:
    kashfiyot_daqiqa: int = 60
    tasdiq_daqiqa: int = 15
    kashfiyot_kechikish_daqiqa: int = 40
    tasdiq_kechikish_daqiqa: int = 14


@dataclass(frozen=True, slots=True)
class Rejadagi:
    """Jadvaldagi bitta sessiya."""

    turi: str
    sham_vaqti: datetime
    vaqt: datetime
    #: Shundan keyin sessiya o'tkazib yuborilgan hisoblanadi
    oxirgi_muddat: datetime


def _utc(t: datetime) -> datetime:
    if t.tzinfo is None:
        raise ValueError("naive vaqt — UTC kerak")
    return t.astimezone(UTC)


def sham_boshi(t: datetime) -> datetime:
    """`t` ichida turgan 4 soatlik shamning ochilishi."""
    t = _utc(t)
    return t.replace(hour=t.hour - t.hour % SHAM_SOAT, minute=0, second=0, microsecond=0)


def keyingi_sham(t: datetime) -> datetime:
    """`t` dan KEYIN ochiladigan birinchi sham (qat'iy katta)."""
    return sham_boshi(t) + timedelta(hours=SHAM_SOAT)


def kun_va_tartib(sham_vaqti: datetime) -> tuple[str, int]:
    """Sham ochilishi -> (`YYYY-MM-DD`, 1..6)."""
    s = _utc(sham_vaqti)
    if s.hour % SHAM_SOAT or s.minute or s.second or s.microsecond:
        raise ValueError(f"4 soatlik sham ochilishi emas: {s.isoformat()}")
    return s.date().isoformat(), s.hour // SHAM_SOAT + 1


def sessiya_vaqti(turi: str, sham_vaqti: datetime, j: JadvalSozlamasi) -> datetime:
    daqiqa = j.kashfiyot_daqiqa if turi == KASHFIYOT else j.tasdiq_daqiqa
    return _utc(sham_vaqti) - timedelta(minutes=daqiqa)


def _rejadagi(turi: str, sham: datetime, j: JadvalSozlamasi) -> Rejadagi:
    vaqt = sessiya_vaqti(turi, sham, j)
    kechikish = (
        j.kashfiyot_kechikish_daqiqa if turi == KASHFIYOT else j.tasdiq_kechikish_daqiqa
    )
    return Rejadagi(turi, sham, vaqt, vaqt + timedelta(minutes=kechikish))


def atrofdagi(hozir: datetime, j: JadvalSozlamasi) -> list[Rejadagi]:
    """`hozir` atrofidagi sessiyalar — vaqt bo'yicha tartibda.

    Oldingi va keyingi bir necha sham qamraladi: kechikkan sessiya
    ham, eng yaqin kelajakdagisi ham shu ro'yxatda bo'lishi kerak.
    """
    boshi = sham_boshi(hozir)
    natija = [
        _rejadagi(turi, boshi + timedelta(hours=SHAM_SOAT * k), j)
        for k in range(-1, 3)
        for turi in RASMIY_TURLAR
    ]
    return sorted(natija, key=lambda r: r.vaqt)


def bajariladiganlar(hozir: datetime, j: JadvalSozlamasi) -> list[Rejadagi]:
    """Hozir yugurishi kerak bo'lgan sessiyalar (vaqti kelgan, muddati o'tmagan).

    Allaqachon bajarilganini bu funksiya BILMAYDI — buni ishchi bazadan
    tekshiradi. Bu yerda faqat soat hisobi.
    """
    hozir = _utc(hozir)
    return [r for r in atrofdagi(hozir, j) if r.vaqt <= hozir <= r.oxirgi_muddat]


def keyingisi(hozir: datetime, j: JadvalSozlamasi, turi: str | None = None) -> Rejadagi:
    """Kelajakdagi eng yaqin sessiya (ixtiyoriy: faqat bir turi)."""
    hozir = _utc(hozir)
    for r in atrofdagi(hozir, j):
        if r.vaqt > hozir and (turi is None or r.turi == turi):
            return r
    raise AssertionError("atrofdagi() kelajakni qamramadi")  # pragma: no cover


def oldingi_rasmiy_slot(turi: str, sham_vaqti: datetime) -> tuple[str, datetime]:
    """"Ketma-ket" hisoblagichi bog'lanadigan oldingi sessiya — O'Z TURIDAN.

    B(C) dan oldin B(C - 4 soat), A(C) dan oldin A(C - 4 soat). Ikki
    zanjir ATAYLAB ajratilgan: admin faqat rasmiy B sessiyalarini ko'radi.
    A ham zanjirga qo'shilsa, B da birinchi marta tasdiqlangan coin
    "🔁 2-marta" bo'lib chiqardi va rasmiy bo'lmagan A sessiyasi B
    hisobini uzib qo'yardi.

    Orada sessiya o'tkazib yuborilgan bo'lsa zanjir uziladi va hisob
    1 dan boshlanadi.
    """
    if turi not in (TASDIQ, KASHFIYOT):
        raise ValueError(f"rasmiy sessiya emas: {turi}")
    return turi, sham_vaqti - timedelta(hours=SHAM_SOAT)


def kunlik_yangilash_vaqti(hozir: datetime, soat: int, daqiqa: int) -> datetime:
    """`hozir` dan oldingi eng yaqin kunlik yangilash payti (UTC)."""
    hozir = _utc(hozir)
    bugun = hozir.replace(hour=soat, minute=daqiqa, second=0, microsecond=0)
    return bugun if bugun <= hozir else bugun - timedelta(days=1)


def ms(t: datetime) -> int:
    """Binance millisekund formati."""
    return int(_utc(t).timestamp() * 1000)


def ms_dan(son: float) -> datetime:
    return datetime.fromtimestamp(float(son) / 1000.0, tz=UTC)
