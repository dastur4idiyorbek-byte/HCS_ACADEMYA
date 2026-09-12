"""REJIM B — KUZATUV. To'rt blok hisoblanadi, ZANJIR UZILMAYDI.

--------------------------------------------------------------------
IKKI REJIM, BITTA HISOBLASH
--------------------------------------------------------------------

    Rejim A (signal)   `chain/block_chain_engine.py`
        blok "yo'q" desa -> ZANJIR UZILADI -> keyingi bloklar
        umuman hisoblanmaydi

    Rejim B (kuzatuv)   SHU FAYL
        blok "yo'q" desa -> HECH NARSA UZILMAYDI -> to'rt blok ham,
        har doim, to'liq hisoblanadi

Ikkalasi AYNAN bir xil blok funksiyalarini chaqiradi
(`fundamental_blok`, `struktura_blok`, `zona_blok`,
`tasdiqlash_blok`). Bu fayl ularning ichiga kirmaydi va ularni
o'zgartirmaydi — faqat boshqacha TARTIBDA chaqiradi. Shuning
uchun "panel boshqa narsa ko'rsatyapti" degan holat bo'lishi
mumkin emas: ikkalasi bir xil hisobni ko'radi, faqat Rejim A
yarim yo'lda to'xtaydi.

--------------------------------------------------------------------
QATTIQ TO'SIQ — REJIM B DA TO'XTATMAYDI
--------------------------------------------------------------------

Fundamental blokdagi delisting/unlock to'sig'i Rejim A da zanjirni
uzadi. Bu yerda esa u faqat ⚠️ OGOHLANTIRISH: coin ro'yxatda
qoladi, lekin admin xavfni ko'radi. Sabab sodda — biz savdo
qarori qabul qilmayapmiz, ko'rsatayapmiz. "Bu coinda unlock
yaqin" degan xabar — aynan admin bilishi kerak bo'lgan narsa,
uni yashirish foyda bermaydi.

--------------------------------------------------------------------
FILTR BIRINCHI — KEYIN HISOB
--------------------------------------------------------------------

3-qism filtri (`watch_panel/uptrend_filter.py`) Diqqat darajasini
hisoblashdan OLDIN qo'llanadi. Downtrend coin uchun qolgan uch
blok UMUMAN hisoblanmaydi — bu resursni tejash, chunki u coin
baribir hech qaysi ro'yxatga kirmaydi.

Diqqqat: bu Rejim A dagi "zanjir uzildi" bilan bir narsa EMAS.
U yerda blok natijasi zanjirni uzadi; bu yerda esa coin umuman
nomzod emasligi aniqlangani uchun hisob boshlanmaydi.

--------------------------------------------------------------------
DIQQAT DARAJASI — TO'RT ICHKI TEKSHIRUV, TO'RT BLOK EMAS
--------------------------------------------------------------------

Prompt to'rt segmentli indikator so'radi. Segmentlar BLOKLARga
bog'lansa, amalda ikkitasi qotib qolardi:

    Fundamental — manba ulanmagan, DOIM bo'sh
    Struktura   — filtrdan o'tganlar uchun DOIM to'la

ya'ni 20 coin bir-biridan atigi ikki segment bilan farq qilardi.
Shuning uchun segmentlar — HAQIQATAN o'zgaradigan to'rt ichki
tekshiruv (loyiha egasining qarori, 2026-09-12):

    1. Zona konfluensiyasi  (kamida O'RTA daraja: Fib+OB)
    2. Volume Profile
    3. Liquidity Sweep
    4. RSI divergensiyasi

To'rt blokning O'ZI yo'qolmaydi — ular chuqur ko'rinishda alohida
karta bo'lib qoladi (5.3-qism).

--------------------------------------------------------------------
IKKI DARVOZA: YO'NALISH VA BOSQICH
--------------------------------------------------------------------

Coin nomzod bo'lishi uchun IKKALASI ham kerak:

    YO'NALISH — struktura yuqoriga qaraydimi (HH/HL yoki burilish)
    BOSQICH   — narx harakatning QAYERIDA

Ikkinchisi 2026-09-12 da qo'shildi. Sabab: HH/HL ketma-ketligi
coin ALLAQACHON YURGANDA ham to'g'ri bo'ladi — aslida u eng
kuchli aynan shunda ko'rinadi. Birinchi yozuvda faqat yo'nalish
tekshirilgan va Top 20 ga harakatini tugatgan coinlar chiqqan.

Endi narx oxirgi impulsning qaytish zonasidan YUQORIDA bo'lsa,
coin ro'yxatga kirmaydi: bizga yurish potensiali bor, lekin hali
yurmagan coin kerak.

--------------------------------------------------------------------
ALTERNATIV YO'LLAR — TO'LIQ SAQLANADI
--------------------------------------------------------------------

Blok ZAIF (1/N) chiqsa, zaxira usullar ketma-ket sinaladi va
biri ishlasa blok qutqariladi (prompt, 1-qism: "Bu jarayon —
TO'LIQ SAQLANADI"):

    Blok 2: trend_flag, qosh_tub
    Blok 3: qosh_tub (zona beradi), oldingi_swing (zona beradi)
    Blok 4: hajm_sakrashi, tez_harakat, qayta_sinov

Ular `alternatives/alternative_chain.py` dan AYNAN o'sha holda
chaqiriladi — ko'chirilmaydi. `qutqar()` funksiyasi zanjir
mantig'idan MUSTAQIL: u faqat blokni ko'radi va alternativlarni
sinaydi, hech narsani uzmaydi. Shuning uchun uni Rejim B da
ishlatish mumkin.

G'olib alternativ blokka `alternativ:<nom>` degan ijobiy tekshiruv
bo'lib qo'shiladi va ekranda ko'rinadi (5.3-qism talabi: "qaysi
usul ishlagani ko'rsatiladi").

Blok 3 da g'olib alternativ ZONA beradi va u asosiy zona O'RNIGA
ishlatiladi — keyingi blok ham, ekran ham o'shani ko'radi.

--------------------------------------------------------------------
TIMEFRAME
--------------------------------------------------------------------

    Struktura + filtr  — 4 soatlik
    Zona + sweep/RSI   — 1 soatlik
    Pastki tasdiq      — 15 daqiqalik

Har bir blok o'z timeframeini natijada QAYTARADI, ekranda aynan
o'shani yozish uchun. Raqam qo'lda yozilmaydi — aks holda config
o'zgarganda ekranda eski qiymat qolib ketardi.

QAT'IY CHEGARA: bu faylda Entry, Stop yoki TP hisoblanmaydi.
`entry_stop_tp` import qilinmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.analysis.alternatives.alternative_chain import (
    alternativlar_2,
    alternativlar_3,
    alternativlar_4,
    qutqar,
    zona_bilan,
)
from core.analysis.alternatives.natija import AlternativNatija
from core.analysis.confirmation.confirmation_block import TasdiqKirish, tasdiqlash_blok
from core.analysis.fundamental.fundamental_block import (
    FundamentalKirish,
    delisting_tosig,
    fundamental_blok,
    unlock_tosig,
)
from core.analysis.structure.bos_choch import bos_choch_topish
from core.analysis.structure.structure_block import StrukturaKirish, struktura_blok
from core.analysis.structure.swing_detector import SwingTuri, oxirgi, swinglar
from core.analysis.structure.uptrend_filter import (
    Bosqich,
    BosqichNatija,
    Yonalish,
    YonalishNatija,
    bosqich_aniqla,
    yonalish_aniqla,
)
from core.analysis.turlar import Blok, Holat, Tekshiruv
from core.analysis.zone_quality.order_block import ObTarifi
from core.analysis.zone_quality.zone_block import ZonaDarajasi, ZonaKirish, ZonaNatija, zona_blok
from core.domain.models import Candle

#: Nisbiy kuch nechta sham oldin bilan solishtiriladi.
#: `relative_strength.NISBAT_OYNA` bilan bir xil bo'lishi shart
#: emas: u yerda HA/YO'Q, bu yerda esa TARTIBLASH uchun raqam.
NISBAT_OYNA = 20

#: Zona konfluensiyasi segmenti ✅ bo'lishi uchun eng kam daraja.
#: O'RTA = Fib + OB ustma-ust tushgan.
YETARLI_DARAJA = (ZonaDarajasi.ORTA, ZonaDarajasi.KUCHLI)


@dataclass(frozen=True, slots=True)
class Timeframelar:
    """Qaysi blok qaysi grafikdan o'qiganini ekranga chiqarish uchun."""

    struktura: str = "4h"
    zona: str = "1h"
    pastki: str = "15m"


