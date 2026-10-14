"""Sessiyada ishlatiladigan chegaralar: YAML standarti + admin o'zgarishi.

IKKI QATLAM:

    1. `config/default.yaml` -> `radar:`   standart qiymat
    2. `radar_sozlamalar` jadvali           admin saytda o'zgartirgani

Ikkinchisi birinchisini bosadi. Bazadagi qiymat ruxsat etilgan
oraliqdan chiqsa (masalan kimdir jadvalga qo'lda yozgan bo'lsa), u
TASHLAB YUBORILADI va standart ishlaydi — sababi ogohlantirishga
yoziladi. Noto'g'ri raqam bilan jim ishlagandan ko'ra standart yaxshi.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from core.config.schema import RADAR_BUTUN_KALITLAR, RADAR_ORALIQLARI, RadarConfig


@dataclass(frozen=True, slots=True)
class Chegaralar:
    """Bitta sessiyaning haqiqiy chegaralari."""

    min_kapitalizatsiya_usd: float
    min_hajm_24s_usd: float
    elak_hajm_x: float
    yangi_listing_kun: int
    hajm_x: float
    narx_ozgarish_pct: float
    funding_8s_pct: float
    oi_osish_pct: float
    long_short_nisbat: float
    btc_farq_pp: float
    aylanma_max_pct: float
    unlock_kun: int
    unlock_min_pct: float
    nomzod_min: int
    top_n: int
    namuna_soni: int
    portlash_24s_pct: float
    portlash_7k_pct: float
    #: Sozlanmaydi (oraliqlar jadvalida yo'q), lekin sessiyaga yoziladi
    oi_oyna_soat: int = 8

    def lugat(self) -> dict[str, float]:
        """`sozlama_json` uchun — sessiya qaysi raqam bilan hisoblangani."""
        return dataclasses.asdict(self)


def standart(config: RadarConfig) -> Chegaralar:
    return chegaralar_qur(config, {})[0]


def chegaralar_qur(
    config: RadarConfig, ozgarishlar: dict[str, float]
) -> tuple[Chegaralar, list[str]]:
    """YAML + bazadagi o'zgarishlar -> chegaralar va ogohlantirishlar."""
    qiymatlar: dict[str, float] = {
        kalit: float(getattr(config, kalit)) for kalit in RADAR_ORALIQLARI
    }
    ogohlar: list[str] = []
    for kalit, qiymat in ozgarishlar.items():
        if kalit not in RADAR_ORALIQLARI:
            ogohlar.append(f"noma'lum sozlama tashlandi: {kalit}")
            continue
        xato = qiymat_xatosi(kalit, qiymat)
        if xato:
            ogohlar.append(f"{kalit}: {xato} — standart ishlatildi")
            continue
        qiymatlar[kalit] = float(qiymat)

    tayyor: dict[str, float | int] = {
        kalit: int(q) if kalit in RADAR_BUTUN_KALITLAR else q for kalit, q in qiymatlar.items()
    }
    return Chegaralar(**tayyor, oi_oyna_soat=config.oi_oyna_soat), ogohlar  # type: ignore[arg-type]


def qiymat_xatosi(kalit: str, qiymat: float) -> str | None:
    """Qiymat yaroqsiz bo'lsa — sababi, aks holda `None`."""
    if kalit not in RADAR_ORALIQLARI:
        return "noma'lum kalit"
    try:
        son = float(qiymat)
    except (TypeError, ValueError):
        return "son emas"
    if math.isnan(son) or math.isinf(son):
        return "son emas"
    past, yuqori = RADAR_ORALIQLARI[kalit]
    if not past <= son <= yuqori:
        return f"{past:g}..{yuqori:g} oralig'idan tashqarida"
    if kalit in RADAR_BUTUN_KALITLAR and son != int(son):
        return "butun son bo'lishi kerak"
    return None
