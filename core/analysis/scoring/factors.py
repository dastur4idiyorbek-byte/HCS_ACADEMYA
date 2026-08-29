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
from core.analysis.level_types import LevelType
from core.analysis.market_structure import MarketStructure, structure_alignment
from core.analysis.support_resistance import LiquiditySweep, RangePosition, ZoneMap
from core.config.schema import (
    IndicatorConfig,
    ScoreUplift,
    ScoreWeights,
    TradeRulesConfig,
)
from core.domain.models import ScoreComponent, SignalLevels, SRZone

#: Narx zonaga shu ATR masofasidan yaqin bo'lsa — to'liq yaqinlik balli
FULL_PROXIMITY_ATR = 0.25
#: Zona shu martadan ko'p sinalgan bo'lsa — to'liq ishonch balli
FULL_TOUCHES = 5
#: Faqat Fibonacci'ga tayangan zona shu ulushda baholanadi (pivot tasdig'i yo'q)
FIBONACCI_ONLY_FACTOR = 0.5

#: Sweep "yangi" hisoblanadigan sham soni — undan keyin dalil kuchi so'nadi
SWEEP_FRESH_BARS = 10


def _uplift(base: float, evidence: float, share: float) -> float:
    """Dalilni mavjud bahoga QO'SHADI — almashtirmaydi, pasaytirmaydi.

        yangi = eski + (1 - eski) * dalil * ulush

    Ikki xossa kafolatlanadi: dalil bo'lmasa eski qiymat o'zgarmaydi,
    dalil to'liq bo'lsa ham natija 1 dan oshmaydi. Aynan shu shakl
    tufayli CryptoSpot3% qatlami ballni faqat ko'taradi va shuning
    uchun signal SONIGA ta'sir qila oladi.
    """
    dalil = min(1.0, max(0.0, evidence))
    return base + (1.0 - base) * dalil * share


def _combine(evidence: list[float]) -> float:
    """Mustaqil dalillarni birlashtiradi:  1 - (1-a)(1-b)...

    Bu — "noisy-OR": har bir dalil qolgan SHUBHANI kamaytiradi.
    Bitta kuchli dalil o'zi ham ko'p narsa aytadi, ikkitasi birga esa
    ko'proq. O'rtacha olish esa teskarisini qilardi: ikkinchi tasdiq
    birinchisini SUSAYTIRARDI, agar u sal zaifroq bo'lsa.
    """
    shubha = 1.0
    for dalil in evidence:
        shubha *= 1.0 - min(1.0, max(0.0, dalil))
    return 1.0 - shubha


