"""3.1-band: indikatorlar — S/R ni TASDIQLOVCHI qatlam.

Hisob-kitob to'g'riligi ma'lum misollar bilan tekshiriladi: indikator
xatosi butun strategiyani jimgina buzadi va backtest natijalarini
soxtalashtiradi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.indicators import (
    adx,
    build_snapshot,
    confirm,
    ema,
    ema_series,
    is_trending,
    macd,
    rsi,
    rsi_recovering_from_oversold,
    timeframe_trend,
    trend_direction,
    volume_average,
    volume_confirms,
    volume_ratio,
)
from core.config.schema import IndicatorConfig
from core.domain.enums import TrendDirection
from core.domain.models import Candle

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(i: int, close: float, high: float | None = None,
         low: float | None = None, volume: float = 1000.0) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(hours=i),
        open=close,
        high=high if high is not None else close * 1.005,
        low=low if low is not None else close * 0.995,
        close=close,
        volume=volume,
    )


def qator(narxlar: list[float], hajmlar: list[float] | None = None) -> list[Candle]:
    return [
        sham(i, narx, volume=hajmlar[i] if hajmlar else 1000.0)
        for i, narx in enumerate(narxlar)
    ]


# --------------------------------------------------------------------------- #
#  EMA — ma'lum misol bilan tekshiruv
# --------------------------------------------------------------------------- #

MASHHUR_NARXLAR = [
    22.27, 22.19, 22.08, 22.17, 22.18, 22.13, 22.23, 22.43,
    22.24, 22.29, 22.15, 22.39, 22.38, 22.61, 23.36,
]


def test_ema_malum_misolga_mos() -> None:
    """StockCharts'ning klassik EMA(10) misoli."""
    qiymatlar = ema_series(MASHHUR_NARXLAR, 10)
    kutilgan = [22.22, 22.21, 22.24, 22.27, 22.33, 22.52]
    olingan = [round(q, 2) for q in qiymatlar[9:]]
    assert olingan == kutilgan


def test_ema_birinchi_qiymat_sma() -> None:
    """EMA'ni birinchi narxdan boshlash uzoq vaqt noto'g'ri natija berardi."""
    qiymatlar = ema_series([10, 20, 30, 40], 4)
    assert qiymatlar[:3] == [None, None, None]
    assert qiymatlar[3] == pytest.approx(25.0)


def test_ema_malumot_yetmasa_none() -> None:
    assert ema([1, 2, 3], 10) is None
    assert ema([], 10) is None


def test_ema_notogri_davr_rad_etiladi() -> None:
    with pytest.raises(ValueError, match="musbat"):
        ema_series([1, 2, 3], 0)


# --------------------------------------------------------------------------- #
#  Trend yo'nalishi (3.1-band qat'iy sharti)
# --------------------------------------------------------------------------- #


def test_kotarilish_trendi_uchta_shart_bilan() -> None:
    """Narx ikkala EMA'dan yuqori VA tez EMA sekinidan baland."""
    assert trend_direction(110, ema_fast=105, ema_slow=100) is TrendDirection.UP


@pytest.mark.parametrize(
    ("narx", "tez", "sekin", "izoh"),
    [
        (95, 105, 100, "narx EMA'lardan past"),
        (110, 100, 105, "tez EMA sekinidan past"),
        (102, 105, 100, "narx tez EMA'dan past"),
    ],
)
def test_kotarilish_trendi_bir_shart_buzilsa_yoq(
    narx: float, tez: float, sekin: float, izoh: str
) -> None:
    assert trend_direction(narx, tez, sekin) is not TrendDirection.UP, izoh


def test_ema_hisoblanmasa_trend_flat() -> None:
    """0.3-band: noaniqlik "trend bor" degani emas."""
    assert trend_direction(100, None, None) is TrendDirection.FLAT
    assert timeframe_trend(qator([100] * 10), fast=50, slow=200) is TrendDirection.FLAT


def test_timeframe_trendi_kotarilishda() -> None:
    kotarilish = qator([100 + i * 0.5 for i in range(250)])
    assert timeframe_trend(kotarilish, fast=50, slow=200) is TrendDirection.UP


