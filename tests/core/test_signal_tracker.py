"""2-bo'lim: signal holatini avtomatik kuzatish.

Holat mashinasi tizimning eng ko'p ishlaydigan qismi — har bir narx
nuqtasida chaqiriladi. Xato bu yerda foydalanuvchiga noto'g'ri natija
ko'rsatilishiga olib keladi, shuning uchun to'liq qamrab olinadi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.domain.enums import SignalSource, SignalStatus
from core.domain.models import Signal, signal_levels
from core.signals import SignalEventKind, SignalTracker

BOSH = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def signal(symbol: str = "BTC", entry: float = 100.0, created_at: datetime = BOSH) -> Signal:
    return Signal(
        symbol=symbol,
        levels=signal_levels(entry=entry, stop=entry * 0.99, tp1=entry * 1.03, tp2=entry * 1.05),
        source=SignalSource.MANUAL,
        created_at=created_at,
    )


@pytest.fixture
def tracker() -> SignalTracker:
    return SignalTracker()


# --------------------------------------------------------------------------- #
#  Asosiy yo'l: ⏳ -> ✅ -> 🎯 -> 🎯🎯
# --------------------------------------------------------------------------- #


def test_toliq_muvaffaqiyatli_yol(tracker: SignalTracker) -> None:
    key = tracker.track(signal())

    assert tracker.on_price("BTC", 101.0, BOSH) == [], "narx hali Entry'ga yetmagan"
    assert tracker.get(key).status is SignalStatus.PENDING

    hodisalar = tracker.on_price("BTC", 100.0, BOSH + timedelta(minutes=5))
    assert [h.kind for h in hodisalar] == [SignalEventKind.ACTIVATED]
    assert tracker.get(key).status is SignalStatus.ACTIVE

    hodisalar = tracker.on_price("BTC", 103.0, BOSH + timedelta(hours=2))
    assert [h.kind for h in hodisalar] == [SignalEventKind.TP1_HIT]
    assert tracker.get(key).status is SignalStatus.TP1_HIT

    hodisalar = tracker.on_price("BTC", 105.0, BOSH + timedelta(hours=4))
    assert [h.kind for h in hodisalar] == [SignalEventKind.TP2_HIT]
    assert tracker.get(key).status is SignalStatus.TP2_HIT
    assert tracker.get(key).closed_at is not None


def test_stop_signalni_yopadi(tracker: SignalTracker) -> None:
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)

    hodisalar = tracker.on_price("BTC", 99.0, BOSH + timedelta(hours=3))
    turlar = [h.kind for h in hodisalar]
    assert SignalEventKind.STOPPED in turlar
    assert tracker.get(key).status is SignalStatus.STOPPED


def test_tp1_dan_keyin_stop_ham_mumkin(tracker: SignalTracker) -> None:
    """TP1 olingach narx qaytib Stop'ga tushishi mumkin."""
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    tracker.on_price("BTC", 103.0, BOSH + timedelta(hours=1))

    hodisalar = tracker.on_price("BTC", 99.0, BOSH + timedelta(hours=5))
    assert SignalEventKind.STOPPED in [h.kind for h in hodisalar]
    assert tracker.get(key).status is SignalStatus.STOPPED


def test_yopilgan_signal_qayta_ozgarmaydi(tracker: SignalTracker) -> None:
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    tracker.on_price("BTC", 99.0, BOSH + timedelta(hours=3))

    assert tracker.on_price("BTC", 110.0, BOSH + timedelta(hours=4)) == []
    assert tracker.get(key).status is SignalStatus.STOPPED


# --------------------------------------------------------------------------- #
#  Narx sakrashi (gap) — ehtiyotkor talqin
# --------------------------------------------------------------------------- #


def test_narx_sakrasa_kirib_darhol_stop_yeydi(tracker: SignalTracker) -> None:
    """Narx Entry'dan Stop'gacha bir sakrashda tushsa.

    Limit buyurtma Entry'da bajarilib, keyin Stop yegan deb qaraladi — bu
    eng ehtiyotkor talqin (0.3-band). "Kirmagan" deb hisoblash foydani
    oshirib ko'rsatardi.
    """
    key = tracker.track(signal())
    hodisalar = tracker.on_price("BTC", 98.0, BOSH + timedelta(minutes=1))

    turlar = [h.kind for h in hodisalar]
    assert SignalEventKind.ACTIVATED in turlar
    assert SignalEventKind.STOPPED in turlar
    assert tracker.get(key).status is SignalStatus.STOPPED


def test_narx_sakrasa_tp1_va_tp2_ketma_ket(tracker: SignalTracker) -> None:
    tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)

    hodisalar = tracker.on_price("BTC", 106.0, BOSH + timedelta(hours=1))
    assert [h.kind for h in hodisalar] == [SignalEventKind.TP1_HIT, SignalEventKind.TP2_HIT]


