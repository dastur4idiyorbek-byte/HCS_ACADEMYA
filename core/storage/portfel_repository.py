"""Portfel moduli uchun ma'lumotlarga kirish qatlami (3-prompt).

NIMA UCHUN ALOHIDA FAYL. `repositories.py` allaqachon 890 satr — u
yerga qo'shish uni yana kattalashtirardi. Portfel moduli o'z jadvallari
bilan ishlaydi va boshqa repositorylarga tegmaydi.

MUHIM CHEGARA. `core/portfolio/` paketi HECH NARSAGA bog'lanmaydi —
u sof funksiya. Bazadan o'qish va yozish SHU YERDA turadi: modul
"bo'laklar ro'yxati"ni oladi va yangi ro'yxatni qaytaradi, uni
saqlash esa bu qatlamning ishi.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.portfolio.capital_allocator import Bolak, bolaklarni_yarat
from core.portfolio.pnl_calculator import OchiqPozitsiya, YopilganQism
from core.storage.models import CapitalBlock, PositionExit, SignalRecord, UserPosition
from core.utils.time_utils import utc_now


class PortfelRepository:
    """Bo'lak holati va yopilgan qismlar."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ----------------------------------------------------------------- #
    #  Kapital bo'laklari
    # ----------------------------------------------------------------- #

    async def bolaklar(self, user_id: int) -> list[Bolak]:
        """Foydalanuvchining bo'laklari. Yo'q bo'lsa — bo'sh ro'yxat."""
        stmt = (
            select(CapitalBlock)
            .where(CapitalBlock.user_id == user_id)
            .order_by(CapitalBlock.raqam)
        )
        qatorlar = (await self._session.execute(stmt)).scalars()
        return [
            Bolak(
                raqam=q.raqam,
                hajm=q.hajm_usd,
                band_kapital=q.band_kapital_usd,
                band_xavf=q.band_xavf_usd,
            )
            for q in qatorlar
        ]

    async def bolaklarni_tayyorla(
        self, user_id: int, balans: float, soni: int = 3
    ) -> list[Bolak]:
        """Bo'laklarni o'qiydi; hali yo'q bo'lsa — yaratib beradi.

        BAND QISM SAQLANADI. Balans o'zgarganda yoki bo'lak soni
        boshqacha bo'lganda bo'laklar qayta quriladi, lekin ochiq
        pozitsiyalarga ketgan pul YO'QOLMAYDI — u o'sha raqamli
        bo'lakka ko'chiriladi. Ansiz balansni o'zgartirish ochiq
        savdolarni "bepul" qilib qo'yardi.
        """
        mavjud = await self.bolaklar(user_id)
        kutilgan_hajm = balans / soni if soni > 0 else 0.0
        togri = len(mavjud) == soni and all(
            abs(b.hajm - kutilgan_hajm) < 0.01 for b in mavjud
        )
        if togri:
            return mavjud

        band = {b.raqam: (b.band_kapital, b.band_xavf) for b in mavjud}
        yangilar = [
            Bolak(
                raqam=b.raqam,
                hajm=b.hajm,
                band_kapital=band.get(b.raqam, (0.0, 0.0))[0],
                band_xavf=band.get(b.raqam, (0.0, 0.0))[1],
            )
            for b in bolaklarni_yarat(balans, soni)
        ]
        await self.saqla(user_id, yangilar)
        return yangilar

    async def saqla(self, user_id: int, bolaklar: list[Bolak]) -> None:
        """Bo'laklar holatini bazaga yozadi (bor bo'lsa yangilaydi)."""
        stmt = select(CapitalBlock).where(CapitalBlock.user_id == user_id)
        qatorlar = {q.raqam: q for q in (await self._session.execute(stmt)).scalars()}

        for bolak in bolaklar:
            qator = qatorlar.pop(bolak.raqam, None)
            if qator is None:
                qator = CapitalBlock(user_id=user_id, raqam=bolak.raqam, hajm_usd=bolak.hajm)
                self._session.add(qator)
            qator.hajm_usd = bolak.hajm
            qator.band_kapital_usd = bolak.band_kapital
            qator.band_xavf_usd = bolak.band_xavf

        # Bo'lak soni kamaysa, ortiqchalari qolib ketmasin.
        for ortiqcha in qatorlar.values():
            await self._session.delete(ortiqcha)

        await self._session.flush()

    # ----------------------------------------------------------------- #
    #  Yopilgan qismlar
    # ----------------------------------------------------------------- #

    async def qism_yoz(  # noqa: PLR0913 — bitta yozuvning barcha ustuni
        self,
        position_id: int,
        bosqich: int,
        narx: float,
        ulush_pct: float,
        miqdor_usd: float,
        natija_usd: float,
        sabab: str = "",
        yopilgan_vaqt: datetime | None = None,
    ) -> PositionExit:
        """Pozitsiyaning bitta qismi yopilganini qayd etadi."""
        yozuv = PositionExit(
            position_id=position_id,
            bosqich=bosqich,
            narx=narx,
            ulush_pct=ulush_pct,
            miqdor_usd=miqdor_usd,
            natija_usd=natija_usd,
            sabab=sabab,
            yopilgan_vaqt=yopilgan_vaqt or utc_now(),
        )
        self._session.add(yozuv)
        await self._session.flush()
        return yozuv

    async def yopilgan_qismlar(self, user_id: int) -> list[YopilganQism]:
        """PNL hisobi uchun — DB modeliga bog'lanmagan ko'rinish."""
        stmt = (
            select(PositionExit, UserPosition.signal_id, SignalRecord.symbol)
            .join(UserPosition, PositionExit.position_id == UserPosition.id)
            .join(SignalRecord, UserPosition.signal_id == SignalRecord.id)
            .where(UserPosition.user_id == user_id)
            .order_by(PositionExit.yopilgan_vaqt)
        )
        return [
            YopilganQism(
                signal_id=signal_id,
                symbol=symbol,
                yopilgan_vaqt=chiqish.yopilgan_vaqt,
                miqdor_usd=chiqish.miqdor_usd,
                natija_usd=chiqish.natija_usd,
                sabab=chiqish.sabab,
            )
            for chiqish, signal_id, symbol in (await self._session.execute(stmt)).all()
        ]

    async def ochiq_pozitsiyalar(
        self, user_id: int, narxlar: dict[str, float] | None = None
    ) -> list[OchiqPozitsiya]:
        """Hozir ochiq savdolar.

        `narxlar` — joriy narx (symbol -> narx). Narxi YO'Q coin
        `joriy_narx=None` bilan qaytadi: u unrealized hisobiga
        KIRMAYDI va ekranda alohida aytiladi. "Narx olinmadi" ni
        "+$0.00" deb ko'rsatish aldash bo'lardi.
        """
        narxlar = narxlar or {}
        stmt = (
            select(UserPosition, SignalRecord.symbol)
            .join(SignalRecord, UserPosition.signal_id == SignalRecord.id)
            .where(UserPosition.user_id == user_id, UserPosition.closed_at.is_(None))
        )
        natija = []
        for pozitsiya, symbol in (await self._session.execute(stmt)).all():
            sotilgan = await self._sotilgan_ulush(pozitsiya.id)
            ochiq_miqdor = pozitsiya.amount_usd * max(0.0, 100.0 - sotilgan) / 100
            if ochiq_miqdor <= 0:
                continue
            natija.append(
                OchiqPozitsiya(
                    signal_id=pozitsiya.signal_id,
                    symbol=symbol,
                    entry=pozitsiya.entry_price,
                    ochiq_miqdor_usd=ochiq_miqdor,
                    joriy_narx=narxlar.get(symbol),
                )
            )
        return natija

    async def _sotilgan_ulush(self, position_id: int) -> float:
        stmt = select(PositionExit.ulush_pct).where(PositionExit.position_id == position_id)
        return sum((await self._session.execute(stmt)).scalars())
