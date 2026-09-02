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
from collections import Counter
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


#: Kirishga ruxsat berilmaganda qo'yiladigan bosqich kodlari.
#: `core/pipeline/context.py` dagi `STAGE_LABELS` shu nomlarni
#: o'qiydi — ular kodda qo'lda yozilmaydi.
KIRISH_RAD_SABABLARI: tuple[str, ...] = ("threshold", "setup_contract", "score_floor")


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """Reytingdagi bitta nomzod."""

    candidate: SignalCandidate
    rank: int
    #: Kirishga ruxsat berilmagan bo'lsa — sabab kodi, aks holda `None`.
    #: Ilgari bu yerda `passed_threshold: bool` turardi va u faqat
    #: bitta sababni ifodalay olardi. Sifat darvozasi qo'shilgach
    #: sabablar uchtaga chiqdi, ya'ni "nega o'tmadi" degan savol
    #: javobsiz qolardi.
    rejection: str | None = None
    #: CryptoSpot3% shartnomasi TO'LIQ bajarilganmi.
    setup_complete: bool = False

    @property
    def admitted(self) -> bool:
        """Nomzod kirishga ruxsat oldimi."""
        return self.rejection is None

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
        """Nomzodlarni ballga qarab saralaydi va kirishga ruxsat beradi.

        SARALASH har doim ball bo'yicha. RUXSAT esa ikki xil bo'lishi
        mumkin — `scoring.quality_gate.enabled` ga qarab.

        O'CHIQ (standart, eski mexanizm)
            Chegara BAZAVIY ballda tekshiriladi. CryptoSpot3%
            dalillari (struktura, daraja turi, sweep) aynan shu
            bazaviy ball ichida — ular S/R va trend omillarini
            ko'taradi (`factors.py`, `_uplift`), ya'ni tuzilmasi
            kuchli nomzod chegaradan o'z kuchi bilan o'tadi.

        YOQILGAN (sifat darvozasi)
            Ruxsatni DALIL beradi: CryptoSpot3% shartnomasi
            bajarilishi shart. Ball esa faqat tartiblaydi va
            xavfsizlik poli sifatida qoladi.

        NIMA UCHUN IKKINCHI YO'L QO'SHILDI. Birinchi yozuvda bu yerda
        "parallel darvoza qilinmadi, chunki dalil omil ichida" deb
        yozilgan edi. Mulohaza to'g'ri, lekin o'lchov unga qarshi
        chiqdi: to'rtta mustaqil kirish filtri sinaldi, signal soni
        610 dan 884 gacha o'zgardi, win-rate esa 36.9-39.1% bo'lib
        qoldi (`docs/BACKTEST_NATIJA_2026-09-02_6.md`).

        Sabab: ball nomzodlarni bir-biriga NISBATAN o'lchaydi. U "eng
        yaxshisi qaysi" deydi, "shu yetarlimi" demaydi. Dalilni ball
        ichiga qo'shish uni tartiblovchiga aylantiradi, qaror
        qiluvchiga emas.

        Bonus (Kill Zone) hech qaysi yo'lda ruxsatga kirmaydi: u
        kirish vaqti haqida, tuzilma haqida emas.

        Args:
            threshold: minimal BAZAVIY ball. `None` — Bozor Salomatligi
                past, hech kim o'tmaydi (3.5-band).
        """
        tartiblangan = sorted(candidates, key=lambda c: c.score, reverse=True)

        natija = [
            RankedCandidate(
                candidate=nomzod,
                rank=index + 1,
                rejection=self._kirish_rad_sababi(nomzod, threshold),
                setup_complete=nomzod.setup_qualified,
            )
            for index, nomzod in enumerate(tartiblangan)
        ]

        otganlar = [r for r in natija if r.admitted]
        if natija and not otganlar:
            sabablar = Counter(r.rejection for r in natija)
            logger.info(
                "Kirishga hech kim o'tmadi: eng yuqori bazaviy ball %.1f, "
                "chegara %s, sabablar %s — signal berilmaydi (normal holat)",
                max(r.base_score for r in natija),
                f"{threshold:.0f}" if threshold is not None else "yopiq",
                dict(sabablar),
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

    def _kirish_rad_sababi(
        self, nomzod: SignalCandidate, threshold: float | None
    ) -> str | None:
        """Nomzod kirishga ruxsat oldimi — olmasa, NEGA.

        BALL FAQAT TARTIBLAYDI (sifat darvozasi yoqilganda).

        Ball nomzodlarni bir-biriga NISBATAN o'lchaydi: u "eng
        yaxshisi qaysi" deydi, "shu yetarlimi" demaydi. Darvoza faqat
        balldan iborat bo'lsa, tizim uyumning eng yuqorisini oladi —
        uyumning o'zi yomon bo'lsa ham.

        Yoqilganda qaror DALILGA o'tadi: CryptoSpot3% shartnomasi
        (yo'nalish + yalash + daraja turi) bajarilishi shart. Ball
        esa faqat tartiblaydi va xavfsizlik poli sifatida qoladi.
        """
        if threshold is None:
            # Bozor Salomatligi past — chegara umuman yopiq (3.5-band).
            return "threshold"

        ball = nomzod.breakdown.base_total
        darvoza = self._config.scoring.quality_gate
        if not darvoza.enabled:
            return None if ball >= threshold else "threshold"

        if darvoza.require_setup_contract and not nomzod.setup_qualified:
            return "setup_contract"
        if ball < darvoza.min_base_score:
            return "score_floor"
        return None

    @staticmethod
    def passed(ranked: list[RankedCandidate]) -> list[SignalCandidate]:
        """Chegaradan o'tgan nomzodlar, eng yuqori balldan boshlab."""
        return [r.candidate for r in ranked if r.admitted]


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
