"""3.7-band: Bozor Salomatligi Indeksi uchun kiruvchi ma'lumotlar.

Nima uchun alohida obyekt: indeks besh xil manbadan (bozor, foydalanuvchilar,
faol signallar) ma'lumot oladi. Ularni bitta obyektga yig'ish hisoblagichni
SOF funksiyaga aylantiradi — u hech qayerga murojaat qilmaydi, faqat
berilgandan hisoblaydi. Shu sababli backtestda ham ishlaydi.

`None` qiymat — "ma'lumot yo'q" degani. Har bir omil bunday holatda o'zini
qanday tutishini alohida hal qiladi (pastdagi izohlarga qarang) — jimgina
nol yoki 0.5 qo'yilmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.domain.enums import TrendDirection
from core.domain.models import Candle
from core.position_sizing import AggregateCapacity


@dataclass(frozen=True, slots=True)
class HealthInputs:
    """Indeks hisoblash uchun tizimning hozirgi holati."""

    computed_at: datetime

    # --- 1-omil (ASOSIY): halol ro'yxatning SMC struktura kengligi ---
    #: Har bir halol coin uchun STRUKTURA yo'nalishi
    #: (`market_structure.analyze_structure()` natijasidan).
    #:
    #: Nima uchun bu asosiy omil bo'ldi: BTC Dominance foydali, lekin
    #: ko'pchilik treyder uchun qaror mezoni emas. Struktura esa real
    #: narx harakatining o'zi — "nechta coin HH/HL qadam tashlayapti".
    universe_structures: dict[str, TrendDirection] = field(default_factory=dict)

    # --- 6-omil (kichik vazn): BTC Dominance ---
    #: Hozirgi BTC dominance foizi (masalan 54.2)
    btc_dominance: float | None = None
    #: Sutkalik o'zgarish, foiz punktlarida (masalan +0.3 yoki -1.8)
    btc_dominance_change_24h: float | None = None

    # --- 3-omil: Volatillik rejimi ---
    #: Har bir coin uchun ADX qiymati
    universe_adx: dict[str, float] = field(default_factory=dict)

    # --- 4-omil: Agregat foydalanuvchi sig'imi (5.2-band) ---
    capacity: AggregateCapacity | None = None

    # --- 5-omil: Faol signallar to'yinganligi ---
    open_signals: int = 0
    max_open_signals: int = 5

    # --- 7-omil: QT davri (AMDX) ---
    #: Etalon coin (BTC) shamlari — davr SOATDAN emas, SHAM
    #: STRUKTURASIDAN o'qiladi (`quarterly.py`). Bo'sh bo'lsa davr
    #: aniqlanmaydi va omil neytral qoladi: soatdan davr o'ylab
    #: topilmaydi.
    reference_candles: list[Candle] = field(default_factory=list)

    @property
    def universe_size(self) -> int:
        return len(self.universe_structures)

    @property
    def structure_uptrend_ratio(self) -> float | None:
        """SMC strukturasi ko'tarilishda bo'lgan coinlar ulushi (0..1).

        FLAT ("aniq emas") maxrajda qoladi, lekin ko'tarilish deb
        sanalmaydi — noaniqlik dalil emas (0.3-band).
        """
        if not self.universe_structures:
            return None
        kotarilish = sum(
            1 for y in self.universe_structures.values() if y is TrendDirection.UP
        )
        return kotarilish / len(self.universe_structures)

    @property
    def average_adx(self) -> float | None:
        if not self.universe_adx:
            return None
        return sum(self.universe_adx.values()) / len(self.universe_adx)

    @property
    def saturation_ratio(self) -> float:
        """Faol signallar limitga qanchalik yaqin (0..1)."""
        if self.max_open_signals <= 0:
            return 1.0
        return min(1.0, self.open_signals / self.max_open_signals)
