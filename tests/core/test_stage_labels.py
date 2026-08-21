"""Rad etish bosqichlari uchun odam o'qiydigan nomlar (3.7-band).

Dashboard adminга `classic_ta:zone_position` deb ko'rsatsa, u hech
narsa demaydi. Nomlar `core/pipeline/context.py` da yozilgan, lekin
bosqich kodlari BOSHQA fayllarda (strategiyalar, sikl) yaratiladi —
ya'ni ikkisi bir-biridan ajralib ketishi mumkin va buni faqat ish
paytida sezilardi.

Bu test kodni skanerlab, nomsiz qolgan bosqichni topadi.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.pipeline import ROUTINE_STAGES, STAGE_LABELS, is_routine_stage, stage_label

ILDIZ = Path(__file__).resolve().parents[2]

#: Strategiya bosqichlariga qo'shiladigan, sikl o'zi qo'yadigan kodlar
SIKL_QOSHADIGAN = ("no_setup", "error")


def _strategiya_bosqichlari() -> set[str]:
    """`strategiya_nomi:bosqich` ko'rinishidagi barcha kodlar."""
    topilgan: set[str] = set()
    for fayl in (ILDIZ / "core" / "analysis" / "strategies").glob("*.py"):
        matn = fayl.read_text(encoding="utf-8")
        nomlar = re.findall(r'^\s*name = "([a-z_]+)"', matn, re.MULTILINE)
        if not nomlar:
            continue
        bosqichlar = set(re.findall(r'_reject\(\s*"([a-z_]+)"', matn))
        bosqichlar.update(SIKL_QOSHADIGAN)
        for nom in nomlar:
            topilgan.update(f"{nom}:{bosqich}" for bosqich in bosqichlar)
    return topilgan


def _sikl_bosqichlari() -> set[str]:
    """Sikl o'zi qo'yadigan kodlar — nomli ham, pozitsion ham yoziladi."""
    matn = (ILDIZ / "core" / "pipeline" / "cycle.py").read_text(encoding="utf-8")
    nomli = re.findall(r'stage="([a-z_]+)"', matn)
    pozitsion = re.findall(r'RejectedCandidate\(\s*"[^"]*",\s*"([a-z_]+)"', matn)
    return set(nomli) | set(pozitsion)


def _barcha_bosqichlar() -> set[str]:
    return _strategiya_bosqichlari() | _sikl_bosqichlari()


def test_bosqichlar_topildi() -> None:
    """Skaner ishlayotganini tekshiradi — aks holda test bo'sh o'tardi."""
    bosqichlar = _barcha_bosqichlar()
    assert len(bosqichlar) > 15, f"skaner juda kam bosqich topdi: {bosqichlar}"
    assert "classic_ta:zone_position" in bosqichlar
    assert "threshold" in bosqichlar


@pytest.mark.parametrize("bosqich", sorted(_barcha_bosqichlar()))
def test_har_bir_bosqichning_nomi_bor(bosqich: str) -> None:
    assert bosqich in STAGE_LABELS, (
        f"'{bosqich}' uchun o'zbekcha nom yo'q. "
        "Uni `core/pipeline/context.py` dagi STAGE_LABELS ga qo'shing — "
        "aks holda dashboardda kod nomi ko'rinadi."
    )


def test_ortiqcha_nom_yoq() -> None:
    """Kodda yo'q bosqich uchun nom saqlanib qolmasin."""
    ortiqcha = set(STAGE_LABELS) - _barcha_bosqichlar()
    assert not ortiqcha, (
        f"Bu bosqichlar kodda yo'q, lekin STAGE_LABELS da qolgan: {sorted(ortiqcha)}"
    )


def test_vaqt_shartlari_haqiqiy_bosqichlar() -> None:
    """`ROUTINE_STAGES` da xato yozilgan kod jimgina ishlamay qolardi."""
    assert _barcha_bosqichlar() >= ROUTINE_STAGES
    assert is_routine_stage("opening_range_scalp:window")
    assert not is_routine_stage("classic_ta:zone_position")


def test_nomsiz_bosqich_kodning_ozini_qaytaradi() -> None:
    """0.3-band: nom topilmasa ham dashboard yiqilmasligi kerak."""
    assert stage_label("kelajakdagi:bosqich") == "kelajakdagi:bosqich"
