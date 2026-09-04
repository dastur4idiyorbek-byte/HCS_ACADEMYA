"""Halol skrining — coin qarorlari (harom / shubhali / halol).

`screener.py` 2026-09-04 da eski tahlil moduli bilan birga olib
tashlandi: u CoinMarketCap reytingiga tayangan "Top 30" ro'yxatini
yasardi. Yangi modulda ro'yxat QAT'IY va `config` da yozilgan
(`zanjir.kuzatiladigan_coinlar`), ya'ni o'zgaruvchan reyting kerak
emas.

Lekin o'sha paytda BU FAYLDAGI import olib tashlanmadi va natijada
paket serverda `ModuleNotFoundError` bilan yiqildi. Xato faqat
Railway'da ko'rindi, chunki hech bir test bu paketni import
qilmasdi. Endi `tests/test_import_qilinadi.py` har bir modulni
import qiladi.
"""

from core.halal_screening.rulings import (
    DEFAULT_HALAL_REASON,
    DEFAULT_HARAM_REASON,
    DEFAULT_MASHBOOH_REASON,
    RulingRegistry,
    StaticRulingRegistry,
)

__all__ = [
    "DEFAULT_HALAL_REASON",
    "DEFAULT_HARAM_REASON",
    "DEFAULT_MASHBOOH_REASON",
    "RulingRegistry",
    "StaticRulingRegistry",
]
