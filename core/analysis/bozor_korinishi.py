"""BOZOR KO'RINISHI — sayt uchun haftalik va kunlik qarash.

LOYIHA EGASINING SHARTI (2026-09-03):

    "Haftalik va kunlik shunchaki qarash. Asosiy tahlil 4 soatlik.
     Bu umumiy ta'sir qilmaydi, faqat veb sayt uchun post.
     San uni 4 soatlikka bog'lama."

SHUNING UCHUN BU MODUL SIGNAL BERMAYDI VA SIGNALGA TA'SIR
QILMAYDI. U hech bir strategiyadan chaqirilmaydi, hech bir
darvozada turmaydi. Uning yagona iste'molchisi — sayt.

Bir marta rejim sifatida sinalgan (haftalik/kunlik 4 soatlik
kirishni to'sadigan qilib) va o'lchov uni RAD ETGAN: PF 0.84 ->
0.75 (`docs/BACKTEST_NATIJA_2026-09-03.md`). Ya'ni qaror ham,
o'lchov ham bir xil javob berdi.

NIMA KO'RSATILADI (loyiha egasi bergan ro'yxat):

    BTC, ETH          — narx
    BTC.D, USDT.D     — ustunlik foizlari
    TOTAL, TOTAL2,
    TOTAL3, OTHERS    — bozor kapitalizatsiyasi kesimlari

TAXMIN YOZILMAYDI. Modul FAKT beradi: qiymat, o'zgarish,
struktura yo'nalishi. "Kutilma" qatori ham an'anaviy o'qishdan
iborat va shunday belgilanadi — kafolat emas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.analysis.market_structure import analyze_structure
from core.domain.enums import TrendDirection
from core.domain.models import Candle


class KorinishTuri(str, Enum):
    """Qarash qanchalik keng."""

    HAFTALIK = "haftalik"
    KUNLIK = "kunlik"

    @property
    def label_uz(self) -> str:
        return "Haftalik qarash" if self is KorinishTuri.HAFTALIK else "Kunlik qarash"


#: Ko'rsatiladigan asboblar — loyiha egasi bergan ro'yxat, shu tartibda.
ASBOBLAR: tuple[tuple[str, str], ...] = (
    ("BTC", "Bitcoin"),
    ("ETH", "Ethereum"),
    ("BTC.D", "Bitcoin ustunligi"),
    ("USDT.D", "USDT ustunligi"),
    ("TOTAL", "Umumiy kapitalizatsiya"),
    ("TOTAL2", "BTC'siz kapitalizatsiya"),
    ("TOTAL3", "BTC va ETH'siz"),
    ("OTHERS", "Top 10'dan tashqari"),
)

#: Foiz bilan o'lchanadigan asboblar — ular narx emas, ULUSH.
ULUSH_ASBOBLARI = frozenset({"BTC.D", "USDT.D"})


@dataclass(frozen=True, slots=True)
class Asbob:
    """Bitta qatorning holati."""

    kod: str
    nom: str
    qiymat: float
    ozgarish_pct: float | None
    yonalish: TrendDirection

    @property
    def ulushmi(self) -> bool:
        return self.kod in ULUSH_ASBOBLARI

    def izoh(self) -> str:
        """Bir qatorli FAKT — taxmin emas."""
        yonalish_nomi = {
            TrendDirection.UP: "ko'tarilishda",
            TrendDirection.DOWN: "pasayishda",
            TrendDirection.FLAT: "yon harakatda",
        }[self.yonalish]
        if self.ozgarish_pct is None:
            return f"{yonalish_nomi} (o'zgarish uchun tarix yetarli emas)"
        belgi = "+" if self.ozgarish_pct >= 0 else ""
        return f"{yonalish_nomi}, {belgi}{self.ozgarish_pct:.2f}%"


@dataclass(frozen=True, slots=True)
class BozorKorinishi:
    """Bitta post — hafta boshida yoki kun boshida."""

    turi: KorinishTuri
    sana: datetime
    asboblar: list[Asbob] = field(default_factory=list)

    def asbob(self, kod: str) -> Asbob | None:
        return next((a for a in self.asboblar if a.kod == kod), None)

    @property
    def xulosa(self) -> str:
        """FAKTLARDAN yig'ilgan xulosa — hech narsa o'ylab topilmaydi."""
        kotarilgan = [a.kod for a in self.asboblar if a.yonalish is TrendDirection.UP]
        pasaygan = [a.kod for a in self.asboblar if a.yonalish is TrendDirection.DOWN]
        if not kotarilgan and not pasaygan:
            return "Bozor yon harakatda — aniq yo'nalish yo'q."
        qismlar = []
        if kotarilgan:
            qismlar.append("ko'tarilishda: " + ", ".join(kotarilgan))
        if pasaygan:
            qismlar.append("pasayishda: " + ", ".join(pasaygan))
        return "; ".join(qismlar) + "."

    @property
    def kutilma(self) -> str:
        """AN'ANAVIY o'qish — kafolat emas, va shunday yoziladi.

        Faqat uchta keng tarqalgan holat nomlanadi. Boshqa
        kombinatsiya uchun hech narsa o'ylab topilmaydi.
        """
        btc_d = self.asbob("BTC.D")
        usdt_d = self.asbob("USDT.D")
        if btc_d is None or usdt_d is None:
            return "Ustunlik ma'lumoti yo'q — o'qish berilmaydi."

        if usdt_d.yonalish is TrendDirection.UP:
            return (
                "USDT ustunligi o'smoqda — an'anaviy o'qishda bu kapital "
                "kriptodan chiqib, kutish holatiga o'tayotganini bildiradi. "
                "Kafolat emas."
            )
        if (
            usdt_d.yonalish is TrendDirection.DOWN
            and btc_d.yonalish is TrendDirection.DOWN
        ):
            return (
                "USDT va BTC ustunligi birga pasaymoqda — an'anaviy "
                "o'qishda bu altcoinlar uchun qulay davr. Kafolat emas."
            )
        if (
            usdt_d.yonalish is TrendDirection.DOWN
            and btc_d.yonalish is TrendDirection.UP
        ):
            return (
                "Kapital kriptoga kirmoqda, lekin asosan BTC'ga — "
                "an'anaviy o'qishda altcoinlar ortda qoladi. Kafolat emas."
            )
        return "Ustunliklar aniq yo'nalish bermayapti — o'qish berilmaydi."


def _yonalish(qiymatlar: list[float]) -> TrendDirection:
    """Sonlar qatorining yo'nalishi — sodda va ataylab shunday.

    Uchtadan kam nuqta bo'lsa FLAT: yo'nalish e'lon qilish uchun
    ma'lumot yetarli emas. Bu 0.3-band qoidasi — "aniqlab
    bo'lmadi" jazoga ham, ishonchga ham aylanmaydi.
    """
    if len(qiymatlar) < 3:
        return TrendDirection.FLAT
    birinchi, oxirgi = qiymatlar[0], qiymatlar[-1]
    if birinchi <= 0:
        return TrendDirection.FLAT
    ozgarish = (oxirgi - birinchi) / birinchi * 100
    if ozgarish > 1.0:
        return TrendDirection.UP
    if ozgarish < -1.0:
        return TrendDirection.DOWN
    return TrendDirection.FLAT


def _ozgarish(qiymatlar: list[float]) -> float | None:
    if len(qiymatlar) < 2 or qiymatlar[0] <= 0:
        return None
    return (qiymatlar[-1] - qiymatlar[0]) / qiymatlar[0] * 100


def korinish_qur(
    turi: KorinishTuri,
    sana: datetime,
    narx_qatorlari: dict[str, list[Candle]],
    kesim_tarixi: dict[str, list[float]],
) -> BozorKorinishi:
    """Ko'rinishni quradi.

    Args:
        turi: haftalik yoki kunlik.
        sana: post sanasi.
        narx_qatorlari: `BTC`, `ETH` uchun shamlar (shu turdagi
            timeframe: haftalik yoki kunlik).
        kesim_tarixi: `BTC.D`, `USDT.D`, `TOTAL`, `TOTAL2`,
            `TOTAL3`, `OTHERS` uchun saqlangan qiymatlar tarixi
            (eng eskisidan eng yangisiga). Bu qiymatlar birjadan
            sham sifatida kelmaydi — ular har kuni O'ZIMIZ
            saqlaymiz va tarix shundan yig'iladi.

    Tarix yetarli bo'lmasa qator baribir chiqadi: qiymat
    ko'rsatiladi, yo'nalish esa FLAT bo'ladi va izohda "tarix
    yetarli emas" deb yoziladi. Bo'sh sahifa ko'rsatishdan
    ko'ra ochiq aytish yaxshiroq.
    """
    asboblar: list[Asbob] = []
    for kod, nom in ASBOBLAR:
        shamlar = narx_qatorlari.get(kod)
        if shamlar:
            yopilishlar = [s.close for s in shamlar]
            asboblar.append(
                Asbob(
                    kod=kod,
                    nom=nom,
                    qiymat=yopilishlar[-1],
                    ozgarish_pct=_ozgarish(yopilishlar[-2:]),
                    yonalish=analyze_structure(shamlar).direction,
                )
            )
            continue

        tarix = kesim_tarixi.get(kod) or []
        if not tarix:
            continue
        asboblar.append(
            Asbob(
                kod=kod,
                nom=nom,
                qiymat=tarix[-1],
                ozgarish_pct=_ozgarish(tarix),
                yonalish=_yonalish(tarix),
            )
        )

    return BozorKorinishi(turi=turi, sana=sana, asboblar=asboblar)
