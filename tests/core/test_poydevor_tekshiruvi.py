"""POYDEVOR TEKSHIRUVI — kod "zona" degan joy rostdan zonami?

NIMA UCHUN BU FAYL BOR.

Loyihada oltita gipoteza sinaldi va hammasi ball qatlamiga
tegishli edi: qaysi omilga necha ball berish, qaysi filtrni
yoqish. Hech biri natijani o'zgartirmadi.

Lekin bitta narsa hech qachon tekshirilmagan: BALL NIMANING
USTIGA quriladi. Agar `find_bullish_order_blocks` "order block"
deb qaytargan joy aslida order block bo'lmasa, uning ustidagi
har qanday ball — bo'sh raqam. Poydevor tekshirilmagan holda
ustidagi qavatlarni qayta-qayta bo'yash bilan barobar.

USUL. Shamlar QO'LDA quriladi, ya'ni to'g'ri javob oldindan
ma'lum. Bozor ma'lumoti ishlatilmaydi — u yerda "to'g'ri javob"
degan narsa yo'q, faqat taxmin bor.

Bu testlar aniqlovchilarni maqtash uchun emas. Ular ikki xil
javob berishi mumkin va IKKALASI HAM foydali:
  - naqsh topildi     -> ta'rif bajarilyapti
  - naqsh topilmadi   -> ball qurilgan poydevor bo'sh
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.analysis.market_structure import analyze_structure
from core.analysis.smc.zones import (
    ZoneSource,
    find_bullish_fvgs,
    find_bullish_order_blocks,
    find_impulse,
)
from core.analysis.support_resistance import SupportResistanceDetector
from core.config.schema import SupportResistanceConfig
from core.domain.enums import TrendDirection
from core.domain.models import Candle

BOSH = datetime(2025, 1, 1, tzinfo=UTC)


def sham(
    index: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 100.0,
) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(hours=4 * index),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        closed=True,
    )


def tekis(index: int, narx: float, kenglik: float = 0.5) -> Candle:
    """Ma'nosiz "to'ldiruvchi" sham — naqsh yaratmasligi kerak."""
    return sham(index, narx, narx + kenglik, narx - kenglik, narx)


# --------------------------------------------------------------------------- #
#  1. Support / Resistance zonasi
# --------------------------------------------------------------------------- #


def _zigzag(tublar: list[float], choqqilar: list[float]) -> list[Candle]:
    """Tub va cho'qqilar navbatlashgan TOZA qator.

    Har burilish nuqtasi orasiga oraliq shamlar qo'yiladi, ya'ni
    burilish aniq lokal ekstremum bo'ladi. Shamlar kichik: naqsh
    faqat burilishdan kelib chiqsin, sham kattaligidan emas.
    """
    burilishlar: list[float] = []
    for tub, choqqi in zip(tublar, choqqilar, strict=True):
        burilishlar.append(tub)
        burilishlar.append(choqqi)

    narxlar: list[float] = [burilishlar[0]]
    for oldingi, keyingi in zip(burilishlar, burilishlar[1:], strict=False):
        qadam = (keyingi - oldingi) / 3
        narxlar.extend([oldingi + qadam, oldingi + 2 * qadam, keyingi])

    return [
        sham(i, narx, narx + 0.3, narx - 0.3, narx)
        for i, narx in enumerate(narxlar)
    ]


def test_uch_marta_qaytgan_narx_SUPPORT_deb_belgilanadi() -> None:
    """Eng oddiy ta'rif: narx bir joydan bir necha marta qaytdi.

    Aynan 100 dan uch marta qaytadi. Kod shu yerda support
    ko'rmasa, S/R qatlamining o'zi ishlamayapti degani.
    """
    shamlar: list[Candle] = []
    i = 0
    for _ in range(3):
        shamlar.append(tekis(i, 110))
        i += 1
        shamlar.append(sham(i, 108, 109, 100.0, 102))
        i += 1   # tub — 100
        shamlar.append(tekis(i, 106))
        i += 1
        shamlar.append(sham(i, 108, 115.0, 107, 112))
        i += 1    # cho'qqi — 115
        shamlar.append(tekis(i, 111))
        i += 1
    shamlar.append(sham(i, 105, 106, 101, 103))                  # narx tubga yaqin

    detector = SupportResistanceDetector(
        SupportResistanceConfig(swing_lookback=1, min_touches=2), atr_period=5
    )
    xarita = detector.detect(shamlar)

    assert xarita is not None, "zona xaritasi umuman qurilmadi"
    supportlar = xarita.supports
    assert supportlar, "uch marta qaytgan narx support deb belgilanmadi"
    assert any(z.low <= 100.5 and z.high >= 99.5 for z in supportlar), (
        f"support 100 atrofida kutilgan edi, topilgani: "
        f"{[(z.low, z.high) for z in supportlar]}"
    )


