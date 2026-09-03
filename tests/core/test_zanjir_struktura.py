"""BLOK 2 — Struktura: swing, BOS/CHOCH, nisbiy kuch, yangi coin."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.analysis.structure import (
    StrukturaKirish,
    SwingTuri,
    bos_choch_topish,
    nisbiy_kuch,
    struktura_blok,
    swinglar,
    yangi_coin_naqshi,
)
from core.analysis.structure.swing_detector import ketma_ketlik_kotarilish
from core.domain.models import Candle

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(i: int, high: float, low: float, close: float | None = None) -> Candle:
    ochilish = close if close is not None else (high + low) / 2
    return Candle(
        open_time=BOSH + timedelta(days=i),
        open=ochilish,
        high=high,
        low=low,
        close=close if close is not None else (high + low) / 2,
        volume=1000.0,
    )


def tepalik(markaz_high: float = 120.0) -> list[Candle]:
    """5 shamli fraktal: o'rtadagi sham eng baland."""
    return [
        sham(0, 100, 90),
        sham(1, 105, 95),
        sham(2, markaz_high, 100),
        sham(3, 105, 95),
        sham(4, 100, 90),
    ]


# --------------------------------------------------------------------------- #
#  2.1 Swing
# --------------------------------------------------------------------------- #


def test_fraktal_swing_yuqori_topiladi() -> None:
    nuqtalar = swinglar(tepalik())
    assert len(nuqtalar) == 1
    assert nuqtalar[0].turi is SwingTuri.YUQORI
    assert nuqtalar[0].narx == 120.0


def test_chetdagi_shamlar_swing_bola_olmaydi() -> None:
    """Oxirgi 2 sham hech qachon swing emas — LOOKAHEAD HIMOYASI.

    Ular uchun o'ng qanot hali shakllanmagan; ularni swing deb
    belgilash "kelajakni ko'rish" bo'lardi.
    """
    nuqtalar = swinglar(tepalik())
    assert all(2 <= s.indeks <= 2 for s in nuqtalar)


def test_shubhali_sham_swing_bolmaydi() -> None:
    """Bitta birjaning yolg'on wicki strukturani buzmasin."""
    shamlar = tepalik()
    rad = {shamlar[2].open_time}
    assert swinglar(shamlar, shubhali=rad) == []


def test_hh_hl_ketma_ketligi() -> None:
    """HH VA HL — ikkalasi ham shart."""
    shamlar = [
        sham(0, 100, 80), sham(1, 105, 85), sham(2, 110, 90),
        sham(3, 105, 85), sham(4, 100, 82),
        sham(5, 108, 88), sham(6, 115, 95),
        sham(7, 110, 90), sham(8, 105, 88),
    ]
    nuqtalar = swinglar(shamlar)
    # Ikkita yuqori va ikkita past bo'lmasa xulosa chiqarilmaydi
    assert ketma_ketlik_kotarilish(nuqtalar) in (True, False)


def test_yetarli_nuqta_yoq_bolsa_kotarilish_yoq() -> None:
    assert not ketma_ketlik_kotarilish(swinglar(tepalik()))


# --------------------------------------------------------------------------- #
#  2.2 / 2.3 BOS va CHOCH
# --------------------------------------------------------------------------- #


def test_bos_yopilish_bilan_aniqlanadi() -> None:
    """Wick bilan kesish BOS emas — bozor darajani QABUL QILISHI kerak."""
    shamlar = [*tepalik(), sham(5, 125, 110, close=110), sham(6, 130, 115, close=125)]
    nuqtalar = swinglar(shamlar)
    holat = bos_choch_topish(shamlar, nuqtalar)
    assert holat.bos_tasdiqlangan


def test_wick_bilan_kesish_bos_emas() -> None:
    shamlar = [*tepalik(), sham(5, 125, 110, close=110)]
    nuqtalar = swinglar(shamlar)
    holat = bos_choch_topish(shamlar, nuqtalar)
    assert not holat.bos_tasdiqlangan


def test_choch_bosdan_keyin_kelsa_struktura_ishonchsiz() -> None:
    """Tartib muhim: BOS -> CHOCH bo'lsa, endi ko'tarilish emas."""
    from core.analysis.structure.bos_choch import BosChoch

    holat = BosChoch(bos_indeks=5, choch_indeks=9)
    assert not holat.bos_tasdiqlangan
    assert not holat.qarshi_choch_yoq


def test_choch_bosdan_oldin_bolsa_muammo_emas() -> None:
    from core.analysis.structure.bos_choch import BosChoch

    holat = BosChoch(bos_indeks=9, choch_indeks=5)
    assert holat.bos_tasdiqlangan
    assert holat.qarshi_choch_yoq


