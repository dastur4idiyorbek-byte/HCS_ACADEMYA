"""Alternativ zanjir — ZAIF bloklarni alternativ yo'llar bilan qutqaradi.

Asosiy `zanjir_yur` bilan yagona farq:

    Asosiy:     0/N bo'lsa uziladi, 1/N o'tadi.
    Alternativ: 0/N bo'lsa uziladi, 1/N ZAIF — alternativlar ketma-ket
                sinab ko'riladi. Hammasi sinsa blok bo'sh — uziladi.

Tasnif (prompt): KUCHLI = ≥2/N, ZAIF = 1/N, BO'SH = 0/N.
Bitta istisno: o'lchangan tekshiruvlarning HAMMASI ijobiy bo'lsa
(masalan 1/1), blok KUCHLI hisoblanadi — ma'lumot yo'qligi jazoga
aylanmasin (`MALUMOT_YOQ` maxrajdan chiqadi degan tamoyil).

Eskiz (prompt):
    Blok 2: 2A Trend Line + Flag, 2B Double Bottom/Top
    Blok 3: 3A Double Bottom (zona), 3B Oldingi Swing (zona)
    Blok 4: 4A Hajm spike, 4B Tez harakat, 4C Retest

G'olib alternativ blokka ijobiy tekshiruv sifatida qo'shiladi
(`alternativ:<nom>`), shuning uchun blok kuchi 1 dan 2 ga chiqadi va
zanjir davom etadi. Zona beruvchi alternativ g'alaba qozonsa, uning
zonasi Entry/Stop/TP uchun asosiy zona O'RNIDA ishlatiladi.
"""

from __future__ import annotations

from core.analysis.alternatives.double_pattern import qosh_tub_topish
from core.analysis.alternatives.natija import AlternativNatija
from core.analysis.alternatives.prior_swing import oldingi_swing_zona
from core.analysis.alternatives.tasdiq import hajm_sakrashi, qayta_sinov, tez_harakat
from core.analysis.alternatives.trend_flag import trend_flag
from core.analysis.chain.block_chain_engine import ZanjirKirish, ZanjirNatija
from core.analysis.confirmation.confirmation_block import TasdiqKirish, tasdiqlash_blok
from core.analysis.fundamental.fundamental_block import fundamental_blok
from core.analysis.structure.structure_block import StrukturaKirish, struktura_blok
from core.analysis.structure.swing_detector import Swing, swinglar
from core.analysis.turlar import Blok, Zanjir, blok_sozla, ha
from core.analysis.zone_quality.fibonacci import Zona
from core.analysis.zone_quality.zone_block import ZonaKirish, ZonaNatija, zona_blok
from core.domain.models import Candle

#: Kuchli blok uchun eng kam ijobiy tekshiruv soni.
KUCHLI_ENG_KAM = 2

#: Zaif blok — aynan shuncha ijobiy tekshiruv.
ZAIF_KUCH = 1

KUCHLI = "kuchli"
ZAIF = "zaif"
BOSH = "bosh"
OLCHANMADI = "olchanmadi"


def blok_tasnifi(blok: Blok) -> str:
    """Blokni KUCHLI / ZAIF / BO'SH / OLCHANMADI ga ajratadi.

    `OLCHANMADI` — barcha tekshiruvlar `MALUMOT_YOQ`. Bu "bo'sh" EMAS:
    zanjirni uzmaydi, ishonchga ham kirmaydi (asosiy zanjirdagi kabi).
    """
    if blok.olchanmadi:
        return OLCHANMADI
    if blok.kuch >= KUCHLI_ENG_KAM or blok.kuch == blok.maxraj:
        return KUCHLI
    if blok.kuch == ZAIF_KUCH:
        return ZAIF
    return BOSH


def qutqar(
    blok: Blok,
    alternativlar: list[AlternativNatija],
    ochirilgan: frozenset[str] = frozenset(),
) -> tuple[Blok, AlternativNatija | None]:
    """ZAIF blokni birinchi o'tgan alternativ bilan qutqaradi.

    Returns:
        `(blok, g'olib_alternativ)`. G'olib zona berishi mumkin
        (Blok 3). Qutqarib bo'lmasa blokning o'tish talabi ko'tarilib,
        o'tmaydigan qilinadi — zanjir uziladi.
    """
    if blok_tasnifi(blok) != ZAIF:
        return blok, None

    for alt in alternativlar:
        if alt.nom in ochirilgan:
            continue
        if alt.otdi:
            return _alternativ_qosh(blok, alt), alt

    # Hammasi sinsa — blok bo'sh: o'tish talabini ko'taramiz
    # (kuch 1 < talab 2), shunda `otdi` False bo'ladi.
    return (
        Blok(blok.nom, blok.tekshiruvlar, blok.qattiq_tosiq, blok.ziddiyatli, KUCHLI_ENG_KAM),
        None,
    )


