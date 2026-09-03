"""5-qism, chiqish rejasi — masshtablab sotish, trailing, vaqt chegarasi.

REJA (2-prompt):

    TP1 da   50% sotiladi, Stop KIRISH NARXIGA (breakeven) ko'chadi
    TP2 da   30% sotiladi
    qolgan 20%  TRAILING STOP bilan
    1-2 hafta   TP dan keyin rivoj yo'q -> joriy narxda yopiladi
    3-4 hafta   na Stop, na TP1 -> joriy narxda yopiladi

TRAILING HAQIDA OGOHLANTIRISH — O'LCHANGAN DALIL BOR. Eski tizimda
surilgan Stop sinaldi va natijani BUZDI: PF 0.84 -> 0.36 (1R/1R),
0.15 (1R/0.5R), 0.72 (2R/1R). Sabab: 4 soatlik shovqin Stopga tegib,
savdolar TP ga yetmasdan yopilardi (`GIPOTEZA_DAFTARI.md`, 9-to'plam).

SHU SABABDAN BU YERDA TRAILING BOSHQACHA:

    1. U faqat TP2 dan KEYINGI 20% ga tegadi — ya'ni savdo
       allaqachon foydali, xavf yo'q
    2. Timeframe 4 soatlik emas, KUNLIK — shovqin ancha kam
    3. Standart holatda O'CHIQ, backtest yoqishga ruxsat bersagina
       yoqiladi

Eski o'lchov "trailing yomon" demaydi — u "TP1 dan OLDIN trailing
yomon" deydi. Farqi shu, va u backtest bilan tekshiriladi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

#: Har TP da qancha ulush sotiladi (foizda). Yig'indisi 100 dan kam —
#: qolgani trailing yoki vaqt chegarasi bilan yopiladi.
ULUSHLAR = (50.0, 30.0)

#: TP1 dan keyin Stop kirish narxiga ko'chadimi.
TP1_BREAKEVEN = True

#: Trailing standart holatda O'CHIQ — yuqoridagi izohga qarang.
TRAILING_YOQILGAN = False

#: Trailing Stop cho'qqidan shuncha R pastda ergashadi.
#: 🔴 O'LCHANMAGAN.
TRAILING_R = 1.0

#: TP dan keyin qolgan ulush shuncha kun rivojsiz tursa — yopiladi.
#: 🔴 O'LCHANMAGAN. Promptda 1-2 hafta.
QOLDIQ_MUDDAT_KUN = 14

#: Umumiy muddat: na Stop, na TP1.
#: 🔴 O'LCHANMAGAN. Promptda 3-4 hafta.
UMUMIY_MUDDAT_KUN = 28


@dataclass(frozen=True, slots=True)
class ChiqishRejasi:
    """Signal bilan birga yuboriladigan chiqish qoidalari."""

    ulushlar: tuple[float, ...] = ULUSHLAR
    tp1_breakeven: bool = TP1_BREAKEVEN
    trailing_yoqilgan: bool = TRAILING_YOQILGAN
    trailing_r: float = TRAILING_R
    qoldiq_muddat: timedelta = field(
        default_factory=lambda: timedelta(days=QOLDIQ_MUDDAT_KUN)
    )
    umumiy_muddat: timedelta = field(
        default_factory=lambda: timedelta(days=UMUMIY_MUDDAT_KUN)
    )

    def ulush(self, tp_indeksi: int, tp_soni: int) -> float:
        """`tp_indeksi` chi TP da necha foiz sotiladi.

        TP soni MOSLASHUVCHAN (1, 2 yoki 3), shuning uchun ulushlar
        ham moslashadi:

            1 TP  -> 100%
            2 TP  -> 50 / 50   (ikkinchisi qoldiqni ham oladi)
            3 TP  -> 50 / 30 / 20

        Loyiha egasining sharti: "2 TP MAJBURIY EMAS — signallar
        1 TP, 2 TP, 3 TP bo'lishi mumkin, sharoitga qarab".
        """
        if tp_soni <= 1:
            return 100.0
        if tp_indeksi < len(self.ulushlar):
            berilgan = self.ulushlar[tp_indeksi]
            oxirgimi = tp_indeksi == tp_soni - 1
            return 100.0 - sum(self.ulushlar[:tp_indeksi]) if oxirgimi else berilgan
        return 100.0 - sum(self.ulushlar)


def chiqish_rejasi(
    *,
    trailing_yoqilgan: bool = TRAILING_YOQILGAN,
    trailing_r: float = TRAILING_R,
) -> ChiqishRejasi:
    """Standart reja. Sozlamalar backtest variantlaridan keladi."""
    return ChiqishRejasi(trailing_yoqilgan=trailing_yoqilgan, trailing_r=trailing_r)


def trailing_stop(
    entry: float,
    dastlabki_stop: float,
    choqqi: float,
    reja: ChiqishRejasi,
) -> float | None:
    """Cho'qqiga qarab surilgan Stop. `None` — hali surilmaydi.

    R BIRLIGIDA hisoblanadi, foizda emas: 100$ lik va 0.001$ lik
    coinda bir xil ishlashi uchun.
    """
    if not reja.trailing_yoqilgan:
        return None
    xavf = entry - dastlabki_stop
    if xavf <= 0:
        return None
    yangi = choqqi - xavf * reja.trailing_r
    # Stop faqat YUQORIGA suriladi — bu qat'iy qoida, buzilsa
    # xavf jimgina oshib ketardi.
    return yangi if yangi > dastlabki_stop else None
