"""SMC tuzilmaviy zonalari: Order Block, FVG va impuls/korreksiya.

Nima uchun ALOHIDA PAKET. `level_types.py` da "Strong Order Block"
bor edi, lekin u TASNIF — mavjud S/R zonasiga yorliq qo'yadi. Bu yerda
esa zonaning O'ZI topiladi: chekkalari bilan, chunki ular ENTRY va
STOP uchun ishlatiladi.

    Order Block  — impuls boshlangan nuqtadagi so'nggi qarama-qarshi
                   sham. Narx unga qaytsa — kirish zonasi; blokning
                   tashqi chekkasi — Stop.
    FVG          — uch sham orasidagi "bo'sh joy" (1-shamning yuqori
                   chekkasi 3-shamning quyi chekkasiga yetmagan).
                   Narx bo'shliqqa qaytsa — kirish zonasi.
    Impuls       — o'sish harakati; uning Fibonacci darajalari
                   korreksiya qayerda tugashi mumkinligini ko'rsatadi.

ASOSIY TAMOYIL (`bozor_salomatligi_asosiy_tuzatish.md`): ENTRY ham,
STOP ham BIR XIL strukturaviy manbadan kelib chiqadi. Biri qat'iy
foiz, ikkinchisi struktura bo'lib qolmaydi.

Bu modul SOF: tarmoqqa ham, bazaga ham murojaat qilmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.domain.models import Candle


class ZoneSource(str, Enum):
    """Zona qaysi usul bilan topilgan — ball va izoh uchun."""

    ORDER_BLOCK = "order_block"
    FVG = "fvg"
    FIBONACCI = "fibonacci"


@dataclass(frozen=True, slots=True)
class StructureZone:
    """Kirish nomzodi bo'la oladigan tuzilmaviy zona.

    `low`/`high` — zonaning chegaralari. SPOT xaridida Stop zonaning
    QUYI chekkasidan sal pastda turadi: zona buzilsa, uni yaratgan
    tuzilma ham buzilgan bo'ladi va kirish sababi qolmaydi.
    """

    source: ZoneSource
    low: float
    high: float
    #: Zonani hosil qilgan oxirgi shamning indeksi
    index: int
    at: datetime | None = None

    @property
    def center(self) -> float:
        return (self.low + self.high) / 2

    @property
    def width(self) -> float:
        return self.high - self.low

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high

    def overlaps(self, other: StructureZone) -> bool:
        """Ikki zona kesishadimi — confluence shu asosda aniqlanadi."""
        return self.low <= other.high and other.low <= self.high


# --------------------------------------------------------------------------- #
#  Impuls va korreksiya
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Impulse:
    """Yuqoriga qaragan impuls harakat: `start_index` dan `end_index` gacha."""

    start_index: int
    end_index: int
    low: float
    high: float

    @property
    def size(self) -> float:
        return self.high - self.low

    def retracement(self, ratio: float) -> float:
        """Fibonacci qaytish darajasi.

        0.382 — sayoz korreksiya, 0.618 — chuqur. Narx shu darajaga
        qaytganda kirish nomzodi ko'rib chiqiladi.
        """
        return self.high - self.size * ratio

    def retracement_ratio(self, price: float) -> float | None:
        """Berilgan narx impulsning necha ulushiga qaytgan (0..1+)."""
        if self.size <= 0:
            return None
        return (self.high - price) / self.size


def find_impulse(candles: list[Candle], lookback: int = 60) -> Impulse | None:
    """So'nggi YUQORIGA qaragan impulsni topadi.

    Usul: oynadagi eng yuqori cho'qqi topiladi, keyin undan OLDINGI
    eng past nuqta. Ya'ni "qayerdan qayerga ko'tarildi".

    NIMA UCHUN CHO'QQIDAN ORQAGA QARAYMIZ: eng past nuqtani avval
    izlasak, u cho'qqidan KEYIN bo'lib chiqishi mumkin — bu esa
    impuls emas, tushish bo'lardi. Fibonacci esa faqat ko'tarilish
    ustiga qurilsa ma'noga ega (spot: faqat xarid).
    """
    oyna = candles[-lookback:] if lookback > 0 else candles
    if len(oyna) < 3:
        return None

    ofset = len(candles) - len(oyna)
    cho_qqi = max(range(len(oyna)), key=lambda i: oyna[i].high)
    if cho_qqi == 0:
        return None

    tub = min(range(cho_qqi), key=lambda i: oyna[i].low)
    balandlik = oyna[cho_qqi].high - oyna[tub].low
    if balandlik <= 0:
        return None

    return Impulse(
        start_index=ofset + tub,
        end_index=ofset + cho_qqi,
        low=oyna[tub].low,
        high=oyna[cho_qqi].high,
    )


def fibonacci_zone(
    impulse: Impulse, ratios: list[float] | None = None
) -> StructureZone | None:
    """Fibonacci korreksiya zonasi — berilgan darajalar orasidagi oraliq.

    Standart 0.382-0.618 "oltin zona": sog'lom korreksiya odatda shu
    oraliqda tugaydi. Undan chuqurroq qaytish tuzilmaning o'zi
    buzilayotganini bildiradi.
    """
    nisbatlar = sorted(ratios or [0.382, 0.618])
    if impulse.size <= 0 or not nisbatlar:
        return None

    # Nisbat KATTA bo'lsa narx PAST bo'ladi (ko'proq qaytgan).
    return StructureZone(
        source=ZoneSource.FIBONACCI,
        low=impulse.retracement(nisbatlar[-1]),
        high=impulse.retracement(nisbatlar[0]),
        index=impulse.end_index,
    )


# --------------------------------------------------------------------------- #
#  Order Block
# --------------------------------------------------------------------------- #


def find_bullish_order_blocks(
    candles: list[Candle],
    lookback: int = 60,
    min_move_pct: float = 1.0,
    limit: int = 3,
) -> list[StructureZone]:
    """Ko'tarilish Order Blocklari — impuls boshlangan nuqtadagi tushuvchi sham.

    Ta'rif: TUSHUVCHI sham, undan keyin darhol kuchli KO'TARILISH
    boshlanadi. O'sha tushuvchi shamning tanasi — institutsional
    xaridlar qoldirgan iz. Narx unga qaytsa, o'sha xaridlar yana
    faollashishi kutiladi.

    `min_move_pct` — keyingi harakat shu foizdan katta bo'lishi kerak.
    Ansiz har bir tushuvchi sham "order block" bo'lib chiqardi va
    tushuncha ma'nosini yo'qotardi.
    """
    oyna = candles[-lookback:] if lookback > 0 else candles
    if len(oyna) < 3:
        return []

    ofset = len(candles) - len(oyna)
    natija: list[StructureZone] = []

    # Oxiridan boshiga: eng YANGI bloklar birinchi bo'lsin.
    for i in range(len(oyna) - 2, -1, -1):
        sham = oyna[i]
        if sham.is_bullish:
            continue

        # Blokdan keyingi harakat: keyingi shamlarning eng yuqori nuqtasi
        keyingi = oyna[i + 1 : i + 4]
        if not keyingi:
            continue
        cho_qqi = max(s.high for s in keyingi)
        if sham.low <= 0:
            continue
        harakat = (cho_qqi - sham.low) / sham.low * 100
        if harakat < min_move_pct:
            continue

        # Blok TANASI olinadi, soyasi emas: soya — shovqin, tana —
        # haqiqiy savdo hajmi bo'lgan oraliq.
        natija.append(
            StructureZone(
                source=ZoneSource.ORDER_BLOCK,
                low=min(sham.open, sham.close),
                high=max(sham.open, sham.close),
                index=ofset + i,
                at=sham.open_time,
            )
        )
        if len(natija) >= limit:
            break

    return natija


# --------------------------------------------------------------------------- #
#  Fair Value Gap
# --------------------------------------------------------------------------- #


def find_bullish_fvgs(
    candles: list[Candle],
    lookback: int = 60,
    min_gap_pct: float = 0.1,
    limit: int = 3,
) -> list[StructureZone]:
    """Ko'tarilish FVG lari — uch sham orasidagi to'ldirilmagan bo'shliq.

    Ta'rif: 1-shamning YUQORI nuqtasi 3-shamning QUYI nuqtasidan past
    bo'lsa, orada narx umuman savdo qilmagan oraliq qoladi. Bozor
    bunday bo'shliqlarni ko'pincha qaytib to'ldiradi — shuning uchun
    u kirish zonasi.

    `min_gap_pct` juda mayda bo'shliqlarni kesadi: har bir tez
    harakatda mikroskopik gaplar paydo bo'ladi va ular kirish
    nuqtasi sifatida ma'noga ega emas.
    """
    oyna = candles[-lookback:] if lookback > 0 else candles
    if len(oyna) < 3:
        return []

    ofset = len(candles) - len(oyna)
    natija: list[StructureZone] = []

    for i in range(len(oyna) - 3, -1, -1):
        birinchi, uchinchi = oyna[i], oyna[i + 2]
        past, baland = birinchi.high, uchinchi.low
        if baland <= past or past <= 0:
            continue
        if (baland - past) / past * 100 < min_gap_pct:
            continue

        natija.append(
            StructureZone(
                source=ZoneSource.FVG,
                low=past,
                high=baland,
                index=ofset + i + 1,
                at=oyna[i + 1].open_time,
            )
        )
        if len(natija) >= limit:
            break

    return natija


# --------------------------------------------------------------------------- #
#  Confluence
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Confluence:
    """Bir joyda uchrashgan zonalar — kirish nomzodi.

    `zones` da qancha ko'p manba bo'lsa, kirish shunchalik kuchli:
    Fibonacci + Order Block + FVG birga tushgan joy metodikada eng
    ishonchli kirish deb qaraladi.
    """

    low: float
    high: float
    zones: list[StructureZone]

    @property
    def strength(self) -> int:
        """Nechta TURLI manba mos keldi (1..3)."""
        return len({z.source for z in self.zones})

    @property
    def center(self) -> float:
        return (self.low + self.high) / 2

    def describe(self) -> str:
        nomlar = {
            ZoneSource.ORDER_BLOCK: "Order Block",
            ZoneSource.FVG: "FVG",
            ZoneSource.FIBONACCI: "Fibonacci",
        }
        # Tartib barqaror bo'lishi uchun manbalar ro'yxat tartibida
        korilgan: list[str] = []
        for z in self.zones:
            nom = nomlar[z.source]
            if nom not in korilgan:
                korilgan.append(nom)
        return " + ".join(korilgan)


def find_confluences(zones: list[StructureZone]) -> list[Confluence]:
    """Kesishuvchi zonalarni guruhlaydi, kuchlisidan boshlab qaytaradi.

    KESISHISH — bu "bir joyda" degani. Ikki zona kesishmasa, ular
    ikki xil kirish nomzodi; kesishsa, bitta va kuchliroq nomzod.
    """
    qolgan = list(zones)
    natija: list[Confluence] = []

    while qolgan:
        asos = qolgan.pop(0)
        guruh = [asos]
        past, baland = asos.low, asos.high

        # Guruh o'sib borishi mumkin: yangi qo'shilgan zona boshqasini
        # ham tortib kelishi mumkin, shuning uchun aylanma takrorlanadi.
        ozgardi = True
        while ozgardi:
            ozgardi = False
            for z in list(qolgan):
                if z.low <= baland and past <= z.high:
                    guruh.append(z)
                    qolgan.remove(z)
                    # Kesishma OLINADI, birlashma emas: kirish zonasi
                    # qancha tor bo'lsa, Stop shuncha yaqin va xavf
                    # shuncha kichik.
                    past = max(past, z.low)
                    baland = min(baland, z.high)
                    ozgardi = True

        natija.append(Confluence(low=past, high=baland, zones=guruh))

    natija.sort(key=lambda c: (c.strength, c.center), reverse=True)
    return natija
