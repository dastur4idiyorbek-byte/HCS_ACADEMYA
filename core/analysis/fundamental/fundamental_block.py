"""BLOK 1 — to'rt ichki tekshiruvni yig'adi.

ZIDDIYAT BELGISI (2-prompt, 4-qism, BLOK 1 oxiri): agar ichki
tekshiruvlar orasida KUCHLI ziddiyat bo'lsa — blok "ziddiyatli" deb
belgilanadi, LEKIN bloklanmaydi. Bu — yangi bosqich emas, shu blok
ichidagi bitta bayroq.

Ziddiyat ta'rifi: o'lchangan tekshiruvlar teng ikkiga bo'lingan
(masalan 2 ha / 2 yo'q). Bunda blok o'tadi, lekin ishonch pasayadi
va admin monitorida ⚠️ ko'rinadi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.analysis.fundamental.capital_flow import PulOqimi, pul_oqimi
from core.analysis.fundamental.catalyst_watch import Katalizator, katalizator
from core.analysis.fundamental.market_regime import BozorHolati, bozor_holati
from core.analysis.fundamental.sentiment_sector import Kayfiyat, kayfiyat
from core.analysis.turlar import Blok, blok

BLOK_NOMI = "Fundamental"


@dataclass(frozen=True, slots=True)
class TokenUnlock:
    """Coin uchun yaqinlashayotgan token unlock ma'lumoti.

    `kun_qoldi` va `pct` `None` bo'lsa — manba yo'q, tekshiruv
    o'tkazib yuboriladi (blok shu sabab bilan to'silmaydi).
    """

    kun_qoldi: int | None
    pct: float | None
    izoh: str = ""


@dataclass(frozen=True, slots=True)
class DelistingXavfi:
    """Delisting xavfi — aniq bo'lsa coin butunlay chetlatiladi."""

    anik: bool
    sabab: str = ""


@dataclass(frozen=True, slots=True)
class FundamentalKirish:
    """Blok 1 uchun barcha xom ma'lumot bitta joyda."""

    holat: BozorHolati = field(default_factory=BozorHolati)
    oqim: PulOqimi = field(default_factory=PulOqimi)
    voqea: Katalizator = field(default_factory=Katalizator)
    kayf: Kayfiyat = field(default_factory=Kayfiyat)
    unlock: TokenUnlock | None = None
    delisting: DelistingXavfi | None = None


def delisting_tosig(xavf: DelistingXavfi | None) -> str | None:
    """Delisting xavfi ANIQ bo'lsa — butunlay chetlatish sababini qaytaradi."""
    if xavf is not None and xavf.anik:
        return f"Delisting xavfi: {xavf.sabab or 'aniq'}"
    return None


def unlock_tosig(
    unlock: TokenUnlock | None,
    *,
    yaqin_kun: int,
    katta_pct: float,
) -> str | None:
    """Token unlock <yaqin_kun kun va >katta_pct% bo'lsa — to'siq.

    Manba yo'q (`None`) bo'lsa to'siq ham yo'q — ma'lumot yetishmasligi
    chetlatishga aylanmaydi (MALUMOT_YOQ tamoyili).
    """
    if unlock is None or unlock.kun_qoldi is None or unlock.pct is None:
        return None
    if unlock.kun_qoldi < yaqin_kun and unlock.pct > katta_pct:
        return f"Token Unlock: {unlock.kun_qoldi} kunda {unlock.pct:.1f}%"
    return None


def fundamental_blok(
    kirish: FundamentalKirish,
    *,
    unlock_yaqin_kun: int = 7,
    unlock_katta_pct: float = 5.0,
) -> Blok:
    """To'rt tekshiruvni bajaradi va blok holatini qaytaradi.

    Qattiq to'siqlar (zanjirni UZADI): delisting > token unlock >
    katalizator. Ulardan birortasi bo'lsa blok o'tmaydi — ichki
    tekshiruvlar hisoblangani bilan zanjir shu yerda to'xtaydi.
    """
    voqea_tekshiruv, tosiq = katalizator(kirish.voqea)

    qattiq = (
        delisting_tosig(kirish.delisting)
        or unlock_tosig(
            kirish.unlock,
            yaqin_kun=unlock_yaqin_kun,
            katta_pct=unlock_katta_pct,
        )
        or tosiq
    )

    tekshiruvlar = [
        bozor_holati(kirish.holat),
        pul_oqimi(kirish.oqim),
        voqea_tekshiruv,
        kayfiyat(kirish.kayf),
    ]

    return blok(
        BLOK_NOMI,
        tekshiruvlar,
        qattiq_tosiq=qattiq,
        ziddiyatli=_ziddiyatlimi(tekshiruvlar),
    )


def _ziddiyatlimi(tekshiruvlar: list) -> bool:  # noqa: ANN001
    """O'lchangan tekshiruvlar TENG ikkiga bo'linganmi.

    Faqat juft sonda ma'noga ega: 2/4 yoki 1/2. Toq sonda ko'pchilik
    har doim bor, ya'ni ziddiyat yo'q.
    """
    olchangan = [t for t in tekshiruvlar if t.olchandi]
    if len(olchangan) < 2 or len(olchangan) % 2 != 0:
        return False
    ijobiy = sum(1 for t in olchangan if t.ijobiy)
    return ijobiy == len(olchangan) // 2
