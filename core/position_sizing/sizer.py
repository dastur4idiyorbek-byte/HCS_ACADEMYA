"""5.1-band: pozitsiya hajmi hisoblagichi.

MUHIM CHEGARA (spetsifikatsiyadan): bu — moliyaviy maslahat yoki pul
boshqaruvi EMAS. Bot hech qachon haqiqiy hisobga ulanmaydi, pulni ushlab
turmaydi, "shuncha oling/soting" demaydi. Bu — hisob-kitob yordamchisi.

Formula:
    Xavf qilinadigan pul   = Balans × bitta savdo uchun xavf foizi
    Tavsiya etilgan miqdor = Xavf qilinadigan pul ÷ Stop masofasi (%)

SPOT CHEKLOVI: Stop masofasi kichik bo'lsa (3.3-band: 1% gacha), formula
balansdan katta pozitsiya beradi. Spot savdoda leverage yo'q, shuning uchun
natija `max_position_pct_of_balance` bilan kesiladi va foydalanuvchiga
ochiq aytiladi — jim qisqartirish ishonchni yo'qotadi.
"""

from __future__ import annotations

from core.config.schema import PositionSizingConfig
from core.domain.models import PositionSuggestion, SignalLevels
from core.position_sizing.budget import DailyRiskBudget, resolve_daily_risk_pct

BUDGET_EXHAUSTED_NOTE = (
    "Bugungi xavf chegarangiz tugadi — yangi pozitsiya uchun byudjet qolmadi."
)
CAPPED_NOTE_TEMPLATE = (
    "Spot savdoda leverage yo'q. Xavf byudjeti bo'yicha hisoblangan hajm "
    "${raw:,.2f} bo'lardi, lekin mablag' ulushingiz ${capped:,.2f} — shuning "
    "uchun shu miqdor tavsiya etiladi. Bu holda haqiqiy xavfingiz "
    "${effective_risk:,.2f} (kunlik byudjetdan ancha past — bu xavfsiz tomon)."
)
NO_CAPITAL_NOTE = (
    "Bo'sh mablag'ingiz qolmadi — mavjud pozitsiyalar balansni to'liq band qilgan."
)


class PositionSizer:
    """Pozitsiya hajmi tavsiyasini hisoblaydi."""

    def __init__(self, config: PositionSizingConfig) -> None:
        self._config = config

    def budget_for(self, balance: float) -> DailyRiskBudget:
        """Balansga mos kunlik xavf byudjetini yaratadi (5.1-band pog'onalari)."""
        pct = resolve_daily_risk_pct(balance, self._config.risk_tiers)
        return DailyRiskBudget(balance=balance, daily_risk_pct=pct)

    def suggest(
        self,
        symbol: str,
        levels: SignalLevels,
        budget: DailyRiskBudget,
        commit: bool = False,
    ) -> PositionSuggestion:
        """Bitta signal uchun tavsiya.

        Args:
            commit: `True` bo'lsa xavf byudjetdan ajratiladi (foydalanuvchi
                "Men kirdim" deganda). `False` — faqat ko'rsatish uchun
                hisob-kitob, byudjetga tegmaydi.
        """
        stop_pct = levels.stop_distance_pct
        if stop_pct <= 0:
            raise ValueError("Stop masofasi musbat bo'lishi kerak")

        planned_risk = budget.next_allocation(self._config)

        if planned_risk <= 0:
            return PositionSuggestion(
                symbol=symbol,
                balance=budget.balance,
                daily_risk_pct=budget.daily_risk_pct,
                daily_budget_usd=budget.total_usd,
                remaining_budget_usd=budget.remaining_usd,
                risk_amount_usd=0.0,
                position_size_usd=0.0,
                stop_distance_pct=stop_pct,
                units=0.0,
                entry=levels.entry,
                within_daily_limit=False,
                note=BUDGET_EXHAUSTED_NOTE,
            )

        # Kapital cheklovi tufayli haqiqiy xavf rejalashtirilgandan kam bo'lishi
        # mumkin — shuning uchun avval hajmni aniqlaymiz, keyin haqiqiy xavfni
        # byudjetdan ajratamiz. Aks holda byudjet yo'qdan band bo'lib qolardi.
        risk_amount = planned_risk

        raw_position = risk_amount / (stop_pct / 100)
        # Uch bosqichli cheklov:
        #   (a) bitta pozitsiya balansdan oshmaydi (leverage yo'q),
        #   (b) barcha ochiq pozitsiyalar yig'indisi balansdan oshmaydi,
        #   (c) kapital ham xavf byudjeti kabi taqsimlanadi, aks holda
        #       birinchi signal keyingilariga joy qoldirmaydi.
        max_position = min(
            budget.balance * self._config.max_position_pct_of_balance / 100,
            budget.available_capital,
            budget.next_capital_share(self._config),
        )
        position = min(raw_position, max_position)

        if position <= 0:
            return PositionSuggestion(
                symbol=symbol,
                balance=budget.balance,
                daily_risk_pct=budget.daily_risk_pct,
                daily_budget_usd=budget.total_usd,
                remaining_budget_usd=budget.remaining_usd,
                risk_amount_usd=0.0,
                position_size_usd=0.0,
                stop_distance_pct=stop_pct,
                units=0.0,
                entry=levels.entry,
                within_daily_limit=False,
                note=NO_CAPITAL_NOTE,
            )

        effective_risk = min(planned_risk, position * stop_pct / 100)

        note: str | None = None
        if position < raw_position:
            note = CAPPED_NOTE_TEMPLATE.format(
                raw=raw_position,
                capped=position,
                effective_risk=effective_risk,
            )

        if commit:
            budget.commit_capital(position)
            effective_risk = budget.allocate(effective_risk)

        risk_amount = effective_risk

        return PositionSuggestion(
            symbol=symbol,
            balance=budget.balance,
            daily_risk_pct=budget.daily_risk_pct,
            daily_budget_usd=budget.total_usd,
            remaining_budget_usd=budget.remaining_usd,
            risk_amount_usd=risk_amount,
            position_size_usd=position,
            stop_distance_pct=stop_pct,
            units=position / levels.entry,
            entry=levels.entry,
            within_daily_limit=True,
            note=note,
        )
