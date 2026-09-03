"""3.4 — Volume Profile: POC (Point of Control) va yuqori hajmli tugun.

TA'RIF: narx oralig'i N ta savatga bo'linadi, har savatga o'sha
oraliqda savdo qilingan hajm yig'iladi. Eng ko'p hajmli savat — POC.

NIMA UCHUN MUHIM: POC — bozor eng ko'p "kelishgan" narx. Unga
yaqin zona kuchliroq: u yerda haqiqiy buyurtmalar bor, shunchaki
grafikdagi chiziq emas.

SODDALASHTIRISH — HAJM SHAM ICHIDA TEKIS TAQSIMLANADI. Haqiqiy
volume profile har bir savdoni alohida hisoblaydi; bizda faqat
OHLCV bor. Sham hajmini uning `low..high` oralig'iga tekis bo'lish
— keng qabul qilingan yaqinlashtirish. Bu ANIQLIK yo'qotadi, lekin
POC ning umumiy joyi to'g'ri chiqadi.
"""

from __future__ import annotations

from core.domain.models import Candle

#: Narx oralig'i necha savatga bo'linadi.
#: 🔴 O'LCHANMAGAN. Ko'p savat — aniqroq, lekin shovqinliroq.
SAVAT_SONI = 50

#: Zona POC dan shu foizdan yaqin bo'lsa — ✅.
#: 🔴 O'LCHANMAGAN.
POC_YAQINLIK_PCT = 2.0


def poc_narx(shamlar: list[Candle], savatlar: int = SAVAT_SONI) -> float | None:
    """Eng ko'p hajm o'tgan narx darajasi."""
    if not shamlar:
        return None

    eng_past = min(s.low for s in shamlar)
    eng_yuqori = max(s.high for s in shamlar)
    kenglik = eng_yuqori - eng_past
    if kenglik <= 0:
        return eng_past

    hajmlar = [0.0] * savatlar
    qadam = kenglik / savatlar

    for sham in shamlar:
        # Sham qaysi savatlarni qamrab oladi
        boshi = int((sham.low - eng_past) / qadam)
        oxiri = int((sham.high - eng_past) / qadam)
        boshi = max(0, min(savatlar - 1, boshi))
        oxiri = max(0, min(savatlar - 1, oxiri))
        qamrov = oxiri - boshi + 1
        ulush = sham.volume / qamrov
        for j in range(boshi, oxiri + 1):
            hajmlar[j] += ulush

    eng_kop = max(range(savatlar), key=lambda j: hajmlar[j])
    return eng_past + qadam * (eng_kop + 0.5)


def poc_yaqinmi(
    zona_markazi: float,
    poc: float | None,
    yaqinlik_pct: float = POC_YAQINLIK_PCT,
) -> bool | None:
    """Zona POC ga yaqinmi. `None` — POC hisoblanmagan."""
    if poc is None or poc <= 0:
        return None
    farq_pct = abs(zona_markazi - poc) / poc * 100
    return farq_pct <= yaqinlik_pct
