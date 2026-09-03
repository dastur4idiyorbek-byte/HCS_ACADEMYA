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
class FundamentalKirish:
    """Blok 1 uchun barcha xom ma'lumot bitta joyda."""

    holat: BozorHolati = field(default_factory=BozorHolati)
    oqim: PulOqimi = field(default_factory=PulOqimi)
    voqea: Katalizator = field(default_factory=Katalizator)
    kayf: Kayfiyat = field(default_factory=Kayfiyat)


def fundamental_blok(kirish: FundamentalKirish) -> Blok:
    """To'rt tekshiruvni bajaradi va blok holatini qaytaradi."""
    voqea_tekshiruv, tosiq = katalizator(kirish.voqea)

    tekshiruvlar = [
        bozor_holati(kirish.holat),
        pul_oqimi(kirish.oqim),
        voqea_tekshiruv,
        kayfiyat(kirish.kayf),
    ]

    return blok(
        BLOK_NOMI,
        tekshiruvlar,
        qattiq_tosiq=tosiq,
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
