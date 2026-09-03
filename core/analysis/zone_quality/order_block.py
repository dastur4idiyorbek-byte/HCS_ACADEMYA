"""3.2 — Order Block.

IKKI TA'RIF, IKKALASI HAM BACKTEST QILINADI (2-prompt talabi):

    last_opposite  — reversaldan oldingi so'nggi QARAMA-QARSHI sham.
                     Ko'tarilish uchun: o'sishdan oldingi oxirgi
                     tushuvchi sham tanasi.
    sweep_candle   — likvidlikni yalab o'tgan sham (oldingi pastni
                     kesib, o'sha shamning o'zi yuqoriga yopilgan).

Ikkalasi bir xil g'oyaning ikki o'qilishi: "katta o'yinchi qayerda
buyurtma qoldirdi". Qaysi biri yaxshi ishlashini FAQAT o'lchov
aytadi — shuning uchun tanlov config'da, taxmin qilinmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.analysis.zone_quality.fibonacci import Zona
from core.domain.models import Candle


class ObTarifi(str, Enum):
    LAST_OPPOSITE = "last_opposite"
    SWEEP_CANDLE = "sweep_candle"


@dataclass(frozen=True, slots=True)
class OrderBlock:
    zona: Zona
    indeks: int
    tarif: ObTarifi


def ob_topish(
    shamlar: list[Candle],
    impuls_boshi: int,
    tarif: ObTarifi = ObTarifi.LAST_OPPOSITE,
    orqaga: int = 10,
) -> OrderBlock | None:
    """Impuls boshlanishidan ORQAGA qarab Order Block qidiradi.

    Args:
        impuls_boshi: ko'tarilish boshlangan sham indeksi
        orqaga: necha sham orqaga qaraladi
    """
    boshlanish = max(0, impuls_boshi - orqaga)
    oyna = list(range(boshlanish, min(impuls_boshi + 1, len(shamlar))))
    if not oyna:
        return None

    if tarif is ObTarifi.SWEEP_CANDLE:
        return _sweep(shamlar, oyna)
    return _last_opposite(shamlar, oyna)


def _last_opposite(shamlar: list[Candle], oyna: list[int]) -> OrderBlock | None:
    """Oxirgi TUSHUVCHI sham (close < open) tanasi."""
    for i in reversed(oyna):
        sham = shamlar[i]
        if sham.close < sham.open:
            return OrderBlock(
                zona=Zona(past=sham.close, yuqori=sham.open, manba="order_block"),
                indeks=i,
                tarif=ObTarifi.LAST_OPPOSITE,
            )
    return None


def _sweep(shamlar: list[Candle], oyna: list[int]) -> OrderBlock | None:
    """Oldingi pastni kesib o'tib, YUQORIGA yopilgan sham.

    Bu — "stop huntingdan keyin qaytish" naqshi. Shamning butun
    diapazoni (low..high) zona bo'ladi, tanasi emas: yalash aynan
    wickda sodir bo'ladi.
    """
    for i in reversed(oyna):
        if i == 0:
            continue
        sham = shamlar[i]
        oldingi = shamlar[i - 1]
        yaladi = sham.low < oldingi.low
        qaytdi = sham.close > oldingi.low
        if yaladi and qaytdi:
            return OrderBlock(
                zona=Zona(past=sham.low, yuqori=sham.high, manba="order_block"),
                indeks=i,
                tarif=ObTarifi.SWEEP_CANDLE,
            )
    return None
