"""5-bo'lim: pozitsiya hajmi, kunlik byudjet va agregat sig'im.

Bu fayldagi eng muhim test — `test_barcha_signallar_stop_yesa_limitdan_oshmaydi`.
Spetsifikatsiyaning 5.1.1-bandida u sinov sharti sifatida ochiq belgilangan:
"qaysi usul tanlanmasin, barcha faol signallar bir vaqtda Stop yesa, jami
zarar kunlik limit foizidan oshmasligi KERAK".
"""

from __future__ import annotations

import pytest

from core.config.schema import AggregateConfig, PositionSizingConfig, RiskTier
from core.domain.models import SignalLevels, signal_levels
from core.position_sizing import (
    DailyRiskBudget,
    PositionSizer,
    compute_aggregate_capacity,
    resolve_daily_risk_pct,
)

POGONALAR = [
    RiskTier(max_balance=1000, daily_risk_pct=3.0),
    RiskTier(max_balance=10000, daily_risk_pct=2.0),
    RiskTier(max_balance=None, daily_risk_pct=1.5),
]


def darajalar(entry: float = 100.0, stop_pct: float = 1.0) -> SignalLevels:
    stop = entry * (1 - stop_pct / 100)
    return signal_levels(entry=entry, stop=stop, tp1=entry * 1.03, tp2=entry * 1.05)


# --------------------------------------------------------------------------- #
#  5.1 — pog'onali xavf foizi
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("balans", "kutilgan"),
    [(0, 3.0), (500, 3.0), (1000, 3.0), (1000.01, 2.0), (5000, 2.0), (10000, 2.0), (50000, 1.5)],
)
def test_pogonali_xavf_foizi(balans: float, kutilgan: float) -> None:
    assert resolve_daily_risk_pct(balans, POGONALAR) == kutilgan


def test_manfiy_balans_rad_etiladi() -> None:
    with pytest.raises(ValueError, match="manfiy"):
        resolve_daily_risk_pct(-1, POGONALAR)


# --------------------------------------------------------------------------- #
#  5.1.1 — MAJBURIY INVARIANT
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("usul", ["sequential_decay", "equal_split"])
@pytest.mark.parametrize("signallar_soni", [1, 2, 3, 5, 10])
@pytest.mark.parametrize("balans", [100, 500, 5000, 50000])
@pytest.mark.parametrize("stop_pct", [0.3, 0.8, 1.0])
def test_barcha_signallar_stop_yesa_limitdan_oshmaydi(
    usul: str, signallar_soni: int, balans: float, stop_pct: float
) -> None:
    """5.1.1-banddagi tekshirish sharti.

    Barcha faol signallar bir vaqtda Stop yesa, jami zarar kunlik limit
    foizidan oshmasligi KERAK — usul, signal soni, balans va Stop masofasidan
    qat'i nazar.
    """
    config = PositionSizingConfig(risk_tiers=POGONALAR, allocation_method=usul)
    sizer = PositionSizer(config)
    budget = sizer.budget_for(balans)
    levels = darajalar(stop_pct=stop_pct)

    jami_zarar = 0.0
    for _ in range(signallar_soni):
        taklif = sizer.suggest("TEST", levels, budget, commit=True)
        # Stop yeganda haqiqiy zarar = pozitsiya hajmi × Stop masofasi
        jami_zarar += taklif.position_size_usd * stop_pct / 100

    limit = balans * budget.daily_risk_pct / 100
    assert jami_zarar <= limit + 1e-9, (
        f"{usul}: {signallar_soni} ta signal, jami zarar ${jami_zarar:.4f} "
        f"kunlik limit ${limit:.4f} dan oshdi"
    )


@pytest.mark.parametrize("usul", ["sequential_decay", "equal_split"])
def test_ajratilgan_xavf_byudjetdan_oshmaydi(usul: str) -> None:
    config = PositionSizingConfig(risk_tiers=POGONALAR, allocation_method=usul)
    sizer = PositionSizer(config)
    budget = sizer.budget_for(2000)
    levels = darajalar()

    for _ in range(20):
        sizer.suggest("TEST", levels, budget, commit=True)

    assert budget.allocated <= budget.total_usd + 1e-9


