"""Migratsiyalar model ta'rifi bilan mos kelishini tekshiradi.

Nima uchun bu kerak: ishlab chiqishda jadvallar `create_all` bilan
yaratiladi, serverda esa `alembic upgrade head` bilan. Ikkalasi ajralib
ketsa, natija eng yomon turdagi xato bo'ladi — testlar yashil, server
buzuq. Bu test aynan shu ajralishni ushlaydi.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

from core.storage import Database

ILDIZ = Path(__file__).resolve().parents[2]
ALEMBIC = ILDIZ / ".venv" / "bin" / "alembic"


def _sxema(db_yoli: Path) -> dict:
    """Jadval -> ustunlar va indekslar (alembic o'z jadvalisiz)."""
    ulanish = sqlite3.connect(db_yoli)
    try:
        natija: dict = {}
        jadvallar = sorted(
            nom for (nom,) in ulanish.execute(
                "select name from sqlite_master where type='table'"
            )
            if not nom.startswith(("alembic", "sqlite_"))
        )
        for nom in jadvallar:
            natija[nom] = {
                "ustunlar": {
                    qator[1]: (qator[2], bool(qator[3]), qator[5])
                    for qator in ulanish.execute(f"PRAGMA table_info('{nom}')")
                },
                "indekslar": sorted(
                    qator[1]
                    for qator in ulanish.execute(f"PRAGMA index_list('{nom}')")
                    if not qator[1].startswith("sqlite_")
                ),
            }
        return natija
    finally:
        ulanish.close()


@pytest.mark.skipif(not ALEMBIC.is_file(), reason="alembic o'rnatilmagan")
@pytest.mark.asyncio
async def test_migratsiya_modellar_bilan_bir_xil_sxema_beradi(tmp_path) -> None:  # noqa: ANN001
    """`alembic upgrade head` va `create_all` bir xil natija berishi kerak.

    Farq chiqsa — model o'zgartirilgan, lekin migratsiya yozilmagan.
    Tuzatish: `alembic revision --autogenerate -m "..."`.
    """
    modellardan = tmp_path / "modellar.db"
    migratsiyadan = tmp_path / "migratsiya.db"

    await Database(f"sqlite+aiosqlite:///{modellardan}").init_models()

    natija = subprocess.run(
        [str(ALEMBIC), "upgrade", "head"],
        cwd=ILDIZ,
        env={**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{migratsiyadan}"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert natija.returncode == 0, f"alembic upgrade muvaffaqiyatsiz:\n{natija.stderr}"

    kutilgan = _sxema(modellardan)
    olingan = _sxema(migratsiyadan)

    assert kutilgan, "modellardan birorta jadval yaratilmadi"
    assert olingan == kutilgan, (
        "Migratsiya modellardan farq qiladi — yangi migratsiya yozing:\n"
        "  alembic revision --autogenerate -m \"nima o'zgardi\"\n"
        f"faqat modellarda: {sorted(set(kutilgan) - set(olingan))}\n"
        f"faqat migratsiyada: {sorted(set(olingan) - set(kutilgan))}"
    )


@pytest.mark.skipif(not ALEMBIC.is_file(), reason="alembic o'rnatilmagan")
@pytest.mark.asyncio
async def test_create_all_dan_keyin_upgrade_xato_bermaydi(tmp_path) -> None:  # noqa: ANN001
    """`create_all` bilan yaratilgan baza keyin yangilanishi kerak.

    Tuzoq: `create_all` jadvallarni yaratadi, lekin `alembic_version` ni
    to'ldirmaydi. Belgilanmasa, serverdagi birinchi `alembic upgrade head`
    noldan boshlashga urinadi va "jadval allaqachon mavjud" deb yiqiladi —
    ya'ni botni umuman yangilab bo'lmasdi.
    """
    db_yoli = tmp_path / "mavjud.db"
    await Database(f"sqlite+aiosqlite:///{db_yoli}").init_models()

    natija = subprocess.run(
        [str(ALEMBIC), "upgrade", "head"],
        cwd=ILDIZ,
        env={**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_yoli}"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert natija.returncode == 0, (
        f"mavjud bazani yangilab bo'lmadi:\n{natija.stderr}"
    )

    ulanish = sqlite3.connect(db_yoli)
    try:
        versiya = ulanish.execute("SELECT version_num FROM alembic_version").fetchone()
    finally:
        ulanish.close()
    assert versiya is not None, "`alembic_version` belgilanmagan"


@pytest.mark.skipif(not ALEMBIC.is_file(), reason="alembic o'rnatilmagan")
def test_migratsiyalar_ilova_kodini_import_qilmaydi() -> None:
    """Migratsiyalar muzlatilgan tarix — ular `core.*` ga tayanmasligi kerak.

    Aks holda modellar ko'chirilganda yoki o'zgartirilganda ESKI
    migratsiyalar ishlamay qoladi va serverni yangilab bo'lmaydi.
    """
    versiyalar = sorted((ILDIZ / "migrations" / "versions").glob("*.py"))
    assert versiyalar, "birorta migratsiya topilmadi"

    for fayl in versiyalar:
        matn = fayl.read_text(encoding="utf-8")
        assert "core.storage" not in matn, (
            f"{fayl.name} ilova kodiga bog'langan — `migrations/env.py` dagi "
            "`_render_item` standart SQLAlchemy tipini yozishi kerak"
        )


def test_bir_dona_bosh_migratsiya() -> None:
    """Ikki `head` bo'lsa `upgrade head` xato beradi (branch chalkashligi)."""
    versiyalar = sorted((ILDIZ / "migrations" / "versions").glob("*.py"))
    assert versiyalar, "birorta migratsiya topilmadi"

    barcha_id = set()
    ota_id = set()
    for fayl in versiyalar:
        matn = fayl.read_text(encoding="utf-8")
        for qator in matn.splitlines():
            if qator.startswith("revision: str ="):
                barcha_id.add(qator.split("=", 1)[1].strip().strip("\"'"))
            elif qator.startswith("down_revision: "):
                qiymat = qator.split("=", 1)[1].strip().strip("\"'")
                if qiymat != "None":
                    ota_id.add(qiymat)

    boshlar = barcha_id - ota_id
    assert len(boshlar) == 1, f"bitta `head` bo'lishi kerak, topildi: {sorted(boshlar)}"

