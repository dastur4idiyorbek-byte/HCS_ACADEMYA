"""Retseptning 4-qadami: NOMZODGA MUDDAT.

MUAMMO. Chiqish qoidasi faqat ikkita — TP yoki Stop. Ya'ni tizim
jimgina shunday deb turibdi: "bozor qachon bo'lmasin, bir kun
bularning biriga boradi". Uchinchi yo'l — narx o'rtada osilib
qolishi — hisobga olinmagan.

Sanoat naqshida (QuantConnect LEAN) Alpha `Insight` chiqaradi:
yo'nalish, ishonch va MUDDAT. Bizda uchinchisi yo'q edi.

O'LCHOV: o'rtacha ushlash 45.2 soat, bozor esa ikki yilda +31.5%
o'sgan (`BACKTEST_NATIJA_2026-09-02_6.md`). Kapital foydasiz
pozitsiyalarda band turadi va o'sha vaqtda tizim boshqa hech narsa
qila olmaydi — ochiq signal limiti to'lgan bo'ladi.

MUHIM FARQ: `CANCELLED` va `TIMED_OUT` bir xil emas.

    CANCELLED — narx Entry'ga umuman yetmadi. Pozitsiya OCHILMAGAN,
                natija yo'q, statistikaga kirmaydi.
    TIMED_OUT — pozitsiya ochilgan, lekin na nishonga, na Stopga
                bordi. Bozor narxida yopiladi va natija HISOBGA
                KIRADI — foyda ham, zarar ham bo'lishi mumkin.

Ikkalasini bir turkumga qo'yish raqamlarni buzardi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.domain.enums import SignalStatus
from core.domain.models import Signal, signal_levels
from core.signals import SignalEventKind, SignalTracker

BOSH = datetime(2026, 1, 1, tzinfo=UTC)


def signal(created: datetime = BOSH) -> Signal:
    return Signal(
        symbol="BTC",
        levels=signal_levels(100.0, 95.0, 110.0, 120.0),
        source=__import__(
            "core.domain.enums", fromlist=["SignalSource"]
        ).SignalSource.CLASSIC_TA,
        created_at=created,
    )


def faol_kuzatuvchi(soat: float) -> tuple[SignalTracker, int]:
    """Kirish narxiga yetgan, ya'ni FAOL signal bilan kuzatuvchi."""
    tracker = SignalTracker(max_holding=timedelta(hours=soat))
    kalit = tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)  # Entry'ga yetdi -> ACTIVE
    return tracker, kalit


# --------------------------------------------------------------------------- #
#  Standart holat — muddat YO'Q
# --------------------------------------------------------------------------- #


def test_standart_holatda_muddat_yoq() -> None:
    from core.config import load_config

    assert load_config().trade_rules.max_holding_hours == 0


def test_muddatsiz_kuzatuvchi_pozitsiyani_yopmaydi() -> None:
    tracker = SignalTracker()
    tracker.track(signal())
    tracker.on_price("BTC", 100.0, BOSH)

    hodisalar = tracker.check_expiry(BOSH + timedelta(days=30), lambda _s: 101.0)

    assert hodisalar == []


# --------------------------------------------------------------------------- #
#  Muddat ishlaydi
# --------------------------------------------------------------------------- #


def test_muddat_tugasa_bozor_narxida_yopiladi() -> None:
    tracker, kalit = faol_kuzatuvchi(24)

    hodisalar = tracker.check_expiry(BOSH + timedelta(hours=25), lambda _s: 103.0)

    assert len(hodisalar) == 1
    hodisa = hodisalar[0]
    assert hodisa.kind is SignalEventKind.TIMED_OUT
    assert hodisa.new_status is SignalStatus.TIMED_OUT
    assert hodisa.price == 103.0
    assert tracker.get(kalit).status is SignalStatus.TIMED_OUT


def test_muddat_tugamaguncha_tegilmaydi() -> None:
    tracker, _ = faol_kuzatuvchi(24)

    assert tracker.check_expiry(BOSH + timedelta(hours=23), lambda _s: 103.0) == []