# --------------------------------------------------------------------------- #
#  SPOT cheklovi — leverage yo'q
# --------------------------------------------------------------------------- #


def test_pozitsiyalar_yigindisi_balansdan_oshmaydi() -> None:
    """Spot savdo: bir vaqtda ochiq pozitsiyalar balansdan katta bo'la olmaydi."""
    config = PositionSizingConfig(risk_tiers=POGONALAR)
    sizer = PositionSizer(config)
    budget = sizer.budget_for(500)
    levels = darajalar(stop_pct=0.5)

    jami_hajm = sum(
        sizer.suggest("TEST", levels, budget, commit=True).position_size_usd for _ in range(15)
    )
    assert jami_hajm <= budget.balance + 1e-9


def test_kapital_cheklanganda_izoh_beriladi() -> None:
    """Kesish jim bo'lmasligi kerak — foydalanuvchi sababini bilishi shart."""
    config = PositionSizingConfig(risk_tiers=POGONALAR)
    sizer = PositionSizer(config)
    budget = sizer.budget_for(500)

    taklif = sizer.suggest("TEST", darajalar(stop_pct=0.5), budget, commit=True)
    assert taklif.note is not None
    assert "leverage" in taklif.note.lower()


def test_bir_nechta_signal_birga_yashay_oladi() -> None:
    """Birinchi signal butun kapitalni band qilib qo'ymasligi kerak."""
    config = PositionSizingConfig(risk_tiers=POGONALAR)
    sizer = PositionSizer(config)
    budget = sizer.budget_for(500)
    levels = darajalar(stop_pct=0.8)

    hajmlar = [
        sizer.suggest("TEST", levels, budget, commit=True).position_size_usd for _ in range(3)
    ]
    assert all(h > 0 for h in hajmlar), f"barcha signal hajmi musbat bo'lishi kerak: {hajmlar}"
    assert hajmlar[0] > hajmlar[1] > hajmlar[2], "ketma-ket kamayib borishi kerak"


# --------------------------------------------------------------------------- #
#  Byudjet holati
# --------------------------------------------------------------------------- #


def test_byudjet_tugaganda_taklif_berilmaydi() -> None:
    config = PositionSizingConfig(risk_tiers=POGONALAR)
    sizer = PositionSizer(config)
    budget = DailyRiskBudget(balance=1000, daily_risk_pct=3.0)
    budget.allocate(budget.total_usd)  # byudjetni to'liq band qilamiz

    taklif = sizer.suggest("TEST", darajalar(), budget)
    assert taklif.position_size_usd == 0
    assert not taklif.within_daily_limit
    assert "chegarangiz tugadi" in (taklif.note or "")


def test_commit_false_byudjetga_tegmaydi() -> None:
    """Faqat ko'rsatish uchun hisob byudjetni band qilmasligi kerak."""
    config = PositionSizingConfig(risk_tiers=POGONALAR)
    sizer = PositionSizer(config)
    budget = sizer.budget_for(1000)

    sizer.suggest("TEST", darajalar(), budget, commit=False)
    assert budget.allocated == 0
    assert budget.committed_capital == 0


def test_tp_ga_borganda_limit_boshaydi() -> None:
    """5.2-band: signal TP'ga borsa foydalanuvchi limiti bo'shaydi."""
    budget = DailyRiskBudget(balance=1000, daily_risk_pct=3.0)
    ajratilgan = budget.allocate(10.0)
    budget.commit_capital(400.0)

    budget.release(ajratilgan)
    budget.release_capital(400.0)

    assert budget.allocated == 0
    assert budget.committed_capital == 0
    assert budget.remaining_usd == pytest.approx(30.0)


