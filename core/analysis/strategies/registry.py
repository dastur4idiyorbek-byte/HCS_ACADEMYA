"""6.1-band: strategiyalar registri — plug-in arxitekturasining markazi.

Yangi strategiya qo'shish uchun:
    1. Shu papkaga `Strategy` interfeysini amalga oshiruvchi fayl qo'shiladi
    2. `_STRATEGY_TYPES` ro'yxatiga qo'shiladi
    3. Konfiguratsiyada yoqiladi

Boshqa HECH QAYERNI o'zgartirish shart emas: signal sikli (15-bosqich)
registrni chaqiradi, Risk Engine esa strategiya turini umuman bilmaydi —
u faqat `SignalCandidate` ni ko'radi.
"""

from __future__ import annotations

from core.analysis.strategies.base import Strategy
from core.analysis.strategies.classic_ta import ClassicTaStrategy
from core.analysis.strategies.correction_entry import CorrectionEntryStrategy
from core.analysis.strategies.narx_harakati_strategiya import NarxHarakatiStrategy
from core.analysis.strategies.opening_range_scalp import OpeningRangeScalpStrategy
from core.config.schema import AppConfig
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Barcha mavjud strategiyalar. Tartib muhim emas — har biri mustaqil.
_STRATEGY_TYPES: list[type[Strategy]] = [
    ClassicTaStrategy,
    OpeningRangeScalpStrategy,
    CorrectionEntryStrategy,
    NarxHarakatiStrategy,
]


def build_strategies(config: AppConfig, enabled_only: bool = True) -> list[Strategy]:
    """Konfiguratsiyaga qarab strategiyalarni quradi.

    Args:
        enabled_only: `True` — faqat yoqilganlari qaytariladi.
    """
    hammasi = [turi(config) for turi in _STRATEGY_TYPES]
    natija = [s for s in hammasi if s.enabled] if enabled_only else hammasi

    logger.info(
        "Strategiyalar: %s",
        ", ".join(f"{s.name}({'yoq' if s.enabled else 'och'})" for s in hammasi) or "yo'q",
    )
    return natija


def required_timeframes(strategies: list[Strategy]) -> set[str]:
    """Barcha strategiyalar uchun kerakli timeframelar birlashmasi.

    Ma'lumot yuklovchi shu ro'yxatga tayanadi — har bir strategiya uchun
    alohida so'rov yuborilmaydi.
    """
    kerakli: set[str] = set()
    for strategiya in strategies:
        kerakli.update(strategiya.required_timeframes())
    return kerakli
