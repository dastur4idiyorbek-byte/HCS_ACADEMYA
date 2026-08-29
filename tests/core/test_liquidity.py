"""LIT (Liquidity Sweep) va MSNR (daraja turlari) — CryptoSpot3% 1- va 3-qism.

Shamlar sun'iy: har bir test aynan bitta naqshni quradi va uni
aniqlanganini (yoki aniqlanmaganini) tekshiradi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.analysis.level_types import LevelType, classify_level_type
from core.analysis.market_structure import analyze_structure
from core.analysis.support_resistance import detect_liquidity_sweep
from core.config.schema import LiquiditySweepConfig
from core.domain.enums import ZoneKind
from core.domain.models import Candle, SRZone

BOSH = datetime(2026, 1, 1, tzinfo=UTC)
SOZLAMA = LiquiditySweepConfig(
    enabled=True, lookback_bars=30, min_sweep_pct=0.3, max_reclaim_bars=3
)


def sham(
    index: int, high: float, low: float, close: float, open_: float | None = None
) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(hours=index),
        open=open_ if open_ is not None else close,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
    )


def support(low: float = 99.0, high: float = 101.0) -> SRZone:
    return SRZone(kind=ZoneKind.SUPPORT, low=low, high=high, touches=3)


def tekis(n: int, narx: float = 105.0) -> list[Candle]:
    return [sham(i, narx + 0.5, narx - 0.5, narx) for i in range(n)]


# --------------------------------------------------------------------------- #
#  LIT — Liquidity Sweep
# --------------------------------------------------------------------------- #


def test_yalab_otib_qaytish_aniqlanadi() -> None:
    """Soya zona pastiga kirdi, yopilish zona ichida — naqsh to'liq."""
    shamlar = tekis(20)
    # 99.0 dan 0.5% pastga (98.5) soya tashlab, 100 da yopiladi
    shamlar.append(sham(20, 101.0, 98.5, 100.0))
    shamlar += tekis(2, 102.0)

    natija = detect_liquidity_sweep(shamlar, support(), SOZLAMA)

    assert natija is not None
    assert natija.swept_price == 98.5
    assert natija.depth_pct > 0.3


def test_qaytmasa_naqsh_yoq() -> None:
    """Narx buzib tushib qolgan bo'lsa — bu sweep emas, oddiy pasayish."""
    shamlar = tekis(20)
    shamlar.append(sham(20, 100.0, 98.0, 98.2))
    shamlar += [sham(21 + i, 98.5, 97.0, 97.5) for i in range(5)]

    assert detect_liquidity_sweep(shamlar, support(), SOZLAMA) is None


def test_sayoz_tegish_yalash_hisoblanmaydi() -> None:
    """Chegaradan sal pastga tushish har kuni bo'ladi — bu dalil emas."""
    shamlar = tekis(20)
    shamlar.append(sham(20, 101.0, 98.95, 100.0))  # atigi 0.05%

    assert detect_liquidity_sweep(shamlar, support(), SOZLAMA) is None


def test_kech_qaytish_qabul_qilinmaydi() -> None:
    """Qaytish `max_reclaim_bars` ichida bo'lishi kerak."""
    shamlar = tekis(20)
    shamlar.append(sham(20, 100.0, 98.0, 98.2))
    shamlar += [sham(21 + i, 98.6, 98.0, 98.3) for i in range(5)]
    # Qaytish sodir bo'ldi, lekin YALASHDAN KEYIN 6 sham o'tgan.
    # Diqqat: bu sham zonaga qayta kirmasligi kerak — aks holda u
    # o'zi yangi (va haqiqiy) sweep bo'lib qolardi.
    shamlar.append(sham(26, 101.0, 99.2, 100.5))

    assert detect_liquidity_sweep(shamlar, support(), SOZLAMA) is None


def test_eng_songgi_yalash_qaytariladi() -> None:
    """Eski yalash bugungi kirish uchun dalil emas."""
    shamlar = tekis(10)
    shamlar.append(sham(10, 101.0, 98.0, 100.0))  # eski
    shamlar += tekis(5)
    shamlar.append(sham(16, 101.0, 97.5, 100.0))  # yangi
    shamlar += tekis(2)

    natija = detect_liquidity_sweep(shamlar, support(), SOZLAMA)

    assert natija is not None
    assert natija.swept_price == 97.5


def test_ochirilgan_sozlama_hech_narsa_qaytarmaydi() -> None:
    shamlar = tekis(20) + [sham(20, 101.0, 98.5, 100.0)]
    ochiq = LiquiditySweepConfig(enabled=False)

    assert detect_liquidity_sweep(shamlar, support(), ochiq) is None


def test_bosh_royxat_xato_bermaydi() -> None:
    assert detect_liquidity_sweep([], support(), SOZLAMA) is None


def test_resistance_zonasi_yuqoridan_yalanadi() -> None:
    """Simmetriya: qarshilik zonasi uchun naqsh teskari tomondan."""
    zona = SRZone(kind=ZoneKind.RESISTANCE, low=109.0, high=111.0, touches=3)
    shamlar = tekis(20, 105.0)
    shamlar.append(sham(20, 112.0, 109.0, 110.0))

    natija = detect_liquidity_sweep(shamlar, zona, SOZLAMA)

    assert natija is not None
    assert natija.swept_price == 112.0


# --------------------------------------------------------------------------- #
#  MSNR — daraja turlari
# --------------------------------------------------------------------------- #


def test_malumotsiz_tasnif_oddiy_daraja_beradi() -> None:
    assert classify_level_type(support(), [], 1.0) is LevelType.PLAIN
    assert classify_level_type(support(), tekis(5), 0.0) is LevelType.PLAIN


