"""Biznes-mantiq xizmatlari.

Bu qatlam repository'lar ustida turadi va "nima qilinishi kerak" degan
savolga javob beradi (Telegram emas, biznes tilida). Handlerlar shu
xizmatlarni chaqiradi — o'zlari qaror qabul qilmaydi.

Eslatma: sof ma'lumot tiplari bu yerda emas, `core/domain/` da. Aks holda
aylanma bog'liqlik paydo bo'lardi: repository -> services -> repository.
"""

from core.services.kirish_rejasi import decide_entry_plan
from core.services.portfolio import blended_result_pct, compute_outcome, summarize
from core.services.subscription import SubscriptionOutcome, SubscriptionService

__all__ = [
    "decide_entry_plan",
    "blended_result_pct",
    "SubscriptionOutcome",
    "SubscriptionService",
    "compute_outcome",
    "summarize",
]
