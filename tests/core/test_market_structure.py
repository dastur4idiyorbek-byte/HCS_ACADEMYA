"""SMC — Market Structure: HH/HL/LH/LL, BOS va CHOCH.

Shamlar sun'iy, lekin har bir test aynan bitta xatti-harakatni sinaydi:
zigzag qurilib, undan qanday struktura chiqishi tekshiriladi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.analysis.market_structure import (
    SwingLabel,
    analyze_structure,
    label_swings,
    structure_alignment,
)
from core.analysis.support_resistance.pivots import Pivot
from core.domain.enums import TrendDirection, ZoneKind
from core.domain.models import Candle

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(index: int, high: float, low: float, close: float | None = None) -> Candle:
    yopilish = close if close is not None else (high + low) / 2
    return Candle(
        open_time=BOSH + timedelta(hours=index),
        open=yopilish,
        high=high,
        low=low,
        close=yopilish,
        volume=1000.0,
    )


def zigzag(nuqtalar: list[float], qadam: int = 6) -> list[Candle]:
    """Berilgan burilish narxlari orqali silliq zigzag quradi.

    Har bir burilish orasida `qadam` ta oraliq sham bo'ladi — pivot
    aniqlash uchun chap va o'ngdan tasdiq kerak (`lookback`).
    """
    shamlar: list[Candle] = []
    indeks = 0
    for i in range(len(nuqtalar) - 1):
        boshi, oxiri = nuqtalar[i], nuqtalar[i + 1]
        for j in range(qadam):
            ulush = (j + 1) / qadam
            narx = boshi + (oxiri - boshi) * ulush
            shamlar.append(sham(indeks, narx + 0.05, narx - 0.05, narx))
            indeks += 1
    # Oxirgi burilish o'ngdan tasdiqlanishi uchun tekis quyruq
    oxirgi = nuqtalar[-1]
    for _ in range(qadam):
        shamlar.append(sham(indeks, oxirgi + 0.05, oxirgi - 0.05, oxirgi))
        indeks += 1
    return shamlar


def pivot(index: int, price: float, *, high: bool) -> Pivot:
    return Pivot(
        index,
        price,
        ZoneKind.RESISTANCE if high else ZoneKind.SUPPORT,
        BOSH + timedelta(hours=index),
    )


# --------------------------------------------------------------------------- #
#  Swing belgilash
# --------------------------------------------------------------------------- #


def test_kotarilish_ketma_ketligi_hh_va_hl_beradi() -> None:
    swings = label_swings(
        [
            pivot(0, 100, high=False),
            pivot(1, 110, high=True),
            pivot(2, 104, high=False),
            pivot(3, 118, high=True),
        ]
    )
    belgilar = [s.label for s in swings]
    assert belgilar == [
        SwingLabel.FIRST,
        SwingLabel.FIRST,
        SwingLabel.HL,
        SwingLabel.HH,
    ]


def test_pasayish_ketma_ketligi_lh_va_ll_beradi() -> None:
    swings = label_swings(
        [
            pivot(0, 120, high=True),
            pivot(1, 110, high=False),
            pivot(2, 116, high=True),
            pivot(3, 102, high=False),
        ]
    )
    assert [s.label for s in swings][2:] == [SwingLabel.LH, SwingLabel.LL]


def test_chuqqi_chuqurlik_bilan_solishtirilmaydi() -> None:
    """Cho'qqi faqat cho'qqi bilan, chuqurlik faqat chuqurlik bilan.

    Aralashtirilsa, "cho'qqi avvalgi chuqurlikdan baland" degan
    ma'nosiz taqqoslash chiqadi va har bir cho'qqi HH bo'lib qolardi.
    """
    swings = label_swings(
        [
            pivot(0, 100, high=False),
            pivot(1, 110, high=True),
            pivot(2, 95, high=False),  # avvalgi CHUQURLIKDAN past -> LL
        ]
    )
    assert swings[2].label is SwingLabel.LL


def test_bir_xil_narxdagi_chuqqi_avvalgi_belgini_saqlaydi() -> None:
    """Qo'sh cho'qqi trend buzilishi emas.

    `>` va `<` bilan yozilganda teng narx "past" toifasiga tushardi va
    tekis bozor sun'iy ravishda "pasayish" ko'rinardi.
    """
    swings = label_swings(
        [
            pivot(0, 100, high=True),
            pivot(1, 110, high=True),
            pivot(2, 110, high=True),
        ]
    )
    assert swings[1].label is SwingLabel.HH
    assert swings[2].label is SwingLabel.HH


# --------------------------------------------------------------------------- #
#  Yo'nalish
# --------------------------------------------------------------------------- #


def test_kotarilish_zigzagi_up_beradi() -> None:
    natija = analyze_structure(zigzag([100, 112, 106, 124, 116, 138]))
    assert natija.direction is TrendDirection.UP
    assert natija.is_uptrend


def test_pasayish_zigzagi_down_beradi() -> None:
    natija = analyze_structure(zigzag([140, 126, 134, 112, 120, 98]))
    assert natija.direction is TrendDirection.DOWN


def test_aralash_swinglar_flat_beradi() -> None:
    """Cho'qqi ko'tarilyapti, chuqurlik tushyapti — kengayuvchi diapazon.

    Bu na ko'tarilish, na pasayish. "Uchtadan ikkitasi" kabi yumshoq
    qoida qo'yilsa, bu holat "ko'tarilish" deb o'qilardi.
    """
    natija = analyze_structure(zigzag([100, 120, 92, 130, 84, 140]))
    assert natija.direction is TrendDirection.FLAT


def test_malumot_yoq_bolsa_flat_va_xato_yoq() -> None:
    assert analyze_structure([]).direction is TrendDirection.FLAT


def test_swing_yetmasa_SOF_OZGARISH_ishlatiladi() -> None:
    """Silliq ko'tarilishda burilish nuqtasi bo'lmaydi — lekin trend BOR.

    Bu EMA olib tashlangandan keyin qolgan bo'shliq edi: to'xtovsiz
    o'sish HH/HL ketma-ketligi hosil qilmaydi va struktura "aniq emas"
    derdi — holbuki bu eng kuchli trendning o'zi.
    """
    # 100 -> 110: swing yo'q, lekin sof o'zgarish +10%
    assert analyze_structure(zigzag([100, 110])).direction is TrendDirection.UP
    assert analyze_structure(zigzag([110, 100])).direction is TrendDirection.DOWN


def test_zaxira_olchov_shovqinni_kesadi() -> None:
    """Bir foizdan kichik tebranish trend emas."""
    assert (
        analyze_structure(zigzag([100, 100.3]), fallback_min_pct=1.0).direction
        is TrendDirection.FLAT
    )


# --------------------------------------------------------------------------- #
#  BOS / CHOCH
# --------------------------------------------------------------------------- #


def test_bos_oxirgi_chuqqidan_otganda_qayd_etiladi() -> None:
    shamlar = zigzag([100, 112, 106, 124, 116, 138])
    natija = analyze_structure(shamlar)
    assert natija.last_bos is not None
    assert natija.last_bos.kind == "bos"
    assert natija.last_bos.direction is TrendDirection.UP


def test_choch_oxirgi_chuqurlikdan_tushganda_qayd_etiladi() -> None:
    """Ko'tarilishdan keyin narx oxirgi HL dan pastga yopilsa — CHOCH."""
    shamlar = zigzag([100, 112, 106, 124, 116, 130])
    # Ko'tarilish tugadi va narx oxirgi chuqurlikdan (116) pastga tushdi
    shamlar += [sham(len(shamlar) + i, 114, 108, 110) for i in range(8)]
    natija = analyze_structure(shamlar)
    assert natija.last_choch is not None
    assert natija.last_choch.direction is TrendDirection.DOWN


