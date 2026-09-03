"""Ikki birja narxini solishtirish — tasodifiy "wick" ni rad etish.

2-promptning 2-qismi: Bitget faqat "Binance'da yo'q coin" uchun emas,
IKKINCHI FIKR uchun ham kerak.

MUAMMO NIMADA. Bitta birjada likvidlik yupqalashganda narx bir necha
soniyaga keskin sakraydi va sham uzun "wick" bilan yopiladi. Tahlil
uchun bu wick — YOLG'ON ma'lumot: u bozorning fikri emas, bitta
birjadagi bitta katta buyurtmaning izi. Eski tizim bunday wickni
haqiqiy Swing Low deb o'qib, zonani noto'g'ri joyga qo'yardi.

YECHIM. Ikkala birjaning AYNAN SHU vaqtdagi shami solishtiriladi.
Farq chegaradan katta bo'lsa — sham SHUBHALI deb belgilanadi.

MUHIM QAROR — shubhali sham O'CHIRILMAYDI, BELGILANADI. Uni o'chirish
qatorda teshik qoldirardi va indikatorlar jimgina siljib ketardi.
Belgilangan shamni chaqiruvchi o'zi hal qiladi: struktura moduli uni
Swing nuqta sifatida QABUL QILMAYDI, lekin narx qatorida qoladi.

NIMA UCHUN faqat wick solishtiriladi, close emas: ikki birjaning
close narxi tabiiy ravishda ozgina farq qiladi (arbitraj oynasi), va
bu farq normal. Anomaliya esa AYNAN uchida ko'rinadi — bitta birjada
low 2% pastga tushib, ikkinchisida umuman tushmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from core.domain.models import Candle
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Ikki birja wicki shu foizdan ko'p ajralsa — shubhali.
#:
#: 🔴 O'LCHANMAGAN. Boshlang'ich qiymat: 1.0%. Backtest orqali
#: topiladi (2-prompt, 0-qism, 3-tamoyil: taxminiy raqam qolmaydi).
#: Juda past bo'lsa har ikkinchi sham shubhali chiqadi; juda yuqori
#: bo'lsa filtr umuman ishlamaydi.
STANDART_CHEGARA_PCT = 1.0


@dataclass(frozen=True, slots=True)
class Solishtiruv:
    """Bitta shamning ikki birjadagi holati."""

    open_time: datetime
    #: Yuqori uchdagi farq, foizda (musbat — asosiy birjada balandroq)
    high_farq_pct: float
    #: Pastki uchdagi farq, foizda (musbat — asosiy birjada pastroq)
    low_farq_pct: float
    shubhali: bool
    #: Nima uchun shubhali — log va admin monitori uchun
    sabab: str | None = None


def solishtir(
    asosiy: list[Candle],
    ikkinchi: list[Candle],
    chegara_pct: float = STANDART_CHEGARA_PCT,
) -> dict[datetime, Solishtiruv]:
    """Ikki qatorni vaqt bo'yicha juftlab solishtiradi.

    FAQAT IKKALASIDA HAM BOR shamlar solishtiriladi. Bitget'da
    yo'q sham — bu ma'lumot yo'qligi, anomaliya emas: yangi coin
    bitta birjada ertaroq listing bo'lishi odatiy hol. Bunday
    shamlar natijaga umuman kirmaydi, ya'ni "shubhali emas" deb
    ham belgilanmaydi (fail-safe: yo'q ma'lumot — tasdiq emas).

    Args:
        asosiy: Binance shamlari (yoki qaysi birja asosiy bo'lsa)
        ikkinchi: Bitget shamlari
        chegara_pct: wick farqi shundan oshsa — shubhali

    Returns:
        `open_time` -> `Solishtiruv`. Faqat juftlashgan shamlar.
    """
    xarita = {sham.open_time: sham for sham in ikkinchi}
    natija: dict[datetime, Solishtiruv] = {}

    for sham in asosiy:
        juft = xarita.get(sham.open_time)
        if juft is None:
            continue

        high_farq = _farq_pct(sham.high, juft.high)
        low_farq = _farq_pct(juft.low, sham.low)

        sabab = None
        if high_farq > chegara_pct:
            sabab = f"yuqori uch {high_farq:.2f}% ajralgan"
        elif low_farq > chegara_pct:
            sabab = f"pastki uch {low_farq:.2f}% ajralgan"

        natija[sham.open_time] = Solishtiruv(
            open_time=sham.open_time,
            high_farq_pct=high_farq,
            low_farq_pct=low_farq,
            shubhali=sabab is not None,
            sabab=sabab,
        )

    return natija


def _farq_pct(katta: float, kichik: float) -> float:
    """Ikki narx orasidagi farq, KICHIGIGA nisbatan foizda.

    Manfiy qiymat qaytmaydi: bizni "asosiy birja qaysi tomonga
    ajralgan" emas, "qanchalik ajralgan" qiziqtiradi. Yo'nalish
    `solishtir()` da alohida ikki maydonda saqlanadi.
    """
    if kichik <= 0:
        return 0.0
    return max(0.0, (katta - kichik) / kichik * 100)


def shubhali_vaqtlar(solishtiruvlar: dict[datetime, Solishtiruv]) -> set[datetime]:
    """Struktura moduli uchun tayyor to'plam — Swing nuqtada rad etiladi."""
    return {vaqt for vaqt, s in solishtiruvlar.items() if s.shubhali}


def qamrov_pct(asosiy: list[Candle], solishtiruvlar: dict[datetime, Solishtiruv]) -> float:
    """Asosiy qatorning necha foizi solishtirilgan.

    Bu raqam kerak, chunki qamrov past bo'lsa filtr ISHLAMAYDI, lekin
    ishlayotgandek ko'rinadi. Masalan Bitget'da coin faqat 3 oydan
    beri bor bo'lsa, 2 yillik backtestda qamrov ~12% chiqadi — ya'ni
    shamlarning 88% i tekshirilmagan. Buni bilmasdan "wick filtri
    yoqilgan" deb hisoblash — o'zini aldash.
    """
    if not asosiy:
        return 0.0
    return len(solishtiruvlar) / len(asosiy) * 100
