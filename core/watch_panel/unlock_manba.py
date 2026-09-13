"""Token Unlock kalendari — DefiLlama emissions.

--------------------------------------------------------------------
NEGA BU MUHIM
--------------------------------------------------------------------

Token Unlock — sanasi OLDINDAN MA'LUM sotuv bosimi. Loyiha
asoschilariga yoki investorlarga qulflangan tokenlar ochiladi va
ularning bir qismi bozorga tushadi. Bu — taxmin emas, kalendar.

`catalyst_watch.py` shu sababli uni QATTIQ TO'SIQ qilgan: unlock
yaqin (7 kundan kam) VA katta (muomaladagi tokenning 5% idan
ko'p) bo'lsa, coin butunlay chetlashtiriladi. Ilgari bu to'siq
HECH QACHON ishlamas edi — kalendar ulanmagan, `unlock_kun` doim
`None` edi.

--------------------------------------------------------------------
NEGA DEFILLAMA
--------------------------------------------------------------------

Unlock kalendarini bepul va kalitsiz beradigan yagona manba.
TokenUnlocks.app va CryptoRank pullik yoki kalit talab qiladi.

BITTA SO'ROV — BARCHA LOYIHA. Javob katta (bir necha yuz loyiha),
lekin skanda bir marta olinadi va 80 coin uchun jadvaldan
o'qiladi.

--------------------------------------------------------------------
JAVOB SHAKLI TURLICHA BO'LISHI MUMKIN
--------------------------------------------------------------------

DefiLlama bu endpointni hujjatlashtirmagan va javobni ro'yxat
sifatida ham, `{"protocols": [...]}` ko'rinishida ham qaytarishi
kuzatilgan. Shuning uchun IKKALASI ham o'qiladi va har bir maydon
uchun bir nechta nom sinab ko'riladi.

Hech biri mos kelmasa — `None`. Ya'ni MALUMOT_YOQ, "unlock yo'q"
EMAS: bilmaslik coinni tozalab qo'ymaydi va to'siqni ham
ishga tushirmaydi.

--------------------------------------------------------------------

QAT'IY CHEGARA: bu faylda Entry/Stop/TP hisoblanmaydi.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: DefiLlama emissiya ro'yxati — kalitsiz, bepul.
EMISSIYA_MANZIL = "https://api.llama.fi/emissions"

#: Shundan uzoqdagi unlock e'tiborga olinmaydi.
#:
#: 🔴 O'LCHANMAGAN. 180 kun — yarim yil. Undan narigi unlock
#: hozirgi qarorga ta'sir qilmaydi, lekin jadvalni behuda
#: kattalashtiradi. To'siq baribir 7 kunlik oynada ishlaydi.
UZOQ_CHEGARA_KUN = 180

#: Symbol qaysi maydonlardan izlanadi (birinchi topilgani olinadi).
SYMBOL_MAYDONLARI = ("tSymbol", "symbol", "ticker")

#: Muomaladagi token soni qaysi maydonlardan.
SUPPLY_MAYDONLARI = ("circSupply", "circulatingSupply", "maxSupply", "totalLocked")


@dataclass(frozen=True, slots=True)
class UnlockHodisasi:
    """Bitta coinning eng yaqin unlock hodisasi."""

    kun_qoldi: int
    #: Muomaladagi tokenning necha foizi ochiladi. Supply noma'lum
    #: bo'lsa `None` — sana bor, hajm yo'q.
    pct: float | None
    izoh: str = ""


class UnlockManba:
    """DefiLlama dan unlock kalendarini oladi."""

    def __init__(self) -> None:
        self._session = None

    async def _sessiya(self):  # noqa: ANN202
        import aiohttp

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def yop(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def _json(self, manzil: str):  # noqa: ANN202
        """So'rov. Xato bo'lsa `None` — skan to'xtamaydi."""
        try:
            sessiya = await self._sessiya()
            async with sessiya.get(manzil, timeout=30.0) as javob:
                if javob.status != 200:
                    logger.warning("%s -> %s", manzil, javob.status)
                    return None
                return await javob.json(content_type=None)
        except Exception:  # noqa: BLE001 — manba yo'qligi skanni to'xtatmasin
            logger.exception("Unlock manbasi so'rovi yiqildi")
            return None

    async def jadval(self) -> dict[str, UnlockHodisasi]:
        """Symbol -> eng yaqin unlock. BITTA so'rovda hammasi."""
        malumot = await self._json(EMISSIYA_MANZIL)
        qatorlar = _qatorlar(malumot)
        if not qatorlar:
            return {}

        hozir = time.time()
        jadval: dict[str, UnlockHodisasi] = {}
        for qator in qatorlar:
            juft = _bitta_loyiha(qator, hozir)
            if juft is None:
                continue
            symbol, hodisa = juft
            # ENG YAQINI QOLADI. Bitta symbol bir necha loyihada
            # uchrashi mumkin (eski va yangi yozuv); yaqinrog'i
            # xavfliroq, shuning uchun u saqlanadi.
            avvalgi = jadval.get(symbol)
            if avvalgi is None or hodisa.kun_qoldi < avvalgi.kun_qoldi:
                jadval[symbol] = hodisa
        return jadval


