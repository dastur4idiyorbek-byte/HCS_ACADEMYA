"""Zanjir dvigateli, holat kuzatuvchi va darajalar."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.chain import HolatKuzatuvchi, ZanjirKirish, zanjir_yur
from core.analysis.fundamental.catalyst_watch import Katalizator
from core.analysis.fundamental.fundamental_block import FundamentalKirish
from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.analysis.turlar import blok, ha, yoq
from core.analysis.zone_quality.fibonacci import Zona
from core.domain.models import Candle
from core.position import darajalar_qur
from core.position.scaling_out import chiqish_rejasi, trailing_stop

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def sham(i: int, o: float, h: float, low: float, c: float) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(days=i), open=o, high=h, low=low, close=c, volume=1000.0
    )


# --------------------------------------------------------------------------- #
#  Zanjir uzilishi
# --------------------------------------------------------------------------- #


def test_qattiq_tosiq_birinchi_blokda_uzadi() -> None:
    """Keyingi bloklar UMUMAN hisoblanmaydi — nafaqat e'tiborsiz qoldiriladi."""
    natija = zanjir_yur(
        ZanjirKirish(
            symbol="TEST",
            shamlar=[sham(i, 100, 105, 95, 100) for i in range(50)],
            fundamental=FundamentalKirish(
                voqea=Katalizator(unlock_kun=1, unlock_ulush_pct=30.0)
            ),
        )
    )
    assert natija.zanjir.uzildi_blokda == "Fundamental"
    assert len(natija.zanjir.bloklar) == 1


def test_struktura_bosh_bolsa_zona_hisoblanmaydi() -> None:
    """Yassi narx — struktura yo'q, zanjir 2-blokda uziladi."""
    natija = zanjir_yur(
        ZanjirKirish(symbol="TEST", shamlar=[sham(i, 100, 100, 100, 100) for i in range(50)])
    )
    assert natija.zanjir.uzildi_blokda == "Struktura"
    assert natija.zona_natija is None


def test_bosh_fundamental_zanjirni_uzmaydi() -> None:
    """Backtestdagi odatiy holat: fundamental manba yo'q.

    Bu zanjirni UZMASLIGI kerak, aks holda birorta signal chiqmasdi.
    """
    natija = zanjir_yur(
        ZanjirKirish(symbol="TEST", shamlar=[sham(i, 100, 105, 95, 100) for i in range(50)])
    )
    assert natija.zanjir.uzildi_blokda != "Fundamental"


# --------------------------------------------------------------------------- #
#  Holat kuzatuvchi (6-qism)
# --------------------------------------------------------------------------- #


def test_bekor_qilish_keyingilarini_ham_ochiradi() -> None:
    k = HolatKuzatuvchi()
    h = k.holat("BTC")
    for nom in ("Fundamental", "Struktura", "Zona Sifati", "Tasdiqlash"):
        h.bloklar[nom] = blok(nom, [ha("x")])

    k.bekor_qil("BTC", "Struktura")

    assert set(h.bloklar) == {"Fundamental"}


def test_qarshi_choch_strukturani_buzadi() -> None:
    k = HolatKuzatuvchi()
    k.holat("BTC").bloklar["Struktura"] = blok("Struktura", [ha("x")])
    assert k.tez_tekshir("BTC", qarshi_choch=True) == "Struktura"


def test_narx_zonadan_pastga_tushsa_zona_bekor() -> None:
    k = HolatKuzatuvchi()
    h = k.holat("BTC")
    h.bloklar["Zona Sifati"] = blok("Zona Sifati", [ha("x")])
    h.zona = Zona(100, 110, "fib")
    assert k.tez_tekshir("BTC", narx=95.0) == "Zona Sifati"


def test_narx_zonadan_yuqoriga_chiqsa_buzilish_emas() -> None:
    """Yuqoriga chiqish — harakat boshlangani, buzilish emas."""
    k = HolatKuzatuvchi()
    h = k.holat("BTC")
    h.bloklar["Zona Sifati"] = blok("Zona Sifati", [ha("x")])
    h.zona = Zona(100, 110, "fib")
    assert k.tez_tekshir("BTC", narx=130.0) is None


def test_qattiq_tosiq_hammasini_bekor_qiladi() -> None:
    k = HolatKuzatuvchi()
    h = k.holat("BTC")
    for nom in ("Fundamental", "Struktura"):
        h.bloklar[nom] = blok(nom, [ha("x")])
    assert k.tez_tekshir("BTC", qattiq_tosiq=True) == "Fundamental"
    assert h.bloklar == {}