@dataclass(frozen=True, slots=True)
class KuzatuvKirish:
    """Bitta coin uchun barcha xom ma'lumot."""

    symbol: str
    #: Struktura va filtr uchun (4h)
    struktura_shamlar: list[Candle] = field(default_factory=list)
    #: Zona, sweep va RSI uchun (1h)
    zona_shamlar: list[Candle] = field(default_factory=list)
    #: Pastki TF tasdig'i uchun (15m)
    pastki_shamlar: list[Candle] = field(default_factory=list)
    #: BTC, struktura timeframeida — nisbiy kuch uchun
    btc_shamlar: list[Candle] = field(default_factory=list)
    fundamental: FundamentalKirish = field(default_factory=FundamentalKirish)
    yosh_kun: int | None = None
    etalon: bool = False
    shubhali: set[datetime] = field(default_factory=set)
    ob_tarifi: ObTarifi = ObTarifi.LAST_OPPOSITE
    timeframelar: Timeframelar = field(default_factory=Timeframelar)
    unlock_yaqin_kun: int = 7
    unlock_katta_pct: float = 5.0


@dataclass(frozen=True, slots=True)
class Segment:
    """Diqqat indikatorining bitta segmenti."""

    nom: str
    holat: Holat
    izoh: str
    #: Qaysi grafikdan o'qildi — ekranda ko'rsatiladi
    timeframe: str

    @property
    def yoqilgan(self) -> bool:
        return self.holat is Holat.HA


