"""3-QISM FILTRI — faqat yuqoriga yurish potensiali bor coinlar.

NIMA UCHUN BU ENG MUHIM QOIDA. Biz SPOT savdo qilamiz: faqat
XARID, short yo'q. Tushayotgan coin qanchalik "chiroyli" zona
ko'rsatmasin, u bizga YARAMAYDI. Shuning uchun filtr Diqqat
darajasini hisoblashdan OLDIN qo'llanadi.

IKKI HOLAT O'TADI:

    (a) UPTREND      — HH/HL ketma-ketligi davom etayapti
    (b) YANGI BURILISH — coin tushishdan endi chiqdi: oxirgi swing
                         YUQORI yopilish bilan kesib o'tilgan va
                         bundan oldin struktura tushayotgan edi

NEGA (b) ALOHIDA YOZILDI. Loyihaning mavjud `bos_choch.py` moduli
CHOCH ni faqat BITTA yo'nalishda biladi: "narx oxirgi swing pastni
kesdi — ko'tarilish tugadi". Teskarisi — tushishdan yuqoriga
burilish — u yerda umuman yo'q.

Uni `bos_choch.py` ga qo'shish MUMKIN EDI, lekin qilinmadi:
o'sha fayl Rejim A (signal moduli) tomonidan ishlatiladi va uni
o'zgartirish signal modulining javobini ham o'zgartirardi. Prompt
esa aniq aytadi: mavjud bloklar TEGILMAYDI. Shuning uchun burilish
aniqlash SHU YERDA, yangi modul ichida yozildi.

"YANGI" DEGANI QANCHA VAQT. Burilish `YANGI_OYNA` ta shamdan
oldin bo'lgan bo'lsa, u endi "yangi" emas: shuncha vaqt o'tib coin
haqiqatan ko'tarilayotgan bo'lsa, (a) shartining o'zi uni
o'tkazadi. Aks holda burilish tasdiqlanmagan — demak nomzod emas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.analysis.structure.swing_detector import Swing, SwingTuri, ketma_ketlik_kotarilish
from core.analysis.zone_quality.fibonacci import fib_zona, oxirgi_impuls
from core.domain.models import Candle

#: Burilish shuncha oxirgi sham ichida bo'lsa — "yangi".
#:
#: 🔴 O'LCHANMAGAN. 10 — taxmin, backtestdan chiqmagan. Kuzatuv
#: paneli savdo qarori qabul qilmagani uchun bu raqam pulga
#: ta'sir qilmaydi; agar kelajakda qaror qabul qilinadigan
#: bo'lsa, avval o'lchanishi SHART (`GIPOTEZA_DAFTARI.md`).
YANGI_OYNA = 10

#: Burilishdan oldin struktura tushayotganini tasdiqlash uchun
#: kerakli eng kam swing soni (2 yuqori + 2 past).
ENG_KAM_SWING = 2


class Yonalish(str, Enum):
    """Coinning struktura yo'nalishi — filtr uchun."""

    UPTREND = "uptrend"
    #: Tushishdan endi chiqdi (yuqoriga burilish tasdiqlangan)
    YANGI_BURILISH = "yangi_burilish"
    DOWNTREND = "downtrend"
    #: Na u, na bu — yassi yoki tarix yetmaydi.
    #:
    #: DOWNTREND dan ALOHIDA turadi va bu ataylab: "aniq emas" —
    #: bu "tushyapti" degani emas. Ikkalasi ham filtrdan o'tmaydi,
    #: lekin ekranda sabab boshqacha yoziladi.
    ANIQ_EMAS = "aniq_emas"

    @property
    def otadi(self) -> bool:
        """Shu yo'nalish bilan coin ro'yxatga kira oladimi."""
        return self in (Yonalish.UPTREND, Yonalish.YANGI_BURILISH)


@dataclass(frozen=True, slots=True)
class YonalishNatija:
    """Filtr natijasi — yo'nalish va uni tushuntiruvchi raqamlar."""

    yonalish: Yonalish
    #: Burilish qaysi narxda tasdiqlangan (faqat YANGI_BURILISH da)
    burilish_narx: float | None = None
    #: Burilishdan beri necha sham o'tgan
    burilish_yosh: int | None = None
    izoh: str = ""

    @property
    def otadi(self) -> bool:
        return self.yonalish.otadi