def score_support_resistance(
    zone_map: ZoneMap,
    zone: SRZone,
    range_position: RangePosition | None,
    weight: float,
    level_type: LevelType = LevelType.PLAIN,
    sweep: LiquiditySweep | None = None,
    uplift: float = 0.0,
) -> ScoreComponent:
    """S/R zonasi sifati — eng og'ir omil (25 ball).

    To'rt qismdan iborat:
      1. Yaqinlik    — narx zonaga qanchalik yaqin (ATR birligida)
      2. Ishonchlilik — zona necha marta test qilingan
      3. Discount chuqurligi — narx diapazonda qanchalik pastda
      4. Tozalik     — zona pivotlarga tayanadimi yoki faqat Fibonacci'ga

    CRYPTOSPOT3% DALILLARI SHU YERGA QO'SHILADI, alohida omil sifatida
    emas. Sabab: MSNR daraja turi ham, LIT sweep'i ham AYNAN SHU ZONA
    haqidagi ma'lumot. "Yalab o'tib qaytilgan Quasimodo zonasi" —
    bu boshqa bir omil emas, bu shunchaki SIFATLIROQ S/R zonasi.

    Ular yonma-yon qo'yilsa, bitta narsa ikki joyda o'lchanardi va
    ikkalasi ham yarim kuch bilan ishlardi.
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

    # Zona SIFATI haqidagi qo'shimcha dalil: daraja turi + yalash.
    #
    # Ular BIRLASHTIRILADI, o'rtachalanmaydi. Sabab: ikkalasi ham AYNAN
    # BIR narsani tasdiqlaydi ("bu zona ishonchli"), lekin MUSTAQIL
    # manbalardan — biri tarixiy tuzilmadan, ikkinchisi hozirgi narx
    # harakatidan. Mustaqil tasdiqlar bir-birini KUCHAYTIRISHI kerak,
    # o'rtachalanib bir-birini susaytirmasligi.
    #
    # O'rtacha olinganda "Quasimodo + yangi sweep" holati "faqat
    # Quasimodo" dan deyarli farq qilmasdi — ya'ni metodikaning asosiy
    # da'vosi (naqshlar BIRGA kuchli) modelda aks etmasdi.
    dalillar: list[float] = []
    if level_type is not LevelType.PLAIN:
        dalillar.append(level_type.confidence)
        izoh += f"; {level_type.label}"
    if sweep is not None:
        yangilik = max(0.0, 1.0 - sweep.bars_since / SWEEP_FRESH_BARS)
        dalillar.append(0.6 + 0.4 * yangilik)
        izoh += f"; 🧲 {sweep.describe()}"

    if dalillar and uplift > 0:
        oldingi = xom
        xom = _uplift(xom, _combine(dalillar), uplift)
        izoh += f" [tuzilma dalili: +{(xom - oldingi) * weight:.1f} ball]"

    return ScoreComponent("support_resistance", xom * weight, weight, izoh)


#: Trend balli uchun uch qismning ulushi.
#:
#: EMA ning o'rnini SMC STRUKTURASI egalladi va u eng katta ulushni
#: oladi: struktura narxning o'z qadamlarini o'qiydi, ya'ni EMA kabi
#: kechikmaydi. Aynan shu kechikish tufayli eski tizim "arzon joydan
#: kirish" holatini past baholardi (`docs/ARXITEKTURA.md`, 58-bo'lim).
#:
#: Yuqori timeframe ham katta ulushga ega: kirish timeframedagi trend
#: qaytish paytida deyarli har doim pastga qaragan bo'ladi, katta rasm
#: esa o'sha paytda ham ko'tarilishda bo'lishi mumkin.
TREND_ULUSHLARI = {"struktura": 0.35, "adx": 0.25, "htf": 0.40}


def score_trend(
    snapshot: IndicatorSnapshot,
    confirmation: Confirmation,
    config: IndicatorConfig,
    weight: float,
    htf_alignment: float | None = None,
    structure: MarketStructure | None = None,
) -> ScoreComponent:
    """Trend kuchi — SMC strukturasi, ADX va yuqori timeframelar (20 ball).

    EMA OLIB TASHLANDI. Uning o'rnini struktura egalladi: HH/HL
    ketma-ketligi ham trendni aytadi, lekin KECHIKMASDAN. EMA200 esa
    200 shamlik o'rtacha — u tasdiqlaguncha narx Discount zonasidan
    chiqib ketardi, ya'ni "arzon paytda ol" strategiyasining o'z
    maqsadiga zid ishlardi.

    Uch qism alohida baholanadi va qo'shiladi. Yuqori timeframe
    ko'tarilishda bo'lsa, kirish timeframedagi vaqtinchalik pasayish
    ballni butunlay yo'q qilmaydi.
    """
    if structure is None:
        struktura_kuchi = 0.0
        struktura_matn = "struktura hisoblanmadi"
    else:
        struktura_kuchi = structure_alignment(structure)
        struktura_matn = structure.describe()

    # ADX trend KUCHINI o'lchaydi: chegaradan pastda — tekis bozor.
    adx_qiymati = snapshot.adx
    if adx_qiymati is None:
        adx_kuchi = 0.0
        adx_matn = "ADX hisoblanmadi"
    else:
        adx_kuchi = _taper_up(adx_qiymati, zero=config.adx_trend_threshold, full=40.0)
        adx_matn = f"ADX {adx_qiymati:.0f}"

    ulush = dict(TREND_ULUSHLARI)
    if htf_alignment is None:
        # Yuqori timeframe hisoblanmagan — uning ulushi qolgan ikkitasiga
        # taqsimlanadi. Aks holda hisoblab bo'lmagan narsa jazoga aylanardi
        # (0.3-band: noaniqlik jarima emas).
        qoshimcha = ulush.pop("htf") / 2
        ulush["struktura"] += qoshimcha
        ulush["adx"] += qoshimcha
        htf_matn = "yuqori TF hisoblanmadi"
        htf_kuchi = 0.0
    else:
        htf_kuchi = htf_alignment
        htf_matn = f"yuqori TF {htf_alignment:.0%} ko'tarilishda"

    # Pasayish strukturasi nol ball beradi, lekin JAZOLAMAYDI: qolgan
    # ikki qism o'z ulushini saqlaydi. Qat'iy rad etish kerak bo'lsa
    # `require_structure_alignment` alohida sozlama sifatida bor va
    # standart holatda o'chiq.
    xom = (
        struktura_kuchi * ulush["struktura"]
        + adx_kuchi * ulush["adx"]
        + htf_kuchi * ulush.get("htf", 0.0)
    )
    izoh = f"Trend: 🔵 {struktura_matn}, {adx_matn}, {htf_matn}"
    return ScoreComponent("trend", xom * weight, weight, izoh)


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
    htf_alignment: float | None = None,
    structure: MarketStructure | None = None,
    level_type: LevelType = LevelType.PLAIN,
    sweep: LiquiditySweep | None = None,
    uplift: ScoreUplift | None = None,
) -> list[ScoreComponent]:
    """Barcha omillarni bitta ro'yxatga yig'adi."""
    kotarish = uplift if uplift is not None else ScoreUplift(0.0, 0.0)
    return [
        score_support_resistance(
            zone_map,
            zone,
            range_position,
            weights.support_resistance,
            level_type=level_type,
            sweep=sweep,
            uplift=kotarish.support_resistance,
        ),
        score_trend(
            snapshot,
            confirmation,
            indicators,
            weights.trend,
            htf_alignment,
            structure=structure,
        ),
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
