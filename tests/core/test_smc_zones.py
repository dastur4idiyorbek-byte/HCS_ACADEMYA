"""SMC tuzilmaviy zonalari: Order Block, FVG, impuls va confluence.

Bu zonalar ENTRY va STOP ni belgilaydi — ya'ni ular noto'g'ri
topilsa, savdoning ikkala uchi ham noto'g'ri joyda bo'ladi. Shuning
uchun har bir ta'rif alohida sinaladi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.analysis.smc import (
    ZoneSource,
    fibonacci_zone,
    find_bullish_fvgs,
    find_bullish_order_blocks,
    find_confluences,
    find_impulse,
)
from core.analysis.smc.zones import StructureZone
from core.domain.models import Candle

BOSH = datetime(2026, 9, 1, tzinfo=UTC)


def sham(i: int, o: float, h: float, low: float, c: float) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(hours=i),
        open=o,
        high=h,
        low=low,
        close=c,
        volume=1000.0,
    )


def tekis(n: int, narx: float, boshi: int = 0) -> list[Candle]:
    """Deyarli qimirlamaydigan shamlar — fon shovqini."""
    return [
        sham(boshi + i, narx, narx * 1.001, narx * 0.999, narx) for i in range(n)
    ]


# --------------------------------------------------------------------------- #
#  Impuls va Fibonacci
# --------------------------------------------------------------------------- #


def test_impuls_pastdan_choqqigacha_olinadi() -> None:
    shamlar = [
        sham(0, 100, 101, 99, 100),
        sham(1, 100, 101, 90, 95),   # eng past
        sham(2, 95, 120, 94, 118),
        sham(3, 118, 130, 117, 128),  # cho'qqi
        sham(4, 128, 129, 120, 122),
    ]
    impuls = find_impulse(shamlar)

    assert impuls is not None
    assert impuls.low == 90
    assert impuls.high == 130
    assert impuls.start_index == 1
    assert impuls.end_index == 3


def test_choqqidan_KEYINGI_past_nuqta_impulsga_kirmaydi() -> None:
    """Eng past nuqtani avval izlasak, u cho'qqidan keyin chiqishi
    mumkin — bu esa impuls emas, TUSHISH bo'lardi. Fibonacci faqat
    ko'tarilish ustiga qurilsa ma'noga ega (spot: faqat xarid)."""
    shamlar = [
        sham(0, 100, 101, 95, 100),
        sham(1, 100, 130, 99, 128),   # cho'qqi
        sham(2, 128, 129, 60, 65),    # cho'qqidan KEYIN eng past
    ]
    impuls = find_impulse(shamlar)

    assert impuls is not None
    assert impuls.low == 95, "cho'qqidan oldingi tub olinishi kerak"
    assert impuls.high == 130


def test_fibonacci_darajalari_impulsdan_hisoblanadi() -> None:
    shamlar = [
        sham(0, 100, 101, 100, 100),
        sham(1, 100, 200, 99, 198),
        sham(2, 198, 200, 150, 160),
    ]
    impuls = find_impulse(shamlar)
    assert impuls is not None

    # 100 -> 200 impulsda 50% qaytish = 150
    assert impuls.retracement(0.5) == 150.0
    assert impuls.retracement_ratio(150.0) == 0.5


def test_fibonacci_zonasi_oltin_oraliqni_beradi() -> None:
    shamlar = [
        sham(0, 100, 100, 100, 100),
        sham(1, 100, 200, 100, 200),
        sham(2, 200, 200, 160, 165),
    ]
    impuls = find_impulse(shamlar)
    assert impuls is not None

    zona = fibonacci_zone(impuls, [0.382, 0.618])
    assert zona is not None
    # Nisbat KATTA bo'lsa narx PAST: 0.618 -> 138.2, 0.382 -> 161.8
    assert round(zona.low, 1) == 138.2
    assert round(zona.high, 1) == 161.8
    assert zona.source is ZoneSource.FIBONACCI


def test_malumot_yetmasa_impuls_yoq() -> None:
    assert find_impulse([]) is None
    assert find_impulse(tekis(2, 100)) is None


# --------------------------------------------------------------------------- #
#  Order Block
# --------------------------------------------------------------------------- #


def test_order_block_impuls_oldidagi_tushuvchi_sham() -> None:
    shamlar = [
        *tekis(3, 100),
        sham(3, 100, 100.5, 97, 98),   # TUSHUVCHI sham — order block
        sham(4, 98, 106, 97.5, 105),   # kuchli ko'tarilish
        sham(5, 105, 110, 104, 109),
    ]
    bloklar = find_bullish_order_blocks(shamlar, min_move_pct=1.0)

    assert len(bloklar) >= 1
    blok = bloklar[0]
    assert blok.source is ZoneSource.ORDER_BLOCK
    # TANA olinadi, soya emas: soya shovqin, tana — haqiqiy savdo
    assert blok.low == 98
    assert blok.high == 100


def test_kuchsiz_harakatdan_keyingi_sham_blok_emas() -> None:
    """Ansiz HAR BIR tushuvchi sham "order block" bo'lib chiqardi va
    tushuncha ma'nosini yo'qotardi."""
    shamlar = [
        *tekis(3, 100),
        sham(3, 100, 100.5, 99.5, 99.6),
        sham(4, 99.6, 100.0, 99.4, 99.9),  # harakat ~0.5%
        sham(5, 99.9, 100.1, 99.5, 100.0),
    ]
    assert find_bullish_order_blocks(shamlar, min_move_pct=2.0) == []


def test_kotariluvchi_sham_order_block_bolmaydi() -> None:
    shamlar = [
        *tekis(3, 100),
        sham(3, 98, 106, 97, 105),   # ko'taruvchi
        sham(4, 105, 112, 104, 111),
    ]
    bloklar = find_bullish_order_blocks(shamlar, min_move_pct=1.0)
    assert all(z.index != 3 for z in bloklar)


def test_eng_yangi_blok_birinchi_qaytadi() -> None:
    shamlar = [
        *tekis(2, 100),
        sham(2, 100, 100.5, 97, 98),
        sham(3, 98, 106, 97.5, 105),
        *tekis(2, 105, boshi=4),
        sham(6, 105, 105.5, 102, 103),
        sham(7, 103, 112, 102.5, 111),
    ]
    bloklar = find_bullish_order_blocks(shamlar, min_move_pct=1.0, limit=2)
    assert len(bloklar) == 2
    assert bloklar[0].index > bloklar[1].index


# --------------------------------------------------------------------------- #
#  FVG
# --------------------------------------------------------------------------- #


def test_fvg_uch_sham_orasidagi_boshliq() -> None:
    shamlar = [
        sham(0, 100, 102, 99, 101),    # 1-sham: yuqori = 102
        sham(1, 101, 110, 100, 109),   # o'rtadagi kuchli sham
        sham(2, 109, 112, 105, 111),   # 3-sham: quyi = 105
    ]
    gaplar = find_bullish_fvgs(shamlar, min_gap_pct=0.1)

    assert len(gaplar) == 1
    assert gaplar[0].low == 102
    assert gaplar[0].high == 105
    assert gaplar[0].source is ZoneSource.FVG


def test_boshliq_yopiq_bolsa_fvg_yoq() -> None:
    shamlar = [
        sham(0, 100, 106, 99, 105),   # yuqori 106
        sham(1, 105, 110, 104, 109),
        sham(2, 109, 112, 103, 111),  # quyi 103 < 106 — bo'shliq yo'q
    ]
    assert find_bullish_fvgs(shamlar) == []


def test_mayda_boshliq_kesiladi() -> None:
    """Har bir tez harakatda mikroskopik gaplar paydo bo'ladi — ular
    kirish nuqtasi sifatida ma'noga ega emas."""
    shamlar = [
        sham(0, 100, 100.0, 99, 100),
        sham(1, 100, 101, 99.5, 100.5),
        sham(2, 100.5, 101, 100.02, 100.8),  # bo'shliq 0.02%
    ]
    assert find_bullish_fvgs(shamlar, min_gap_pct=0.1) == []