# --------------------------------------------------------------------------- #
#  3.8 — "Yolg'on signal"
# --------------------------------------------------------------------------- #


def test_tez_stop_yolgon_signal_deb_belgilanadi(tracker: SignalTracker) -> None:
    """Faol bo'lgach 1 soat ichida Stop — zaif kirish nuqtasi belgisi."""
    tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)

    hodisalar = tracker.on_price("BTC", 99.0, BOSH + timedelta(minutes=30))
    assert SignalEventKind.FALSE_SIGNAL in [h.kind for h in hodisalar]


def test_kech_stop_yolgon_signal_emas(tracker: SignalTracker) -> None:
    tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)

    hodisalar = tracker.on_price("BTC", 99.0, BOSH + timedelta(hours=6))
    assert SignalEventKind.FALSE_SIGNAL not in [h.kind for h in hodisalar]


# --------------------------------------------------------------------------- #
#  Mustaqillik: bir signal boshqasiga ta'sir qilmaydi
# --------------------------------------------------------------------------- #


def test_signallar_mustaqil_kuzatiladi(tracker: SignalTracker) -> None:
    btc = tracker.track(signal("BTC", entry=100))
    eth = tracker.track(signal("ETH", entry=50))

    tracker.on_price("BTC", 100.0, BOSH)

    assert tracker.get(btc).status is SignalStatus.ACTIVE
    assert tracker.get(eth).status is SignalStatus.PENDING, "ETH ta'sirlanmasligi kerak"


def test_bir_xil_coinda_bir_nechta_signal(tracker: SignalTracker) -> None:
    past = tracker.track(signal("BTC", entry=100))
    baland = tracker.track(signal("BTC", entry=102))

    tracker.on_price("BTC", 101.5, BOSH)

    assert tracker.get(past).status is SignalStatus.PENDING
    assert tracker.get(baland).status is SignalStatus.ACTIVE


def test_kuzatiladigan_coinlar_royxati(tracker: SignalTracker) -> None:
    """WebSocket obunasi shu ro'yxatga tayanadi."""
    tracker.track(signal("BTC"))
    eth = tracker.track(signal("ETH", entry=50))
    assert tracker.symbols() == {"BTC", "ETH"}

    tracker.on_price("ETH", 50.0, BOSH)
    tracker.on_price("ETH", 49.0, BOSH + timedelta(hours=5))
    assert tracker.get(eth).status is SignalStatus.STOPPED
    assert tracker.symbols() == {"BTC"}, "yopilgan signal kuzatuvdan chiqadi"


def test_ochiq_signallar_royxati(tracker: SignalTracker) -> None:
    """Risk Engine (4.2-band) shu ro'yxatga tayanadi."""
    tracker.track(signal("BTC"))
    tracker.track(signal("ETH", entry=50))
    assert len(tracker.open_signals) == 2

    tracker.on_price("BTC", 100.0, BOSH)
    tracker.on_price("BTC", 99.0, BOSH + timedelta(hours=5))
    assert len(tracker.open_signals) == 1


# --------------------------------------------------------------------------- #
#  4.1 — Zaiflashmoqda
# --------------------------------------------------------------------------- #


def test_zaiflashish_signalni_yopmaydi(tracker: SignalTracker) -> None:
    """Bu TAVSIYA — majburiy avtomatik yopish EMAS."""
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)

    hodisa = tracker.mark_weakening(key, BOSH + timedelta(hours=1), "Ball 40 ga tushdi")
    assert hodisa.kind is SignalEventKind.WEAKENING
    assert tracker.get(key).status is SignalStatus.WEAKENING
    assert tracker.get(key).status.is_open, "signal ochiq qolishi kerak"


def test_zaiflashgan_signal_tp_ga_bora_oladi(tracker: SignalTracker) -> None:
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    tracker.mark_weakening(key, BOSH + timedelta(hours=1), "ball pasaydi")

    hodisalar = tracker.on_price("BTC", 103.0, BOSH + timedelta(hours=2))
    assert [h.kind for h in hodisalar] == [SignalEventKind.TP1_HIT]


def test_zaiflashish_takror_ogohlantirmaydi(tracker: SignalTracker) -> None:
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    tracker.mark_weakening(key, BOSH + timedelta(hours=1), "birinchi")
    assert tracker.mark_weakening(key, BOSH + timedelta(hours=2), "ikkinchi") is None


def test_yopilgan_signal_zaiflasha_olmaydi(tracker: SignalTracker) -> None:
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    tracker.on_price("BTC", 99.0, BOSH + timedelta(hours=5))
    assert tracker.mark_weakening(key, BOSH + timedelta(hours=6), "kech") is None


