"""Arxitektura qoidalarini kod darajasida qo'riqlash.

0.1-band eng muhim tamoyil: "miya" va "tana" QAT'IY ajratilgan. Bu qoida
faqat hujjatda qolsa, vaqt o'tib buziladi — shuning uchun test sifatida
mustahkamlanadi.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

LOYIHA = Path(__file__).resolve().parent.parent
CORE = LOYIHA / "core"

#: `core/` da TAQIQLANGAN paketlar
TAQIQLANGAN = {"aiogram", "telebot", "telegram", "pyrogram"}


def python_fayllar(papka: Path) -> list[Path]:
    return sorted(p for p in papka.rglob("*.py") if "__pycache__" not in p.parts)


def import_qilingan_paketlar(fayl: Path) -> set[str]:
    """Fayldagi barcha import'larning ILDIZ paket nomlari."""
    daraxt = ast.parse(fayl.read_text(encoding="utf-8"), filename=str(fayl))
    paketlar: set[str] = set()
    for tugun in ast.walk(daraxt):
        if isinstance(tugun, ast.Import):
            paketlar |= {alias.name.split(".")[0] for alias in tugun.names}
        elif isinstance(tugun, ast.ImportFrom) and tugun.module and tugun.level == 0:
            paketlar.add(tugun.module.split(".")[0])
    return paketlar


@pytest.mark.parametrize("fayl", python_fayllar(CORE), ids=lambda p: str(p.relative_to(LOYIHA)))
def test_core_telegramga_boglanmagan(fayl: Path) -> None:
    """`core/` Telegram kutubxonalarini import qilmasligi SHART.

    Sabab: kelajakda mobil ilovaga o'tish uchun `core/` ni qayta yozmasdan,
    uning ustiga `api/` qatlamini qo'shish kifoya bo'lishi kerak.
    """
    taqiqlangan = import_qilingan_paketlar(fayl) & TAQIQLANGAN
    assert not taqiqlangan, (
        f"{fayl.relative_to(LOYIHA)} Telegram kutubxonasini import qilyapti: {taqiqlangan}. "
        "0.1-band: 'miya' Telegram API'siga bevosita bog'lanmasligi kerak."
    )


@pytest.mark.parametrize("fayl", python_fayllar(CORE), ids=lambda p: str(p.relative_to(LOYIHA)))
def test_core_bot_paketiga_boglanmagan(fayl: Path) -> None:
    """`core/` `bot/` ni import qilmasligi kerak — bog'liqlik faqat bir tomonlama."""
    assert "bot" not in import_qilingan_paketlar(fayl), (
        f"{fayl.relative_to(LOYIHA)} `bot/` ni import qilyapti — "
        "bog'liqlik yo'nalishi faqat bot -> core bo'lishi kerak."
    )


def test_infratuzilma_papkalari_mavjud() -> None:
    """Tahlil modulidan MUSTAQIL qatlamlar — ular hech qachon yo'qolmasin.

    2026-09-03 — eski `core/analysis/*` ro'yxati bu yerdan chiqarildi:
    o'sha modul butunlay o'chirildi. Yangi tahlil moduli qurilgan sari
    uning papkalari `test_yangi_modul_papkalari` ga qo'shiladi — ikki
    ro'yxat ataylab alohida: biri O'ZGARMAYDIGAN poydevor, ikkinchisi
    O'SIB BORADIGAN qurilish.
    """
    kutilgan = [
        "core/risk_engine",
        "core/position_sizing",
        "core/halal_screening",
        "core/market_data",
        "core/backtest",
        "core/storage",
        "core/domain",
        "core/config",
        "bot/handlers",
        "bot/i18n",
    ]
    yetishmayotgan = [yol for yol in kutilgan if not (LOYIHA / yol).is_dir()]
    assert not yetishmayotgan, f"Yetishmayotgan papkalar: {yetishmayotgan}"


def test_yangi_modul_papkalari() -> None:
    """2-prompt, 9-qism: yangi tahlil moduli qurilgan qismlari.

    Ro'yxat HAR BOSQICHDA o'sadi. Hozir 1-bosqich bajarilgan:
    market_data ichida Bitget mijozi va narx solishtirish.
    """
    kutilgan = [
        "core/market_data/bitget.py",
        "core/market_data/price_reconciliation.py",
    ]
    yetishmayotgan = [yol for yol in kutilgan if not (LOYIHA / yol).exists()]
    assert not yetishmayotgan, f"Yetishmayotgan fayllar: {yetishmayotgan}"


