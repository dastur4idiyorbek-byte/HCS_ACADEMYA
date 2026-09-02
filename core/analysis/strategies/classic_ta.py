"""3.1-band: asosiy strategiya — Support/Resistance BIRINCHI, indikatorlar ikkinchi.

To'g'ri tartib:

    1. AVVAL: muhim S/R zonalari aniqlanadi
    2. Narx Support zonasida VA Discount zonadami (3.1-band davomi)
    3. Stop/TP darajalari S/R va ATR asosida quriladi (3.3 chegaralari bilan)
    4. KEYIN: indikatorlar va yuqori timeframelar BALLGA qo'shiladi
    5. CryptoSpot3% dalillari (SMC struktura, MSNR daraja turi, LIT
       yalash) ballning ICHIGA qo'shiladi — struktura trendni, daraja
       turi va sweep esa S/R zonasini ko'taradi. To'siq emas: dalil
       yo'q bo'lsa ball o'zgarmaydi.

KIM QAROR QILADI. "Signal berilsinmi" degan savolga STRUKTURA (S/R
zonasi) va RISK QOIDASI (3.3-band) javob beradi. Indikatorlar esa
"ko'p coin ichidan qaysi biri" degan savolga javob beradi — ya'ni
reyting uchun.

Nima uchun shunday. Indikatorlar tabiatan KECHIKADI: ular narx
harakatidan keyin tasdiqlaydi. Narx support zonasiga qaytganda MACD
hali kesmagan, RSI hali qaytmagan, kunlik EMA200 esa 200 kunlik
o'rtacha — eng sekin o'lchov. Ular tasdiqlaguncha narx Discount
zonasidan chiqib ketadi. Ya'ni "indikator tasdiqlasin" talabi amalda
"arzon paytda olma, qimmatlashgach ol" degani — strategiyaning o'z
maqsadiga zid.

Bu xatti-harakat `analysis.require_htf_alignment` va
`analysis.indicators.require_confirmation` orqali qaytarilishi mumkin.

Har bir bosqichda "yo'q" javobi olinsa, `analyze()` `None` qaytaradi. Bu
XATO EMAS — 0.2-band bo'yicha normal holat.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from core.analysis.indicators import build_snapshot, confirm
from core.analysis.level_types import classify_level_type
from core.analysis.scoring import Scorer, build_levels
from core.analysis.scoring.setup_route import evaluate_setup
from core.analysis.strategies.base import Strategy, StrategyInput
from core.analysis.support_resistance import (
    SupportResistanceDetector,
    detect_liquidity_sweep,
)
from core.config.schema import AppConfig, TradeRulesConfig
from core.domain.enums import SignalSource, TrendDirection, ZoneKind
from core.domain.models import MultiTimeframeView, SignalCandidate, TimeframeTrend
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RejectionReason:
    """Nomzod nima uchun rad etildi — admin dashboardi va postmortem uchun."""

    stage: str
    detail: str


def classic_ta_rules(config: AppConfig) -> TradeRulesConfig:
    """`classic_ta` uchun amaldagi savdo qoidalari.

    Global `min_risk_reward` (1:3) trend/breakout strategiyalariga xos.
    Mean reversion tabiiy ravishda diapazon o'rtasiga qaytganda yopiladi —
    bu odatda 1:1..1:1.5 beradi.

    YAGONA MANBA bo'lishi shart: darajalarni QURISH (`build_levels`) va
    ularni TEKSHIRISH (`TradeRulesRule`) bir xil nisbatga tayanishi kerak.
    Ikkisi ajralib qolsa, TP2 bir qiymat bo'yicha quriladi, boshqasi
    bo'yicha rad etiladi.
    """
    qoidalar = config.trade_rules
    if qoidalar.tp2_from_structure:
        # Tuzilmaviy TP2 nisbatni PASAYTIRADI — u bozordagi zonaga
        # qo'yiladi, formulaga emas. Tekshiruv eski nisbatda qolsa,
        # darajalar quriladi-yu, Risk Engine ularni darhol yo'q
        # qilardi: bayroq e'lon qilingan, lekin ULANMAGAN bo'lib
        # qolardi (loyihada takrorlanuvchi xato turi).
        return dataclasses.replace(
            qoidalar, min_risk_reward=qoidalar.tp2_structural_min_rr
        )
    return dataclasses.replace(
        qoidalar,
        min_risk_reward=config.strategies.classic_ta.min_risk_reward,
    )


class ClassicTaStrategy(Strategy):
    """S/R + Discount/Premium + indikatorlar strategiyasi."""

    name = "classic_ta"

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._detector = SupportResistanceDetector(
            config.analysis.support_resistance,
            config.analysis.indicators.atr_period,
        )
        self._scorer = Scorer(config)
        self._last_rejection: RejectionReason | None = None

    @property
    def enabled(self) -> bool:
        return self._config.strategies.classic_ta.enabled

    def required_timeframes(self) -> list[str]:
        analysis = self._config.analysis
        return [analysis.entry_timeframe, *analysis.htf_confirmation]

    @property
    def last_rejection(self) -> RejectionReason | None:
        """Oxirgi tahlil nima uchun signal bermadi."""
        return self._last_rejection

    # ------------------------------------------------------------------ #

    def analyze(self, data: StrategyInput) -> SignalCandidate | None:
        """Nomzod qaytaradi yoki `None` (signal berish to'g'ri emas)."""
        self._last_rejection = None
        analysis = self._config.analysis

        # 0) Halollik — skrining allaqachon filtrlagan, lekin takroriy himoya
        if not data.halal_verdict.is_tradable:
            return self._reject("halal", f"{data.symbol}: {data.halal_verdict.reason}")

        shamlar = data.series(analysis.entry_timeframe)
        if len(shamlar) < analysis.indicators.min_candles:
            return self._reject(
                "data",
                f"{analysis.entry_timeframe} uchun sham yetarli emas "
                f"({len(shamlar)} < {analysis.indicators.min_candles})",
            )

        # 1) S/R zonalari — BIRLAMCHI tahlil
        zona_xaritasi = self._detector.detect(shamlar)
        if zona_xaritasi is None:
            return self._reject("zones", "S/R zonalari aniqlanmadi (ATR yoki sham yetarli emas)")

        # 2) Narx Support zonasida VA Discount zonadami
        chegara = analysis.support_resistance.entry_max_range_pct
        if not zona_xaritasi.entry_allowed(chegara):
            return self._reject("zone_position", self._explain_zone(zona_xaritasi, chegara))

        zona = zona_xaritasi.active_zone(ZoneKind.SUPPORT)
        if zona is None:
            return self._reject(
                "zone_position",
                f"Narx birorta support zonasiga {zona_xaritasi.proximity_atr:.1f} ATR "
                "masofasida emas",
            )

        # 3) Ko'p timeframe muvofiqligi (3.2-band) — endi BALL uchun
        korinish = self._timeframe_view(data)
        moslik = korinish.alignment_ratio(TrendDirection.UP)
        if analysis.require_htf_alignment and not korinish.all_aligned(TrendDirection.UP):
            zid = [t.timeframe for t in korinish.trends if t.direction is not TrendDirection.UP]
            return self._reject(
                "timeframes",
                f"Timeframelar zid: {', '.join(zid)} ko'tarilishni tasdiqlamadi",
            )

        # 4) Indikatorlar — TASDIQ EMAS, BAHO
        holat = build_snapshot(shamlar, analysis.indicators)
        if holat is None or not holat.is_complete:
            return self._reject("indicators", "Indikatorlar to'liq hisoblanmadi")

        hukm = confirm(holat, analysis.indicators, zone_ready=True)
        if analysis.indicators.require_confirmation and not hukm.is_confirmed:
            rad_etganlar = [o.name for o in hukm.factors if not o.confirmed]
            return self._reject(
                "confirmation",
                f"Yetarli tasdiq yo'q ({hukm.confirmed_count}/{hukm.min_confirmations} kerak) — "
                f"tasdiqlamaganlar: {', '.join(rad_etganlar)}",
            )

        # 5) Darajalar (3.3-band chegaralari bilan)
        qoidalar = classic_ta_rules(self._config)
        daraja_natijasi = build_levels(zona_xaritasi, qoidalar)
        if not daraja_natijasi.ok:
            return self._reject(daraja_natijasi.stage, daraja_natijasi.reason)

        # 6) CryptoSpot3% qatlami — BONUS uchun, TO'SIQ EMAS
        #
        # Uchalasi ham "yo'q" bo'lishi mumkin va bu normal: nomzod
        # bazaviy 100 ballik tizimda baholanishda davom etadi. Metodika
        # hujjatining o'zi ham shuni talab qiladi — yangi omillar
        # qat'iy filtr sifatida qo'shilmasin.
        # FAKT QATLAMIDAN o'qiladi, o'zi hisoblamaydi: bitta coin
        # uchun struktura bir marta hisoblanadi va barcha strategiyalar
        # o'sha bitta javobni ko'radi (`StrategyInput.structure`).
        struktura = data.structure(analysis.entry_timeframe)
        if analysis.require_structure_alignment and struktura.direction is TrendDirection.DOWN:
            return self._reject(
                "structure",
                f"Struktura pasayishda ({struktura.describe()}) — "
                "spot xaridi tuzilmaga qarshi",
            )

        daraja_turi = classify_level_type(zona, shamlar, zona_xaritasi.atr, struktura)
        yalash = detect_liquidity_sweep(shamlar, zona, analysis.liquidity_sweep)

        # Metodikaning TO'LIQ shartnomasi bajarildimi — YORLIQ.
        # Bu darvoza emas: dalillar allaqachon ball ichiga qo'shilgan
        # (`factors.py`), ya'ni to'liq shartnomali nomzod baribir
        # yuqori ball oladi. Yorliq "Nega bu signal?" ekranida va
        # o'lchovda ishlatiladi.
        shartnoma = evaluate_setup(
            struktura, daraja_turi, yalash, self._config.scoring.setup_route
        )

        # 7) Ball
        tafsilot = self._scorer.score(
            symbol=data.symbol,
            zone_map=zona_xaritasi,
            zone=zona,
            snapshot=holat,
            confirmation=hukm,
            levels=daraja_natijasi.levels,
            htf_alignment=moslik,
            rules=qoidalar,
            structure=struktura,
            level_type=daraja_turi,
            sweep=yalash,
            moment=shamlar[-1].open_time,
            setup=shartnoma,
        )

        logger.info(
            "Nomzod tayyor: %s ball=%.1f (bazaviy %.1f + bonus %.1f) zona=%s "
            "struktura=%s TP manbai=%s",
            data.symbol,
            tafsilot.total,
            tafsilot.base_total,
            tafsilot.bonus_total,
            f"{zona.low:.4g}-{zona.high:.4g}",
            struktura.direction.value,
            "tuzilma" if daraja_natijasi.tp_from_structure else "o'lchangan",
        )
        if shartnoma.qualified:
            logger.info("%s: %s", data.symbol, shartnoma.reason)
        return SignalCandidate(
            symbol=data.symbol,
            levels=daraja_natijasi.levels,
            source=SignalSource.CLASSIC_TA,
            breakdown=tafsilot,
            halal_verdict=data.halal_verdict,
            setup=shartnoma,
        )

    # ------------------------------------------------------------------ #

    def _timeframe_view(self, data: StrategyInput) -> MultiTimeframeView:
        """3.2-band: har bir yuqori timeframe uchun trend yo'nalishi.

        MANBA O'ZGARDI: ilgari bu EMA50 > EMA200 edi. Endi u SMC
        STRUKTURASI — narxning o'z qadamlari (HH/HL yoki LH/LL).

        Nima uchun: EMA200 kunlik grafikda 200 kunlik o'rtacha, ya'ni
        eng sekin o'lchov. U tasdiqlaguncha narx Discount zonasidan
        chiqib ketardi. Struktura esa burilishni birinchi bo'lib
        ko'rsatadi. Qo'shimcha yutuq — 200 sham talabi yo'qoldi:
        haftalik timeframeda u ~3.8 yil tarix degani edi va ko'p
        altcoinlarni jimgina chetlab o'tardi (27- va 58-bo'limlar).

        Sham yetarli bo'lmagan timeframe `FLAT` deb belgilanadi — bu
        muvofiqlikni buzadi, lekin signalni to'xtatmaydi (0.3-band).
        """
        return MultiTimeframeView(
            trends=[
                TimeframeTrend(timeframe=tf, direction=data.structure(tf).direction)
                for tf in self._config.analysis.htf_confirmation
            ]
        )

    def _explain_zone(self, zone_map, max_range_pct: float) -> str:  # noqa: ANN001
        """Zona sharti nima uchun bajarilmaganini tushuntiradi."""
        joylashuv = zone_map.range_position()
        if joylashuv is None:
            return "Support—Resistance diapazoni qurilmadi (bir tomonda zona yo'q)"
        if joylashuv.is_outside_range:
            return joylashuv.describe()
        if joylashuv.percent > max_range_pct:
            return (
                f"Narx diapazonning yuqori qismida ({joylashuv.percent:.0f}%, "
                f"ruxsat {max_range_pct:.0f}%) — kirish uchun qimmat"
            )
        return (
            f"Narx birorta support zonasiga {zone_map.proximity_atr:.1f} ATR masofasida emas"
        )

    def _reject(self, stage: str, detail: str) -> None:
        self._last_rejection = RejectionReason(stage, detail)
        logger.debug("Signal berilmadi (%s): %s", stage, detail)
        return None
