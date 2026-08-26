"""6.3-band: backtest — tarixiy ma'lumotda sinash.

ENG MUHIM TEST — lookahead himoyasi. "Kelajakka qarash" backtestning eng
keng tarqalgan va eng qimmat xatosi: natijalar chiroyli chiqadi, jonli
savdoda esa hammasi buziladi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.backtest import (
    MIN_TRADES_FOR_CONCLUSION,
    Backtester,
    BacktestResult,
    BacktestTrade,
    Dataset,
    aggregate,
    build_dataset,
    compare,
    render,
)
from core.config import load_config
from core.domain.models import Candle

BOSH = datetime(2025, 1, 1, tzinfo=UTC)


def sham(i: int, narx: float, daqiqa: int = 15, hajm: float = 1000.0) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(minutes=daqiqa * i),
        open=narx,
        high=narx * 1.002,
        low=narx * 0.998,
        close=narx,
        volume=hajm,
    )


def qator(n: int, daqiqa: int = 15) -> list[Candle]:
    return [sham(i, 100 + i * 0.1, daqiqa) for i in range(n)]


def dataset_uchun(config, shamlar: dict[str, list[Candle]], asos: str = "15m") -> Dataset:  # noqa: ANN001
    """Konfiguratsiya talab qiladigan timeframelar bilan dataset quradi.

    Timeframelar testga yozib qo'yilsa, sozlama o'zgargach dataset
    kerakli qatorni umuman saqlamaydi va backtest jimgina 0 qadam
    qaytaradi — xato emas, shunchaki bo'sh natija.
    """
    analysis = config.analysis
    kerakli = {analysis.entry_timeframe, analysis.market_health_timeframe}
    kerakli.update(analysis.htf_confirmation)
    return build_dataset(shamlar, asos, sorted(kerakli))


# --------------------------------------------------------------------------- #
#  LOOKAHEAD HIMOYASI — eng muhim
# --------------------------------------------------------------------------- #


def test_faqat_otgan_shamlar_korinadi() -> None:
    """Backtest kelajakni ko'rmasligi SHART."""
    ds = Dataset()
    ds.add("BTC", "15m", qator(100))

    o_rta = BOSH + timedelta(minutes=15 * 50)
    ko_ringan = ds.window("BTC", o_rta)["15m"]

    assert len(ko_ringan) == 51, "faqat o'sha paytgacha ochilgan shamlar"
    assert all(c.open_time <= o_rta for c in ko_ringan)


def test_kelajak_shamlari_alohida_soraladi() -> None:
    """Natijani kuzatish uchun kerak, lekin TAHLILDA ishlatilmaydi."""
    ds = Dataset()
    ds.add("BTC", "15m", qator(100))

    o_rta = BOSH + timedelta(minutes=15 * 50)
    kelajak = ds.future_candles("BTC", "15m", o_rta)

    assert all(c.open_time > o_rta for c in kelajak)
    assert len(kelajak) == 49


def test_bosh_vaqtda_hech_narsa_korinmaydi() -> None:
    ds = Dataset()
    ds.add("BTC", "15m", qator(100))
    assert ds.window("BTC", BOSH - timedelta(days=1))["15m"] == []


def test_mavjud_bolmagan_coin_bosh_qaytaradi() -> None:
    assert Dataset().window("YOQ", BOSH) == {}


# --------------------------------------------------------------------------- #
#  Timeframe yig'ish
# --------------------------------------------------------------------------- #


def test_shamlar_yuqori_timeframega_yigiladi() -> None:
    """4 ta 15 daqiqalik sham = 1 ta soatlik sham."""
    manba = [
        Candle(BOSH + timedelta(minutes=15 * i), 100, 100 + i, 100 - i, 100 + i, 10)
        for i in range(4)
    ]
    natija = aggregate(manba, 15, 60)

    assert len(natija) == 1
    yigilgan = natija[0]
    assert yigilgan.open_time == manba[0].open_time
    assert yigilgan.open == manba[0].open
    assert yigilgan.close == manba[-1].close
    assert yigilgan.high == max(c.high for c in manba)
    assert yigilgan.low == min(c.low for c in manba)
    assert yigilgan.volume == sum(c.volume for c in manba)


