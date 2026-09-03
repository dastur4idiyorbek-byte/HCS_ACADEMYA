"""O'lchov skriptlarining tuzilishi — ular natijaga TA'SIR QILMASLIGI kerak.

Skript strategiyani o'zgartirsa, o'lchov o'z-o'zini o'lchagan bo'lardi.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.zanjir_ablatsiya import SEZILARSIZ, TEKSHIRUVLAR
from scripts.zanjir_backtest import BLOK_TEKSHIRUVLARI
from scripts.zanjir_umumiy import Olchov, csv_saqla, jadval
from scripts.zanjir_walk_forward import bolaklar

ILDIZ = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
#  Ablatsiya ro'yxati kod bilan MOS kelishi kerak
# --------------------------------------------------------------------------- #


def test_ablatsiya_royxati_16_ta() -> None:
    """4 blok × 4 ichki tekshiruv (2-prompt, 8-qism, 3-band)."""
    assert len(TEKSHIRUVLAR) == 16


def test_ablatsiya_kalitlari_kodda_mavjud() -> None:
    """Nomi noto'g'ri yozilgan kalit JIMGINA hech narsani o'chirmasdi.

    Natijada "bu tekshiruv hissa qo'shmaydi" degan YOLG'ON xulosa
    chiqardi — aslida u umuman o'chirilmagan edi.
    """
    manba = ""
    for papka in ("fundamental", "structure", "zone_quality", "confirmation"):
        for fayl in (ILDIZ / "core" / "analysis" / papka).glob("*.py"):
            manba += fayl.read_text(encoding="utf-8")

    yetishmayotgan = [k for _, k in TEKSHIRUVLAR if f'"{k}"' not in manba]
    assert not yetishmayotgan, f"Kodda topilmadi: {yetishmayotgan}"


def test_ablatsiya_kalitlari_takrorlanmaydi() -> None:
    kalitlar = [k for _, k in TEKSHIRUVLAR]
    assert len(kalitlar) == len(set(kalitlar))


def test_sezilarsiz_chegara_promptdagidek() -> None:
    """Promptda "PF 0.00-0.03 farq qilsa" deyilgan."""
    assert pytest.approx(0.03) == SEZILARSIZ


def test_blok_tekshiruvlari_ablatsiya_bilan_mos() -> None:
    """Bosqichma-bosqich backtest AYNAN shu 16 tani biladi."""
    hammasi = set().union(*BLOK_TEKSHIRUVLARI.values())
    ablatsiya = {k for _, k in TEKSHIRUVLAR}
    # `yangi_coin_naqshi` — 17-chi, faqat yangi coinlarda
    assert ablatsiya <= hammasi
    assert hammasi - ablatsiya == {"yangi_coin_naqshi"}


# --------------------------------------------------------------------------- #
#  Skriptlar strategiyaga tegmaydi
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "skript",
    ["zanjir_backtest.py", "zanjir_ablatsiya.py", "zanjir_walk_forward.py"],
)
def test_skript_config_qiymatlarini_ozgartirmaydi(skript: str) -> None:
    """O'lchov skripti sozlamani QO'LDA o'zgartirmasligi kerak.

    Yagona ruxsat etilgan o'zgarish — `ochirilgan_tekshiruvlar`
    orqali ablatsiya. Boshqasi "o'lchov o'z natijasini yasadi"
    degani bo'lardi.
    """
    manba = (ILDIZ / "scripts" / skript).read_text(encoding="utf-8")
    daraxt = ast.parse(manba)
    for tugun in ast.walk(daraxt):
        if isinstance(tugun, ast.Call):
            nom = getattr(tugun.func, "attr", getattr(tugun.func, "id", ""))
            assert nom != "replace", (
                f"{skript} `dataclasses.replace` ishlatmoqda — "
                "o'lchov sozlamani o'zgartirmasligi kerak"
            )


# --------------------------------------------------------------------------- #
#  Jadval va CSV
# --------------------------------------------------------------------------- #


def _olchov(nom: str = "test", pf: float = 1.5) -> Olchov:
    return Olchov(
        nom=nom, signal=100, foydali_pct=40.0, profit_factor=pf,
        ortacha_pct=0.5, jami_pct=50.0, pasayish_pct=10.0,
    )


def test_jadval_barcha_qatorlarni_chizadi() -> None:
    matn = jadval([_olchov("a"), _olchov("b")])
    assert "a" in matn
    assert "b" in matn
    assert "PF" in matn


def test_cheksiz_pf_belgi_bilan() -> None:
    """Zararsiz variantda PF cheksiz — `inf` deb chizilmasin."""
    assert "∞" in jadval([_olchov(pf=float("inf"))])


def test_csv_saqlanadi(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("scripts.zanjir_umumiy.HISOBOT_PAPKA", tmp_path)
    yol = csv_saqla("sinov.csv", [_olchov()])
    assert yol.exists()
    matn = yol.read_text(encoding="utf-8")
    assert "konfiguratsiya" in matn
    assert "test" in matn


# --------------------------------------------------------------------------- #
#  Walk-forward bo'laklari
# --------------------------------------------------------------------------- #


def test_bolaklar_kesishmaydi() -> None:
    """Bitta savdo ikki oynaga tushmasligi kerak."""
    from datetime import UTC, datetime, timedelta

    vaqtlar = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=i) for i in range(90)]
    qismlar = bolaklar(vaqtlar, 3)
    assert len(qismlar) == 3
    for a, b in zip(qismlar, qismlar[1:], strict=False):
        assert a.oxiri < b.boshi


def test_bolaklar_butun_oynani_qamraydi() -> None:
    from datetime import UTC, datetime, timedelta

    vaqtlar = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=i) for i in range(90)]
    qismlar = bolaklar(vaqtlar, 3)
    assert qismlar[0].boshi == vaqtlar[0]
    assert qismlar[-1].oxiri == vaqtlar[-1]


def test_kam_malumotda_bolak_yoq() -> None:
    from datetime import UTC, datetime

    assert bolaklar([datetime(2024, 1, 1, tzinfo=UTC)], 3) == []
