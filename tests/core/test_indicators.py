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
    macd,
    rsi,
    rsi_recovering_from_oversold,
    volume_average,
    volume_ratio,
)
from core.config.schema import IndicatorConfig
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


# --------------------------------------------------------------------------- #
#  Hajm
# --------------------------------------------------------------------------- #


def test_hajm_ortachasi_oxirgi_shamni_hisobga_olmaydi() -> None:
    """Aks holda katta hajm o'rtachani ko'tarib, farqni yashirardi."""
    hajmlar = [100.0] * 20 + [10000.0]
    shamlar = qator([100.0] * 21, hajmlar)

    assert volume_average(shamlar, 20) == pytest.approx(100.0)
    assert volume_ratio(shamlar, 20) == pytest.approx(100.0)


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

    # Uchta omil qoldi: RSI, MACD, hajm. Trend omili EMA bilan birga
    # olib tashlandi — yo'nalishni endi SMC strukturasi aytadi.
    assert hukm.confirmed_count >= 2, hukm.describe()
    assert {o.name for o in hukm.factors} == {"rsi", "macd", "volume"}


def test_tushayotgan_bozorda_momentum_tasdiqlamaydi(config: IndicatorConfig) -> None:
    """Trend omili EMA bilan birga olib tashlandi — MACD tekshiriladi."""
    tushish = [sham(i, 300 - i * 0.5) for i in range(250)]
    hukm = confirm(build_snapshot(tushish, config), config, zone_ready=True)

    assert not hukm.is_confirmed
    assert not hukm.factor("macd").confirmed


def test_trend_omili_endi_yoq(config: IndicatorConfig) -> None:
    """EMA olib tashlandi — u bilan birga "trend" tasdiq omili ham.

    Trend YO'NALISHI endi tasdiqlash qatlamida emas, SMC strukturasida
    (`market_structure.py`) va u to'g'ridan-to'g'ri ball omiliga
    kiradi (`score_trend`).
    """
    hukm = confirm(build_snapshot(kotarilish_shamlari(), config), config, zone_ready=True)
    assert hukm.factor("trend") is None


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


def test_hukm_tushuntirish_beradi(config: IndicatorConfig) -> None:
    """3.6-band: "Nega bu signal?" tugmasi shu matndan to'ladi."""
    hukm = confirm(build_snapshot(kotarilish_shamlari(), config), config, zone_ready=True)
    matn = hukm.describe()

    assert "MACD:" in matn
    assert "RSI:" in matn
    assert "MACD:" in matn
    assert "Hajm:" in matn


# --------------------------------------------------------------------------- #
#  Qat'iy EMA talabi va uning "pullback" bilan ziddiyati
# --------------------------------------------------------------------------- #


