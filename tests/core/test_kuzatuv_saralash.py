"""4-qism — saralash va ikki darajali ro'yxat."""

from __future__ import annotations

from core.analysis.observation_mode import KuzatuvNatija, Segment
from core.analysis.structure.uptrend_filter import (
    Bosqich,
    BosqichNatija,
    Yonalish,
    YonalishNatija,
)
from core.analysis.turlar import Holat
from core.analysis.turlar import blok as blok_yasa
from core.analysis.zone_quality.zone_block import ZonaDarajasi, ZonaNatija
from core.watch_panel.top20_selector import (
    KUZATUV_HAJM,
    TOP_HAJM,
    royxatlarni_qur,
)


def _zona(daraja: ZonaDarajasi) -> ZonaNatija | None:
    """ZonaNatija — faqat `daraja` maydoni muhim, qolgani bo'sh."""
    if daraja is ZonaDarajasi.YOQ:
        return None
    return ZonaNatija(blok=blok_yasa("Zona Sifati", []), zona=None, daraja=daraja)


def natija(
    symbol: str,
    diqqat: int = 0,
    *,
    otadi: bool = True,
    yurgan: bool = False,
    daraja: ZonaDarajasi = ZonaDarajasi.YOQ,
    kuch: float | None = None,
) -> KuzatuvNatija:
    """`yurgan=True` — narx harakatni tugatgan: Top ga emas, +10 ga."""
    segmentlar = tuple(
        Segment(f"s{i}", Holat.HA if i < diqqat else Holat.YOQ, "", "1h") for i in range(4)
    )
    yonalish = YonalishNatija(Yonalish.UPTREND if otadi else Yonalish.DOWNTREND)
    return KuzatuvNatija(
        symbol=symbol,
        yonalish=yonalish,
        bosqich=BosqichNatija(Bosqich.YURGAN if yurgan else Bosqich.KORREKSIYA),
        segmentlar=segmentlar if otadi else (),
        zona_natija=_zona(daraja) if otadi else None,
        nisbiy_kuch=kuch,
    )


# --------------------------------------------------------------------------- #
#  Filtr — eng muhim qulf
# --------------------------------------------------------------------------- #


def test_downtrend_diqqat_yuqori_bolsa_ham_kirmaydi() -> None:
    """QAT'IY QOIDA: filtrdan o'tmagan coin HECH QAYERGA kirmaydi."""
    royxat = royxatlarni_qur(
        [
            natija("PAST", diqqat=4, otadi=False),
            natija("YAXSHI", diqqat=1),
        ]
    )
    nomlar = [n.symbol for n in royxat.top] + [n.symbol for n in royxat.kuzatuvda]
    assert "PAST" not in nomlar
    assert nomlar == ["YAXSHI"]
    assert royxat.otmadi == 1


# --------------------------------------------------------------------------- #
#  Saralash tartibi
# --------------------------------------------------------------------------- #


def test_diqqat_boyicha_kamayish_tartibida() -> None:
    royxat = royxatlarni_qur(
        [natija("A", 1), natija("B", 4), natija("C", 2), natija("D", 3)]
    )
    assert [n.symbol for n in royxat.top] == ["B", "D", "C", "A"]


def test_teng_diqqatda_zona_darajasi_hal_qiladi() -> None:
    royxat = royxatlarni_qur(
        [
            natija("ZAIF", 2, daraja=ZonaDarajasi.ZAIF),
            natija("KUCHLI", 2, daraja=ZonaDarajasi.KUCHLI),
            natija("ORTA", 2, daraja=ZonaDarajasi.ORTA),
        ]
    )
    assert [n.symbol for n in royxat.top] == ["KUCHLI", "ORTA", "ZAIF"]


def test_zona_ham_teng_bolsa_nisbiy_kuch_hal_qiladi() -> None:
    royxat = royxatlarni_qur(
        [
            natija("SEKIN", 2, daraja=ZonaDarajasi.ORTA, kuch=0.9),
            natija("TEZ", 2, daraja=ZonaDarajasi.ORTA, kuch=1.4),
        ]
    )
    assert [n.symbol for n in royxat.top] == ["TEZ", "SEKIN"]