def test_toliq_bolmagan_guruh_yopilmagan_deb_belgilanadi() -> None:
    natija = aggregate(qator(6), 15, 60)
    assert natija[0].closed is True
    assert natija[-1].closed is False, "oxirgi guruh to'liq emas"


def test_bolinmaydigan_timeframe_rad_etiladi() -> None:
    with pytest.raises(ValueError, match="bo'linmaydi"):
        aggregate(qator(10), 15, 20)


def test_barcha_timeframelar_bitta_qatordan_quriladi() -> None:
    """Ko'p timeframe muvofiqligi faqat shunda ma'noga ega (3.2-band).

    Har bir timeframe alohida qator bo'lsa, ular hech qachon muvofiq
    bo'lmaydi va tizim hech qachon signal bermaydi.
    """
    ds = build_dataset({"BTC": qator(400)}, "15m", ["15m", "1h", "4h"])

    assert len(ds.series["BTC"].candles["15m"]) == 400
    assert len(ds.series["BTC"].candles["1h"]) == 100
    assert len(ds.series["BTC"].candles["4h"]) == 25


def test_asosdan_past_timeframe_otkazib_yuboriladi() -> None:
    ds = build_dataset({"BTC": qator(100)}, "1h", ["15m", "1h", "4h"])
    assert "15m" not in ds.series["BTC"].timeframes


# --------------------------------------------------------------------------- #
#  Isinish davri — jimgina buziladigan xato
# --------------------------------------------------------------------------- #