@dataclass(frozen=True, slots=True)
class KuzatuvNatija:
    """Bitta coinning kuzatuv holati.

    `bloklar` bo'sh bo'lsa — coin filtrdan o'tmagan va hisob
    umuman boshlanmagan. Bu "hammasi yo'q chiqdi" degani EMAS.
    """

    symbol: str
    yonalish: YonalishNatija
    #: Narx harakatning qayerida — ikkinchi darvoza
    bosqich: BosqichNatija = field(
        default_factory=lambda: BosqichNatija(Bosqich.NOMALUM)
    )
    #: Oxirgi yopilish narxi — ekranda va bosqich hisobida
    narx: float | None = None
    bloklar: tuple[Blok, ...] = ()
    zona_natija: ZonaNatija | None = None
    segmentlar: tuple[Segment, ...] = ()
    #: Delisting yoki unlock xavfi — ro'yxatdan CHIQARMAYDI
    ogohlantirish: str | None = None
    #: coin/BTC nisbatining o'zgarishi — teng ball chiqqanda tartib uchun
    nisbiy_kuch: float | None = None
    #: Qaysi blok qaysi alternativ bilan qutqarildi: {blok nomi: usul}
    alternativlar: tuple[tuple[str, str], ...] = ()

    #: ANIQ NARX DARAJALARI (5.3-qism talabi).
    #:
    #: Prompt uch marta "ANIQ NARX" so'raydi: BOS qaysi darajada
    #: tasdiqlangan, zona qayerda, sweep qaysi darajada bo'lgan.
    #: Blok tekshiruvlarining izohida bu raqamlar YO'Q — ular
    #: faqat "bor/yo'q" deydi. Shuning uchun ular shu yerda,
    #: bloklarga TEGMASDAN qayta hisoblanadi.
    bos_narx: float | None = None
    #: Sweep tekshiradigan daraja — oxirgi swing PAST.
    #: `liquidity_sweep.sweep_bormi` AYNAN shu nuqtani sinaydi,
    #: shuning uchun ikkalasi bir xil darajani ko'rsatadi.
    sweep_narx: float | None = None
    timeframelar: Timeframelar = field(default_factory=Timeframelar)

    @property
    def otdi(self) -> bool:
        """Coin ro'yxatga kira oladimi.

        IKKALASI HAM shart: struktura yuqoriga qarasin VA narx
        harakatni tugatmagan bo'lsin.
        """
        return self.yonalish.otadi and self.bosqich.nomzod

    @property
    def diqqat(self) -> int:
        """Nechta segment ✅ — 0 dan 4 gacha."""
        return sum(1 for s in self.segmentlar if s.yoqilgan)

    @property
    def zona_darajasi(self) -> ZonaDarajasi:
        return self.zona_natija.daraja if self.zona_natija else ZonaDarajasi.YOQ


