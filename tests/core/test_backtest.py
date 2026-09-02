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
from core.domain.models import Candle, signal_levels

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
    """Isinish BARCHA yuqori timeframelarni qamrab olsin.

    Buni faqat kirish timeframe bo'yicha hisoblash — jimgina buziladigan
    xato: yuqori timeframelarda EMA hisoblanmaydi, trend `FLAT` qaytadi
    va muvofiqlik hech qachon bajarilmaydi. Backtest "signal yo'q"
    deydi, sabab esa strategiyada emas, ma'lumot yetishmasligida.

    BU TEST O'ZI HAM TESHIK EDI. U `htf_confirmation` ni tekshirardi,
    ya'ni hisobning aynan o'sha qismini — va SALOMATLIK timeframei
    hisobda yo'qligini ko'rmadi. Indeks 60 balli qismisiz qoldi va
    sinovning yarmida 26-32 da qotdi (`docs/ARXITEKTURA.md`,
    80-bo'lim).

    Endi tekshiruv nomlangan ro'yxatga emas, TALABGA qaraydi: isinish
    tugagach har bir timeframeda `min_candles` sham bo'lishi kerak.
    Batafsil: `tests/core/test_isinish_davri.py`.
    """
    from core.backtest.dataset import TIMEFRAME_MINUTES
    from core.backtest.warmup import warmup_timeframes

    config = load_config()
    analysis = config.analysis
    kerak = Backtester(config)._warmup_steps()
    kirish = TIMEFRAME_MINUTES[analysis.entry_timeframe]

    eng_yuqori = max(TIMEFRAME_MINUTES[tf] for tf in analysis.htf_confirmation)
    assert eng_yuqori > kirish, "tasdiq timeframei kirishdan yuqori bo'lishi kerak"

    for tf in warmup_timeframes(config):
        shamlar = kerak * kirish // TIMEFRAME_MINUTES[tf]
        assert shamlar >= analysis.indicators.min_candles, (
            f"{tf}: isinishdan keyin {shamlar} sham, "
            f"{analysis.indicators.min_candles} kerak"
        )


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
        min_candles=30,
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


# --------------------------------------------------------------------------- #
#  Tarix oynasi jonli tizimdagidek cheklanadi
# --------------------------------------------------------------------------- #


def test_oyna_cheklanadi_va_oxirgi_shamlar_qoladi() -> None:
    """`limit` eng SO'NGGI shamlarni qoldiradi, eng eskilarini emas."""
    ds = Dataset()
    ds.add("BTC", "15m", qator(100))

    hammasi = ds.window("BTC", BOSH + timedelta(minutes=15 * 99))["15m"]
    cheklangan = ds.window("BTC", BOSH + timedelta(minutes=15 * 99), limit=10)["15m"]

    assert len(hammasi) == 100
    assert len(cheklangan) == 10
    assert cheklangan == hammasi[-10:]


def test_backtest_jonli_oyna_bilan_ishlaydi() -> None:
    """Indikatorlar jonli tizimdagi OYNADA hisoblanishi kerak.

    Jonli bot birjadan `analysis.candles_lookback` (500) tadan ortiq
    sham so'ramaydi — ya'ni ADX ham, S/R zonalari ham shu oynada
    hisoblanadi. Backtest butun tarixni bersa, ikki yillik sinovda
    4 soatlik qatorda 4380 sham bo'lardi va indikatorlar BOSHQA
    qiymat berardi. Sinov o'shanda jonli qarorni emas, boshqa
    qarorni o'lchagan bo'lardi.

    Ikkinchi oqibati — tezlik: indikatorlar butun ro'yxat bo'ylab
    yuradi, ya'ni har qadamda ish hajmi o'sib borardi.
    """
    config = tez_config()
    dataset = dataset_uchun(config, {"BTC": savdo_beradigan_qator()})

    from core.signals import SignalTracker

    kirish = Backtester(config)._build_input(
        dataset,
        BOSH + timedelta(minutes=15 * 1100),
        SignalTracker(config),
        {},
        config.analysis.entry_timeframe,
    )

    assert kirish.symbols, "sinov shartini tekshiradi: coin bo'lishi kerak"
    for coin in kirish.symbols:
        for tf, shamlar in coin.candles.items():
            assert len(shamlar) <= config.analysis.candles_lookback, (
                f"{tf}: oyna {config.analysis.candles_lookback} shamdan oshmasligi kerak"
            )


# --------------------------------------------------------------------------- #
#  Komissiya va sirg'anish
# --------------------------------------------------------------------------- #


def test_natijadan_xarajat_ayriladi() -> None:
    """Ilgari savdo BEPUL bo'lardi — bu eng zararli soddalashtirish.

    649 ta savdoda 0.3% lik xarajat ~195% ni yeb qo'yadi, ya'ni
    xulosani o'zgartira oladigan hajm. Backtestning butun ma'nosi
    haqiqatni oldindan ko'rish bo'lgani uchun bunday "sovg'a"
    natijani tizimli ravishda chiroyliroq ko'rsatardi.
    """

    from core.domain.models import Signal

    config = load_config()
    darajalar = signal_levels(entry=100.0, stop=98.0, tp1=103.0, tp2=106.0)
    signal = Signal(symbol="BTC", levels=darajalar, source="classic_ta", score=70.0)

    motor = Backtester(config)
    xom = motor._xom_natija(signal, 106.0, reached=1)
    sof = motor._result_pct(signal, 106.0, reached=1)

    assert xom > 0
    assert sof == pytest.approx(xom - config.backtest.round_trip_cost_pct)