def _tushayotgan(nuqtalar: list[Swing], kesish_indeks: int) -> bool:
    """KESISH PAYTIDA struktura LH/LL bo'lganmi.

    O'LCHOV NUQTASI — KESISH SHAMI, kesilgan swingning o'zi emas.
    Bu farq muhim: tushish shakli

        H1(200) -> L1(150) -> H2(180, LH) -> L2(130, LL) -> kesish

    da kesiladigan daraja — H2. Agar oyna H2 gacha olinsa, H2 ning
    o'zi ham, undan keyingi L2 ham chiqib ketadi va qo'lda faqat
    bitta yuqori bilan bitta past qoladi — LH/LL ni umuman
    o'lchab bo'lmaydi. Shuning uchun oyna kesish shamigacha
    cho'ziladi: kesishgacha shakllangan HAMMA swing hisobga olinadi,
    kesishdan keyingilari (narx allaqachon ko'tarilgan payt)
    hisobga olinmaydi.

    Bu xato birinchi yozuvda bor edi va testda ushlandi.
    """
    oldingilar = [s for s in nuqtalar if s.indeks < kesish_indeks]
    yuqorilar = [s.narx for s in oldingilar if s.turi is SwingTuri.YUQORI]
    pastlar = [s.narx for s in oldingilar if s.turi is SwingTuri.PAST]
    if len(yuqorilar) < ENG_KAM_SWING or len(pastlar) < ENG_KAM_SWING:
        return False
    # Lower High VA Lower Low — ikkalasi ham shart, xuddi
    # `ketma_ketlik_kotarilish` dagi kabi, faqat teskari tomonga.
    return yuqorilar[-1] < yuqorilar[-2] and pastlar[-1] < pastlar[-2]


def _burilish(shamlar: list[Candle], nuqtalar: list[Swing]) -> tuple[float, int] | None:
    """Tushishdan yuqoriga burilish bo'lganmi.

    Qoida: oxirgi swing YUQORI yopilish bilan kesib o'tilgan
    (wick bilan emas — `bos_choch.py` dagi bilan bir xil tamoyil),
    va o'sha yuqoridan OLDIN struktura tushayotgan edi.

    Returns:
        (kesib o'tilgan narx, kesishdan beri o'tgan sham soni) yoki
        `None`.
    """
    yuqorilar = [s for s in nuqtalar if s.turi is SwingTuri.YUQORI]
    # Eng so'nggisidan orqaga qarab: birinchi kesib o'tilgani —
    # aynan burilish nuqtasi. Undan oldingilari eskirgan.
    for swing in reversed(yuqorilar):
        for i in range(swing.indeks + 1, len(shamlar)):
            if shamlar[i].close > swing.narx:
                if not _tushayotgan(nuqtalar, i):
                    return None
                return swing.narx, len(shamlar) - 1 - i
        # Bu swing kesilmagan — undan oldingilari ham ahamiyatsiz,
        # chunki ular pastroq turadi va allaqachon kesilgan bo'lardi.
    return None


def yonalish_aniqla(shamlar: list[Candle], nuqtalar: list[Swing]) -> YonalishNatija:
    """Coin xarid nomzodi bo'la oladimi — va nima uchun.

    Args:
        shamlar: ASOSIY timeframe shamlari, eskisidan yangisiga
        nuqtalar: o'sha shamlardan hisoblangan swinglar
    """
    if len(nuqtalar) < ENG_KAM_SWING * 2:
        return YonalishNatija(Yonalish.ANIQ_EMAS, izoh="swing nuqtalar yetmaydi")

    if ketma_ketlik_kotarilish(nuqtalar):
        return YonalishNatija(Yonalish.UPTREND, izoh="HH/HL ketma-ketligi davom etmoqda")

    topildi = _burilish(shamlar, nuqtalar)
    if topildi is not None:
        narx, yosh = topildi
        if yosh <= YANGI_OYNA:
            return YonalishNatija(
                Yonalish.YANGI_BURILISH,
                burilish_narx=narx,
                burilish_yosh=yosh,
                izoh=f"tushishdan chiqdi: {narx:g} darajasi yopilish bilan kesildi",
            )
        # Burilish bor, lekin eskirgan VA HH/HL hali yig'ilmagan —
        # ya'ni ko'tarilish tasdiqlanmadi. Bu nomzod emas.
        return YonalishNatija(
            Yonalish.ANIQ_EMAS,
            burilish_narx=narx,
            burilish_yosh=yosh,
            izoh=f"burilish {yosh} sham oldin bo'lgan, ko'tarilish tasdiqlanmadi",
        )

    yuqorilar = [s.narx for s in nuqtalar if s.turi is SwingTuri.YUQORI]
    pastlar = [s.narx for s in nuqtalar if s.turi is SwingTuri.PAST]
    if (
        len(yuqorilar) >= ENG_KAM_SWING
        and len(pastlar) >= ENG_KAM_SWING
        and yuqorilar[-1] < yuqorilar[-2]
        and pastlar[-1] < pastlar[-2]
    ):
        return YonalishNatija(Yonalish.DOWNTREND, izoh="LH/LL — struktura tushmoqda")

    return YonalishNatija(Yonalish.ANIQ_EMAS, izoh="yo'nalish aniq emas")


