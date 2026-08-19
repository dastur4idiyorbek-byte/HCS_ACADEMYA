"""3.9-band: Kunlik Sham Ochilishi Skalping (Opening Range Scalping).

Asosiy S/R strategiyasidan MUSTAQIL, qo'shimcha modul. Kuzatilgan bozor
xatti-harakati: yangi kunlik sham ochilganda (UTC 00:00), ko'p treyder shu
daqiqada kirib, narx qisqa muddatli 1-2% harakat qiladi.

Mantiq:
    1. Kunlik ochilish shamining yuqori/quyi chegarasi — "ochilish diapazoni"
    2. Diapazon juda tor (harakat yo'q) yoki juda keng (Stop uzoq) bo'lmasligi
    3. Hajm o'rtachadan sezilarli yuqori bo'lishi shart
    4. Narx diapazon tepasini yuqoriga yorib o'tishi (spot: faqat long)
    5. Signal faqat ochilishdan keyingi tor oynada — kech kirish eng yomon kirish

MUHIM: HAR KUNI ISHLASHI SHART EMAS. Shart bajarilmasa `None` qaytadi va bu
normal holat (0.2-band).

Bu modul plug-in arxitekturasining sinovi (6.1-band): u `Strategy`
interfeysini amalga oshiradi, Risk Engine uni asosiy strategiyadan farq
qilmasdan chaqiradi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from core.analysis.strategies.base import Strategy, StrategyInput
from core.config.schema import AppConfig, OpeningRangeScalpConfig
from core.domain.enums import SignalSource
from core.domain.models import (
    Candle,
    ScoreBreakdown,
    ScoreComponent,
    SignalCandidate,
    SignalLevels,
)
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class OpeningRange:
    """Kunlik ochilish shamidan olingan diapazon."""

    high: float
    low: float
    volume: float
    opened_at: datetime

    @property
    def size(self) -> float:
        return self.high - self.low

    @property
    def size_pct(self) -> float:
        return 0.0 if self.high <= 0 else self.size / self.high * 100

    @property
    def midpoint(self) -> float:
        return (self.high + self.low) / 2


@dataclass(frozen=True, slots=True)
class ScalpRejection:
    stage: str
    detail: str


class OpeningRangeScalpStrategy(Strategy):
    """Kunlik ochilish diapazonini yorib o'tish strategiyasi."""

    name = "opening_range_scalp"

    def __init__(self, config: AppConfig) -> None:
        self._app_config = config
        self._config = config.strategies.opening_range_scalp
        self._last_rejection: ScalpRejection | None = None

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def required_timeframes(self) -> list[str]:
        return [self._config.timeframe, "1d"]

    @property
    def daily_risk_share_pct(self) -> float:
        """Umumiy kunlik byudjetdan shu strategiyaga ajratilgan ulush."""
        return self._config.daily_risk_share_pct

    @property
    def last_rejection(self) -> ScalpRejection | None:
        return self._last_rejection

    # ------------------------------------------------------------------ #

    def analyze(self, data: StrategyInput) -> SignalCandidate | None:
        """Nomzod qaytaradi yoki `None` (bugun shart bajarilmadi)."""
        self._last_rejection = None
        config = self._config

        if not data.halal_verdict.is_tradable:
            return self._reject("halal", f"{data.symbol}: {data.halal_verdict.reason}")

        shamlar = data.series(config.timeframe)
        if len(shamlar) < config.volume_ma_period + 2:
            return self._reject(
                "data", f"{config.timeframe} uchun sham yetarli emas ({len(shamlar)})"
            )

        ochilish_index = self._find_session_open(shamlar, data.now)
        if ochilish_index is None:
            return self._reject("session", "Bugungi ochilish shami topilmadi")

        diapazon = self._build_range(shamlar[ochilish_index])

        # Signal oynasi: ochilishdan keyingi tor vaqt
        oyna_chegarasi = diapazon.opened_at + timedelta(minutes=config.signal_window_minutes)
        if data.now > oyna_chegarasi:
            return self._reject(
                "window",
                f"Signal oynasi yopilgan ({config.signal_window_minutes} daqiqa) — "
                "kech kirish eng yomon kirish",
            )

        # Diapazon sifati
        if diapazon.size_pct < config.min_range_pct:
            return self._reject(
                "range",
                f"Ochilish diapazoni juda tor ({diapazon.size_pct:.2f}% < "
                f"{config.min_range_pct}%) — harakat yo'q",
            )
        if diapazon.size_pct > config.max_range_pct:
            return self._reject(
                "range",
                f"Ochilish diapazoni juda keng ({diapazon.size_pct:.2f}% > "
                f"{config.max_range_pct}%) — Stop juda uzoq qolardi",
            )

        # Hajm sakrashi
        hajm_nisbati = self._volume_ratio(shamlar, ochilish_index)
        if hajm_nisbati is None:
            return self._reject("volume", "Hajm o'rtachasi hisoblanmadi")
        if hajm_nisbati < config.volume_surge_mult:
            return self._reject(
                "volume",
                f"Hajm sakrashi yetarli emas ({hajm_nisbati:.1f}× < "
                f"{config.volume_surge_mult}×) — harakat ishonchsiz",
            )

        # Yorib o'tish (spot: faqat yuqoriga)
        joriy = shamlar[-1].close
        if joriy <= diapazon.high:
            return self._reject(
                "breakout",
                f"Narx diapazon tepasini ({diapazon.high:.6g}) yorib o'tmadi",
            )

        darajalar = self._build_levels(joriy, diapazon)
        if darajalar is None:
            return self._reject(
                "levels",
                f"Darajalar {config.min_move_pct}–{config.max_move_pct}% oralig'iga "
                "sig'madi",
            )

        tafsilot = self._score(
            data.symbol, diapazon, hajm_nisbati, joriy, darajalar
        )

        logger.info(
            "Skalping nomzodi: %s ball=%.1f diapazon=%.2f%% hajm=%.1f×",
            data.symbol,
            tafsilot.total,
            diapazon.size_pct,
            hajm_nisbati,
        )
        return SignalCandidate(
            symbol=data.symbol,
            levels=darajalar,
            source=SignalSource.OPENING_RANGE_SCALP,
            breakdown=tafsilot,
            halal_verdict=data.halal_verdict,
        )

    # ------------------------------------------------------------------ #

    def _find_session_open(self, candles: list[Candle], now: datetime) -> int | None:
        """Bugungi kunlik ochilish shamining indeksini topadi."""
        ochilish_vaqti = self._config.session_open_time
        bugun = now.date()

        for index in range(len(candles) - 1, -1, -1):
            sham = candles[index]
            if sham.open_time.date() != bugun:
                # Kecha va undan oldingi shamlar — bugungi ochilish yo'q
                return None
            if sham.open_time.timetz().replace(tzinfo=None) == ochilish_vaqti:
                return index
        return None

    def _build_range(self, candle: Candle) -> OpeningRange:
        return OpeningRange(
            high=candle.high,
            low=candle.low,
            volume=candle.volume,
            opened_at=candle.open_time,
        )

    def _volume_ratio(self, candles: list[Candle], open_index: int) -> float | None:
        """Ochilish shamining hajmi oldingi kunlar o'rtachasiga nisbatan.

        O'rtacha ochilish shamidan OLDINGI shamlardan olinadi — ochilish
        shamining o'zi o'rtachaga kirsa, sakrash yashiringan bo'lardi.
        """
        davr = self._config.volume_ma_period
        boshlanish = max(0, open_index - davr)
        oyna = candles[boshlanish:open_index]
        if len(oyna) < 2:
            return None
        ortacha = sum(sham.volume for sham in oyna) / len(oyna)
        return None if ortacha <= 0 else candles[open_index].volume / ortacha

    def _build_levels(self, entry: float, opening_range: OpeningRange) -> SignalLevels | None:
        """Stop diapazon o'rtasida, TP kutilayotgan harakat oralig'ida.

        Stop nima uchun diapazon o'rtasida, pastida emas: yorib o'tish
        muvaffaqiyatsiz bo'lsa narx odatda diapazon ichiga qaytadi.
        O'rtaga qaytish — "yorib o'tish yolg'on edi" degan aniq belgi, va
        bu diapazon pastini kutishdan ko'ra tezroq va arzonroq chiqish.
        """
        config = self._config
        stop = opening_range.midpoint
        if stop >= entry:
            return None

        tp1 = entry * (1 + config.min_move_pct / 100)
        tp2 = entry * (1 + config.max_move_pct / 100)

        try:
            return SignalLevels(entry=entry, stop=stop, tp1=tp1, tp2=tp2)
        except ValueError:
            return None

    def _score(
        self,
        symbol: str,
        opening_range: OpeningRange,
        volume_ratio: float,
        price: float,
        levels: SignalLevels,
    ) -> ScoreBreakdown:
        """Skalping uchun ball — asosiy strategiyanikidan boshqa omillar."""
        config = self._config
        vaznlar = config.weights

        # 1) Hajm sakrashi — eng og'ir omil. Minimal shart (2×) bajarilgan
        # bo'lsa 0.5 dan boshlanadi, 4× da to'liq ballga yetadi.
        ortiqcha = (volume_ratio - config.volume_surge_mult) / config.volume_surge_mult
        hajm_ulushi = 0.5 + max(0.0, min(1.0, ortiqcha)) * 0.5

        # 2) Diapazon sifati — o'rtacha kenglik eng yaxshi
        ideal = (config.min_range_pct + config.max_range_pct) / 2
        chetlanish = abs(opening_range.size_pct - ideal) / (config.max_range_pct - ideal)
        diapazon_ulushi = max(0.0, 1.0 - chetlanish)

        # 3) Yo'nalish aniqligi — diapazondan qanchalik uzoqqa chiqdi
        chiqish = (price - opening_range.high) / opening_range.size if opening_range.size else 0
        yonalish_ulushi = min(1.0, chiqish / 0.5)

        # 4) Risk/Reward
        rr = levels.risk_reward_tp2
        rr_ulushi = min(1.0, rr / 2.0)

        return ScoreBreakdown(
            symbol=symbol,
            components=[
                ScoreComponent(
                    "volume_surge",
                    hajm_ulushi * vaznlar.volume_surge,
                    vaznlar.volume_surge,
                    f"Hajm ochilishda o'rtachadan {volume_ratio:.1f}× yuqori",
                ),
                ScoreComponent(
                    "range_quality",
                    diapazon_ulushi * vaznlar.range_quality,
                    vaznlar.range_quality,
                    f"Ochilish diapazoni {opening_range.size_pct:.2f}% "
                    f"({config.min_range_pct}–{config.max_range_pct}% ideal oralig'i)",
                ),
                ScoreComponent(
                    "direction_clarity",
                    yonalish_ulushi * vaznlar.direction_clarity,
                    vaznlar.direction_clarity,
                    f"Narx diapazon tepasidan {chiqish:.0%} chiqdi",
                ),
                ScoreComponent(
                    "risk_reward",
                    rr_ulushi * vaznlar.risk_reward,
                    vaznlar.risk_reward,
                    f"R/R 1:{rr:.1f}",
                ),
            ],
        )

    def _reject(self, stage: str, detail: str) -> None:
        self._last_rejection = ScalpRejection(stage, detail)
        logger.debug("Skalping signal bermadi (%s): %s", stage, detail)
        return None


def scalp_trade_rules(config: OpeningRangeScalpConfig) -> tuple[float, float, float]:
    """3.9-band strategiyasi uchun TP oralig'i va minimal R/R.

    3.3-banddagi universal qoida TP ni 3–5% deb belgilaydi, skalping esa
    1–2% harakatni kutadi. Ikkalasi bir xil chegara bilan tekshirilsa,
    skalping signallari HAR DOIM rad etilardi.

    Returns:
        `(min_tp_pct, max_tp_pct, min_risk_reward)`.
    """
    # Skalpingda Stop diapazon o'rtasida — R/R odatda 1:1..1:3 oralig'ida.
    # 1:3 talab qilish bu strategiyani imkonsiz qilardi.
    return config.min_move_pct, config.max_move_pct, 1.0
