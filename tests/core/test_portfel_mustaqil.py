"""5-qism: portfel moduli TAHLIL MODULISIZ ishlashi kerak.

3-promptning yakuniy talabi:

    "signal modulidan SOXTA (mock) signal yuborib, bu modulning
     MUSTAQIL, to'g'ri ishlashini tekshirish — haqiqiy tahlil
     modulisiz ham ishlashi kerak, bu mustaqillikning isboti"

Shuning uchun bu faylda `core.analysis` dan HECH NARSA import
qilinmaydi. Signal — oddiy `dataclass`: symbol, entry, stop va TP
ro'yxati. Modul uni qayerdan kelganini bilmaydi va bilishi ham
shart emas.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from core.portfolio.capital_allocator import (
    band_qil,
    bolaklarni_yarat,
    bosat,
    joylashtir,
    umumiy_xavf_pct,
)
from core.portfolio.exit_manager import (
    chiqish_rejasi_qur,
    holat_boshla,
    natija_pct,
    stop_urildi,
    tp_bajarildi,
)
from core.portfolio.pnl_calculator import OchiqPozitsiya, YopilganQism, xulosa_qur
from core.portfolio.pnl_dashboard import dashboard_qur, matn

HOZIR = datetime(2026, 9, 4, 15, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class SoxtaSignal:
    """Tahlil modulidan KELMAGAN signal — qo'lda yozilgan."""

    signal_id: int
    symbol: str
    entry: float
    stop: float
    tplar: tuple[float, ...]

    @property
    def stop_masofa_pct(self) -> float:
        return (self.entry - self.stop) / self.entry * 100


# --------------------------------------------------------------------- #
#  Mustaqillikning MEXANIK isboti
# --------------------------------------------------------------------- #


def test_portfel_paketi_TAHLILGA_bogliq_emas() -> None:
    """Izohga emas, kodga qaraydi.

    `tests/test_arxitektura.py` portfelni 0-qavatga qo'ydi, ya'ni u
    hech qanday `core.*` paketga bog'lanmasligi kerak. Bu test o'sha
    qoidaning portfelga tegishli qismini ALOHIDA aytadi, chunki
    3-promptning asosiy sharti shu.
    """
    paket = Path(__file__).resolve().parents[2] / "core" / "portfolio"
    tashqi: set[str] = set()

    for fayl in sorted(paket.glob("*.py")):
        daraxt = ast.parse(fayl.read_text(encoding="utf-8"), filename=str(fayl))
        for tugun in ast.walk(daraxt):
            if isinstance(tugun, ast.ImportFrom):
                modul = tugun.module or ""
                if modul.startswith("core.") and not modul.startswith("core.portfolio"):
                    tashqi.add(f"{fayl.name}: {modul}")
            elif isinstance(tugun, ast.Import):
                for nom in tugun.names:
                    if nom.name.startswith("core.") and not nom.name.startswith(
                        "core.portfolio"
                    ):
                        tashqi.add(f"{fayl.name}: {nom.name}")

    assert not tashqi, (
        "Portfel moduli boshqa `core` paketiga bog'landi: " + ", ".join(sorted(tashqi))
    )


# --------------------------------------------------------------------- #
#  To'liq yo'l: soxta signal -> kapital -> chiqish -> PNL -> ekran
# --------------------------------------------------------------------- #


def test_soxta_signal_toliq_yoldan_otadi() -> None:
    """Signal keldi, TP lar olindi, ekranda to'g'ri raqam chiqdi."""
    signal = SoxtaSignal(1, "BTC", entry=100.0, stop=95.0, tplar=(110.0, 120.0))
    bolaklar = bolaklarni_yarat(900.0, 3)

    # 1) Kapital
    taqsimot = joylashtir(bolaklar, signal.stop_masofa_pct)
    assert taqsimot is not None
    assert taqsimot.bolak_raqami == 1
    assert taqsimot.toliq_bolak  # Stop 5% < chegara 10%
    assert taqsimot.miqdor_usd == pytest.approx(300.0)
    assert taqsimot.xavf_usd == pytest.approx(15.0)
    bolaklar = band_qil(bolaklar, taqsimot)

    # 2) Chiqish rejasi — ikkala TP ham olindi
    holat = holat_boshla(chiqish_rejasi_qur(signal.entry, signal.stop, list(signal.tplar)))
    holat = tp_bajarildi(holat)
    assert holat.xavfsizmi  # Stop breakeven ga ko'chdi
    holat = tp_bajarildi(holat)
    assert holat.yopilgan

    # (10% + 20%) / 2 = 15%
    natija = natija_pct(holat, signal.tplar[-1])
    assert natija == pytest.approx(15.0)

    # 3) Kapital bo'shadi
    bolaklar = bosat(bolaklar, taqsimot.bolak_raqami, taqsimot.miqdor_usd, taqsimot.xavf_usd)
    assert umumiy_xavf_pct(bolaklar) == 0.0
    assert all(not b.band for b in bolaklar)

    # 4) PNL — har bosqich alohida yozuv
    qismlar = [
        YopilganQism(
            signal_id=signal.signal_id,
            symbol=signal.symbol,
            yopilgan_vaqt=HOZIR - timedelta(days=kun),
            miqdor_usd=taqsimot.miqdor_usd * bosqich.ulush_pct / 100,
            natija_usd=taqsimot.miqdor_usd
            * bosqich.ulush_pct
            / 100
            * (bosqich.narx - signal.entry)
            / signal.entry,
            sabab=f"TP{bosqich.raqam}",
        )
        for kun, bosqich in zip((2, 0.2), holat.reja.bosqichlar, strict=True)
    ]
    xulosa = xulosa_qur(qismlar, [], balans_usd=900.0, hozir=HOZIR)

    # 300$ ning 15% i = 45$
    assert xulosa.davr("hafta").realized_usd == pytest.approx(45.0)
    assert xulosa.davr("hafta").savdo_soni == 1
    # TP2 bugun yopildi: 150$ x 20% = 30$
    assert xulosa.davr("bugun").realized_usd == pytest.approx(30.0)

    # 5) Ekran
    dashboard = dashboard_qur(xulosa, bolaklar)
    assert not dashboard.bosh
    assert dashboard.bosh_bolaklar == (1, 2, 3)
    assert "$45.00" in matn(dashboard)


