"""Zanjir modulining jonli holatini saqlash (4-prompt, 3-qism).

QAT'IY QOIDA — BIR TOMONLAMA OQIM:

    modul -> hisoblaydi -> shu jadval -> ekran

Teskarisi TAQIQLANADI: bu yerdagi hech narsa zanjir moduliga kirish
(input) sifatida qaytmaydi va signal qaroriga ta'sir qilmaydi.

Bu qoida eski tizimda buzilgan edi: Bozor Salomatligi Indeksi
"ko'rsatkich" deb boshlanib, keyin signal chiqishini to'sadigan
darvozaga aylangan. Natijada modul o'zining ko'rsatkichiga qarab
qaror qiladigan, tekshirib bo'lmaydigan halqa paydo bo'lgandi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.storage.models import ZanjirHolati
from core.utils.time_utils import utc_now


@dataclass(frozen=True, slots=True)
class BlokHolati:
    """Bitta blokning ekran uchun tayyor holati."""

    nom: str
    kuch: int
    maxraj: int
    otdi: bool
    olchanmadi: bool
    tosiq: str = ""


@dataclass(frozen=True, slots=True)
class CoinHolati:
    """Bitta coinning oxirgi tekshiruv natijasi."""

    symbol: str
    bloklar: tuple[BlokHolati, ...]
    toliq: bool
    uzildi_blokda: str | None
    ishonch: float
    natija: str
    izoh: str = ""
    signal_id: int | None = None
    tekshirilgan: datetime | None = None


class ZanjirHolatRepository:
    """Oxirgi holatni yozadi va o'qiydi."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def yoz(self, holat: CoinHolati) -> None:
        """Coinning holatini YANGILAYDI (yo'q bo'lsa yaratadi).

        Har yugurishda o'sha qator ustiga yoziladi — tarix
        saqlanmaydi. Sabab jadval izohida.
        """
        stmt = select(ZanjirHolati).where(ZanjirHolati.symbol == holat.symbol)
        qator = (await self._session.execute(stmt)).scalar_one_or_none()
        if qator is None:
            qator = ZanjirHolati(symbol=holat.symbol)
            self._session.add(qator)

        qator.bloklar_json = json.dumps(
            [
                {
                    "nom": b.nom,
                    "kuch": b.kuch,
                    "maxraj": b.maxraj,
                    "otdi": b.otdi,
                    "olchanmadi": b.olchanmadi,
                    "tosiq": b.tosiq,
                }
                for b in holat.bloklar
            ],
            ensure_ascii=False,
        )
        qator.toliq = holat.toliq
        qator.uzildi_blokda = holat.uzildi_blokda
        qator.ishonch = holat.ishonch
        qator.natija = holat.natija
        qator.izoh = holat.izoh
        qator.signal_id = holat.signal_id
        qator.tekshirilgan = holat.tekshirilgan or utc_now()
        await self._session.flush()

    async def barchasi(self) -> list[CoinHolati]:
        """Barcha coinlarning oxirgi holati — ekran uchun."""
        stmt = select(ZanjirHolati).order_by(ZanjirHolati.symbol)
        return [
            CoinHolati(
                symbol=q.symbol,
                bloklar=tuple(
                    BlokHolati(
                        nom=b.get("nom", ""),
                        kuch=int(b.get("kuch", 0)),
                        maxraj=int(b.get("maxraj", 0)),
                        otdi=bool(b.get("otdi")),
                        olchanmadi=bool(b.get("olchanmadi")),
                        tosiq=b.get("tosiq", "") or "",
                    )
                    for b in json.loads(q.bloklar_json)
                ),
                toliq=q.toliq,
                uzildi_blokda=q.uzildi_blokda,
                ishonch=q.ishonch,
                natija=q.natija,
                izoh=q.izoh,
                signal_id=q.signal_id,
                tekshirilgan=q.tekshirilgan,
            )
            for q in (await self._session.execute(stmt)).scalars()
        ]
