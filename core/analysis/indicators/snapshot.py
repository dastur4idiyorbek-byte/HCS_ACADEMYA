"""Indikatorlarning bir lahzadagi holati.

Nima uchun bitta obyektga yig'iladi: har bir indikator alohida hisoblansa,
ball hisoblash (8-bosqich) va Risk Engine har biri uchun alohida chaqiruv
qilardi. Bitta snapshot — bir marta hisoblanadi, hamma joyda ishlatiladi.

`None` qiymat — "hisoblab bo'lmadi" degani, "nol" emas. Bu farq muhim:
0.3-band bo'yicha hisoblanmagan indikator tasdiq bera olmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.indicators.momentum import MacdResult, macd, rsi, rsi_recovering_from_oversold
from core.analysis.indicators.trend import adx, closes
from core.analysis.indicators.volatility import atr, atr_pct
from core.analysis.indicators.volume import volume_ratio
from core.config.schema import IndicatorConfig
from core.domain.models import Candle


@dataclass(frozen=True, slots=True)
class IndicatorSnapshot:
    """Bitta coin, bitta timeframe uchun barcha indikator qiymatlari."""

    price: float
    rsi: float | None
    rsi_recovering: bool
    macd: MacdResult | None
    volume_ratio: float | None
    adx: float | None
    atr: float | None
    atr_pct: float | None

    @property
    def is_complete(self) -> bool:
        """Barcha indikator hisoblandimi.

        To'liq bo'lmagan snapshot bilan signal berilmaydi (0.3-band).
        """
        return all(
            qiymat is not None
            for qiymat in (
                self.rsi,
                self.macd,
                self.volume_ratio,
                self.adx,
                self.atr,
            )
        )


def build_snapshot(candles: list[Candle], config: IndicatorConfig) -> IndicatorSnapshot | None:
    """Shamlardan indikator holatini quradi.

    Returns:
        `IndicatorSnapshot`, yoki `None` — sham umuman yo'q.
    """
    if not candles:
        return None

    narxlar = closes(candles)
    return IndicatorSnapshot(
        price=narxlar[-1],
        rsi=rsi(narxlar, config.rsi_period),
        rsi_recovering=rsi_recovering_from_oversold(
            narxlar, config.rsi_period, config.rsi_oversold
        ),
        macd=macd(narxlar, config.macd_fast, config.macd_slow, config.macd_signal),
        volume_ratio=volume_ratio(candles, config.volume_ma_period),
        adx=adx(candles, config.adx_period),
        atr=atr(candles, config.atr_period),
        atr_pct=atr_pct(candles, config.atr_period),
    )
