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


# --------------------------------------------------------------------------- #
#  Xulosa YASHIRMASLIGI kerak
# --------------------------------------------------------------------------- #


def test_walk_forward_chetlatilgan_oynani_aytadi(capsys) -> None:  # noqa: ANN001
    """Kam savdoli oyna xulosadan chiqariladi, lekin YASHIRILMAYDI.

    Bir marta bu funksiya uchinchi oynani (7 savdo, PF 0.59) jimgina
    tashlab, "barcha oynada PF ≥ 1.0" deb yozgan edi — o'z jadvaliga
    zid gap.
    """
    from scripts.zanjir_walk_forward import _xulosa

    _xulosa([
        Olchov("oyna 1", 21, 47.6, 1.72, 1.98, 41.5, 17.3),
        Olchov("oyna 2", 16, 56.2, 2.35, 3.00, 48.0, 21.4),
        Olchov("oyna 3", 7, 42.9, 0.59, -1.00, -7.0, 9.8),
    ])
    chiqish = capsys.readouterr().out

    assert "oyna 3" in chiqish
    assert "0.59" in chiqish
    # Eski, YOLG'ON da'vo qaytmasin
    assert "🟢 Barcha oynada" not in chiqish
    # Va o'quvchi chetlatish bo'lganini bilsin
    assert "DIQQAT" in chiqish


def test_ablatsiya_kam_savdoda_xulosa_chiqarmaydi(capsys) -> None:  # noqa: ANN001
    """35 savdoda "hissa qo'shmaydi" degan gap tasodifdan farq qilmaydi."""
    from scripts.zanjir_ablatsiya import ISHONCHLI_SAVDO, _xulosa

    _xulosa(
        Olchov("TAYANCH", 35, 48.6, 1.83, 2.10, 73.5, 30.7),
        [Olchov("— 1.1", 35, 48.6, 1.83, 2.10, 73.5, 30.7)],
    )
    chiqish = capsys.readouterr().out

    assert str(ISHONCHLI_SAVDO) in chiqish
    assert "HISSA QO'SHMAYDI" not in chiqish


def test_rad_sababi_raqamsiz_guruhlanadi() -> None:
    """Ansiz voronka o'nlab "1 × ..." qatoriga aylanardi."""
    from core.backtest.zanjir_engine import _sabab_turi

    assert _sabab_turi("stop juda yaqin (2.60%)") == "stop juda yaqin"
    assert _sabab_turi("TP1/Stop nisbati past (0.71)") == "TP1/Stop nisbati past"
    assert _sabab_turi(None) == "nomalum"
