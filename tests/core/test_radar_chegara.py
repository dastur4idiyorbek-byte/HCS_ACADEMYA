"""MODUL 4.0.0 NING QAT'IY CHEGARALARI — kod matnidan tekshiriladi.

    1. Signal bermaydi: Entry/Stop/TP hisoblaydigan modul import
       qilinmaydi, jadvallarda bunday ustun yo'q.
    2. Modul 3.0.0 ga tegmaydi: `core/watch_panel` dan faqat unlock
       kalendari O'QILADI; `kuzatuv_*` jadvallariga murojaat yo'q.
    3. Botga bog'lanmaydi: loyiha egasining qarori — modul faqat sayt
       uchun. `bot/` radarni bilmaydi, radar `bot/` ni bilmaydi.
    4. Halol modulining `verdict_for()` i ishlatilmaydi (u noma'lum
       coinga HALAL beradi).
"""

from __future__ import annotations

import ast
from pathlib import Path

ILDIZ = Path(__file__).resolve().parents[2]
RADAR = sorted((ILDIZ / "core" / "portlash_radari").glob("*.py"))

TAQIQLANGAN_MODUL = (
    "core.position",
    "core.services",
    "core.risk_engine",
    "core.position_sizing",
    "core.analysis",
    "bot",
)


def _importlar(yol: Path) -> set[str]:
    natija: set[str] = set()
    for tugun in ast.walk(ast.parse(yol.read_text(encoding="utf-8"))):
        if isinstance(tugun, ast.Import):
            natija.update(a.name for a in tugun.names)
        elif isinstance(tugun, ast.ImportFrom) and tugun.module:
            natija.add(tugun.module)
    return natija


def test_radar_fayllari_bor() -> None:
    assert len(RADAR) >= 10


def test_savdo_darajasi_modullari_import_qilinmaydi() -> None:
    for yol in RADAR:
        for imp in _importlar(yol):
            assert not any(imp == t or imp.startswith(f"{t}.") for t in TAQIQLANGAN_MODUL), (
                f"{yol.name} {imp} ni import qilyapti — radar signal bermaydi"
            )


def test_modul_3_dan_faqat_unlock_kalendari_oqiladi() -> None:
    for yol in RADAR:
        for imp in _importlar(yol):
            if imp.startswith("core.watch_panel"):
                assert imp == "core.watch_panel.unlock_manba", f"{yol.name}: {imp}"


def test_kuzatuv_jadvallariga_murojaat_yoq() -> None:
    for yol in RADAR:
        matn = yol.read_text(encoding="utf-8")
        for nom in ("Kuzatuv", "kuzatuv_holatlari", "kuzatuv_skani", "kuzatuv_bozor"):
            assert nom not in matn, f"{yol.name} Modul 3.0.0 jadvaliga tegyapti: {nom}"


def test_verdict_for_ishlatilmaydi() -> None:
    for yol in RADAR:
        assert "verdict_for(" not in yol.read_text(encoding="utf-8").replace(
            "`verdict_for()`", ""
        ), yol.name


def test_radar_jadvallarida_savdo_darajasi_ustuni_yoq() -> None:
    from core.storage.base import Base

    for nom, jadval in Base.metadata.tables.items():
        if not nom.startswith("radar_"):
            continue
        for ustun in jadval.columns:
            past = ustun.name.lower()
            assert not any(
                s in past for s in ("entry", "stop", "tp1", "tp2", "take_profit", "kirish")
            ), f"{nom}.{ustun.name}"


def test_bot_radarga_boglanmagan() -> None:
    """Loyiha egasi: "Botga shart emas, faqat veb uchun" (2026-10-14)."""
    for yol in sorted((ILDIZ / "bot").rglob("*.py")):
        matn = yol.read_text(encoding="utf-8")
        assert "portlash_radari" not in matn, f"{yol.relative_to(ILDIZ)} radarga bog'langan"


def test_radar_alohida_jarayon_sifatida_ishga_tushadi() -> None:
    skript = (ILDIZ / "scripts" / "start.sh").read_text(encoding="utf-8")
    assert "python -m core.portlash_radari" in skript
