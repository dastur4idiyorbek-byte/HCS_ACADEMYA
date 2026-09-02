"""3.8-band: haftalik "O'z-o'zini tekshirish hisoboti" (faqat admin uchun).

MUHIM TAMOYIL: xulosalar AVTOMATIK O'ZGARTIRISH QILMAYDI. Tizim o'z
sozlamalarini o'zi o'zgartirsa, xato naqsh butun strategiyani buzishi
mumkin va buni hech kim sezmasdan qolardi.

Shuning uchun hisobot faqat ADMINGA ANIQ TAVSIYA beradi. Qaror — insonniki.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.analysis.postmortem.outcome import ClosedSignal, Outcome
from core.analysis.postmortem.patterns import Pattern, find_patterns
from core.config.schema import PostmortemConfig
from core.domain.models import PeriodStats


@dataclass(frozen=True, slots=True)
class SelfAuditReport:
    """Haftalik hisobot."""

    generated_at: datetime
    period_days: int
    stats: PeriodStats
    patterns: list[Pattern]
    sample_warning: str | None

    @property
    def has_findings(self) -> bool:
        return bool(self.patterns)


def compute_stats(signals: list[ClosedSignal]) -> PeriodStats:
    """Davr raqamlarini hisoblaydi."""
    ballar = [s.score for s in signals if s.score is not None]
    vaqtlar = [s.holding_hours for s in signals if s.holding_hours is not None]

    return PeriodStats(
        total=len(signals),
        tp2=sum(1 for s in signals if s.outcome is Outcome.TP2),
        tp1_then_stop=sum(1 for s in signals if s.outcome is Outcome.TP1_THEN_STOP),
        stop=sum(1 for s in signals if s.outcome is Outcome.STOP),
        cancelled=sum(1 for s in signals if s.outcome is Outcome.CANCELLED),
        false_signals=sum(1 for s in signals if s.is_false_signal),
        average_score=sum(ballar) / len(ballar) if ballar else None,
        average_holding_hours=sum(vaqtlar) / len(vaqtlar) if vaqtlar else None,
    )


def build_report(
    signals: list[ClosedSignal],
    config: PostmortemConfig,
    now: datetime,
) -> SelfAuditReport:
    """Hisobotni quradi.

    Namuna kichik bo'lsa, naqsh e'lon qilinmaydi va bu OCHIQ aytiladi —
    "naqsh topilmadi" bilan "ma'lumot yetarli emas" bir xil narsa emas.
    """
    statistika = compute_stats(signals)
    naqshlar = find_patterns(signals, config)

    ogohlantirish = None
    if statistika.traded < config.min_sample_size:
        ogohlantirish = (
            f"Namuna kichik ({statistika.traded} ta savdo, kamida "
            f"{config.min_sample_size} kerak) — naqsh izlanmadi. Bu "
            "\"muammo yo'q\" degani EMAS, shunchaki ma'lumot yetarli emas."
        )

    return SelfAuditReport(
        generated_at=now,
        period_days=config.lookback_days,
        stats=statistika,
        patterns=naqshlar,
        sample_warning=ogohlantirish,
    )


def render_report(report: SelfAuditReport) -> str:
    """Hisobotni admin uchun o'qiladigan matnga aylantiradi."""
    s = report.stats
    qatorlar = [
        f"🧾 O'z-o'zini tekshirish hisoboti ({report.period_days} kun)",
        f"   {report.generated_at:%Y-%m-%d %H:%M} UTC",
        "",
        f"📊 Jami signal: {s.total} ta (savdoga aylangani: {s.traded})",
    ]

    if s.traded:
        qatorlar += [
            f"   🎯🎯 TP2: {s.tp2}   🎯 TP1→Stop: {s.tp1_then_stop}   🛑 Stop: {s.stop}",
            f"   Win-rate: {s.win_rate:.0%}   Stop: {s.stop_rate:.0%}",
        ]
    if s.cancelled:
        qatorlar.append(f"   ❌ Bekor bo'lgan (Entry'ga yetmagan): {s.cancelled}")
    if s.false_signals:
        qatorlar.append(f"   ⚠️ Yolg'on signal (tez Stop): {s.false_signals}")
    if s.average_score is not None:
        qatorlar.append(f"   O'rtacha ball: {s.average_score:.0f}/100")
    if s.average_holding_hours is not None:
        qatorlar.append(f"   O'rtacha ushlab turish: {s.average_holding_hours:.1f} soat")

    qatorlar.append("")

    if report.sample_warning:
        qatorlar.append(f"ℹ️ {report.sample_warning}")
    elif not report.patterns:
        qatorlar.append(
            "✅ Sezilarli naqsh topilmadi — hozirgi sozlamalar ma'lumotga mos ishlayapti."
        )
    else:
        qatorlar.append(f"🔍 Aniqlangan naqshlar ({len(report.patterns)} ta):")
        qatorlar.append("")
        for naqsh in report.patterns:
            qatorlar.append(naqsh.describe())
            qatorlar.append("")

    qatorlar.append(
        "⚠️ Bu tavsiyalar AVTOMATIK qo'llanilmaydi. Sozlamani o'zgartirish "
        "qarori — sizniki."
    )
    return "\n".join(qatorlar)
