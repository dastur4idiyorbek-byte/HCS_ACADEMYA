"""Tasdiqlash qatlami — indikatorlar S/R zonasini tasdiqlaydimi.

3.1-banddagi TO'G'RI TARTIB shu yerda amalga oshadi:

    1. AVVAL: narx muhim S/R zonasida va Discount zonadami  (6-bosqich)
    2. KEYIN: indikatorlar shu holatni tasdiqlaydimi           (shu modul)
    3. Faqat ikkalasi ham "ha" bo'lsa signal ko'rib chiqiladi

Shuning uchun `confirm()` funksiyasi S/R holatini KIRUVCHI shart sifatida
oladi. Indikatorlar o'zicha "signal bor" deb ayta olmaydi — bu ataylab
shunday tuzilgan.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.indicators.snapshot import IndicatorSnapshot
from core.config.schema import IndicatorConfig
from core.domain.enums import TrendDirection


@dataclass(frozen=True, slots=True)
class ConfirmationFactor:
    """Bitta tasdiqlovchi omil."""

    name: str
    confirmed: bool
    strength: float          # 0..1 — darajali baho (3.5-band "bor/yo'q" emas)
    explanation: str


@dataclass(frozen=True, slots=True)
class Confirmation:
    """Indikatorlarning umumiy hukmi.

    `zone_ready` — S/R qatlami "narx kerakli zonada" deganmi. Agar yo'q
    bo'lsa, indikatorlar qanchalik yaxshi bo'lmasin, `is_confirmed` `False`
    bo'ladi.
    """

    zone_ready: bool
    factors: list[ConfirmationFactor]
    #: Nechta omil tasdiqlashi shart. 4 — qat'iy "hammasi" varianti.
    min_confirmations: int = 2

    @property
    def is_confirmed(self) -> bool:
        """Signal ko'rib chiqilishi uchun shartlar.

        1. Zona tayyor (S/R + Discount) — MAJBURIY, bu chetlab o'tilmaydi
        2. Kamida `min_confirmations` ta indikator tasdiqlagan

        Nima uchun "hammasi" emas: MACD kechikuvchi indikator — u faqat narx
        ko'tarilgandan keyin tasdiqlaydi, o'sha paytda narx Discount
        zonasidan chiqib ketgan bo'ladi. 4/4 talabi bilan ikki oyna
        kesishmaydi va tizim amalda hech qachon signal bermaydi (o'lchangan).

        Qolgan tanlovni 3.5-banddagi ball chegarasi qiladi — u aynan shu
        uchun mo'ljallangan.
        """
        return self.zone_ready and self.confirmed_count >= self.min_confirmations

    @property
    def confirmed_count(self) -> int:
        return sum(1 for omil in self.factors if omil.confirmed)

    def factor(self, name: str) -> ConfirmationFactor | None:
        for omil in self.factors:
            if omil.name == name:
                return omil
        return None

    def describe(self) -> str:
        """3.6-band: "Nega bu signal?" tugmasi uchun matn."""
        qatorlar = [
            f"{'✅' if omil.confirmed else '❌'} {omil.explanation}" for omil in self.factors
        ]
        if not self.zone_ready:
            qatorlar.insert(0, "❌ Narx kerakli S/R zonasida emas (Discount sharti bajarilmadi)")
        return "\n".join(qatorlar)


def confirm(
    snapshot: IndicatorSnapshot,
    config: IndicatorConfig,
    zone_ready: bool,
) -> Confirmation:
    """Indikatorlar S/R holatini tasdiqlaydimi.

    Args:
        snapshot: indikator qiymatlari.
        config: chegaralar (RSI, ADX va h.k.).
        zone_ready: S/R qatlamining hukmi — narx kerakli zonada va
            Discount'dami (`ZoneMap.entry_allowed()`).
    """
    return Confirmation(
        zone_ready=zone_ready,
        factors=[
            _trend_factor(snapshot, config),
            _rsi_factor(snapshot, config),
            _macd_factor(snapshot),
            _volume_factor(snapshot),
        ],
        min_confirmations=config.min_confirmations,
    )


def _trend_factor(snapshot: IndicatorSnapshot, config: IndicatorConfig) -> ConfirmationFactor:
    """3.1-band: narx ikkala EMA'dan yuqori VA EMA50 > EMA200."""
    if snapshot.ema_fast is None or snapshot.ema_slow is None:
        return ConfirmationFactor(
            "trend", False, 0.0, "Trend: EMA hisoblanmadi — ma'lumot yetarli emas"
        )

    yonalish = snapshot.trend
    tasdiq = yonalish is TrendDirection.UP

    # Kuch: EMA'lar orasidagi farq ATR birligida. Nima uchun ATR, foiz emas:
    # EMA50 va EMA200 orasidagi masofa timeframega bog'liq — 15 daqiqalik
    # grafikda 0.2%, kunlikda 15%. Bitta foiz chegarasi ikkalasiga ham mos
    # kelmaydi va past timeframeda bu omil doim nolga yaqin bo'lib qolardi
    # (o'lchov: docs/ARXITEKTURA.md, 28-bo'lim). ATR volatillikni o'zi
    # hisobga oladi, shuning uchun o'lchov timeframedan mustaqil bo'ladi.
    if not tasdiq:
        kuch = 0.0
    elif snapshot.atr is None or snapshot.atr <= 0:
        # ATR yo'q — kuchni o'lchab bo'lmaydi. Yo'nalish tasdiqlangan, lekin
        # qo'shimcha ball berilmaydi (0.3-band: noaniqlikda kamroq).
        kuch = 0.0
    else:
        ajralish_atr = abs(snapshot.ema_fast - snapshot.ema_slow) / snapshot.atr
        kuch = min(1.0, ajralish_atr / config.ema_separation_full_atr)

    izoh = (
        f"Trend: narx ikkala EMA'dan yuqori, tez EMA sekinidan baland "
        f"({snapshot.ema_fast:.4g} > {snapshot.ema_slow:.4g})"
        if tasdiq
        else f"Trend: ko'tarilish tasdiqlanmadi ({yonalish.value})"
    )
    return ConfirmationFactor("trend", tasdiq, kuch, izoh)


def _rsi_factor(snapshot: IndicatorSnapshot, config: IndicatorConfig) -> ConfirmationFactor:
    """3.1-band: RSI 30dan QAYTISH (unda turish emas)."""
    if snapshot.rsi is None:
        return ConfirmationFactor("rsi", False, 0.0, "RSI: hisoblanmadi")

    if snapshot.rsi >= config.rsi_overbought:
        return ConfirmationFactor(
            "rsi",
            False,
            0.0,
            f"RSI: haddan tashqari sotib olingan ({snapshot.rsi:.0f}) — kirish uchun kech",
        )

    if snapshot.rsi_recovering:
        return ConfirmationFactor(
            "rsi",
            True,
            1.0,
            f"RSI: {config.rsi_oversold:.0f} dan qaytmoqda "
            f"(hozir {snapshot.rsi:.0f}) — kuchli tasdiq",
        )

    # Qaytish bo'lmasa ham, RSI o'rta zonada bo'lsa zaif tasdiq beriladi:
    # narx o'sishga joy bor.
    ortada = config.rsi_oversold <= snapshot.rsi < 55
    kuch = 0.5 if ortada else 0.0
    izoh = "o'rta zonada, o'sishga joy bor" if ortada else "tasdiq yo'q"
    return ConfirmationFactor("rsi", ortada, kuch, f"RSI: {snapshot.rsi:.0f} — {izoh}")


def _macd_factor(snapshot: IndicatorSnapshot) -> ConfirmationFactor:
    """3.1-band: MACD signal chiziqni PASTDAN kesib o'tish."""
    natija = snapshot.macd
    if natija is None:
        return ConfirmationFactor("macd", False, 0.0, "MACD: hisoblanmadi")

    if natija.bullish_cross:
        return ConfirmationFactor(
            "macd", True, 1.0, "MACD: signal chiziqni pastdan kesib o'tdi — kuchli tasdiq"
        )
    if natija.is_bullish:
        return ConfirmationFactor(
            "macd", True, 0.6, "MACD: signal chiziqdan yuqorida (kesish oldinroq bo'lgan)"
        )
    izoh = (
        "MACD: momentum musbat, lekin signal chiziqdan pastda — sekinlashmoqda"
        if natija.above_zero
        else "MACD: signal chiziqdan pastda — tasdiq yo'q"
    )
    return ConfirmationFactor("macd", False, 0.0, izoh)


def _volume_factor(snapshot: IndicatorSnapshot) -> ConfirmationFactor:
    """3.1-band: hajm so'nggi 20 sham o'rtachasidan yuqori."""
    nisbat = snapshot.volume_ratio
    if nisbat is None:
        return ConfirmationFactor("volume", False, 0.0, "Hajm: hisoblanmadi")

    tasdiq = nisbat >= 1.0
    # 2× o'rtacha — to'liq kuch. Undan yuqorisi qo'shimcha ball bermaydi.
    kuch = min(1.0, (nisbat - 1.0)) if tasdiq else 0.0
    return ConfirmationFactor(
        "volume",
        tasdiq,
        kuch,
        f"Hajm: o'rtachadan {nisbat:.1f}× "
        f"({'yuqori' if tasdiq else 'past — harakat zaif'})",
    )
