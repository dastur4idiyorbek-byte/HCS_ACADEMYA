"""Rejim B — kuzatuv: zanjir UZILMAYDI, to'rt blok ham hisoblanadi.

ENG MUHIM TEST: `test_blok_yoq_desa_ham_qolganlari_hisoblanadi`.
Rejim A dan farqni aynan u qulflaydi. Agar kelajakda kimdir bu
faylga zanjir mantig'ini olib kirsa, o'sha test yiqiladi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.analysis.fundamental.fundamental_block import (
    DelistingXavfi,
    FundamentalKirish,
    TokenUnlock,
)
from core.analysis.observation_mode import (
    KuzatuvKirish,
    Timeframelar,
    kuzatuv_yur,
)
from core.analysis.structure.uptrend_filter import Yonalish
from core.analysis.turlar import Holat
from core.domain.models import Candle

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(i: int, high: float, low: float, close: float | None = None) -> Candle:
    ochilish = close if close is not None else (high + low) / 2
    return Candle(
        open_time=BOSH + timedelta(hours=4 * i),
        open=ochilish,
        high=high,
        low=low,
        close=close if close is not None else (high + low) / 2,
        volume=1000.0,
    )


def _cho_qqi(i: int, high: float) -> list[Candle]:
    past = high - 20
    return [
        sham(i, high - 15, past),
        sham(i + 1, high - 10, past + 2),
        sham(i + 2, high, past + 5),
        sham(i + 3, high - 10, past + 2),
        sham(i + 4, high - 15, past),
    ]


def _tub(i: int, low: float) -> list[Candle]:
    yuqori = low + 20
    return [
        sham(i, yuqori, low + 15),
        sham(i + 1, yuqori - 2, low + 10),
        sham(i + 2, yuqori - 5, low),
        sham(i + 3, yuqori - 2, low + 10),
        sham(i + 4, yuqori, low + 15),
    ]


def kotarilish() -> list[Candle]:
    """HH/HL — filtrdan o'tadigan shakl."""
    return _tub(0, 100) + _cho_qqi(5, 150) + _tub(10, 120) + _cho_qqi(15, 180)


def tushish() -> list[Candle]:
    """LH/LL — filtrdan o'tmaydigan shakl."""
    return _cho_qqi(0, 200) + _tub(5, 150) + _cho_qqi(10, 180) + _tub(15, 130)


def kirish(**kw) -> KuzatuvKirish:  # noqa: ANN003
    asos = {
        "symbol": "TEST",
        "struktura_shamlar": kotarilish(),
        "zona_shamlar": kotarilish(),
        "pastki_shamlar": kotarilish(),
        "btc_shamlar": kotarilish(),
    }
    asos.update(kw)
    return KuzatuvKirish(**asos)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
#  Rejim B ning O'ZAGI: zanjir uzilmaydi
# --------------------------------------------------------------------------- #


def test_blok_yoq_desa_ham_qolganlari_hisoblanadi() -> None:
    """To'rtala blok ham natijada bo'ladi — biri "yo'q" desa ham.

    Rejim A da fundamental blok qattiq to'siq bersa, struktura,
    zona va tasdiqlash UMUMAN hisoblanmasdi. Bu yerda to'rttasi
    ham bor.
    """
    natija = kuzatuv_yur(
        kirish(
            fundamental=FundamentalKirish(
                delisting=DelistingXavfi(anik=True, sabab="birjadan chiqarilmoqda")
            )
        )
    )
    assert len(natija.bloklar) == 4
    nomlar = [b.nom for b in natija.bloklar]
    assert nomlar == ["Fundamental", "Struktura", "Zona Sifati", "Tasdiqlash"]


def test_qattiq_tosiq_toxtatmaydi_faqat_ogohlantiradi() -> None:
    natija = kuzatuv_yur(
        kirish(
            fundamental=FundamentalKirish(
                delisting=DelistingXavfi(anik=True, sabab="birjadan chiqarilmoqda")
            )
        )
    )
    assert natija.ogohlantirish is not None
    assert "Delisting" in natija.ogohlantirish
    # Coin ro'yxatda QOLADI — bu Rejim A dan asosiy farq.
    assert natija.otdi
    assert len(natija.bloklar) == 4


def test_unlock_xavfi_ham_ogohlantirish() -> None:
    natija = kuzatuv_yur(
        kirish(
            fundamental=FundamentalKirish(
                unlock=TokenUnlock(kun_qoldi=3, pct=12.0, izoh="katta unlock")
            )
        )
    )
    assert natija.ogohlantirish is not None
    assert natija.otdi


# --------------------------------------------------------------------------- #
#  3-qism filtri: Downtrend uchun hisob BOSHLANMAYDI
# --------------------------------------------------------------------------- #


def test_downtrend_uchun_bloklar_hisoblanmaydi() -> None:
    """Resurs tejash: nomzod bo'lmagan coin uchun hisob yurmaydi."""
    natija = kuzatuv_yur(kirish(struktura_shamlar=tushish()))
    assert natija.yonalish.yonalish is Yonalish.DOWNTREND
    assert not natija.otdi
    assert natija.bloklar == ()
    assert natija.segmentlar == ()
    assert natija.diqqat == 0


