"""2-qism: dinamik chiqish rejasi — N ta TP ga moslashadi.

QOIDA (3-prompt, 2-qism):

    TP[k] ga yetganda:
        1/N qism sotiladi
        Stop -> TP[k-1] narxiga ko'chiriladi
                (k=1 bo'lsa Stop -> Entry, ya'ni breakeven)

    Eng oxirgi TP da qolgan HAMMASI sotiladi.

ENG MUHIM TALAB: "faqat 2 ta TP" yoki "faqat 3 ta TP" degan
cheklov YO'Q. N — o'zgaruvchi. Shuning uchun bu faylda birorta
ham `if tp_soni == 2` ko'rinishidagi shart yo'q: formula
bittada N ni oladi.

Eski `core/position/scaling_out.py` da ulushlar QO'LDA yozilgan
jadval edi (50/50, 50/30/20) va u faqat 1-3 TP ni bilardi. Bu
modul o'sha cheklovni olib tashlaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

#: Nol bilan solishtirishda ishlatiladigan aniqlik.
EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class Bosqich:
    """Bitta TP bosqichi va undan keyingi Stop."""

    raqam: int
    narx: float
    ulush_pct: float
    #: Shu bosqich bajarilgandan KEYIN Stop qayerga ko'chadi.
    yangi_stop: float


@dataclass(frozen=True, slots=True)
class ChiqishRejasi:
    """Signalning to'liq chiqish rejasi."""

    entry: float
    boshlangich_stop: float
    bosqichlar: tuple[Bosqich, ...]

    @property
    def tp_soni(self) -> int:
        return len(self.bosqichlar)


@dataclass(frozen=True, slots=True)
class ChiqishHolati:
    """Rejaning HOZIRGI holati — qaysi bosqichgacha bajarilgani."""

    reja: ChiqishRejasi
    bajarilgan: int = 0
    joriy_stop: float = 0.0
    #: Hali sotilmagan ulush, foizda.
    ochiq_ulush_pct: float = 100.0
    yopilgan: bool = False
    yopilish_sababi: str = ""
    #: Stop yoki muddat bilan yopilganda — o'sha paytda ochiq
    #: bo'lgan ulush. `ochiq_ulush_pct` nolga tushgani uchun uni
    #: keyin tiklab bo'lmasdi va natija hisobida o'sha qism
    #: JIMGINA yo'qolardi.
    qoldiq_ulush_pct: float = 0.0

    @property
    def keyingi_bosqich(self) -> Bosqich | None:
        if self.yopilgan or self.bajarilgan >= self.reja.tp_soni:
            return None
        return self.reja.bosqichlar[self.bajarilgan]

    @property
    def xavfsizmi(self) -> bool:
        """Stop kamida kirish narxiga ko'chganmi (zarar imkoni yo'q)."""
        return self.joriy_stop >= self.reja.entry


def chiqish_rejasi_qur(
    entry: float,
    stop: float,
    tplar: list[float] | tuple[float, ...],
    ulushlar: list[float] | tuple[float, ...] | None = None,
) -> ChiqishRejasi:
    """N ta TP dan chiqish rejasini quradi.

    Args:
        ulushlar: har bosqichda sotiladigan ulush. Berilmasa — teng
            (100/N). Berilsa uzunligi TP soniga teng bo'lishi shart.

    OXIRGI BOSQICH QOLGANINI YOPADI. Ulushlar yig'indisi
    yaxlitlash tufayli 100 dan biroz farq qilsa (masalan N=3 da
    33.33 x 3 = 99.99), qoldiq oxirgi bosqichga qo'shiladi.
    Ansiz pozitsiyaning bir tiyini abadiy ochiq qolardi.
    """
    if not tplar:
        raise ValueError("Kamida bitta TP bo'lishi kerak")
    if stop >= entry:
        raise ValueError(f"Spot/long uchun Stop({stop}) < Entry({entry}) bo'lishi shart")

    oldingi = entry
    for i, narx in enumerate(tplar, start=1):
        if narx <= oldingi:
            raise ValueError(
                f"TP tartibi noto'g'ri: TP{i}({narx}) oldingi darajadan ({oldingi}) yuqori emas"
            )
        oldingi = narx

    n = len(tplar)
    if ulushlar is None:
        ulushlar = tuple(100.0 / n for _ in range(n))
    elif len(ulushlar) != n:
        raise ValueError(f"Ulushlar soni ({len(ulushlar)}) TP soniga ({n}) teng emas")

    bosqichlar = []
    yigindi = 0.0
    for k, (narx, ulush) in enumerate(zip(tplar, ulushlar, strict=True), start=1):
        oxirgimi = k == n
        haqiqiy_ulush = 100.0 - yigindi if oxirgimi else float(ulush)
        yigindi += haqiqiy_ulush
        # Stop OLDINGI TP ga ko'chadi; birinchisida — Entry ga.
        bosqichlar.append(
            Bosqich(
                raqam=k,
                narx=float(narx),
                ulush_pct=haqiqiy_ulush,
                yangi_stop=entry if k == 1 else float(tplar[k - 2]),
            )
        )

    return ChiqishRejasi(
        entry=float(entry),
        boshlangich_stop=float(stop),
        bosqichlar=tuple(bosqichlar),
    )


