"""2.2 va 2.3 — Break of Structure va Change of Character.

TA'RIFLAR (SMC amaliyoti, loyihaning eski moduli bilan bir xil):

    BOS   — narx OXIRGI swing yuqorini YOPILISH bilan kesib o'tdi.
            Ko'tarilish davom etmoqda.
    CHOCH — narx OXIRGI swing pastni YOPILISH bilan kesib o'tdi.
            Ko'tarilish tugadi, xarakter o'zgardi.

YOPILISH BILAN, WICK BILAN EMAS. Bu — ataylab. Wick bilan kesish
har uchinchi shamda "BOS" beradi va struktura ma'nosini yo'qotadi.
Yopilish esa "bozor bu darajani QABUL QILDI" degani.

TARTIB MUHIM: BOS yoki CHOCH — qaysi biri KEYIN sodir bo'lgan, o'sha
hozirgi holatni belgilaydi. Ikkalasini mustaqil "bor/yo'q" deb
o'qish xato bo'lardi: eski BOS'dan keyin CHOCH kelgan bo'lsa,
struktura endi ko'tarilish emas.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.domain.models import Candle


@dataclass(frozen=True, slots=True)
class BosChoch:
    """Struktura buzilishlarining hozirgi holati."""

    #: Oxirgi BOS bo'lgan sham indeksi (`None` — umuman bo'lmagan)
    bos_indeks: int | None = None
    #: Oxirgi CHOCH bo'lgan sham indeksi
    choch_indeks: int | None = None
    bos_narx: float | None = None
    choch_narx: float | None = None

    @property
    def bos_tasdiqlangan(self) -> bool:
        """BOS bor VA undan keyin CHOCH kelmagan."""
        if self.bos_indeks is None:
            return False
        return self.choch_indeks is None or self.choch_indeks < self.bos_indeks

    @property
    def qarshi_choch_yoq(self) -> bool | None:
        """Hozirgi yo'nalishga qarshi CHOCH paydo bo'lmaganmi.

        UCH HOLAT, IKKITA EMAS:

            None  — yo'nalish umuman aniqlanmagan (na BOS, na CHOCH).
                    "Qarshi CHOCH yo'q" degan gap MA'NOSIZ: nimaga
                    qarshi? Bu holat O'LCHANMAGAN deb belgilanadi.
            True  — yo'nalish bor va u buzilmagan
            False — CHOCH oxirgi BOS'dan KEYIN kelgan, struktura
                    endi ishonchsiz

        NIMA UCHUN `None` MUHIM. Ilgari bu yerda `True` qaytardi va
        oqibati: YASSI, o'lik grafik ham "qarshi CHOCH yo'q ✅"
        olardi va struktura bloki 1/3 bilan o'tardi. Ya'ni hech
        narsa bo'lmagani "yaxshi xabar" deb o'qilardi. Bu — eski
        tizimning eng qimmat xatosi turi (`OLCHOVLAR_XULOSASI.md`
        #13: hech nima qilmayotgan omillar ball berardi).
        """
        if self.bos_indeks is None and self.choch_indeks is None:
            return None
        if self.choch_indeks is None:
            return True
        return self.bos_indeks is not None and self.bos_indeks > self.choch_indeks


def bos_choch_topish(shamlar: list[Candle], nuqtalar: list[Swing]) -> BosChoch:
    """Swing nuqtalardan keyin kelgan shamlarda kesishni qidiradi.

    Har bir swing uchun undan KEYINGI shamlar tekshiriladi. Swingning
    o'z shami va undan oldingilar qaralmaydi — aks holda o'tmishga
    qarab "kesib o'tgan" deb topilardi (lookahead teskarisi, lekin
    xato baribir).
    """
    natija = BosChoch()

    for swing in nuqtalar:
        # Fraktal o'ngdan 2 sham bilan TASDIQLANADI, ya'ni swing
        # faqat `indeks + qanot` dan keyin ma'lum bo'ladi. Kesishni
        # o'sha paytdan qidiramiz.
        boshlanish = swing.indeks + 1
        for i in range(boshlanish, len(shamlar)):
            sham = shamlar[i]
            if swing.turi is SwingTuri.YUQORI and sham.close > swing.narx:
                natija = _yangila(natija, bos=(i, swing.narx))
                break
            if swing.turi is SwingTuri.PAST and sham.close < swing.narx:
                natija = _yangila(natija, choch=(i, swing.narx))
                break

    return natija


def _yangila(
    joriy: BosChoch,
    bos: tuple[int, float] | None = None,
    choch: tuple[int, float] | None = None,
) -> BosChoch:
    """Eng SO'NGGI hodisani saqlaydi — oldingisi ustiga yozadi."""
    if bos is not None and (joriy.bos_indeks is None or bos[0] > joriy.bos_indeks):
        return BosChoch(
            bos_indeks=bos[0],
            bos_narx=bos[1],
            choch_indeks=joriy.choch_indeks,
            choch_narx=joriy.choch_narx,
        )
    if choch is not None and (joriy.choch_indeks is None or choch[0] > joriy.choch_indeks):
        return BosChoch(
            bos_indeks=joriy.bos_indeks,
            bos_narx=joriy.bos_narx,
            choch_indeks=choch[0],
            choch_narx=choch[1],
        )
    return joriy