def test_zona_takroriy_TEGISHNI_sanaydi() -> None:
    """`touches` — naqshning kuchi. U rost bo'lishi kerak."""
    shamlar: list[Candle] = []
    i = 0
    for _ in range(4):
        shamlar.append(sham(i, 108, 109, 100.0, 102))
        i += 1
        shamlar.append(sham(i, 108, 115.0, 107, 112))
        i += 1
    shamlar.append(sham(i, 105, 106, 101, 103))

    detector = SupportResistanceDetector(
        SupportResistanceConfig(swing_lookback=1, min_touches=2), atr_period=5
    )
    xarita = detector.detect(shamlar)

    assert xarita is not None
    supportlar = [z for z in xarita.supports if z.low <= 101 and z.high >= 99]
    assert supportlar, "takroriy tub topilmadi"
    assert supportlar[0].touches >= 2, (
        f"to'rt marta qaytdi, sanalgani: {supportlar[0].touches}"
    )


# --------------------------------------------------------------------------- #
#  2. Bozor strukturasi — HH/HL va LH/LL
# --------------------------------------------------------------------------- #


def test_kotarilish_qadamlari_UP_deb_oqiladi() -> None:
    """Har bir tub va cho'qqi oldingisidan YUQORI — bu ko'tarilish."""
    tublar = [100.0, 106.0, 112.0, 118.0, 124.0]
    choqqilar = [105.0, 111.0, 117.0, 123.0, 129.0]

    struktura = analyze_structure(_zigzag(tublar, choqqilar), lookback=1)

    assert struktura.direction is TrendDirection.UP, struktura.describe()


def test_pasayish_qadamlari_DOWN_deb_oqiladi() -> None:
    tublar = [124.0, 118.0, 112.0, 106.0, 100.0]
    choqqilar = [129.0, 123.0, 117.0, 111.0, 105.0]

    struktura = analyze_structure(_zigzag(tublar, choqqilar), lookback=1)

    assert struktura.direction is TrendDirection.DOWN, struktura.describe()


def test_aralash_qadamlar_UP_deb_oqilmasin() -> None:
    """Diapazon — bu ko'tarilish EMAS.

    Eng xavfli xato shu bo'lardi: yon harakatni "ko'tarilish" deb
    o'qish. Unda tizim diapazonning tepasidan xarid qilardi.
    """
    tublar = [100.0, 101.0, 99.0, 100.5, 99.5]
    choqqilar = [110.0, 109.0, 110.5, 109.5, 110.0]

    struktura = analyze_structure(_zigzag(tublar, choqqilar), lookback=1)

    assert struktura.direction is not TrendDirection.UP, (
        f"yon harakat ko'tarilish deb o'qildi: {struktura.describe()}"
    )


# --------------------------------------------------------------------------- #
#  3. Fair Value Gap
# --------------------------------------------------------------------------- #


def test_uch_sham_orasidagi_HAQIQIY_boshliq_topiladi() -> None:
    """Ta'rif: 1-shamning yuqorisi 3-shamning quyisidan PAST.

    Qo'lda quramiz: 1-sham 100-101, 3-sham 104-106. Orada
    101..104 — narx umuman savdo qilmagan oraliq.
    """
    shamlar = [
        tekis(0, 100),
        sham(1, 100.2, 101.0, 100.0, 100.8),   # 1-sham: yuqorisi 101
        sham(2, 101.0, 105.0, 101.0, 104.5),   # 2-sham: sakrash
        sham(3, 104.5, 106.0, 104.0, 105.5),   # 3-sham: quyisi 104
        tekis(4, 105),
    ]

    natija = find_bullish_fvgs(shamlar, lookback=10, min_gap_pct=0.1)

    assert natija, "aniq bo'shliq topilmadi"
    fvg = natija[0]
    assert fvg.source is ZoneSource.FVG
    assert fvg.low == 101.0 and fvg.high == 104.0, (
        f"bo'shliq 101..104 kutilgan edi, topilgani {fvg.low}..{fvg.high}"
    )