def test_narx_nomalum_bolsa_yopilmaydi() -> None:
    """Raqam O'YLAB TOPILMAYDI.

    Narxsiz pozitsiyani yopish natijani taxmin qilish demakdir.
    0.3-band: noaniqlik dalil emas.
    """
    tracker, kalit = faol_kuzatuvchi(24)

    hodisalar = tracker.check_expiry(BOSH + timedelta(hours=48), lambda _s: None)

    assert hodisalar == []
    assert tracker.get(kalit).status is SignalStatus.ACTIVE


def test_narx_manbai_berilmasa_muddat_ishlamaydi() -> None:
    tracker, _ = faol_kuzatuvchi(24)

    assert tracker.check_expiry(BOSH + timedelta(hours=48)) == []


def test_yopilgan_signal_qayta_yopilmaydi() -> None:
    tracker, kalit = faol_kuzatuvchi(24)
    tracker.on_price("BTC", 94.0, BOSH + timedelta(hours=1))  # Stop
    assert tracker.get(kalit).status is SignalStatus.STOPPED

    assert tracker.check_expiry(BOSH + timedelta(hours=48), lambda _s: 103.0) == []
    assert tracker.get(kalit).status is SignalStatus.STOPPED


def test_kutayotgan_signal_MUDDAT_emas_BEKOR_boladi() -> None:
    """Narx Entry'ga yetmagan bo'lsa — bu boshqa turkum.

    Pozitsiya ochilmagan, ya'ni natija yo'q. Uni `TIMED_OUT` deb
    belgilash statistikaga natijasi bo'lmagan savdoni qo'shardi.
    """
    tracker = SignalTracker(
        pending_expiry=timedelta(hours=6), max_holding=timedelta(hours=24)
    )
    kalit = tracker.track(signal())

    hodisalar = tracker.check_expiry(BOSH + timedelta(hours=48), lambda _s: 103.0)

    assert [h.kind for h in hodisalar] == [SignalEventKind.CANCELLED]
    assert tracker.get(kalit).status is SignalStatus.CANCELLED


def test_tp1_olingan_signal_ham_muddat_bilan_yopiladi() -> None:
    """Breakeven'da osilib qolgan pozitsiya ham kapitalni band qiladi."""
    tracker, kalit = faol_kuzatuvchi(24)
    tracker.on_price("BTC", 110.0, BOSH + timedelta(hours=1))  # TP1
    assert tracker.get(kalit).status is SignalStatus.TP1_HIT

    hodisalar = tracker.check_expiry(BOSH + timedelta(hours=48), lambda _s: 108.0)

    assert [h.kind for h in hodisalar] == [SignalEventKind.TIMED_OUT]


# --------------------------------------------------------------------------- #
#  Holat tizimga to'g'ri ulangan
# --------------------------------------------------------------------------- #


def test_timed_out_yopiq_holat() -> None:
    assert SignalStatus.TIMED_OUT.is_closed
    assert not SignalStatus.TIMED_OUT.is_open
    assert not SignalStatus.TIMED_OUT.is_enterable
    assert SignalStatus.TIMED_OUT.value in SignalStatus.closed_values()


def test_hodisa_signalni_yopadi() -> None:
    from core.signals.events import SignalEvent

    hodisa = SignalEvent(
        signal_id=1,
        symbol="BTC",
        kind=SignalEventKind.TIMED_OUT,
        price=100.0,
        at=BOSH,
        new_status=SignalStatus.TIMED_OUT,
    )

    assert hodisa.closes_signal


@pytest.mark.parametrize("kalit", ["holat_timed_out", "qisqa_timed_out"])
def test_tarjima_bor(kalit: str) -> None:
    """Yangi holat ekranda kod nomi bilan ko'rinmasin."""
    import json
    from pathlib import Path

    matnlar = json.loads(
        (Path(__file__).resolve().parents[2] / "bot" / "i18n" / "uz.json").read_text(
            encoding="utf-8"
        )
    )

    assert kalit in matnlar["signal"]
