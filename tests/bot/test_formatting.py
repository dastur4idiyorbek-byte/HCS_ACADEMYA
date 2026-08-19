"""5.1.0-band: signal-kartochka shabloni."""

from __future__ import annotations

from bot.formatting import format_pct, format_price, render_signal_card
from core.analysis import decide_entry_plan
from core.config.schema import EntryOrderConfig, PositionSizingConfig
from core.domain.models import SignalLevels
from core.position_sizing import PositionSizer

KONFIG = EntryOrderConfig()


def darajalar() -> SignalLevels:
    return SignalLevels(entry=2450.0, stop=2431.4, tp1=2523.5, tp2=2560.0)


def test_kartochka_spetsifikatsiya_tuzilishiga_mos() -> None:
    reja = decide_entry_plan(2478.0, darajalar(), KONFIG)
    kartochka = render_signal_card("eth", darajalar(), reja)

    assert "🟢 SIGNAL: ETH/USDT" in kartochka
    assert "📥 KIRISH" in kartochka
    assert "📤 CHIQISH (OCO)" in kartochka
    assert "📊 Risk/Reward: 1:" in kartochka
    for qator in ("🎯 TP1:", "🎯 TP2:", "🛑 Stop:"):
        assert qator in kartochka


def test_limit_va_market_kartochkada_korinadi() -> None:
    kutish = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    darhol = render_signal_card("ETH", darajalar(), decide_entry_plan(2451.0, darajalar(), KONFIG))

    assert "🎯 Limit" in kutish
    assert "⚡ Market" in darhol


def test_limit_kartochkasida_entry_narxi_korsatiladi() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    assert "2,450" in kartochka, "Limit buyurtma Entry narxida qo'yiladi"


def test_market_kartochkasida_joriy_narx_korsatiladi() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2451.0, darajalar(), KONFIG))
    assert "2,451" in kartochka


def test_miqdor_pozitsiya_hisobidan_toladi() -> None:
    """"Miqdor" maydoni core/position_sizing natijasi bilan bog'lanadi."""
    sizer = PositionSizer(PositionSizingConfig())
    byudjet = sizer.budget_for(1200)
    taklif = sizer.suggest("ETH", darajalar(), byudjet)

    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG), taklif)
    assert "$" in kartochka.split("Miqdor:")[1].split("\n")[0]


def test_balans_kiritilmagan_bolsa_taklif_korsatiladi() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    assert "balansingizni kiriting" in kartochka


def test_stop_manfiy_foiz_bilan_korsatiladi() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    stop_qatori = next(q for q in kartochka.splitlines() if "Stop:" in q)
    assert "(-0." in stop_qatori


def test_arzon_coin_narxi_kesilmaydi() -> None:
    arzon = SignalLevels(entry=0.00042, stop=0.0004167, tp1=0.0004347, tp2=0.000441)
    kartochka = render_signal_card("PEPE", arzon, decide_entry_plan(0.00043, arzon, KONFIG))
    assert "0.0004" in kartochka, "arzon coin narxi nolga aylanmasligi kerak"


def test_narx_formatlash() -> None:
    assert format_price(67432.1234) == "67,432.12"
    assert format_price(2.5) == "2.5"
    assert format_price(0.00042) == "0.00042"


def test_foiz_formatlash() -> None:
    assert format_pct(3.0) == "+3.00%"
    assert format_pct(-0.8) == "-0.80%"
    assert format_pct(3.0, signed=False) == "3.00%"


def test_kartochkada_zona_qatori_korsatiladi() -> None:
    """3.1-band davomi: foydalanuvchi narx arzon yoki qimmat ekanini ko'radi."""
    from core.analysis.support_resistance import compute_range_position
    from core.domain.enums import ZoneKind
    from core.domain.models import SRZone

    support = SRZone(ZoneKind.SUPPORT, low=2400, high=2440, touches=3)
    resistance = SRZone(ZoneKind.RESISTANCE, low=2600, high=2640, touches=3)
    joy = compute_range_position(2460, support, resistance)

    kartochka = render_signal_card(
        "ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG), range_position=joy
    )
    assert "📍" in kartochka
    assert "Discount" in kartochka


def test_zona_qatori_ixtiyoriy() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    assert "📍" not in kartochka