def _qatorlar(malumot: object) -> list:
    """Javobning ikki shaklidan ham ro'yxatni ajratib oladi."""
    if isinstance(malumot, list):
        return malumot
    if isinstance(malumot, dict):
        for kalit in ("protocols", "data"):
            ichki = malumot.get(kalit)
            if isinstance(ichki, list):
                return ichki
    return []


def _bitta_loyiha(qator: object, hozir: float) -> tuple[str, UnlockHodisasi] | None:
    """Bitta loyiha yozuvidan symbol va eng yaqin unlockni oladi."""
    if not isinstance(qator, dict):
        return None

    symbol = _matn(qator, SYMBOL_MAYDONLARI)
    if not symbol:
        return None

    hodisa = _eng_yaqin(qator, hozir)
    if hodisa is None:
        return None

    vaqt, tokenlar = hodisa
    kun = math.ceil((vaqt - hozir) / 86400.0)
    if kun < 0 or kun > UZOQ_CHEGARA_KUN:
        return None

    supply = _son(qator, SUPPLY_MAYDONLARI)
    pct = None
    if supply is not None and supply > 0 and tokenlar is not None:
        pct = round(100.0 * tokenlar / supply, 3)

    nomi = qator.get("name")
    izoh = str(nomi) if isinstance(nomi, str) else ""
    return symbol.upper(), UnlockHodisasi(kun_qoldi=kun, pct=pct, izoh=izoh)


def _eng_yaqin(qator: dict, hozir: float) -> tuple[float, float | None] | None:
    """Kelajakdagi eng yaqin hodisaning vaqti va token soni.

    `upcomingEvent` bo'lsa o'sha ishlatiladi — DefiLlama uni
    ataylab "keyingisi" deb beradi. Bo'lmasa `events` dan
    kelajakdagilari saralanadi.
    """
    for kalit in ("upcomingEvent", "events"):
        hodisalar = qator.get(kalit)
        if not isinstance(hodisalar, list):
            continue
        eng_yaqin: tuple[float, float | None] | None = None
        for hodisa in hodisalar:
            juft = _hodisa(hodisa, hozir)
            if juft is None:
                continue
            if eng_yaqin is None or juft[0] < eng_yaqin[0]:
                eng_yaqin = juft
        if eng_yaqin is not None:
            return eng_yaqin
    return None


def _hodisa(hodisa: object, hozir: float) -> tuple[float, float | None] | None:
    """Bitta hodisa: vaqt (kelajakda) va ochiladigan token soni."""
    if not isinstance(hodisa, dict):
        return None
    try:
        vaqt = float(hodisa["timestamp"])
    except (KeyError, TypeError, ValueError):
        return None
    if vaqt <= hozir:
        return None

    # `noOfTokens` — RO'YXAT. Bitta hodisada bir nechta ulush
    # bo'lishi mumkin (jamoa, investor, ekotizim) va ularning
    # YIG'INDISI bozorga tushadi.
    tokenlar = hodisa.get("noOfTokens")
    jami: float | None = None
    if isinstance(tokenlar, list):
        yigindi = 0.0
        topildi = False
        for son in tokenlar:
            if isinstance(son, int | float):
                yigindi += float(son)
                topildi = True
        jami = yigindi if topildi else None
    elif isinstance(tokenlar, int | float):
        jami = float(tokenlar)

    return vaqt, jami


def _matn(qator: dict, maydonlar: tuple[str, ...]) -> str | None:
    for maydon in maydonlar:
        qiymat = qator.get(maydon)
        if isinstance(qiymat, str) and qiymat.strip():
            return qiymat.strip()
    return None


def _son(qator: dict, maydonlar: tuple[str, ...]) -> float | None:
    for maydon in maydonlar:
        qiymat = qator.get(maydon)
        if isinstance(qiymat, int | float):
            return float(qiymat)
        if isinstance(qiymat, str):
            try:
                return float(qiymat)
            except ValueError:
                continue
    return None
