"""3.5-band: ball omillari — har biri DARAJALI (graduated) baholanadi.

"Bor/yo'q" emas: har bir omil 0..1 oralig'ida baholanadi va vazniga
ko'paytiriladi. Sabab — ikki signal ikkalasi ham "RSI tasdiqladi" bo'lsa-yu,
biri RSI 31 dan, ikkinchisi RSI 45 dan qaytgan bo'lsa, ular bir xil ball
olmasligi kerak.

Vaznlar (`config/default.yaml` -> `scoring.weights`, jami 100):
    S/R zonasi sifati 25 | Trend 20 | RSI 15 | Hajm 15 | MACD 10 | R/R 15

S/R eng yuqori vaznga ega — 3.1-bandga mos.
"""

from __future__ import annotations

from core.analysis.indicators import Confirmation, IndicatorSnapshot
from core.analysis.support_resistance import RangePosition, ZoneMap
from core.config.schema import IndicatorConfig, ScoreWeights, TradeRulesConfig
from core.domain.models import ScoreComponent, SignalLevels, SRZone

#: Narx zonaga shu ATR masofasidan yaqin bo'lsa — to'liq yaqinlik balli
FULL_PROXIMITY_ATR = 0.25
#: Zona shu martadan ko'p sinalgan bo'lsa — to'liq ishonch balli
FULL_TOUCHES = 5
#: Faqat Fibonacci'ga tayangan zona shu ulushda baholanadi (pivot tasdig'i yo'q)
FIBONACCI_ONLY_FACTOR = 0.5


def score_support_resistance(
    zone_map: ZoneMap,
    zone: SRZone,
    range_position: RangePosition | None,
    weight: float,
) -> ScoreComponent:
    """S/R zonasi sifati — eng og'ir omil (25 ball).

    To'rt qismdan iborat:
      1. Yaqinlik    — narx zonaga qanchalik yaqin (ATR birligida)
      2. Ishonchlilik — zona necha marta test qilingan
      3. Discount chuqurligi — narx diapazonda qanchalik pastda
      4. Tozalik     — zona pivotlarga tayanadimi yoki faqat Fibonacci'ga
    """
    masofa_atr = zone_map.distance_in_atr(zone)
    yaqinlik = _taper(masofa_atr, full=FULL_PROXIMITY_ATR, zero=2.0)

    ishonch = min(1.0, zone.touches / FULL_TOUCHES)

    chuqurlik = range_position.depth if range_position and range_position.is_discount else 0.0

    tozalik = FIBONACCI_ONLY_FACTOR if zone.from_fibonacci else 1.0

    # Yaqinlik va chuqurlik eng muhim: ular "hozir kirish to'g'rimi" degan
    # savolga javob beradi. Ishonchlilik — zonaning tarixiy sifati.
    xom = (yaqinlik * 0.35 + chuqurlik * 0.35 + ishonch * 0.30) * tozalik

    izoh = (
        f"S/R: zonaga {masofa_atr:.2f} ATR masofada, {zone.touches} marta sinalgan"
        + (f", Discount chuqurligi {chuqurlik:.0%}" if chuqurlik else ", Discount emas")
        + (" (faqat Fibonacci)" if zone.from_fibonacci else "")
    )
    return ScoreComponent("support_resistance", xom * weight, weight, izoh)


def score_trend(
    snapshot: IndicatorSnapshot,
    confirmation: Confirmation,
    config: IndicatorConfig,
    weight: float,
) -> ScoreComponent:
    """Trend kuchi — EMA ajralishi va ADX birgalikda (20 ball)."""
    omil = confirmation.factor("trend")
    if omil is None or not omil.confirmed:
        return ScoreComponent(
            "trend", 0.0, weight, omil.explanation if omil else "Trend: tasdiq yo'q"
        )

    ema_kuchi = omil.strength

    # ADX trend KUCHINI o'lchaydi: chegaradan pastda — tekis bozor.
    adx_qiymati = snapshot.adx
    if adx_qiymati is None:
        adx_kuchi = 0.0
        adx_matn = "ADX hisoblanmadi"
    else:
        adx_kuchi = _taper_up(adx_qiymati, zero=config.adx_trend_threshold, full=40.0)
        adx_matn = f"ADX {adx_qiymati:.0f}"

    xom = ema_kuchi * 0.5 + adx_kuchi * 0.5
    return ScoreComponent("trend", xom * weight, weight, f"Trend: EMA muvofiq, {adx_matn}")


