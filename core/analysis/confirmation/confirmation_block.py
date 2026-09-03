"""BLOK 4 — to'rt tasdiqlash tekshiruvini yig'adi."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.analysis.confirmation.fundamental_recheck import fundamental_hamon_mos
from core.analysis.confirmation.liquidity_sweep import sweep_bormi
from core.analysis.confirmation.lower_tf_confirm import pastki_tf_tasdigi
from core.analysis.confirmation.rsi_divergence import (
    divergensiya,
    past_zonadan_qaytish,
    rsi,
)
from core.analysis.structure.swing_detector import Swing
from core.analysis.turlar import Blok, blok, ha, malumot_yoq, yoq
from core.analysis.zone_quality.fibonacci import Zona
from core.domain.models import Candle

BLOK_NOMI = "Tasdiqlash"


@dataclass(frozen=True, slots=True)
class TasdiqKirish:
    shamlar: list[Candle] = field(default_factory=list)
    nuqtalar: list[Swing] = field(default_factory=list)
    pastki_shamlar: list[Candle] = field(default_factory=list)
    zona: Zona | None = None
    #: Zanjir boshida hisoblangan fundamental blok
    eski_fundamental: Blok | None = None
    #: Hozirgi holatdagi fundamental blok
    yangi_fundamental: Blok | None = None


def tasdiqlash_blok(kirish: TasdiqKirish) -> Blok:
    qiymatlar = rsi(kirish.shamlar)
    rsi_ijobiy = bool(qiymatlar) and (
        past_zonadan_qaytish(qiymatlar) or divergensiya(kirish.shamlar, qiymatlar)
    )
    mos = fundamental_hamon_mos(kirish.eski_fundamental, kirish.yangi_fundamental)

    tekshiruvlar = [
        _bayroq(
            "liquidity_sweep",
            sweep_bormi(kirish.shamlar, kirish.nuqtalar),
            "swing yalandi va qaytdi",
        ),
        _bayroq(
            "pastki_tf",
            pastki_tf_tasdigi(kirish.pastki_shamlar, kirish.zona),
            "mini-BOS/sweep",
        ),
        (
            malumot_yoq("rsi_divergensiya", "RSI uchun sham yetmaydi")
            if not qiymatlar
            else _bayroq("rsi_divergensiya", rsi_ijobiy, f"RSI {qiymatlar[-1]:.0f}")
        ),
        (
            malumot_yoq("fundamental_mos", "solishtirishga blok yo'q")
            if mos is None
            else _bayroq("fundamental_mos", mos, "fundamental hamon kuchda")
        ),
    ]
    return blok(BLOK_NOMI, tekshiruvlar)


def _bayroq(nom: str, qiymat: bool, izoh: str):  # noqa: ANN202
    return ha(nom, f"{izoh} ✓") if qiymat else yoq(nom, f"{izoh} ✗")