def test_zarar_qayd_etiladi() -> None:
    budget = DailyRiskBudget(balance=1000, daily_risk_pct=3.0)
    budget.register_loss(15.0)
    assert budget.realized_loss_pct == pytest.approx(1.5)


# --------------------------------------------------------------------------- #
#  5.2 — agregat sig'im
# --------------------------------------------------------------------------- #


def test_agregat_sigim_spetsifikatsiya_misoli() -> None:
    """5.2-banddagi aniq misol: 10 foydalanuvchi, 7 tasining limiti to'lgan."""
    config = AggregateConfig(capacity_used_threshold=0.8)
    band = [DailyRiskBudget(balance=1000, daily_risk_pct=3.0) for _ in range(7)]
    for budget in band:
        budget.allocate(budget.total_usd * 0.9)  # 90% band
    bosh = [DailyRiskBudget(balance=1000, daily_risk_pct=3.0) for _ in range(3)]

    sigim = compute_aggregate_capacity([*band, *bosh], config)

    assert sigim.active_users == 10
    assert sigim.users_with_headroom == 3
    assert sigim.headroom_ratio == pytest.approx(0.3)


def test_foydalanuvchi_yoq_bolsa_sigim_toliq() -> None:
    """Fail-safe: foydalanuvchi yo'qligi tizimni o'zini cheklashiga sabab bo'lmasin."""
    sigim = compute_aggregate_capacity([], AggregateConfig())
    assert sigim.headroom_ratio == 1.0
    assert sigim.budget_free_ratio == 1.0


def test_sigim_izohi_admin_uchun_oqiladi() -> None:
    budgets = [DailyRiskBudget(balance=1000, daily_risk_pct=3.0) for _ in range(4)]
    budgets[0].allocate(budgets[0].total_usd)
    izoh = compute_aggregate_capacity(budgets, AggregateConfig()).describe()
    assert "3/4" in izoh


# --------------------------------------------------------------------------- #
#  3.9 — Strategiya byudjeti umumiy limit ichida
# --------------------------------------------------------------------------- #


def test_strategiya_byudjeti_oz_ulushidan_oshmaydi() -> None:
    umumiy = DailyRiskBudget(balance=1000, daily_risk_pct=3.0)   # $30
    skalp = umumiy.sub_budget(30.0)                              # $9

    assert skalp.total_usd == pytest.approx(9.0)
    assert skalp.allocate(20.0) == pytest.approx(9.0), "ulushdan oshmaydi"
    assert skalp.is_exhausted


def test_strategiya_byudjeti_umumiy_limitga_boysunadi() -> None:
    """3.9-band: ikkalasi birga umumiy kunlik limitdan oshmasligi KERAK."""
    umumiy = DailyRiskBudget(balance=1000, daily_risk_pct=3.0)   # $30
    skalp = umumiy.sub_budget(30.0)                              # $9

    umumiy.allocate(28.0)  # asosiy strategiya deyarli hammasini oldi
    assert skalp.remaining_usd == pytest.approx(2.0), (
        "o'z ulushi qolsa ham, umumiy qoldiqdan oshmaydi"
    )
    assert skalp.allocate(9.0) == pytest.approx(2.0)
    assert umumiy.allocated <= umumiy.total_usd + 1e-9


def test_strategiya_byudjeti_boshatiladi() -> None:
    umumiy = DailyRiskBudget(balance=1000, daily_risk_pct=3.0)
    skalp = umumiy.sub_budget(30.0)

    berildi = skalp.allocate(5.0)
    skalp.release(berildi)

    assert skalp.allocated == 0
    assert umumiy.allocated == 0, "umumiy byudjet ham bo'shashi kerak"


@pytest.mark.parametrize("yomon", [0, -10, 150])
def test_notogri_ulush_rad_etiladi(yomon: float) -> None:
    umumiy = DailyRiskBudget(balance=1000, daily_risk_pct=3.0)
    with pytest.raises(ValueError, match="Ulush"):
        umumiy.sub_budget(yomon)