# --------------------------------------------------------------------------- #
#  BOSQICH — coin harakatning qayerida
# --------------------------------------------------------------------------- #
#
# NIMA UCHUN QO'SHILDI (2026-09-12, loyiha egasining kuzatuvi).
#
# Filtr faqat YO'NALISHni tekshirardi: "HH/HL ketma-ketligi bormi".
# Lekin HH/HL ketma-ketligi coin ALLAQACHON YURGANDA ham to'g'ri
# bo'ladi — aslida u eng kuchli aynan shunda ko'rinadi. Natijada
# Top 20 ga harakatini tugatgan coinlar chiqardi.
#
# Loyiha egasi buni ekranda ko'rdi va aytdi: "ular allaqachon yurib
# bo'lgan, bizga yurish potensiali bor lekin HALI YURMAGANI kerak".
#
# Yechim: yo'nalishdan tashqari NARXNING O'RNI ham tekshiriladi.
# O'lchov — loyihaning O'Z Fibonacci zonasi (`fib_zona`), yangi
# raqam o'ylab topilmadi:
#
#     narx zona TEPASIDA   -> YURGAN     (nomzod EMAS)
#     narx zona ICHIDA     -> KORREKSIYA (nomzod ✓)
#     narx zona PASTIDA    -> CHUQUR     (nomzod ✓, chuqurroq qaytgan)
#
# Zona chegaralari — 38.2% va 61.8% qaytish (`fibonacci.py` dagi
# FIB_YUQORI/FIB_PAST). Ular allaqachon config'da va o'zgartirilsa
# bu yerga ham o'tadi.


class Bosqich(str, Enum):
    """Narx oxirgi impulsning qayerida."""

    #: Fib zonasi ichida — klassik qaytish nuqtasi
    KORREKSIYA = "korreksiya"
    #: Zonadan pastda — chuqurroq qaytgan
    CHUQUR = "chuqur"
    #: Zona tepasida — harakat allaqachon bo'lgan
    YURGAN = "yurgan"
    #: Impuls topilmadi
    NOMALUM = "nomalum"

    @property
    def nomzod(self) -> bool:
        """Shu bosqichda coin ro'yxatga kira oladimi.

        `NOMALUM` o'tadi: impuls topilmasligi "yurib bo'lgan"
        degani EMAS. Uni rad etish ma'lumot yo'qligini jazoga
        aylantirardi (`turlar.py` dagi MALUMOT_YOQ tamoyili).
        """
        return self is not Bosqich.YURGAN


@dataclass(frozen=True, slots=True)
class BosqichNatija:
    bosqich: Bosqich
    #: Narx impuls oralig'ining necha foizida (0 — tub, 100 — cho'qqi)
    ulush: float | None = None
    #: Impuls chegaralari — ekranda ko'rsatish uchun
    impuls_past: float | None = None
    impuls_yuqori: float | None = None
    izoh: str = ""

    @property
    def nomzod(self) -> bool:
        return self.bosqich.nomzod


def bosqich_aniqla(shamlar: list[Candle], nuqtalar: list[Swing]) -> BosqichNatija:
    """Narx oxirgi ko'tarilish impulsining qayerida.

    Args:
        shamlar: ASOSIY timeframe, eskisidan yangisiga
        nuqtalar: o'sha shamlardan hisoblangan swinglar
    """
    if not shamlar:
        return BosqichNatija(Bosqich.NOMALUM, izoh="sham yo'q")

    impuls = oxirgi_impuls(nuqtalar)
    zona = fib_zona(nuqtalar)
    if impuls is None or zona is None:
        return BosqichNatija(Bosqich.NOMALUM, izoh="ko'tarilish impulsi topilmadi")

    boshi, oxiri = impuls
    uzunlik = oxiri.narx - boshi.narx
    if uzunlik <= 0:
        return BosqichNatija(Bosqich.NOMALUM, izoh="impuls uzunligi noldan katta emas")

    narx = shamlar[-1].close
    ulush = round(100.0 * (narx - boshi.narx) / uzunlik, 1)

    if narx > zona.yuqori:
        return BosqichNatija(
            Bosqich.YURGAN,
            ulush,
            boshi.narx,
            oxiri.narx,
            f"narx impulsning {ulush:g}% ida — qaytish zonasidan yuqorida",
        )
    if narx >= zona.past:
        return BosqichNatija(
            Bosqich.KORREKSIYA,
            ulush,
            boshi.narx,
            oxiri.narx,
            f"narx qaytish zonasida ({ulush:g}%)",
        )
    return BosqichNatija(
        Bosqich.CHUQUR,
        ulush,
        boshi.narx,
        oxiri.narx,
        f"narx zonadan pastda ({ulush:g}%) — chuqur qaytish",
    )
