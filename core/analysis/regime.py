"""BOZOR REJIMI — har timeframe bitta savolga javob beradi.

MUAMMO (loyiha egasining kuzatuvi, 2026-09-03).

Tizim bir nechta timeframeni o'qiydi va ularning hammasini BITTA
BALLGA qo'shadi. Lekin ular bir-biridan mustaqil emas: kunlik
ko'tarilish va 4 soatlik ko'tarilish ko'pincha AYNAN BIR XIL
narsa. Ya'ni bitta dalil bir necha marta sanaladi va ball o'zini
haqiqatdan kuchliroq ko'rsatadi.

Ikkinchi muammo undan ham jiddiyroq: ballda hech kim "YO'Q" deya
olmaydi. Haftalik tushayotgan bo'lsa ham, boshqa beshta omil
yaxshi bo'lsa, ball baribir yetadi va signal chiqadi. Bozor
pasayayotganda spot xarid qilish esa — eng qimmat xato.

YECHIM: HAR TIMEFRAME BITTA ISH QILADI.

    haftalik   ->  bu hafta nima kutamiz      (yo'nalish)
    kunlik     ->  bugun bozor qay holatda    (rejim)
    4 soatlik  ->  kirish shu yerda           (tahlil)

Haftalik va kunlik SIGNAL BERMAYDI — ular REJIMNI aytadi. Rejim
esa qanday qoida bilan ishlashni belgilaydi:

    KO'TARILISH  ->  tuzatishni kutib olinadi (odatiy Discount)
    DIAPAZON     ->  faqat diapazon TUBIDAN olinadi (chuqurroq)
    TUSHISH      ->  umuman olinmaydi

Bu ball emas, SHART. Rejim "yo'q" desa, ball qancha bo'lishidan
qat'i nazar signal chiqmaydi.

BU GIPOTEZA. Standart holatda o'chiq bo'lib, backtest bilan
o'lchanadi (`docs/GIPOTEZA_DAFTARI.md`). Ilgari shunga
o'xshash "kunlik trend majburiy" filtri sinalgan va u natijani
yaxshilamagan (natija #3). LEKIN u boshqa narsa edi: filtr
signallarni FAQAT KESARDI. Bu yerda har rejim uchun BOSHQA
QOIDA bor — kesish emas, moslashish.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.config.schema import RegimeRulesConfig
from core.domain.enums import TrendDirection


class BozorRejimi(str, Enum):
    """Bozorning uchta holati — boshqa holat yo'q."""

    KOTARILISH = "kotarilish"
    DIAPAZON = "diapazon"
    TUSHISH = "tushish"

    @property
    def emoji(self) -> str:
        return {
            BozorRejimi.KOTARILISH: "📈",
            BozorRejimi.DIAPAZON: "↔️",
            BozorRejimi.TUSHISH: "📉",
        }[self]

    @property
    def label_uz(self) -> str:
        return {
            BozorRejimi.KOTARILISH: "Ko'tarilish",
            BozorRejimi.DIAPAZON: "Diapazon",
            BozorRejimi.TUSHISH: "Pasayish",
        }[self]


@dataclass(frozen=True, slots=True)
class RejimQarori:
    """Rejim va uning SABABI.

    Sabab kartochkada ham, "Nega signal yo'q?" ekranida ham
    ko'rsatiladi: foydalanuvchi qaysi timeframe qaror qilganini
    ko'rishi kerak.
    """

    rejim: BozorRejimi
    haftalik: TrendDirection
    kunlik: TrendDirection
    sabab: str

    @property
    def kirish_mumkin(self) -> bool:
        return self.rejim is not BozorRejimi.TUSHISH


def rejimni_aniqla(
    haftalik: TrendDirection,
    kunlik: TrendDirection,
) -> RejimQarori:
    """Haftalik va kunlik strukturadan rejimni chiqaradi.

    JADVAL TO'LIQ — har kombinatsiya uchun javob bor:

        haftalik   kunlik     rejim
        --------   --------   -----------
        DOWN       har qanday TUSHISH      katta rasm qarshi
        har qanday DOWN        TUSHISH     bugun qarshi
        UP         UP          KO'TARILISH ikkalasi bir tomonda
        qolgani                DIAPAZON    aniq yo'nalish yo'q

    FLAT "yomon" degani emas — u "aniq emas" degani, va aniq
    bo'lmagan bozor diapazon deb hisoblanadi. Bu 0.3-bandning
    qoidasi: ma'lumot yetishmasligi jazoga aylanmaydi, lekin
    ishonchga ham aylanmaydi.
    """
    if haftalik is TrendDirection.DOWN:
        return RejimQarori(
            BozorRejimi.TUSHISH,
            haftalik,
            kunlik,
            "Haftalik struktura pasayishda — spot xaridi katta rasmga qarshi",
        )
    if kunlik is TrendDirection.DOWN:
        return RejimQarori(
            BozorRejimi.TUSHISH,
            haftalik,
            kunlik,
            "Kunlik struktura pasayishda — bugun xarid qilinmaydi",
        )
    if haftalik is TrendDirection.UP and kunlik is TrendDirection.UP:
        return RejimQarori(
            BozorRejimi.KOTARILISH,
            haftalik,
            kunlik,
            "Haftalik va kunlik ko'tarilishda — tuzatish kutiladi",
        )
    return RejimQarori(
        BozorRejimi.DIAPAZON,
        haftalik,
        kunlik,
        "Aniq yo'nalish yo'q — faqat diapazon tubidan olinadi",
    )


def kirish_chegarasi(rejim: BozorRejimi, qoidalar: RegimeRulesConfig) -> float:
    """Shu rejimda narx diapazonning qaysi qismigacha ruxsat etiladi.

    KO'TARILISH da chegara kengroq: trend ichidagi tuzatish
    ko'pincha diapazon o'rtasiga yetmay tugaydi, uni qattiq
    talab qilish kirishni butunlay yo'q qilardi.

    DIAPAZON da chegara qattiqroq: bu yerda trend yordam
    bermaydi, faqat tubdan olingan xaridning o'zi ma'noga ega.
    """
    if rejim is BozorRejimi.KOTARILISH:
        return qoidalar.kotarilish_max_range_pct
    if rejim is BozorRejimi.DIAPAZON:
        return qoidalar.diapazon_max_range_pct
    return 0.0