def _tekshiruv(blok: Blok | None, nom: str) -> Tekshiruv | None:
    if blok is None:
        return None
    for t in blok.tekshiruvlar:
        if t.nom == nom:
            return t
    return None


def _segment(
    nom: str, tekshiruv: Tekshiruv | None, timeframe: str, *, sabab: str = ""
) -> Segment:
    if tekshiruv is None:
        return Segment(nom, Holat.MALUMOT_YOQ, sabab or "hisoblanmadi", timeframe)
    return Segment(nom, tekshiruv.holat, tekshiruv.izoh, timeframe)


def _nisbiy_kuch_qiymati(coin: list[Candle], btc: list[Candle]) -> float | None:
    """coin/BTC nisbati `NISBAT_OYNA` sham ichida necha marta o'zgardi.

    FAQAT TARTIBLASH UCHUN. Bu raqam hech qanday qarorga kirmaydi —
    teng Diqqat darajasi chiqqanda qaysi coin yuqoriroq turishini
    hal qiladi, xolos (4-qism). 1.0 dan katta — coin BTC dan
    tezroq o'sgan.
    """
    if len(coin) <= NISBAT_OYNA or len(btc) <= NISBAT_OYNA:
        return None
    if btc[-1].close <= 0 or btc[-1 - NISBAT_OYNA].close <= 0:
        return None
    hozir = coin[-1].close / btc[-1].close
    avval = coin[-1 - NISBAT_OYNA].close / btc[-1 - NISBAT_OYNA].close
    if avval <= 0:
        return None
    return hozir / avval


def _ogohlantirish(kirish: KuzatuvKirish) -> str | None:
    """Delisting/unlock xavfi — ko'rsatiladi, LEKIN to'smaydi.

    Rejim A da bu ikkisi zanjirni uzadi. Kuzatuv rejimida esa
    coin ro'yxatda qoladi: biz savdo qilmayapmiz, ko'rsatayapmiz,
    va aynan shu xabar admin bilishi kerak bo'lgan narsa.
    """
    return delisting_tosig(kirish.fundamental.delisting) or unlock_tosig(
        kirish.fundamental.unlock,
        yaqin_kun=kirish.unlock_yaqin_kun,
        katta_pct=kirish.unlock_katta_pct,
    )


