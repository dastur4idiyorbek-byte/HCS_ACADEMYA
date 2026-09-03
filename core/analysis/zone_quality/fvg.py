"""3.3 — Fair Value Gap: uch shamli bo'shliq.

TA'RIF: uchta ketma-ket shamda 1-shamning `high` i 3-shamning `low`
idan PAST bo'lsa — orada narx umuman savdo qilmagan oraliq qoladi.
Bu — "adolatsiz qiymat", va bozor odatda unga qaytadi.

Ko'tarilish FVG (bullish): `sham[i-1].high < sham[i+1].low`.
Bo'shliq = o'sha ikki daraja orasi.

O'RTADAGI SHAM tekshirilmaydi — u shunchaki tez harakat qilgan
sham. Muhimi — chetlardagi ikki sham orasida teshik qolganmi.

FAQAT ENG SO'NGGI TO'LDIRILMAGAN FVG qaytariladi. To'ldirilgani
(narx qaytib kirgani) endi zona emas — u o'z vazifasini bajardi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.zone_quality.fibonacci import Zona
from core.domain.models import Candle


@dataclass(frozen=True, slots=True)
class FVG:
    zona: Zona
    indeks: int


def fvg_topish(shamlar: list[Candle], orqaga: int = 50) -> FVG | None:
    """Eng so'nggi TO'LDIRILMAGAN ko'tarilish FVG si.

    Args:
        orqaga: necha sham orqaga qaraladi
    """
    if len(shamlar) < 3:
        return None

    boshlanish = max(1, len(shamlar) - orqaga)
    for i in range(len(shamlar) - 2, boshlanish - 1, -1):
        oldingi = shamlar[i - 1]
        keyingi = shamlar[i + 1]
        if oldingi.high >= keyingi.low:
            continue

        zona = Zona(past=oldingi.high, yuqori=keyingi.low, manba="fvg")
        if _toldirilgan(shamlar[i + 2 :], zona):
            continue
        return FVG(zona=zona, indeks=i)

    return None


def _toldirilgan(keyingilar: list[Candle], zona: Zona) -> bool:
    """Narx bo'shliqqa qaytib kirdimi.

    "Kirdi" — pastki chegaraga TEGDI degani, to'liq kesib o'tish
    shart emas: FVG ning vazifasi narxni jalb qilish, va u tegishi
    bilan bajarilgan hisoblanadi.
    """
    return any(sham.low <= zona.yuqori for sham in keyingilar)
