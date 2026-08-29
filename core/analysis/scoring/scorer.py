"""3.5-band: ball hisoblash, chegara qo'llash va reytinglash.

Jarayon (spetsifikatsiyadan):
    1. Halol ro'yxatdagi coinlar parallel tahlil qilinadi
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
from datetime import datetime

from core.analysis.indicators import Confirmation, IndicatorSnapshot
from core.analysis.level_types import LevelType
from core.analysis.market_structure import MarketStructure
from core.analysis.scoring.bonuses import build_bonus_components
from core.analysis.scoring.factors import build_components
from core.analysis.support_resistance import LiquiditySweep, ZoneMap
from core.config.schema import AppConfig, TradeRulesConfig
from core.domain.models import (
    ScoreBreakdown,
    ScoreComponent,
    SignalCandidate,
    SignalLevels,
    SRZone,
)
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """Reytingdagi bitta nomzod."""

    candidate: SignalCandidate
    rank: int
    passed_threshold: bool
    #: CryptoSpot3% shartnomasi TO'LIQ bajarilganmi — YORLIQ, darvoza
    #: emas. "Nega bu signal?" ekrani va o'lchov uchun.
    setup_complete: bool = False

    @property
    def score(self) -> float:
        return self.candidate.score

    @property
    def base_score(self) -> float:
        """Klassik yo'l TEKSHIRADIGAN ball — bonussiz."""
        return self.candidate.breakdown.base_total


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
        htf_alignment: float | None = None,
        rules: TradeRulesConfig | None = None,
        structure: MarketStructure | None = None,
        level_type: LevelType = LevelType.PLAIN,
        sweep: LiquiditySweep | None = None,
        moment: datetime | None = None,
        setup: object | None = None,
    ) -> ScoreBreakdown:
        """Bitta nomzod uchun ball tafsilotini quradi.

        `htf_alignment` — yuqori timeframelarning qanchasi ko'tarilishda
        (0..1). Ilgari bu TO'SIQ edi; endi ball ichida hisobga olinadi
        (`analysis.require_htf_alignment`).

        `rules` — STRATEGIYANING savdo qoidalari. Berilmasa global
        qiymatlar olinadi.

        Nima uchun uzatilishi SHART: nisbat endi strategiya darajasida
        (mean reversion 1:1.5, global 1:3). Darajalar 1:1.5 bo'yicha
        quriladi, lekin ball global 1:3 bo'yicha hisoblansa, R/R
        komponenti "minimaldan past" deb 0 qaytaradi — 15 balldan
        ayrilish esa chegaradan o'tishni imkonsiz qiladi. Ya'ni
        3-tuzatish jimgina bekor bo'lardi.

        `structure`, `level_type`, `sweep` — CryptoSpot3% dalillari.
        Ular ALOHIDA OMIL EMAS: S/R va trend omillarining ICHIGA
        qo'shiladi (`factors.py`, `_uplift`), chunki ular aynan o'sha
        ikki narsa haqidagi ma'lumot. Berilmasa omillar eski holicha
        hisoblanadi — hech narsa yo'qolmaydi.
        """
        komponentlar = build_components(
            zone_map=zone_map,
            zone=zone,
            range_position=zone_map.range_position(),
            snapshot=snapshot,
            confirmation=confirmation,
            levels=levels,
            weights=self._config.scoring.weights,
            indicators=self._config.analysis.indicators,
            rules=rules if rules is not None else self._config.trade_rules,
            htf_alignment=htf_alignment,
            structure=structure,
            level_type=level_type,
            sweep=sweep,
            uplift=self._config.scoring.uplift,
        )
        komponentlar += build_bonus_components(
            moment=moment,
            bonuses=self._config.scoring.bonuses,
            session=self._config.analysis.session_overlap,
        )
        return ScoreBreakdown(
            symbol=symbol,
            components=komponentlar,
            setup_complete=bool(getattr(setup, "qualified", False)),
        )

    def rank(
        self,
        candidates: list[SignalCandidate],
        threshold: float | None,
    ) -> list[RankedCandidate]:
        """Nomzodlarni ballga qarab saralaydi va chegarani qo'llaydi.

        BITTA DARVOZA, ICHIDA IKKALA MODUL.

        Chegara BAZAVIY ballda tekshiriladi. Bu "eski modul" degani
        EMAS: CryptoSpot3% dalillari (struktura, daraja turi, sweep)
        aynan shu bazaviy ball ichida — ular S/R va trend omillarini
        ko'taradi (`factors.py`, `_uplift`).

        Ya'ni ikki modul ORALASHIB ishlaydi: tuzilmasi kuchli nomzod
        yuqoriroq bazaviy ball oladi va chegaradan O'Z KUCHI bilan
        o'tadi. Shu sababli yangi modul nafaqat QAYSI signal
        chiqishiga, balki QANCHA signal chiqishiga ham ta'sir qiladi.

        Nima uchun parallel ikkinchi darvoza QILINMADI: ikkita mustaqil
        darvoza ikkita alohida qoidalar to'plami degani — ikki barobar
        sozlash, ikki barobar xato va "qaysi biri ishladi" degan doimiy
        savol. Dalil omil ichiga qo'shilganda bitta raqam yetarli.

        Bonus (Kill Zone) esa chegaraga KIRMAYDI: u kirish vaqti
        haqida, tuzilma haqida emas, va u faqat saralashga ta'sir
        qiladi.

        Args:
            threshold: minimal BAZAVIY ball. `None` — Bozor Salomatligi
                past, hech kim o'tmaydi (3.5-band).
        """
        tartiblangan = sorted(candidates, key=lambda c: c.score, reverse=True)

        natija = [
            RankedCandidate(
                candidate=nomzod,
                rank=index + 1,
                passed_threshold=(
                    threshold is not None and nomzod.breakdown.base_total >= threshold
                ),
                setup_complete=nomzod.setup_qualified,
            )
            for index, nomzod in enumerate(tartiblangan)
        ]

        otganlar = [r for r in natija if r.passed_threshold]
        if natija and not otganlar:
            eng_yuqori = max(r.base_score for r in natija)
            logger.info(
                "Chegaradan hech kim o'tmadi: eng yuqori bazaviy ball %.1f, chegara %s — "
                "signal berilmaydi (normal holat)",
                eng_yuqori,
                f"{threshold:.0f}" if threshold is not None else "yopiq",
            )
        elif otganlar:
            toliq = sum(1 for r in otganlar if r.setup_complete)
            logger.info(
                "Chegaradan %d nomzod o'tdi, shundan %d tasida CryptoSpot3% "
                "shartnomasi to'liq bajarilgan",
                len(otganlar),
                toliq,
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
            # Chegara BAZAVIY shkalada o'lchanadi — postmortem uchun
            # ikkalasi ham kerak.
            "base_total": round(breakdown.base_total, 2),
            "setup_complete": breakdown.setup_complete,
            "components": [
                {
                    "name": komponent.name,
                    "earned": round(komponent.earned, 2),
                    "maximum": round(komponent.maximum, 2),
                    "explanation": komponent.explanation,
                    "bonus": komponent.bonus,
                }
                for komponent in breakdown.components
            ],
        },
        ensure_ascii=False,
    )