def test_soxta_signal_stop_bilan_yopilsa_zarar_CHEGARADA() -> None:
    """Bo'lakning ichki chegarasi ishlayotganining isboti."""
    signal = SoxtaSignal(2, "ETH", entry=100.0, stop=80.0, tplar=(115.0,))
    bolaklar = bolaklarni_yarat(900.0, 3)

    # Stop 20% — chegaradan (10%) uzoq, ya'ni bo'lakning yarmi ishlatiladi.
    taqsimot = joylashtir(bolaklar, signal.stop_masofa_pct)
    assert taqsimot is not None
    assert not taqsimot.toliq_bolak
    assert taqsimot.miqdor_usd == pytest.approx(150.0)
    # 150$ x 20% = 30$ — bu bo'lakning (300$) AYNAN 10% i.
    assert taqsimot.xavf_usd == pytest.approx(30.0)

    bolaklar = band_qil(bolaklar, taqsimot)
    assert bolaklar[0].xavf_pct == pytest.approx(10.0)

    holat = stop_urildi(holat_boshla(chiqish_rejasi_qur(100.0, 80.0, [115.0])))
    assert natija_pct(holat, 80.0) == pytest.approx(-20.0)
    # Pozitsiyaning -20% i = 150$ x 20% = 30$, ya'ni ajratilgan xavf.
    assert taqsimot.miqdor_usd * 0.20 == pytest.approx(taqsimot.xavf_usd)


def test_uchta_signal_uchta_bolakni_egallaydi_tortinchisi_KUTADI() -> None:
    """Bo'lak qolmasa signal rad etilmaydi — kutadi (3-prompt, 1-qism)."""
    bolaklar = bolaklarni_yarat(900.0, 3)

    for kutilgan_raqam in (1, 2, 3):
        taqsimot = joylashtir(bolaklar, stop_masofa_pct=5.0)
        assert taqsimot is not None
        assert taqsimot.bolak_raqami == kutilgan_raqam
        bolaklar = band_qil(bolaklar, taqsimot)

    assert joylashtir(bolaklar, stop_masofa_pct=5.0) is None
    assert umumiy_xavf_pct(bolaklar) == pytest.approx(5.0)


def test_ochiq_savdo_ekranda_REALIZED_bilan_qoshilmaydi() -> None:
    """Signal hali yopilmagan — "foyda" deb ko'rsatilmaydi."""
    signal = SoxtaSignal(3, "SOL", entry=100.0, stop=95.0, tplar=(110.0, 120.0))
    bolaklar = bolaklarni_yarat(900.0, 3)
    taqsimot = joylashtir(bolaklar, signal.stop_masofa_pct)
    assert taqsimot is not None
    bolaklar = band_qil(bolaklar, taqsimot)

    xulosa = xulosa_qur(
        [],
        [OchiqPozitsiya(3, "SOL", 100.0, taqsimot.miqdor_usd, joriy_narx=105.0)],
        balans_usd=900.0,
        hozir=HOZIR,
    )
    dashboard = dashboard_qur(xulosa, bolaklar)
    chiqish = matn(dashboard)

    assert xulosa.davr("boshidan").realized_usd == 0.0
    assert dashboard.unrealized_usd == pytest.approx(15.0)
    assert "hali pul emas" in chiqish
    assert dashboard.band_bolaklar == (1,)
