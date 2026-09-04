"""4-qism: bot va veb-sayt uchun umumiy dashboard ma'lumoti.

BITTA MANBA, IKKI EKRAN. Bot ham, sayt ham AYNAN shu funksiyadan
o'qiydi. Ansiz ikkita hisob-kitob paydo bo'lardi va vaqt o'tib
ular bir-biridan farq qilib ketardi — foydalanuvchi botda bir
raqam, saytda boshqasini ko'rardi.

Bu fayl FAQAT tayyor raqamlarni matnga aylantiradi. Hisob
`pnl_calculator.py` da, kapital holati `capital_allocator.py`
da — bu yerda mantiq takrorlanmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.portfolio.capital_allocator import Bolak, umumiy_xavf_pct
from core.portfolio.pnl_calculator import PnlXulosasi

#: Davr kaliti -> foydalanuvchi ko'radigan nom.
DAVR_NOMLARI = {
    "bugun": "Bugungi",
    "hafta": "7 kunlik",
    "oy": "30 kunlik",
    "boshidan": "Boshidan beri",
}


@dataclass(frozen=True, slots=True)
class DashboardQatori:
    """Bitta qator: nom va ikki raqam."""

    nom: str
    usd: float
    pct: float

    @property
    def belgi(self) -> str:
        if self.usd > 0:
            return "🟢"
        return "🔴" if self.usd < 0 else "⚪"

    def matn(self) -> str:
        ishora = "+" if self.usd >= 0 else "−"
        return (
            f"{self.belgi} {self.nom}: {ishora}${abs(self.usd):,.2f} "
            f"({ishora}{abs(self.pct):.1f}%)"
        )


@dataclass(frozen=True, slots=True)
class Dashboard:
    """Bot va sayt uchun tayyor manzara."""

    qatorlar: tuple[DashboardQatori, ...]
    unrealized_usd: float
    ochiq_soni: int
    band_bolaklar: tuple[int, ...]
    bosh_bolaklar: tuple[int, ...]
    xavf_pct: float
    #: Hech qanday savdo bo'lmaganmi. Shunda ekran RAQAM emas,
    #: rostini aytadigan matn ko'rsatishi kerak.
    bosh: bool


def dashboard_qur(xulosa: PnlXulosasi, bolaklar: list[Bolak]) -> Dashboard:
    """PNL va kapital holatidan bitta manzara yasaydi."""
    qatorlar = tuple(
        DashboardQatori(
            nom=DAVR_NOMLARI.get(d.nom, d.nom),
            usd=d.realized_usd,
            pct=d.realized_pct,
        )
        for d in xulosa.davrlar
    )
    boshidan = xulosa.davr("boshidan")
    savdo_bormi = bool(boshidan and boshidan.savdo_soni)

    return Dashboard(
        qatorlar=qatorlar,
        unrealized_usd=xulosa.unrealized_usd,
        ochiq_soni=xulosa.ochiq_soni,
        band_bolaklar=tuple(b.raqam for b in bolaklar if b.band),
        bosh_bolaklar=tuple(b.raqam for b in bolaklar if not b.band),
        xavf_pct=umumiy_xavf_pct(bolaklar),
        bosh=not savdo_bormi and xulosa.ochiq_soni == 0,
    )


def matn(dashboard: Dashboard) -> str:
    """Telegram uchun tayyor matn.

    Sayt shu MA'LUMOTNI oladi, lekin o'z ko'rinishida chizadi —
    HTML matn bu yerdan yuborilmaydi.
    """
    if dashboard.bosh:
        return (
            "📊 <b>Mening natijam</b>\n\n"
            "Hozircha yopilgan savdo yo'q.\n"
            "Birinchi signal yopilgach raqamlar shu yerda paydo bo'ladi."
        )

    qatorlar = ["📊 <b>Mening natijam</b>", ""]
    qatorlar.extend(q.matn() for q in dashboard.qatorlar)

    if dashboard.ochiq_soni:
        ishora = "+" if dashboard.unrealized_usd >= 0 else "−"
        qatorlar.append("")
        qatorlar.append(
            f"📈 Ochiq savdolarda: {ishora}${abs(dashboard.unrealized_usd):,.2f} "
            "<i>(hali pul emas)</i>"
        )

    qatorlar.append("")
    if dashboard.band_bolaklar:
        band = ", ".join(str(r) for r in dashboard.band_bolaklar)
        qatorlar.append(f"🔒 Band: {dashboard.ochiq_soni} ta savdo (bo'lak {band})")
    if dashboard.bosh_bolaklar:
        qatorlar.append(f"🟩 Bo'sh: {len(dashboard.bosh_bolaklar)} ta bo'lak")
    qatorlar.append(f"⚠️ Xavf ostida: balansning {dashboard.xavf_pct:.1f}% i")

    return "\n".join(qatorlar)
