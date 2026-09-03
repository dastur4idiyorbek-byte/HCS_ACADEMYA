"""1.4 — Kayfiyat/sektor: Fear & Greed + Sektor rotatsiyasi + Yangiliklar.

QOIDA (2-prompt): kamida 2/3 mos bo'lsa — ✅.

MANBA HOLATI: uchtasidan faqat Fear & Greed'ning to'liq tarixi bepul
(alternative.me, 2018-dan). Sektor va yangiliklar backtestda yo'q.

"2/3" QOIDASI MAVJUDLARIGA MOSLASHADI — `market_regime.py` dagi bilan
bir xil sabab: aks holda faqat F&G bor holatda shart hech qachon
bajarilmasdi.

FEAR & GREED YO'NALISHI — TESKARI. Bu ataylab shunday:
qo'rquv (past qiymat) = arzon narx = XARID imkoni. Ochko'zlik
(yuqori qiymat) = bozor to'lgan = xarid uchun yomon payt. Buni
"greed = ijobiy" deb o'qish — cho'qqida sotib olish demak.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.turlar import Tekshiruv, ha, malumot_yoq, yoq

#: Fear & Greed shundan PAST bo'lsa — xaridga qulay (qo'rquv).
#: 🔴 O'LCHANMAGAN. 55 — "neytraldan biroz yuqori" chegarasi:
#: 50 dan past qattiq, 75 dan past juda yumshoq bo'lardi.
FNG_YUQORI_CHEGARA = 55


@dataclass(frozen=True, slots=True)
class Kayfiyat:
    """1.4 uchun xom ma'lumot."""

    #: Fear & Greed indeksi, 0..100
    fear_greed: int | None = None
    #: Coin sektori so'nggi 7 kunda bozordan kuchliroqmi
    sektor_kuchli: bool | None = None
    #: Yangiliklar oqimi ijobiymi (CryptoPanic, institutsional xaridlar)
    yangilik_ijobiy: bool | None = None


def kayfiyat(malumot: Kayfiyat) -> Tekshiruv:
    ovozlar: list[bool] = []
    sabablar: list[str] = []

    if malumot.fear_greed is not None:
        mos = malumot.fear_greed < FNG_YUQORI_CHEGARA
        ovozlar.append(mos)
        sabablar.append(f"F&G {malumot.fear_greed}")

    if malumot.sektor_kuchli is not None:
        ovozlar.append(bool(malumot.sektor_kuchli))
        sabablar.append("sektor kuchli" if malumot.sektor_kuchli else "sektor zaif")

    if malumot.yangilik_ijobiy is not None:
        ovozlar.append(bool(malumot.yangilik_ijobiy))
        sabablar.append("yangilik ijobiy" if malumot.yangilik_ijobiy else "yangilik salbiy")

    if not ovozlar:
        return malumot_yoq("kayfiyat", "F&G/sektor/yangilik — hech biri yo'q")

    kerak = len(ovozlar) if len(ovozlar) <= 2 else 2
    mos_soni = sum(ovozlar)
    izoh = f"{mos_soni}/{len(ovozlar)} mos ({', '.join(sabablar)})"
    return ha("kayfiyat", izoh) if mos_soni >= kerak else yoq("kayfiyat", izoh)