def rbs_shakli() -> list[Candle]:
    """Haqiqiy RBS naqshi: zona QARSHILIK bo'lgan, keyin buzilgan.

        1. narx zonaga ko'tarilib, aynan undan PASTGA QAYTADI
           (zona ichida pivot high hosil bo'ladi -> u qarshilik edi)
        2. keyin narx zonadan yuqoriga yopilib o'tadi
        3. va yuqorida qoladi -> endi u support
    """
    shamlar = [sham(i, 96.0, 94.0, 95.0) for i in range(6)]
    shamlar.append(sham(6, 100.0, 98.0, 99.5))  # zona ichidan qaytish
    shamlar += [sham(7 + i, 96.0, 94.0, 95.0) for i in range(6)]
    shamlar += [sham(13 + i, 106.0, 104.0, 105.0) for i in range(10)]
    return shamlar


def test_buzilgan_qarshilik_rbs_deb_belgilanadi() -> None:
    assert classify_level_type(support(), rbs_shakli(), 1.0) is LevelType.RBS


def test_qarshilik_bolmagan_zona_rbs_emas() -> None:
    """Narx shunchaki zonani kesib o'tgan — bu RBS EMAS.

    Regressiya: avval faqat "narx qachondir kesib o'tganmi" tekshirilardi
    va kalibrlash to'plamidagi 27 zonaning HAMMASI RBS deb tasniflanardi.
    Ko'tarilayotgan narx har qanday support zonasini kesib o'tgan
    bo'ladi — ya'ni tasnif hech narsani ajratmasdi.
    """
    shamlar = [sham(i, 98.0, 96.0, 97.0) for i in range(10)]  # zonadan past
    shamlar += [sham(10 + i, 106.0, 104.0, 105.0) for i in range(10)]  # ustida

    assert classify_level_type(support(), shamlar, 1.0) is LevelType.PLAIN


def test_otish_bolmasa_oddiy_daraja() -> None:
    """Narx doim zonadan yuqorida bo'lgan — bu flip emas."""
    shamlar = [sham(i, 106.0, 104.0, 105.0) for i in range(20)]

    assert classify_level_type(support(), shamlar, 1.0) is LevelType.PLAIN


def test_kuchli_order_block_engulfing_bilan_aniqlanadi() -> None:
    """Zona ichida tushuvchi sham, uni qamrab olgan ko'taruvchi, keyin impuls."""
    shamlar = tekis(6, 105.0)
    # Zona ichida tushuvchi sham: ochilish 100.8, yopilish 99.4
    shamlar.append(sham(6, 101.0, 99.2, 99.4, open_=100.8))
    # Qamrab oluvchi ko'tariluvchi: ochilish 99.3 (<= oldingi yopilish),
    # yopilish 101.5 (> oldingi ochilish)
    shamlar.append(sham(7, 101.8, 99.2, 101.5, open_=99.3))
    # Impuls — kamida bir ATR yuqoriga
    shamlar += [sham(8 + i, 110.0, 105.0, 108.0) for i in range(4)]

    assert classify_level_type(support(), shamlar, atr_value=2.0) is LevelType.STRONG_OB


def test_ocl_struktura_darajasi_bilan_ustma_ust_tushadi() -> None:
    """Zona BOS/CHOCH darajasini o'z ichiga olsa — OCL."""
    from core.analysis.market_structure import MarketStructure, StructureBreak
    from core.domain.enums import TrendDirection

    struktura = MarketStructure(
        swings=[],
        direction=TrendDirection.UP,
        last_bos=StructureBreak("bos", 100.0, 5, TrendDirection.UP),
    )
    # Flip ham, order block ham yo'q — faqat struktura darajasi mos keladi
    shamlar = [sham(i, 106.0, 104.0, 105.0) for i in range(20)]

    assert classify_level_type(support(), shamlar, 1.0, struktura) is LevelType.OCL


def test_quasimodo_yolgon_breakoutda_aniqlanadi() -> None:
    """Zona ichida yangi past nuqta, keyin zonadan yuqoriga qaytish."""
    from core.analysis.market_structure import MarketStructure, Swing, SwingLabel
    from core.domain.enums import TrendDirection
    from core.domain.enums import ZoneKind as ZK

    shamlar = tekis(12, 105.0)
    shamlar.append(sham(12, 101.0, 98.0, 99.5))  # yangi past
    shamlar += [sham(13 + i, 106.0, 104.0, 105.0) for i in range(5)]  # qaytdi

    struktura = MarketStructure(
        swings=[Swing(12, 98.0, ZK.SUPPORT, SwingLabel.LL)],
        direction=TrendDirection.FLAT,
    )

    assert classify_level_type(support(), shamlar, 1.0, struktura) is LevelType.QUASIMODO


def test_tasnif_ishonch_darajasi_tartiblangan() -> None:
    """Kuchliroq naqsh — yuqoriroq ishonch. Bonus shunga ko'paytiriladi."""
    assert LevelType.PLAIN.confidence == 0.0
    assert LevelType.RBS.confidence < LevelType.OCL.confidence
    assert LevelType.OCL.confidence < LevelType.QUASIMODO.confidence


def test_haqiqiy_zigzagda_tasnif_xato_bermaydi() -> None:
    """Yaxlit tekshiruv: haqiqiy struktura bilan ham ishlaydi."""
    shamlar = tekis(8, 100.0)
    for i in range(30):
        narx = 100 + i
        shamlar.append(sham(8 + i, narx + 1, narx - 1, narx))

    struktura = analyze_structure(shamlar)
    tur = classify_level_type(support(), shamlar, 2.0, struktura)

    assert isinstance(tur, LevelType)