def test_hammasi_teng_bolsa_tartib_BARQAROR() -> None:
    """Ikki yugurish bir xil natija berishi kerak.

    Ansiz admin har safar boshqa tartib ko'rardi va "nega o'zgardi?"
    degan savol tug'ilardi — aslida hech narsa o'zgarmagan bo'lardi.
    """
    coinlar = [natija(s, 2, daraja=ZonaDarajasi.ORTA, kuch=1.0) for s in ("C", "A", "B")]
    birinchi = [n.symbol for n in royxatlarni_qur(list(coinlar)).top]
    ikkinchi = [n.symbol for n in royxatlarni_qur(list(reversed(coinlar))).top]
    assert birinchi == ikkinchi == ["A", "B", "C"]


def test_nisbiy_kuch_yoq_bolsa_yiqilmaydi() -> None:
    royxat = royxatlarni_qur([natija("A", 2, kuch=None), natija("B", 2, kuch=1.2)])
    assert [n.symbol for n in royxat.top] == ["B", "A"]


# --------------------------------------------------------------------------- #
#  Ikki daraja
# --------------------------------------------------------------------------- #


def test_top_20_hali_yurmaganlardan_toladi() -> None:
    coinlar = [natija(f"C{i:02d}", diqqat=4 - (i % 4)) for i in range(40)]
    royxat = royxatlarni_qur(coinlar)
    assert len(royxat.top) == TOP_HAJM
    # Hammasi "hali yurmagan" — +10 bo'sh qoladi.
    assert royxat.kuzatuvda == ()


def test_yurib_bolganlar_ON_talikka_tushadi() -> None:
    """IKKI RO'YXAT — IKKI MA'NO, tartib bo'yicha bo'linish emas."""
    tayyor = [natija(f"T{i:02d}", 3) for i in range(5)]
    kech = [natija(f"K{i:02d}", 4, yurgan=True) for i in range(15)]
    royxat = royxatlarni_qur(tayyor + kech)

    # Top da FAQAT hali yurmaganlar — diqqat darajasi pastroq
    # bo'lsa ham.
    assert [n.symbol for n in royxat.top] == [f"T{i:02d}" for i in range(5)]
    assert len(royxat.kuzatuvda) == KUZATUV_HAJM
    assert all(n.symbol.startswith("K") for n in royxat.kuzatuvda)


def test_yurgan_coin_diqqat_yuqori_bolsa_ham_TOP_ga_kirmaydi() -> None:
    royxat = royxatlarni_qur(
        [natija("YURGAN", 4, yurgan=True), natija("SEKIN", 1)]
    )
    assert [n.symbol for n in royxat.top] == ["SEKIN"]
    assert [n.symbol for n in royxat.kuzatuvda] == ["YURGAN"]


def test_kam_nomzod_bolsa_suniy_toldirilmaydi() -> None:
    """Bozor tushayotganda nomzod kam bo'lishi NORMAL."""
    royxat = royxatlarni_qur([natija(f"C{i}", 2) for i in range(3)])
    assert len(royxat.top) == 3
    assert royxat.kuzatuvda == ()


def test_hech_kim_otmasa_ikkala_royxat_bosh() -> None:
    royxat = royxatlarni_qur([natija(f"C{i}", 4, otadi=False) for i in range(10)])
    assert royxat.top == ()
    assert royxat.kuzatuvda == ()
    assert royxat.otmadi == 10


def test_bosh_kirish_yiqilmaydi() -> None:
    royxat = royxatlarni_qur([])
    assert royxat.top == ()
    assert royxat.otmadi == 0


def test_top_hajmi_aynan_20_da_kesiladi() -> None:
    """Chegara aynan 20 da — bittaga adashish bo'lmasin."""
    coinlar = [natija(f"C{i:02d}", 2) for i in range(25)]
    royxat = royxatlarni_qur(coinlar)
    assert len(royxat.top) == TOP_HAJM
    assert royxat.top[-1].symbol == "C19"
    # 21-dan keyingilari TOPga sig'madi va ular "yurgan" EMAS —
    # shuning uchun +10 ga ham tushmaydi.
    assert royxat.kuzatuvda == ()
