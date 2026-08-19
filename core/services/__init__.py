"""Biznes-mantiq xizmatlari.

Bu qatlam repository'lar ustida turadi va "nima qilinishi kerak" degan
savolga javob beradi (Telegram emas, biznes tilida). Handlerlar shu
xizmatlarni chaqiradi — o'zlari qaror qabul qilmaydi.
"""

from core.services.subscription import SubscriptionOutcome, SubscriptionService

__all__ = ["SubscriptionOutcome", "SubscriptionService"]
