"""Kuzatuv natijasini bazaga yozadi — bir tomonlama.

    skaner -> jadval -> ekran

Sayt bu jadvalga HECH NARSA yozmaydi (bitta istisno: admin skan
so'raganda `kuzatuv_skani.sorov` bayrog'i, va u ham natijaga emas,
BUYRUQQA tegishli).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.analysis.observation_mode import KuzatuvNatija
from core.storage.models import KuzatuvBozor, KuzatuvHolati, KuzatuvSkani
from core.watch_panel.cmc_snapshot import BozorSurati
from core.watch_panel.live_market_data import BozorYigmasi
from core.watch_panel.top20_selector import Royxatlar

#: Skan qaysi bosqichda.
BOSH = "bosh"
YURMOQDA = "yurmoqda"
TUGADI = "tugadi"
XATO = "xato"

#: Coin qaysi ro'yxatda.
TOP = "top"
KUZATUVDA = "kuzatuvda"
TASHQARIDA = "royxatdan_tashqari"


def _bloklar_json(natija: KuzatuvNatija) -> str:
    return json.dumps(
        [
            {
                "nom": b.nom,
                "kuch": b.kuch,
                "maxraj": b.maxraj,
                "otdi": b.otdi,
                "olchanmadi": b.olchanmadi,
                "tosiq": b.qattiq_tosiq,
                "tekshiruvlar": [
                    {"nom": t.nom, "holat": t.holat.value, "izoh": t.izoh}
                    for t in b.tekshiruvlar
                ],
            }
            for b in natija.bloklar
        ],
        ensure_ascii=False,
    )


def _segmentlar_json(natija: KuzatuvNatija) -> str:
    return json.dumps(
        [
            {
                "nom": s.nom,
                "holat": s.holat.value,
                "izoh": s.izoh,
                "timeframe": s.timeframe,
            }
            for s in natija.segmentlar
        ],
        ensure_ascii=False,
    )


class KuzatuvRepository:
    """Holat va skan boshqaruvi."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def yoz(
        self, natija: KuzatuvNatija, *, royxat: str, orin: int | None
    ) -> None:
        """Coin holatini YANGILAYDI (yo'q bo'lsa yaratadi).

        Tarix saqlanmaydi — har skanda o'sha qator ustiga yoziladi.
        """
        stmt = select(KuzatuvHolati).where(KuzatuvHolati.symbol == natija.symbol)
        qator = (await self._session.execute(stmt)).scalar_one_or_none()
        if qator is None:
            qator = KuzatuvHolati(symbol=natija.symbol)
            self._session.add(qator)

        zona = natija.zona_natija.zona if natija.zona_natija else None

        qator.yonalish = natija.yonalish.yonalish.value
        qator.yonalish_izoh = natija.yonalish.izoh
        qator.otdi = natija.otdi
        qator.diqqat = natija.diqqat
        qator.segmentlar_json = _segmentlar_json(natija)
        qator.bloklar_json = _bloklar_json(natija)
        qator.zona_darajasi = natija.zona_darajasi.value
        qator.zona_past = zona.past if zona else None
        qator.zona_yuqori = zona.yuqori if zona else None
        qator.ogohlantirish = natija.ogohlantirish
        qator.nisbiy_kuch = natija.nisbiy_kuch
        qator.royxat = royxat
        qator.orin = orin
        qator.tekshirilgan = datetime.now(UTC)

    async def royxatlarni_yoz(self, royxatlar: Royxatlar, qolganlar: list[KuzatuvNatija]) -> None:
        """Ikki ro'yxat va ro'yxatdan tashqaridagilarni birga yozadi.

        `qolganlar` — filtrdan o'tmagan yoki 30 dan pastda qolgan
        coinlar. Ular ham YOZILADI: keyingi skanda o'rni o'zgarsa,
        eski yozuv yangilanishi kerak. Aks holda bir marta Top 20 ga
        kirgan coin u yerdan HECH QACHON chiqmasdi.
        """
        for i, natija in enumerate(royxatlar.top, start=1):
            await self.yoz(natija, royxat=TOP, orin=i)
        for i, natija in enumerate(royxatlar.kuzatuvda, start=len(royxatlar.top) + 1):
            await self.yoz(natija, royxat=KUZATUVDA, orin=i)
        for natija in qolganlar:
            await self.yoz(natija, royxat=TASHQARIDA, orin=None)

    async def _skan(self) -> KuzatuvSkani:
        """Yagona qator (id=1) — yo'q bo'lsa yaratiladi."""
        qator = await self._session.get(KuzatuvSkani, 1)
        if qator is None:
            qator = KuzatuvSkani(id=1)
            self._session.add(qator)
            await self._session.flush()
        return qator

    async def sorov_bormi(self) -> bool:
        """Admin qo'lda skan so'raganmi — va bayroqni DARHOL tushiradi.

        Bayroq o'qish bilan birga tushiriladi: aks holda skan
        tugaguncha admin yana bossa yoki bot qayta yuklansa, bitta
        so'rov ikki marta bajarilardi.
        """
        qator = await self._skan()
        if not qator.sorov:
            return False
        qator.sorov = False
        return True

    async def sorov_qoy(self) -> None:
        """Sayt tomonidan chaqiriladi — admin "hozir yangila" bosdi."""
        qator = await self._skan()
        qator.sorov = True

    async def boshlandi(self) -> None:
        qator = await self._skan()
        qator.holat = YURMOQDA
        qator.boshlandi = datetime.now(UTC)
        qator.tugadi = None
        qator.izoh = ""

    async def tugadi(self, *, tekshirildi: int, otdi: int) -> None:
        qator = await self._skan()
        qator.holat = TUGADI
        qator.tekshirildi = tekshirildi
        qator.otdi = otdi
        qator.tugadi = datetime.now(UTC)

    async def xato(self, izoh: str) -> None:
        qator = await self._skan()
        qator.holat = XATO
        qator.izoh = izoh[:500]
        qator.tugadi = datetime.now(UTC)

    async def bozorni_yoz(
        self,
        yigma: BozorYigmasi,
        surat: BozorSurati | None,
    ) -> None:
        """Jonli yig'ma va CoinGecko suratini birga yozadi.

        Surat `None` bo'lsa — CoinGecko javob bermagan. O'sha
        ustunlar TEGILMAYDI (eski qiymat qoladi), nolga tushmaydi:
        "kapitalizatsiya nol" degan yolg'on ma'no bermasin.
        """
        stmt = select(KuzatuvBozor).where(KuzatuvBozor.symbol == yigma.symbol)
        qator = (await self._session.execute(stmt)).scalar_one_or_none()
        if qator is None:
            qator = KuzatuvBozor(symbol=yigma.symbol)
            self._session.add(qator)

        if yigma.narx is not None:
            qator.narx = yigma.narx
        qator.xarid_bosimi = yigma.xarid_bosimi
        qator.hajm_usd = yigma.hajm_usd
        qator.yirik_savdo = yigma.yirik_savdo
        qator.yiriklar_json = yigma.yiriklar_json()

        if surat is not None:
            qator.market_cap = surat.market_cap
            qator.hajm_24s = surat.hajm_24s
            qator.ozgarish_1s = surat.ozgarish_1s
            qator.ozgarish_24s = surat.ozgarish_24s
            qator.ozgarish_7k = surat.ozgarish_7k
            if yigma.narx is None and surat.narx is not None:
                qator.narx = surat.narx

        qator.yangilangan = datetime.now(UTC)

    async def bozordan_tashqarilarni_ochir(self, qoladigan: list[str]) -> None:
        """Top 20 dan chiqqan coinlarning jonli qatorini o'chiradi.

        NEGA O'CHIRILADI (holatdan farqli o'laroq). Jonli ma'lumot
        "hozir" haqida: coin Top 20 dan chiqqach unga oqim ulanmaydi
        va qator MUZLAB qoladi. Uni ekranda ko'rsatish — 40 daqiqa
        oldingi xarid bosimini "hozirgi" deb aytish bo'lardi.
        """
        saqlash = {s.upper() for s in qoladigan}
        qatorlar = (await self._session.execute(select(KuzatuvBozor))).scalars().all()
        for qator in qatorlar:
            if qator.symbol.upper() not in saqlash:
                await self._session.delete(qator)
