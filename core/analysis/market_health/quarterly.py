"""QT — Quarterly Theory (AMDX), CryptoSpot3% metodikasining 5-qismi.

Katta vaqt oralig'i to'rtga bo'linadi:

    A  Accumulation   — yig'ish, tor diapazon
    M  Manipulation   — yolg'on harakat, likvidlik yig'ib olinadi
    D  Distribution   — asosiy harakat
    X  Continuation   — tasdiqlanish va davom etish

DAVR SOATGA EMAS, SHAM STRUKTURASIGA BOG'LANGAN
------------------------------------------------
Ilgari sutka UTC bo'yicha to'rt olti soatlik chorakka bo'linardi va
davr bozor holatidan QAT'I NAZAR har kuni bir xil ritmda o'zgarardi.
Bu — o'lchanmagan taxmin edi: soat 13:00 bo'lgani "hozir asosiy
harakat davri" degani emas.

Endi davr NARX HARAKATIDAN o'qiladi:

    A  tor diapazon, sokinlik           — hech narsa buzilmagan
    M  likvidlik yig'ib olindi (sweep)  — yolg'on harakat bo'ldi
    D  struktura buzildi (BOS)          — asosiy harakat ketyapti
    X  buzilishdan keyin narx ushlab    — tasdiqlangan davom etish
       turibdi

Aniqlab bo'lmasa `None` qaytadi va omil NEYTRAL bo'ladi — soatdan
davr "o'ylab topilmaydi".

VAZN BARIBIR KICHIK (5). Loyihada bashorat kuchi o'lchanmagan
ko'rsatkichga katta vazn berish allaqachon zarar keltirgan (BTC
Dominance — `docs/ARXITEKTURA.md`, 33- va 57-bo'limlar). Struktura
asosidagi davr ham backtest bilan tasdiqlanmaguncha shu vaznda
qoladi.
"""

from __future__ import annotations

from enum import Enum

from core.analysis.market_structure import analyze_structure
from core.domain.enums import TrendDirection
from core.domain.models import Candle

#: AMDX nechta davrdan iborat
QUARTERS = 4


class QuarterPhase(str, Enum):
    """AMDX davri."""

    ACCUMULATION = "A"
    MANIPULATION = "M"
    DISTRIBUTION = "D"
    CONTINUATION = "X"

    @property
    def score(self) -> float:
        """Davr uchun ball ulushi (0..1) — BOSHLANG'ICH qiymatlar.

        Mantiq: X (tasdiqlanish) — eng ishonchli davr, M (manipulyatsiya)
        — eng xavflisi, chunki aynan o'sha yerda yolg'on harakatlar
        bo'ladi. A va D orasida.
        """
        return {"A": 0.75, "M": 0.25, "D": 0.5, "X": 1.0}[self.value]

    @property
    def label(self) -> str:
        return {
            "A": "A (Accumulation) — yig'ish davri",
            "M": "M (Manipulation) — yolg'on harakat davri",
            "D": "D (Distribution) — asosiy harakat davri",
            "X": "X (Continuation) — tasdiqlanish va davom etish",
        }[self.value]

    @property
    def next_phase(self) -> QuarterPhase:
        tartib = list(QuarterPhase)
        return tartib[(tartib.index(self) + 1) % QUARTERS]


def quarterly_phase(
    candles: list[Candle],
    lookback: int = 40,
    recent_bars: int = 6,
    quiet_ratio: float = 0.6,
) -> QuarterPhase | None:
    """Sham strukturasidan AMDX davrini o'qiydi.

    Hodisalar ENG YANGISI bo'yicha tanlanadi: sweep dan keyin BOS
    bo'lgan bo'lsa, davr D (yoki X), aksincha bo'lsa M.

    Args:
        candles: eng eskisidan eng yangisiga.
        lookback: qancha sham ko'riladi.
        recent_bars: "yaqinda" deb hisoblanadigan oxirgi shamlar soni.
        quiet_ratio: so'nggi diapazon oldingisidan shuncha marta kichik
            bo'lsa — sokinlik (A davri).

    Returns:
        Davr, yoki `None` — aniqlab bo'lmadi (omil neytral qoladi).
    """
    oyna = candles[-lookback:] if lookback > 0 else candles
    if len(oyna) < recent_bars * 2:
        return None

    struktura = analyze_structure(oyna)
    songgi = oyna[-recent_bars:]
    oldingi = oyna[:-recent_bars]

    # --- BOS: struktura buzildimi va qachon ---
    bos = struktura.last_bos
    bos_yaqin = bos is not None and bos.index >= len(oyna) - recent_bars

    # --- Sweep: oldingi tubdan pastga tushib, ichkariga QAYTGAN ---
    oldingi_tub = min(s.low for s in oldingi)
    sweep = any(
        s.low < oldingi_tub and s.close > oldingi_tub for s in songgi
    )

    if bos is not None and not bos_yaqin and struktura.direction is TrendDirection.UP:
        # Buzilish bo'lgan, narx undan keyin ham ushlab turibdi
        return QuarterPhase.CONTINUATION
    if bos_yaqin:
        return QuarterPhase.DISTRIBUTION
    if sweep:
        return QuarterPhase.MANIPULATION

    # --- Sokinlik: so'nggi diapazon oldingisidan sezilarli kichik ---
    songgi_diapazon = max(s.high for s in songgi) - min(s.low for s in songgi)
    oldingi_diapazon = max(s.high for s in oldingi) - min(s.low for s in oldingi)
    if oldingi_diapazon > 0 and songgi_diapazon <= oldingi_diapazon * quiet_ratio:
        return QuarterPhase.ACCUMULATION

    # Hech biri emas — DAVR O'YLAB TOPILMAYDI.
    return None


def describe_phase(candles: list[Candle]) -> str:
    """Saytdagi shkala ostida ko'rsatiladigan bir qatorli matn."""
    davr = quarterly_phase(candles)
    if davr is None:
        return "Davr aniqlanmadi — narx harakati hali bir ma'no bermayapti"
    return f"{davr.label}; keyingisi — {davr.next_phase.value}"