def score_rsi(
    snapshot: IndicatorSnapshot, confirmation: Confirmation, weight: float
) -> ScoreComponent:
    """RSI holati (15 ball). "30dan qaytish" — to'liq ball, o'rta zona — yarim."""
    omil = confirmation.factor("rsi")
    if omil is None:
        return ScoreComponent("rsi", 0.0, weight, "RSI: hisoblanmadi")
    return ScoreComponent("rsi", omil.strength * weight, weight, omil.explanation)


def score_volume(confirmation: Confirmation, weight: float) -> ScoreComponent:
    """Hajm tasdig'i (15 ball). O'rtachadan 2× — to'liq ball."""
    omil = confirmation.factor("volume")
    if omil is None:
        return ScoreComponent("volume", 0.0, weight, "Hajm: hisoblanmadi")
    return ScoreComponent("volume", omil.strength * weight, weight, omil.explanation)


def score_macd(confirmation: Confirmation, weight: float) -> ScoreComponent:
    """MACD momentum (10 ball). Yangi kesish — to'liq, mavjud holat — qisman."""
    omil = confirmation.factor("macd")
    if omil is None:
        return ScoreComponent("macd", 0.0, weight, "MACD: hisoblanmadi")
    return ScoreComponent("macd", omil.strength * weight, weight, omil.explanation)


def score_risk_reward(
    levels: SignalLevels,
    rules: TradeRulesConfig,
    weight: float,
) -> ScoreComponent:
    """Risk/Reward sifati (15 ball).

    Minimal talab (1:3) — yarim ball. Undan yuqorisi qo'shimcha ball beradi,
    lekin 1:6 dan keyin to'yinadi: haddan tashqari uzoq TP amalda kamdan-kam
    ishlaydi.
    """
    rr = levels.risk_reward_tp2
    minimal = rules.min_risk_reward

    if rr < minimal:
        return ScoreComponent(
            "risk_reward", 0.0, weight, f"R/R 1:{rr:.1f} — minimal 1:{minimal:.0f} dan past"
        )

    ortiqcha = _taper_up(rr, zero=minimal, full=minimal * 2)
    xom = 0.5 + 0.5 * ortiqcha
    return ScoreComponent("risk_reward", xom * weight, weight, f"R/R 1:{rr:.1f}")


def build_components(
    zone_map: ZoneMap,
    zone: SRZone,
    range_position: RangePosition | None,
    snapshot: IndicatorSnapshot,
    confirmation: Confirmation,
    levels: SignalLevels,
    weights: ScoreWeights,
    indicators: IndicatorConfig,
    rules: TradeRulesConfig,
) -> list[ScoreComponent]:
    """Barcha omillarni bitta ro'yxatga yig'adi."""
    return [
        score_support_resistance(zone_map, zone, range_position, weights.support_resistance),
        score_trend(snapshot, confirmation, indicators, weights.trend),
        score_rsi(snapshot, confirmation, weights.rsi),
        score_volume(confirmation, weights.volume),
        score_macd(confirmation, weights.macd),
        score_risk_reward(levels, rules, weights.risk_reward),
    ]


# --------------------------------------------------------------------------- #
#  Yordamchi funksiyalar
# --------------------------------------------------------------------------- #


def _taper(value: float, full: float, zero: float) -> float:
    """Kichik qiymat yaxshi: `full` va undan past — 1.0, `zero` va undan yuqori — 0.0."""
    if value <= full:
        return 1.0
    if value >= zero:
        return 0.0
    return (zero - value) / (zero - full)


def _taper_up(value: float, zero: float, full: float) -> float:
    """Katta qiymat yaxshi: `zero` va undan past — 0.0, `full` va undan yuqori — 1.0."""
    if value <= zero:
        return 0.0
    if value >= full:
        return 1.0
    return (value - zero) / (full - zero)