# --------------------------------------------------------------------------- #
#  RSI
# --------------------------------------------------------------------------- #

RSI_NARXLAR = [
    44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
    45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
]


def test_rsi_qolda_hisobga_mos() -> None:
    """avg_gain=3.34/14, avg_loss=1.40/14 -> RSI = 70.46."""
    assert rsi(RSI_NARXLAR, 14) == pytest.approx(70.46, abs=0.01)


def test_rsi_faqat_osish_bolsa_yuz() -> None:
    """Nolga bo'lish o'rniga aniq qiymat."""
    assert rsi([float(i) for i in range(1, 30)], 14) == 100.0


def test_rsi_ozgarish_bolmasa_ellik() -> None:
    assert rsi([100.0] * 30, 14) == 50.0


def test_rsi_malumot_yetmasa_none() -> None:
    assert rsi([1, 2, 3], 14) is None


def test_rsi_qaytish_aniqlanadi() -> None:
    """3.1-band: RSI 30dan QAYTISH — unda turish emas."""
    tushib_qaytgan = [100.0] * 20 + [100 - i * 2 for i in range(1, 12)] + [82, 85, 88]
    assert rsi_recovering_from_oversold(tushib_qaytgan, 14, oversold=30, lookback=5)


def test_rsi_pastda_turgani_qaytish_emas() -> None:
    tushayotgan = [100 - i for i in range(40)]
    assert not rsi_recovering_from_oversold(tushayotgan, 14, oversold=30, lookback=5)


# --------------------------------------------------------------------------- #
#  MACD
# --------------------------------------------------------------------------- #


def test_macd_kotarilishda_musbat() -> None:
    """Tezlashayotgan ko'tarilishda MACD ham musbat, ham signal chiziqdan yuqori."""
    kotarilish = [100 + i * 1.05 ** (i / 10) for i in range(60)]
    natija = macd(kotarilish, 12, 26, 9)

    assert natija is not None
    assert natija.macd > 0
    assert natija.above_zero
    assert natija.is_bullish


def test_togri_chiziqda_macd_neytral() -> None:
    """Chekka holat: mutlaqo bir tekis o'sishda MACD va signal tenglashadi.

    Momentum o'zgarmayotgani uchun MACD hech qanday afzallik bermaydi —
    bu to'g'ri xatti-harakat, uni "ko'tarilish" deb hisoblash xato bo'lardi.
    """
    natija = macd([100 + i for i in range(60)], 12, 26, 9)

    assert natija.macd > 0, "MACD nol chizig'idan yuqorida"
    assert natija.above_zero
    assert natija.histogram == pytest.approx(0.0)
    assert not natija.is_bullish, "signal chiziqdan ustun emas -> tasdiq yo'q"


def test_macd_tushishda_manfiy() -> None:
    tushish = [200 - i for i in range(60)]
    natija = macd(tushish, 12, 26, 9)
    assert natija.macd < 0
    assert not natija.is_bullish


def test_macd_kesish_aniqlanadi() -> None:
    """Tushishdan keyin ko'tarilish — signal chiziq pastdan kesiladi."""
    narxlar = [200 - i for i in range(50)] + [150 + i * 3 for i in range(20)]
    natija = macd(narxlar, 12, 26, 9)
    assert natija is not None
    # Kesish yoki allaqachon yuqorida bo'lishi kerak
    assert natija.bullish_cross or natija.is_bullish


def test_macd_malumot_yetmasa_none() -> None:
    assert macd([100.0] * 20, 12, 26, 9) is None


def test_macd_notogri_davrlar_rad_etiladi() -> None:
    with pytest.raises(ValueError, match="kichik"):
        macd([100.0] * 100, fast=26, slow=12)


# --------------------------------------------------------------------------- #
#  ADX
# --------------------------------------------------------------------------- #


