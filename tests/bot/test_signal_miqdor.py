"""5.1-band: signal kartochkasida MIQDOR ko'rsatilishi kerak.

Nima uchun alohida test: pozitsiya hajmi moduli 11-bosqichda qurilgan,
signal yuborish 15-bosqichda ulangan — lekin ikkalasi BIR-BIRIGA
ulanmagandi. `render_signal_card` `suggestion` ni qabul qilardi, hech kim
uni uzatmasdi. Natijada karta doim "balansingizni kiriting" derdi,
foydalanuvchi balansini kiritgan bo'lsa ham.

Bunday xato jimgina yashaydi: kod yiqilmaydi, test ham yiqilmaydi —
faqat va'da bajarilmaydi.
"""

from __future__ import annotations

import pytest

from bot.formatting import render_signal_card
from bot.handlers.signals import suggest_size
from core.analysis import decide_entry_plan
from core.config import load_config
from core.domain.models import signal_levels

DARAJALAR = signal_levels(entry=100.0, stop=99.2, tp1=103.5, tp2=105.0)


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


@pytest.fixture
def reja(config):  # noqa: ANN001, ANN201
    return decide_entry_plan(100.0, DARAJALAR, config.analysis.entry_order)


def test_balans_kiritilgan_bolsa_miqdor_korsatiladi(config, reja) -> None:  # noqa: ANN001
    """ENG MUHIM: 5-bandning asosiy va'dasi."""
    tavsiya = suggest_size("BTC", DARAJALAR, 1000.0, config)

    assert tavsiya is not None, "balans bor — tavsiya hisoblanishi kerak"
    assert tavsiya.position_size_usd > 0

    karta = render_signal_card("BTC", DARAJALAR, reja, suggestion=tavsiya)

    assert "$" in karta
    assert "balansingizni kiriting" not in karta


def test_balans_yoq_bolsa_taklif_korsatiladi(config, reja) -> None:  # noqa: ANN001
    """Balanssiz signal baribir yuboriladi, faqat miqdor o'rniga taklif."""
    assert suggest_size("BTC", DARAJALAR, None, config) is None

    karta = render_signal_card("BTC", DARAJALAR, reja, suggestion=None)

    assert "balansingizni kiriting" in karta


@pytest.mark.parametrize("balans", [0.0, -100.0])
def test_notogri_balans_tavsiya_bermaydi(config, balans) -> None:  # noqa: ANN001
    assert suggest_size("BTC", DARAJALAR, balans, config) is None


def test_katta_balans_katta_pozitsiya_beradi(config) -> None:  # noqa: ANN001
    """Miqdor balansga mutanosib o'sishi kerak."""
    kichik = suggest_size("BTC", DARAJALAR, 500.0, config)
    katta = suggest_size("BTC", DARAJALAR, 5000.0, config)

    assert katta.position_size_usd > kichik.position_size_usd


def test_xavf_kunlik_limitdan_oshmaydi(config) -> None:  # noqa: ANN001
    """5.1.1-band: bitta signal kunlik xavf limitidan oshmasligi kerak."""
    balans = 1000.0
    tavsiya = suggest_size("BTC", DARAJALAR, balans, config)

    from core.position_sizing import PositionSizer

    byudjet = PositionSizer(config.position_sizing).budget_for(balans)
    kunlik_limit = balans * byudjet.daily_risk_pct / 100

    assert tavsiya.risk_amount_usd <= kunlik_limit + 1e-9, (
        f"bitta signal xavfi {tavsiya.risk_amount_usd:.2f}$ > "
        f"kunlik limit {kunlik_limit:.2f}$"
    )


def test_tavsiya_byudjetni_band_qilmaydi(config) -> None:  # noqa: ANN001
    """5.4-band: byudjet faqat «Men kirdim» bosilganda ajratiladi.

    Ko'rsatish uchun hisob byudjetga tegmasligi kerak — aks holda signal
    ko'rgan har bir foydalanuvchining limiti bekorga yeb qo'yilardi.
    """
    from core.position_sizing import PositionSizer

    sizer = PositionSizer(config.position_sizing)
    byudjet = sizer.budget_for(1000.0)
    oldin = byudjet.remaining_usd

    sizer.suggest("BTC", DARAJALAR, byudjet, commit=False)

    assert byudjet.remaining_usd == oldin
