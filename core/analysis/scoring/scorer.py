"""3.5-band: ball hisoblash, chegara qo'llash va reytinglash.

Jarayon (spetsifikatsiyadan):
    1. Top 30 Halal coin parallel tahlil qilinadi
    2. Har biriga yig'indi ball hisoblanadi, reytinglanadi
    3. Minimal ball chegarasi qo'llaniladi — chegara STATIK EMAS, Bozor
       Salomatligi Indeksiga qarab moslashadi
    4. Chegaradan o'tganlar signal nomzodi
    5. Hech kim o'tmasa — signal berilmaydi (normal holat)

Chegarani hisoblash `RiskEngine.score_threshold()` da — u konfiguratsiyaga
va indeksga bog'liq. Bu modul faqat ballni hisoblaydi va saralaydi.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from core.analysis.indicators import Confirmation, IndicatorSnapshot
from core.analysis.scoring.factors import build_components
from core.analysis.support_resistance import ZoneMap
from core.config.schema import AppConfig
from core.domain.models import ScoreBreakdown, SignalCandidate, SignalLevels, SRZone
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """Reytingdagi bitta nomzod."""

    candidate: SignalCandidate
    rank: int
    passed_threshold: bool

    @property
    def score(self) -> float:
        return self.candidate.score


class Scorer:
    """Nomzodlarni baholaydi va reytinglaydi."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def score(
        self,
        symbol: str,
        zone_map: ZoneMap,
        zone: SRZone,
        snapshot: IndicatorSnapshot,
        confirmation: Confirmation,
        levels: SignalLevels,
    ) -> ScoreBreakdown:
        """Bitta nomzod uchun ball tafsilotini quradi."""
        komponentlar = build_components(
            zone_map=zone_map,
            zone=zone,
            range_position=zone_map.range_position(),
            snapshot=snapshot,
            confirmation=confirmation,
            levels=levels,
            weights=self._config.scoring.weights,
            indicators=self._config.analysis.indicators,
            rules=self._config.trade_rules,
        )
        return ScoreBreakdown(symbol=symbol, components=komponentlar)

    def rank(
        self,
        candidates: list[SignalCandidate],
        threshold: float | None,
    ) -> list[RankedCandidate]:
        """Nomzodlarni ballga qarab saralaydi va chegarani qo'llaydi.

        Args:
            threshold: minimal ball. `None` — Bozor Salomatligi past, hech
                kim o'tmaydi (3.5-band: "indeks past -> yangi signal umuman
                berilmaydi").
        """
        tartiblangan = sorted(candidates, key=lambda c: c.score, reverse=True)

        natija = [
            RankedCandidate(
                candidate=nomzod,
                rank=index + 1,
                passed_threshold=threshold is not None and nomzod.score >= threshold,
            )
            for index, nomzod in enumerate(tartiblangan)
        ]

        otganlar = sum(1 for r in natija if r.passed_threshold)
        if natija and not otganlar:
            eng_yuqori = natija[0].score
            logger.info(
                "Chegaradan hech kim o'tmadi: eng yuqori ball %.1f, chegara %s — "
                "signal berilmaydi (normal holat)",
                eng_yuqori,
                f"{threshold:.0f}" if threshold is not None else "yopiq",
            )
        return natija

    @staticmethod
    def passed(ranked: list[RankedCandidate]) -> list[SignalCandidate]:
        """Chegaradan o'tgan nomzodlar, eng yuqori balldan boshlab."""
        return [r.candidate for r in ranked if r.passed_threshold]


def breakdown_to_json(breakdown: ScoreBreakdown) -> str:
    """Ball tafsilotini bazaga saqlash uchun JSON matnga aylantiradi.

    3.6-band: "Nega bu signal?" tugmasi shu ma'lumotdan to'ladi, shuning
    uchun u signal bilan birga saqlanishi kerak — keyinroq qayta hisoblash
    mumkin emas (bozor holati o'zgargan bo'ladi).
    """
    return json.dumps(
        {
            "symbol": breakdown.symbol,
            "total": round(breakdown.total, 2),
            "maximum": round(breakdown.maximum, 2),
            "components": [
                {
                    "name": komponent.name,
                    "earned": round(komponent.earned, 2),
                    "maximum": round(komponent.maximum, 2),
                    "explanation": komponent.explanation,
                }
                for komponent in breakdown.components
            ],
        },
        ensure_ascii=False,
    )


def breakdown_to_text(breakdown: ScoreBreakdown) -> str:
    """3.6-band: "Nega bu signal?" tugmasi uchun o'qiladigan matn."""
    qatorlar = [f"📊 {breakdown.symbol} — {breakdown.total:.0f}/{breakdown.maximum:.0f} ball", ""]
    for komponent in breakdown.components:
        ulush = "▰" * round(komponent.ratio * 5) + "▱" * (5 - round(komponent.ratio * 5))
        qatorlar.append(
            f"{ulush} {komponent.earned:.0f}/{komponent.maximum:.0f} — {komponent.explanation}"
        )
    return "\n".join(qatorlar)