# --------------------------------------------------------------------------- #
#  Confluence
# --------------------------------------------------------------------------- #


def zona(source: ZoneSource, low: float, high: float, index: int = 0) -> StructureZone:
    return StructureZone(source=source, low=low, high=high, index=index)


def test_kesishgan_zonalar_bitta_nomzodga_birlashadi() -> None:
    natija = find_confluences(
        [
            zona(ZoneSource.FIBONACCI, 138, 162),
            zona(ZoneSource.ORDER_BLOCK, 145, 152),
            zona(ZoneSource.FVG, 148, 155),
        ]
    )

    assert len(natija) == 1
    assert natija[0].strength == 3
    # KESISHMA olinadi, birlashma emas: kirish zonasi qancha tor
    # bo'lsa, Stop shuncha yaqin va xavf shuncha kichik.
    assert natija[0].low == 148
    assert natija[0].high == 152


def test_kesishmagan_zonalar_alohida_qoladi() -> None:
    natija = find_confluences(
        [
            zona(ZoneSource.ORDER_BLOCK, 100, 105),
            zona(ZoneSource.FVG, 120, 125),
        ]
    )
    assert len(natija) == 2
    assert all(c.strength == 1 for c in natija)


def test_kuchli_confluence_birinchi_turadi() -> None:
    natija = find_confluences(
        [
            zona(ZoneSource.ORDER_BLOCK, 100, 105),
            zona(ZoneSource.FIBONACCI, 120, 130),
            zona(ZoneSource.FVG, 122, 128),
        ]
    )
    assert natija[0].strength == 2
    assert natija[0].low == 122


def test_bir_xil_manbadan_ikkita_zona_kuchni_oshirmaydi() -> None:
    """Ikkita FVG — bu ikkita dalil emas, bitta usulning ikki natijasi.
    Kuch TURLI manbalar sonidan chiqadi."""
    natija = find_confluences(
        [
            zona(ZoneSource.FVG, 100, 110),
            zona(ZoneSource.FVG, 105, 115),
        ]
    )
    assert natija[0].strength == 1


def test_confluence_izohi_manbalarni_sanaydi() -> None:
    natija = find_confluences(
        [
            zona(ZoneSource.FIBONACCI, 138, 162),
            zona(ZoneSource.ORDER_BLOCK, 145, 152),
        ]
    )
    matn = natija[0].describe()
    assert "Fibonacci" in matn
    assert "Order Block" in matn


def test_bosh_royxat_xato_bermaydi() -> None:
    assert find_confluences([]) == []
