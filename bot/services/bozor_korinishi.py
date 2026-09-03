"""Sayt uchun bozor ko'rinishi — haftalik va kunlik post.

LOYIHA EGASINING SHARTI (2026-09-03):

    "Haftalik va kunlik shunchaki qarash. Asosiy tahlil 4
     soatlik. Bu umumiy ta'sir qilmaydi, faqat veb sayt uchun
     post. San uni 4 soatlikka bog'lama."

SHUNING UCHUN BU XIZMAT SIGNAL YO'LIDAN TASHQARIDA. U
`PipelineRunner` ni chaqirmaydi, strategiyaga hech narsa
bermaydi va hech qanday darvozada turmaydi. Yagona natijasi —
bazaga yoziladigan post, uni sayt ko'rsatadi.

`tests/core/test_bozor_korinishi.py` bu shartni kod bilan
qulflaydi: strategiya yoki quvur faylida `bozor_korinishi`
so'zi paydo bo'lsa test yiqiladi.

NIMA UCHUN QIYMATLAR SAQLANADI. BTC.D, USDT.D, TOTAL va
hosilalari birjadan SHAM sifatida kelmaydi — manba faqat
hozirgi holatni beradi. Yo'nalishni aytish uchun tarix kerak,
va uni o'zimiz yig'amiz.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from core.analysis.bozor_korinishi import (
    ASBOBLAR,
    BozorKorinishi,
    KorinishTuri,
    korinish_qur,
)
from core.config.schema import AppConfig
from core.market_data.base import CandleProvider
from core.market_data.global_metrics import CoinGeckoGlobalMetrics
from core.storage.database import Database
from core.storage.repositories import (
    BozorKesimiRepository,
    BozorKorinishiRepository,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)

#: Narx qatori bor asboblar — qolganlari saqlangan tarixdan keladi.
NARX_ASBOBLARI = ("BTC", "ETH")

#: Yo'nalish uchun nechta nuqta olinadi.
TARIX_CHUQURLIGI = 30


class BozorKorinishiXizmati:
    """Kesimlarni yozadi va postni quradi."""

    def __init__(
        self,
        database: Database,
        config: AppConfig,
        candles: CandleProvider,
        metrics: CoinGeckoGlobalMetrics | None = None,
    ) -> None:
        self._db = database
        self._config = config
        self._candles = candles
        self._metrics = metrics or CoinGeckoGlobalMetrics(config.market_data)

    # ------------------------------------------------------------------ #

    async def kunlik_yozuv(self, hozir: datetime | None = None) -> bool:
        """Kunlik kesimlarni saqlaydi. Bugun yozilgan bo'lsa — o'tkazadi.

        Returns:
            `True` — yangi yozuv qo'shildi.
        """
        hozir = hozir or utc_now()
        kesimlar = await self._metrics.fetch()
        if kesimlar is None:
            logger.warning("Bozor kesimlari olinmadi — post yangilanmaydi")
            return False

        async with self._db.session() as session:
            repo = BozorKesimiRepository(session)
            oxirgi = await repo.oxirgi_vaqt("TOTAL")
            if oxirgi is not None and hozir - oxirgi < timedelta(hours=20):
                return False
            for kod, qiymat in kesimlar.kesimlar().items():
                await repo.yozish(kod, qiymat, hozir)
        logger.info("Bozor kesimlari saqlandi: %s", ", ".join(kesimlar.kesimlar()))
        return True

    async def post_qur(
        self, turi: KorinishTuri, hozir: datetime | None = None
    ) -> BozorKorinishi | None:
        """Postni quradi va saqlaydi."""
        hozir = hozir or utc_now()
        timeframe = "1w" if turi is KorinishTuri.HAFTALIK else "1d"

        narx_qatorlari = {}
        for kod in NARX_ASBOBLARI:
            try:
                shamlar = await self._candles.fetch_candles(kod, timeframe, 60)
            except Exception:  # noqa: BLE001 — post signalni to'xtatmaydi
                logger.warning("%s %s shamlari olinmadi", kod, timeframe, exc_info=True)
                continue
            if shamlar:
                narx_qatorlari[kod] = shamlar

        async with self._db.session() as session:
            kesim_repo = BozorKesimiRepository(session)
            kesim_tarixi = {
                kod: await kesim_repo.tarix(kod, TARIX_CHUQURLIGI)
                for kod, _ in ASBOBLAR
                if kod not in NARX_ASBOBLARI
            }

        korinish = korinish_qur(turi, hozir, narx_qatorlari, kesim_tarixi)
        if not korinish.asboblar:
            logger.warning("Bozor ko'rinishi bo'sh — post saqlanmadi")
            return None

        async with self._db.session() as session:
            await BozorKorinishiRepository(session).saqlash(
                turi=turi.value,
                sana=hozir,
                asboblar_json=json.dumps(
                    [
                        {
                            "kod": a.kod,
                            "nom": a.nom,
                            "qiymat": a.qiymat,
                            "ozgarish": a.ozgarish_pct,
                            "yonalish": a.yonalish.value,
                            "ulush": a.ulushmi,
                            "izoh": a.izoh(),
                        }
                        for a in korinish.asboblar
                    ],
                    ensure_ascii=False,
                ),
                xulosa=korinish.xulosa,
                kutilma=korinish.kutilma,
            )
        logger.info(
            "Bozor ko'rinishi saqlandi: %s, %d ta asbob",
            turi.value,
            len(korinish.asboblar),
        )
        return korinish

    async def close(self) -> None:
        await self._metrics.close()
