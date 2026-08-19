"""5.1.1-band: kunlik xavf byudjeti va uni faol signallar orasida taqsimlash.

MUHIM (spetsifikatsiyadan): "Signal Stop foizi" va "kunlik balans limiti" —
ikki xil tushuncha, aralashtirilmaydi.

    Kunlik xavf byudjeti ($) = Balans × Kunlik limit foizi
    Har bir signalga ajratiladigan xavf = qolgan byudjetdan ulush

Ikki usul qo'llab-quvvatlanadi (admin tanlaydi):
  1. `sequential_decay` (tavsiya etiladi) — har yangi signalga o'sha paytdagi
     QOLGAN byudjetdan standart foiz ajratiladi. Byudjet hech qachon
     tugamaydi, faqat kichrayib boradi.
  2. `equal_split` — kutilayotgan N ta signal orasida teng bo'linadi.

TEKSHIRISH SHARTI (spetsifikatsiyada test sifatida belgilangan): qaysi usul
tanlanmasin, barcha faol signallar bir vaqtda Stop yesa, jami zarar kunlik
limit foizidan OSHMASLIGI kerak. Bu `tests/core/test_position_sizing.py` da
sinaladi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.config.schema import PositionSizingConfig, RiskTier
from core.domain.enums import AllocationMethod


def resolve_daily_risk_pct(balance: float, tiers: list[RiskTier]) -> float:
    """5.1-band: balans darajasiga qarab pog'onali kunlik xavf foizi.

    Pog'onalar `max_balance` bo'yicha o'sish tartibida bo'lishi kerak
    (buni konfiguratsiya tekshiruvi kafolatlaydi), oxirgisi `None` — cheksiz.
    """
    if balance < 0:
        raise ValueError("Balans manfiy bo'lishi mumkin emas")
    if not tiers:
        raise ValueError("Risk pog'onalari (risk_tiers) aniqlanmagan")

    for tier in tiers:
        if tier.max_balance is None or balance <= tier.max_balance:
            return tier.daily_risk_pct
    return tiers[-1].daily_risk_pct


@dataclass(slots=True)
class DailyRiskBudget:
    """Bitta foydalanuvchining bitta kunlik xavf byudjeti.

    `allocated` — bugun ochilgan pozitsiyalarga ajratilgan xavf yig'indisi.
    `realized_loss` — allaqachon Stop bilan yopilgan zararlar.
    """

    balance: float
    daily_risk_pct: float
    allocated: float = 0.0
    realized_loss: float = 0.0
    allocations: list[float] = field(default_factory=list)
    # SPOT cheklovi: bir vaqtda ochiq pozitsiyalarga band bo'lgan kapital.
    # Xavf byudjetidan alohida hisob — xavf "qancha yo'qotishim mumkin",
    # kapital esa "qancha pulim band". Ikkalasi ham cheklanadi.
    committed_capital: float = 0.0

    @property
    def total_usd(self) -> float:
        """Kunlik xavf byudjeti, dollarda."""
        return self.balance * self.daily_risk_pct / 100

    @property
    def remaining_usd(self) -> float:
        """Hali taqsimlanmagan byudjet."""
        return max(0.0, self.total_usd - self.allocated)

    @property
    def available_capital(self) -> float:
        """Yangi pozitsiya uchun bo'sh kapital (spot: leverage yo'q)."""
        return max(0.0, self.balance - self.committed_capital)

    def commit_capital(self, amount: float) -> float:
        """Pozitsiyaga kapital band qiladi, bo'sh kapitaldan oshmagan holda."""
        granted = min(max(0.0, amount), self.available_capital)
        self.committed_capital += granted
        return granted

    def release_capital(self, amount: float) -> None:
        """Pozitsiya yopilganda kapital bo'shaydi."""
        self.committed_capital = max(0.0, self.committed_capital - max(0.0, amount))

    @property
    def used_ratio(self) -> float:
        """Byudjetning necha ulushi band (0..1) — 5.2-band agregat hisobi uchun."""
        total = self.total_usd
        return 1.0 if total <= 0 else min(1.0, self.allocated / total)

    @property
    def is_exhausted(self) -> bool:
        """5.1-band: "bugungi xavf chegarangiz tugadi"."""
        return self.remaining_usd <= 0

    def next_allocation(self, config: PositionSizingConfig) -> float:
        """Keyingi signalga ajratiladigan xavf miqdorini hisoblaydi (yozmaydi)."""
        remaining = self.remaining_usd
        if remaining <= 0:
            return 0.0

        method = AllocationMethod(config.allocation_method)
        if method is AllocationMethod.SEQUENTIAL_DECAY:
            amount = remaining * config.sequential_decay_fraction
        else:  # EQUAL_SPLIT
            free_slots = config.equal_split_expected_slots - len(self.allocations)
            amount = remaining / max(1, free_slots)

        amount = min(amount, remaining)
        return amount if amount >= config.min_allocation_usd else 0.0

    def next_capital_share(self, config: PositionSizingConfig) -> float:
        """Keyingi signalga ajratiladigan KAPITAL ulushi.

        Nima uchun kerak: spot savdoda Stop masofasi kichik bo'lsa (3.3-band:
        1% gacha), xavf byudjetidan kelib chiqqan pozitsiya balansdan bir necha
        marta katta chiqadi. Agar kapital taqsimlanmasa, birinchi signal butun
        balansni band qilib, keyingilariga joy qoldirmaydi.

        Shuning uchun kapital ham xavf byudjeti bilan BIR XIL usulda
        taqsimlanadi — natijada bir necha signal birga yashay oladi.
        """
        available = self.available_capital
        if available <= 0:
            return 0.0

        method = AllocationMethod(config.allocation_method)
        if method is AllocationMethod.SEQUENTIAL_DECAY:
            share = available * config.sequential_decay_fraction
        else:  # EQUAL_SPLIT
            free_slots = config.equal_split_expected_slots - len(self.allocations)
            share = available / max(1, free_slots)
        return min(share, available)

    def allocate(self, amount: float) -> float:
        """Byudjetdan xavf ajratadi. Qolgan byudjetdan oshsa — kesiladi.

        Bu — invariantning kod darajasidagi kafolati: `allocated` hech qachon
        `total_usd` dan oshmaydi.
        """
        if amount <= 0:
            return 0.0
        granted = min(amount, self.remaining_usd)
        if granted <= 0:
            return 0.0
        self.allocated += granted
        self.allocations.append(granted)
        return granted

    def sub_budget(self, share_pct: float) -> StrategyBudget:
        """3.9-band: strategiyaga umumiy byudjetdan ulush ajratadi.

        Qo'shimcha strategiya (masalan skalping) o'z byudjeti bilan ishlaydi,
        lekin u umumiy kunlik limitning ICHIDA. Shu sababli `StrategyBudget`
        mustaqil hisob yuritmaydi — u asosiy byudjetdan ajratadi va uning
        cheklovlariga bo'ysunadi.

        Args:
            share_pct: umumiy kunlik byudjetdan ulush, foizda.
        """
        if not 0 < share_pct <= 100:
            raise ValueError("Ulush (0, 100] oralig'ida bo'lishi kerak")
        return StrategyBudget(parent=self, share_pct=share_pct)

    def release(self, amount: float) -> None:
        """5.2-band: signal TP'ga borsa, limit "bo'shaydi"."""
        if amount <= 0:
            return
        self.allocated = max(0.0, self.allocated - amount)
        if amount in self.allocations:
            self.allocations.remove(amount)

    def register_loss(self, amount: float) -> None:
        """Stop bilan yopilgan zararni qayd etadi (4.1-band kunlik chegara uchun)."""
        self.realized_loss += max(0.0, amount)

    @property
    def realized_loss_pct(self) -> float:
        """Bugungi realizatsiya qilingan zarar, balansdan foizda."""
        return 0.0 if self.balance <= 0 else self.realized_loss / self.balance * 100


