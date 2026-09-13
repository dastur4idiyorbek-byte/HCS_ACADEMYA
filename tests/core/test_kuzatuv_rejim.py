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


def _qaytish(i: int, close: float) -> list[Candle]:
    """Cho'qqidan keyingi qaytish shamlari.

    Oxirgi IKKI sham hech qachon fraktal bo'lmaydi (`swinglar`
    oynasi chekkalarni qoldiradi), shuning uchun bular yangi swing
    yasamaydi — faqat narxni pastga suradi.
    """
    return [
        sham(i, close + 6, close + 1, close=close + 4),
        sham(i + 1, close + 4, close - 2, close=close),
    ]


def kotarilish() -> list[Candle]:
    """HH/HL VA narx qaytish zonasida — nomzod shakl.

    Impuls 120 -> 180 (uzunlik 60). Fib zonasi 142.9..157.1.
    Oxirgi yopilish 150 — zona ICHIDA, ya'ni coin hali yurmagan.
    """
    return (
        _tub(0, 100)
        + _cho_qqi(5, 150)
        + _tub(10, 120)
        + _cho_qqi(15, 180)
        + _qaytish(20, 150.0)
    )


def kotarilish_yurgan() -> list[Candle]:
    """HH/HL, LEKIN narx cho'qqiga yaqin — ALLAQACHON YURGAN.

    Aynan shu shakl birinchi yozuvda Top 20 ga chiqardi.
    """
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
        # Cho'qqidan qaytish — aks holda coin "yurgan" deb
        # chetlanadi va nisbiy kuch umuman hisoblanmaydi.
        + _qaytish(30, 190.0)
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
    """Oyna (20 sham) to'lmasa — hisoblanmaydi, nol EMAS."""
    qisqa = kotarilish()[:15]
    natija = kuzatuv_yur(kirish(struktura_shamlar=qisqa, btc_shamlar=qisqa))
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


# --------------------------------------------------------------------------- #
#  ALTERNATIV YO'LLAR — prompt 1-qismi: "TO'LIQ SAQLANADI"
# --------------------------------------------------------------------------- #


def test_alternativ_generatorlar_chaqiriladi() -> None:
    """Uch blok uchun ham alternativ ro'yxati SO'RALADI.

    Bu test chaqiruvni KUZATADI, natijani emas. Sabab: alternativ
    g'alaba qozonishi ma'lumotga bog'liq, lekin ular SINALISHI —
    har doim shart. Birinchi yozuvda alternativlar umuman
    chaqirilmagan edi va bu test o'shani ushlagan bo'lardi.
    """
    from core.analysis import observation_mode as om

    chaqirilgan: list[str] = []

    def kuzat(nom: str, asl):  # noqa: ANN001, ANN202
        def orab(*a, **kw):  # noqa: ANN002, ANN003, ANN202
            chaqirilgan.append(nom)
            return asl(*a, **kw)

        return orab

    asl2, asl3, asl4 = om.alternativlar_2, om.alternativlar_3, om.alternativlar_4
    om.alternativlar_2 = kuzat("blok2", asl2)  # type: ignore[assignment]
    om.alternativlar_3 = kuzat("blok3", asl3)  # type: ignore[assignment]
    om.alternativlar_4 = kuzat("blok4", asl4)  # type: ignore[assignment]
    try:
        kuzatuv_yur(kirish())
    finally:
        om.alternativlar_2, om.alternativlar_3, om.alternativlar_4 = asl2, asl3, asl4

    assert chaqirilgan == ["blok2", "blok3", "blok4"], (
        "alternativ yo'llar sinalmadi — prompt 1-qismi buzilgan"
    )


def test_golib_alternativ_blokka_tekshiruv_bolib_qoshiladi() -> None:
    """5.3-qism: "qaysi usul ishlagani ko'rsatiladi".

    G'olib alternativ blokka `alternativ:<nom>` degan ijobiy
    tekshiruv bo'lib tushadi va shu yo'l bilan ekranga chiqadi.
    """
    natija = kuzatuv_yur(kirish())
    if not natija.alternativlar:
        # Bu ma'lumotda hech bir blok ZAIF chiqmagan — normal holat.
        return

    blok_nomi, usul = natija.alternativlar[0]
    blok = next(b for b in natija.bloklar if b.nom == blok_nomi)
    nomlar = [t.nom for t in blok.tekshiruvlar]
    assert f"alternativ:{usul}" in nomlar


