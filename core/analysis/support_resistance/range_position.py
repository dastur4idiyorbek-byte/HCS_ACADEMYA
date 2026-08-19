"""Discount / Premium zonalari — S/R diapazonini ichki bo'lish (3.1-band davomi).

Support va Resistance orasidagi diapazon ikki qismga bo'linadi:

    Resistance  ───────────────────  100%
                                            PREMIUM — narx QIMMAT
    O'rta chiziq ─ ─ ─ ─ ─ ─ ─ ─ ─    50%
                                            DISCOUNT — narx ARZON
    Support     ───────────────────    0%

Qat'iy qoida:
    Narx Support zonasida VA Discount zonada  -> OLISH ko'rib chiqiladi
    Narx Resistance zonasida VA Premium zonada -> SOTISH/chiqish ko'rib chiqiladi

Ya'ni Support yaqinida turgan narx ham, agar u diapazonning yuqori yarmida
bo'lsa (masalan oraliq juda tor), kirish uchun to'liq kuchga EGA EMAS.

Bu — S/R'dan ajralgan yangi tushuncha emas, balki doimiy qo'llaniladigan
qo'shimcha qatlam. Natijasi 3.5-banddagi "S/R zonasi sifati" (25 ball)
ichiga kiradi: narx qanchalik chuqur Discount'da bo'lsa, ball shunchalik
yuqori.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.domain.models import SRZone

#: Diapazonni ikkiga bo'luvchi chiziq
EQUILIBRIUM_PCT = 50.0


class RangeBand(str, Enum):
    """Narx diapazonning qaysi yarmida turibdi."""

    DISCOUNT = "discount"    # pastki yarim — narx arzon, kirish uchun qulay
    PREMIUM = "premium"      # yuqori yarim — narx qimmat, chiqish uchun qulay

    @property
    def emoji(self) -> str:
        return "🟩" if self is RangeBand.DISCOUNT else "🟥"

    @property
    def label_uz(self) -> str:
        return "Discount" if self is RangeBand.DISCOUNT else "Premium"


@dataclass(frozen=True, slots=True)
class RangePosition:
    """Narxning Support—Resistance diapazoni ichidagi nisbiy joylashuvi.

    `percent` 0 dan kichik yoki 100 dan katta bo'lishi mumkin: narx
    diapazondan chiqib ketgan (breakdown yoki breakout). Bu holat
    yashirilmaydi — u muhim ma'lumot.
    """

    percent: float
    support: SRZone
    resistance: SRZone
    price: float

    @property
    def band(self) -> RangeBand:
        return RangeBand.DISCOUNT if self.percent < EQUILIBRIUM_PCT else RangeBand.PREMIUM

    @property
    def is_discount(self) -> bool:
        return self.band is RangeBand.DISCOUNT

    @property
    def depth(self) -> float:
        """Zonaning chuqurligi 0..1 oralig'ida.

        Discount uchun: 0 — o'rta chiziqda, 1 — aynan Support'da.
        Premium uchun:  0 — o'rta chiziqda, 1 — aynan Resistance'da.

        Ball hisoblashda (3.5-band) aynan shu qiymat ishlatiladi: chuqurroq
        Discount — yuqoriroq ball.
        """
        cheklangan = max(0.0, min(100.0, self.percent))
        if self.is_discount:
            return (EQUILIBRIUM_PCT - cheklangan) / EQUILIBRIUM_PCT
        return (cheklangan - EQUILIBRIUM_PCT) / EQUILIBRIUM_PCT

    @property
    def is_outside_range(self) -> bool:
        """Narx diapazondan chiqib ketganmi (breakdown/breakout)."""
        return not 0.0 <= self.percent <= 100.0

    def allows_entry(self, price_in_support_zone: bool) -> bool:
        """Kirish uchun qat'iy shart: Support zonasida VA Discount zonada.

        Args:
            price_in_support_zone: narx aynan support zonasi ichidami.
        """
        return price_in_support_zone and self.is_discount and not self.is_outside_range

    def describe(self) -> str:
        """Foydalanuvchiga ko'rsatiladigan izoh (3.6-band shaffofligi)."""
        if self.percent < 0:
            return (
                f"{RangeBand.DISCOUNT.emoji} Zona: Support'dan pastda "
                f"({self.percent:.0f}%) — qo'llab-quvvatlash buzilgan"
            )
        if self.percent > 100:
            return (
                f"{RangeBand.PREMIUM.emoji} Zona: Resistance'dan yuqorida "
                f"({self.percent:.0f}%) — qarshilik yorib o'tilgan"
            )
        if self.is_discount:
            return (
                f"{self.band.emoji} Zona: {self.band.label_uz} ({self.percent:.0f}%) — "
                "Support'ga yaqin, kirish uchun qulay"
            )
        return (
            f"{self.band.emoji} Zona: {self.band.label_uz} ({self.percent:.0f}%) — "
            "Resistance'ga yaqin, kirish uchun qulay emas"
        )


def compute_range_position(
    price: float,
    support: SRZone,
    resistance: SRZone,
) -> RangePosition | None:
    """Narxning diapazon ichidagi joylashuvini foizda hisoblaydi.

    Tayanch nuqtalar — zonalarning MARKAZLARI. Chekkalarni olish diapazonni
    zona kengligiga bog'liq qilib qo'yardi: keng zona diapazonni sun'iy
    ravishda toraytirib, foizni buzardi.

    Returns:
        `RangePosition`, yoki `None` — diapazon yaroqsiz (Resistance
        Support'dan past yoki ular ustma-ust tushgan). 0.3-band bo'yicha
        bunday holatda tahlil davom etmaydi.
    """
    past = support.center
    baland = resistance.center
    diapazon = baland - past

    if diapazon <= 0:
        return None

    return RangePosition(
        percent=(price - past) / diapazon * 100,
        support=support,
        resistance=resistance,
        price=price,
    )
