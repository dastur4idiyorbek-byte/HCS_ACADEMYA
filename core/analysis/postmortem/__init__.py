"""3.8-band: Signal Xotirasi — o'z-o'zini tekshiruvchi qism (Self-Audit Loop).

Har bir yopilgan signal statistikaga qo'shilib qolmaydi — tizim orqaga
qarab "nima uchun shunday bo'ldi" tahlil qiladi va NAQSH izlaydi.

Statistika va naqsh farqi:
    statistika — "35% signal Stop yedi"
    naqsh      — "Salomatlik 60dan past bo'lganda 70% Stop yeydi"

Ikkinchisi sababga ishora qiladi, birinchisi esa yo'q.

MUHIM TAMOYIL: xulosalar AVTOMATIK O'ZGARTIRISH QILMAYDI. Tizim o'z
sozlamalarini o'zi o'zgartirsa, xato naqsh butun strategiyani buzishi va
buni hech kim sezmasdan qolishi mumkin. Hisobot faqat adminga aniq tavsiya
beradi — qaror insonniki.

HALOLLIK CHEGARASI: naqsh faqat namuna yetarli bo'lganda e'lon qilinadi.
"Naqsh topilmadi" va "ma'lumot yetarli emas" — bir xil narsa emas, va
hisobotda ular ajratiladi.

    outcome.py   — yopilgan signal va uning konteksti
    patterns.py  — naqsh izlash
    report.py    — haftalik hisobot
"""

from core.analysis.postmortem.outcome import ClosedSignal, Outcome, outcome_from_status
from core.analysis.postmortem.patterns import Pattern, Segment, find_patterns
from core.analysis.postmortem.report import (
    PeriodStats,
    SelfAuditReport,
    build_report,
    compute_stats,
    render_report,
)

__all__ = [
    "ClosedSignal",
    "Outcome",
    "Pattern",
    "PeriodStats",
    "Segment",
    "SelfAuditReport",
    "build_report",
    "compute_stats",
    "find_patterns",
    "outcome_from_status",
    "render_report",
]
