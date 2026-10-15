"""Elak, o'rin, holat va ketma-ket hisoblagich — sof mantiq.

O'RIN QOIDASI (`docs/MODUL_4_0_0.md`, 6-bo'lim, 3-bosqich):

    1. ✅ soni                 ko'pi yuqorida
    2. TASDIQLANGAN            oldin
    3. Yoqilg'i ✅ soni         ko'pi yuqorida
    4. Hajm nisbati            kattasi yuqorida, noma'lum — oxirida
    5. Symbol                  alifbo — natija har doim bir xil chiqsin

Hammasi xom o'lchov, formula yo'q. "Ketma-ket" hisoblagichi bu
ro'yxatda ATAYLAB yo'q: u faqat ma'lumot, tartibga ta'sir qilmaydi.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from core.portlash_radari.sozlama import Chegaralar
from core.portlash_radari.tekshiruvlar import MIN_TARIX_KUN
from core.portlash_radari.vaqt import KASHFIYOT, QOLDA, TASDIQ

TASDIQLANGAN = "tasdiqlangan"
VAQTINCHALIK = "vaqtinchalik"
NOMZOD = "nomzod"
ODDIY = "oddiy"


def yangi_listingmi(
    onboard: datetime | None,
    hozir: datetime,
    tarix_kunlar: int,
    ch: Chegaralar,
) -> bool:
    """Binance'da yosh yoki tarixi qisqa coin.

    Ikkala belgi ham kerak: `onboardDate` ba'zan juda eski bo'ladi
    (kontrakt qayta ishga tushirilgan), tarix esa kesh hali
    yangilanmagan paytda bo'sh bo'lishi mumkin.
    """
    if onboard is not None and hozir - onboard < timedelta(days=ch.yangi_listing_kun):
        return True
    return tarix_kunlar < MIN_TARIX_KUN


def elakdan_otadimi(
    hajm_24s: float | None,
    ortacha_30k: float | None,
    tarix_kunlar: int,
    yangi_listing: bool,
    ch: Chegaralar,
) -> tuple[bool, float | None]:
    """1-bosqich: hajm 30 kunlik o'rtachadan `elak_hajm_x` barobar katta.

    Yangi listing o'rtachasiz o'tadi — uning tarixi yo'q, lekin
    aynan shunday coinlar ko'pincha portlaydi.

    Qaytadi: (o'tdimi, hajm nisbati yoki `None`).
    """
    nisbat = None
    if (
        hajm_24s is not None
        and ortacha_30k is not None
        and ortacha_30k > 0
        and tarix_kunlar >= MIN_TARIX_KUN
    ):
        nisbat = hajm_24s / ortacha_30k
    if nisbat is not None and nisbat >= ch.elak_hajm_x:
        return True, nisbat
    return yangi_listing, nisbat


@dataclass(frozen=True, slots=True)
class TartibKirishi:
    symbol: str
    tasdiq_soni: int
    tasdiqlangan: bool
    yoqilgi_soni: int
    hajm_nisbati: float | None


def _kalit(k: TartibKirishi) -> tuple:
    nisbat_yoq = k.hajm_nisbati is None
    return (
        -k.tasdiq_soni,
        0 if k.tasdiqlangan else 1,
        -k.yoqilgi_soni,
        nisbat_yoq,
        -(k.hajm_nisbati or 0.0),
        k.symbol,
    )


def orinlar(kirishlar: list[TartibKirishi]) -> dict[str, int]:
    """Symbol -> o'rin (1 dan)."""
    return {k.symbol: i for i, k in enumerate(sorted(kirishlar, key=_kalit), start=1)}


def holat(turi: str, nomzod: bool, a_nomzodmi: bool | None) -> str:
    """Coinning sessiyadagi holati.

    `a_nomzodmi` — shu shamning kashfiyot (A) sessiyasida nomzod
    bo'lganmi. `None` — A sessiyasi yo'q (bot o'chiq edi): tasdiqni
    bilib bo'lmaydi, coin oddiy "nomzod" bo'lib qoladi.
    """
    if turi != TASDIQ or a_nomzodmi is None:
        return NOMZOD if nomzod else ODDIY
    if nomzod and a_nomzodmi:
        return TASDIQLANGAN
    if nomzod:
        return NOMZOD
    return VAQTINCHALIK if a_nomzodmi else ODDIY


def ketma_ket(turi: str, nomzod: bool, oldingi: int | None) -> int:
    """Necha rasmiy sessiya ketma-ket nomzod.

    Kechirim yo'q: nomzod bo'lmasa darhol 0. Qayta chiqsa — yangi
    voqea, 1 dan. Qo'lda tekshiruv zanjirga kirmaydi.
    """
    if turi not in (KASHFIYOT, TASDIQ) or not nomzod:
        return 0
    return (oldingi or 0) + 1


def namuna_tanla(nomzodlar: list[str], soni: int, urug: str) -> list[str]:
    """Nazorat guruhi — takrorlanadigan tasodifiy tanlov.

    Urug' sessiyadan olinadi: bir sessiya qayta hisoblansa ham aynan
    o'sha coinlar tanlanadi (testda ham, tekshiruvda ham).
    """
    if soni <= 0 or not nomzodlar:
        return []
    tartibli = sorted(set(nomzodlar))
    return random.Random(urug).sample(tartibli, min(soni, len(tartibli)))


__all__ = [
    "NOMZOD",
    "ODDIY",
    "QOLDA",
    "TASDIQLANGAN",
    "VAQTINCHALIK",
    "TartibKirishi",
    "elakdan_otadimi",
    "holat",
    "ketma_ket",
    "namuna_tanla",
    "orinlar",
    "yangi_listingmi",
]
