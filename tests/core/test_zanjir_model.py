"""XGBoost model skriptining sof qismlari.

`xgboost` va `pandas` `requirements-ml.txt` da — ular FAQAT
o'lchov muhitida o'rnatiladi. Shuning uchun bu testlar ular
bo'lmasa O'TKAZIB YUBORILADI, yiqilmaydi.

Nima uchun baribir yoziladi: `_tayanch_belgisi` — solishtiruvning
adolatliligini belgilaydigan joy. U noto'g'ri bo'lsa, model
"tayanchdan yaxshi" deb ko'rinadi-yu, aslida tayanch noto'g'ri
qurilgan bo'ladi. Bu — o'lchovning eng jimgina xatosi.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("xgboost")

from scripts.zanjir_model import _tayanch_belgisi, _xulosa  # noqa: E402


def test_tayanch_hozirgi_qoidalarni_takrorlaydi() -> None:
    """Tayanch — jonli tizim signal qiladigan qatorlar."""
    jadval = pd.DataFrame(
        [
            # 0: hammasi joyida -> TAYANCH OLADI
            {"zanjir_toliq": 1, "stop_pct": 4.0, "nisbat": 1.5,
             "narx_entry_farq_pct": 2.0, "tp1_pct": 6.0},
            # 1: zanjir uzilgan
            {"zanjir_toliq": 0, "stop_pct": 4.0, "nisbat": 1.5,
             "narx_entry_farq_pct": 2.0, "tp1_pct": 6.0},
            # 2: stop juda yaqin
            {"zanjir_toliq": 1, "stop_pct": 0.8, "nisbat": 1.5,
             "narx_entry_farq_pct": 2.0, "tp1_pct": 6.0},
            # 3: nisbat past
            {"zanjir_toliq": 1, "stop_pct": 4.0, "nisbat": 1.0,
             "narx_entry_farq_pct": 2.0, "tp1_pct": 6.0},
            # 4: narx zonadan pastga tushgan
            {"zanjir_toliq": 1, "stop_pct": 4.0, "nisbat": 1.5,
             "narx_entry_farq_pct": -1.0, "tp1_pct": 6.0},
            # 5: TP1 allaqachon ortda (narx TP1 dan yuqori)
            {"zanjir_toliq": 1, "stop_pct": 4.0, "nisbat": 1.5,
             "narx_entry_farq_pct": 8.0, "tp1_pct": 6.0},
        ]
    )
    belgi = _tayanch_belgisi(jadval)
    assert list(belgi) == [True, False, False, False, False, False]


def test_xulosa_bekor_qatorlarni_savdo_deb_sanamaydi() -> None:
    """`bekor` qatorda natija 0 — u savdo EMAS.

    Aks holda "signal" va "savdo" bir xil bo'lib, g'alaba foizi
    sun'iy ravishda pasayardi."""
    natijalar = pd.Series([0.0, 5.0, -2.0, 0.0, 3.0])
    x = _xulosa(natijalar, "sinov")
    assert x["signal"] == 5
    assert x["savdo"] == 3
    assert x["foydali_pct"] == pytest.approx(200 / 3)
    assert x["pf"] == pytest.approx(8.0 / 2.0)
    assert x["jami_pct"] == pytest.approx(6.0)


def test_xulosa_zararsiz_holatda_pf_cheksiz() -> None:
    """Zarar bo'lmasa PF cheksiz — nolga bo'lish emas."""
    x = _xulosa(pd.Series([2.0, 3.0]), "sinov")
    assert x["pf"] == float("inf")


# --------------------------------------------------------------------------- #
#  Yakuniy xulosa — CHEGARA IMTIHONDAN KEYIN TANLANMASIN
# --------------------------------------------------------------------------- #

#: 2026-09-10 dagi haqiqiy o'lchov (Actions 34469933617).
#: Har bir oyna uchun (savdo, jami_pct), tartib `NOMLAR` bilan bir xil.
OLCHOV_NOMLARI = (
    "TAYANCH (hozirgi qoidalar)",
    "kutilgan foyda >= 0.0%",
    "kutilgan foyda >= 1.5%",
    "kutilgan foyda >= 2.0%",
)
OLCHOV_OYNALARI = (
    ((27, -2.0), (296, -160.5), (25, 8.1), (10, -12.2)),
    ((23, -8.0), (315, 102.4), (35, 7.9), (26, 21.4)),
    ((32, -52.2), (259, -22.0), (34, -43.0), (24, -84.5)),
    ((80, -106.9), (345, -348.6), (38, -67.8), (30, -46.7)),
)


def _oynalar(nomlar, oynalar) -> list[list[dict]]:  # noqa: ANN001
    return [
        [
            {"nom": nom, "savdo": savdo, "jami_pct": jami,
             "signal": 0, "foydali_pct": 0.0, "pf": 0.0, "ortacha_pct": 0.0}
            for nom, (savdo, jami) in zip(nomlar, oyna, strict=True)
        ]
        for oyna in oynalar
    ]


def test_xulosa_har_oynadan_alohida_chegara_tanlamaydi(capsys) -> None:  # noqa: ANN001
    """HAQIQIY XATONING REGRESSIYA TESTI.

    Ilgari xulosa har bir oynaning ENG YAXSHI chegarasini tanlardi.
    Shu sababli 2026-09-10 dagi o'lchov "🟢 Model 4/4 oynada
    tayanchdan yaxshi" deb chiqdi — chegara esa har oynada boshqa
    edi (1.5%, 0.0%, 0.0%, 2.0%). Jonli savdoda chegara OLDINDAN
    qo'yiladi, ya'ni o'sha natijaga erishib bo'lmasdi.

    Bir xil chegara bilan sanalganda bitta ham konfiguratsiya
    foyda bermaydi.
    """
    from scripts.zanjir_model import _yakuniy_xulosa

    _yakuniy_xulosa(_oynalar(OLCHOV_NOMLARI, OLCHOV_OYNALARI))
    chiqish = capsys.readouterr().out

    assert "🟢" not in chiqish, f"foydasiz natija yashil deb ko'rsatildi:\n{chiqish}"
    assert "MANFIY" in chiqish
    # Jami raqamlar bir xil chegara bo'yicha qo'shilsin.
    assert "-428.7" in chiqish, "«kutilgan foyda >= 0.0%» jamisi noto'g'ri"
    assert "-94.8" in chiqish, "«kutilgan foyda >= 1.5%» jamisi noto'g'ri"


def test_xulosa_haqiqiy_foydani_yashil_deydi(capsys) -> None:  # noqa: ANN001
    """Chegara BARCHA oynada tayanchdan yaxshi va jami musbat bo'lsa."""
    from scripts.zanjir_model import _yakuniy_xulosa

    nomlar = ("TAYANCH", "yaxshi chegara")
    oynalar = (
        ((20, -5.0), (20, 30.0)),
        ((20, -3.0), (20, 25.0)),
        ((20, 1.0), (20, 40.0)),
    )
    _yakuniy_xulosa(_oynalar(nomlar, oynalar))
    chiqish = capsys.readouterr().out

    assert "🟢" in chiqish
    assert "yaxshi chegara" in chiqish
