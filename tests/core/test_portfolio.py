"""5.4-band: shaxsiy portfel va foyda/zarar hisobi.

Eng muhim qism — QISMLI YOPISH. TP1 olinib, keyin narx Stop'ga qaytsa,
bu foydali bo'lishi mumkin. Buni hisobga olmasak, tizim uni sof zarar deb
ko'rsatardi va foydalanuvchi raqamlarga ishonmay qolardi.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from core.config.schema import PortfolioConfig
from core.domain.portfolio import PositionSnapshot
from core.services import blended_result_pct, compute_outcome, summarize

KONFIG = PortfolioConfig(tp1_close_pct=50.0)
BUGUN = date(2026, 8, 19)


# --------------------------------------------------------------------------- #
#  Qismli yopish — 5.4-banddagi asosiy mexanizm
# --------------------------------------------------------------------------- #


def test_tp1_dan_keyin_stop_foyda_berishi_mumkin() -> None:
    """$100, entry 100, TP1 103 (50% yopildi), Stop 99.

    50% × +3% + 50% × −1% = +1%
    Qismli yopish hisobga olinmasa, natija −1% ko'rinardi.
    """
    natija = compute_outcome(100, entry_price=100, exit_price=99, config=KONFIG, tp1_price=103)

    assert natija.pnl_pct == pytest.approx(1.0)
    assert natija.pnl_usd == pytest.approx(1.0)
    assert natija.is_profit
    assert natija.partial_close_pct == 50.0


def test_tp1_ga_yetmasdan_stop_sof_zarar() -> None:
    natija = compute_outcome(100, entry_price=100, exit_price=99, config=KONFIG)

    assert natija.pnl_pct == pytest.approx(-1.0)
    assert not natija.is_profit
    assert natija.partial_exit_price is None


def test_tp2_gacha_toliq_foyda() -> None:
    """50% TP1 da (+3%), 50% TP2 da (+5%) = +4%."""
    natija = compute_outcome(100, entry_price=100, exit_price=105, config=KONFIG, tp1_price=103)
    assert natija.pnl_pct == pytest.approx(4.0)


def test_qismli_ulush_sozlanadi() -> None:
    """TP1 da ko'proq yopilsa, keyingi Stop kamroq ta'sir qiladi."""
    kop = PortfolioConfig(tp1_close_pct=80.0)
    kam = PortfolioConfig(tp1_close_pct=20.0)

    kop_natija = compute_outcome(100, 100, 99, kop, tp1_price=103)
    kam_natija = compute_outcome(100, 100, 99, kam, tp1_price=103)

    assert kop_natija.pnl_pct > kam_natija.pnl_pct


def test_miqdor_natijaga_proporsional() -> None:
    kichik = compute_outcome(100, 100, 105, KONFIG)
    katta = compute_outcome(1000, 100, 105, KONFIG)

    assert katta.pnl_usd == pytest.approx(kichik.pnl_usd * 10)
    assert katta.pnl_pct == pytest.approx(kichik.pnl_pct), "foiz miqdorga bog'liq emas"


@pytest.mark.parametrize(
    ("miqdor", "entry"),
    [(0, 100), (-50, 100), (100, 0), (100, -5)],
)
def test_notogri_qiymatlar_rad_etiladi(miqdor: float, entry: float) -> None:
    with pytest.raises(ValueError):
        compute_outcome(miqdor, entry, 105, KONFIG)


def test_arzon_coinlarda_ham_togri_ishlaydi() -> None:
    natija = compute_outcome(
        amount_usd=250, entry_price=0.00042, exit_price=0.000441, config=KONFIG
    )
    assert natija.pnl_pct == pytest.approx(5.0)
    assert natija.pnl_usd == pytest.approx(12.5)


# --------------------------------------------------------------------------- #
#  Portfel xulosasi
# --------------------------------------------------------------------------- #


def pozitsiya(
    symbol: str = "BTC",
    amount: float = 100.0,
    pnl_pct: float | None = None,
    pnl_usd: float | None = None,
) -> PositionSnapshot:
    yopilgan = pnl_pct is not None
    return PositionSnapshot(
        symbol=symbol,
        amount_usd=amount,
        entry_price=100.0,
        trade_date=BUGUN,
        closed_at=datetime(2026, 8, 19, tzinfo=UTC) if yopilgan else None,
        pnl_usd=pnl_usd,
        pnl_pct=pnl_pct,
    )


def test_portfel_xulosasi() -> None:
    xulosa = summarize(
        [
            pozitsiya("BTC", 100, pnl_pct=5.0, pnl_usd=5.0),
            pozitsiya("ETH", 200, pnl_pct=-1.0, pnl_usd=-2.0),
            pozitsiya("SOL", 150, pnl_pct=3.0, pnl_usd=4.5),
            pozitsiya("ADA", 50),  # ochiq
        ]
    )

    assert xulosa.total_positions == 4
    assert xulosa.open_positions == 1
    assert xulosa.closed_positions == 3
    assert xulosa.winning == 2
    assert xulosa.losing == 1
    assert xulosa.win_rate == pytest.approx(2 / 3)
    assert xulosa.realized_pnl_usd == pytest.approx(7.5)


def test_ochiq_pozitsiya_natijaga_kirmaydi() -> None:
    """Hali yopilmagan pozitsiya foyda/zararga qo'shilmasligi kerak."""
    xulosa = summarize([pozitsiya("BTC", 100), pozitsiya("ETH", 200)])

    assert xulosa.closed_positions == 0
    assert xulosa.realized_pnl_usd == 0
    assert xulosa.win_rate is None
    assert xulosa.realized_pnl_pct is None


