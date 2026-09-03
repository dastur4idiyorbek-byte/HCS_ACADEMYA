"""O'LCHOVNING O'ZI to'g'ri o'lchayaptimi (audit, 1-bosqich).

Bu fayl savdo mantig'ini emas, ASBOBNI tekshiradi. Uchta topilma
qulflanadi:

    1.1  BTC ning 24 soatlik o'zgarishi jonli tizim va backtestda
         AYNAN bir joydan hisoblanadi
    1.2  voronka hech bir rad etishni tashlab yubormaydi
    1.3  `LevelResult` ning `stage` maydoniga bool tushib qolmaydi

Uchalasi ham bitta turkumdan: ular natijani emas, natijaning
O'LCHOVINI buzadi. Bunday xato eng qimmati — u yolg'on raqamni
haqiqat qilib ko'rsatadi.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from core.backtest.engine import (
    BOSHQA_BOSQICH,
    VORONKA_TARTIBI,
    BacktestResult,
    voronka_kaliti,
)
from core.config import load_config
from core.domain.models import Candle
from core.pipeline.context import STAGE_LABELS
from core.risk_engine.btc_filter import btc_ozgarishi_24h

# --------------------------------------------------------------------------- #
#  1.1 — BTC filtri: bitta manba
# --------------------------------------------------------------------------- #


def _shamlar(narxlar: list[float], timeframe_soat: int = 4) -> list[Candle]:
    boshi = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            open_time=boshi + timedelta(hours=timeframe_soat * i),
            open=narx,
            high=narx,
            low=narx,
            close=narx,
            volume=1.0,
        )
        for i, narx in enumerate(narxlar)
    ]


@pytest.fixture
def filtr():
    return load_config().risk_engine.btc_filter


def test_btc_ozgarishi_foizni_togri_hisoblaydi(filtr):
    # 4 soatlik qatorda sutka = 6 sham. 100 -> 110 = +10%.
    narxlar = [100.0] * 6 + [110.0]
    candles = {"BTC": {"4h": _shamlar(narxlar)}}
    assert btc_ozgarishi_24h(candles, filtr, "4h") == pytest.approx(10.0)


def test_btc_yoq_bolsa_nol_emas_none(filtr):
    """`None` — "noma'lum". Nol bo'lsa qoida "BTC qimirlamadi" deb o'qiydi.

    Backtestda aynan shu farq bor edi: u qattiq `0.0` uzatardi va
    `BtcMarketRule` sinovda HECH QACHON to'xtatmasdi, jonlida esa
    to'xtatardi.
    """
    assert btc_ozgarishi_24h({}, filtr, "4h") is None
    assert btc_ozgarishi_24h({"ETH": {"4h": _shamlar([1.0] * 10)}}, filtr, "4h") is None


def test_btc_tarix_qisqa_bolsa_none(filtr):
    candles = {"BTC": {"4h": _shamlar([100.0, 101.0])}}
    assert btc_ozgarishi_24h(candles, filtr, "4h") is None


def test_sozlamadagi_timeframe_yoq_bolsa_zaxira_ishlatiladi(filtr):
    candles = {"BTC": {"1d": _shamlar([100.0, 100.0, 105.0], timeframe_soat=24)}}
    assert btc_ozgarishi_24h(candles, filtr, "1d") == pytest.approx(5.0)


def test_jonli_va_backtest_bitta_funksiyani_chaqiradi():
    """Ikkala tomon ham `btc_ozgarishi_24h` ni import qilsin.

    Nusxa ko'chirilsa ular jimgina ajralib ketadi — bu loyihada
    besh marta uchragan xato turi.
    """
    for yol in ("bot/services/runner.py", "core/backtest/engine.py"):
        matn = Path(yol).read_text(encoding="utf-8")
        assert "btc_ozgarishi_24h" in matn, yol

    # Backtest qiymatni QATTIQ raqam bilan uzatmasin. Izohda bu satr
    # tarix sifatida qolgani uchun matn qidiruvi emas, AST tekshiriladi.
    daraxt = ast.parse(Path("core/backtest/engine.py").read_text(encoding="utf-8"))
    for tugun in ast.walk(daraxt):
        if not isinstance(tugun, ast.keyword) or tugun.arg != "btc_change_24h_pct":
            continue
        assert not isinstance(tugun.value, ast.Constant), (
            "core/backtest/engine.py: btc_change_24h_pct qattiq qiymat bilan "
            "uzatilmoqda — jonli tizim bilan ajralib ketadi"
        )


# --------------------------------------------------------------------------- #
#  1.2 — voronka hech narsani yo'qotmaydi
# --------------------------------------------------------------------------- #


def _natija(rejections: dict[str, int], signals: int = 0) -> BacktestResult:
    natija = BacktestResult(label="sinov", steps=100)
    natija.rejections = dict(rejections)
    natija.signals_emitted = signals
    return natija


def test_har_bir_nomlangan_bosqich_voronkaga_tushadi():
    """STAGE_LABELS dagi HAR BIR bosqich voronkada o'z qatorini topsin.

    Ilgari voronka to'rtta kalitni bilardi va qolgan o'n uchtasi
    jimgina tashlab yuborilardi — hisobot "hammasi shu yerda
    to'xtadi" deb yolg'on ko'rsatardi.
    """
    yoqotilgan = [
        bosqich
        for bosqich in STAGE_LABELS
        if voronka_kaliti(bosqich) is BOSHQA_BOSQICH
    ]
    assert not yoqotilgan, f"Voronkada joyi yo'q bosqichlar: {sorted(yoqotilgan)}"


def test_voronka_yigindisi_rad_etishlar_bilan_teng():
    natija = _natija(
        {
            "market_health": 5,
            "classic_ta:halal": 3,
            "classic_ta:data": 7,
            "classic_ta:zones": 11,
            "classic_ta:zone_position": 40,
            "classic_ta:levels:stop_too_close": 9,
            "classic_ta:levels:stop_too_far": 4,
            "threshold": 25,
            "risk_engine:btc_market_filter": 6,
            "risk_engine:score_below_threshold": 2,
        },
        signals=12,
    )
    assert natija.voronka_yigindisi == sum(natija.rejections.values())

    qatorlardagi_rad = sum(rad for _, _, rad, _, _ in natija.funnel())
    assert qatorlardagi_rad == sum(natija.rejections.values())


def test_tanilmagan_bosqich_ham_sanaladi():
    """Yangi bosqich qo'shilganda yig'indi buzilmasin."""
    natija = _natija({"butunlay:yangi_bosqich": 8, "threshold": 2}, signals=1)
    assert natija.voronka_yigindisi == 10
    kalitlar = [q[0] for q in natija.funnel()]
    assert BOSHQA_BOSQICH in kalitlar


def test_voronka_zanjiri_signalgacha_yetadi():
    """Oxirgi bosqichdan o'tganlar soni chiqqan signallarga teng."""
    natija = _natija({"classic_ta:zone_position": 30, "threshold": 10}, signals=5)
    qatorlar = natija.funnel()
    assert qatorlar[-1][3] == natija.signals_emitted


