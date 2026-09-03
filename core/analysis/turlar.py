"""Blok zanjiri uchun umumiy tiplar — barcha 4 blok shu tilda gapiradi.

NIMA UCHUN BITTA JOYDA: eski tizimda har bir strategiya o'z natija
tipini qaytarardi va ularni solishtirish uchun har safar yangi
moslashtiruvchi kod yozilardi. Ablatsiya esa AYNAN solishtirishga
tayanadi — "bu tekshiruvni olib tashlasak nima o'zgaradi".

UCHTA HOLAT, IKKITA EMAS. `MALUMOT_YOQ` alohida turadi va bu —
loyihaning eng qimmat saboqlaridan biri. Agar "ma'lumot yo'q" ni
"yo'q" (❌) deb hisoblasak, backtestda tarixi bo'lmagan har bir
manba blokni nolga tushiradi va zanjir HECH QACHON ulanmaydi —
ya'ni biz strategiyani emas, ma'lumot yetishmasligini o'lchagan
bo'lardik (`docs/FUNDAMENTAL_MALUMOT_MANBALARI.md`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Holat(str, Enum):
    """Bitta ichki tekshiruvning natijasi."""

    HA = "ha"
    YOQ = "yoq"
    #: Manba mavjud emas yoki tarix yetmaydi. Maxrajga KIRMAYDI.
    MALUMOT_YOQ = "malumot_yoq"


@dataclass(frozen=True, slots=True)
class Tekshiruv:
    """Bitta ichki tekshiruv — 16 tasidan biri."""

    nom: str
    holat: Holat
    #: Odam o'qiydigan sabab. Admin monitorida va "Nega bu signal?" da.
    izoh: str = ""

    @property
    def ijobiy(self) -> bool:
        return self.holat is Holat.HA

    @property
    def olchandi(self) -> bool:
        return self.holat is not Holat.MALUMOT_YOQ


@dataclass(frozen=True, slots=True)
class Blok:
    """Bitta katta blokning natijasi (4 ichki tekshiruvdan yig'ilgan).

    ZANJIR QOIDASI (2-prompt, 4-qism):

        0/4  -> blok BUTUNLAY BO'SH -> zanjir shu yerda UZILADI
        1-4/4 -> blok o'tadi, kuch darajasi bilan

    `olchanmadi` — uchinchi holat, promptda yo'q, lekin amalda zarur:
    barcha ichki tekshiruvlarning ma'lumoti yo'q bo'lsa, bu "blok
    bo'sh" degani EMAS. Bunday blok zanjirni uzmaydi, lekin ishonch
    formulasiga ham kirmaydi — u shunchaki jim turadi.
    """

    nom: str
    tekshiruvlar: tuple[Tekshiruv, ...]
    #: Ichki tekshiruvdan tashqari sabab bilan butunlay to'sish
    #: (masalan Token Unlock qattiq to'sig'i). Bu holda `otdi` False.
    qattiq_tosiq: str | None = None
    #: 1-blokdagi "ZIDDIYATLI" belgisi (2-prompt, 4-qism, BLOK 1)
    ziddiyatli: bool = False

    @property
    def kuch(self) -> int:
        """Necha ichki tekshiruv ✅ bo'ldi."""
        return sum(1 for t in self.tekshiruvlar if t.ijobiy)

    @property
    def maxraj(self) -> int:
        """Necha ichki tekshiruv HAQIQATAN o'lchandi.

        `MALUMOT_YOQ` kirmaydi: 4 tadan 2 tasining manbai bo'lmasa,
        "2/4" deb yozish yolg'on — aslida "2/2" o'lchandi.
        """
        return sum(1 for t in self.tekshiruvlar if t.olchandi)

    @property
    def olchanmadi(self) -> bool:
        return self.maxraj == 0

    @property
    def otdi(self) -> bool:
        if self.qattiq_tosiq is not None:
            return False
        if self.olchanmadi:
            # Ma'lumot yo'qligi zanjirni uzmaydi — yuqoridagi izohga qarang.
            return True
        return self.kuch >= 1

    @property
    def nisbat(self) -> float:
        """Ishonch formulasi uchun 0..1. O'lchanmagan blok — 0.0 emas, `None`."""
        return self.kuch / self.maxraj if self.maxraj else 0.0

    def __str__(self) -> str:
        if self.qattiq_tosiq:
            return f"{self.nom}: TO'SILDI ({self.qattiq_tosiq})"
        if self.olchanmadi:
            return f"{self.nom}: o'lchanmadi"
        belgi = "✅" if self.otdi else "❌"
        ziddiyat = " ⚠️ ziddiyatli" if self.ziddiyatli else ""
        return f"{self.nom}: {self.kuch}/{self.maxraj} {belgi}{ziddiyat}"


@dataclass(frozen=True, slots=True)
class Zanjir:
    """To'rt blokning ketma-ket natijasi.

    `uzildi_blokda` — qaysi blokda uzilgani. `None` bo'lsa zanjir
    to'liq bog'langan va signal chiqishi mumkin.
    """

    bloklar: tuple[Blok, ...] = field(default_factory=tuple)
    uzildi_blokda: str | None = None

    @property
    def toliq(self) -> bool:
        return self.uzildi_blokda is None and len(self.bloklar) == 4

    @property
    def olchangan_bloklar(self) -> tuple[Blok, ...]:
        return tuple(b for b in self.bloklar if not b.olchanmadi)

    def ishonch(self) -> float:
        """Yakuniy ishonch darajasi, 0..1.

        FORMULA: o'lchangan bloklarning nisbatlari O'RTACHASI.

        NIMA UCHUN YIG'INDI EMAS: yig'indi blok soniga bog'liq bo'lardi
        va o'lchanmagan blok natijani jimgina pasaytirardi. O'rtacha esa
        "har bir blok o'z ichida qanchalik kuchli" degan savolga javob
        beradi — blok soni o'zgarsa ham ma'nosi buzilmaydi.

        🔴 CHEGARA O'LCHANMAGAN. Qaysi ishonchdan yuqorisi signal
        beradi — backtest orqali topiladi (2-prompt, 0-qism, 3-tamoyil).
        Bu funksiya faqat RAQAM beradi, qaror qabul qilmaydi.
        """
        olchangan = self.olchangan_bloklar
        if not olchangan:
            return 0.0
        return sum(b.nisbat for b in olchangan) / len(olchangan)

    def matn(self) -> str:
        """Jonli Oshxona monitori uchun (2-prompt, 6-qism)."""
        qatorlar = [str(b) for b in self.bloklar]
        if self.uzildi_blokda:
            qatorlar.append(f"⛓️‍💥 zanjir uzildi: {self.uzildi_blokda}")
        else:
            qatorlar.append(f"🔗 to'liq — ishonch {self.ishonch():.2f}")
        return "\n".join(qatorlar)


def blok(
    nom: str,
    tekshiruvlar: list[Tekshiruv],
    *,
    qattiq_tosiq: str | None = None,
    ziddiyatli: bool = False,
) -> Blok:
    """Qulaylik uchun quruvchi — ro'yxatni tuple ga aylantiradi."""
    return Blok(
        nom=nom,
        tekshiruvlar=tuple(tekshiruvlar),
        qattiq_tosiq=qattiq_tosiq,
        ziddiyatli=ziddiyatli,
    )


def ha(nom: str, izoh: str = "") -> Tekshiruv:
    return Tekshiruv(nom=nom, holat=Holat.HA, izoh=izoh)


def yoq(nom: str, izoh: str = "") -> Tekshiruv:
    return Tekshiruv(nom=nom, holat=Holat.YOQ, izoh=izoh)


def malumot_yoq(nom: str, izoh: str = "manba mavjud emas") -> Tekshiruv:
    return Tekshiruv(nom=nom, holat=Holat.MALUMOT_YOQ, izoh=izoh)