def test_har_bir_paket_hujjatlangan() -> None:
    """Har bir `__init__.py` nima uchun borligini tushuntirishi kerak."""
    hujjatsiz = []
    for fayl in CORE.rglob("__init__.py"):
        if "__pycache__" in fayl.parts:
            continue
        daraxt = ast.parse(fayl.read_text(encoding="utf-8"))
        if ast.get_docstring(daraxt) is None and not daraxt.body:
            hujjatsiz.append(str(fayl.relative_to(LOYIHA)))
    assert not hujjatsiz, f"Izohsiz bo'sh paketlar: {hujjatsiz}"


# --------------------------------------------------------------------------- #
#  Qavatlar: bog'liqlik faqat PASTGA qaraydi
# --------------------------------------------------------------------------- #

#: Har bir modul QAYSI qavatda. Kichik raqam — pastroq qavat.
#:
#: Qoida bitta: modul faqat O'ZIDAN PAST yoki teng qavatga suyanadi.
#: Buzilsa "nima nimani bajaryapti" ko'rinmay qoladi — poydevor tomga
#: suyanib turadi (`docs/ARXITEKTURA.md`, qurilish xaritasi).
QAVATLAR = {
    "utils": 0,
    "domain": 0,
    "config": 1,
    "storage": 1,
    "market_data": 2,
    "halal_screening": 2,
    "analysis": 3,
    "position_sizing": 4,
    "risk_engine": 4,
    "signals": 4,
    "pipeline": 5,
    "services": 5,
    "backtest": 6,
}


def core_modullari() -> list[str]:
    return sorted(
        p.name for p in CORE.iterdir() if p.is_dir() and p.name != "__pycache__"
    )


def core_bogliqliklari(modul: str) -> set[str]:
    """`core.<modul>` ichidan qaysi boshqa `core.*` paketlar chaqiriladi."""
    topilgan: set[str] = set()
    for fayl in python_fayllar(CORE / modul):
        daraxt = ast.parse(fayl.read_text(encoding="utf-8"), filename=str(fayl))
        for tugun in ast.walk(daraxt):
            if isinstance(tugun, ast.ImportFrom) and (tugun.module or "").startswith(
                "core."
            ):
                bolaklar = tugun.module.split(".")
                if len(bolaklar) > 1 and bolaklar[1] != modul:
                    topilgan.add(bolaklar[1])
    return topilgan


def test_har_bir_modulning_qavati_belgilangan() -> None:
    """Yangi modul qo'shilsa, uning qavati ham aytilishi kerak.

    Aks holda u qoidadan jimgina chetda qolardi.
    """
    nomlanmagan = set(core_modullari()) - set(QAVATLAR)
    assert not nomlanmagan, (
        f"Bu modullarning qavati belgilanmagan: {sorted(nomlanmagan)}. "
        "`QAVATLAR` ga qo'shing — qaysi qatorda turishini ayting."
    )


@pytest.mark.parametrize("modul", sorted(QAVATLAR))
def test_bogliqlik_faqat_pastga_qaraydi(modul: str) -> None:
    """Poydevor tomga suyanmasin.

    Ilgari ikkita g'isht teskari yotardi:

      1. `storage` -> `analysis.postmortem`, `pipeline` — baza qatlami
         tahlil qatlamidan tur o'qirdi
      2. `analysis.market_health` -> `position_sizing` — bozor tahlili
         foydalanuvchining puliga qarardi

    Ikkalasi ham turlarni `domain` ga ko'chirish bilan yechildi.
    """
    if not (CORE / modul).is_dir():
        pytest.skip(f"{modul} papkasi yo'q")

    oz_qavati = QAVATLAR[modul]
    buzilganlar = [
        f"{modul}({oz_qavati}) -> {bogliq}({QAVATLAR[bogliq]})"
        for bogliq in core_bogliqliklari(modul)
        if bogliq in QAVATLAR and QAVATLAR[bogliq] > oz_qavati
    ]

    assert not buzilganlar, (
        "Bog'liqlik TEPAGA qaragan: " + ", ".join(buzilganlar) + ". "
        "Ikki tomon ham ishlatadigan tipni `core/domain` ga ko'chiring."
    )


# --------------------------------------------------------------------------- #
#  Yopiq holatlar ro'yxati BITTA joyda
# --------------------------------------------------------------------------- #


