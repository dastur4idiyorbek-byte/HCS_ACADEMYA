"""4.2 — Pastki TF tasdig'i: 15/30min da mini-BOS yoki mini-sweep.

YANGI KOD YO'Q (2-prompt talabi). Bu modul yuqori TF uchun yozilgan
AYNAN SHU funksiyalarni kichikroq timeframe bilan qayta chaqiradi:

    swinglar()        — 5 shamli fraktal, o'sha ta'rif
    bos_choch_topish() — o'sha kesish qoidasi
    sweep_bormi()      — o'sha yalash qoidasi

NIMA UCHUN NUSXA YOZILMAYDI: agar pastki TF uchun alohida
"mini_swing()" yozilsa, ikkalasi vaqt o'tib ajralib ketardi —
masalan biri wick bilan, ikkinchisi close bilan kesishni
hisoblardi. Bu loyihada aynan shunday xato bo'lgan (eski modulda
darajalar ikki joyda qurilardi).

ZONA CHEGARASI: pastki TF shamlarining faqat ZONA ICHIDAGI qismi
qaraladi. Aks holda tasdiq zonadan uzoqda topilib, kirish narxi
butunlay boshqa joyda bo'lardi.
"""

from __future__ import annotations

from core.analysis.confirmation.liquidity_sweep import sweep_bormi
from core.analysis.structure.bos_choch import bos_choch_topish
from core.analysis.structure.swing_detector import swinglar
from core.analysis.zone_quality.fibonacci import Zona
from core.domain.models import Candle


def pastki_tf_tasdigi(pastki_shamlar: list[Candle], zona: Zona | None) -> bool:
    """Zona ichida mini-BOS yoki mini-sweep bormi.

    Args:
        pastki_shamlar: 15m yoki 30m shamlar
        zona: yuqori TF dan kelgan zona. `None` bo'lsa tasdiq yo'q.
    """
    if zona is None or not pastki_shamlar:
        return False

    ichkilar = _zona_ichidagilar(pastki_shamlar, zona)
    if len(ichkilar) < 5:
        # 5 shamli fraktal uchun minimum. Kamida shuncha bo'lmasa
        # swing umuman topilmaydi va tasdiq har doim "yo'q" chiqardi.
        return False

    nuqtalar = swinglar(ichkilar)
    if not nuqtalar:
        return False

    holat = bos_choch_topish(ichkilar, nuqtalar)
    return holat.bos_tasdiqlangan or sweep_bormi(ichkilar, nuqtalar)


def _zona_ichidagilar(shamlar: list[Candle], zona: Zona) -> list[Candle]:
    """Narxi zonaga TEGGAN shamlar (to'liq ichida bo'lishi shart emas).

    Sham diapazoni zona bilan kesishsa yetarli: 15 daqiqalik sham
    zonadan kengroq bo'lishi mumkin va "to'liq ichida" sharti uni
    rad etardi.
    """
    return [s for s in shamlar if s.low <= zona.yuqori and s.high >= zona.past]
