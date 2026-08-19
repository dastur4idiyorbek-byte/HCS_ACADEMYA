"""Biznes-mantiq xizmatlari.

Bu qatlam repository'lar ustida turadi va "nima qilinishi kerak" degan
savolga javob beradi (Telegram emas, biznes tilida). Handlerlar shu
xizmatlarni chaqiradi — o'zlari qaror qabul qilmaydi.

Eslatma: sof ma'lumot tiplari bu yerda emas, `core/domain/` da. Aks holda
aylanma bog'liqlik paydo bo'lardi: repository -> services -> repository.
"""

from core.services.portfolio import compute_outcome, summarize
from core.services.subscription import SubscriptionOutcome, SubscriptionService

__all__ = [
    "SubscriptionOutcome",
    "SubscriptionService",
    "compute_outcome",
    "summarize",
]
