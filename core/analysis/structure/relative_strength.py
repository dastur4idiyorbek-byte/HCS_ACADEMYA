"""2.4 — Nisbiy kuch: coin narxi / BTC narxi trendi.

QOIDA (2-prompt): ko'tarilish signalida coin BTC'dan KUCHLI bo'lishi
kerak.

NIMA UCHUN MUHIM: kripto bozorda coinlarning ko'pchiligi BTC bilan
birga harakatlanadi. Coin ko'tarilayotgan bo'lsa-yu, BTC undan
tezroq ko'tarilayotgan bo'lsa — bu coinning o'z kuchi emas, bozor
to'lqini. To'lqin qaytganda esa u BTC'dan tezroq tushadi.

O'LCHOV: `coin/BTC` nisbatining N sham oldingisiga qaraganda
o'sganmi. Sof narx emas, NISBAT olinadi — shuning uchun BTC ham,
coin ham tushayotgan, lekin coin kamroq tushayotgan holat ham
"kuchli" hisoblanadi. Bu to'g'ri: bunday coin qaytishda oldinda
boradi.

BTC O'ZI UCHUN: nisbat har doim 1.0 bo'ladi va trend hech qachon
o'smaydi. Shuning uchun BTC bu tekshiruvda `None` (o'lchanmadi)
qaytaradi — "BTC BTC'dan zaif" degan bema'ni xulosa chiqmasin.
"""

from __future__ import annotations

from core.domain.models import Candle

#: Nisbat necha sham oldingi bilan solishtiriladi.
#: 🔴 O'LCHANMAGAN. 20 kunlik oyna — o'rta muddat gorizontiga
#: (1 kun - 1 oy) mos, lekin backtest bilan tekshiriladi.
NISBAT_OYNA = 20


def nisbiy_kuch(
    coin: list[Candle],
    btc: list[Candle],
    oyna: int = NISBAT_OYNA,
    etalon: bool = False,
) -> bool | None:
    """Coin BTC'dan kuchliroqmi.

    Returns:
        `True` — nisbat o'sgan, `False` — o'smagan,
        `None` — ma'lumot yetmaydi yoki coinning o'zi BTC.
    """
    if etalon:
        return None
    if len(coin) <= oyna or len(btc) <= oyna:
        return None

    hozir = _nisbat(coin[-1], btc[-1])
    avval = _nisbat(coin[-1 - oyna], btc[-1 - oyna])
    if hozir is None or avval is None:
        return None
    return hozir > avval


def _nisbat(coin_sham: Candle, btc_sham: Candle) -> float | None:
    if btc_sham.close <= 0:
        return None
    return coin_sham.close / btc_sham.close