def test_eng_yaxshi_va_eng_yomon() -> None:
    xulosa = summarize(
        [
            pozitsiya("BTC", 100, pnl_pct=5.0, pnl_usd=5.0),
            pozitsiya("ETH", 100, pnl_pct=-2.0, pnl_usd=-2.0),
            pozitsiya("SOL", 100, pnl_pct=1.0, pnl_usd=1.0),
        ]
    )
    assert xulosa.best_pnl_pct == 5.0
    assert xulosa.worst_pnl_pct == -2.0


def test_umumiy_foiz_qoyilgan_pulga_nisbatan() -> None:
    xulosa = summarize(
        [
            pozitsiya("BTC", 100, pnl_pct=10.0, pnl_usd=10.0),
            pozitsiya("ETH", 300, pnl_pct=-2.0, pnl_usd=-6.0),
        ]
    )
    assert xulosa.total_invested_usd == 400
    assert xulosa.realized_pnl_pct == pytest.approx(1.0)


def test_bosh_portfel_xato_bermaydi() -> None:
    xulosa = summarize([])
    assert xulosa.total_positions == 0
    assert xulosa.win_rate is None


# --------------------------------------------------------------------------- #
#  Signalning O'Z natijasi ham qismli yopishni hisobga oladi
# --------------------------------------------------------------------------- #


def test_blended_natija_tp1_ulushini_hisobga_oladi() -> None:
    """entry 100, TP1 103 (50% sotildi), yakuniy chiqish 100 (breakeven).

    To'g'ri javob +1.5%: yarmi +3% bilan sotilgan, yarmi nolda chiqqan.
    Ilgari signalning natijasi "0%" deb yozilardi va TP1 dagi foyda
    statistikadan butunlay yo'qolardi.
    """
    assert blended_result_pct(100.0, 100.0, 103.0, 50.0) == pytest.approx(1.5)


def test_blended_natija_tp2_da_ham_toliq_emas() -> None:
    """TP2 da ham butun pozitsiya TP2 narxida sotilmaydi — yarmi TP1 da
    ketgan. Aks holda natija haqiqiydan yuqori ko'rinardi."""
    # entry 100, TP1 103, TP2 105 -> 50%×3 + 50%×5 = 4.0
    assert blended_result_pct(100.0, 105.0, 103.0, 50.0) == pytest.approx(4.0)


def test_tp1_ga_yetilmagan_bolsa_oddiy_hisob() -> None:
    assert blended_result_pct(100.0, 99.0, None, 50.0) == pytest.approx(-1.0)


def test_ulush_100_bolsa_hammasi_tp1_da() -> None:
    assert blended_result_pct(100.0, 90.0, 103.0, 100.0) == pytest.approx(3.0)
