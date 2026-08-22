"""3.1-band: asosiy strategiya — Support/Resistance BIRINCHI, indikatorlar ikkinchi.

To'g'ri tartib:

    1. AVVAL: muhim S/R zonalari aniqlanadi
    2. Narx Support zonasida VA Discount zonadami (3.1-band davomi)
    3. Stop/TP darajalari S/R va ATR asosida quriladi (3.3 chegaralari bilan)
    4. KEYIN: indikatorlar va yuqori timeframelar BALLGA qo'shiladi

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

from dataclasses import dataclass

from core.analysis.indicators import build_snapshot, confirm
from core.analysis.scoring import Scorer, build_levels
from core.analysis.strategies.base import Strategy, StrategyInput
from core.analysis.support_resistance import SupportResistanceDetector
from core.config.schema import AppConfig
from core.domain.enums import SignalSource, TrendDirection, ZoneKind
from core.domain.models import MultiTimeframeView, SignalCandidate, TimeframeTrend
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RejectionReason:
    """Nomzod nima uchun rad etildi — admin dashboardi va postmortem uchun."""

    stage: str
    detail: str


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
        if len(shamlar) < analysis.indicators.ema_slow:
            return self._reject(
                "data",
                f"{analysis.entry_timeframe} uchun sham yetarli emas "
                f"({len(shamlar)} < {analysis.indicators.ema_slow})",
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
        daraja_natijasi = build_levels(zona_xaritasi, self._config.trade_rules)
        if not daraja_natijasi.ok:
            return self._reject("levels", daraja_natijasi.reason)

        # 6) Ball
        tafsilot = self._scorer.score(
            symbol=data.symbol,
            zone_map=zona_xaritasi,
            zone=zona,
            snapshot=holat,
            confirmation=hukm,
            levels=daraja_natijasi.levels,
            htf_alignment=moslik,
        )

        logger.info(
            "Nomzod tayyor: %s ball=%.1f zona=%s TP manbai=%s",
            data.symbol,
            tafsilot.total,
            f"{zona.low:.4g}-{zona.high:.4g}",
            "tuzilma" if daraja_natijasi.tp_from_structure else "o'lchangan",
        )
        return SignalCandidate(
            symbol=data.symbol,
            levels=daraja_natijasi.levels,
            source=SignalSource.CLASSIC_TA,
            breakdown=tafsilot,
            halal_verdict=data.halal_verdict,
        )

    # ------------------------------------------------------------------ #

    def _timeframe_view(self, data: StrategyInput) -> MultiTimeframeView:
        """3.2-band: har bir yuqori timeframe uchun trend yo'nalishi.

        Sham yetarli bo'lmagan timeframe `FLAT` deb belgilanadi — bu
        muvofiqlikni buzadi va signal berilmaydi (0.3-band).

        Diqqat: bu yerda `htf_trend_requires_price_above_fast` ishlatiladi,
        `trend_requires_price_above_fast` emas. 3.1-band'ning "narx
        EMA'lardan yuqori" sharti KIRISH qarori haqida; 3.2-band esa
        yuqori timeframelarning TREND YO'NALISHI haqida. Ikkalasiga bir xil
        qat'iy shartni qo'llash ularni bir-birini inkor qiladigan qilib
        qo'yadi — o'lchov `docs/ARXITEKTURA.md` 27-bo'limda.
        """
        from core.analysis.indicators import timeframe_trend

        indicators = self._config.analysis.indicators
        return MultiTimeframeView(
            trends=[
                TimeframeTrend(
                    timeframe=tf,
                    direction=timeframe_trend(
                        data.series(tf),
                        indicators.ema_fast,
                        indicators.ema_slow,
                        indicators.htf_trend_requires_price_above_fast,
                    ),
                )
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
