"""3.10-band: Correction Entry — bozor pasayganda ishlaydigan kirish.

MUAMMO (jonli o'lchov, `bozor_salomatligi_asosiy_tuzatish.md`). Bozor
Salomatligi past bo'lgan payt — narxlar ARZONLASHGAN payt, ya'ni
"arzon ol" strategiyasi uchun eng qulay lahza. Eski tizim esa aynan
shunda coinlarni umuman tahlil qilmasdi (`cycle.py`), indeks qayta
ko'tarilganda — narx allaqachon o'sib bo'lgach — signal berardi.
Natijada tizim narxning eng yaxshi emas, eng YOMON nuqtasini tanlardi.

YECHIM: pasayishda ham qaraymiz, lekin FAQAT tuzilma ruxsat bergan
joyda. Zanjir qat'iy:

    1. Yo'nalish darvozasi  — kunlik TF ko'tarilishda bo'lishi SHART
    2. Impuls               — qayerdan qayerga ko'tarilgan
    3. Korreksiya zonasi    — Fibonacci "oltin zona" + OB + FVG
    4. Confluence           — kamida IKKI turli manba bir joyda
    5. Pastki TF tasdig'i   — aniq nuqta 15m da tasdiqlanadi
    6. Darajalar            — Entry zona ichida, Stop uning tashqi chekkasida

ASOSIY FARQ `classic_ta` DAN: u S/R zonasiga tayanadi va Stopni ATR
bilan qo'yadi. Bu yerda ENTRY ham, STOP ham BIR XIL strukturaviy
manbadan chiqadi — biri qat'iy foiz, ikkinchisi struktura bo'lib
qolmaydi.

QAT'IY DARVOZA — YO'NALISH. Tushayotgan bozorda "arzon" degan narsa
yo'q: narx yana ham arzonlashaveradi. Spot xaridida bu eng qimmat
xato, shuning uchun u YAGONA murosasiz shart.

Bu modul SOF: tarmoqqa ham, bazaga ham murojaat qilmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.indicators.momentum import rsi, rsi_recovering_from_oversold
from core.analysis.indicators.trend import closes
from core.analysis.market_structure import analyze_structure
from core.analysis.smc import (
    Confluence,
    StructureZone,
    fibonacci_zone,
    find_bullish_fvgs,
    find_bullish_order_blocks,
    find_confluences,
    find_impulse,
)
from core.analysis.strategies.base import Strategy, StrategyInput
from core.config.schema import AppConfig
from core.domain.enums import SignalSource, TrendDirection
from core.domain.models import Candle, ScoreBreakdown, ScoreComponent, SignalCandidate, SignalLevels
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RejectionReason:
    """Nomzod nima uchun rad etildi — dashboard va postmortem uchun."""

    stage: str
    detail: str


@dataclass(frozen=True, slots=True)
class EntryPlan:
    """Tuzilmadan chiqarilgan kirish rejasi."""

    entry: float
    stop: float
    confluence: Confluence
    #: Pastki TF tasdig'i topilganmi
    confirmed: bool
    #: Korreksiya impulsning necha ulushiga qaytgan
    retracement: float | None


class CorrectionEntryStrategy(Strategy):
    """Korreksiya tugashini kutib, tuzilmaviy kirish nuqtasini qidiradi."""

    name = "correction_entry"

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._last_rejection: RejectionReason | None = None

    @property
    def enabled(self) -> bool:
        return self._config.strategies.correction_entry.enabled

    def required_timeframes(self) -> list[str]:
        c = self._config.strategies.correction_entry
        # Takrorlanmasin: uchtasi bir xil bo'lishi ham mumkin
        return list(dict.fromkeys([c.trend_timeframe, c.zone_timeframe, c.confirm_timeframe]))

    @property
    def last_rejection(self) -> RejectionReason | None:
        return self._last_rejection

    # ------------------------------------------------------------------ #

    def analyze(self, data: StrategyInput) -> SignalCandidate | None:
        self._last_rejection = None
        c = self._config.strategies.correction_entry

        if not data.halal_verdict.is_tradable:
            return self._reject("halal", f"{data.symbol}: {data.halal_verdict.reason}")

        zona_shamlar = data.series(c.zone_timeframe)
        trend_shamlar = data.series(c.trend_timeframe)
        if len(zona_shamlar) < 10 or len(trend_shamlar) < 5:
            return self._reject(
                "data",
                f"Sham yetarli emas ({c.zone_timeframe}: {len(zona_shamlar)}, "
                f"{c.trend_timeframe}: {len(trend_shamlar)})",
            )

        # 1) YO'NALISH DARVOZASI — yagona murosasiz shart.
        #
        # Tushayotgan bozorda korreksiya YUQORIGA bo'ladi va undan
        # keyin narx YANA PASTGA ketadi. Spot xaridida bunga kirish —
        # tushayotgan pichoqni ushlash.
        struktura = analyze_structure(
            trend_shamlar,
            self._config.analysis.market_structure.swing_lookback,
            self._config.analysis.market_structure.min_swings,
            self._config.analysis.market_structure.fallback_min_pct,
        )
        if struktura.direction is not TrendDirection.UP:
            return self._reject(
                "trend",
                f"{c.trend_timeframe} ko'tarilishda emas ({struktura.describe()}) — "
                "pasayishdagi korreksiya spot xaridi uchun tuzoq",
            )

        # 2) Impuls — qayerdan qayerga ko'tarilgan
        impuls = find_impulse(zona_shamlar, c.impulse_lookback)
        if impuls is None:
            return self._reject("impulse", "Ko'tarilish impulsi topilmadi")

        narx = zona_shamlar[-1].close
        if narx >= impuls.high:
            return self._reject(
                "retracement",
                f"Narx ({narx:.6g}) hali korreksiyaga tushmagan — "
                f"impuls cho'qqisi {impuls.high:.6g}",
            )

        # 3) Zonalar: Fibonacci + Order Block + FVG
        zonalar: list[StructureZone] = []
        fib = fibonacci_zone(impuls, c.fib_ratios)
        if fib is not None:
            zonalar.append(fib)
        zonalar.extend(
            find_bullish_order_blocks(
                zona_shamlar, c.impulse_lookback, c.ob_min_move_pct
            )
        )
        zonalar.extend(
            find_bullish_fvgs(zona_shamlar, c.impulse_lookback, c.fvg_min_gap_pct)
        )

        # 4) Confluence — kamida ikki TURLI manba bir joyda.
        #
        # "Eng ko'p ball beruvchi usulni tanlash" emas: beshta usuldan
        # bittasi har doim mos keladi va bu tarixga moslashib qolish
        # bo'lardi. Ikki mustaqil manbaning bir joyda uchrashuvi esa
        # tasodif bo'lish ehtimoli ancha past.
        nomzodlar = [
            k
            for k in find_confluences(zonalar)
            if k.strength >= c.min_confluence and k.low > 0
        ]
        if not nomzodlar:
            return self._reject(
                "confluence",
                f"Kamida {c.min_confluence} ta turli manba bir joyga tushmadi "
                f"({len(zonalar)} ta zona ko'rildi)",
            )

        # Narx zonaga YETIB KELGAN bo'lishi kerak — bo'lmasa bu hali
        # reja, kirish emas.
        yaqin = [k for k in nomzodlar if k.low <= narx <= k.high]
        if not yaqin:
            eng = nomzodlar[0]
            return self._reject(
                "zone_position",
                f"Narx ({narx:.6g}) kirish zonasiga yetmagan "
                f"({eng.low:.6g}-{eng.high:.6g})",
            )
        tanlangan = yaqin[0]

        # 5) PASTKI TF TASDIG'I — zona katta, nuqta aniq bo'lishi kerak
        tasdiq = self._confirm(data, tanlangan)
        if not tasdiq:
            return self._reject(
                "confirm",
                f"{c.confirm_timeframe} da zona ichida qaytish belgisi yo'q — "
                "kirish hali erta",
            )

        # 6) Darajalar: Entry va Stop BIR XIL zonadan
        reja = EntryPlan(
            entry=narx,
            # Stop zonaning QUYI chekkasidan sal pastda: zona buzilsa,
            # uni yaratgan tuzilma ham buzilgan va kirish sababi qolmaydi.
            stop=tanlangan.low * (1 - c.stop_buffer_pct / 100),
            confluence=tanlangan,
            confirmed=True,
            retracement=impuls.retracement_ratio(narx),
        )
        # 6a) STOP MASOFASI XAVFSIZLIK ORALIG'IDAMI.
        #
        # Stop TUZILMADAN chiqadi — bu tamoyil o'zgarmaydi. Lekin
        # tuzilma juda tor bo'lib qolishi mumkin: ikki zonaning
        # kesishmasi 0.5% bo'lsa, Stop shuncha yaqin turadi va uni
        # oddiy bozor shovqini yeb qo'yadi. Bunday holatda Stopni
        # KENGAYTIRMAYMIZ (kengaytirilgan Stop endi hech narsani
        # anglatmaydi) — nomzodni rad etamiz.
        qoidalar = self._config.trade_rules
        stop_pct = (reja.entry - reja.stop) / reja.entry * 100
        if stop_pct < qoidalar.min_stop_distance_pct:
            return self._reject(
                "levels:stop_too_close",
                f"Tuzilmaviy Stop juda yaqin ({stop_pct:.2f}% < "
                f"{qoidalar.min_stop_distance_pct}%) — bu masofani bozor "
                "shovqini yeb qo'yadi",
            )
        if stop_pct > qoidalar.max_stop_distance_pct:
            return self._reject(
                "levels:stop_too_far",
                f"Tuzilmaviy Stop juda uzoq ({stop_pct:.2f}% > "
                f"{qoidalar.max_stop_distance_pct}%) — pozitsiya juda kichrayadi",
            )

        darajalar = self._levels(reja, impuls)
        if darajalar is None:
            return self._reject(
                "levels",
                f"1:{c.min_risk_reward} nisbat uchun joy yetmadi "
                f"(Stop {reja.entry - reja.stop:.6g}, cho'qqi {impuls.high:.6g})",
            )

        tafsilot = self._score(data.symbol, reja, impuls, zona_shamlar)
        logger.info(
            "Correction Entry nomzodi: %s ball=%.1f zona=%s (%s) qaytish=%.0f%%",
            data.symbol,
            tafsilot.total,
            f"{tanlangan.low:.6g}-{tanlangan.high:.6g}",
            tanlangan.describe(),
            (reja.retracement or 0) * 100,
        )
        return SignalCandidate(
            symbol=data.symbol,
            levels=darajalar,
            source=SignalSource.CORRECTION_ENTRY,
            breakdown=tafsilot,
            halal_verdict=data.halal_verdict,
        )

    # ------------------------------------------------------------------ #

    def _confirm(self, data: StrategyInput, zone: Confluence) -> bool:
        """Pastki TF da zona ichida qaytish belgisi bormi.

        Yuqori TF zonasi KATTA bo'lishi mumkin (4 soatlik shamda u
        narxning bir necha foizini qamrab oladi). Kirish o'sha
        zonaning istalgan joyida emas, narx qaytishni BOSHLAGAN aniq
        nuqtada bo'lishi kerak.

        Belgi: pastki TF da zona ichida mini Order Block yoki FVG
        paydo bo'lgan — ya'ni o'sha yerda xarid bosimi ko'ringan.
        """
        c = self._config.strategies.correction_entry
        shamlar = data.series(c.confirm_timeframe)
        if len(shamlar) < 5:
            # Pastki TF ma'lumoti yo'q — tasdiq ham yo'q. Noaniqlikda
            # kirmaymiz (0.3-band).
            return False

        oyna = shamlar[-c.confirm_lookback :]
        mayda = [
            *find_bullish_order_blocks(oyna, c.confirm_lookback, c.ob_min_move_pct / 2),
            *find_bullish_fvgs(oyna, c.confirm_lookback, c.fvg_min_gap_pct / 2),
        ]
        return any(z.low <= zone.high and zone.low <= z.high for z in mayda)

    def _levels(self, plan: EntryPlan, impulse) -> SignalLevels | None:  # noqa: ANN001
        """TP — impuls cho'qqisi tomon; nisbat tekshiriladi.

        TP ham TUZILMADAN: korreksiya tugagach narx odatda avvalgi
        cho'qqini qayta sinaydi. TP2 shu yerda, TP1 esa yo'lning
        yarmida.
        """
        c = self._config.strategies.correction_entry
        xavf = plan.entry - plan.stop
        if xavf <= 0:
            return None

        tp2 = impulse.high
        foyda = tp2 - plan.entry
        if foyda <= 0 or foyda / xavf < c.min_risk_reward:
            return None

        tp1 = plan.entry + foyda / 2
        try:
            return SignalLevels(entry=plan.entry, stop=plan.stop, tp1=tp1, tp2=tp2)
        except ValueError:
            return None

    def _score(
        self, symbol: str, plan: EntryPlan, impulse, candles: list[Candle]  # noqa: ANN001
    ) -> ScoreBreakdown:
        """Ball — confluence kuchi, korreksiya chuqurligi va RSI.

        Vaznlar `classic_ta` nikidan ALOHIDA: bu yerda S/R zonasi ham,
        MACD ham yo'q. Ular BOSHLANG'ICH qiymatlar va backtest bilan
        tasdiqlanishi kerak.
        """
        c = self._config.strategies.correction_entry
        qismlar: list[ScoreComponent] = []

        # 1) Confluence kuchi (40) — nechta mustaqil manba mos keldi
        kuch = min(3, plan.confluence.strength)
        qismlar.append(
            ScoreComponent(
                "confluence",
                40.0 * (kuch / 3),
                40.0,
                f"Tuzilma: {plan.confluence.describe()} ({kuch} manba)",
            )
        )

        # 2) Korreksiya chuqurligi (25) — "oltin zona" ga yaqinlik
        nisbat = plan.retracement
        if nisbat is None:
            chuqurlik, izoh = 0.0, "Korreksiya chuqurligi hisoblanmadi"
        else:
            # 0.5 atrofi eng yaxshi: sayoz qaytish — kuchli trend, lekin
            # kirish qimmat; chuqur qaytish — arzon, lekin tuzilma
            # buzilish xavfi ortadi.
            uzoqlik = min(1.0, abs(nisbat - 0.5) / 0.5)
            chuqurlik = 25.0 * (1 - uzoqlik)
            izoh = f"Korreksiya: impulsning {nisbat * 100:.0f}% i"
        qismlar.append(ScoreComponent("retracement", chuqurlik, 25.0, izoh))

        # 3) Risk/foyda (20)
        xavf = plan.entry - plan.stop
        rr = (impulse.high - plan.entry) / xavf if xavf > 0 else 0.0
        qismlar.append(
            ScoreComponent(
                "risk_reward",
                min(20.0, 20.0 * rr / (c.min_risk_reward * 2)),
                20.0,
                f"Nisbat 1:{rr:.1f}",
            )
        )

        # 4) RSI qaytishi (15)
        narxlar = closes(candles)
        ind = self._config.analysis.indicators
        qiymat = rsi(narxlar, ind.rsi_period)
        qaytdi = rsi_recovering_from_oversold(
            narxlar, ind.rsi_period, c.rsi_reversal_max
        )
        qismlar.append(
            ScoreComponent(
                "rsi",
                15.0 if qaytdi else 0.0,
                15.0,
                (
                    f"RSI {qiymat:.0f} — {c.rsi_reversal_max:.0f} dan qaytdi"
                    if qaytdi
                    else f"RSI {qiymat:.0f} — qaytish belgisi yo'q"
                )
                if qiymat is not None
                else "RSI hisoblanmadi",
            )
        )

        return ScoreBreakdown(symbol=symbol, components=qismlar)

    def _reject(self, stage: str, detail: str) -> None:
        self._last_rejection = RejectionReason(stage, detail)
        logger.debug("Correction Entry signal bermadi (%s): %s", stage, detail)
        return None
