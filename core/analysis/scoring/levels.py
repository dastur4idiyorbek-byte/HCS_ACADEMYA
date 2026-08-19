"""Stop va TP darajalarini qurish (3.1 va 3.3-band birgalikda).

3.1-band tuzilmani belgilaydi:
    Stop — eng yaqin support/ATR asosida
    TP1  — eng yaqin resistance
    TP2  — kamida 1:3 R/R ta'minlaydigan masofa

3.3-band esa qat'iy chegaralar qo'yadi:
    Stop masofasi narxning 1%idan oshmasligi shart
    TP 3%–5% oralig'ida bo'lishi shart

Bu ikkisi tez-tez ZIDDIYATGA kiradi: haqiqiy support 1% dan uzoqroqda
bo'lishi mumkin, yoki eng yaqin resistance 3% dan yaqinroqda. Bunday
holatda daraja "majburlab" qurilmaydi — signal umuman berilmaydi
(0.2-band: "signal bermaslik normal holat").

Shuning uchun `build_levels()` sababni ham qaytaradi: admin nima uchun
signal chiqmaganini ko'ra olishi kerak (3.7-band dashboardi).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.support_resistance import ZoneMap
from core.config.schema import TradeRulesConfig
from core.domain.models import SignalLevels

#: Stop support zonasining pastidan shu ulushdagi ATR masofasida qo'yiladi.
#: Aynan chegaraga qo'yilsa, zonaga tegib qaytish ham Stop'ni ishga tushirardi.
STOP_BUFFER_ATR = 0.25


@dataclass(frozen=True, slots=True)
class LevelResult:
    """Darajalarni qurish natijasi.

    `levels is None` — qurib bo'lmadi, sababi `reason` da.
    """

    levels: SignalLevels | None
    reason: str
    #: TP1 haqiqiy resistance zonasidan olinganmi (tuzilmaviy) yoki
    #: o'lchangan masofadan (qarshilik topilmaganda). Bu farq signal
    #: tafsilotida ko'rsatiladi — 3.6-band shaffofligi.
    tp_from_structure: bool = True

    @property
    def ok(self) -> bool:
        return self.levels is not None


def build_levels(
    zone_map: ZoneMap,
    rules: TradeRulesConfig,
    entry_price: float | None = None,
) -> LevelResult:
    """S/R zonalari va ATR asosida Entry/Stop/TP1/TP2 quradi.

    Args:
        zone_map: aniqlangan zonalar (6-bosqich).
        rules: 3.3-banddagi universal chegaralar.
        entry_price: kirish narxi. Berilmasa joriy narx ishlatiladi.
    """
    entry = entry_price if entry_price is not None else zone_map.price
    if entry <= 0:
        return LevelResult(None, "Kirish narxi musbat bo'lishi kerak")

    support = zone_map.nearest_support()
    if support is None:
        return LevelResult(None, "Narxdan pastda support zonasi topilmadi")

    stop_natija = _build_stop(entry, support.low, zone_map.atr, rules)
    if stop_natija is None:
        masofa = (entry - support.low) / entry * 100
        return LevelResult(
            None,
            f"Support zonasi juda uzoq: Stop {masofa:.2f}% da qolardi, "
            f"chegara {rules.max_stop_distance_pct}%",
        )
    stop = stop_natija
    stop_masofa_pct = (entry - stop) / entry * 100

    tp1_natija = _build_tp1(entry, zone_map, rules)
    tuzilmaviy_tp = tp1_natija is not None

    if tp1_natija is None:
        if not rules.allow_measured_tp:
            return LevelResult(
                None,
                f"Mos resistance topilmadi: TP1 {rules.min_tp_distance_pct}–"
                f"{rules.max_tp_distance_pct}% oralig'ida bo'lishi kerak",
                tp_from_structure=False,
            )
        # Toza ko'tarilish trendida ustda qarshilik bo'lmaydi — TP1
        # o'lchangan masofa bo'yicha qo'yiladi.
        tp1_natija = entry * (1 + rules.min_tp_distance_pct / 100)
    tp1 = tp1_natija

    tp2_natija = _build_tp2(entry, tp1, stop_masofa_pct, rules)
    if tp2_natija is None:
        kerak = rules.min_risk_reward * stop_masofa_pct
        return LevelResult(
            None,
            f"1:{rules.min_risk_reward:.0f} R/R uchun TP2 {kerak:.2f}% da bo'lishi kerak, "
            f"lekin chegara {rules.max_tp_distance_pct}%",
            tp_from_structure=tuzilmaviy_tp,
        )
    tp2 = tp2_natija

    try:
        levels = SignalLevels(entry=entry, stop=stop, tp1=tp1, tp2=tp2)
    except ValueError as exc:
        return LevelResult(None, f"Darajalar tartibi buzildi: {exc}", tuzilmaviy_tp)

    izoh = (
        "Darajalar S/R va ATR asosida qurildi"
        if tuzilmaviy_tp
        else "Stop S/R asosida; TP ustda qarshilik yo'qligi sababli o'lchangan masofa bo'yicha"
    )
    return LevelResult(levels, izoh, tp_from_structure=tuzilmaviy_tp)


def _build_stop(
    entry: float,
    support_low: float,
    atr: float,
    rules: TradeRulesConfig,
) -> float | None:
    """Stop support zonasidan pastda, lekin chegaradan uzoq bo'lmasligi kerak."""
    tuzilmaviy = support_low - atr * STOP_BUFFER_ATR
    eng_past_ruxsat = entry * (1 - rules.max_stop_distance_pct / 100)

    if tuzilmaviy <= 0:
        return None
    # Tuzilmaviy Stop chegaradan uzoqda bo'lsa — signal berilmaydi.
    # Uni sun'iy ravishda yaqinlashtirish support zonasi ichida Stop qo'yish
    # demakdir: narx zonaga tegib qaytsa ham Stop ishga tushardi.
    if tuzilmaviy < eng_past_ruxsat:
        return None
    return tuzilmaviy if tuzilmaviy < entry else None


def _build_tp1(entry: float, zone_map: ZoneMap, rules: TradeRulesConfig) -> float | None:
    """TP1 — eng yaqin resistance, 3.3-band oralig'iga tushishi shart."""
    eng_past = entry * (1 + rules.min_tp_distance_pct / 100)
    eng_baland = entry * (1 + rules.max_tp_distance_pct / 100)

    for zona in zone_map.resistances:
        # Zonaning PASTKI chegarasi — narx u yerga yetganda sotish boshlanadi
        nishon = zona.low
        if eng_past <= nishon <= eng_baland:
            return nishon

    return None


def _build_tp2(
    entry: float,
    tp1: float,
    stop_distance_pct: float,
    rules: TradeRulesConfig,
) -> float | None:
    """TP2 — kamida 1:N R/R, lekin 3.3-band oralig'idan chiqmasdan."""
    kerakli_pct = stop_distance_pct * rules.min_risk_reward
    nishon = entry * (1 + kerakli_pct / 100)
    eng_baland = entry * (1 + rules.max_tp_distance_pct / 100)

    if nishon > eng_baland:
        return None
    # TP2 TP1 dan yuqori bo'lishi shart
    if nishon <= tp1:
        nishon = tp1 * 1.001
        if nishon > eng_baland:
            return None
    return nishon
