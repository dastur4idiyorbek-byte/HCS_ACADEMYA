"""Isinish davri: tahlil boshlanishidan OLDIN qancha tarix kerak.

MUAMMO. Jonli tizim birjadan har bir timeframe uchun 500 tagacha sham
so'raydi — haftalik qatorda bu ~9.6 yil. Ya'ni jonli tizim ishga
tushgan zahoti Bozor Salomatligi indeksining ASOSIY omili (halol
ro'yxatning struktura kengligi, vazni 45) hisoblanadi.

Backtestda esa tarix sinov oynasining o'zi bilan cheklangan edi.
730 kunlik sinovda haftalik qatorda atigi ~104 sham bor, va
`indicators.min_candles` (60) shartiga sinovning yarmidan keyingina
yetiladi. Undan oldin `universe_facts()` BO'SH qaytardi:

    halal_structure_breadth -> 0.0  (vazn 45)
    volatility_regime       -> 0.0  (vazn 15)

Ya'ni indeksning 60 balli qismi sinovning yarmida ERISHIB
BO'LMAYDIGAN edi. Indeks 26-32 bandida qotib qolar, tizim esa
ko'tarilayotgan bozorda "kasal" degan qarorni o'qir edi.

Bu 68, 69 va 79-bo'limlardagi backtest/jonli farqlarining
davomi va aynan bir turkumdan: sinov jonli qarorni emas, boshqa
qarorni o'lchayotgan edi.

YECHIM. Isinish uzunligi ENG YUQORI timeframedan hisoblanadi va
salomatlik timeframei ham unga kiradi. Sinov oynasi qisqarmasin
uchun ma'lumot `days + warmup_days()` uchun yuklanadi: isinish
qismi tahlil qilinmaydi, faqat indikatorlarni to'ldiradi.

Bu modul BITTA manba: dvigatel nechta qadamni tashlab yuborishini,
skript esa nechta kun ortiqcha yuklashini shu yerdan o'qiydi. Ikki
joyda alohida hisoblansa, ular jimgina ajralib ketardi — 68-bo'lim
aynan shundan tug'ilgan.
"""

from __future__ import annotations

from core.config.schema import AppConfig
from core.utils.time_utils import TIMEFRAME_MINUTES

#: Isinish oxirida bir necha qadam zaxira — chegaraga tirab qo'yilgan
#: hisob bitta sham surilsa yana yetmay qolardi.
ZAXIRA_QADAM = 10


def warmup_timeframes(config: AppConfig) -> list[str]:
    """Isinishga TA'SIR QILADIGAN timeframelar.

    Salomatlik timeframei ro'yxatda: u hech bir strategiyaga
    tegishli emas, lekin indeks butun rejimni tanlaydi.
    """
    analysis = config.analysis
    return [
        analysis.entry_timeframe,
        analysis.market_health_timeframe,
        *analysis.htf_confirmation,
    ]


def _eng_yuqori_daqiqa(config: AppConfig) -> int:
    kirish = TIMEFRAME_MINUTES.get(config.analysis.entry_timeframe, 15)
    return max(
        (TIMEFRAME_MINUTES.get(tf, kirish) for tf in warmup_timeframes(config)),
        default=kirish,
    )


def warmup_steps(config: AppConfig) -> int:
    """Kirish timeframeidagi necha qadam tahlilsiz o'tkaziladi."""
    kirish = TIMEFRAME_MINUTES.get(config.analysis.entry_timeframe, 15)
    nisbat = max(1, _eng_yuqori_daqiqa(config) // kirish)
    return config.analysis.indicators.min_candles * nisbat + ZAXIRA_QADAM


def warmup_days(config: AppConfig) -> int:
    """Sinov oynasidan TASHQARI yuklanadigan kunlar soni.

    Yuqoriga yaxlitlanadi: kam yuklab isinishga yetmaganidan ko'ra,
    bir necha kun ortiqcha yuklagan afzal.
    """
    daqiqa = _eng_yuqori_daqiqa(config)
    kerakli_daqiqa = (config.analysis.indicators.min_candles + 1) * daqiqa
    return -(-kerakli_daqiqa // 1440)  # ceil
