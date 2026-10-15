"""Calibration — "biz aytgandan keyin narx qayerga bordi" (`docs/MODUL_4_0_0.md`, 11).

Har RASMIY sessiyadagi har pool va namuna coini uchun 24 soat va 7
kundan keyin:

    oxiri       davr oxiridagi narx, %
    eng yuqori  davr ichidagi eng yuqori narx, %
    eng past    davr ichidagi eng past narx, %

Hammasi o'sha sessiyadagi narxga nisbatan. Eng yuqori/past shamlardan
olinadi (24 soat — 1 soatlik, 7 kun — 4 soatlik): faqat sessiya
nuqtalaridagi narx portlashning cho'qqisini ko'rmay qolardi.

BU RAQAMLAR QARORGA KIRMAYDI. Ular faqat chegaralarni taxmin bilan
emas, dalil bilan to'g'rilash uchun yig'iladi.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.portlash_radari.manba import BinanceFutures, Sham
from core.portlash_radari.repository import Baholanadigan, RadarRepository
from core.storage import Database
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Davr:
    kod: str
    interval: str
    shamlar: int
    #: Shuncha vaqt o'tib ham sham kelmasa — baholash to'xtatiladi
    #: (coin delisting bo'lgan bo'lishi mumkin) va yozuv bo'sh qiymat
    #: bilan yopiladi. Aks holda u har soatda qayta so'ralardi.
    voz_kechish: timedelta


DAVRLAR = (
    Davr("24s", "1h", 24, timedelta(days=3)),
    Davr("7k", "4h", 42, timedelta(days=10)),
)


def natijani_hisobla(
    narx: float, shamlar: list[Sham], boshi: datetime
) -> tuple[float, float, float] | None:
    """(oxiri %, eng yuqori %, eng past %) yoki `None` (sham yo'q)."""
    ichida = [s for s in shamlar if s.ochilish >= boshi]
    if not ichida or narx <= 0:
        return None
    eng_yuqori = max(s.yuqori for s in ichida)
    eng_past = min(s.past for s in ichida)
    oxiri = ichida[-1].yopilish

    def foiz(x: float) -> float:
        return round((x / narx - 1.0) * 100.0, 4)

    return foiz(oxiri), foiz(eng_yuqori), foiz(eng_past)


class RadarBaholash:
    def __init__(
        self,
        database: Database,
        binance: BinanceFutures,
        soat: Callable[[], datetime] = utc_now,
    ) -> None:
        self._db = database
        self._b = binance
        self._soat = soat

    async def yur(self, limit: int = 200) -> int:
        """Vaqti kelgan yozuvlarni baholaydi. Nechtasi yozilgani qaytadi."""
        hozir = self._soat()
        yozildi = 0
        for davr in DAVRLAR:
            async with self._db.session() as s:
                navbat = await RadarRepository(s).baholanadiganlar(davr.kod, hozir, limit)
            if not navbat:
                continue
            natijalar = await asyncio.gather(*(self._bitta(davr, b, hozir) for b in navbat))
            async with self._db.session() as s:
                repo = RadarRepository(s)
                for b, n in zip(navbat, natijalar, strict=True):
                    if n is None:
                        continue
                    await repo.baholashni_yoz(b.natija_id, davr.kod, *n, vaqt=hozir)
                    yozildi += 1
        async with self._db.session() as s:
            await RadarRepository(s).baholandi(hozir)
        if yozildi:
            logger.info("Radar calibration: %d ta yozuv baholandi", yozildi)
        return yozildi

    async def _bitta(
        self, davr: Davr, b: Baholanadigan, hozir: datetime
    ) -> tuple[float | None, float | None, float | None] | None:
        """Yozish uchun qiymatlar, yoki `None` — hozircha yozilmaydi."""
        shamlar = await self._b.shamlar(b.symbol, davr.interval, b.boshlandi, davr.shamlar)
        if shamlar is None:
            # So'rov YIQILDI (tarmoq, 429, 451) — bu "sham yo'q" emas.
            # Keyingi soatda qayta urinadi; aks holda bir necha kunlik
            # uzilishdan keyin to'plangan yozuvlar butunlay bo'sh qolardi.
            return None
        natija = natijani_hisobla(b.narx, shamlar, b.boshlandi)
        if natija is not None:
            return natija
        if hozir - b.boshlandi > davr.voz_kechish:
            logger.warning("Radar calibration: %s uchun sham yo'q — voz kechildi", b.symbol)
            return None, None, None
        return None