# --------------------------------------------------------------------------- #
#  Eskirish va himoya
# --------------------------------------------------------------------------- #


def test_entryga_yetmagan_signal_eskiradi(tracker: SignalTracker) -> None:
    key = tracker.track(signal())
    hodisalar = tracker.check_expiry(BOSH + timedelta(hours=25))

    assert [h.kind for h in hodisalar] == [SignalEventKind.CANCELLED]
    assert tracker.get(key).status is SignalStatus.CANCELLED


def test_faol_signal_eskirmaydi(tracker: SignalTracker) -> None:
    tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    assert tracker.check_expiry(BOSH + timedelta(days=5)) == []


def test_notogri_narx_etiborsiz_qoldiriladi(tracker: SignalTracker) -> None:
    key = tracker.track(signal())
    assert tracker.on_price("BTC", 0, BOSH) == []
    assert tracker.on_price("BTC", -5, BOSH) == []
    assert tracker.get(key).status is SignalStatus.PENDING


def test_naive_vaqt_rad_etiladi(tracker: SignalTracker) -> None:
    tracker.track(signal())
    with pytest.raises(ValueError, match="timezone-aware"):
        tracker.on_price("BTC", 100.0, datetime(2026, 8, 19, 12, 0))


def test_coin_belgisi_registrga_bogliq_emas(tracker: SignalTracker) -> None:
    key = tracker.track(signal("btc"))
    tracker.on_price("BTC", 100.0, BOSH)
    assert tracker.get(key).status is SignalStatus.ACTIVE


# --------------------------------------------------------------------------- #
#  Qo'lda bekor qilish (admin)
# --------------------------------------------------------------------------- #


def test_qolda_bekor_qilish_signalni_yopadi(tracker: SignalTracker) -> None:
    key = tracker.track(signal())

    hodisa = tracker.cancel(key, BOSH + timedelta(minutes=5), "Admin bekor qildi")

    assert hodisa is not None
    assert hodisa.kind is SignalEventKind.CANCELLED
    assert hodisa.closes_signal
    assert hodisa.detail == "Admin bekor qildi"
    assert tracker.get(key).status is SignalStatus.CANCELLED
    assert tracker.symbols() == set(), "bekor qilingan coin kuzatuvdan chiqadi"


def test_faol_signal_ham_bekor_qilinadi(tracker: SignalTracker) -> None:
    """Kutilayotgan signalgina emas — allaqachon sotib olingani ham."""
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    assert tracker.get(key).status is SignalStatus.ACTIVE

    hodisa = tracker.cancel(key, BOSH + timedelta(hours=1), "Admin bekor qildi", price=102.0)

    assert hodisa is not None
    assert hodisa.price == 102.0, "yopilish narxi — bozordagi joriy narx"
    assert tracker.get(key).status is SignalStatus.CANCELLED


def test_yopilgan_signal_qayta_bekor_qilinmaydi(tracker: SignalTracker) -> None:
    """TP yoki Stop bilan tugagan natija keyin o'zgartirilmaydi."""
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    tracker.on_price("BTC", 99.0, BOSH + timedelta(hours=2))
    assert tracker.get(key).status is SignalStatus.STOPPED

    assert tracker.cancel(key, BOSH + timedelta(hours=3), "kech") is None
    assert tracker.get(key).status is SignalStatus.STOPPED


def test_notanish_signal_bekor_qilinmaydi(tracker: SignalTracker) -> None:
    assert tracker.cancel(12345, BOSH, "yo'q signal") is None


def test_narx_berilmasa_kirish_narxi_olinadi(tracker: SignalTracker) -> None:
    """Narx noma'lum bo'lsa foyda/zarar nolga teng deb qaraladi (0.3-band)."""
    key = tracker.track(signal(entry=100.0))
    hodisa = tracker.cancel(key, BOSH, "sabab")
    assert hodisa.price == 100.0


def test_tp1_bayrogi_stopdan_keyin_ham_qoladi(tracker: SignalTracker) -> None:
    """TP1 dan keyin Stop ishlasa, qismli sotish hisobga olinishi kerak.

    `status` ga qarash yetarli emas edi: u STOPPED bo'lib qolardi va
    "TP1 oldi, keyin Stop" sof zarar ko'rinardi (5.4-band).
    """
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    tracker.on_price("BTC", 103.0, BOSH + timedelta(hours=1))
    assert tracker.get(key).tp1_reached is True

    tracker.on_price("BTC", 99.0, BOSH + timedelta(hours=2))
    assert tracker.get(key).status is SignalStatus.STOPPED
    assert tracker.get(key).tp1_reached is True


