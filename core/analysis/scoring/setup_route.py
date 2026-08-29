"""CryptoSpot3% MUSTAQIL kirish yo'li — ikkinchi darvoza.

NIMA UCHUN BU KERAK BO'LDI
--------------------------
Birinchi yozuvda metodika omillari faqat BONUS berardi: ular nomzodni
yuqoriga suradi, lekin chegaradan o'tkaza olmasdi. Bu yechim bir
tomonlama edi va aslida yangi modulni ishlatmasdi ham.

O'ylab ko'ring: eski modul 10 kunda 3 ta signal bergan bo'lsa, yangi
modul o'sha uchtasini QAYTA TARTIBLAB chiqadi, xolos. U hech qachon
"mana bu ham yaxshi kirish" deya olmaydi. Ya'ni metodikaning butun
kuchi — sweep + struktura naqshini TOPISH qobiliyati — reyting
bezagiga aylanib qolgan edi.

Metodikaning o'zi esa TO'LIQ KIRISH SHARTNOMASINI tavsiflaydi:

    1. Trend yo'nalishi SMC orqali aniqlanadi (HH/HL)
    2. Narx muhim darajaga yaqinlashadi
    3. Liquidity Sweep kutiladi — daraja "yalab o'tiladi"
    4. Sweep'dan keyin struktura o'zgarishi tasdiqlanadi (BOS)
    5. Kirish — POI zonasida

Bu — o'z-o'zicha yetarli kirish sababi, "qo'shimcha ball" emas.

IKKI YO'L, BITTA DARVOZA
------------------------
Endi nomzod ikki yo'ldan biri bilan o'tadi:

    A yo'li — KLASSIK:  bazaviy ball >= chegara (50/55)
    B yo'li — SETUP:    metodikaning to'liq shartnomasi bajarildi
                        VA bazaviy ball pastki poldan yuqori

Ular BIR-BIRINI TO'LDIRADI, almashtirmaydi. A yo'li "hamma omillar
o'rtacha yaxshi" degan holatni ushlaydi; B yo'li esa "ayrim omillar
o'rtacha, lekin TUZILMA mukammal" degan holatni — aynan o'sha holat
klassik ball tizimida yo'qolib ketardi, chunki support'da xarid
qilinganda MACD hali kesmagan, RSI o'rta zonada bo'ladi.

NIMA UCHUN B YO'LIDA HAM POL BOR
-------------------------------
`min_base_score` — bu sifat chegarasi emas, XAVFSIZLIK poli. Nomzod
bu yergacha yetib kelgan bo'lsa, uning Stop/TP darajalari va R/R
nisbati allaqachon tekshirilgan (`build_levels`, 3.3-band). Pol esa
"tuzilma chiroyli, lekin qolgan hammasi yomon" holatini kesadi.

Shartlar QAT'IY va BIRGALIKDA talab qilinadi: har biri alohida
kamdan-kam uchraydi, uchalasi birga esa haqiqatan noyob. Shuning
uchun bu yo'l darvozani yuvib yubormaydi — o'lchov
`scripts/cryptospot3_olchov.py` da.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.level_types import LevelType
from core.analysis.market_structure import MarketStructure
from core.analysis.support_resistance.liquidity import LiquiditySweep
from core.config.schema import SetupRouteConfig
from core.domain.enums import TrendDirection


@dataclass(frozen=True, slots=True)
class SetupVerdict:
    """Metodikaning to'liq shartnomasi bajarildimi."""

    qualified: bool
    #: Har bir shart alohida — "nega o'tmadi" degan savolga javob
    parts: dict[str, bool]
    reason: str

    @property
    def failed(self) -> list[str]:
        return [nom for nom, ok in self.parts.items() if not ok]


#: Bo'sh hukm — qatlam o'chirilgan yoki ma'lumot yetmagan holat
BOSH_HUKM = SetupVerdict(False, {}, "CryptoSpot3% shartnomasi tekshirilmadi")


def evaluate_setup(
    structure: MarketStructure | None,
    level_type: LevelType,
    sweep: LiquiditySweep | None,
    config: SetupRouteConfig,
) -> SetupVerdict:
    """Metodikaning to'liq kirish shartnomasini baholaydi.

    Uchala shart ham bajarilishi kerak — bu ATAYLAB qat'iy. Yumshoq
    "uchtadan ikkitasi" qoidasi qo'yilsa, yo'l darvozani yuvib
    yuborardi va chegara ma'nosini yo'qotardi.
    """
    if not config.enabled or structure is None:
        return BOSH_HUKM

    yonalish = structure.direction is TrendDirection.UP
    if yonalish and config.require_bos:
        yonalish = structure.last_bos is not None

    yalash = sweep is not None and sweep.bars_since <= config.max_sweep_age_bars
    daraja = level_type.confidence >= config.min_level_confidence

    qismlar = {"yo'nalish": yonalish, "yalash": yalash, "daraja": daraja}
    otdi = all(qismlar.values())

    if otdi:
        sabab = (
            f"CryptoSpot3% shartnomasi to'liq: {structure.describe()}; "
            f"{level_type.label}; {sweep.describe() if sweep else ''}"
        )
    else:
        yetmagan = [nom for nom, ok in qismlar.items() if not ok]
        sabab = f"CryptoSpot3% shartnomasi to'liq emas — yetmagan: {', '.join(yetmagan)}"

    return SetupVerdict(qualified=otdi, parts=qismlar, reason=sabab)