def test_adx_kuchli_trendda_yuqori() -> None:
    kuchli = [sham(i, 100 + i * 2) for i in range(60)]
    qiymat = adx(kuchli, 14)

    assert qiymat is not None
    assert qiymat > 25, f"kuchli trendda ADX yuqori bo'lishi kerak: {qiymat}"


def test_adx_tekis_bozorda_past() -> None:
    """4.4-band: tekis bozorda signal berilmaydi."""
    tekis = [sham(i, 100 + (1 if i % 2 else -1)) for i in range(60)]
    qiymat = adx(tekis, 14)

    assert qiymat is not None
    assert qiymat < 25, f"tekis bozorda ADX past bo'lishi kerak: {qiymat}"


def test_adx_malumot_yetmasa_none() -> None:
    assert adx([sham(i, 100) for i in range(10)], 14) is None


def test_trendda_ekanini_aniqlash() -> None:
    kuchli = [sham(i, 100 + i * 2) for i in range(60)]
    tekis = [sham(i, 100 + (1 if i % 2 else -1)) for i in range(60)]

    assert is_trending(kuchli, 14, threshold=20) is True
    assert is_trending(tekis, 14, threshold=20) is False
    assert is_trending([sham(0, 100)], 14, threshold=20) is None


# --------------------------------------------------------------------------- #
#  Hajm
# --------------------------------------------------------------------------- #


def test_hajm_ortachasi_oxirgi_shamni_hisobga_olmaydi() -> None:
    """Aks holda katta hajm o'rtachani ko'tarib, farqni yashirardi."""
    hajmlar = [100.0] * 20 + [10000.0]
    shamlar = qator([100.0] * 21, hajmlar)

    assert volume_average(shamlar, 20) == pytest.approx(100.0)
    assert volume_ratio(shamlar, 20) == pytest.approx(100.0)


def test_hajm_tasdigi() -> None:
    kuchli = qator([100.0] * 21, [100.0] * 20 + [200.0])
    zaif = qator([100.0] * 21, [100.0] * 20 + [50.0])

    assert volume_confirms(kuchli, 20)
    assert not volume_confirms(zaif, 20)


def test_hajm_malumot_yetmasa_tasdiq_yoq() -> None:
    """0.3-band: noaniqlik tasdiq emas."""
    assert volume_average(qator([100.0] * 5), 20) is None
    assert not volume_confirms(qator([100.0] * 5), 20)


# --------------------------------------------------------------------------- #
#  Snapshot
# --------------------------------------------------------------------------- #


@pytest.fixture
def config() -> IndicatorConfig:
    return IndicatorConfig()


def test_snapshot_barcha_qiymatlarni_yigadi(config: IndicatorConfig) -> None:
    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    holat = build_snapshot(shamlar, config)

    assert holat is not None
    assert holat.is_complete
    assert holat.trend is TrendDirection.UP


def test_snapshot_malumot_yetmasa_toliq_emas(config: IndicatorConfig) -> None:
    holat = build_snapshot([sham(i, 100) for i in range(30)], config)
    assert holat is not None
    assert not holat.is_complete, "to'liq bo'lmagan snapshot bilan signal berilmaydi"


def test_snapshot_bosh_royxatda_none(config: IndicatorConfig) -> None:
    assert build_snapshot([], config) is None


# --------------------------------------------------------------------------- #
#  TASDIQLASH QATLAMI — 3.1-bandning markaziy qoidasi
# --------------------------------------------------------------------------- #


def kotarilish_shamlari(n: int = 250) -> list[Candle]:
    """Tezlashayotgan ko'tarilish, oxirida hajm sakraydi.

    Bir tekis chiziq emas: MACD momentum o'zgarishiga tayanadi, mutlaqo
    tekis o'sishda esa momentum o'zgarmaydi.
    """
    narxlar = [100 + i * 0.5 + (i / 40) ** 2 for i in range(n)]
    shamlar = [sham(i, narx) for i, narx in enumerate(narxlar[:-1])]
    shamlar.append(sham(n - 1, narxlar[-1], volume=2500.0))
    return shamlar