def test_monitor_matni_tort_qatorli() -> None:
    """Jonli Oshxona ko'rinishi (2-prompt, 6-qism)."""
    k = HolatKuzatuvchi()
    k.holat("BTC").bloklar["Fundamental"] = blok("Fundamental", [ha("a"), yoq("b")])
    matn = k.holat("BTC").matn()
    assert "BTC" in matn
    assert "Fundamental: 1/2" in matn
    assert matn.count("tekshirilmagan") == 3


# --------------------------------------------------------------------------- #
#  Darajalar (5-qism)
# --------------------------------------------------------------------------- #


def _nuqtalar() -> list[Swing]:
    return [
        Swing(SwingTuri.PAST, 90.0, BOSH, 0),
        Swing(SwingTuri.YUQORI, 120.0, BOSH, 5),
        Swing(SwingTuri.YUQORI, 140.0, BOSH, 8),
    ]


def test_stop_zona_chetidan_olinadi() -> None:
    """Qat'iy foiz EMAS — struktura (2-prompt, "NIMA QILINMAYDI")."""
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), _nuqtalar(), 100.0)
    assert d.yaroqli
    assert d.stop == 95.0
    assert d.entry == 100.0


def test_narx_zonadan_pastda_rad_etiladi() -> None:
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), _nuqtalar(), 90.0)
    assert not d.yaroqli
    assert "zona buzilgan" in d.rad_sababi


def test_narx_zona_ustida_bolsa_entry_zona_cheti() -> None:
    """Entry = joriy narx QILINMAYDI — eski tizimning o'lik tarmog'i.

    Bu yerda LIMIT buyurtma zonaning yuqori chetida kutadi.
    """
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), _nuqtalar(), 115.0)
    assert d.entry == 105.0


def test_juda_yaqin_stop_rad_etiladi() -> None:
    d = darajalar_qur(Zona(99.0, 100.0, "fib"), _nuqtalar(), 100.0)
    assert not d.yaroqli
    assert "juda yaqin" in d.rad_sababi


def test_juda_uzoq_stop_rad_etiladi() -> None:
    d = darajalar_qur(Zona(50.0, 105.0, "fib"), _nuqtalar(), 100.0)
    assert not d.yaroqli
    assert "juda uzoq" in d.rad_sababi


def test_past_nisbat_rad_etiladi() -> None:
    """TP1/Stop poli — eski tizimda YAGONA ishlagan narsa edi."""
    nuqtalar = [
        Swing(SwingTuri.PAST, 90.0, BOSH, 0),
        Swing(SwingTuri.YUQORI, 101.0, BOSH, 5),
    ]
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), nuqtalar, 100.0)
    assert not d.yaroqli
    assert "nisbati past" in d.rad_sababi


def test_tp_soni_moslashuvchan() -> None:
    """1, 2 yoki 3 — struktura nechta nuqta bersa."""
    bitta = [Swing(SwingTuri.YUQORI, 140.0, BOSH, 8)]
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), bitta, 100.0)
    assert len(d.tplar) == 1


def test_tp_takrorlanmaydi() -> None:
    """Bir xil narxdagi ikkita swing — bitta qarshilik, ikkita TP emas."""
    nuqtalar = [
        Swing(SwingTuri.YUQORI, 140.0, BOSH, 8),
        Swing(SwingTuri.YUQORI, 140.0, BOSH, 12),
    ]
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), nuqtalar, 100.0)
    assert d.tplar == (140.0,)


def test_YAQIN_darajalar_BITTA_TP_ga_birlashadi() -> None:
    """2026-09-04 da jonli signalda topilgan kamchilik.

    LTC signalida TP2 = 54.70, TP3 = 54.78 chiqdi — orasi 0.16%.
    Bu ikkita nishon emas, BITTA qarshilikning ikki nuqtasi.
    Pozitsiyani u yerda 30/30 qilib bo'lish ma'nosiz: ikkinchi
    sotuvning komissiyasi (0.1% + 0.05% sirg'anish) farqning katta
    qismini yeydi, ekranda esa foydalanuvchi ikkita bir xil raqamni
    ko'radi.

    Ilgari faqat AYNAN TENG narxlar birlashardi, ya'ni qoida
    so'zda bor edi-yu amalda deyarli hech qachon ishlamasdi:
    bozorda ikkita swing bir xil songa tushishi juda kam uchraydi.
    """
    nuqtalar = [
        Swing(SwingTuri.YUQORI, 107.7, BOSH, 8),   # TP1
        Swing(SwingTuri.YUQORI, 111.6, BOSH, 12),  # TP2
        Swing(SwingTuri.YUQORI, 111.8, BOSH, 16),  # TP2 dan 0.2% — birlashadi
    ]
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), nuqtalar, 100.0)

    assert d.yaroqli
    assert d.tplar == (107.7, 111.6), "yaqin darajalar birlashmadi"