def breakdown_from_json(raw: str) -> ScoreBreakdown | None:
    """Bazada saqlangan JSON dan ball tafsilotini tiklaydi.

    NIMA UCHUN KERAK BO'LIB QOLDI: `breakdown_to_text()` yozilgan, lekin
    HECH QAYERDA CHAQIRILMAGAN edi — bot "Nega bu signal?" tugmasida
    bazadagi XOM JSON ni ko'rsatib turardi. Bu loyihaning 2-naqshi:
    "e'lon qilingan, lekin ulanmagan".

    Eski yozuvlarda `bonus` kaliti yo'q — u `False` deb olinadi.

    Buzuq yoki begona matn kelsa `None` qaytadi: chaqiruvchi tomon
    matnning o'zini ko'rsatadi (qo'lda kiritilgan signalda izoh turadi).
    """
    try:
        xom = json.loads(raw)
        komponentlar = [
            ScoreComponent(
                name=str(k["name"]),
                earned=float(k["earned"]),
                maximum=float(k["maximum"]),
                explanation=str(k.get("explanation", "")),
                bonus=bool(k.get("bonus", False)),
            )
            for k in xom["components"]
        ]
    except (TypeError, ValueError, KeyError):
        return None
    if not komponentlar:
        return None
    return ScoreBreakdown(
        symbol=str(xom.get("symbol", "")),
        components=komponentlar,
        setup_complete=bool(xom.get("setup_complete", False)),
    )


#: Bonus omillari uchun belgi — "Nega bu signal?" ekranida ajratib turadi.
BONUS_BELGILARI = {"session_overlap": "⏰"}


def breakdown_to_text(breakdown: ScoreBreakdown) -> str:
    """3.6-band: "Nega bu signal?" tugmasi uchun o'qiladigan matn.

    TOPILMAGAN BONUS KO'RSATILMAYDI. "Liquidity Sweep topilmadi"
    qatorini chiqarish foydalanuvchini chalkashtiradi: u yo'qlikni
    kamchilik deb o'qiydi, holbuki bu omil bo'lmasligi mutlaqo normal.
    Bazaviy omillar esa DOIM ko'rsatiladi — ular ballning o'zagi.
    """
    qatorlar = [
        f"📊 {breakdown.symbol} — {breakdown.total:.0f}/{breakdown.maximum:.0f} ball",
        "",
    ]
    if breakdown.setup_complete:
        qatorlar += ["✅ CryptoSpot3% shartnomasi TO'LIQ: struktura + daraja + sweep", ""]
    for komponent in breakdown.components:
        if komponent.bonus and komponent.earned <= 0:
            continue
        if komponent.bonus:
            belgi = BONUS_BELGILARI.get(komponent.name, "✨")
            qatorlar.append(
                f"{belgi} +{komponent.earned:.0f} — {komponent.explanation}"
            )
            continue
        ulush = "▰" * round(komponent.ratio * 5) + "▱" * (5 - round(komponent.ratio * 5))
        qatorlar.append(
            f"{ulush} {komponent.earned:.0f}/{komponent.maximum:.0f} — {komponent.explanation}"
        )
    return "\n".join(qatorlar)