def test_zona_tayyor_bolmasa_indikatorlar_yetarli_emas(config: IndicatorConfig) -> None:
    """3.1-bandning ENG MUHIM qoidasi.

    Indikatorlar qanchalik yaxshi bo'lmasin, narx kerakli S/R zonasida
    bo'lmasa signal YO'Q. Yolg'iz indikator-asosli signal taqiqlangan.
    """
    holat = build_snapshot(kotarilish_shamlari(), config)
    hukm = confirm(holat, config, zone_ready=False)

    assert not hukm.is_confirmed
    assert "S/R zonasida emas" in hukm.describe()


def test_zona_tayyor_va_indikatorlar_tasdiqlasa_signal(config: IndicatorConfig) -> None:
    holat = build_snapshot(kotarilish_shamlari(), config)
    hukm = confirm(holat, config, zone_ready=True)

    assert hukm.confirmed_count >= 3, hukm.describe()


def test_tushayotgan_bozorda_trend_tasdiqlamaydi(config: IndicatorConfig) -> None:
    tushish = [sham(i, 300 - i * 0.5) for i in range(250)]
    hukm = confirm(build_snapshot(tushish, config), config, zone_ready=True)

    assert not hukm.is_confirmed
    assert not hukm.factor("trend").confirmed


def test_zaif_hajm_tasdiqlamaydi(config: IndicatorConfig) -> None:
    shamlar = kotarilish_shamlari()[:-1]
    shamlar.append(sham(249, shamlar[-1].close, volume=200.0))  # hajm keskin tushdi

    hukm = confirm(build_snapshot(shamlar, config), config, zone_ready=True)
    assert not hukm.factor("volume").confirmed


def test_haddan_tashqari_sotib_olinganda_rsi_rad_etadi(config: IndicatorConfig) -> None:
    """RSI juda yuqori bo'lsa kirish uchun kech."""
    keskin = [sham(i, 100 * (1.03 ** i)) for i in range(250)]
    holat = build_snapshot(keskin, config)

    hukm = confirm(holat, config, zone_ready=True)
    if holat.rsi and holat.rsi >= config.rsi_overbought:
        assert not hukm.factor("rsi").confirmed
        assert "kech" in hukm.factor("rsi").explanation


def test_omillar_darajali_baholanadi(config: IndicatorConfig) -> None:
    """3.5-band: "bor/yo'q" emas, darajali (graduated)."""
    hukm = confirm(build_snapshot(kotarilish_shamlari(), config), config, zone_ready=True)

    for omil in hukm.factors:
        assert 0.0 <= omil.strength <= 1.0, f"{omil.name}: {omil.strength}"


def test_trend_kuchi_timeframedan_mustaqil(config: IndicatorConfig) -> None:
    """28-bo'lim: trend kuchi ATR birligida o'lchanadi, foizda emas.

    Bir xil SHAKLDAGI, lekin har xil volatillikdagi ikki qator bir xil
    trend kuchini berishi kerak. Foiz bilan o'lchanganda bunday bo'lmasdi:
    past timeframeda EMA50—EMA200 ajralishi 0.2%, kunlikda 15% — bitta
    foiz chegarasi ikkalasiga ham to'g'ri kelmaydi va past timeframeda bu
    omil doim nolga yaqin bo'lib qolardi.
    """
    mayin = [sham(i, 100 + i * 0.01) for i in range(250)]
    keskin = [
        Candle(
            open_time=sham_obyekti.open_time,
            open=sham_obyekti.open,
            high=sham_obyekti.close * 1.02,
            low=sham_obyekti.close * 0.98,
            close=sham_obyekti.close,
            volume=sham_obyekti.volume,
        )
        for sham_obyekti in mayin
    ]

    mayin_kuch = confirm(build_snapshot(mayin, config), config, zone_ready=True).factor(
        "trend"
    )
    keskin_kuch = confirm(build_snapshot(keskin, config), config, zone_ready=True).factor(
        "trend"
    )

    assert mayin_kuch.confirmed and keskin_kuch.confirmed
    # Keskin qatorda ATR kattaroq -> bir xil EMA ajralishi kamroq ATR beradi.
    assert keskin_kuch.strength < mayin_kuch.strength