@dataclass(slots=True)
class StrategyBudget:
    """Bitta strategiyaga ajratilgan byudjet ulushi (3.9-band).

    MUHIM: bu mustaqil byudjet EMAS. U asosiy `DailyRiskBudget` dan ajratadi,
    shuning uchun ikki strategiya birgalikda ham kunlik limitdan oshmaydi —
    spetsifikatsiyaning aniq talabi.
    """

    parent: DailyRiskBudget
    share_pct: float
    allocated: float = 0.0

    @property
    def total_usd(self) -> float:
        """Shu strategiyaga ajratilgan yuqori chegara."""
        return self.parent.total_usd * self.share_pct / 100

    @property
    def remaining_usd(self) -> float:
        """Qolgan byudjet — strategiya ulushi VA umumiy qoldiqning kichigi.

        Ikkinchi shart muhim: asosiy strategiya byudjetni to'liq ishlatgan
        bo'lsa, skalping o'z ulushi qolganiga qaramay signal bera olmaydi.
        """
        oz_ulushi = max(0.0, self.total_usd - self.allocated)
        return min(oz_ulushi, self.parent.remaining_usd)

    @property
    def is_exhausted(self) -> bool:
        return self.remaining_usd <= 0

    def allocate(self, amount: float) -> float:
        """Byudjetdan xavf ajratadi — ham o'z ulushidan, ham umumiydan."""
        if amount <= 0:
            return 0.0
        beriladigan = min(amount, self.remaining_usd)
        if beriladigan <= 0:
            return 0.0
        berildi = self.parent.allocate(beriladigan)
        self.allocated += berildi
        return berildi

    def release(self, amount: float) -> None:
        if amount <= 0:
            return
        self.allocated = max(0.0, self.allocated - amount)
        self.parent.release(amount)
