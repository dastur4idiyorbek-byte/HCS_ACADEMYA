"""3.8-band: yopilgan signalning natijasi va konteksti.

BU MODULDA ENDI TA'RIF YO'Q — faqat qayta e'lon.

`Outcome`, `ClosedSignal` va `outcome_from_status` `core.domain` ga
ko'chirildi: ularni tahlil qatlami ham, xotira qatlami ham o'qiydi,
ya'ni joyi ikkalasidan quyida (`docs/ARXITEKTURA.md`, qurilish
xaritasi). Bu yerdagi nom saqlanadi, chunki postmortem moduli o'z
lug'ati bilan o'qilishi kerak.

Nima uchun postmortem bazadan emas, SOF ma'lumotdan ishlaydi: naqsh
izlash mantig'i backtestda ham, jonli rejimda ham bir xil kod bilan
sinaladi.
"""

from __future__ import annotations

from core.domain.models import ClosedSignal, Outcome, outcome_from_status

__all__ = ["ClosedSignal", "Outcome", "outcome_from_status"]