# --------------------------------------------------------------------------- #
#  Kirish mumkinligi (foydalanuvchi ro'yxati shunga tayanadi)
# --------------------------------------------------------------------------- #


def test_kirish_mumkin_ochiq_bilan_bir_xil_emas() -> None:
    """TP1 olingan signal ochiq, lekin unga endi kirilmaydi.

    Ikkalasi bitta xususiyat bo'lib qolsa, foydalanuvchi ro'yxatida
    kech qolingan signalning narxlari ham ochilib ketardi.
    """
    kirish_mumkin = {h for h in SignalStatus if h.is_enterable}
    assert kirish_mumkin == {SignalStatus.PENDING, SignalStatus.ACTIVE}

    assert SignalStatus.TP1_HIT.is_open, "TP1 olingan signal hali kuzatuvda"
    assert not SignalStatus.TP1_HIT.is_enterable, "lekin unga kirish kech"
    assert not SignalStatus.WEAKENING.is_enterable, "zaiflashayotganiga ham"


def test_yopilgan_holatlarga_kirib_bolmaydi() -> None:
    for holat in SignalStatus:
        if holat.is_closed:
            assert not holat.is_enterable, holat


# --------------------------------------------------------------------------- #
#  TP1 dan keyin Stop kirish narxiga ko'tariladi (breakeven)
# --------------------------------------------------------------------------- #


def test_tp1_dan_keyin_stop_kirish_narxiga_kotariladi(tracker: SignalTracker) -> None:
    """TP1 da pozitsiyaning bir qismi sotiladi va qo'lda foyda qoladi.

    Qolgan qismni eski Stopda ushlab turish shu foydani qaytarib berish
    xavfini saqlaydi. Stop kirish narxiga ko'tarilsa, eng yomon holat —
    nolga chiqish.
    """
    s = signal()  # entry 100, stop 99, tp1 103
    key = tracker.track(s)
    tracker.on_price("BTC", 100.0, BOSH)          # faollashdi
    tracker.on_price("BTC", 103.0, BOSH)          # TP1
    assert tracker.get(key).status is SignalStatus.TP1_HIT
    assert tracker.get(key).effective_stop == 100.0

    # 99.5 — ESKI Stop (99) dan yuqori, lekin kirish narxidan past
    hodisalar = tracker.on_price("BTC", 99.5, BOSH)
    assert [h.kind for h in hodisalar] == [SignalEventKind.STOPPED]
    assert tracker.get(key).status is SignalStatus.STOPPED


def test_tp1_gacha_stop_ozgarmaydi(tracker: SignalTracker) -> None:
    """Breakeven FAQAT TP1 dan keyin. Aks holda har bir signal kirish
    narxida yopilib, tuzilmaga nafas olishga joy qolmasdi."""
    s = signal()
    key = tracker.track(s)
    tracker.on_price("BTC", 100.0, BOSH)

    assert tracker.get(key).effective_stop == 99.0
    assert tracker.on_price("BTC", 99.5, BOSH) == []
    assert tracker.get(key).status is SignalStatus.ACTIVE


def test_tp1_xabarida_stopni_kotarish_aytiladi(tracker: SignalTracker) -> None:
    """Foydalanuvchi buni O'ZI qilishi kerak — bot uning hisobiga
    ulanmaydi, shuning uchun ko'rsatma aniq yozilishi shart."""
    tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    hodisalar = tracker.on_price("BTC", 103.0, BOSH)

    matn = hodisalar[0].detail
    assert "Stopni kirish narxiga" in matn
    assert "100" in matn


def test_breakeven_chiqish_yolgon_signal_deb_belgilanmaydi(
    tracker: SignalTracker,
) -> None:
    """"Yolg'on signal" — faol bo'lgach TEZ Stop yegan holat (3.8-band).

    TP1 ni olib, keyin nolga qaytgan signal esa foyda keltirgan: uni
    yolg'on deb belgilash statistikani buzardi.
    """
    tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    tracker.on_price("BTC", 103.0, BOSH + timedelta(minutes=5))
    hodisalar = tracker.on_price("BTC", 99.9, BOSH + timedelta(minutes=10))

    assert all(h.kind is not SignalEventKind.FALSE_SIGNAL for h in hodisalar)


def test_tp2_gacha_kuzatuv_davom_etadi(tracker: SignalTracker) -> None:
    """TP1 dan keyin signal YOPILMAYDI — to'liq TP gacha yuradi."""
    key = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)
    tracker.on_price("BTC", 103.0, BOSH)
    assert tracker.get(key).status.is_open

    hodisalar = tracker.on_price("BTC", 105.0, BOSH)
    assert [h.kind for h in hodisalar] == [SignalEventKind.TP2_HIT]
    assert tracker.get(key).status is SignalStatus.TP2_HIT