def test_birlashganda_PASTKISI_qoladi() -> None:
    """Pastki daraja birinchi uriladi — bajarilish ehtimoli yuqori.

    Yuqorisini tanlash natijani optimistik tomonga surardi.
    """
    nuqtalar = [
        Swing(SwingTuri.YUQORI, 120.0, BOSH, 8),
        Swing(SwingTuri.YUQORI, 120.5, BOSH, 12),
    ]
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), nuqtalar, 100.0)
    assert d.tplar == (120.0,)


def test_UZOQ_darajalar_saqlanadi() -> None:
    """Birlashtirish haqiqiy qarshiliklarni yo'qotmasin."""
    nuqtalar = [
        Swing(SwingTuri.YUQORI, 110.0, BOSH, 8),
        Swing(SwingTuri.YUQORI, 120.0, BOSH, 12),
        Swing(SwingTuri.YUQORI, 130.0, BOSH, 16),
    ]
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), nuqtalar, 100.0)
    assert d.tplar == (110.0, 120.0, 130.0)


def test_birlashtirish_KESISHDAN_OLDIN_boladi() -> None:
    """Yaqin swinglar to'plami uzoqdagi TP ni siqib chiqarmasin.

    Eng yaqin uchtasi bir joyda to'planib qolsa, ilgari ro'yxat
    o'sha uchta bir xil daraja bilan to'lardi va HAQIQIY uzoq
    qarshiliklar umuman ko'rinmasdi.
    """
    nuqtalar = [
        Swing(SwingTuri.YUQORI, 110.0, BOSH, 8),
        Swing(SwingTuri.YUQORI, 110.3, BOSH, 10),
        Swing(SwingTuri.YUQORI, 110.6, BOSH, 12),
        Swing(SwingTuri.YUQORI, 125.0, BOSH, 14),
        Swing(SwingTuri.YUQORI, 140.0, BOSH, 16),
    ]
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), nuqtalar, 100.0)
    assert d.tplar == (110.0, 125.0, 140.0)


def test_oraliq_nolga_qoyilsa_birlashtirish_OCHADI() -> None:
    """Sozlama o'chirilsa eski xatti-harakat qaytadi — o'lchov uchun."""
    nuqtalar = [
        Swing(SwingTuri.YUQORI, 120.0, BOSH, 8),
        Swing(SwingTuri.YUQORI, 120.5, BOSH, 12),
    ]
    d = darajalar_qur(
        Zona(95.0, 105.0, "fib"), nuqtalar, 100.0, eng_kam_oraliq_pct=0.0
    )
    assert d.tplar == (120.0, 120.5)


def test_qarshi_nuqta_yoq_bolsa_rad() -> None:
    d = darajalar_qur(Zona(95.0, 105.0, "fib"), [], 100.0)
    assert not d.yaroqli
    assert "struktura nuqtasi" in d.rad_sababi


# --------------------------------------------------------------------------- #
#  Chiqish rejasi
# --------------------------------------------------------------------------- #


def test_ulushlar_tp_soniga_moslashadi() -> None:
    r = chiqish_rejasi()
    assert r.ulush(0, 1) == pytest.approx(100.0)
    assert [r.ulush(i, 2) for i in range(2)] == [50.0, 50.0]
    assert [r.ulush(i, 3) for i in range(3)] == [50.0, 30.0, 20.0]


def test_trailing_standart_holatda_ochiq() -> None:
    """O'LCHANGAN QAROR: eski tizimda surilgan Stop PF ni 0.84 -> 0.36 qilgan."""
    assert trailing_stop(100.0, 90.0, 130.0, chiqish_rejasi()) is None


def test_trailing_faqat_yuqoriga_suriladi() -> None:
    r = chiqish_rejasi(trailing_yoqilgan=True, trailing_r=1.0)
    assert trailing_stop(100.0, 90.0, 105.0, r) == pytest.approx(95.0)  # 105-10 > 90
    assert trailing_stop(100.0, 90.0, 95.0, r) is None                  # 95-10 < 90


def test_trailing_r_birligida() -> None:
    """Foizda emas, R da — 100$ va 0.001$ coinda bir xil ishlasin."""
    r = chiqish_rejasi(trailing_yoqilgan=True, trailing_r=1.0)
    assert trailing_stop(100.0, 90.0, 120.0, r) == pytest.approx(110.0)


def test_buzuq_daraja_trailingni_yiqitmaydi() -> None:
    r = chiqish_rejasi(trailing_yoqilgan=True)
    assert trailing_stop(100.0, 100.0, 120.0, r) is None
