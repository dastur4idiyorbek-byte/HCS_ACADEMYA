"""3.1 — Fibonacci korreksiya zonasi.

Oxirgi IMPULS harakat (swing past -> swing yuqori) topiladi va uning
38.2% / 50% / 61.8% qaytish darajalari hisoblanadi. Narx shu oraliqda
bo'lsa — ✅.

ORALIQ, BITTA CHIZIQ EMAS. "Narx aynan 61.8% da" degan shart amalda
deyarli bajarilmaydi. Zona sifatida 38.2%..61.8% oralig'i olinadi —
bu SMC amaliyotidagi "discount zone" tushunchasi bilan bir xil.

NIMA UCHUN 78.6% EMAS: chuqurroq qaytish ham Fibonacci darajasi,
lekin u impulsning bekor bo'lganini bildiradi. 61.8% dan pastda
struktura ko'pincha buziladi — bu ehtiyotkorlik emas, kuzatuv.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.structure.swing_detector import Swing, SwingTuri

#: Zona chegaralari — impuls uzunligining ulushi
FIB_YUQORI = 0.382
FIB_PAST = 0.618


@dataclass(frozen=True, slots=True)
class Zona:
    """Narx oralig'i. Barcha zona turlari shu tipda qaytadi."""

    past: float
    yuqori: float
    manba: str

    def ichida(self, narx: float) -> bool:
        return self.past <= narx <= self.yuqori

    def kesishadimi(self, boshqa: Zona) -> bool:
        """Ikki zona ustma-ust tushadimi — darajali birlashtirish uchun."""
        return self.past <= boshqa.yuqori and boshqa.past <= self.yuqori

    @property
    def markaz(self) -> float:
        return (self.past + self.yuqori) / 2


def fib_zona(nuqtalar: list[Swing]) -> Zona | None:
    """Oxirgi ko'tarilish impulsining Fibonacci qaytish zonasi.

    IMPULS = oxirgi swing PAST dan undan KEYINGI swing YUQORIgacha.
    Tartib muhim: yuqori pastdan keyin kelishi kerak, aks holda bu
    ko'tarilish impulsi emas, tushish.
    """
    past = oxirgi_impuls(nuqtalar)
    if past is None:
        return None
    boshi, oxiri = past

    uzunlik = oxiri.narx - boshi.narx
    if uzunlik <= 0:
        return None

    return Zona(
        past=oxiri.narx - uzunlik * FIB_PAST,
        yuqori=oxiri.narx - uzunlik * FIB_YUQORI,
        manba="fibonacci",
    )


def oxirgi_impuls(nuqtalar: list[Swing]) -> tuple[Swing, Swing] | None:
    """Oxirgi ko'tarilish impulsi: (boshlanish pasti, tugash yuqorisi).

    OCHIQ — kuzatuv paneli ham chaqiradi. U "narx shu impulsning
    qayerida?" degan savolga javob berish uchun kerak: impuls
    tepasida turgan coin allaqachon YURGAN, pastida turgani esa
    hali yurmagan.
    """
    yuqori = None
    for s in reversed(nuqtalar):
        if s.turi is SwingTuri.YUQORI:
            yuqori = s
            break
    if yuqori is None:
        return None

    for s in reversed(nuqtalar):
        if s.turi is SwingTuri.PAST and s.indeks < yuqori.indeks:
            return s, yuqori
    return None