def zanjir_yur_alternativ(kirish: ZanjirKirish) -> ZanjirNatija:
    """To'rt blokni yuritadi; ZAIF blokni alternativ bilan qutqaradi."""
    bloklar: list[Blok] = []

    # --- BLOK 1: Fundamental (alternativsiz — promptda yo'q) ---
    b1 = blok_sozla(
        fundamental_blok(
            kirish.fundamental,
            unlock_yaqin_kun=kirish.unlock_yaqin_kun,
            unlock_katta_pct=kirish.unlock_katta_pct,
        ),
        kirish.ochirilgan,
    )
    bloklar.append(b1)
    if not b1.otdi:
        return ZanjirNatija(Zanjir(tuple(bloklar), uzildi_blokda=b1.nom))

    nuqtalar = swinglar(kirish.shamlar, shubhali=kirish.shubhali)

    # --- BLOK 2: Struktura ---
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
    )
    b2, _ = qutqar(b2, _alternativlar_2(kirish.shamlar, nuqtalar), kirish.ochirilgan)
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
    b3 = blok_sozla(zona_natija.blok, kirish.ochirilgan)
    b3, alt_zona = qutqar(b3, _alternativlar_3(nuqtalar), kirish.ochirilgan)
    bloklar.append(b3)
    if not b3.otdi:
        return ZanjirNatija(
            Zanjir(tuple(bloklar), uzildi_blokda=b3.nom),
            zona_natija=_zona_bilan(zona_natija, alt_zona),
        )

    zona = alt_zona.zona if alt_zona is not None else zona_natija.zona

    # --- BLOK 4: Tasdiqlash ---
    b4 = blok_sozla(
        tasdiqlash_blok(
            TasdiqKirish(
                shamlar=kirish.shamlar,
                nuqtalar=nuqtalar,
                pastki_shamlar=kirish.pastki_shamlar,
                zona=zona,
                eski_fundamental=kirish.eski_fundamental or b1,
                yangi_fundamental=b1,
            )
        ),
        kirish.ochirilgan,
    )
    b4, _ = qutqar(b4, _alternativlar_4(kirish.shamlar, nuqtalar), kirish.ochirilgan)
    bloklar.append(b4)
    if not b4.otdi:
        return ZanjirNatija(
            Zanjir(tuple(bloklar), uzildi_blokda=b4.nom),
            zona_natija=_zona_bilan(zona_natija, alt_zona),
        )

    return ZanjirNatija(
        Zanjir(tuple(bloklar)),
        zona_natija=_zona_bilan(zona_natija, alt_zona),
    )


def _alternativ_qosh(blok: Blok, alt: AlternativNatija) -> Blok:
    """G'olib alternativni blokka ijobiy tekshiruv sifatida qo'shadi."""
    yangi = blok.tekshiruvlar + (ha(f"alternativ:{alt.nom}", alt.izoh),)
    return Blok(blok.nom, yangi, blok.qattiq_tosiq, blok.ziddiyatli, blok.eng_kam_kuch)


def _zona_bilan(asl: ZonaNatija | None, alt_zona: AlternativNatija | None) -> ZonaNatija | None:
    """Alternativ zona g'alaba qozonsa, asosiy zona O'RNINI oladi."""
    if asl is None or alt_zona is None or alt_zona.zona is None:
        return asl
    return ZonaNatija(
        blok=asl.blok,
        zona=alt_zona.zona,
        daraja=asl.daraja,
        qatlamlar=asl.qatlamlar + (alt_zona.zona.manba,),
    )


def _alternativlar_2(shamlar: list[Candle], nuqtalar: list[Swing]) -> list[AlternativNatija]:
    """Blok 2: 2A trend+flag, 2B qo'sh tub."""
    return [
        _flag_alt(shamlar, nuqtalar),
        _qosh_tub_alt(nuqtalar),
    ]


def _alternativlar_3(nuqtalar: list[Swing]) -> list[AlternativNatija]:
    """Blok 3: 3A qo'sh tub (zona), 3B oldingi swing (zona)."""
    return [
        _qosh_tub_zona_alt(nuqtalar),
        _oldingi_swing_alt(nuqtalar),
    ]


def _alternativlar_4(shamlar: list[Candle], nuqtalar: list[Swing]) -> list[AlternativNatija]:
    """Blok 4: 4A hajm, 4B tezlik, 4C retest."""
    hajm = hajm_sakrashi(shamlar)
    tezlik = tez_harakat(shamlar)
    retest = qayta_sinov(shamlar, nuqtalar)
    return [
        AlternativNatija(
            "hajm_sakrashi",
            hajm,
            "hajm o'rtachadan yuqori" if hajm else "hajm zaif",
        ),
        AlternativNatija(
            "tez_harakat",
            tezlik,
            "sham diapazoni keng" if tezlik else "harakat sust",
        ),
        AlternativNatija(
            "qayta_sinov",
            retest,
            "buzilgan daraja ushlandi" if retest else "retest yo'q",
        ),
    ]


def _flag_alt(shamlar: list[Candle], nuqtalar: list[Swing]) -> AlternativNatija:
    otdi = trend_flag(shamlar, nuqtalar)
    return AlternativNatija(
        "trend_flag",
        otdi,
        "HL trend, narx chiziq ustida" if otdi else "trend yoki flag yo'q",
    )


def _qosh_tub_alt(nuqtalar: list[Swing]) -> AlternativNatija:
    tub = qosh_tub_topish(nuqtalar)
    return AlternativNatija(
        "qosh_tub",
        tub is not None,
        "ikki tub bir darajada" if tub is not None else "tub topilmadi",
    )


def _qosh_tub_zona_alt(nuqtalar: list[Swing]) -> AlternativNatija:
    tub = qosh_tub_topish(nuqtalar)
    if tub is None:
        return AlternativNatija("qosh_tub", False, "tub topilmadi")
    zona = Zona(past=tub.tub_narx, yuqori=tub.boyin_narx, manba="qosh_tub")
    return AlternativNatija(
        "qosh_tub",
        True,
        f"tub {tub.tub_narx:.4f}..{tub.boyin_narx:.4f}",
        zona=zona,
    )


def _oldingi_swing_alt(nuqtalar: list[Swing]) -> AlternativNatija:
    zona = oldingi_swing_zona(nuqtalar)
    if zona is None:
        return AlternativNatija("oldingi_swing", False, "swing past topilmadi")
    return AlternativNatija(
        "oldingi_swing",
        True,
        f"swing zona {zona.past:.4f}..{zona.yuqori:.4f}",
        zona=zona,
    )