def kuzatuv_yur(kirish: KuzatuvKirish) -> KuzatuvNatija:
    """Bitta coinni Rejim B da baholaydi.

    Zanjir UZILMAYDI: filtrdan o'tgan coin uchun to'rt blok ham
    to'liq hisoblanadi, blokning biri "yo'q" desa ham.
    """
    tf = kirish.timeframelar
    struktura_nuqtalar = swinglar(kirish.struktura_shamlar, shubhali=kirish.shubhali)
    yonalish = yonalish_aniqla(kirish.struktura_shamlar, struktura_nuqtalar)
    bosqich = bosqich_aniqla(kirish.struktura_shamlar, struktura_nuqtalar)
    narx = kirish.struktura_shamlar[-1].close if kirish.struktura_shamlar else None

    if not (yonalish.otadi and bosqich.nomzod):
        # Nomzod emas — qolgan uch blok hisoblanmaydi (resurs tejash).
        # Sabab NATIJADA qoladi: ekranda "nega ro'yxatda yo'q"
        # degan savolga javob bo'lsin.
        return KuzatuvNatija(
            kirish.symbol, yonalish, bosqich=bosqich, narx=narx, timeframelar=tf
        )

    b_fund = fundamental_blok(
        kirish.fundamental,
        unlock_yaqin_kun=kirish.unlock_yaqin_kun,
        unlock_katta_pct=kirish.unlock_katta_pct,
    )
    qutqarilganlar: list[tuple[str, str]] = []

    def _qutqar(
        blok: Blok, alternativlar: list[AlternativNatija]
    ) -> tuple[Blok, AlternativNatija | None]:
        """Blokni alternativ bilan qutqaradi va g'olibni qayd etadi."""
        yangi_blok, golib = qutqar(blok, alternativlar)
        if golib is not None:
            qutqarilganlar.append((blok.nom, golib.nom))
        return yangi_blok, golib

    b_struktura, _ = _qutqar(
        struktura_blok(
            StrukturaKirish(
                shamlar=kirish.struktura_shamlar,
                btc_shamlar=kirish.btc_shamlar,
                yosh_kun=kirish.yosh_kun,
                etalon=kirish.etalon,
                shubhali=kirish.shubhali,
            )
        ),
        alternativlar_2(kirish.struktura_shamlar, struktura_nuqtalar),
    )

    zona_nuqtalar = swinglar(kirish.zona_shamlar, shubhali=kirish.shubhali)
    zona_xom = zona_blok(
        ZonaKirish(
            shamlar=kirish.zona_shamlar,
            nuqtalar=zona_nuqtalar,
            ob_tarifi=kirish.ob_tarifi,
        )
    )
    b_zona, alt_zona = _qutqar(zona_xom.blok, alternativlar_3(zona_nuqtalar))
    # Alternativ zona g'alaba qozonsa, u asosiy zona O'RNINI oladi —
    # keyingi blok ham, ekran ham o'shani ko'radi.
    zona_natija = ZonaNatija(
        blok=b_zona,
        zona=zona_xom.zona,
        daraja=zona_xom.daraja,
        qatlamlar=zona_xom.qatlamlar,
    )
    zona_natija = zona_bilan(zona_natija, alt_zona) or zona_natija

    b_tasdiq, _ = _qutqar(
        tasdiqlash_blok(
            TasdiqKirish(
                shamlar=kirish.zona_shamlar,
                nuqtalar=zona_nuqtalar,
                pastki_shamlar=kirish.pastki_shamlar,
                zona=zona_natija.zona,
                # Rejim A da bu ikkisi VAQT bo'yicha solishtiriladi
                # (zanjir boshidagi va hozirgi fundamental). Kuzatuvda
                # esa tarix saqlanmaydi, shuning uchun ikkalasi bir xil
                # — tekshiruv "mos" deb o'qiydi va bu to'g'ri: vaqt
                # o'tmagan, o'zgarish ham bo'lmagan.
                eski_fundamental=b_fund,
                yangi_fundamental=b_fund,
            )
        ),
        alternativlar_4(kirish.zona_shamlar, zona_nuqtalar),
    )

    segmentlar = (
        Segment(
            "zona_konfluensiya",
            Holat.HA if zona_natija.daraja in YETARLI_DARAJA else Holat.YOQ,
            f"{zona_natija.daraja.value}: {', '.join(zona_natija.qatlamlar) or 'qatlam yo‘q'}",
            tf.zona,
        ),
        _segment("volume_profile", _tekshiruv(zona_natija.blok, "volume_profile"), tf.zona),
        _segment("liquidity_sweep", _tekshiruv(b_tasdiq, "liquidity_sweep"), tf.zona),
        _segment("rsi_divergensiya", _tekshiruv(b_tasdiq, "rsi_divergensiya"), tf.zona),
    )

    holat = bos_choch_topish(kirish.struktura_shamlar, struktura_nuqtalar)
    sweep_swing = oxirgi(zona_nuqtalar, SwingTuri.PAST)

    return KuzatuvNatija(
        symbol=kirish.symbol,
        yonalish=yonalish,
        bosqich=bosqich,
        narx=narx,
        bos_narx=holat.bos_narx if holat.bos_tasdiqlangan else None,
        sweep_narx=sweep_swing.narx if sweep_swing is not None else None,
        bloklar=(b_fund, b_struktura, zona_natija.blok, b_tasdiq),
        alternativlar=tuple(qutqarilganlar),
        zona_natija=zona_natija,
        segmentlar=segmentlar,
        ogohlantirish=_ogohlantirish(kirish),
        nisbiy_kuch=_nisbiy_kuch_qiymati(kirish.struktura_shamlar, kirish.btc_shamlar),
        timeframelar=tf,
    )


__all__ = [
    "KuzatuvKirish",
    "KuzatuvNatija",
    "Segment",
    "Timeframelar",
    "Yonalish",
    "kuzatuv_yur",
]