def test_boshliqsiz_qatorda_FVG_topilmaydi() -> None:
    """Uzluksiz qatorda FVG bo'lmasligi kerak — aks holda har
    joyda "bo'shliq" ko'rinardi va tushuncha ma'nosini yo'qotardi."""
    shamlar = [sham(i, 100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(10)]

    assert find_bullish_fvgs(shamlar, lookback=10, min_gap_pct=0.1) == []


# --------------------------------------------------------------------------- #
#  4. Order Block
# --------------------------------------------------------------------------- #


def test_impulsdan_oldingi_tushuvchi_sham_ORDER_BLOCK() -> None:
    """Ta'rif: kuchli ko'tarilishdan oldingi oxirgi tushuvchi sham.

    Qo'lda quramiz: 100 dan 98 ga tushgan sham, keyin 108 gacha
    ko'tarilish. Blok TANASI 98..100.
    """
    shamlar = [
        tekis(0, 101),
        sham(1, 100.0, 100.2, 97.5, 98.0),     # tushuvchi sham — TANA 98..100
        sham(2, 98.0, 104.0, 98.0, 103.5),     # impuls boshlandi
        sham(3, 103.5, 108.0, 103.0, 107.5),
        tekis(4, 107),
    ]

    natija = find_bullish_order_blocks(shamlar, lookback=10, min_move_pct=1.0)

    assert natija, "impulsdan oldingi tushuvchi sham topilmadi"
    ob = natija[0]
    assert ob.source is ZoneSource.ORDER_BLOCK
    assert ob.low == 98.0 and ob.high == 100.0, (
        f"blok tanasi 98..100 kutilgan edi, topilgani {ob.low}..{ob.high}"
    )


def test_ORDER_BLOCK_tarifi_TUZILMANI_talab_qilmaydi() -> None:
    """TOPILGAN KAMCHILIK — bu test ayblov emas, hujjat.

    Klassik ta'rifda order block impulsi tuzilmani BUZISHI kerak
    (oldingi cho'qqi olinadi, ya'ni BOS). Bizning aniqlovchi buni
    talab qilmaydi: har qanday tushuvchi shamdan keyin kichik
    ko'tarilish bo'lsa, u "order block" deb belgilanadi.

    Bu yerda TUSHUVCHI trend ichida, hech qanday cho'qqi
    olinmagan holatda ham blok topilishini ko'rsatamiz.

    Oqibati: "order block yaqinida" degan ball ko'pincha oddiy
    qizil shamga beriladi. Ball noto'g'ri emas — u shunchaki
    o'zi o'ylagan narsani o'lchamaydi.
    """
    shamlar = [
        sham(0, 120, 121, 118, 118.5),
        sham(1, 118.5, 119, 115, 115.5),       # tushuvchi
        sham(2, 115.5, 117.5, 115.0, 117.0),   # kichik qaytish (~2%)
        sham(3, 117.0, 117.2, 112.0, 112.5),   # tushish davom etadi
        sham(4, 112.5, 113, 108, 108.5),
    ]

    natija = find_bullish_order_blocks(shamlar, lookback=10, min_move_pct=1.0)

    assert natija, (
        "tushish trendida ham blok topilishi KUTILGAN edi — agar bu "
        "test yiqilsa, ta'rif qattiqlashgan, hujjatni yangilang"
    )


# --------------------------------------------------------------------------- #
#  5. Impuls
# --------------------------------------------------------------------------- #


def test_impuls_tubdan_choqqigacha_olinadi() -> None:
    """Fibonacci shu impuls ustiga quriladi — u to'g'ri bo'lmasa,
    barcha Fib darajalari noto'g'ri joyda bo'ladi."""
    shamlar = [
        tekis(0, 110),
        sham(1, 108, 109, 100.0, 101),         # TUB — 100
        sham(2, 101, 112, 101, 111),
        sham(3, 111, 130.0, 110, 129),         # CHO'QQI — 130
        tekis(4, 125),
    ]

    impuls = find_impulse(shamlar, lookback=10)

    assert impuls is not None, "aniq impuls topilmadi"
    assert impuls.low == 100.0 and impuls.high == 130.0, (
        f"impuls 100..130 kutilgan edi, topilgani {impuls.low}..{impuls.high}"
    )


def test_choqqidan_KEYINGI_tub_impuls_deb_olinmaydi() -> None:
    """Ko'tarilish impulsi tubdan cho'qqiga qarab boradi.

    Agar kod eng past nuqtani cho'qqidan KEYIN olsa, u aslida
    tushishni "impuls" deb o'qigan bo'lardi va Fibonacci teskari
    tomonga qurilardi.
    """
    shamlar = [
        sham(0, 118, 119, 117, 118),
        sham(1, 118, 130.0, 117, 129),         # CHO'QQI oldinda
        sham(2, 129, 129, 120, 121),
        sham(3, 121, 122, 100.0, 101),         # TUB — cho'qqidan KEYIN
    ]

    impuls = find_impulse(shamlar, lookback=10)

    if impuls is not None:
        assert impuls.start_index < impuls.end_index, (
            "tub cho'qqidan keyin olindi — bu ko'tarilish impulsi emas"
        )
        assert impuls.low != 100.0, "keyingi tub impuls boshi deb olindi"
