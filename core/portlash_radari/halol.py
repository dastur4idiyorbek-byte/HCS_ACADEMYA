"""Halol reestr holati — SANOQQA KIRMAYDI, faqat yonida ko'rsatiladi.

NIMA UCHUN `verdict_for()` EMAS. U reestrda yo'q coinga `HALAL`
qaytaradi (`core/halal_screening/rulings.py`). Modul 3.0.0 da bu
to'g'ri — u faqat 80 ta tekshirilgan coin bilan ishlaydi. Radar esa
yuzlab futures coinini ko'radi va ularning ko'pchiligi hech qachon
tekshirilmagan. `verdict_for()` ularning hammasini yolg'on "✅ halol"
qilib ko'rsatardi.

Shuning uchun radar reestrni O'ZI O'QIYDI va "yozilmagan"ni
"halol"dan ajratadi. Halol moduliga tegilmaydi.

TARTIB (`StaticRulingRegistry` bilan bir xil ustunlik):

    1. stablecoin                 -> shubhali
    2. bazadagi qaror (admin)     -> halol / harom / shubhali
    3. YAML urug'lari             -> harom / shubhali
    4. 80 talik ro'yxat           -> halol (ishchi taxmin, docs/HALOL_ROYXAT.md)
    5. qolgani                    -> baholanmagan
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.schema import AppConfig
from core.storage.models import CoinRuling

HALOL = "halol"
HAROM = "harom"
SHUBHALI = "shubhali"
BAHOLANMAGAN = "baholanmagan"

#: `coin_rulings.status` -> radar holati
_STATUS = {"halal": HALOL, "haram": HAROM, "mashbooh": SHUBHALI}


class Reestr:
    """Bir sessiya davomida o'zgarmaydigan reestr surati."""

    def __init__(
        self,
        bazadagi: dict[str, str],
        config: AppConfig,
    ) -> None:
        self._bazadagi = {k.upper(): v for k, v in bazadagi.items()}
        hs = config.halal_screening
        self._stablecoin = {s.upper() for s in hs.stablecoin_symbols}
        self._harom_urug = {s.upper() for s in hs.seed_haram_symbols}
        self._shubhali_urug = {s.upper() for s in hs.seed_mashbooh_symbols}
        self._halol_royxat = {s.upper() for s in config.zanjir.kuzatiladigan_coinlar}

    def holati(self, belgi: str) -> str:
        b = belgi.upper()
        if b in self._stablecoin:
            return SHUBHALI
        status = self._bazadagi.get(b)
        if status in _STATUS:
            return _STATUS[status]
        if b in self._harom_urug:
            return HAROM
        if b in self._shubhali_urug:
            return SHUBHALI
        if b in self._halol_royxat:
            return HALOL
        return BAHOLANMAGAN


async def bazadagi_qarorlar(session: AsyncSession) -> dict[str, str]:
    """`coin_rulings` -> {belgi: status}. FAQAT O'QIYDI."""
    natija = await session.execute(select(CoinRuling.symbol, CoinRuling.status))
    return {symbol.upper(): status for symbol, status in natija.all()}
