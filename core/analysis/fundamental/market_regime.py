"""1.1 — Bozor holati: Funding Rate + Open Interest + DXY.

QOIDA (2-prompt): uch ko'rsatkichdan kamida IKKITASI signal
yo'nalishiga mos bo'lsa — ✅.

Uchtasidan faqat bittasining (Funding) 2 yillik tarixi bepul mavjud.
Qolgan ikkitasi `None` bo'lib kelishi normal va bu — xato emas:
`MALUMOT_YOQ` qaytariladi, blok maxraji kichrayadi.

NIMA UCHUN "KAMIDA 2 TA" QOIDASI SAQLANADI: agar faqat bitta
ko'rsatkich mavjud bo'lsa, "2 ta mos" sharti hech qachon bajarilmaydi
va tekshiruv doim ❌ chiqardi — ya'ni jimgina o'lik qoida. Shuning
uchun shart MAVJUD ko'rsatkichlarga nisbatan hisoblanadi: mavjudlarning
KO'PCHILIGI mos bo'lsa ✅ (1 tadan 1, 2 tadan 2, 3 tadan 2).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.turlar import Tekshiruv, ha, malumot_yoq, yoq

#: Funding rate shundan yuqori bo'lsa — bozor "qizigan", long tomon
#: haddan tashqari to'lgan. Ko'tarilish signali uchun bu SALBIY belgi.
#:
#: 🔴 O'LCHANMAGAN. 0.01% (kunlik ~0.03%) — Binance'ning "normal"
#: darajasi sifatida keng qabul qilingan qiymat, lekin BIZ uni
#: o'lchamaganmiz. Backtest orqali topiladi.
FUNDING_QIZIGAN = 0.0001

#: Funding manfiy va shundan past bo'lsa — short tomon to'lgan,
#: ko'tarilish uchun IJOBIY belgi (short squeeze yoqilg'isi).
FUNDING_SOVUGAN = -0.0001

#: Open Interest shu foizdan ko'p o'ssa — yangi pul kirdi.
OI_OSISH_PCT = 5.0

#: DXY shu foizdan ko'p tushsa — dollar zaiflashdi, risk aktivlarga ijobiy.
DXY_TUSHISH_PCT = 0.5


@dataclass(frozen=True, slots=True)
class BozorHolati:
    """1.1 uchun xom ma'lumot. Har biri `None` bo'lishi mumkin."""

    #: Oxirgi funding rate (kasr: 0.0001 = 0.01%)
    funding_rate: float | None = None
    #: Open Interest 24 soatlik o'zgarishi, foizda
    oi_ozgarish_pct: float | None = None
    #: DXY (dollar indeksi) 24 soatlik o'zgarishi, foizda
    dxy_ozgarish_pct: float | None = None


def bozor_holati(malumot: BozorHolati) -> Tekshiruv:
    """Uch ko'rsatkichning KO'PCHILIGI ko'tarilishga mos bo'lsa ✅.

    Faqat LONG yo'nalish tekshiriladi — loyiha spot, long-only
    (`docs/ARXITEKTURA.md`). Short yo'nalish uchun teskari mantiq
    yozilmaydi: yozilsa, u hech qachon chaqirilmaydigan o'lik
    tarmoq bo'lardi.
    """
    ovozlar: list[bool] = []
    sabablar: list[str] = []

    if malumot.funding_rate is not None:
        # Funding SOVUQ bo'lsa ko'tarilishga ijobiy: shortlar to'lagan,
        # ya'ni yuqoriga siqib chiqarish uchun yoqilg'i bor.
        mos = malumot.funding_rate <= FUNDING_SOVUGAN
        ovozlar.append(mos)
        sabablar.append(f"funding {malumot.funding_rate * 100:.4f}%")

    if malumot.oi_ozgarish_pct is not None:
        mos = malumot.oi_ozgarish_pct >= OI_OSISH_PCT
        ovozlar.append(mos)
        sabablar.append(f"OI {malumot.oi_ozgarish_pct:+.1f}%")

    if malumot.dxy_ozgarish_pct is not None:
        mos = malumot.dxy_ozgarish_pct <= -DXY_TUSHISH_PCT
        ovozlar.append(mos)
        sabablar.append(f"DXY {malumot.dxy_ozgarish_pct:+.2f}%")

    if not ovozlar:
        return malumot_yoq("bozor_holati", "funding/OI/DXY — hech biri yo'q")

    kerak = _kopchilik(len(ovozlar))
    mos_soni = sum(ovozlar)
    izoh = f"{mos_soni}/{len(ovozlar)} mos ({', '.join(sabablar)})"
    return ha("bozor_holati", izoh) if mos_soni >= kerak else yoq("bozor_holati", izoh)


def _kopchilik(jami: int) -> int:
    """Nechta ovoz kerak.

    1 tadan 1, 2 tadan 2, 3 tadan 2. Uchta ko'rsatkichda promptdagi
    "kamida 2 ta" sharti aynan saqlanadi; kamroq ko'rsatkichda esa
    shart mavjudlariga MOSLASHADI — aks holda qoida o'lik bo'lardi.
    """
    return jami if jami <= 2 else 2
