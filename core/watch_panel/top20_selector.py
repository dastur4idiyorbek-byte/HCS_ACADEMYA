"""4-QISM — saralash va ikki darajali ro'yxat.

    🟢 TOP 20    — eng yuqori Diqqat darajasiga ega 20 ta
    🟡 +10       — ulardan keyingi 10 ta, "diqqatga molik"

RO'YXAT DIQQAT DARAJASI BO'YICHA TARTIBLANADI, boshqa shart yo'q.

BU YERDA BIR MARTA "BOSQICH" DARVOZASI BO'LGAN va u OLIB
TASHLANDI (2026-09-13). 12-sentyabrda panelda ko'ringan coinlar
"allaqachon yurib bo'lgan"dek tuyuldi va narxning Fibonacci
zonasidagi o'rni bo'yicha qo'shimcha shart qo'yildi.

13-sentyabrda loyiha egasi natijani tekshirdi: o'sha 20 coindan
17 tasi haqiqatan yuqoriga yurgan edi. Ya'ni ro'yxat TO'G'RI
bo'lgan va qo'shimcha shart uni faqat buzgan.

Shuning uchun saralash o'zining dastlabki, ISHLAGAN holiga
qaytarildi.

FILTRDAN O'TMAGANLAR HECH QAYERGA KIRMAYDI. 3-qism qoidasi: coin
Downtrend bo'lsa, Diqqat darajasi qanchalik yuqori chiqishidan
QAT'I NAZAR, na Top 20 ga, na +10 ga qo'yilmaydi.

SUN'IY TO'LDIRISH YO'Q. Filtrdan o'tgan coin 20 tadan kam bo'lsa,
Top 20 kamroq ko'rinadi va +10 bo'sh qoladi. Bu — NORMAL holat:
bozor tushayotgan paytda xarid nomzodi kam bo'lishi kerak. Ro'yxatni
to'ldirish uchun pastroq coinni ko'tarish — aynan foydalanuvchini
chalg'itish bo'lardi.

TENG BALL CHIQQANDA TARTIB (prompt bo'yicha, shu ketma-ketlikda):

    1. Diqqat darajasi          (yuqoriroq ustun)
    2. Zona konfluensiya darajasi (Kuchli > O'rta > Zaif > Yo'q)
    3. Nisbiy kuch (coin/BTC)    (yuqoriroq ustun)
    4. Symbol alifbo bo'yicha    (BARQARORLIK uchun)

4-band promptda yo'q, lekin zarur: ansiz uchala mezoni ham teng
ikki coin har yugurishda o'rin almashardi va admin "nega tartib
o'zgardi?" deb o'ylardi. Alifbo — ma'noli emas, lekin BARQAROR.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.observation_mode import KuzatuvNatija
from core.analysis.zone_quality.zone_block import ZonaDarajasi

#: Asosiy ro'yxat hajmi.
TOP_HAJM = 20

#: Ikkinchi darajali ro'yxat hajmi.
KUZATUV_HAJM = 10

#: Zona darajasining tartib og'irligi — faqat SOLISHTIRISH uchun.
#: Bu ball EMAS va hech qanday qarorga qo'shilmaydi.
DARAJA_OGIRLIGI = {
    ZonaDarajasi.KUCHLI: 3,
    ZonaDarajasi.ORTA: 2,
    ZonaDarajasi.ZAIF: 1,
    ZonaDarajasi.YOQ: 0,
}


@dataclass(frozen=True, slots=True)
class Royxatlar:
    """Saralangan natija — ikki daraja va chetda qolganlar soni."""

    top: tuple[KuzatuvNatija, ...]
    kuzatuvda: tuple[KuzatuvNatija, ...]
    #: Filtrdan o'tmaganlar (Downtrend yoki aniq emas)
    otmadi: int = 0

    @property
    def jami_korinadi(self) -> int:
        return len(self.top) + len(self.kuzatuvda)


def _tartib_kaliti(n: KuzatuvNatija) -> tuple:
    """Kamayish tartibida saralash uchun kalit.

    Uchala raqam MANFIY belgi bilan olinadi, symbol esa musbat:
    shunda `sorted` bitta yugurishda "raqamlar kamayadi, nom
    o'sadi" tartibini beradi va `reverse=True` kerak bo'lmaydi
    (u symbolni ham teskari qilib yuborardi).
    """
    return (
        -n.diqqat,
        -DARAJA_OGIRLIGI.get(n.zona_darajasi, 0),
        -(n.nisbiy_kuch if n.nisbiy_kuch is not None else 0.0),
        n.symbol,
    )


def royxatlarni_qur(natijalar: list[KuzatuvNatija]) -> Royxatlar:
    """80 coindan ikki darajali ro'yxat yasaydi."""
    otganlar = sorted((n for n in natijalar if n.otdi), key=_tartib_kaliti)

    return Royxatlar(
        top=tuple(otganlar[:TOP_HAJM]),
        kuzatuvda=tuple(otganlar[TOP_HAJM : TOP_HAJM + KUZATUV_HAJM]),
        otmadi=len(natijalar) - len(otganlar),
    )
