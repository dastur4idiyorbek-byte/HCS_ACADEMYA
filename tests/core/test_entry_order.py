"""5.1.0-band: kirish buyurtmasi turini avtomatik tanlash."""

from __future__ import annotations

import pytest

from core.analysis import decide_entry_plan
from core.config.schema import EntryOrderConfig
from core.domain.enums import ExitOrderType, OrderType
from core.domain.models import SignalLevels, signal_levels

KONFIG = EntryOrderConfig(market_threshold_pct=0.15, zone_broken_threshold_pct=0.30)


def darajalar(entry: float = 100.0) -> SignalLevels:
    return signal_levels(entry=entry, stop=entry * 0.992, tp1=entry * 1.035, tp2=entry * 1.05)


def test_narx_zonaga_yetmagan_bolsa_limit() -> None:
    """Narx Entry'dan yuqorida — kutamiz, Limit buyurtma."""
    reja = decide_entry_plan(101.5, darajalar(), KONFIG)
    assert reja.order_type is OrderType.LIMIT
    assert reja.entry_price == 100.0, "Limit buyurtma Entry narxida qo'yiladi"
    assert reja.is_valid


def test_narx_zonada_bolsa_market() -> None:
    """Narx allaqachon Entry zonasida — kutish shart emas."""
    reja = decide_entry_plan(100.1, darajalar(), KONFIG)
    assert reja.order_type is OrderType.MARKET
    assert reja.entry_price == 100.1, "Market buyurtma joriy narxda bajariladi"
    assert reja.is_valid


def test_narx_aynan_entryda_bolsa_market() -> None:
    reja = decide_entry_plan(100.0, darajalar(), KONFIG)
    assert reja.order_type is OrderType.MARKET
    assert reja.distance_pct == pytest.approx(0.0)


@pytest.mark.parametrize("narx", [100.15, 99.85])
def test_chegara_aynan_ustida_market(narx: float) -> None:
    """Chegara qamrab oluvchi (inclusive) — 0.15% aynan MARKET hisoblanadi."""
    assert decide_entry_plan(narx, darajalar(), KONFIG).order_type is OrderType.MARKET


def test_zona_buzilgan_bolsa_signal_berilmaydi() -> None:
    """0.3-band fail-safe: narx zonadan pastga tushsa, kirish asosi yo'qolgan."""
    reja = decide_entry_plan(99.5, darajalar(), KONFIG)
    assert not reja.is_valid
    assert "zonasi ushlab tura olmadi" in reja.reason


def test_zona_buzilish_chegarasi_orasidagi_holat() -> None:
    """MARKET chegarasidan tashqarida, lekin zona hali buzilmagan."""
    reja = decide_entry_plan(99.75, darajalar(), KONFIG)  # -0.25%
    assert reja.order_type is OrderType.LIMIT
    assert reja.is_valid
    assert reja.entry_price == 100.0


def test_chiqish_har_doim_oco() -> None:
    for narx in (101.5, 100.0, 99.5):
        assert decide_entry_plan(narx, darajalar(), KONFIG).exit_order_type is ExitOrderType.OCO


def test_masofa_foizi_togri_hisoblanadi() -> None:
    reja = decide_entry_plan(102.0, darajalar(), KONFIG)
    assert reja.distance_pct == pytest.approx(2.0)

    reja = decide_entry_plan(98.0, darajalar(), KONFIG)
    assert reja.distance_pct == pytest.approx(-2.0)


def test_manfiy_narx_rad_etiladi() -> None:
    with pytest.raises(ValueError, match="musbat"):
        decide_entry_plan(0, darajalar(), KONFIG)


def test_arzon_coinlarda_ham_ishlaydi() -> None:
    """Foiz asosidagi hisob narx miqyosiga bog'liq bo'lmasligi kerak."""
    arzon = signal_levels(entry=0.00042, stop=0.0004167, tp1=0.0004347, tp2=0.000441)
    reja = decide_entry_plan(0.0004203, arzon, KONFIG)
    assert reja.order_type is OrderType.MARKET
