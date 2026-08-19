"""3.8-band: naqsh (pattern) izlash — statistika EMAS.

Farq muhim: statistika "35% signal Stop yedi" deydi. Naqsh esa
"Bozor Salomatligi 60dan past bo'lganda signallarning 70% Stop yeydi"
deydi — ya'ni SABABGA ishora qiladi.

HALOLLIK CHEGARASI: naqsh faqat namuna yetarli bo'lganda e'lon qilinadi.
5 ta signal asosida "70% Stop yeydi" deyish statistika emas, shovqin.
Shuning uchun har bir naqsh `min_sample_size` va `min_effect_pct`
shartlaridan o'tishi kerak.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.analysis.postmortem.outcome import ClosedSignal
from core.config.schema import PostmortemConfig


@dataclass(frozen=True, slots=True)
class Segment:
    """Signallarning bir guruhi va uning natijalari."""

    label: str
    signals: list[ClosedSignal]

    @property
    def size(self) -> int:
        return len(self.signals)

    @property
    def win_rate(self) -> float | None:
        """Foyda bilan yopilganlar ulushi (0..1)."""
        if not self.signals:
            return None
        return sum(1 for s in self.signals if s.outcome.is_win) / len(self.signals)

    @property
    def stop_rate(self) -> float | None:
        if not self.signals:
            return None
        return sum(1 for s in self.signals if s.outcome.is_loss) / len(self.signals)

    @property
    def false_signal_rate(self) -> float | None:
        if not self.signals:
            return None
        return sum(1 for s in self.signals if s.is_false_signal) / len(self.signals)


@dataclass(frozen=True, slots=True)
class Pattern:
    """Aniqlangan naqsh va uning ishonchliligi."""

    name: str
    worse: Segment
    better: Segment
    effect_pct: float
    recommendation: str

    @property
    def sample_size(self) -> int:
        return self.worse.size + self.better.size

    def describe(self) -> str:
        return (
            f"⚠️ {self.name}\n"
            f"   {self.worse.label}: {self.worse.stop_rate:.0%} Stop "
            f"({self.worse.size} ta signal)\n"
            f"   {self.better.label}: {self.better.stop_rate:.0%} Stop "
            f"({self.better.size} ta signal)\n"
            f"   💡 {self.recommendation}"
        )


def split_by(
    signals: list[ClosedSignal],
    predicate: Callable[[ClosedSignal], bool | None],
    worse_label: str,
    better_label: str,
) -> tuple[Segment, Segment]:
    """Signallarni ikki guruhga ajratadi.

    `predicate` `None` qaytarsa (ma'lumot yo'q), signal ikkala guruhga ham
    kirmaydi — noma'lum ma'lumot naqshni buzmasligi kerak.
    """
    yomon: list[ClosedSignal] = []
    yaxshi: list[ClosedSignal] = []
    for signal in signals:
        natija = predicate(signal)
        if natija is None:
            continue
        (yomon if natija else yaxshi).append(signal)
    return Segment(worse_label, yomon), Segment(better_label, yaxshi)


def _make_pattern(
    name: str,
    worse: Segment,
    better: Segment,
    config: PostmortemConfig,
    recommendation: Callable[[Segment, Segment], str],
) -> Pattern | None:
    """Naqshni faqat halollik shartlaridan o'tsa qaytaradi."""
    if worse.size < config.min_sample_size or better.size < config.min_sample_size:
        return None

    worse_stop = worse.stop_rate or 0.0
    better_stop = better.stop_rate or 0.0
    ta_sir = (worse_stop - better_stop) * 100

    if ta_sir < config.min_effect_pct:
        return None

    return Pattern(
        name=name,
        worse=worse,
        better=better,
        effect_pct=ta_sir,
        recommendation=recommendation(worse, better),
    )