def test_yopiq_holatlar_qolda_takrorlanmasin() -> None:
    """`tp2_hit + stopped + cancelled` uchligi kodda yozilmasin.

    Bu ro'yxat `repositories.py` da uch joyda, saytda esa yana ikki
    joyda qo'lda yozilgan edi. Yangi yopuvchi holat qo'shilganda
    ularning biri unutilsa, signal ba'zi ko'rinishlarda abadiy
    "ochiq" bo'lib qolardi va statistika jimgina boshqa raqam
    berardi — hech qanday xato xabari chiqmasdan.

    Manba: `SignalStatus.closed_values()` (Python) va
    `YOPIQ_HOLATLAR` (sayt). Ular `is_closed` dan chiqadi.
    """
    from core.domain.enums import SignalStatus

    ildiz = Path(__file__).resolve().parent.parent
    uchlik = {"tp2_hit", "stopped", "cancelled"}

    #: Ro'yxat bir necha qatorga yoyilgan bo'lishi mumkin —
    #: `repositories.py` da u aynan shunday yozilgan edi. Shuning
    #: uchun qator emas, OYNA tekshiriladi.
    OYNA = 6

    #: E'lon qilish TAKRORLASH emas. Enum a'zosi va TS union a'zosi
    #: holatlarni SANAB CHIQADI — bu ularning yagona ta'rifi. Test
    #: qidirayotgan narsa boshqa: "yopiqmi" degan savolga javob
    #: beruvchi TO'PLAM ikkinchi marta yozilgani.
    ELON = re.compile(r'^\s*(\|\s*"|[A-Z][A-Z0-9_]*\s*=\s*")')

    #: To'plam ekanini ko'rsatuvchi belgilar. Bularsiz uchta nom bir
    #: joyda uchrashi mumkin (masalan har biriga alohida javob
    #: qaytaruvchi `yakuni()` funksiyasi) — u takrorlash emas.
    KONTEKST = ("in_(", "not_in(", "in (", "in [", "in {", "= [", "= {", "||", ".includes(")

    def qidir(matn: str) -> list[int]:
        satrlar = matn.splitlines()
        topilgan: list[int] = []
        for i in range(len(satrlar)):
            oyna = [s for s in satrlar[i : i + OYNA] if not ELON.match(s)]
            if any("YOPIQ_HOLATLAR" in s for s in oyna):
                continue
            birlashgan = "\n".join(oyna)
            if not any(belgi in birlashgan for belgi in KONTEKST):
                continue
            bor = {
                h
                for h in uchlik
                if f"'{h}'" in birlashgan
                or f'"{h}"' in birlashgan
                or f"{h.upper()}.value" in birlashgan
                or f"SignalStatus.{h.upper()}" in birlashgan
            }
            if len(bor) == len(uchlik):
                topilgan.append(i + 1)
        return topilgan

    ayblanuvchi: list[str] = []
    fayllar = [
        *(ildiz / "core").rglob("*.py"),
        *(ildiz / "bot").rglob("*.py"),
        *(ildiz / "web" / "src").rglob("*.ts"),
        *(ildiz / "web" / "src").rglob("*.tsx"),
    ]
    for fayl in fayllar:
        if "node_modules" in fayl.parts or fayl.name == "enums.py":
            continue
        uchragan = qidir(fayl.read_text(encoding="utf-8"))
        if uchragan:
            ayblanuvchi.append(f"{fayl.relative_to(ildiz)}:{uchragan[0]}")

    assert not ayblanuvchi, (
        "Yopiq holatlar ro'yxati qo'lda takrorlangan:\n  "
        + "\n  ".join(ayblanuvchi)
        + "\n\nO'rniga `SignalStatus.closed_values()` yoki "
        "`YOPIQ_HOLATLAR` ishlating."
    )

    # Manbaning o'zi to'g'ri ishlayotganini ham tekshiramiz — aks holda
    # yuqoridagi skaner bo'sh ro'yxatni "yaxshi" deb o'qib qo'yardi.
    yopiq = set(SignalStatus.closed_values())
    assert uchlik <= yopiq
    assert set(SignalStatus.open_values()) & yopiq == set()

    # QOIDA ISHLADI. To'rtinchi yopuvchi holat (`timed_out`)
    # qo'shilganda hech bir ro'yxatni qo'lda yangilash kerak
    # bo'lmadi — u `is_closed` dan o'zi chiqdi. Ilgari bu beshta
    # joyni qo'lda topishni talab qilardi va bittasi unutilsa
    # signal ba'zi ko'rinishlarda abadiy "ochiq" qolardi.
    assert SignalStatus.TIMED_OUT.value in yopiq
