"""4.5-band: BTC ning 24 soatlik o'zgarishi — YAGONA MANBA.

NIMA UCHUN ALOHIDA MODUL. Bu hisob ilgari faqat `bot/services/runner.py`
da bor edi, backtest esa `btc_change_24h_pct=0.0` uzatardi. Natijada
`BtcMarketRule` sinovda HECH QACHON to'xtatmasdi, jonli tizimda esa
to'xtatardi — ya'ni backtest boshqa tizimni o'lchayotgan edi.

Bu loyihada takrorlanuvchi xato turi (`docs/ARXITEKTURA.md`, 68 va
80-bo'lim): bitta fakt ikki joyda alohida hisoblanadi va jimgina
ajralib ketadi. Shuning uchun hisob SOF funksiya sifatida shu yerda
turadi va ikkala tomon ham aynan shuni chaqiradi.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from core.config.schema import BtcFilterConfig
from core.domain.models import Candle
from core.utils.time_utils import timeframe_minutes

#: Bir sutkadagi daqiqalar — 24 soatlik oynani sham soniga aylantirish uchun.
MINUTES_PER_DAY = 1440


def btc_ozgarishi_24h(
    candles: Mapping[str, Mapping[str, Sequence[Candle]]],
    filtr: BtcFilterConfig,
    zaxira_timeframe: str,
) -> float | None:
    """BTC ning 24 soatlik o'zgarishi, foizda. Hisoblab bo'lmasa `None`.

    `None` — "noma'lum", "nol" emas. Farqi muhim: `BtcMarketRule`
    noma'lum qiymatda fail-safe tarmog'iga tushadi, nol qiymatda esa
    "BTC qimirlamadi" deb o'qiydi va hech qachon to'xtatmaydi.

    Args:
        candles: coin -> timeframe -> shamlar (jonli tizim va
            backtest ikkalasida ham shu shakl).
        filtr: `risk_engine.btc_filter` sozlamasi.
        zaxira_timeframe: sozlamadagi timeframe yuklanmagan bo'lsa
            ishlatiladigan qator (odatda kirish timeframei). Ansiz
            sozlama o'zgarganda filtr jimgina "noma'lum" ga qaytardi.
    """
    tf_shamlar = candles.get(filtr.reference_symbol.upper(), {})
    if not tf_shamlar:
        return None

    timeframe = filtr.timeframe if filtr.timeframe in tf_shamlar else zaxira_timeframe
    seriya = tf_shamlar.get(timeframe, [])
    kerak = max(1, MINUTES_PER_DAY // timeframe_minutes(timeframe))
    if len(seriya) <= kerak:
        return None

    avvalgi = seriya[-1 - kerak].close
    if avvalgi <= 0:
        return None
    return (seriya[-1].close - avvalgi) / avvalgi * 100
