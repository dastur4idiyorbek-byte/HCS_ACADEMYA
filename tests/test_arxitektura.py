"""Arxitektura qoidalarini kod darajasida qo'riqlash.

0.1-band eng muhim tamoyil: "miya" va "tana" QAT'IY ajratilgan. Bu qoida
faqat hujjatda qolsa, vaqt o'tib buziladi — shuning uchun test sifatida
mustahkamlanadi.
"""

from __future__ import annotations

import ast
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


def test_spetsifikatsiyadagi_barcha_papkalar_mavjud() -> None:
    """7-bo'lim 1-bosqich: struktura BOSHIDANOQ to'liq bo'lishi kerak."""
    kutilgan = [
        "core/analysis/support_resistance",
        "core/analysis/indicators",
        "core/analysis/scoring",
        "core/analysis/market_health",
        "core/analysis/postmortem",
        "core/analysis/strategies",
        "core/risk_engine",
        "core/position_sizing",
        "core/halal_screening",
        "core/market_data",
        "core/backtest",
        "bot/handlers",
        "bot/i18n",
    ]
    yetishmayotgan = [yol for yol in kutilgan if not (LOYIHA / yol).is_dir()]
    assert not yetishmayotgan, f"Yetishmayotgan papkalar: {yetishmayotgan}"


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
