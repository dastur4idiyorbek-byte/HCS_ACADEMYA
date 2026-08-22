"""3.5-band: ball chegarasini O'LCHAB tanlash.

Nima uchun kerak bo'ldi
-----------------------
Chegara `70` (yuqori salomatlik) va `80` (o'rta salomatlik) deb
qo'yilgan edi. Bu raqamlar 100 ballik shkalada mantiqiy ko'rinadi —
"signal uchun kamida 80 ball kerak" degan gap tabiiy eshitiladi.

Lekin ball funksiyasi DARAJALI: har bir omil 0..1 oralig'ida
baholanadi va vazniga ko'paytiriladi. Omillarning bir qismi esa bu
strategiyada BIR VAQTDA to'liq bo'la olmaydi:

  • Support'da xarid qilish -> MACD hali signal chizig'idan pastda
    (kesish keyinroq keladi) -> MACD 0/10.
  • Support'da xarid qilish -> RSI past bo'lishi kerak, lekin aynan
    30 dan qaytish kam uchraydi; o'rta zona yarim ball beradi.
  • R/R aynan 1:3 bo'lsa (3.3-banddagi eng kam talab) -> 50% ball.

Ya'ni 100 ball nazariy, amalda erishib bo'lmaydigan cho'qqi. Chegarani
100 ga qarab qo'yish — boshqa shkaladagi raqamni bu yerga ko'chirish.

Bu skript ball funksiyasini turli sifatdagi sozlamalarda ishga tushirib,
HAQIQIY taqsimotni ko'rsatadi. Chegara shu taqsimotdan tanlanadi.

Ishga tushirish:
    python -m scripts.kalibrlash
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from core.analysis.strategies import StrategyInput
from core.analysis.strategies.classic_ta import ClassicTaStrategy
from core.config import load_config
from core.config.schema import AppConfig
from core.domain.enums import HalalStatus
from core.domain.models import Candle, HalalVerdict

BOSH = datetime(2026, 1, 1, tzinfo=UTC)
HALOL = HalalVerdict("BTC", HalalStatus.HALAL, "halol")


@dataclass(frozen=True, slots=True)
class Sozlama:
    """Bitta sinov sozlamasi — sifat darajalari bo'yicha o'zgaradi."""

    nom: str
    oxirgi_ulush: float      # narx diapazonning qayeriga qaytdi (past = chuqurroq)
    hajm_kuchi: float        # oxirgi shamlardagi hajm o'rtachaga nisbatan
    kotarilish: float        # tsikldan tsiklga siljish (trend qiyaligi)
    tsikllar: int            # zona necha marta sinaladi


def shamlar_yasa(s: Sozlama) -> list[Candle]:
    """Sozlamaga mos sham seriyasini quradi."""
    SUPPORT, RESISTANCE = 8000.0, 8480.0
    FITIL = 0.008

    natija: list[Candle] = []
    i = 0

    def qoshish(narx: float, hajm: float) -> None:
        nonlocal i
        natija.append(
            Candle(
                open_time=BOSH + timedelta(hours=i),
                open=narx,
                high=narx * (1 + FITIL),
                low=narx * (1 - FITIL),
                close=narx,
                volume=hajm,
            )
        )
        i += 1

    for tsikl in range(s.tsikllar):
        siljish = 1 + tsikl * s.kotarilish
        for ulush in (0.05, 0.45, 0.95, 0.60, 0.20, 0.05):
            narx = (SUPPORT + (RESISTANCE - SUPPORT) * ulush) * siljish
            for _ in range(3):
                qoshish(narx, 1000.0)

    siljish = 1 + (s.tsikllar - 1) * s.kotarilish
    tayanch = (SUPPORT + (RESISTANCE - SUPPORT) * s.oxirgi_ulush) * siljish
    for j in range(6):
        qoshish(tayanch, 1000.0 * s.hajm_kuchi if j >= 4 else 1200.0)

    return natija


def kirish(config: AppConfig, candles: list[Candle]) -> StrategyInput:
    tf = {t: candles for t in config.analysis.timeframes}
    return StrategyInput(
        symbol="BTC",
        now=candles[-1].open_time,
        halal_verdict=HALOL,
        candles=tf,
        market_health=None,
    )


def sozlamalar() -> list[Sozlama]:
    """Yomondan a'logacha — amalda uchraydigan oraliq."""
    natija: list[Sozlama] = []
    for ulush, sifat in ((0.20, "chuqur"), (0.34, "o'rta"), (0.48, "sayoz")):
        for hajm, hajm_nomi in ((1.2, "past hajm"), (2.0, "yaxshi hajm"), (2.7, "kuchli hajm")):
            for kotar, trend_nomi in ((0.002, "sust trend"), (0.005, "o'rta trend"),
                                      (0.009, "kuchli trend")):
                natija.append(
                    Sozlama(
                        nom=f"{sifat} qaytish / {hajm_nomi} / {trend_nomi}",
                        oxirgi_ulush=ulush,
                        hajm_kuchi=hajm,
                        kotarilish=kotar,
                        tsikllar=12,
                    )
                )
    return natija


def main() -> None:
    config = load_config()
    strategiya = ClassicTaStrategy(config)

    ballar: list[tuple[float, str]] = []
    rad_etilgan = 0

    for s in sozlamalar():
        nomzod = strategiya.analyze(kirish(config, shamlar_yasa(s)))
        if nomzod is None:
            rad_etilgan += 1
            continue
        ballar.append((nomzod.score, s.nom))

    ballar.sort(reverse=True)

    print(f"Sinalgan sozlamalar : {len(sozlamalar())}")
    print(f"Nomzod chiqdi       : {len(ballar)}")
    print(f"Rad etildi          : {rad_etilgan}\n")

    if not ballar:
        print("Birorta nomzod chiqmadi — kalibrlash uchun ma'lumot yo'q.")
        return

    faqat_ballar = [b for b, _ in ballar]
    print(f"Eng yuqori ball     : {max(faqat_ballar):.1f}")
    print(f"Eng past ball       : {min(faqat_ballar):.1f}")
    print(f"O'rtacha            : {statistics.mean(faqat_ballar):.1f}")
    print(f"Mediana             : {statistics.median(faqat_ballar):.1f}\n")

    print("Eng yaxshi 5 sozlama:")
    for ball, nom in ballar[:5]:
        print(f"  {ball:5.1f}  {nom}")

    # Chegaralar konfiguratsiyadan olinadi — skriptga yozib qo'yilsa, u
    # sozlama o'zgargach jimgina eskirib qolardi.
    thresholds = config.scoring.thresholds
    joriy = {
        thresholds.threshold_mid_health: "joriy (o'rta salomatlik)",
        thresholds.threshold_high_health: "joriy (yuqori salomatlik)",
    }
    sinaladigan = sorted({80, 70, 60, 55, 50, 45, 40} | set(joriy), reverse=True)

    print("\nQaysi chegarada nechtasi o'tadi:")
    for chegara in sinaladigan:
        otgan = sum(1 for b in faqat_ballar if b >= chegara)
        ulush = otgan / len(faqat_ballar) * 100
        belgi = f"  <- {joriy[chegara]}" if chegara in joriy else ""
        print(f"  chegara {chegara:5.0f}: {otgan:3d} / {len(faqat_ballar)} ({ulush:4.0f}%){belgi}")


if __name__ == "__main__":
    main()
