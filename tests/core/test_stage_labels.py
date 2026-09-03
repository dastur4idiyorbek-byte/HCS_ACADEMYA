"""Rad etish bosqichlari uchun odam o'qiydigan nomlar (3.7-band).

Dashboard adminga `classic_ta:zone_position` deb ko'rsatsa, u hech
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
        # Ikki nuqta ham qamrab olinadi: `_reject("levels:stop_too_close")`
        # kabi aniqlashtirilgan kodlar ham nomlanishi kerak.
        bosqichlar = set(re.findall(r'_reject\(\s*"([a-z0-9_:]+)"', matn))
        bosqichlar.update(SIKL_QOSHADIGAN)
        for nom in nomlar:
            topilgan.update(f"{nom}:{bosqich}" for bosqich in bosqichlar)
    return topilgan


def _sikl_bosqichlari() -> set[str]:
    """Sikl o'zi qo'yadigan kodlar — nomli ham, pozitsion ham yoziladi."""
    matn = (ILDIZ / "core" / "pipeline" / "cycle.py").read_text(encoding="utf-8")
    nomli = re.findall(r'stage="([a-z0-9_]+)"', matn)
    pozitsion = re.findall(r'RejectedCandidate\(\s*"[^"]*",\s*"([a-z0-9_]+)"', matn)
    return set(nomli) | set(pozitsion)


def _risk_bosqichlari() -> set[str]:
    """`risk_engine:{sabab}` — sikl `BlockReason` dan quradi."""
    from core.domain.enums import BlockReason

    matn = (ILDIZ / "core" / "pipeline" / "cycle.py").read_text(encoding="utf-8")
    if 'f"risk_engine:{' not in matn:
        return set()

    bosqichlar = {f"risk_engine:{sabab.value}" for sabab in BlockReason}
    # Sabab ro'yxati bo'sh bo'lsa sikl oddiy "risk_engine" yozadi —
    # zaxira yo'l ham nomlanishi kerak.
    if '"risk_engine"' in matn:
        bosqichlar.add("risk_engine")
    return bosqichlar


def _daraja_bosqichlari() -> set[str]:
    """`levels:*` — `build_levels()` qaytaradigan aniqlashtirilgan bosqichlar.

    QAYSI STRATEGIYAGA TEGISHLI — kod o'zi aytadi. Ilgari bu yerda
    `classic_ta` qattiq yozilgan edi va darajalarni ishlatadigan
    ikkinchi strategiya qo'shilganda ro'yxat jimgina eskirardi.
    Endi skaner `_reject(<narsa>.stage)` yozuvini qidiradi: kim
    `LevelResult.stage` ni uzatsa, o'shanga barcha `levels:*`
    bosqichlari tegishli.
    """
    import re as _re

    matn = (ILDIZ / "core" / "analysis" / "scoring" / "levels.py").read_text(encoding="utf-8")
    # Barcha `"levels:*"` satrlari — shartli ifodaning ikkala tarmog'i ham
    # topilishi kerak (`A if shart else B`).
    topilgan = set(_re.findall(r'"(levels:[a-z0-9_]+)"', matn))
    # `LevelResult.stage` ning standart qiymati ham ishlatiladi: support
    # topilmagan yoki TP qurilmagan holatlar uni o'zgartirmaydi.
    topilgan.add("levels")

    natija: set[str] = set()
    for fayl in (ILDIZ / "core" / "analysis" / "strategies").glob("*.py"):
        matn_s = fayl.read_text(encoding="utf-8")
        if not _re.search(r"_reject\(\s*[a-z_]+\.stage", matn_s):
            continue
        for nom in _re.findall(r'^\s*name = "([a-z_]+)"', matn_s, _re.MULTILINE):
            natija.update(f"{nom}:{b}" for b in topilgan)
    return natija


def _kirish_bosqichlari() -> set[str]:
    """Kirishga ruxsat bermaslik sabablari — `Scorer` dan keladi.

    Sikl ularni `stage=element.rejection` deb yozadi, ya'ni kodda
    satr sifatida ko'rinmaydi. Manba `KIRISH_RAD_SABABLARI` —
    `risk_engine:{BlockReason}` bilan bir xil naqsh.
    """
    from core.analysis.scoring.scorer import KIRISH_RAD_SABABLARI

    matn = (ILDIZ / "core" / "pipeline" / "cycle.py").read_text(encoding="utf-8")
    if "element.rejection" not in matn:
        return set()
    return set(KIRISH_RAD_SABABLARI)


def _barcha_bosqichlar() -> set[str]:
    return (
        _strategiya_bosqichlari()
        | _sikl_bosqichlari()
        | _risk_bosqichlari()
        | _daraja_bosqichlari()
        | _kirish_bosqichlari()
    )


def test_skaner_raqamli_nomni_ham_koradi() -> None:
    """Skanerning O'ZIDAGI teshik.

    Ilgari ifodalar faqat `[a-z_]` ni qabul qilardi, ya'ni ichida
    RAQAM bo'lgan bosqich (`levels:tp2_no_structure`) skanerga
    ko'rinmasdi. Nomsiz qolsa ham test jim o'tardi — himoyaning
    o'zi teshik edi.
    """
    assert "classic_ta:levels:tp2_no_structure" in _barcha_bosqichlar()


def test_bosqichlar_topildi() -> None:
    """Skaner ishlayotganini tekshiradi — aks holda test bo'sh o'tardi."""
    bosqichlar = _barcha_bosqichlar()
    assert len(bosqichlar) > 15, f"skaner juda kam bosqich topdi: {bosqichlar}"
    assert "classic_ta:zone_position" in bosqichlar
    assert "threshold" in bosqichlar
    assert "setup_contract" in bosqichlar, (
        "Sifat darvozasining rad etish sababi ham nomlanishi kerak — "
        "aks holda dashboard 'ball past' deb noto'g'ri sabab ko'rsatadi"
    )
    assert "risk_engine:correlation" in bosqichlar, (
        "Risk Engine sabablari ham nomlanishi kerak — aks holda dashboard "
        "13 ta qoidani bitta qatorga yig'ib, sababni yashiradi"
    )


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
