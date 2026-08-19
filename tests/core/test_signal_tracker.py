"""2-bo'lim: signal holatini avtomatik kuzatish.

Holat mashinasi tizimning eng ko'p ishlaydigan qismi — har bir narx
nuqtasida chaqiriladi. Xato bu yerda foydalanuvchiga noto'g'ri natija
ko'rsatilishiga olib keladi, shuning uchun to'liq qamrab olinadi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.domain.enums import SignalSource, SignalStatus
from core.domain.models import Signal, SignalLevels
from core.signals import SignalEventKind, SignalTracker

BOSH = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def signal(symbol: str = "BTC", entry: float = 100.0, created_at: datetime = BOSH) -> Signal:
    return Signal(
        symbol=symbol,
        levels=SignalLevels(entry=entry, stop=entry * 0.99, tp1=entry * 1.03, tp2=entry * 1.05),
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