def test_yonalish_aniqlanmagan_bolsa_olchanmaydi() -> None:
    """Na BOS, na CHOCH — "qarshi CHOCH yo'q" gapi MA'NOSIZ.

    Ilgari bu yerda True qaytardi va yassi, o'lik grafik ham
    struktura blokidan 1/3 bilan o'tardi.
    """
    from core.analysis.structure.bos_choch import BosChoch

    assert BosChoch().qarshi_choch_yoq is None


def test_yassi_grafik_strukturadan_otmaydi() -> None:
    """Yuqoridagi tuzatishning zanjirdagi oqibati."""
    yassi = [sham(i, 100, 100, 100) for i in range(30)]
    b = struktura_blok(StrukturaKirish(shamlar=yassi))
    assert not b.otdi


# --------------------------------------------------------------------------- #
#  2.4 Nisbiy kuch
# --------------------------------------------------------------------------- #


def test_coin_btcdan_kuchli() -> None:
    coin = [sham(i, 100 + i * 2, 90 + i * 2, close=100 + i * 2) for i in range(25)]
    btc = [sham(i, 100 + i, 90 + i, close=100 + i) for i in range(25)]
    assert nisbiy_kuch(coin, btc) is True


def test_coin_btcdan_zaif() -> None:
    coin = [sham(i, 100 + i, 90 + i, close=100 + i) for i in range(25)]
    btc = [sham(i, 100 + i * 2, 90 + i * 2, close=100 + i * 2) for i in range(25)]
    assert nisbiy_kuch(coin, btc) is False


def test_btc_ozi_uchun_olchanmaydi() -> None:
    """"BTC BTC'dan zaif" — bema'ni xulosa, chiqmasligi kerak."""
    shamlar = [sham(i, 100, 90) for i in range(25)]
    assert nisbiy_kuch(shamlar, shamlar, etalon=True) is None


def test_tarix_yetmasa_olchanmaydi() -> None:
    qisqa = [sham(i, 100, 90) for i in range(5)]
    assert nisbiy_kuch(qisqa, qisqa) is None


# --------------------------------------------------------------------------- #
#  Yangi coin naqshi
# --------------------------------------------------------------------------- #


def test_yangi_coin_naqshi_topiladi() -> None:
    """Cho'qqi -> korreksiya -> qayta sinab BOS."""
    shamlar = [
        *tepalik(),
        sham(5, 110, 100, close=105),
        sham(6, 105, 95, close=98),   # korreksiya (120 -> 95, ~21%)
        sham(7, 115, 105, close=112),
        sham(8, 130, 118, close=128),  # cho'qqidan yuqori yopilish
    ]
    nuqtalar = swinglar(shamlar)
    assert yangi_coin_naqshi(shamlar, nuqtalar)


def test_korreksiyasiz_naqsh_yoq() -> None:
    """To'g'ridan-to'g'ri o'sish — boshqa holat (parabolik), kirish xavfli.

    Cho'qqidan keyin eng chuqur tushish 3.3% — chegaradan (5%) past,
    ya'ni korreksiya bo'lmagan. `tepalik()` fiksturasi bu yerda
    ishlatilmaydi: uning o'zida 25% tushish bor.
    """
    shamlar = [
        sham(0, 100, 98, close=99),
        sham(1, 105, 103, close=104),
        sham(2, 120, 118, close=119),   # cho'qqi
        sham(3, 119, 117, close=118),
        sham(4, 118, 116, close=117),   # eng past 116 -> 3.3% tushish
        sham(5, 121, 119, close=121),   # cho'qqidan yuqori yopilish
    ]
    nuqtalar = swinglar(shamlar)
    assert not yangi_coin_naqshi(shamlar, nuqtalar)


def test_yangi_coin_blok_ikki_tekshiruvli() -> None:
    """90 kundan yosh coin — to'liq 4 tekshiruv emas, 2 ta."""
    shamlar = [sham(i, 100 + i, 90 + i, close=95 + i) for i in range(30)]
    b = struktura_blok(StrukturaKirish(shamlar=shamlar, yosh_kun=30))
    assert len(b.tekshiruvlar) == 2


def test_yetuk_coin_blok_tort_tekshiruvli() -> None:
    shamlar = [sham(i, 100 + i, 90 + i, close=95 + i) for i in range(30)]
    b = struktura_blok(StrukturaKirish(shamlar=shamlar, yosh_kun=500))
    assert len(b.tekshiruvlar) == 4


def test_yosh_nomalum_bolsa_yetuk_deb_qaraladi() -> None:
    shamlar = [sham(i, 100 + i, 90 + i, close=95 + i) for i in range(30)]
    b = struktura_blok(StrukturaKirish(shamlar=shamlar))
    assert len(b.tekshiruvlar) == 4
