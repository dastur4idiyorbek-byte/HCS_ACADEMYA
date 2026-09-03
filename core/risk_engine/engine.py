"""4-bo'lim: Risk Engine — umumiy nazorat qatlami.

Barcha strategiyalar signalni foydalanuvchiga yetkazishdan oldin MAJBURIY
ravishda shu qatlamdan o'tadi. Mantiq — "VA" (AND): barcha qoidalar ruxsat
berishi kerak.

Nima uchun barcha qoidalar tekshiriladi (birinchisida to'xtamasdan): admin
dashboardi "signal nega berilmadi?" savoliga TO'LIQ javob ko'rsatishi kerak
— bitta sabab emas, hammasi. Bu 3.8-banddagi postmortem tahlili uchun ham
zarur.
"""

from __future__ import annotations

from datetime import datetime

from core.config.schema import AppConfig
from core.domain.enums import BlockReason
from core.domain.models import RiskDecision, SignalCandidate
from core.risk_engine.context import RiskContext
from core.risk_engine.rules import (
    ConsecutiveLossRule,
    CorrelationRule,
    DailyLossLimitRule,
    FreshDataRule,
    FridayPrayerRule,
    HalalRule,
    KillSwitchRule,
    MaxOpenSignalsRule,
    RiskRule,
)
from core.utils.logging_setup import get_logger
from core.utils.time_utils import utc_now

logger = get_logger(__name__)


def build_default_rules(config: AppConfig) -> list[RiskRule]:
    """Tahlildan MUSTAQIL xavfsizlik qoidalari.

    2026-09-03 da qisqartirildi. Eski tahlil moduli olib tashlanganda
    unga bog'liq beshta qoida ham ketdi (`rules.py` sarlavhasiga qarang).
    Bu yerda qolganlar signal QANDAY tug'ilganidan qat'i nazar amal
    qiladi — shuning uchun yangi modul kelganda ular o'zgarmaydi.
    """
    risk = config.risk_engine

    return [
        KillSwitchRule(risk),
        FridayPrayerRule(risk),
        ConsecutiveLossRule(risk),
        DailyLossLimitRule(risk),
        MaxOpenSignalsRule(risk),
        CorrelationRule(risk),
        FreshDataRule(risk, max_age_seconds=risk.max_candle_age_seconds),
        HalalRule(),
    ]


class RiskEngine:
    """Signal nomzodini barcha risk qoidalaridan o'tkazadi."""

    def __init__(self, config: AppConfig, rules: list[RiskRule] | None = None) -> None:
        self._config = config
        self._rules = rules if rules is not None else build_default_rules(config)

    @property
    def rules(self) -> list[RiskRule]:
        return list(self._rules)

    def suspended_rules(self, now: datetime | None = None) -> set[str]:
        """Sinov davrida vaqtincha to'xtatilgan qoidalar nomi.

        Bular BOZORNI emas, BIZNING holatimizni o'lchaydi: bugungi
        zararimiz, nechta signalimiz ochiq, ketma-ket nechta Stop
        yedik. 100 kunlik kuzatuvda ular namunani qiyshaytiradi —
        yomon ertalakdan keyin tizim o'zini o'chiradi va qolgan kunni
        umuman ko'rmaymiz.

        Bozorga oid va diniy qoidalar bu ro'yxatga TUSHMAYDI — ular
        strategiyaning o'zi, kuzatiladigan narsaning bir qismi.
        """
        sinov = self._config.sinov
        lahza = now or utc_now()
        if not sinov.faolmi(lahza):
            return set()
        return set(sinov.suspend_risk_rules)

    def evaluate(self, candidate: SignalCandidate, context: RiskContext) -> RiskDecision:
        """Nomzodni baholaydi. Barcha rad sabablari yig'iladi."""
        qaror = RiskDecision.allow()
        toxtatilgan = self.suspended_rules(context.now)

        for rule in self._rules:
            if rule.name in toxtatilgan:
                # Sinov davri: JIM O'TKAZIB YUBORILMAYDI — sabab logda
                # qoladi, ekranda esa sinov yozuvi turadi.
                logger.debug("Sinov davri: '%s' qoidasi tekshirilmadi", rule.name)
                continue
            try:
                natija = rule.check(candidate, context)
            except Exception:  # noqa: BLE001
                # 0.3-band: bitta qoidaning nosozligi butun tizimni to'xtatmaydi,
                # lekin noaniqlikda signal BERILMAYDI.
                logger.exception("Risk qoidasi xato berdi: %s", rule.name)
                natija = RiskDecision.block(
                    BlockReason.INTERNAL_ERROR,
                    f"'{rule.name}' qoidasi tekshirilmadi (ichki xato) — "
                    "xavfsizlik uchun signal berilmaydi.",
                )
            qaror = qaror.merged_with(natija)

        if not qaror.allowed:
            logger.info(
                "Signal to'xtatildi: %s | sabablar: %s",
                candidate.symbol,
                ", ".join(r.value for r in qaror.reasons),
            )
        return qaror