def test_qutqarilganlar_royxati_natijada_boladi() -> None:
    """Qaysi blok qaysi usul bilan qutqarilgani yozib boriladi."""
    natija = kuzatuv_yur(kirish())
    for blok_nomi, usul in natija.alternativlar:
        assert blok_nomi in {b.nom for b in natija.bloklar}
        assert usul, "usul nomi bo'sh"


def test_zaif_blok_alternativ_bilan_qutqariladi() -> None:
    """ZAIF blok (1/N) alternativ g'alaba qozonsa 2/N ga chiqadi."""
    from core.analysis.alternatives.alternative_chain import qutqar
    from core.analysis.alternatives.natija import AlternativNatija
    from core.analysis.turlar import blok as blok_yasa
    from core.analysis.turlar import ha, yoq

    zaif = blok_yasa("Struktura", [ha("a", ""), yoq("b", ""), yoq("c", "")])
    assert zaif.kuch == 1

    qutqarilgan, golib = qutqar(
        zaif, [AlternativNatija("trend_flag", True, "ishladi")]
    )
    assert golib is not None
    assert golib.nom == "trend_flag"
    assert qutqarilgan.kuch == 2
    assert qutqarilgan.otdi


def test_hamma_alternativ_sinsa_blok_otmaydi() -> None:
    """Rejim B da bu ZANJIRNI UZMAYDI — blok shunchaki o'tmagan."""
    from core.analysis.alternatives.alternative_chain import qutqar
    from core.analysis.alternatives.natija import AlternativNatija
    from core.analysis.turlar import blok as blok_yasa
    from core.analysis.turlar import ha, yoq

    zaif = blok_yasa("Struktura", [ha("a", ""), yoq("b", ""), yoq("c", "")])
    qutqarilgan, golib = qutqar(
        zaif, [AlternativNatija("trend_flag", False, "ishlamadi")]
    )
    assert golib is None
    assert not qutqarilgan.otdi


# --------------------------------------------------------------------------- #
#  QAYTARILGAN QOIDA: "cho'qqiga yaqin" coin ham ro'yxatda qoladi
# --------------------------------------------------------------------------- #
#
# 12-sentyabrda bu yerga ikkinchi darvoza qo'yilgan edi: narx
# Fibonacci qaytish zonasining tepasida bo'lsa, coin "allaqachon
# yurgan" deb Top ro'yxatdan chiqarilardi.
#
# 13-sentyabrda loyiha egasi natijani o'lchadi: darvoza
# qo'yilishidan OLDINGI ro'yxatdagi 20 coindan 17 tasi haqiqatan
# yuqoriga yurgan. Ya'ni filtr to'g'ri ishlagan, darvoza esa aynan
# ishlaydigan nomzodlarni chiqarib tashlagan.
#
# Shuning uchun darvoza olib tashlandi va quyidagi test uni QAYTA
# QO'SHIB BO'LMASLIGI uchun yozildi.


def test_choqqiga_yaqin_coin_HAM_royxatga_kiradi() -> None:
    """Narxning o'rni ro'yxatdan CHIQARMAYDI — faqat yo'nalish hal qiladi.

    Agar kimdir bosqich darvozasini qaytarsa, shu test yiqiladi.

    NEGA BU MUHIM: HH/HL ketma-ketligi coin harakatni boshlaganda
    ham to'g'ri bo'ladi. "Cho'qqiga yaqin" degani "tugadi" degani
    EMAS — kuchli trendda narx cho'qqi yonida uzoq turadi va
    yuqoriga davom etadi. O'lchov buni tasdiqladi: 20 dan 17 tasi.
    """
    natija = kuzatuv_yur(kirish(struktura_shamlar=kotarilish_yurgan()))
    assert natija.yonalish.yonalish is Yonalish.UPTREND
    assert natija.otdi, "cho'qqiga yaqinlik ro'yxatdan chiqarmasin"
    assert len(natija.bloklar) == 4, "to'rt blok ham hisoblansin"


def test_qaytish_zonasidagi_coin_ham_kiradi() -> None:
    natija = kuzatuv_yur(kirish())
    assert natija.otdi
    assert len(natija.bloklar) == 4


def test_natijada_bosqich_tushunchasi_YOQ() -> None:
    """Darvoza qoldiqsiz olib tashlangan bo'lsin."""
    natija = kuzatuv_yur(kirish())
    assert not hasattr(natija, "bosqich"), "bosqich maydoni qaytib kelgan"
    assert not hasattr(natija, "xaridga_tayyor"), "ikkinchi darvoza qaytib kelgan"


def test_narx_natijada_boladi() -> None:
    natija = kuzatuv_yur(kirish())
    assert natija.narx is not None
    assert natija.narx > 0


