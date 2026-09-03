"""BLOK 3 — darajali birlashtirish (bu blokning o'ziga xosligi).

BOSHQA BLOKLARDAN FARQI. Blok 1, 2 va 4 da har bir ichki tekshiruv
mustaqil ovoz. Bu yerda esa Fib/OB/FVG — BIR-BIRINI ICHIGA OLGAN
qatlamlar (2-prompt, 4-qism):

    faqat Fib          ZAIF     (1 qatlam)
    Fib + OB           O'RTA    (2 qatlam)
    Fib + OB + FVG     KUCHLI   (3 qatlam)

NIMA UCHUN "ICHIGA OLGAN": OB va FVG mustaqil ovoz bo'lganda,
grafikning BOSHQA-BOSHQA joyidagi uchta zona "3/4 kuchli" deb
o'qilardi — aslida ular bir-biriga hech qanday aloqasi yo'q uchta
alohida daraja. Konfluensiya esa AYNAN ustma-ust tushishni
anglatadi. Shuning uchun OB va FVG faqat Fib zonasi bilan
KESISHSA hisoblanadi.

Volume Profile — mustaqil, alohida ✅/❌ (promptda shunday).

ZONA — HAM NATIJA. Bu blok faqat ball bermaydi, u ENTRY va STOP
uchun aniq narx oralig'ini ham qaytaradi (5-qism).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.analysis.turlar import Blok, blok, ha, malumot_yoq, yoq
from core.analysis.zone_quality.fibonacci import Zona, fib_zona
from core.analysis.zone_quality.fvg import fvg_topish
from core.analysis.zone_quality.order_block import ObTarifi, ob_topish
from core.analysis.zone_quality.volume_profile import poc_narx, poc_yaqinmi
from core.domain.models import Candle

BLOK_NOMI = "Zona Sifati"


class ZonaDarajasi(str, Enum):
    YOQ = "yoq"
    ZAIF = "zaif"
    ORTA = "orta"
    KUCHLI = "kuchli"


@dataclass(frozen=True, slots=True)
class ZonaKirish:
    shamlar: list[Candle] = field(default_factory=list)
    nuqtalar: list[Swing] = field(default_factory=list)
    ob_tarifi: ObTarifi = ObTarifi.LAST_OPPOSITE


@dataclass(frozen=True, slots=True)
class ZonaNatija:
    """Blok natijasi VA topilgan zona (Entry/Stop uchun)."""

    blok: Blok
    zona: Zona | None
    daraja: ZonaDarajasi
    #: Qaysi qatlamlar mos keldi — admin monitorida ko'rinadi
    qatlamlar: tuple[str, ...] = ()


def zona_blok(kirish: ZonaKirish) -> ZonaNatija:
    """Fib zonasini asos qilib, unga OB va FVG ni QATLAYDI."""
    asos = fib_zona(kirish.nuqtalar)
    if asos is None:
        tekshiruvlar = [
            yoq("fibonacci", "impuls topilmadi"),
            malumot_yoq("order_block", "asos zona yo'q"),
            malumot_yoq("fvg", "asos zona yo'q"),
            malumot_yoq("volume_profile", "asos zona yo'q"),
        ]
        return ZonaNatija(
            blok=blok(BLOK_NOMI, tekshiruvlar),
            zona=None,
            daraja=ZonaDarajasi.YOQ,
        )

    qatlamlar = ["fibonacci"]
    tekshiruvlar = [ha("fibonacci", f"{asos.past:.4f}..{asos.yuqori:.4f}")]

    # --- Order Block: FAQAT Fib zonasi bilan kesishsa hisoblanadi ---
    impuls_boshi = _impuls_boshi(kirish.nuqtalar)
    ob = (
        ob_topish(kirish.shamlar, impuls_boshi, kirish.ob_tarifi)
        if impuls_boshi is not None
        else None
    )
    ob_mos = ob is not None and ob.zona.kesishadimi(asos)
    if ob_mos:
        qatlamlar.append("order_block")
        tekshiruvlar.append(ha("order_block", f"{kirish.ob_tarifi.value} kesishdi"))
    else:
        tekshiruvlar.append(yoq("order_block", "kesishmadi yoki topilmadi"))

    # --- FVG: u ham FAQAT kesishsa ---
    fvg = fvg_topish(kirish.shamlar)
    fvg_mos = fvg is not None and fvg.zona.kesishadimi(asos)
    if fvg_mos:
        qatlamlar.append("fvg")
        tekshiruvlar.append(ha("fvg", "bo'shliq zona bilan kesishdi"))
    else:
        tekshiruvlar.append(yoq("fvg", "kesishmadi yoki topilmadi"))

    # --- Volume Profile: MUSTAQIL ovoz ---
    poc = poc_narx(kirish.shamlar)
    yaqin = poc_yaqinmi(asos.markaz, poc)
    if yaqin is None:
        tekshiruvlar.append(malumot_yoq("volume_profile", "POC hisoblanmadi"))
    elif yaqin:
        tekshiruvlar.append(ha("volume_profile", f"POC {poc:.4f} yaqin"))
    else:
        tekshiruvlar.append(yoq("volume_profile", f"POC {poc:.4f} uzoq"))

    return ZonaNatija(
        blok=blok(BLOK_NOMI, tekshiruvlar),
        zona=_qatlangan_zona(asos, ob, fvg, ob_mos, fvg_mos),
        daraja=_daraja(len(qatlamlar)),
        qatlamlar=tuple(qatlamlar),
    )


def _daraja(qatlam_soni: int) -> ZonaDarajasi:
    if qatlam_soni >= 3:
        return ZonaDarajasi.KUCHLI
    if qatlam_soni == 2:
        return ZonaDarajasi.ORTA
    return ZonaDarajasi.ZAIF


def _qatlangan_zona(asos: Zona, ob, fvg, ob_mos: bool, fvg_mos: bool) -> Zona:  # noqa: ANN001
    """Mos kelgan qatlamlarning KESISHMASI — eng aniq oraliq.

    Kesishma olinadi, birlashma emas: uchta qatlam ustma-ust
    tushgan joy — eng ishonchli nuqta. Birlashma esa zonani
    kengaytirib, Stop ni uzoqlashtirardi va R/R ni buzardi.
    """
    past, yuqori = asos.past, asos.yuqori
    if ob_mos and ob is not None:
        past = max(past, ob.zona.past)
        yuqori = min(yuqori, ob.zona.yuqori)
    if fvg_mos and fvg is not None:
        past = max(past, fvg.zona.past)
        yuqori = min(yuqori, fvg.zona.yuqori)
    # Kesishma bo'sh chiqsa (chegara holati) — asosga qaytamiz
    if past >= yuqori:
        return asos
    nomlar = ["fib"] + (["ob"] if ob_mos else []) + (["fvg"] if fvg_mos else [])
    return Zona(past=past, yuqori=yuqori, manba="+".join(nomlar))


def _impuls_boshi(nuqtalar: list[Swing]) -> int | None:
    """Oxirgi ko'tarilish impulsi qaysi shamdan boshlangan."""
    for s in reversed(nuqtalar):
        if s.turi is SwingTuri.PAST:
            return s.indeks
    return None
