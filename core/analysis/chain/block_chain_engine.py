"""To'rt katta blokni KETMA-KET ishga tushiradi.

ASOSIY QOIDA (2-prompt, 4-qism): blok butunlay bo'sh bo'lsa (0/4)
zanjir shu yerda uziladi va KEYINGI BLOKLAR UMUMAN HISOBLANMAYDI.

NIMA UCHUN "HISOBLANMAYDI" MUHIM (nafaqat "e'tiborga olinmaydi"):

  1. TEZLIK. Zona va tasdiqlash bloklari eng qimmat qismlar
     (volume profile, pastki TF). Struktura yo'q coin uchun ularni
     hisoblash — bekorga vaqt.
  2. HALOLLIK. Hisoblab keyin tashlab yuborish "biz buni ko'rdik"
     degan tuyg'u beradi. Aslida ko'rmadik — zanjir uzilgan edi.

ESKI TIZIMDAN FARQ. Eski ball tizimida 6 omil QO'SHILARDI: bitta
kuchli omil qolgan beshtasining yo'qligini yopib ketardi. Zanjirda
bunday almashtirish MUMKIN EMAS — har bir blok o'z halqasi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.analysis.confirmation.confirmation_block import TasdiqKirish, tasdiqlash_blok
from core.analysis.fundamental.fundamental_block import (
    FundamentalKirish,
    fundamental_blok,
)
from core.analysis.structure.structure_block import StrukturaKirish, struktura_blok
from core.analysis.structure.swing_detector import swinglar
from core.analysis.turlar import Blok, Zanjir, blok_sozla
from core.analysis.zone_quality.order_block import ObTarifi
from core.analysis.zone_quality.zone_block import ZonaKirish, ZonaNatija, zona_blok
from core.domain.models import Candle


@dataclass(frozen=True, slots=True)
class ZanjirKirish:
    """Bitta coin uchun barcha kerakli ma'lumot."""

    symbol: str
    #: ASOSIY timeframe (yetuk coin uchun 1D)
    shamlar: list[Candle] = field(default_factory=list)
    #: Pastki TF (15m/30m) — 4.2 tasdig'i uchun
    pastki_shamlar: list[Candle] = field(default_factory=list)
    #: BTC shamlari, asosiy TF da — nisbiy kuch uchun
    btc_shamlar: list[Candle] = field(default_factory=list)
    fundamental: FundamentalKirish = field(default_factory=FundamentalKirish)
    #: 4.4 uchun: zanjir BOSHIDA hisoblangan fundamental
    eski_fundamental: Blok | None = None
    yosh_kun: int | None = None
    etalon: bool = False
    shubhali: set[datetime] = field(default_factory=set)
    ob_tarifi: ObTarifi = ObTarifi.LAST_OPPOSITE
    #: ABLATSIYA uchun o'chiriladigan ichki tekshiruvlar nomi.
    #:
    #: Zanjir YURAYOTGANDA qo'llanadi — har bir blok qurilgandan
    #: keyin darhol. Ilgari ablatsiya zanjir tugagandan KEYIN
    #: qo'llanardi va bu o'lchovni buzardi: 2-blokda uzilgan
    #: nomzodning 3- va 4-bloklari umuman hisoblanmagan bo'lardi,
    #: ya'ni tekshiruvni o'chirish nomzodni oldinga O'TKAZA
    #: OLMASDI. Natijada ablatsiya faqat bitta yo'nalishda
    #: ishlardi va "hech bir tekshiruv hissa qo'shmaydi" degan
    #: xulosa chiqargandi (2026-09-04).
    ochirilgan: frozenset[str] = frozenset()
    #: Blok o'tishi uchun kerakli eng kam ijobiy tekshiruv soni.
    #: Sukut 1 — promptning qoidasi. Boshqa qiymat FAQAT o'lchov
    #: uchun beriladi (`scripts/zanjir_blok_qoidasi.py`).
    eng_kam_kuch: int = 1


@dataclass(frozen=True, slots=True)
class ZanjirNatija:
    zanjir: Zanjir
    #: Zona bloki topgan narx oralig'i — Entry/Stop uchun (5-qism)
    zona_natija: ZonaNatija | None = None


def zanjir_yur(kirish: ZanjirKirish) -> ZanjirNatija:
    """To'rt blokni tartib bilan yuritadi, birinchi uzilishda to'xtaydi."""
    bloklar: list[Blok] = []

    # --- BLOK 1: Fundamental ---
    b1 = blok_sozla(fundamental_blok(kirish.fundamental), kirish.ochirilgan, kirish.eng_kam_kuch)
    bloklar.append(b1)
    if not b1.otdi:
        return ZanjirNatija(Zanjir(tuple(bloklar), uzildi_blokda=b1.nom))

    # --- BLOK 2: Struktura ---
    nuqtalar = swinglar(kirish.shamlar, shubhali=kirish.shubhali)
    b2 = blok_sozla(
        struktura_blok(
            StrukturaKirish(
                shamlar=kirish.shamlar,
                btc_shamlar=kirish.btc_shamlar,
                yosh_kun=kirish.yosh_kun,
                etalon=kirish.etalon,
                shubhali=kirish.shubhali,
            )
        ),
        kirish.ochirilgan,
        kirish.eng_kam_kuch,
    )
    bloklar.append(b2)
    if not b2.otdi:
        return ZanjirNatija(Zanjir(tuple(bloklar), uzildi_blokda=b2.nom))

    # --- BLOK 3: Zona sifati ---
    zona_natija = zona_blok(
        ZonaKirish(
            shamlar=kirish.shamlar,
            nuqtalar=nuqtalar,
            ob_tarifi=kirish.ob_tarifi,
        )
    )
    b3 = blok_sozla(zona_natija.blok, kirish.ochirilgan, kirish.eng_kam_kuch)
    bloklar.append(b3)
    if not b3.otdi:
        return ZanjirNatija(
            Zanjir(tuple(bloklar), uzildi_blokda=b3.nom),
            zona_natija=zona_natija,
        )

    # --- BLOK 4: Tasdiqlash ---
    b4 = blok_sozla(tasdiqlash_blok(
        TasdiqKirish(
            shamlar=kirish.shamlar,
            nuqtalar=nuqtalar,
            pastki_shamlar=kirish.pastki_shamlar,
            zona=zona_natija.zona,
            # Eski fundamental berilmagan bo'lsa — shu siklda
            # hisoblangani bilan solishtiriladi, ya'ni har doim mos.
            # Bu holatni `fundamental_recheck` MALUMOT_YOQ deb emas,
            # "mos" deb o'qiydi va bu to'g'ri: vaqt o'tmagan.
            eski_fundamental=kirish.eski_fundamental or b1,
            yangi_fundamental=b1,
        )
    ), kirish.ochirilgan, kirish.eng_kam_kuch)
    bloklar.append(b4)
    if not b4.otdi:
        return ZanjirNatija(
            Zanjir(tuple(bloklar), uzildi_blokda=b4.nom),
            zona_natija=zona_natija,
        )

    return ZanjirNatija(Zanjir(tuple(bloklar)), zona_natija=zona_natija)
