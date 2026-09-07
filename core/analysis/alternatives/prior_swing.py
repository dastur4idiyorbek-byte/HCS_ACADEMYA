"""3B — Oldingi Swing High/Low zonasi.

Zona bloki ZAIF bo'lganda (fib bor, lekin OB/FVG/POC mos kelmadi)
ikkinchi alternativ: oldingi swing PAST — o'z-o'zidan support
zonasi. Narx unga qaytib kelayotgan bo'lsa, o'sha yer zona.

Zona oldingi swing PAST atrofida tor oraliq sifatida quriladi va
`darajalar_qur` ga uzatiladi: stop zona ostiga (swing pastidan
pastga), entry zona ichida yoki chetida.
"""

from __future__ import annotations

from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.analysis.zone_quality.fibonacci import Zona

#: Oldingi swing atrofidagi zona umumiy kengligi (foizda, ikki tomonga).
#: 🔴 O'LCHANMAGAN.
OLDIINGI_SWING_KENGLIK_PCT = 2.0


def oldingi_swing_zona(
    nuqtalar: list[Swing],
    kenglik_pct: float = OLDIINGI_SWING_KENGLIK_PCT,
) -> Zona | None:
    """Oxirgi swing PAST atrofidagi zona."""
    for s in reversed(nuqtalar):
        if s.turi is not SwingTuri.PAST:
            continue
        if s.narx <= 0:
            return None
        yarim = kenglik_pct / 2
        past = s.narx * (1 - yarim / 100)
        yuqori = s.narx * (1 + yarim / 100)
        return Zona(past=past, yuqori=yuqori, manba="oldingi_swing")
    return None
