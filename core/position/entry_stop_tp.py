"""5-qism — Entry / Stop / TP struktura asosida.

    ENTRY  = Zona Sifati bloki topgan zona ichida
    STOP   = zonaning TASHQI cheti (qat'iy % emas)
    TP1..3 = qarshi struktura nuqtalari (swing yuqorilar)

XAVFSIZLIK CHEGARALARI (promptda ~3% va ~12-15%): bular Stop ni
BELGILAMAYDI, faqat rad etadi. Zona chetidagi Stop 20% uzoqda
bo'lsa — bu zonaning o'zi noto'g'ri, signal berilmaydi.

TP1/STOP NISBATI: minimal ~1:1.2. Eski tizimda bu nisbat 1:1.5 edi
va u YAGONA ishlagan narsa bo'lib chiqdi (PF 0.30 -> 0.84,
`OLCHOVLAR_XULOSASI.md` #8). Shuning uchun poli SAQLANADI, lekin
aniq qiymati backtest bilan qayta topiladi — eski raqamni ko'chirib
yozish "o'lchandi" degani emas.

TP SONI MOSLASHUVCHAN: 1, 2 yoki 3 — struktura nechta nuqta
bersa. Loyiha egasining sharti: "2 TP MAJBURIY EMAS".
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.structure.swing_detector import Swing, SwingTuri
from core.analysis.zone_quality.fibonacci import Zona

#: Stop shu foizdan yaqin bo'lsa — shovqin ichida, rad etiladi.
#: 🔴 O'LCHANMAGAN. Promptda ~3%.
STOP_ENG_KAM_PCT = 3.0

#: Stop shu foizdan uzoq bo'lsa — zona noto'g'ri, rad etiladi.
#: 🔴 O'LCHANMAGAN. Promptda ~12-15%.
STOP_ENG_KOP_PCT = 15.0

#: TP1/Stop nisbatining minimal qiymati.
#: 🔴 O'LCHANMAGAN. Promptda ~1:1.2.
TP1_ENG_KAM_NISBAT = 1.2

#: Ko'pi bilan shuncha TP quriladi.
TP_ENG_KOP = 3


@dataclass(frozen=True, slots=True)
class Darajalar:
    entry: float
    stop: float
    tplar: tuple[float, ...]
    #: Rad etilgan bo'lsa — sabab. `None` bo'lsa daraja yaroqli.
    rad_sababi: str | None = None

    @property
    def yaroqli(self) -> bool:
        return self.rad_sababi is None

    @property
    def xavf(self) -> float:
        """R birligi — kirish va stop orasidagi masofa."""
        return self.entry - self.stop


def darajalar_qur(
    zona: Zona,
    nuqtalar: list[Swing],
    joriy_narx: float,
    *,
    eng_kam_stop_pct: float = STOP_ENG_KAM_PCT,
    eng_kop_stop_pct: float = STOP_ENG_KOP_PCT,
    eng_kam_nisbat: float = TP1_ENG_KAM_NISBAT,
) -> Darajalar:
    """Zona va struktura nuqtalaridan darajalarni quradi.

    ENTRY TANLOVI. Zona ichida narx qayerda bo'lsa — o'sha. Narx
    zonadan yuqorida bo'lsa, entry zonaning YUQORI cheti bo'ladi
    (LIMIT buyurtma o'sha yerda kutadi). Zonadan pastda bo'lsa —
    zona buzilgan, rad etiladi.

    Nima uchun "entry = joriy narx" QILINMAYDI: eski tizimda aynan
    shunday edi va oqibati — LIMIT tarmog'i va zona yaxlitligi
    qoidasi butunlay o'lik qoldi (`GIPOTEZA_DAFTARI.md`, audit
    3-bosqichi).
    """
    if joriy_narx < zona.past:
        return _rad(zona, "narx zonadan pastga tushgan — zona buzilgan")

    entry = joriy_narx if zona.ichida(joriy_narx) else zona.yuqori
    stop = zona.past

    if stop >= entry:
        return _rad(zona, "stop kirish narxidan yuqori")

    stop_pct = (entry - stop) / entry * 100
    if stop_pct < eng_kam_stop_pct:
        return _rad(zona, f"stop juda yaqin ({stop_pct:.2f}%)")
    if stop_pct > eng_kop_stop_pct:
        return _rad(zona, f"stop juda uzoq ({stop_pct:.2f}%)")

    tplar = _tp_nuqtalari(nuqtalar, entry)
    if not tplar:
        return _rad(zona, "qarshi struktura nuqtasi topilmadi")

    nisbat = (tplar[0] - entry) / (entry - stop)
    if nisbat < eng_kam_nisbat:
        return _rad(zona, f"TP1/Stop nisbati past ({nisbat:.2f})")

    return Darajalar(entry=entry, stop=stop, tplar=tuple(tplar))


def _tp_nuqtalari(nuqtalar: list[Swing], entry: float) -> list[float]:
    """Entry'dan YUQORIDAGI swing yuqorilar, yaqinidan uzog'iga.

    Takrorlanuvchi darajalar tashlanadi: bir xil narxdagi ikkita
    swing bitta qarshilik, ikkita TP emas.
    """
    yuqorilar = sorted(
        {s.narx for s in nuqtalar if s.turi is SwingTuri.YUQORI and s.narx > entry}
    )
    return yuqorilar[:TP_ENG_KOP]


def _rad(zona: Zona, sabab: str) -> Darajalar:
    return Darajalar(entry=zona.markaz, stop=zona.past, tplar=(), rad_sababi=sabab)