def holat_boshla(reja: ChiqishRejasi) -> ChiqishHolati:
    """Signal endi ochilganda — hech bir TP bajarilmagan holat."""
    return ChiqishHolati(reja=reja, joriy_stop=reja.boshlangich_stop)


def tp_bajarildi(holat: ChiqishHolati) -> ChiqishHolati:
    """Navbatdagi TP ga yetildi: ulush sotiladi, Stop ko'chadi."""
    bosqich = holat.keyingi_bosqich
    if bosqich is None:
        return holat

    qolgan = holat.ochiq_ulush_pct - bosqich.ulush_pct
    oxirgimi = bosqich.raqam >= holat.reja.tp_soni

    return replace(
        holat,
        bajarilgan=bosqich.raqam,
        joriy_stop=bosqich.yangi_stop,
        ochiq_ulush_pct=0.0 if oxirgimi else max(0.0, qolgan),
        yopilgan=oxirgimi or qolgan <= EPSILON,
        yopilish_sababi="oxirgi TP" if oxirgimi else "",
    )


def stop_urildi(holat: ChiqishHolati) -> ChiqishHolati:
    """Stop tegdi — qolgan ulush shu narxda yopiladi."""
    if holat.yopilgan:
        return holat
    sabab = (
        "stop"
        if holat.bajarilgan == 0
        else f"stop (TP{holat.bajarilgan} dan keyin)"
    )
    return replace(
        holat,
        qoldiq_ulush_pct=holat.ochiq_ulush_pct,
        ochiq_ulush_pct=0.0,
        yopilgan=True,
        yopilish_sababi=sabab,
    )


def natija_pct(holat: ChiqishHolati, yopilish_narxi: float) -> float:
    """Signalning umumiy natijasi, KIRISH narxiga nisbatan foizda.

    Har bosqich O'Z narxida hisoblanadi — pozitsiya bir yo'la
    yopilmagan. Ochiq qolgan ulush `yopilish_narxi` da sotiladi.

    Xarajat (komissiya/sirg'anish) bu yerda QO'SHILMAYDI: u
    savdo qatlamiga tegishli va PNL hisoblagichida qo'llanadi.
    """
    entry = holat.reja.entry
    if entry <= 0:
        raise ValueError("Kirish narxi musbat bo'lishi kerak")

    natija = 0.0
    for bosqich in holat.reja.bosqichlar[: holat.bajarilgan]:
        natija += (bosqich.narx - entry) / entry * 100 * bosqich.ulush_pct / 100

    # Ochiq qolgan ulush (hali yopilmagan savdo) yoki Stop bilan
    # yopilgan qoldiq — ikkalasi ham `yopilish_narxi` da sotiladi.
    qoldiq = holat.ochiq_ulush_pct + holat.qoldiq_ulush_pct
    if qoldiq > EPSILON:
        natija += (yopilish_narxi - entry) / entry * 100 * qoldiq / 100
    return natija
