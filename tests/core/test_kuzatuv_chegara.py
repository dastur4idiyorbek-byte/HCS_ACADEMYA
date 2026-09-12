"""KUZATUV MODULINING IKKI QAT'IY CHEGARASI.

Bu testlar KOD MATNINI o'qiydi, chaqiruv natijasini emas. Sabab:
chegara "hozir ishlayaptimi" degan savol emas, "buzish MUMKINMI"
degan savol. Yangi fayl qo'shilganda ham u avtomatik tekshiriladi.

    1. Entry / Stop / TP hech qayerda hisoblanmaydi (9-prompt,
       0-qism va 6-qism: "QAT'IY CHEGARA, o'zgarmas")
    2. Rejim A (`block_chain_engine`) kuzatuv modulidan
       chaqirilmaydi — ikki rejim bir-biriga aralashmaydi
"""

from __future__ import annotations

import ast
from pathlib import Path

ILDIZ = Path(__file__).resolve().parents[2]

#: Kuzatuv moduli qaysi fayllardan iborat.
KUZATUV_FAYLLARI = (
    *sorted((ILDIZ / "core" / "watch_panel").glob("*.py")),
    ILDIZ / "core" / "analysis" / "observation_mode.py",
    # Filtr `analysis` ichida turadi (arxitektura qavati), lekin
    # kuzatuv modulining qismi — chegara unga ham tegishli.
    ILDIZ / "core" / "analysis" / "structure" / "uptrend_filter.py",
)

#: Savdo darajasini hisoblaydigan hamma narsa.
TAQIQLANGAN_MODUL = (
    "core.position.entry_stop_tp",
    "core.position",
    "core.services.kirish_rejasi",
    "core.risk_engine",
)

#: Bu nomlar chaqirilsa — daraja hisoblanyapti degani.
TAQIQLANGAN_NOM = (
    "darajalar_qur",
    "signal_levels",
    "decide_entry_plan",
)

#: Rejim A — kuzatuv moduliga kirmasligi kerak.
REJIM_A = (
    "core.analysis.chain.block_chain_engine",
    "core.analysis.chain",
    "core.services.zanjir_sikl",
)


def _daraxt(yol: Path) -> ast.Module:
    return ast.parse(yol.read_text(encoding="utf-8"), filename=str(yol))


def _importlar(daraxt: ast.Module) -> set[str]:
    natija: set[str] = set()
    for tugun in ast.walk(daraxt):
        if isinstance(tugun, ast.Import):
            natija.update(a.name for a in tugun.names)
        elif isinstance(tugun, ast.ImportFrom) and tugun.module:
            natija.add(tugun.module)
            natija.update(f"{tugun.module}.{a.name}" for a in tugun.names)
    return natija


def _chaqiriqlar(daraxt: ast.Module) -> set[str]:
    natija: set[str] = set()
    for tugun in ast.walk(daraxt):
        if not isinstance(tugun, ast.Call):
            continue
        nishon = tugun.func
        if isinstance(nishon, ast.Name):
            natija.add(nishon.id)
        elif isinstance(nishon, ast.Attribute):
            natija.add(nishon.attr)
    return natija


def test_fayllar_topildi() -> None:
    """Ro'yxat bo'sh bo'lib qolsa, qolgan testlar YOLG'ON yashil beradi."""
    assert len(KUZATUV_FAYLLARI) >= 2
    for yol in KUZATUV_FAYLLARI:
        assert yol.exists(), yol


def test_entry_stop_tp_import_qilinmaydi() -> None:
    for yol in KUZATUV_FAYLLARI:
        topilgan = _importlar(_daraxt(yol))
        for taqiq in TAQIQLANGAN_MODUL:
            xato = [i for i in topilgan if i == taqiq or i.startswith(taqiq + ".")]
            assert not xato, f"{yol.name}: savdo darajasi moduli import qilingan — {xato}"


def test_daraja_hisoblovchi_funksiya_chaqirilmaydi() -> None:
    for yol in KUZATUV_FAYLLARI:
        topilgan = _chaqiriqlar(_daraxt(yol))
        xato = topilgan & set(TAQIQLANGAN_NOM)
        assert not xato, f"{yol.name}: daraja hisoblovchi chaqirilgan — {xato}"


def test_rejim_a_chaqirilmaydi() -> None:
    """Kuzatuv moduli zanjir dvigatelini ISHLATMAYDI.

    `ZanjirKirish` kabi TIP import qilinishi ham taqiqlangan: bu
    ikki modulni bir-biriga bog'lardi va Rejim A o'zgarganda
    kuzatuv paneli jimgina buzilardi.
    """
    for yol in KUZATUV_FAYLLARI:
        topilgan = _importlar(_daraxt(yol))
        for taqiq in REJIM_A:
            xato = [i for i in topilgan if i == taqiq or i.startswith(taqiq + ".")]
            assert not xato, f"{yol.name}: Rejim A import qilingan — {xato}"


def test_blok_fayllari_ozgarmagan_holda_chaqiriladi() -> None:
    """To'rt blok funksiyasi AYNAN o'z joyidan import qilinadi.

    Agar kimdir blok mantig'ini kuzatuv moduliga KO'CHIRIB yozsa,
    ikki nusxa paydo bo'lardi va ular asta ajralib ketardi. Test
    import borligini talab qiladi — ya'ni mantiq bitta joyda.
    """
    yol = ILDIZ / "core" / "analysis" / "observation_mode.py"
    topilgan = _importlar(_daraxt(yol))
    for kerak in (
        "core.analysis.fundamental.fundamental_block.fundamental_blok",
        "core.analysis.structure.structure_block.struktura_blok",
        "core.analysis.zone_quality.zone_block.zona_blok",
        "core.analysis.confirmation.confirmation_block.tasdiqlash_blok",
    ):
        assert kerak in topilgan, f"blok funksiyasi import qilinmagan: {kerak}"
