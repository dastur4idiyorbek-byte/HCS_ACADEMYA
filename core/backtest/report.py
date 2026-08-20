"""Backtest natijasini o'qiladigan hisobotga aylantiradi.

MUHIM: hisobot hech qachon "X% aniqlik" da'vosini qilmaydi (3.6-band).
U faqat o'lchangan raqamlarni ko'rsatadi va namuna kichik bo'lsa buni
OCHIQ aytadi — 3.8-banddagi halollik chegarasi bilan bir xil tamoyil.
"""

from __future__ import annotations

from core.backtest.engine import BacktestResult

#: Xulosa chiqarish uchun minimal savdo soni. Undan kam bo'lsa raqamlar
#: shovqin — 10 ta savdodan "win-rate 70%" degan xulosa chiqarilmaydi.
MIN_TRADES_FOR_CONCLUSION = 30


def render(result: BacktestResult) -> str:
    """Bitta backtest natijasi."""
    qatorlar = [
        f"📉 Backtest: {result.label}",
        f"   Qadamlar: {result.steps:,}  |  Signal: {result.signals_emitted}  "
        f"|  Yopilgan savdo: {result.closed}",
    ]

    if not result.trades:
        qatorlar.append("")
        qatorlar.append("   Savdo bo'lmadi. Rad etish sabablari:")
        for bosqich, soni in result.top_rejections():
            qatorlar.append(f"     {soni:>6} × {bosqich}")
        qatorlar += _near_miss_qatorlari(result)
        return "\n".join(qatorlar)

    qatorlar += [
        "",
        f"   Win-rate:        {result.win_rate:.1%}",
        f"   TP2 gacha:       {result.tp2_rate:.1%}",
        f"   O'rtacha natija: {result.average_result_pct:+.2f}%",
        f"   Umumiy natija:   {result.total_return_pct:+.1f}%",
        f"   Maks. pasayish:  {result.max_drawdown_pct:.1f}%",
        f"   Ketma-ket zarar: {result.max_consecutive_losses} ta",
        f"   O'rtacha ushlash: {result.average_holding_hours:.1f} soat",
    ]

    if result.closed < MIN_TRADES_FOR_CONCLUSION:
        qatorlar += [
            "",
            f"   ⚠️ Namuna kichik ({result.closed} savdo, kamida "
            f"{MIN_TRADES_FOR_CONCLUSION} kerak). Raqamlar yo'nalish beradi, "
            "xulosa emas.",
        ]

    if result.rejections:
        qatorlar += ["", "   Eng ko'p rad etish sabablari:"]
        for bosqich, soni in result.top_rejections():
            qatorlar.append(f"     {soni:>6} × {bosqich}")
    qatorlar += _near_miss_qatorlari(result)

    return "\n".join(qatorlar)


def _near_miss_qatorlari(result: BacktestResult) -> list[str]:
    """Chegaraga yetmagan nomzodlar haqida — chegarani sozlash uchun.

    Nol savdo chiqqanda bu qatorlar hal qiluvchi: ular "zanjir umuman
    nomzod yaratmadi"ni "nomzod yaratdi, lekin ball yetmadi"dan ajratadi.
    """
    eng_yuqori = result.best_near_miss
    if eng_yuqori is None:
        return []
    return [
        "",
        f"   Chegaraga yetmagan nomzodlar: {len(result.near_miss_scores)} ta",
        f"     eng yuqori ball: {eng_yuqori:.1f}  |  "
        f"o'rtacha: {result.average_near_miss:.1f}",
    ]


def compare(results: list[BacktestResult]) -> str:
    """Bir nechta konfiguratsiyani yonma-yon taqqoslaydi.

    Backtestning ASOSIY maqsadi shu: "qat'iy EMA talabimi yoki yumshoq",
    "nechta indikator tasdig'i kerak" kabi savollarga taxmin bilan emas,
    RAQAM bilan javob berish.
    """
    if not results:
        return "Taqqoslash uchun natija yo'q."

    sarlavha = (
        f"{'konfiguratsiya':<26} {'signal':>7} {'savdo':>6} {'win':>7} "
        f"{'o‘rt.%':>8} {'jami%':>8} {'pasayish':>9}"
    )
    qatorlar = [sarlavha, "-" * len(sarlavha)]

    for natija in results:
        win = f"{natija.win_rate:.0%}" if natija.win_rate is not None else "—"
        ortacha = (
            f"{natija.average_result_pct:+.2f}"
            if natija.average_result_pct is not None
            else "—"
        )
        qatorlar.append(
            f"{natija.label:<26} {natija.signals_emitted:>7} {natija.closed:>6} "
            f"{win:>7} {ortacha:>8} {natija.total_return_pct:>+8.1f} "
            f"{natija.max_drawdown_pct:>8.1f}%"
        )

    yetarli = [r for r in results if r.closed >= MIN_TRADES_FOR_CONCLUSION]
    qatorlar.append("")

    if not yetarli:
        qatorlar.append(
            f"⚠️ Hech bir konfiguratsiyada {MIN_TRADES_FOR_CONCLUSION} ta savdo "
            "yig'ilmadi — taqqoslash xulosa uchun yetarli emas."
        )
        return "\n".join(qatorlar)

    eng_yaxshi = max(yetarli, key=lambda r: r.total_return_pct)
    qatorlar.append(
        f"💡 Umumiy natija bo'yicha eng yaxshisi: «{eng_yaxshi.label}» "
        f"({eng_yaxshi.total_return_pct:+.1f}%, pasayish {eng_yaxshi.max_drawdown_pct:.1f}%)"
    )
    qatorlar.append(
        "   Bu — o'lchov, kafolat emas. Qaror qabul qilishdan oldin pasayish "
        "chuqurligini ham hisobga oling."
    )
    return "\n".join(qatorlar)
