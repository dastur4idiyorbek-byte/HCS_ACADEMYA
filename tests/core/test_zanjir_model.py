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
