"""Qo'sh tub (Double Bottom) — 2B va 3A alternativlari uchun umumiy.

Qo'sh tub — ko'tarilish (long) uchun: ikkita swing PAST bir-biriga
yaqin narxda, orasida balandroq cho'qqi (bo'yin). Narx bo'yinni
yuqoriga yorib o'tsa — naqsh tasdiqlanadi.

Qo'sh CHO'QQI (Double Top) YOZILMAYDI — loyiha spot, long-only
(`docs/ARXITEKTURA.md`). Teskari mantiq yozilsa, u hech qachon
chaqirilmaydigan o'lik tarmoq bo'lardi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.structure.swing_detector import Swing, SwingTuri

#: Ikki tub bir-biridan shu foizdan uzoq bo'lmasa — "bir xil daraja".
#: 🔴 O'LCHANMAGAN.
QOSH_TUB_MOSLIK_PCT = 3.0


@dataclass(frozen=True, slots=True)
class QoshTub:
    """Ikki tub va ular orasidagi bo'yin."""

    birinchi: Swing
    ikkinchi: Swing
    boyin: Swing
    tub_narx: float

    @property
    def boyin_narx(self) -> float:
        return self.boyin.narx


def qosh_tub_topish(
    nuqtalar: list[Swing],
    moslik_pct: float = QOSH_TUB_MOSLIK_PCT,
) -> QoshTub | None:
    """Oxirgi ikki swing PAST va ular orasidagi bo'yinni topadi.

    Ikki tub "bir xil daraja" bo'lishi shart — aks holda bu qo'sh
    tub emas, oddiy tushayotgan ketma-ketlik. Shuning uchun ikki
    tubning farqi `moslik_pct` dan kichik bo'lishi tekshiriladi.
    """
    pastlar = [s for s in nuqtalar if s.turi is SwingTuri.PAST]
    if len(pastlar) < 2:
        return None

    birinchi, ikkinchi = pastlar[-2], pastlar[-1]
    if ikkinchi.indeks <= birinchi.indeks:
        return None

    tub_narx = min(birinchi.narx, ikkinchi.narx)
    baland_narx = max(birinchi.narx, ikkinchi.narx)
    if tub_narx <= 0:
        return None
    farq_pct = (baland_narx - tub_narx) / tub_narx * 100
    if farq_pct > moslik_pct:
        return None

    boyin: Swing | None = None
    for s in nuqtalar:
        if birinchi.indeks < s.indeks < ikkinchi.indeks and s.turi is SwingTuri.YUQORI:
            if boyin is None or s.narx > boyin.narx:
                boyin = s
    if boyin is None:
        return None

    return QoshTub(birinchi=birinchi, ikkinchi=ikkinchi, boyin=boyin, tub_narx=tub_narx)