def test_buzilish_soya_bilan_emas_yopilish_bilan_tasdiqlanadi() -> None:
    """Soya ko'pincha likvidlik ovi — uni BOS deb hisoblash yolg'on signal.

    Bu yerda narx cho'qqidan YUQORIGA soya tashlaydi, lekin pastda
    yopiladi. BOS qayd etilmasligi kerak.
    """
    shamlar = zigzag([100, 112, 106, 124], qadam=6)
    cho_qqi = max(s.high for s in shamlar)
    # Soyasi cho'qqidan baland, yopilishi past
    shamlar += [sham(len(shamlar) + i, cho_qqi + 5, 118, 119) for i in range(8)]

    natija = analyze_structure(shamlar)
    if natija.last_bos is not None:
        # BOS bo'lsa, u soyali shamdan OLDIN sodir bo'lgan bo'lishi kerak
        assert natija.last_bos.index < len(shamlar) - 8


# --------------------------------------------------------------------------- #
#  Ballga uzatiladigan o'lchov
# --------------------------------------------------------------------------- #


def test_alignment_pasayishda_nol_beradi() -> None:
    natija = analyze_structure(zigzag([140, 126, 134, 112, 120, 98]))
    assert structure_alignment(natija) == 0.0


def test_alignment_kotarilishda_yuqori_beradi() -> None:
    natija = analyze_structure(zigzag([100, 112, 106, 124, 116, 138]))
    assert structure_alignment(natija) >= 0.7


def test_alignment_aniqlanmaganda_ortacha_beradi() -> None:
    """Aniqlab bo'lmagan struktura JAZO emas — o'rtacha bonus oladi."""
    assert structure_alignment(analyze_structure([])) == 0.4


def test_describe_matn_beradi() -> None:
    natija = analyze_structure(zigzag([100, 112, 106, 124, 116, 138]))
    matn = natija.describe()
    assert "Ko'tarilish" in matn
    assert matn == natija.describe()