def test_risk_engine_qoidasi_threshold_ga_tushmaydi():
    """`risk_engine:score_below_threshold` — risk qoidasi, ball emas."""
    assert voronka_kaliti("risk_engine:score_below_threshold") == "risk_engine"
    assert voronka_kaliti("threshold") == "threshold"


def test_voronka_tartibi_qaror_zanjiri_bilan_mos():
    """Zona bosqichi ballgacha, ball esa Risk Engine'gacha turadi."""
    tartib = list(VORONKA_TARTIBI)
    assert tartib.index("zone_position") < tartib.index("levels")
    assert tartib.index("levels") < tartib.index("threshold")
    assert tartib.index("threshold") < tartib.index("risk_engine")


# --------------------------------------------------------------------------- #
#  1.3 — `stage` ga bool tushmasin
# --------------------------------------------------------------------------- #


def test_level_result_stage_pozitsion_uzatilmaydi():
    """`LevelResult(None, "...", tuzilmaviy)` — uchinchi argument `stage`.

    Unga bool uzatilganda bosqich "classic_ta:True" bo'lib chiqar,
    STAGE_LABELS da topilmas va voronkada sanalmasdi. Ikkitadan ortiq
    pozitsion argument umuman berilmasin — qolganlari NOMLI bo'lsin.
    """
    manba = Path("core/analysis/scoring/levels.py").read_text(encoding="utf-8")
    daraxt = ast.parse(manba)
    xatolar = []
    for tugun in ast.walk(daraxt):
        if not isinstance(tugun, ast.Call):
            continue
        nom = tugun.func.id if isinstance(tugun.func, ast.Name) else None
        if nom == "LevelResult" and len(tugun.args) > 2:
            xatolar.append(tugun.lineno)
    assert not xatolar, (
        "LevelResult ga ikkitadan ortiq pozitsion argument uzatilgan "
        f"(qatorlar: {xatolar}). `stage=` va `tp_from_structure=` nomli bo'lsin."
    )


def test_tartib_buzildi_bosqichi_nomlangan():
    assert "classic_ta:levels:tartib_buzildi" in STAGE_LABELS
    assert voronka_kaliti("classic_ta:levels:tartib_buzildi") == "levels"
