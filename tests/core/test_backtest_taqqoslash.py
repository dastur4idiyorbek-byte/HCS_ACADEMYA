"""Backtest taqqoslash rejimi — brief talab qilgan MAJBURIY sinov.

`bozor_salomatligi_asosiy_tuzatish.md`: "hech qanday yangi qoida
sinovsiz jonli ishga tushirilmasin". Correction Entry shu sababdan
konfiguratsiyada o'chirilgan turibdi, uni faqat taqqoslash natijasi
yoqishi mumkin.

Bu testlar taqqoslashning O'ZINI tekshiradi — strategiyani emas.
Chunki oldingi versiyada taqqoslash butunlay ishlamas edi: variantlar
EMA davridan qolgan, allaqachon olib tashlangan sozlamaga murojaat
qilardi va `--compare` birinchi qadamda `TypeError` bilan tushardi.
Xato faqat tarmoqli mashinada, ma'lumot yuklab bo'lingandan keyin
ko'rinardi — ya'ni eng noqulay joyda.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from core.config import load_config
from scripts.backtest import (
    KeshYetishmaydi,
    _kerakli_timeframelar,
    _keshdan_yigish,
    _variantlar,
)


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


# --------------------------------------------------------------------------- #
#  Variantlar
# --------------------------------------------------------------------------- #


def test_variantlar_quriladi(config) -> None:  # noqa: ANN001
    """Har bir variant haqiqiy `AppConfig` bo'lishi kerak.

    Eski `_variantlar()` mavjud bo'lmagan maydonni o'zgartirmoqchi
    bo'lardi va aynan shu yerda tushardi.
    """
    variantlar = _variantlar(config)

    assert len(variantlar) >= 2
    for nom, variant in variantlar:
        assert nom, "har bir variantning nomi bo'lishi kerak"
        assert dataclasses.is_dataclass(variant)


def test_hozirgi_holat_ham_olchanadi(config) -> None:  # noqa: ANN001
    """Taqqoslashda O'ZGARTIRILMAGAN sozlama ham bo'lishi SHART.

    Ansiz "yaxshiroq" degan so'zning ma'nosi qolmaydi: nimadan
    yaxshiroq?
    """
    variantlar = _variantlar(config)
    asoslar = [v for _nom, v in variantlar if v == config]

    assert asoslar, "o'zgartirilmagan sozlama variantlar ichida yo'q"


def test_har_bir_variant_bitta_narsani_ozgartiradi(config) -> None:  # noqa: ANN001
    """Bir vaqtda ikkita sozlama o'zgarsa, qaysi biri ta'sir qilgani
    noma'lum bo'lib qoladi.

    Bu taqqoslashning eng asosiy sharti: bitta o'zgaruvchi.
    """
    olchanadigan = [
        lambda c: c.analysis.require_htf_alignment,
        lambda c: c.analysis.indicators.require_confirmation,
        lambda c: c.analysis.indicators.adx_trend_threshold,
        lambda c: c.analysis.support_resistance.entry_max_range_pct,
    ]

    for nom, variant in _variantlar(config):
        farqlar = [o for o in olchanadigan if o(variant) != o(config)]
        assert len(farqlar) <= 1, f"{nom}: bir vaqtda {len(farqlar)} sozlama o'zgargan"


def test_variantlar_bir_biriga_tasir_qilmaydi(config) -> None:  # noqa: ANN001
    """Sozlama nusxalanadi, umumiy obyekt o'zgartirilmaydi.

    Aks holda ro'yxatdagi keyingi variant oldingisining sozlamasi
    bilan ishlab ketardi va taqqoslash yolg'on natija berardi.
    """
    _variantlar(config)

    assert not config.analysis.require_htf_alignment, "asos sozlama o'zgardi"
    assert not config.analysis.indicators.require_confirmation
    assert config.analysis.indicators.adx_trend_threshold == 20.0
    assert config.analysis.support_resistance.entry_max_range_pct == 55.0


def test_rad_etilgan_gipotezalar_yoqilmagan(config) -> None:  # noqa: ANN001
    """Ikki gipoteza backtest bilan RAD ETILDI — ular yopiq qolsin.

    `correction_entry` (natija #1) va `tp2_from_structure` (natija
    #2). Ularni jimgina qayta yoqib qo'yish — o'lchovni bekor
    qilish demakdir.
    """
    assert not config.strategies.correction_entry.enabled
    assert not config.trade_rules.tp2_from_structure

    for nom, variant in _variantlar(config):
        assert not variant.strategies.correction_entry.enabled, nom
        assert not variant.trade_rules.tp2_from_structure, nom


def test_boshqa_sozlamalar_tegilmaydi(config) -> None:  # noqa: ANN001
    """Faqat o'lchanayotgan narsa o'zgaradi — taqqoslash halol bo'lsin."""
    for _nom, variant in _variantlar(config):
        assert variant.scoring == config.scoring
        assert variant.market_health == config.market_health
        assert variant.backtest == config.backtest
        assert variant.risk_engine == config.risk_engine


def test_xarajat_barcha_variantda_bir_xil(config) -> None:  # noqa: ANN001
    """Komissiya va sirg'anish variantga qarab o'zgarmasligi kerak.

    Aks holda "yaxshiroq" variant shunchaki arzonroq hisoblangan
    bo'lardi.
    """
    for _nom, variant in _variantlar(config):
        assert variant.backtest.round_trip_cost_pct == (
            config.backtest.round_trip_cost_pct
        )
        assert variant.backtest.round_trip_cost_pct > 0, "savdo bepul emas"


# --------------------------------------------------------------------------- #
#  Ma'lumot: o'chirilgan strategiya ham timeframe talab qiladi
# --------------------------------------------------------------------------- #


def test_ochirilgan_strategiyaning_timeframei_ham_yuklanadi(config) -> None:  # noqa: ANN001
    """Bu — tizimdagi tuzoq.

    `correction_entry` konfiguratsiyada o'chirilgan. Agar ma'lumot
    faqat YOQILGAN strategiyalarga qarab yuklansa, taqqoslashda yangi
    variant uchun 4h/15m/1d shamlari umuman bo'lmasdi — u nol savdo
    qaytarardi va biz buni "strategiya yomon" deb o'qib qo'yardik.
    """
    ce = config.strategies.correction_entry
    assert not ce.enabled, "sinov shartini tekshiradi: strategiya o'chirilgan"

    timeframelar = _kerakli_timeframelar(config)

    assert ce.zone_timeframe in timeframelar
    assert ce.confirm_timeframe in timeframelar
    assert ce.trend_timeframe in timeframelar


# --------------------------------------------------------------------------- #
#  Offline rejim
# --------------------------------------------------------------------------- #


def test_offline_yetishmagan_fayllarni_aytadi(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    """Tarmoqsiz muhitda xato ANIQ bo'lishi kerak.

    "Yuklab bo'lmadi" degan umumiy xabar foydasiz — qaysi fayl
    yetishmayotgani aytilsa, uni boshqa mashinada yig'ib ko'chirish
    mumkin.
    """
    import scripts.backtest as bt

    monkeypatch.setattr(bt, "KESH", tmp_path / "candles")

    with pytest.raises(KeshYetishmaydi) as xato:
        _keshdan_yigish(["BTC", "ETH"], ["4h"])

    matn = str(xato.value)
    assert "BTC_4h.json" in matn
    assert "ETH_4h.json" in matn


def test_offline_keshdan_oqiydi(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    from datetime import UTC, datetime, timedelta

    import scripts.backtest as bt
    from core.domain.models import Candle

    kesh = tmp_path / "candles"
    monkeypatch.setattr(bt, "KESH", kesh)

    bosh = datetime(2025, 1, 1, tzinfo=UTC)
    shamlar = [
        Candle(
            open_time=bosh + timedelta(hours=4 * i),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
        )
        for i in range(5)
    ]
    bt._keshga_yozish("BTC", "4h", shamlar)

    dataset = _keshdan_yigish(["BTC"], ["4h"])

    assert dataset.symbols == ["BTC"]
    assert len(dataset.series["BTC"].candles["4h"]) == 5


# --------------------------------------------------------------------------- #
#  Uchidan uchiga: taqqoslash haqiqatda ishga tushadimi
# --------------------------------------------------------------------------- #


def test_har_bir_variant_backtestda_ishga_tushadi() -> None:
    """MEXANIZM sinovi — strategiyani baholash EMAS.

    Sun'iy qatorda chiqqan raqamlar hech narsani isbotlamaydi va ular
    tekshirilmaydi ham. Tekshiriladigan narsa bitta: `--compare`
    zanjiri boshidan oxirigacha uziladimi yoki yo'q. Eski versiyada
    aynan shu uzilardi va buni bilish uchun avval bir soatlik ma'lumot
    yuklash kerak bo'lardi.
    """
    import dataclasses as dc

    from core.analysis.strategies import build_strategies, required_timeframes
    from core.backtest import Backtester, build_dataset
    from tests.core.test_backtest import savdo_beradigan_qator, tez_config

    asos = tez_config()
    # Korreksiya strategiyasining timeframelari ham sinov qatoriga
    # moslashtiriladi, aks holda u ma'lumot yo'qligidan to'xtardi.
    ce = dc.replace(
        asos.strategies.correction_entry,
        zone_timeframe="15m",
        confirm_timeframe="15m",
        trend_timeframe="30m",
        impulse_lookback=30,
        confirm_lookback=10,
    )
    asos = dc.replace(
        asos, strategies=dc.replace(asos.strategies, correction_entry=ce)
    )

    kerakli = required_timeframes(build_strategies(asos, enabled_only=False))
    kerakli |= {asos.analysis.entry_timeframe, asos.analysis.market_health_timeframe}
    kerakli |= set(asos.analysis.htf_confirmation)
    dataset = build_dataset({"BTC": savdo_beradigan_qator()}, "15m", sorted(kerakli))

    for nom, variant in _variantlar(asos):
        natija = Backtester(variant, label=nom).run(dataset, max_steps=300)
        assert natija.label == nom
        assert natija.steps > 0, f"{nom}: birorta qadam bajarilmadi"


# --------------------------------------------------------------------------- #
#  Backtest jonli tizim bilan BIR XIL narsani o'lchashi kerak
# --------------------------------------------------------------------------- #


def test_salomatlik_timeframei_ham_yuklanadi(config) -> None:  # noqa: ANN001
    """Indeks timeframei hech bir strategiyaning ro'yxatida yo'q.

    U strategiyadan tashqarida hisoblanadi — lekin aynan u rejimni
    tanlaydi. Yuklanmasa, backtest indeksni boshqa timeframedan
    o'lchardi va butun taqqoslash boshqa savolga javob berardi.
    """
    timeframelar = _kerakli_timeframelar(config)

    assert config.analysis.market_health_timeframe in timeframelar
    assert config.analysis.entry_timeframe in timeframelar
    for tf in config.analysis.htf_confirmation:
        assert tf in timeframelar


def test_indeks_oz_timeframeida_olchanadi() -> None:
    """Jonli tizim HAFTALIK strukturani ko'radi — backtest ham shunday.

    Ilgari backtest kirish timeframeidan (4h) o'lchardi. Indeks butun
    rejim tanlovini boshqarganidan keyin bu farq javobni ishonchsiz
    qilardi: o'lchanayotgan narsa jonlidagi narsa emas edi.

    Sinov shunday qurilgan: 4 soatlik qator KO'TARILISHDA, haftalik
    qator PASAYISHDA. Agar struktura noto'g'ri timeframedan olinsa,
    kenglik 100% chiqadi va indeks baland bo'ladi.
    """
    from datetime import UTC, datetime, timedelta

    from core.analysis.market_structure import analyze_structure
    from core.backtest import Backtester, Dataset
    from core.domain.enums import TrendDirection
    from core.domain.models import Candle
    from core.signals import SignalTracker

    bosh = datetime(2025, 1, 1, tzinfo=UTC)

    def qator(n: int, qadam: float, soat: int) -> list[Candle]:
        shamlar = []
        narx = 100.0
        for i in range(n):
            keyingi = narx + qadam if i % 3 else narx + qadam * 0.4
            shamlar.append(
                Candle(
                    open_time=bosh + timedelta(hours=soat * i),
                    open=narx,
                    high=max(narx, keyingi) + 0.5,
                    low=min(narx, keyingi) - 0.5,
                    close=keyingi,
                    volume=1000.0,
                )
            )
            narx = keyingi
        return shamlar

    config = load_config()
    kirish_tf = config.analysis.entry_timeframe
    salomatlik_tf = config.analysis.market_health_timeframe

    ds = Dataset()
    ds.add("BTC", kirish_tf, qator(200, +2.0, 4))
    ds.add("BTC", salomatlik_tf, qator(200, -2.0, 168))

    lahza = bosh + timedelta(days=400)

    # Sinov sharti: ikki qator HAQIQATAN qarama-qarshi
    oyna = ds.window("BTC", lahza)
    assert analyze_structure(oyna[kirish_tf]).direction is TrendDirection.UP
    assert analyze_structure(oyna[salomatlik_tf]).direction is not TrendDirection.UP

    kirish = Backtester(config)._build_input(
        ds, lahza, SignalTracker(config), {}, kirish_tf
    )

    assert kirish.market_health is not None
    assert kirish.market_health.value < 60, (
        "haftalik qator pasayishda — indeks baland bo'lsa, struktura "
        "kirish timeframeidan olinyapti"
    )


def test_qt_davri_uchun_etalon_shamlar_beriladi() -> None:
    """QT omili backtestda HAR DOIM neytral qolardi.

    `reference_candles` umuman berilmasdi, ya'ni jonli tizimda ballga
    ta'sir qiladigan omil sinovda o'lchanmasdi. Sinov natijasi esa
    aynan jonli xatti-harakatni bashorat qilishi kerak.
    """
    from datetime import UTC, datetime, timedelta

    from core.backtest import Backtester, Dataset
    from core.domain.models import Candle

    bosh = datetime(2025, 1, 1, tzinfo=UTC)
    config = load_config()
    etalon = config.risk_engine.btc_filter.reference_symbol.upper()

    shamlar = [
        Candle(
            open_time=bosh + timedelta(hours=168 * i),
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=1000.0,
        )
        for i in range(80)
    ]
    ds = Dataset()
    ds.add(etalon, config.analysis.market_health_timeframe, shamlar)

    lahza = bosh + timedelta(days=400)
    olingan = Backtester(config)._etalon_shamlar(
        ds, lahza, config.analysis.market_health_timeframe
    )

    assert olingan, "etalon shamlar berilishi kerak"
    assert all(s.open_time <= lahza for s in olingan), "kelajakka qaralmasin"

    # Etalon coin dataset'da bo'lmasa — bo'sh, ya'ni davr aniqlanmaydi
    assert Backtester(config)._etalon_shamlar(
        Dataset(), bosh, config.analysis.market_health_timeframe
    ) == []
