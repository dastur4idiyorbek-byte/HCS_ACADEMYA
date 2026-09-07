"""Alternativ zanjir — zaif blokni qutqarish va alternativ deteksiyalar."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.alternatives import (
    blok_tasnifi,
    hajm_sakrashi,
    oldingi_swing_zona,
    qayta_sinov,
    qosh_tub_topish,
    qutqar,
    tez_harakat,
    trend_flag,
    zanjir_yur_alternativ,
)
from core.analysis.alternatives.natija import AlternativNatija
from core.analysis.chain import ZanjirKirish
from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.analysis.turlar import blok, ha, malumot_yoq, yoq
from core.domain.models import Candle

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(
    i: int,
    o: float,
    h: float,
    low: float,
    c: float,
    hajm: float = 1000.0,
) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(days=i),
        open=o,
        high=h,
        low=low,
        close=c,
        volume=hajm,
    )


# --------------------------------------------------------------------------- #
#  Tasnif: KUCHLI / ZAIF / BO'SH / OLCHANMADI
# --------------------------------------------------------------------------- #


def test_tasnif_kuchli_zaif_bosh() -> None:
    assert blok_tasnifi(blok("B", [ha("a"), ha("b"), yoq("c"), yoq("d")])) == "kuchli"
    assert blok_tasnifi(blok("B", [ha("a"), yoq("b"), yoq("c"), yoq("d")])) == "zaif"
    assert blok_tasnifi(blok("B", [yoq("a"), yoq("b"), yoq("c"), yoq("d")])) == "bosh"


def test_tasnif_bitta_olchangan_ijobiy_kuchli() -> None:
    """1/1 — barcha o'lchanganlar ijobiy, bu zaif EMAS (ma'lumot yo'qligi jazosi yo'q)."""
    b = blok("B", [ha("a"), malumot_yoq("b"), malumot_yoq("c")])
    assert blok_tasnifi(b) == "kuchli"


def test_tasnif_olchanmadi() -> None:
    b = blok("B", [malumot_yoq("a"), malumot_yoq("b")])
    assert blok_tasnifi(b) == "olchanmadi"


# --------------------------------------------------------------------------- #
#  Qutqarish: zaif blok + alternativlar
# --------------------------------------------------------------------------- #


def test_qutqar_zaifni_qutqaradi() -> None:
    zaif = blok("B", [ha("a"), yoq("b"), yoq("c"), yoq("d")])
    natija, alt = qutqar(zaif, [AlternativNatija("flag", True, "trend")])
    assert natija.otdi
    assert natija.kuch == 2  # 1 asosiy + 1 alternativ
    assert alt is not None and alt.nom == "flag"
    assert any(t.nom == "alternativ:flag" for t in natija.tekshiruvlar)


def test_qutqar_hammasi_sinsa_bosh() -> None:
    zaif = blok("B", [ha("a"), yoq("b"), yoq("c"), yoq("d")])
    natija, alt = qutqar(
        zaif,
        [AlternativNatija("flag", False), AlternativNatija("tub", False)],
    )
    assert not natija.otdi
    assert alt is None


def test_qutqar_kuchliga_tegmaydi() -> None:
    kuchli = blok("B", [ha("a"), ha("b"), yoq("c"), yoq("d")])
    natija, alt = qutqar(kuchli, [AlternativNatija("flag", True)])
    assert natija is kuchli
    assert alt is None


def test_qutqar_ketma_ket_birinchi_otgan() -> None:
    zaif = blok("B", [ha("a"), yoq("b"), yoq("c"), yoq("d")])
    natija, alt = qutqar(
        zaif,
        [
            AlternativNatija("bir", False),
            AlternativNatija("ikki", True, "ikkinchi o'tdi"),
            AlternativNatija("uch", True),
        ],
    )
    assert alt is not None and alt.nom == "ikki"
    assert "alternativ:ikki" in [t.nom for t in natija.tekshiruvlar]


def test_qutqar_ochirilganni_sakraydi() -> None:
    zaif = blok("B", [ha("a"), yoq("b"), yoq("c"), yoq("d")])
    natija, alt = qutqar(
        zaif,
        [AlternativNatija("bir", True), AlternativNatija("ikki", False)],
        ochirilgan=frozenset({"bir"}),
    )
    assert alt is None
    assert not natija.otdi


# --------------------------------------------------------------------------- #
#  Alternativ deteksiyalar
# --------------------------------------------------------------------------- #


def test_qosh_tub_topiladi() -> None:
    nuqtalar = [
        Swing(SwingTuri.PAST, 100.0, BOSH, 0),
        Swing(SwingTuri.YUQORI, 120.0, BOSH, 5),
        Swing(SwingTuri.PAST, 100.5, BOSH, 10),
    ]
    tub = qosh_tub_topish(nuqtalar)
    assert tub is not None
    assert tub.tub_narx == pytest.approx(100.0)
    assert tub.boyin_narx == pytest.approx(120.0)


def test_qosh_tub_uzoq_tublar_rad() -> None:
    nuqtalar = [
        Swing(SwingTuri.PAST, 100.0, BOSH, 0),
        Swing(SwingTuri.YUQORI, 120.0, BOSH, 5),
        Swing(SwingTuri.PAST, 110.0, BOSH, 10),  # 10% farq — tub emas
    ]
    assert qosh_tub_topish(nuqtalar) is None


def test_trend_flag_hl_trend() -> None:
    nuqtalar = [
        Swing(SwingTuri.PAST, 100.0, BOSH, 0),
        Swing(SwingTuri.YUQORI, 120.0, BOSH, 5),
        Swing(SwingTuri.PAST, 110.0, BOSH, 10),  # higher low
    ]
    shams = [sham(i, 100, 105, 95, 100) for i in range(15)]
    shams[-1] = sham(14, 115, 118, 112, 116)  # trend chizig'idan yuqori
    assert trend_flag(shams, nuqtalar)


def test_trend_flag_higher_low_kerak() -> None:
    nuqtalar = [
        Swing(SwingTuri.PAST, 100.0, BOSH, 0),
        Swing(SwingTuri.PAST, 90.0, BOSH, 10),  # lower low
    ]
    shams = [sham(i, 100, 105, 95, 100) for i in range(15)]
    assert not trend_flag(shams, nuqtalar)


def test_oldingi_swing_zona() -> None:
    nuqtalar = [
        Swing(SwingTuri.YUQORI, 120.0, BOSH, 5),
        Swing(SwingTuri.PAST, 100.0, BOSH, 10),
    ]
    zona = oldingi_swing_zona(nuqtalar)
    assert zona is not None
    assert zona.past == pytest.approx(99.0)
    assert zona.yuqori == pytest.approx(101.0)


def test_hajm_sakrashi() -> None:
    shams = [sham(i, 100, 105, 95, 100, hajm=1000.0) for i in range(30)]
    shams[-1] = sham(29, 100, 105, 95, 100, hajm=5000.0)
    assert hajm_sakrashi(shams)


def test_hajm_sakrashi_kam_shamda_false() -> None:
    shams = [sham(i, 100, 105, 95, 100, hajm=9999.0) for i in range(5)]
    assert not hajm_sakrashi(shams)


def test_tez_harakat() -> None:
    shams = [sham(i, 100, 103, 97, 100) for i in range(20)]
    shams[-1] = sham(19, 100, 115, 95, 110)
    assert tez_harakat(shams)


def test_qayta_sinov() -> None:
    nuqtalar = [Swing(SwingTuri.YUQORI, 110.0, BOSH, 3)]
    shams = [sham(i, 100, 105, 95, 100) for i in range(10)]
    shams[4] = sham(4, 105, 115, 104, 112)   # BOS: close 112 > 110
    shams[5] = sham(5, 112, 113, 109, 111)   # retest: low 109 <= 110
    shams[-1] = sham(9, 111, 114, 110.5, 113)
    assert qayta_sinov(shams, nuqtalar)


# --------------------------------------------------------------------------- #
#  Zanjir integratsiyasi
# --------------------------------------------------------------------------- #


def test_flat_holatda_strukturada_uziladi() -> None:
    """Yassi narx — struktura yo'q, zanjir 2-blokda uziladi (asosiy zanjir kabi)."""
    natija = zanjir_yur_alternativ(
        ZanjirKirish(symbol="TEST", shamlar=[sham(i, 100, 100, 100, 100) for i in range(50)])
    )
    assert natija.zanjir.uzildi_blokda == "Struktura"


def test_bosh_fundamental_zanjirni_uzmaydi() -> None:
    natija = zanjir_yur_alternativ(
        ZanjirKirish(symbol="TEST", shamlar=[sham(i, 100, 105, 95, 100) for i in range(50)])
    )
    assert natija.zanjir.uzildi_blokda != "Fundamental"