def market_health_pattern(
    signals: list[ClosedSignal],
    config: PostmortemConfig,
    threshold: float = 60.0,
) -> Pattern | None:
    """Spetsifikatsiyadagi asosiy misol: past salomatlikda signallar yomon ishlaydimi."""
    yomon, yaxshi = split_by(
        signals,
        lambda s: (
            None if s.market_health_at_entry is None else s.market_health_at_entry < threshold
        ),
        worse_label=f"Salomatlik {threshold:.0f} dan past",
        better_label=f"Salomatlik {threshold:.0f} va undan yuqori",
    )

    def tavsiya(w: Segment, b: Segment) -> str:  # noqa: ANN001
        return (
            f"Bozor Salomatligi {threshold:.0f} dan past bo'lganda ball chegarasini "
            f"ko'tarish tavsiya etiladi — oxirgi {config.lookback_days} kunlik "
            f"ma'lumot asosida bunday signallarning {w.stop_rate:.0%}i Stop yedi."
        )

    return _make_pattern("Bozor Salomatligi ta'siri", yomon, yaxshi, config, tavsiya)


def score_pattern(
    signals: list[ClosedSignal],
    config: PostmortemConfig,
    threshold: float = 75.0,
) -> Pattern | None:
    """Past ballli signallar sezilarli yomonroq ishlaydimi."""
    yomon, yaxshi = split_by(
        signals,
        lambda s: None if s.score is None else s.score < threshold,
        worse_label=f"Ball {threshold:.0f} dan past",
        better_label=f"Ball {threshold:.0f} va undan yuqori",
    )

    def tavsiya(w: Segment, b: Segment) -> str:  # noqa: ANN001
        return (
            f"Minimal ball chegarasini {threshold:.0f} ga ko'tarish tavsiya etiladi — "
            f"undan past ballli signallarning {w.stop_rate:.0%}i Stop yedi, "
            f"yuqorilariniki esa {b.stop_rate:.0%}."
        )

    return _make_pattern("Ball chegarasi ta'siri", yomon, yaxshi, config, tavsiya)


def false_signal_pattern(
    signals: list[ClosedSignal],
    config: PostmortemConfig,
) -> Pattern | None:
    """"Yolg'on signal" — zaif kirish nuqtasi belgisi (3.8-band)."""
    yomon, yaxshi = split_by(
        signals,
        lambda s: s.is_false_signal,
        worse_label="Yolg'on signal (tez Stop)",
        better_label="Oddiy signallar",
    )

    def tavsiya(w: Segment, b: Segment) -> str:  # noqa: ANN001
        return (
            f"Oxirgi davrda {w.size} ta signal faol bo'lgach darhol Stop yedi. "
            "Kirish nuqtasi zaif bo'lishi mumkin — S/R zonasiga yaqinlik "
            "chegarasini (`proximity_atr_mult`) qisqartirishni ko'rib chiqing."
        )

    return _make_pattern("Zaif kirish nuqtalari", yomon, yaxshi, config, tavsiya)


def strategy_pattern(
    signals: list[ClosedSignal],
    config: PostmortemConfig,
) -> Pattern | None:
    """Qaysidir strategiya sezilarli yomonroq ishlayaptimi."""
    from core.domain.enums import SignalSource

    yomon, yaxshi = split_by(
        signals,
        lambda s: s.source is SignalSource.OPENING_RANGE_SCALP,
        worse_label="Skalping",
        better_label="Asosiy strategiya",
    )

    def tavsiya(w: Segment, b: Segment) -> str:  # noqa: ANN001
        return (
            f"Skalping strategiyasi asosiydan yomonroq ishlamoqda "
            f"({w.stop_rate:.0%} va {b.stop_rate:.0%} Stop). Uning byudjet "
            "ulushini kamaytirish yoki vaqtincha o'chirishni ko'rib chiqing."
        )

    return _make_pattern("Strategiyalar farqi", yomon, yaxshi, config, tavsiya)


#: Barcha naqsh izlovchilar. Yangisini qo'shish — bitta funksiya yozish.
PATTERN_FINDERS = [
    market_health_pattern,
    score_pattern,
    false_signal_pattern,
    strategy_pattern,
]


def find_patterns(
    signals: list[ClosedSignal],
    config: PostmortemConfig,
) -> list[Pattern]:
    """Barcha naqshlarni izlaydi, ta'sir kuchi bo'yicha tartiblaydi."""
    faqat_savdolar = [s for s in signals if s.outcome.counts_in_stats]
    topilganlar = [
        naqsh
        for izlovchi in PATTERN_FINDERS
        if (naqsh := izlovchi(faqat_savdolar, config)) is not None
    ]
    return sorted(topilganlar, key=lambda p: p.effect_pct, reverse=True)
