"""4.3 — RSI(14) va narx-RSI divergensiyasi.

RSI QAYTA YOZILDI. Eski `core/analysis/indicators/` o'chirilgan
(1-prompt), va uni qaytarish o'sha modulning butun bog'liqligini
qaytarardi. Bu yerda faqat BITTA indikator bor va u faqat shu
tekshiruv uchun ishlatiladi.

WILDER USULI (SMMA), oddiy o'rtacha emas. Ikkalasi turli qiymat
beradi va TradingView Wilder'ni ishlatadi — foydalanuvchi grafikda
ko'rgan raqam bilan bizniki mos kelishi kerak.

DIVERGENSIYA: narx yangi PAST qildi, lekin RSI qilmadi — ya'ni
tushish kuchi zaiflashdi. Bu — qaytish belgisi.
"""

from __future__ import annotations

from core.domain.models import Candle

RSI_DAVR = 14
#: RSI shundan past bo'lsa — "sotilgan" zona.
#: 🔴 O'LCHANMAGAN (klassik 30, lekin biz o'lchamaganmiz).
RSI_PAST_ZONA = 35.0


def rsi(shamlar: list[Candle], davr: int = RSI_DAVR) -> list[float]:
    """Har bir sham uchun RSI. Birinchi `davr` ta qiymat — `nan` emas, yo'q.

    Returns:
        Uzunligi `len(shamlar) - davr` bo'lgan ro'yxat. Bo'sh bo'lishi
        mumkin — bu xato emas, ma'lumot yetishmasligi.
    """
    if len(shamlar) <= davr:
        return []

    ozgarishlar = [
        shamlar[i].close - shamlar[i - 1].close for i in range(1, len(shamlar))
    ]
    osish = [max(0.0, o) for o in ozgarishlar]
    tushish = [max(0.0, -o) for o in ozgarishlar]

    ortacha_osish = sum(osish[:davr]) / davr
    ortacha_tushish = sum(tushish[:davr]) / davr
    natija = [_qiymat(ortacha_osish, ortacha_tushish)]

    for i in range(davr, len(ozgarishlar)):
        # Wilder silliqlashi: yangi qiymat 1/davr ulush bilan kiradi
        ortacha_osish = (ortacha_osish * (davr - 1) + osish[i]) / davr
        ortacha_tushish = (ortacha_tushish * (davr - 1) + tushish[i]) / davr
        natija.append(_qiymat(ortacha_osish, ortacha_tushish))

    return natija


def _qiymat(osish: float, tushish: float) -> float:
    if tushish == 0:
        return 100.0
    rs = osish / tushish
    return 100 - (100 / (1 + rs))


def divergensiya(shamlar: list[Candle], qiymatlar: list[float], oyna: int = 20) -> bool:
    """Narx yangi past qildi, RSI qilmadimi (bullish divergensiya).

    Oxirgi `oyna` sham ichida ikkita eng past nuqta solishtiriladi:
    narxniki pasaygan, RSI niki esa PASAYMAGAN bo'lsa — divergensiya.
    """
    if len(qiymatlar) < oyna or len(shamlar) < oyna:
        return False

    # RSI ro'yxati shamlardan `davr` ta qisqa — indekslarni moslash
    surish = len(shamlar) - len(qiymatlar)
    narxlar = [s.low for s in shamlar[surish:]]

    yarim = oyna // 2
    eski_narx = min(narxlar[-oyna:-yarim])
    yangi_narx = min(narxlar[-yarim:])
    eski_rsi = min(qiymatlar[-oyna:-yarim])
    yangi_rsi = min(qiymatlar[-yarim:])

    return yangi_narx < eski_narx and yangi_rsi > eski_rsi


def past_zonadan_qaytish(qiymatlar: list[float], chegara: float = RSI_PAST_ZONA) -> bool:
    """RSI past zonaga tushib, undan CHIQQANMI.

    "Hozir past zonada" emas, "chiqdi" tekshiriladi: tushayotgan
    bozorda RSI haftalab 30 ostida turishi mumkin va unga qarab
    kirish — tushayotgan pichoqni ushlash.
    """
    if len(qiymatlar) < 3:
        return False
    oxirgi_uch = qiymatlar[-3:]
    return any(q < chegara for q in oxirgi_uch[:-1]) and oxirgi_uch[-1] >= chegara