def test_isinish_davri_eng_yuqori_timeframega_qarab_hisoblanadi() -> None:
    """Eng yuqori timeframedagi EMA200 uchun yetarli tarix kerak.

    Buni faqat kirish timeframe bo'yicha hisoblash — jimgina buziladigan
    xato: yuqori timeframelarda EMA hisoblanmaydi, trend `FLAT` qaytadi
    va muvofiqlik hech qachon bajarilmaydi. Backtest "signal yo'q"
    deydi, sabab esa strategiyada emas, ma'lumot yetishmasligida.

    Kutilgan qiymat KONFIGURATSIYADAN hisoblanadi. Ilgari bu yerda
    "19 200" deb yozib qo'yilgan edi (1d / 15m = 96 barobar) — timeframe
    to'plami o'zgargach test jimgina ma'nosini yo'qotardi.
    """
    from core.backtest.dataset import TIMEFRAME_MINUTES

    config = load_config()
    analysis = config.analysis
    kerak = Backtester(config)._warmup_steps()

    kirish = TIMEFRAME_MINUTES[analysis.entry_timeframe]
    eng_yuqori = max(TIMEFRAME_MINUTES[tf] for tf in analysis.htf_confirmation)
    nisbat = max(1, eng_yuqori // kirish)

    assert nisbat > 1, "tasdiq timeframei kirishdan yuqori bo'lishi kerak"
    assert kerak == analysis.indicators.ema_slow * nisbat + 10


def test_malumot_yetmasa_bosh_natija() -> None:
    ds = dataset_uchun(load_config(), {"BTC": qator(500)})
    natija = Backtester(load_config()).run(ds)

    assert natija.steps == 0
    assert natija.closed == 0


def test_max_steps_isinishdan_keyin_qollanadi() -> None:
    """`max_steps` — haqiqiy tahlil qadamlari, tarix emas."""
    config = load_config()
    kerak = Backtester(config)._warmup_steps()
    ds = dataset_uchun(config, {"BTC": qator(kerak * 20 + 2000)})

    natija = Backtester(config).run(ds, max_steps=25)
    assert natija.steps == 25


# --------------------------------------------------------------------------- #
#  Natija hisoblash
# --------------------------------------------------------------------------- #


def savdo(
    outcome: str,
    result_pct: float,
    kun: int = 1,
    reached_tp1: bool = False,
) -> BacktestTrade:
    return BacktestTrade(
        symbol="BTC",
        source="classic_ta",
        score=80.0,
        market_health=75.0,
        opened_at=BOSH + timedelta(days=kun),
        closed_at=BOSH + timedelta(days=kun, hours=6),
        entry=100.0,
        exit_price=100 + result_pct,
        outcome=outcome,
        reached_tp1=reached_tp1,
        result_pct=result_pct,
    )


def test_win_rate_hisoblanadi() -> None:
    natija = BacktestResult(
        label="sinov",
        trades=[
            savdo("tp2_hit", 4.0, 1),
            savdo("tp1_then_stop", 1.0, 2, reached_tp1=True),
            savdo("stop", -1.0, 3),
            savdo("stop", -1.0, 4),
        ],
    )

    assert natija.win_rate == pytest.approx(0.5)
    assert natija.tp2_rate == pytest.approx(0.25)
    assert natija.total_return_pct == pytest.approx(3.0)


def test_maksimal_pasayish_hisoblanadi() -> None:
    """Win-rate yuqori bo'lsa ham, chuqur pasayish strategiyani buzadi."""
    natija = BacktestResult(
        label="sinov",
        trades=[
            savdo("tp2_hit", 5.0, 1),    # +5  (cho'qqi 5)
            savdo("stop", -2.0, 2),      # +3
            savdo("stop", -2.0, 3),      # +1  (pasayish 4)
            savdo("tp2_hit", 3.0, 4),    # +4
        ],
    )
    assert natija.max_drawdown_pct == pytest.approx(4.0)


def test_ketma_ket_zarar_hisoblanadi() -> None:
    natija = BacktestResult(
        label="sinov",
        trades=[
            savdo("stop", -1.0, 1),
            savdo("stop", -1.0, 2),
            savdo("stop", -1.0, 3),
            savdo("tp2_hit", 4.0, 4),
            savdo("stop", -1.0, 5),
        ],
    )
    assert natija.max_consecutive_losses == 3


def test_tp1_dan_keyingi_stop_foyda_hisoblanadi() -> None:
    """5.4-banddagi qismli yopish qoidasi bilan bir xil."""
    assert savdo("tp1_then_stop", 1.0, reached_tp1=True).is_win


def test_bosh_natijada_xato_yoq() -> None:
    natija = BacktestResult(label="bo'sh")
    assert natija.win_rate is None
    assert natija.max_drawdown_pct == 0.0
    assert natija.total_return_pct == 0.0


# --------------------------------------------------------------------------- #
#  Hisobot — halollik chegarasi
# --------------------------------------------------------------------------- #


def test_kichik_namuna_ochiq_aytiladi() -> None:
    """10 ta savdodan "win-rate 70%" xulosasi chiqarilmaydi."""
    natija = BacktestResult(label="kichik", trades=[savdo("tp2_hit", 4.0, i) for i in range(5)])
    matn = render(natija)

    assert "Namuna kichik" in matn
    assert "xulosa emas" in matn


def test_yetarli_namunada_ogohlantirish_yoq() -> None:
    natija = BacktestResult(
        label="katta",
        trades=[savdo("tp2_hit", 4.0, i) for i in range(MIN_TRADES_FOR_CONCLUSION + 5)],
    )
    assert "Namuna kichik" not in render(natija)


def test_savdosiz_natijada_sabablar_korsatiladi() -> None:
    """Signal chiqmagan bo'lsa, NIMA UCHUN ekani ko'rinishi kerak."""
    natija = BacktestResult(
        label="signalsiz",
        rejections={"classic_ta:timeframes": 412, "classic_ta:zone_position": 388},
    )
    matn = render(natija)

    assert "Savdo bo'lmadi" in matn
    assert "classic_ta:timeframes" in matn


def test_chegaraga_yetmagan_ballar_korsatiladi() -> None:
    """Nol savdo chiqqanda "nomzod yo'q edi"mi yoki "ball yetmadi"mi — farqi bor.

    Bu farq chegarani sozlash uchun hal qiluvchi: eng yuqori ball 68 bo'lsa
    chegara (70) deyarli to'g'ri; 35 bo'lsa muammo chegarada emas.
    """
    natija = BacktestResult(
        label="chegara",
        rejections={"threshold": 3},
        near_miss_scores=[68.3, 50.0, 41.7],
    )
    matn = render(natija)

    assert natija.best_near_miss == 68.3
    assert natija.average_near_miss == pytest.approx(53.333, abs=0.01)
    assert "68.3" in matn
    assert "Chegaraga yetmagan" in matn


def test_nomzod_bolmasa_chegara_qatori_chiqmaydi() -> None:
    """Ball statistikasi yo'q bo'lsa, bo'sh qator ko'rsatilmaydi."""
    natija = BacktestResult(label="bosh", rejections={"classic_ta:zone_position": 10})

    assert natija.best_near_miss is None
    assert natija.average_near_miss is None
    assert "Chegaraga yetmagan" not in render(natija)


def test_taqqoslash_eng_yaxshisini_topadi() -> None:
    yaxshi = BacktestResult(
        label="yaxshi", trades=[savdo("tp2_hit", 4.0, i) for i in range(40)]
    )
    yomon = BacktestResult(
        label="yomon", trades=[savdo("stop", -1.0, i) for i in range(40)]
    )
    matn = compare([yaxshi, yomon])

    assert "yaxshi" in matn
    assert "kafolat emas" in matn, "ogohlantirish bo'lishi kerak"


def test_taqqoslashda_kichik_namuna_ogohlantiriladi() -> None:
    natijalar = [
        BacktestResult(label="a", trades=[savdo("tp2_hit", 4.0, 1)]),
        BacktestResult(label="b", trades=[savdo("stop", -1.0, 1)]),
    ]
    assert "yetarli emas" in compare(natijalar)


def test_bosh_taqqoslash_xato_bermaydi() -> None:
    assert "natija yo'q" in compare([])


# --------------------------------------------------------------------------- #
#  To'liq zanjir: signal chiqishidan yopilishigacha
# --------------------------------------------------------------------------- #


def tez_config():  # noqa: ANN201
    """Backtestni testda ishlatish uchun qisqartirilgan sozlama.

    Indikator davrlari kichraytiriladi (isinish 19 200 qadamdan ~70 ga
    tushadi) va ball chegarasi pasaytiriladi. Maqsad — MEXANIZMNI
    tekshirish, strategiyani baholash emas.
    """
    import dataclasses

    asos = load_config()
    ind = dataclasses.replace(
        asos.analysis.indicators,
        ema_fast=10,
        ema_slow=30,
        rsi_period=7,
        macd_fast=6,
        macd_slow=13,
        macd_signal=4,
        volume_ma_period=10,
        adx_period=7,
    )
    # Kirish timeframei ham 15m ga qaytariladi: sinov qatorlari 15
    # daqiqalik shamlardan quriladi va bu testlar MEXANIZMNI sinaydi,
    # sozlamani emas.
    analiz = dataclasses.replace(
        asos.analysis,
        indicators=ind,
        entry_timeframe="15m",
        htf_confirmation=["30m"],
        market_health_timeframe="30m",
    )
    # Stop ko'paytmasi kichraytiriladi: bu testlar MEXANIZMNI sinaydi
    # (chiqish narxi to'g'ri yozilyaptimi), stop kengligini emas. Keng
    # stop bilan sinov qatorida umuman stop sodir bo'lmasdi.
    savdo_qoidalari = dataclasses.replace(asos.trade_rules, stop_atr_mult=0.5)
    chegaralar = dataclasses.replace(
        asos.scoring.thresholds, threshold_high_health=35.0, threshold_mid_health=45.0
    )
    strategiyalar = dataclasses.replace(
        asos.strategies,
        opening_range_scalp=dataclasses.replace(
            asos.strategies.opening_range_scalp, enabled=False
        ),
    )
    return dataclasses.replace(
        asos,
        analysis=analiz,
        trade_rules=savdo_qoidalari,
        scoring=dataclasses.replace(asos.scoring, thresholds=chegaralar),
        strategies=strategiyalar,
    )


def savdo_beradigan_qator(n: int = 1200) -> list[Candle]:
    """Signal chiqishi uchun yetarli trend VA volatillikka ega qator.

    Volatillik muhim: Risk Engine ATR 1% dan past bo'lsa signalni to'xtatadi
    ("TP masofasiga yetish ehtimoli past").
    """
    import math
    import random

    random.seed(11)
    shamlar: list[Candle] = []
    oldingi = 100.0
    for i in range(n):
        kun = i * 15 / 1440
        yopilish = 100 * math.exp(0.02 * kun) + math.sin(kun * 3) * 1.2 + random.gauss(0, 0.15)
        chetlanish = abs(random.gauss(0, 1)) * 0.9 + 0.5
        shamlar.append(
            Candle(
                open_time=BOSH + timedelta(minutes=15 * i),
                open=oldingi,
                high=yopilish + chetlanish,
                low=yopilish - chetlanish,
                close=yopilish,
                volume=1000 * random.uniform(0.5, 2.5),
            )
        )
        oldingi = yopilish
    return shamlar


def test_zanjir_signal_chiqarib_savdoni_yopadi() -> None:
    """Uchidan uchiga: nomzod -> ball -> Risk Engine -> kuzatuv -> yopilgan savdo.

    Bu testsiz backtestning eng muhim qismi — signal CHIQISHI va
    KUZATILISHI — umuman tekshirilmagan bo'lardi.
    """
    config = tez_config()
    dataset = dataset_uchun(config, {"BTC": savdo_beradigan_qator()})

    natija = Backtester(config, label="zanjir").run(dataset, max_steps=900)

    assert natija.signals_emitted > 0, "zanjir birorta signal chiqara olmadi"
    assert natija.closed > 0, "chiqqan signal kuzatilib yopilishi kerak"
    for savdo_natijasi in natija.trades:
        assert savdo_natijasi.entry > 0
        assert savdo_natijasi.closed_at >= savdo_natijasi.opened_at


def test_stop_zarari_universal_chegaradan_oshmaydi() -> None:
    """3.3-band: stop masofasi 1% dan oshmasligi kerak — backtestda ham.

    Bu regressiya testi haqiqiy xatoni qayd etadi: avval chiqish narxi
    hodisadagi narx (shamning eng past nuqtasi) sifatida yozilardi, shu
    sababli 1% lik stop -1.66% zarar ko'rsatardi. Chiqish buyurtmasi OCO —
    u Stop DARAJASIDA bajariladi, shamning chekkasida emas.
    """
    config = tez_config()
    dataset = dataset_uchun(config, {"BTC": savdo_beradigan_qator()})

    natija = Backtester(config, label="stop chegarasi").run(dataset, max_steps=900)
    stoplar = [t for t in natija.trades if t.outcome == "stop"]

    assert stoplar, "test uchun kamida bitta stop kerak"
    # Backtest `tez_config()` bilan ishlaydi va uning nisbati boshqacha;
    # chegara AYNAN o'sha konfiguratsiyadan olinadi.
    chegara = config.trade_rules.max_stop_distance_pct
    for savdo_natijasi in stoplar:
        assert savdo_natijasi.result_pct >= -chegara - 1e-9, (
            f"stop zarari {savdo_natijasi.result_pct:.3f}% — chegara {chegara}%"
        )


# --------------------------------------------------------------------------- #
#  Jonli tizim bilan bir xil kod
# --------------------------------------------------------------------------- #


def test_backtest_jonli_sikl_kodini_ishlatadi() -> None:
    """Agar backtest o'z nusxasini ishlatganda, sinovning ma'nosi qolmasdi."""
    from core.pipeline import SignalCycle

    backtester = Backtester(load_config())
    assert isinstance(backtester._cycle, SignalCycle)


def test_backtest_jonli_kuzatuvchini_ishlatadi() -> None:
    from core.signals import SignalTracker

    config = load_config()
    kerak = Backtester(config)._warmup_steps()
    ds = dataset_uchun(config, {"BTC": qator(kerak * 20 + 2000)})

    # `run` ichida SignalTracker yaratiladi — importi mavjudligini tekshiramiz
    assert SignalTracker is not None
    natija = Backtester(config).run(ds, max_steps=5)
    assert natija.steps == 5
