"""Signal hayotidagi hodisalar.

Nima uchun alohida tip: kuzatuvchi (tracker) faqat "nima sodir bo'ldi"
deb aytadi — kimga xabar yuborish, bazaga yozish yoki statistikaga qo'shish
uni qiziqtirmaydi. Shu sababli bir xil kuzatuv kodi jonli rejimda ham,
backtestda ham ishlaydi (6.3-band).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.domain.enums import SignalStatus


class SignalEventKind(str, Enum):
    ACTIVATED = "activated"        # ⏳ -> ✅ narx Entry'ga yetdi
    TP1_HIT = "tp1_hit"            # 🎯 BIRINCHI TP olindi -> breakeven
    TP_PARTIAL = "tp_partial"      # 🎯 oraliq TP olindi, signal ochiq qoladi
    TP2_HIT = "tp2_hit"            # 🎯🎯 YAKUNIY TP olindi, signal yopiladi
    STOPPED = "stopped"            # 🛑 Stop bo'ldi, signal yopiladi
    CANCELLED = "cancelled"        # Entry'ga yetmasdan eskirdi/bekor qilindi
    WEAKENING = "weakening"        # ⚠️ ball keskin pasaydi (4.1-band)
    FALSE_SIGNAL = "false_signal"  # faol bo'lgach tez Stop yedi (3.8-band)


@dataclass(frozen=True, slots=True)
class SignalEvent:
    """Bitta holat o'zgarishi."""

    signal_id: int | None
    symbol: str
    kind: SignalEventKind
    price: float
    at: datetime
    new_status: SignalStatus
    detail: str | None = None

    @property
    def closes_signal(self) -> bool:
        return self.kind in {
            SignalEventKind.TP2_HIT,
            SignalEventKind.STOPPED,
            SignalEventKind.CANCELLED,
        }
