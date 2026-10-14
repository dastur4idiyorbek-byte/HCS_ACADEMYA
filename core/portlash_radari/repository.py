"""`radar_*` jadvallari bilan ishlash.

FAQAT O'Z JADVALLARIGA YOZADI. Boshqa jadvallardan (halol reestr)
faqat o'qiladi va bu `halol.py` da turadi. Modul 3.0.0 jadvallariga
(`kuzatuv_*`) bu fayl umuman tegmaydi — `tests/core/test_radar_chegara.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.portlash_radari.vaqt import TASDIQ
from core.storage.models import (
    RadarHajm,
    RadarHolati,
    RadarNatija,
    RadarSessiya,
    RadarSozlama,
    RadarYashirin,
)

YURMOQDA = "yurmoqda"
TUGADI = "tugadi"
XATO = "xato"

HOLAT_ID = 1


@dataclass(frozen=True, slots=True)
class Baholanadigan:
    """Calibration navbatidagi bitta yozuv."""

    natija_id: int
    symbol: str
    narx: float
    boshlandi: datetime


class RadarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ----------------------------------------------------------------- #
    #  Sessiyalar
    # ----------------------------------------------------------------- #

    async def sessiya_boshla(
        self,
        turi: str,
        sham_vaqti: datetime,
        kun: str,
        tartib: int,
        sozlama: dict,
        boshlandi: datetime,
    ) -> int:
        sessiya = RadarSessiya(
            turi=turi,
            sham_vaqti=sham_vaqti,
            kun=kun,
            tartib=tartib,
            boshlandi=boshlandi,
            holat=YURMOQDA,
            sozlama_json=json.dumps(sozlama, ensure_ascii=False),
        )
        self._s.add(sessiya)
        await self._s.flush()
        return sessiya.id

    async def sessiya_yakunla(
        self,
        sessiya_id: int,
        *,
        holat: str,
        tugadi: datetime,
        manbalar: dict,
        universum: int = 0,
        darvozadan: int = 0,
        elakdan: int = 0,
        nomzod: int = 0,
        btc_ozgarish: float | None = None,
        izoh: str = "",
    ) -> None:
        await self._s.execute(
            update(RadarSessiya)
            .where(RadarSessiya.id == sessiya_id)
            .values(
                holat=holat,
                tugadi=tugadi,
                manbalar_json=json.dumps(manbalar, ensure_ascii=False),
                universum=universum,
                darvozadan=darvozadan,
                elakdan=elakdan,
                nomzod=nomzod,
                btc_ozgarish=btc_ozgarish,
                izoh=izoh[:2000],
            )
        )

    async def rasmiy_bormi(self, turi: str, sham_vaqti: datetime) -> bool:
        """Bu sessiya allaqachon yurganmi (holati qanday bo'lishidan qat'i nazar).

        Xato bilan tugagan sessiya QAYTA yurgizilmaydi: aks holda Binance
        javob bermagan paytda ishchi har daqiqada urinib, so'rov bo'roni
        qo'zg'atardi. O'tkazib yuborilgan sessiya ekranda ko'rinadi.
        """
        natija = await self._s.execute(
            select(RadarSessiya.id)
            .where(RadarSessiya.turi == turi, RadarSessiya.sham_vaqti == sham_vaqti)
            .limit(1)
        )
        return natija.first() is not None

    async def tugagan_sessiya(self, turi: str, sham_vaqti: datetime) -> RadarSessiya | None:
        natija = await self._s.execute(
            select(RadarSessiya)
            .where(
                RadarSessiya.turi == turi,
                RadarSessiya.sham_vaqti == sham_vaqti,
                RadarSessiya.holat == TUGADI,
            )
            .order_by(RadarSessiya.id.desc())
            .limit(1)
        )
        return natija.scalars().first()

    async def oldingi_tasdiq(self, sham_vaqti: datetime) -> RadarSessiya | None:
        """Shu shamdan oldingi eng so'nggi TUGAGAN rasmiy (B) sessiya.

        Oraliqda sessiya o'tkazib yuborilgan bo'lsa ham topiladi — sessiya
        jadvalidagi foiz "oldingi mavjud rasmiy sessiya"dan hisoblanadi.
        """
        natija = await self._s.execute(
            select(RadarSessiya)
            .where(
                RadarSessiya.turi == TASDIQ,
                RadarSessiya.sham_vaqti < sham_vaqti,
                RadarSessiya.holat == TUGADI,
            )
            .order_by(RadarSessiya.sham_vaqti.desc(), RadarSessiya.id.desc())
            .limit(1)
        )
        return natija.scalars().first()

    async def natijalar(self, sessiya_id: int) -> list[RadarNatija]:
        natija = await self._s.execute(
            select(RadarNatija).where(RadarNatija.sessiya_id == sessiya_id)
        )
        return list(natija.scalars().all())

    async def natijalarni_yoz(self, sessiya_id: int, qatorlar: list[dict]) -> None:
        for q in qatorlar:
            self._s.add(RadarNatija(sessiya_id=sessiya_id, **q))
        await self._s.flush()

    async def yurmoqda_qolganlarni_yop(self, hozir: datetime) -> int:
        """Ishchi to'xtab qolgan paytda yarim qolgan sessiyalar.

        Ular "yurmoqda" holatida abadiy qolmasin — ekranda bu "hozir
        tekshirilyapti" degan yolg'on bo'lardi.
        """
        natija = await self._s.execute(
            update(RadarSessiya)
            .where(RadarSessiya.holat == YURMOQDA)
            .values(holat=XATO, tugadi=hozir, izoh="ishchi sessiya o'rtasida to'xtab qoldi")
        )
        return natija.rowcount or 0

    # ----------------------------------------------------------------- #
    #  30 kunlik o'rtacha
    # ----------------------------------------------------------------- #

    async def ortachalar(self) -> dict[str, tuple[float | None, int]]:
        natija = await self._s.execute(
            select(RadarHajm.symbol, RadarHajm.ortacha_30k, RadarHajm.kunlar)
        )
        return {symbol: (ortacha, kunlar) for symbol, ortacha, kunlar in natija.all()}

    async def ortachalarni_yoz(
        self, qiymatlar: dict[str, tuple[float | None, int]], hozir: datetime
    ) -> None:
        mavjud = {
            q.symbol: q for q in (await self._s.execute(select(RadarHajm))).scalars().all()
        }
        for symbol, (ortacha, kunlar) in qiymatlar.items():
            qator = mavjud.get(symbol)
            if qator is None:
                self._s.add(
                    RadarHajm(symbol=symbol, ortacha_30k=ortacha, kunlar=kunlar, yangilangan=hozir)
                )
            else:
                qator.ortacha_30k = ortacha
                qator.kunlar = kunlar
                qator.yangilangan = hozir
        await self._s.flush()

    # ----------------------------------------------------------------- #
    #  Admin sozlamalari va yashirish (sayt yozadi, bu yerda o'qiladi)
    # ----------------------------------------------------------------- #

    async def sozlamalar(self) -> dict[str, float]:
        natija = await self._s.execute(select(RadarSozlama.kalit, RadarSozlama.qiymat))
        return {kalit: float(qiymat) for kalit, qiymat in natija.all()}

    async def yashirinlar(self, hozir: datetime) -> set[str]:
        natija = await self._s.execute(
            select(RadarYashirin.symbol).where(
                or_(RadarYashirin.gacha.is_(None), RadarYashirin.gacha > hozir)
            )
        )
        return {symbol.upper() for (symbol,) in natija.all()}

    # ----------------------------------------------------------------- #
    #  Ishchi holati
    # ----------------------------------------------------------------- #

    async def _holat(self) -> RadarHolati:
        qator = await self._s.get(RadarHolati, HOLAT_ID)
        if qator is None:
            qator = RadarHolati(id=HOLAT_ID)
            self._s.add(qator)
            await self._s.flush()
        return qator

    async def holat(self) -> RadarHolati:
        return await self._holat()

    async def tirik(self, hozir: datetime) -> None:
        (await self._holat()).ishchi_tirik = hozir

    async def sorovni_ol(self) -> bool:
        """Admin "hozir tekshir" bosganmi. Bosgan bo'lsa bayroq tushiriladi.

        Bayroq SHU YERDA tushiriladi, tekshiruvdan keyin emas: tekshiruv
        yiqilsa ham ishchi uni har daqiqada qayta boshlamasin.
        """
        qator = await self._holat()
        if not qator.sorov:
            return False
        qator.sorov = False
        return True

    async def hajm_yangilandi(self, hozir: datetime) -> None:
        (await self._holat()).hajm_yangilandi = hozir

    async def baholandi(self, hozir: datetime) -> None:
        (await self._holat()).baholash_oxirgi = hozir

    async def xato_yoz(self, matn: str) -> None:
        (await self._holat()).oxirgi_xato = matn[:2000]

    # ----------------------------------------------------------------- #
    #  Calibration
    # ----------------------------------------------------------------- #

    async def baholanadiganlar(
        self, davr: str, hozir: datetime, limit: int = 200
    ) -> list[Baholanadigan]:
        """Vaqti kelgan, hali baholanmagan rasmiy yozuvlar (`24s` | `7k`)."""
        if davr == "24s":
            kutish, vaqt_ustuni = timedelta(hours=24), RadarNatija.kel_24s_vaqt
        else:
            kutish, vaqt_ustuni = timedelta(days=7), RadarNatija.kel_7k_vaqt
        natija = await self._s.execute(
            select(RadarNatija.id, RadarNatija.symbol, RadarNatija.narx, RadarSessiya.boshlandi)
            .join(RadarSessiya, RadarSessiya.id == RadarNatija.sessiya_id)
            .where(
                and_(
                    RadarSessiya.turi == TASDIQ,
                    RadarSessiya.holat == TUGADI,
                    RadarNatija.turi.in_(("elak", "namuna")),
                    RadarNatija.narx.is_not(None),
                    RadarNatija.narx > 0,
                    vaqt_ustuni.is_(None),
                    RadarSessiya.boshlandi <= hozir - kutish,
                )
            )
            .order_by(RadarSessiya.boshlandi)
            .limit(limit)
        )
        return [
            Baholanadigan(natija_id=i, symbol=s, narx=float(n), boshlandi=b)
            for i, s, n, b in natija.all()
        ]

    async def baholashni_yoz(
        self,
        natija_id: int,
        davr: str,
        oxiri: float | None,
        eng_yuqori: float | None,
        eng_past: float | None,
        vaqt: datetime,
    ) -> None:
        if davr == "24s":
            qiymatlar = {
                "kel_24s_oxiri": oxiri,
                "kel_24s_max": eng_yuqori,
                "kel_24s_min": eng_past,
                "kel_24s_vaqt": vaqt,
            }
        else:
            qiymatlar = {
                "kel_7k_oxiri": oxiri,
                "kel_7k_max": eng_yuqori,
                "kel_7k_min": eng_past,
                "kel_7k_vaqt": vaqt,
            }
        await self._s.execute(
            update(RadarNatija).where(RadarNatija.id == natija_id).values(**qiymatlar)
        )

    # ----------------------------------------------------------------- #
    #  Tozalash
    # ----------------------------------------------------------------- #

    async def eskilarni_ochir(self, chegara: datetime) -> int:
        """Muddati o'tgan yashirishlar o'chiriladi (tarix emas — u qoladi)."""
        natija = await self._s.execute(
            delete(RadarYashirin).where(
                RadarYashirin.gacha.is_not(None), RadarYashirin.gacha <= chegara
            )
        )
        return natija.rowcount or 0