def test_uptrend_uchun_hisob_yuradi() -> None:
    natija = kuzatuv_yur(kirish())
    assert natija.yonalish.yonalish is Yonalish.UPTREND
    assert natija.otdi
    assert len(natija.bloklar) == 4


# --------------------------------------------------------------------------- #
#  Diqqat darajasi — to'rt ichki tekshiruvdan
# --------------------------------------------------------------------------- #


def test_tort_segment_boladi() -> None:
    natija = kuzatuv_yur(kirish())
    assert len(natija.segmentlar) == 4
    assert [s.nom for s in natija.segmentlar] == [
        "zona_konfluensiya",
        "volume_profile",
        "liquidity_sweep",
        "rsi_divergensiya",
    ]


def test_diqqat_faqat_ha_larni_sanaydi() -> None:
    """MALUMOT_YOQ — ✅ HAM emas, ❌ HAM emas: sanoqqa kirmaydi."""
    natija = kuzatuv_yur(kirish())
    qolda = sum(1 for s in natija.segmentlar if s.holat is Holat.HA)
    assert natija.diqqat == qolda
    assert 0 <= natija.diqqat <= 4


def test_diqqat_darajasi_chegaradan_chiqmaydi() -> None:
    for shamlar in (kotarilish(), tushish()):
        natija = kuzatuv_yur(kirish(struktura_shamlar=shamlar))
        assert 0 <= natija.diqqat <= len(natija.segmentlar)


# --------------------------------------------------------------------------- #
#  Timeframe ekranga o'tadi
# --------------------------------------------------------------------------- #


def test_segment_oz_timeframeini_olib_yuradi() -> None:
    tf = Timeframelar(struktura="4h", zona="1h", pastki="15m")
    natija = kuzatuv_yur(kirish(timeframelar=tf))
    assert all(s.timeframe == "1h" for s in natija.segmentlar)
    assert natija.timeframelar.struktura == "4h"


def test_timeframe_qolda_yozilmagan() -> None:
    """Config o'zgarsa, ekrandagi yozuv ham o'zgaradi."""
    tf = Timeframelar(struktura="6h", zona="2h", pastki="30m")
    natija = kuzatuv_yur(kirish(timeframelar=tf))
    assert natija.timeframelar.zona == "2h"
    assert all(s.timeframe == "2h" for s in natija.segmentlar)


# --------------------------------------------------------------------------- #
#  Nisbiy kuch — faqat tartiblash uchun
# --------------------------------------------------------------------------- #


def uzun_kotarilish() -> list[Candle]:
    """30 shamli HH/HL — nisbiy kuch oynasi (20) uchun yetarli.

    `kotarilish()` atigi 20 ta sham va oyna unga TENG: nisbiy kuch
    hisoblanmaydi. Shuning uchun uzunroq shakl kerak.
    """
    return (
        _tub(0, 100)
        + _cho_qqi(5, 150)
        + _tub(10, 120)
        + _cho_qqi(15, 180)
        + _tub(20, 150)
        + _cho_qqi(25, 220)
    )


def test_nisbiy_kuch_btc_dan_tez_osgan_coinda_birdan_katta() -> None:
    coin = uzun_kotarilish()
    tekis = [sham(i, 100, 100, close=100.0) for i in range(len(coin))]
    natija = kuzatuv_yur(kirish(struktura_shamlar=coin, btc_shamlar=tekis))
    assert natija.otdi, "shakl filtrdan o'tishi kerak"
    assert natija.nisbiy_kuch is not None
    assert natija.nisbiy_kuch > 1.0


def test_btc_dan_sekin_osgan_coinda_birdan_kichik() -> None:
    coin = uzun_kotarilish()
    # BTC coin bilan bir xil shaklda, lekin ikki barobar tez o'sadi.
    tez_btc = [
        sham(i, s.high * 2, s.low * 2, close=s.close * (1 + i / len(coin)))
        for i, s in enumerate(coin)
    ]
    natija = kuzatuv_yur(kirish(struktura_shamlar=coin, btc_shamlar=tez_btc))
    assert natija.nisbiy_kuch is not None
    assert natija.nisbiy_kuch < 1.0


def test_tarix_yetmasa_nisbiy_kuch_none() -> None:
    natija = kuzatuv_yur(kirish())
    # 20 shamlik oyna uchun 20 ta sham yetmaydi (kotarilish 20 ta).
    assert natija.nisbiy_kuch is None


# --------------------------------------------------------------------------- #
#  CHEGARA: Entry/Stop/TP yo'q
# --------------------------------------------------------------------------- #


def test_natijada_entry_stop_tp_maydoni_yoq() -> None:
    """Natija tipida savdo darajasi bo'lishi MUMKIN EMAS."""
    natija = kuzatuv_yur(kirish())
    maydonlar = set(natija.__slots__)
    taqiqlangan = {"entry", "stop", "tp", "tp1", "tp2", "darajalar", "levels"}
    assert not (maydonlar & taqiqlangan)
