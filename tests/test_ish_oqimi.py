"""GitHub Actions ish oqimining O'ZI to'g'ri sozlanganini tekshiradi.

Nima uchun bu test bor. 2026-09-04 da `olchov: sigim` yugurishi
Actions'da ✅ YASHIL ko'rindi, aslida esa skript traceback bilan
yiqilgan edi. Sabab — `python ... | tee fayl` quvurining chiqish
kodi `tee` niki bo'ladi, ya'ni doim 0.

Bu — o'lchov loyihasida eng xavfli xato turi: natija YO'Q, lekin
tizim "bajarildi" deydi. Shuning uchun sozlama testga bog'landi.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ISH_OQIMI = Path(__file__).resolve().parents[1] / ".github/workflows/zanjir.yml"


def _yukla() -> dict:
    return yaml.safe_load(ISH_OQIMI.read_text(encoding="utf-8"))


def test_pipefail_yoqilgan() -> None:
    """`| tee` Python xatosini YASHIRMASIN."""
    ish = _yukla()["jobs"]["olchov"]
    shell = ish["defaults"]["run"]["shell"]
    assert "pipefail" in shell


def test_yuklash_alohida_qadam_va_shartsiz() -> None:
    """Kesh to'ldirish TANLANGAN o'lchovga bog'liq bo'lmasin.

    Ilgari yuklashni birinchi o'lchov qilardi. `olchov: sigim`
    tanlansa yuklash umuman bo'lmasdi va skript "kesh yo'q" bilan
    yiqilardi.
    """
    qadamlar = _yukla()["jobs"]["olchov"]["steps"]
    yuklash = [q for q in qadamlar if q.get("name") == "Shamlarni yuklash"]
    assert len(yuklash) == 1
    assert "if" not in yuklash[0]
    assert "zanjir_yuklash" in yuklash[0]["run"]


def test_olchov_qadamlari_faqat_keshdan_oqiydi() -> None:
    """Yuklash bitta joyda bo'lsin — o'lchovlar `--offline` yursin."""
    qadamlar = _yukla()["jobs"]["olchov"]["steps"]
    for qadam in qadamlar:
        buyruq = qadam.get("run", "")
        if "scripts.zanjir_" not in buyruq or "zanjir_yuklash" in buyruq:
            continue
        assert "--offline" in buyruq, f"{qadam.get('name')} keshdan o'qimayapti"


def test_kesh_kaliti_unikal_va_prefiksdan_tiklanadi() -> None:
    """Yarim kesh abadiy muzlab qolmasin.

    Kalit unikal bo'lmasa, qisqa yugurish saqlagan yarim kesh
    keyingi yugurishlarda "cache hit" berardi va yetishmagan coin
    HECH QACHON yuklanmasdi.
    """
    qadamlar = _yukla()["jobs"]["olchov"]["steps"]
    kalit_qadam = next(q for q in qadamlar if q.get("id") == "kesh")
    assert "github.run_id" in kalit_qadam["run"]

    tiklash = next(q for q in qadamlar if q.get("id") == "tiklash")
    assert "restore-keys" in tiklash["with"]

    saqlash = next(q for q in qadamlar if q.get("name") == "Sham keshini saqlash")
    assert saqlash["if"].strip() == "always()"