def test_trend_kuchi_sozlanadigan_chegara_bilan_olchanadi() -> None:
    """Sehrli raqam yo'q (6.4-band): chegara konfiguratsiyadan keladi."""
    shamlar = [sham(i, 100 + i * 0.01) for i in range(250)]

    keng = IndicatorConfig(ema_separation_full_atr=10.0)
    tor = IndicatorConfig(ema_separation_full_atr=0.2)

    keng_kuch = confirm(build_snapshot(shamlar, keng), keng, zone_ready=True).factor("trend")
    tor_kuch = confirm(build_snapshot(shamlar, tor), tor, zone_ready=True).factor("trend")

    assert keng_kuch.strength < tor_kuch.strength
    assert tor_kuch.strength == 1.0, "past chegarada to'liq ball berilishi kerak"


def test_atr_yoq_bolsa_trend_kuchi_nol(config: IndicatorConfig) -> None:
    """0.3-band: o'lchab bo'lmasa, qo'shimcha ball berilmaydi."""
    import dataclasses

    holat = build_snapshot([sham(i, 100 + i * 0.01) for i in range(250)], config)
    atrsiz = dataclasses.replace(holat, atr=None)

    omil = confirm(atrsiz, config, zone_ready=True).factor("trend")

    assert omil.confirmed, "yo'nalish hali ham tasdiqlangan"
    assert omil.strength == 0.0


def test_hukm_tushuntirish_beradi(config: IndicatorConfig) -> None:
    """3.6-band: "Nega bu signal?" tugmasi shu matndan to'ladi."""
    hukm = confirm(build_snapshot(kotarilish_shamlari(), config), config, zone_ready=True)
    matn = hukm.describe()

    assert "Trend:" in matn
    assert "RSI:" in matn
    assert "MACD:" in matn
    assert "Hajm:" in matn


# --------------------------------------------------------------------------- #
#  Qat'iy EMA talabi va uning "pullback" bilan ziddiyati
# --------------------------------------------------------------------------- #


def test_qatiy_talab_pullbackni_rad_etadi() -> None:
    """3.1-banddagi qat'iy talab: narx IKKALA EMA'dan yuqori bo'lishi shart.

    Support zonasiga qaytish deyarli har doim narxni EMA50 dan pastga
    tushiradi — shuning uchun qat'iy talab bilan bunday kirish rad etiladi.
    Bu — spetsifikatsiyaning ataylab tanlangan xatti-harakati, xato emas.
    """
    natija = trend_direction(
        price=61_141, ema_fast=61_387, ema_slow=58_876, require_price_above_fast=True
    )
    assert natija is TrendDirection.FLAT


def test_yumshoq_talab_pullbackni_qabul_qiladi() -> None:
    """`false` bo'lsa: trend tuzilishi saqlanadi, pasayish imkoniyat deb qaraladi."""
    natija = trend_direction(
        price=61_141, ema_fast=61_387, ema_slow=58_876, require_price_above_fast=False
    )
    assert natija is TrendDirection.UP


def test_yumshoq_talabda_ham_tuzilma_buzilsa_trend_yoq() -> None:
    """EMA50 < EMA200 bo'lsa — tuzilma tushishda, yumshatish yordam bermaydi."""
    natija = trend_direction(
        price=61_141, ema_fast=58_000, ema_slow=60_000, require_price_above_fast=False
    )
    assert natija is not TrendDirection.UP


def test_yumshoq_talabda_narx_ema200_dan_past_bolsa_trend_yoq() -> None:
    natija = trend_direction(
        price=57_000, ema_fast=61_387, ema_slow=58_876, require_price_above_fast=False
    )
    assert natija is not TrendDirection.UP


def test_snapshot_konfiguratsiyadan_bayroqni_oladi() -> None:
    yumshoq = IndicatorConfig(trend_requires_price_above_fast=False)
    shamlar = [sham(i, 100 + i * 0.5) for i in range(250)]
    assert build_snapshot(shamlar, yumshoq).require_price_above_fast is False
