"""XGBoost dataseti — ustunlar va yorliqlar.

BU FAYL BIR SABABDAN TUG'ILDI. Birinchi yugurish GitHub Actions'da
yiqildi va sabab shu yerda sinalmagan edi: alternativ yo'l g'olib
chiqqanda blokka `alternativ:<nom>` degan YANGI tekshiruv
qo'shiladi, ya'ni ba'zi qatorlarda qo'shimcha ustun bo'ladi.
`csv.DictWriter` esa birinchi qatorning kalitlarini olib, keyingi
qatorda ortiqcha kalit ko'rsa yiqiladi.

Sun'iy ma'lumotda alternativ hech qachon g'olib chiqmadi —
shuning uchun mahalliy sinov o'tib ketdi va xato faqat haqiqiy
bozorda ko'rindi.
"""

from __future__ import annotations

import csv
import math
import random
from datetime import UTC, datetime, timedelta

from core.backtest.dataset import Dataset
from core.config.loader import load_config
from core.domain.models import Candle
from scripts.zanjir_dataset import Qator, _csv_yoz, _ustun_nomi, _yigish

BOSH = datetime(2024, 1, 1, tzinfo=UTC)


def _seriya(n: int, qadam: timedelta) -> list[Candle]:
    rnd = random.Random(11)
    narx = 100.0
    out = []
    for i in range(n):
        narx *= 1 + 0.0015 + 0.02 * math.sin(i / 9) + rnd.uniform(-0.012, 0.012)
        out.append(
            Candle(
                open_time=BOSH + qadam * i,
                open=narx,
                high=narx * 1.01,
                low=narx * 0.99,
                close=narx,
                volume=1000.0,
            )
        )
    return out


# --------------------------------------------------------------------------- #
#  Ustun nomlari
# --------------------------------------------------------------------------- #


def test_ikki_nuqta_ustun_nomidan_chiqariladi() -> None:
    """`alternativ:qosh_tub` -> `alternativ_qosh_tub`.

    Ikki nuqta ba'zi jadval dasturlarida ustunni bo'lib yuboradi.
    """
    assert _ustun_nomi("alternativ:Qo'sh tub") == "alternativ_qo'sh_tub"
    assert _ustun_nomi("Trend / Flag") == "trend___flag"
    assert _ustun_nomi("RSI-14") == "rsi_14"


# --------------------------------------------------------------------------- #
#  CSV — HAR XIL ustunli qatorlar (aynan Actions'da yiqilgan holat)
# --------------------------------------------------------------------------- #


def test_har_xil_ustunli_qatorlar_yoziladi(tmp_path) -> None:  # noqa: ANN001
    """Birinchi qatorda yo'q ustun keyingi qatorda paydo bo'lsa ham yiqilmasin."""
    qatorlar = [
        Qator({"symbol": "BTC", "vaqt": "2024-01-01", "t_a": 1.0}, "stop", -2.0),
        # Bu qatorda QO'SHIMCHA ustun bor — alternativ g'olib chiqqan holat
        Qator(
            {"symbol": "ETH", "vaqt": "2024-01-02", "t_a": 0.0, "t_alternativ_b": 1.0},
            "tp2",
            +5.0,
        ),
    ]
    yol = tmp_path / "sinov.csv"
    ustunlar = _csv_yoz(qatorlar, yol)

    assert "t_alternativ_b" in ustunlar
    qatorlar_ocgan = list(csv.DictReader(yol.open(encoding="utf-8")))
    assert len(qatorlar_ocgan) == 2
    # Birinchi qatorda o'sha ustun YO'Q edi -> "-1.0" ("o'lchanmadi")
    assert qatorlar_ocgan[0]["t_alternativ_b"] == "-1.0"
    assert qatorlar_ocgan[1]["t_alternativ_b"] == "1.0"


def test_ustun_tartibi_qatiy(tmp_path) -> None:  # noqa: ANN001
    """Ikki yugurish bir xil tartib bersin — aks holda CSV larni
    solishtirib bo'lmaydi."""
    qatorlar = [Qator({"symbol": "BTC", "vaqt": "x", "t_b": 1.0, "t_a": 0.0}, "stop", 0.0)]
    birinchi = _csv_yoz(qatorlar, tmp_path / "a.csv")
    ikkinchi = _csv_yoz(qatorlar, tmp_path / "b.csv")
    assert birinchi == ikkinchi
    assert birinchi[:2] == ["symbol", "vaqt"]
    assert birinchi[-3:] == ["yorliq", "natija_pct", "yutdi"]


# --------------------------------------------------------------------------- #
#  Yig'ish
# --------------------------------------------------------------------------- #


def test_dataset_yigiladi_va_yorliq_beriladi() -> None:
    """Uchidan uchigacha: sun'iy bozorda qatorlar chiqsin."""
    config = load_config()
    z = config.zanjir
    ds = Dataset()
    for sym in ("BTC", "ETH"):
        ds.add(sym, z.timeframelar.asosiy, _seriya(300, timedelta(days=1)))
        ds.add(sym, z.timeframelar.tasdiq, _seriya(1200, timedelta(hours=6)))

    qatorlar, tashlandi = _yigish(config, ds, ["BTC", "ETH"], None)

    assert qatorlar, "bitta ham qator yig'ilmadi"
    assert tashlandi == 0
    # Yorliq har doim ma'lum bo'lishi kerak — "nomalum" tashlanadi
    assert all(q.yorliq != "nomalum" for q in qatorlar)
    # Zanjir ustunlari bor
    birinchi = qatorlar[0].ustunlar
    assert "zanjir_toliq" in birinchi
    assert "blok1_kuch" in birinchi
    assert "narx_entry_farq_pct" in birinchi
