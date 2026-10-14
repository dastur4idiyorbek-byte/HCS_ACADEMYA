"""Radar ishchisi — o'z siklida yuradigan asyncio vazifasi.

BOTDAN MUSTAQIL. Loyiha egasining qarori (2026-10-14): Modul 4.0.0
faqat sayt uchun, Telegram botga hech narsa qo'shilmaydi. Shuning
uchun ishchi bot jarayoniga ulanmaydi — u alohida jarayon bo'lib
yuradi (`python -m core.portlash_radari`, `scripts/start.sh`). Radar
yiqilsa bot ham, sayt ham ishlayveradi; bot yiqilsa radar ishlayveradi.

HAR QADAMDA (taxminan har daqiqada):

    1. yurak urishi — sayt ishchi tirikmi yoki yo'qmi shundan biladi
    2. admin "hozir tekshir" bosganmi -> qo'lda tekshiruv
    3. vaqti kelgan rasmiy sessiyalar (A va B) — har biri BIR MARTA
    4. 30 kunlik o'rtacha hajm — kuniga bir marta (00:05 UTC)
    5. calibration — soatiga bir marta

Sessiya allaqachon yurganini ishchi BAZADAN biladi, xotiradan emas:
jarayon qayta ko'tarilsa ham bitta sessiya ikki marta yurmaydi.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta

from core.config.schema import AppConfig
from core.portlash_radari.baholash import RadarBaholash
from core.portlash_radari.manba import BinanceFutures, CoinGeckoTaminot, ManbaJurnali
from core.portlash_radari.repository import RadarRepository
from core.portlash_radari.sessiya import RadarSessiyasi, UnlockManbasi
from core.portlash_radari.vaqt import (
    QOLDA,
    JadvalSozlamasi,
    bajariladiganlar,
    keyingi_sham,
    keyingisi,
    kunlik_yangilash_vaqti,
)
from core.storage import Database
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)

#: Eng uzoq uyqu. Admin "hozir tekshir" bosgach shundan ko'p kutmasin.
MAX_UYQU = timedelta(seconds=60)
MIN_UYQU = timedelta(seconds=5)
#: Calibration oralig'i
BAHOLASH_ORALIGI = timedelta(hours=1)
#: Ishga tushgach birinchi qadamgacha kutish — bot va sayt bilan bir
#: zumda Binance'ga urilmaslik uchun. Kechikish chegarasi (B — 14 daqiqa)
#: bundan ancha katta.
BOSHLANGICH_KUTISH = timedelta(seconds=30)
#: Hajm keshi yangilanmasa, qayta urinish oralig'i
HAJM_QAYTA_URINISH = timedelta(minutes=15)


def jadval_sozlamasi(config: AppConfig) -> JadvalSozlamasi:
    r = config.radar
    return JadvalSozlamasi(
        kashfiyot_daqiqa=r.kashfiyot_daqiqa,
        tasdiq_daqiqa=r.tasdiq_daqiqa,
        kashfiyot_kechikish_daqiqa=r.kashfiyot_kechikish_daqiqa,
        tasdiq_kechikish_daqiqa=r.tasdiq_kechikish_daqiqa,
    )


class RadarIshchisi:
    def __init__(
        self,
        config: AppConfig,
        database: Database,
        *,
        binance: BinanceFutures | None = None,
        coingecko: CoinGeckoTaminot | None = None,
        unlock: UnlockManbasi | None = None,
        soat: Callable[[], datetime] = utc_now,
    ) -> None:
        r = config.radar
        self._config = config
        self._db = database
        self._soat = soat
        self._jadval = jadval_sozlamasi(config)
        self._b = binance or BinanceFutures(
            r.futures_base_url,
            config.halal_screening.stablecoin_symbols,
            kutish=r.sorov_kutish_soniya,
            parallel=r.parallel_sorov,
        )
        self._cg = coingecko or CoinGeckoTaminot(
            config.market_data.coingecko_base_url, kutish=r.sorov_kutish_soniya
        )
        if unlock is None:
            # FAQAT O'QISH uchun: Modul 3.0.0 ning unlock kalendari.
            from core.watch_panel.unlock_manba import UnlockManba

            unlock = UnlockManba()
        self._u = unlock
        self._sessiya = RadarSessiyasi(config, database, self._b, self._cg, self._u, soat)
        self._baholash = RadarBaholash(database, self._b, soat)
        self._oxirgi_baholash: datetime | None = None
        #: Hajm keshi muvaffaqiyatsiz yangilangan oxirgi urinish — Binance
        #: javob bermasa har daqiqada qayta so'ramaslik uchun.
        self._hajm_urinish: datetime | None = None
        self._vazifa: asyncio.Task | None = None

    # ----------------------------------------------------------------- #
    #  Hayot sikli
    # ----------------------------------------------------------------- #

    def start(self) -> None:
        if not self._config.radar.yoqilgan:
            logger.warning("Radar O'CHIQ (radar.yoqilgan = false) — sikl ishga tushmadi")
            return
        self._vazifa = asyncio.create_task(self.yur(), name="radar")

    async def stop(self) -> None:
        if self._vazifa is not None:
            self._vazifa.cancel()
            await asyncio.gather(self._vazifa, return_exceptions=True)
            self._vazifa = None
        await self.yop()

    async def yop(self) -> None:
        await self._b.yop()
        await self._cg.yop()
        yopuvchi = getattr(self._u, "yop", None)
        if yopuvchi is not None:
            await yopuvchi()

    async def yur(self) -> None:
        """Abadiy sikl. Bitta qadamning xatosi siklni to'xtatmaydi."""
        await asyncio.sleep(BOSHLANGICH_KUTISH.total_seconds())
        async with self._db.session() as s:
            yopildi = await RadarRepository(s).yurmoqda_qolganlarni_yop(self._soat())
        if yopildi:
            logger.warning("Radar: %d ta yarim qolgan sessiya yopildi", yopildi)
        logger.info("Radar ishchisi ishga tushdi")

        while True:
            try:
                await self.qadam()
            except asyncio.CancelledError:
                raise
            except Exception as xato:  # noqa: BLE001 — sikl yashashda davom etsin
                logger.exception("Radar qadami yiqildi")
                await self._xato_yoz(str(xato) or type(xato).__name__)
            await asyncio.sleep(self.uyqu().total_seconds())

    # ----------------------------------------------------------------- #
    #  Bitta qadam
    # ----------------------------------------------------------------- #

    async def qadam(self) -> list[str]:
        """Qadam. Nima bajarilgani qaytadi (test va log uchun)."""
        bajarildi: list[str] = []
        hozir = self._soat()
        async with self._db.session() as s:
            repo = RadarRepository(s)
            await repo.tirik(hozir)
            sorov = await repo.sorovni_ol()
            holat = await repo.holat()
            hajm_yangilandi = holat.hajm_yangilandi

        # Kesh umuman yo'q bo'lsa — sessiyadan OLDIN quriladi. Kesh
        # bo'lmasa elak ishlamaydi (o'rtacha yo'q -> nisbat yo'q).
        if hajm_yangilandi is None and self._hajm_vaqti_keldimi():
            await self.hajmni_yangila()
            bajarildi.append("hajm")

        for reja in bajariladiganlar(self._soat(), self._jadval):
            async with self._db.session() as s:
                yurgan = await RadarRepository(s).rasmiy_bormi(reja.turi, reja.sham_vaqti)
            if yurgan:
                continue
            await self._sessiya.yur(reja.turi, reja.sham_vaqti)
            bajarildi.append(reja.turi)

        if sorov:
            logger.info("Radar: admin so'rovi bilan qo'lda tekshiruv")
            await self._sessiya.yur(QOLDA, keyingi_sham(self._soat()))
            bajarildi.append(QOLDA)

        r = self._config.radar
        kerakli = kunlik_yangilash_vaqti(
            self._soat(), r.hajm_yangilash_soat, r.hajm_yangilash_daqiqa
        )
        if (
            "hajm" not in bajarildi
            and hajm_yangilandi is not None
            and hajm_yangilandi < kerakli
            and self._hajm_vaqti_keldimi()
        ):
            await self.hajmni_yangila()
            bajarildi.append("hajm")

        hozir = self._soat()
        if self._oxirgi_baholash is None or hozir - self._oxirgi_baholash >= BAHOLASH_ORALIGI:
            self._oxirgi_baholash = hozir
            await self._baholash.yur()
            async with self._db.session() as s:
                await RadarRepository(s).eskilarni_ochir(hozir)
            bajarildi.append("baholash")
        return bajarildi

    def uyqu(self) -> timedelta:
        """Keyingi sessiyagacha, lekin `MAX_UYQU` dan ko'p emas."""
        hozir = self._soat()
        keyin = keyingisi(hozir, self._jadval).vaqt - hozir
        return max(MIN_UYQU, min(MAX_UYQU, keyin))

    def _hajm_vaqti_keldimi(self) -> bool:
        if self._hajm_urinish is None:
            return True
        return self._soat() - self._hajm_urinish >= HAJM_QAYTA_URINISH

    async def hajmni_yangila(self) -> int:
        """Hamma juftlik uchun 30 kunlik o'rtacha hajm. Nechtasi yozilgani qaytadi."""
        hozir = self._soat()
        self._hajm_urinish = hozir
        jurnal = ManbaJurnali()
        juftliklar = await self._b.juftliklar(jurnal)
        if not juftliklar:
            # Kesh yangilanmadi — lekin vaqt belgisi QO'YILMAYDI: keyingi
            # qadamda qayta urinadi. Sabab ekranda ko'rinsin.
            await self._xato_yoz(
                "30 kunlik hajm yangilanmadi: Binance juftliklar ro'yxatini bermadi"
                + (" (451 — server mintaqasi cheklangan)" if jurnal.cheklangan() else "")
            )
            return 0
        natijalar = await asyncio.gather(
            *(self._b.kunlik_ortacha(j.symbol, hozir) for j in juftliklar)
        )
        qiymatlar = {
            j.symbol: n for j, n in zip(juftliklar, natijalar, strict=True) if n is not None
        }
        async with self._db.session() as s:
            repo = RadarRepository(s)
            await repo.ortachalarni_yoz(qiymatlar, hozir)
            await repo.hajm_yangilandi(hozir)
        logger.info("Radar: 30 kunlik hajm yangilandi — %d/%d", len(qiymatlar), len(juftliklar))
        return len(qiymatlar)

    async def _xato_yoz(self, matn: str) -> None:
        try:
            async with self._db.session() as s:
                await RadarRepository(s).xato_yoz(f"{self._soat().isoformat()} — {matn}")
        except Exception:  # noqa: BLE001 — xatoni yozib bo'lmasa ham sikl yashasin
            logger.exception("Radar xatosini bazaga yozib bo'lmadi")