def test_xarajat_ikki_tomonlama() -> None:
    """Pozitsiya sotib olishda ham, sotishda ham to'laydi.

    TP1 da yarmi yopilsa ham jami hajm o'zgarmaydi — shuning uchun
    xarajat ikki tomonlama bo'lib qoladi, uch emas.
    """
    from core.config.schema import BacktestConfig

    sozlama = BacktestConfig(fee_pct=0.1, slippage_pct=0.05)

    assert sozlama.round_trip_cost_pct == pytest.approx(0.3)


def test_xarajat_nolga_tushirilishi_mumkin() -> None:
    """Xarajatsiz o'lchov ham kerak — ikkisining farqi ko'rinsin."""
    import dataclasses

    from core.config.schema import BacktestConfig
    from core.domain.models import Signal

    config = dataclasses.replace(
        load_config(), backtest=BacktestConfig(fee_pct=0.0, slippage_pct=0.0)
    )
    darajalar = signal_levels(entry=100.0, stop=98.0, tp1=103.0, tp2=106.0)
    signal = Signal(symbol="BTC", levels=darajalar, source="classic_ta", score=70.0)

    motor = Backtester(config)

    assert motor._result_pct(signal, 106.0, reached=0) == pytest.approx(6.0)


# --------------------------------------------------------------------------- #
#  Tayanch: "olib ushlab turish"
# --------------------------------------------------------------------------- #


def test_tayanch_hisoblanadi() -> None:
    """Strategiyaning raqamiga o'LCHOV kerak.

    "O'rtacha -0.73% har savdoda" o'z-o'zicha hech narsa demaydi:
    yomonmi, NIMAGA nisbatan? Agar coinlar shu davrda o'sgan bo'lsa,
    strategiya hech narsa qilmaslikdan ham yomon ishlagan bo'ladi.
    """
    config = tez_config()
    dataset = dataset_uchun(config, {"BTC": savdo_beradigan_qator()})

    natija = Backtester(config, label="tayanch").run(dataset, max_steps=300)

    assert natija.buy_and_hold_pct is not None
    assert natija.buy_and_hold_pct > 0, "sinov qatori ko'tariluvchi"


def test_tayanch_hisobotda_korinadi() -> None:
    """Raqam hisoblanib, ekranda ko'rinmasa — foydasi yo'q."""
    natija = BacktestResult(
        label="sinov",
        trades=[savdo("stop", -1.0, i) for i in range(40)],
        buy_and_hold_pct=25.0,
    )

    matn = render(natija)

    assert "olib ushlab turish" in matn
    assert "+25.0%" in matn
    assert "HECH NARSA QILMASLIKDAN yomon" in matn


def test_tayanchdan_yaxshi_bolsa_ogohlantirish_yoq() -> None:
    natija = BacktestResult(
        label="sinov",
        trades=[savdo("tp2_hit", 4.0, i) for i in range(40)],
        buy_and_hold_pct=5.0,
    )

    matn = render(natija)

    assert "olib ushlab turish" in matn
    assert "HECH NARSA QILMASLIKDAN yomon" not in matn


def test_tayanch_yoq_bolsa_qator_chiqmaydi() -> None:
    """Hisoblab bo'lmasa — raqam O'YLAB TOPILMAYDI."""
    natija = BacktestResult(
        label="sinov", trades=[savdo("stop", -1.0, i) for i in range(40)]
    )

    assert "olib ushlab turish" not in render(natija)


# --------------------------------------------------------------------------- #
#  Win-rate YOLG'ON GAPIRMASIN
# --------------------------------------------------------------------------- #


def test_win_rate_turkumga_emas_NATIJAGA_qaraydi() -> None:
    """"G'alaba" — hisobda pul ko'paygani, turkum nomi emas.

    ILGARI `tp2_hit` va `tp1_then_stop` avtomatik g'alaba sanalardi.
    Run #10 buni ochib berdi: hisobotda "win-rate 64%" va "o'rtacha
    -1.31%" yonma-yon turdi.

    Sabab: `tp1_then_stop` — TP1 olindi, keyin Stop kirish narxida
    ishladi. TP1 juda yaqin bo'lsa qismli foyda arzimas, qolgani
    nolda yopiladi, komissiya ayrilgach natija MANFIY chiqadi.
    Turkum "g'alaba", pul esa kamaygan.
    """
    yutqazgan_galaba = savdo("tp1_then_stop", -0.4)
    yutgan_stop = savdo("stop", 0.2)

    assert not yutqazgan_galaba.is_win, (
        "TP1 olingan, lekin natija manfiy — bu g'alaba emas"
    )
    assert yutgan_stop.is_win


def test_nishonga_yetish_alohida_olchov() -> None:
    """"Nishonga yetdi" savoli yo'qolmadi — u `tp2_rate` da.

    Ikkita savol bor va ular boshqa-boshqa: pul ko'paydimi
    (`win_rate`) va yakuniy nishonga yetdimi (`tp2_rate`).
    Ularni bitta raqamga qo'shish ikkalasini ham buzardi.
    """
    natija = BacktestResult(
        label="sinov",
        trades=[
            savdo("tp2_hit", 3.0),
            savdo("tp1_then_stop", -0.4),
            savdo("stop", -1.0),
            savdo("stop", -1.0),
        ],
    )

    assert natija.tp2_rate == pytest.approx(0.25)
    assert natija.win_rate == pytest.approx(0.25)
