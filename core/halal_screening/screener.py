"""3.4-band: "Halol ro'yxat" mantig'i.

    1. Bozor kapitalizatsiyasi bo'yicha reyting olinadi
    2. Ro'yxat 1-o'rindan boshlab PASTGA qarab tekshiriladi
    3. Har bir coin uchun halol/harom ro'yxati tekshiriladi
    4. Harom/shubhali bo'lsa — O'TKAZIB YUBORILADI
    5. Halol chiqqanlar yig'iladi, TO'LIQ 30 taga YETGUNCHA davom etiladi
    6. NATIJA: aynan 30 ta HALOL, eng yuqori kapitalizatsiyali coin

Qo'shimcha filtrlar: minimal kunlik savdo hajmi (likvidlik), stablecoinlar.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from core.config.schema import HalalScreeningConfig
from core.domain.enums import HalalStatus
from core.domain.models import HalalVerdict, MarketRankEntry, ScreeningResult
from core.halal_screening.rulings import RulingRegistry
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)

LOW_LIQUIDITY_REASON_TEMPLATE = (
    "Kunlik savdo hajmi yetarli emas (${volume:,.0f} < ${minimum:,.0f}) — "
    "likvidlik filtri (3.4-band)."
)


class RankingProvider(Protocol):
    """Kapitalizatsiya reytingi manbai (CoinGecko / CoinMarketCap)."""

    async def fetch_ranking(self, limit: int) -> list[MarketRankEntry]:
        ...


class HalalScreener:
    """Halol coinlar "olamini" (universe) shakllantiradi."""

    def __init__(
        self,
        config: HalalScreeningConfig,
        registry: RulingRegistry,
    ) -> None:
        self._config = config
        self._registry = registry

    def screen(
        self,
        ranking: list[MarketRankEntry],
        now: datetime | None = None,
    ) -> ScreeningResult:
        """Reyting ro'yxatidan Top-N halol ro'yxatini yig'adi.

        Sof funksiya — tarmoqqa murojaat qilmaydi, shuning uchun to'liq
        test qilinadi va backtestda ham ishlatiladi.
        """
        config = self._config
        accepted: list[str] = []
        verdicts: list[HalalVerdict] = []
        skipped: list[HalalVerdict] = []
        scanned = 0

        for entry in sorted(ranking, key=lambda item: item.rank):
            if len(accepted) >= config.target_count:
                break
            if scanned >= config.max_scan_depth:
                logger.warning(
                    "Skan chuqurligi chegarasiga yetildi (%d), yig'ilgan halol coin: %d/%d",
                    config.max_scan_depth,
                    len(accepted),
                    config.target_count,
                )
                break

            scanned += 1
            verdict = self._evaluate(entry)

            if verdict.status is HalalStatus.HALAL:
                accepted.append(verdict.symbol)
                verdicts.append(verdict)
            else:
                skipped.append(verdict)

        complete = len(accepted) == config.target_count
        if not complete:
            # 0.3-band (fail-safe): to'liq bo'lmagan ro'yxat ham qaytariladi,
            # lekin `complete=False` bayrog'i bilan — chaqiruvchi qaror qiladi.
            logger.warning(
                "Halol ro'yxat to'liq emas: %d/%d (skan qilingan: %d)",
                len(accepted),
                config.target_count,
                scanned,
            )

        return ScreeningResult(
            symbols=accepted,
            verdicts=verdicts,
            scanned_depth=scanned,
            generated_at=now or utc_now(),
            complete=complete,
            skipped=skipped,
        )

    async def build_universe(self, provider: RankingProvider) -> ScreeningResult:
        """Reytingni manbadan olib, skrining qiladi.

        Skan chuqurligi bo'yicha so'raymiz — 30 ta halol topish uchun 30 tadan
        ko'proq coin ko'rib chiqilishi kerak (ba'zilari o'tkazib yuboriladi).
        """
        ranking = await provider.fetch_ranking(self._config.max_scan_depth)
        return self.screen(ranking)

    # ------------------------------------------------------------------ #

    def _evaluate(self, entry: MarketRankEntry) -> HalalVerdict:
        """Bitta coin: avval likvidlik, keyin halollik."""
        if entry.volume_24h_usd < self._config.min_daily_volume_usd:
            return HalalVerdict(
                symbol=entry.symbol.upper(),
                status=HalalStatus.MASHBOOH,
                reason=LOW_LIQUIDITY_REASON_TEMPLATE.format(
                    volume=entry.volume_24h_usd,
                    minimum=self._config.min_daily_volume_usd,
                ),
            )
        return self._registry.verdict_for(entry.symbol)

    def pair_for(self, symbol: str) -> str:
        """Birja juftligi nomi, masalan `BTC` -> `BTCUSDT`."""
        return f"{symbol.upper()}{self._config.quote_asset.upper()}"
