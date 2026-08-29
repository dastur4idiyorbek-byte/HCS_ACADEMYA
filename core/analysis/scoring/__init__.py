"""3.5-band: ball (score) va reyting tizimi.

Vaznlar `config/default.yaml` -> `scoring.weights` da (jami 100):
  S/R zonasi sifati 25 | Trend 20 | RSI 15 | Hajm 15 | MACD 10 | R/R 15

S/R eng yuqori vaznga ega — 3.1-bandga mos. Aniq raqamlar backtest
jarayonida moslashtiriladi, lekin STRUKTURA (S/R birinchi) o'zgarmaydi.

Har bir omil DARAJALI (graduated) baholanadi, "bor/yo'q" emas.

Minimal ball chegarasi statik EMAS — `RiskEngine.score_threshold()` orqali
Bozor Salomatligi Indeksiga qarab moslashadi.

    levels.py   — Stop/TP darajalarini S/R va ATR asosida qurish
    factors.py  — bazaviy omillarni darajali baholash (jami 100)
    bonuses.py  — CryptoSpot3% omillari, bazaviy ball USTIGA (jami 25)
    scorer.py   — yig'ish, saralash, chegara qo'llash

Chegara BAZAVIY 100 ballik shkalada o'lchanadi: bonuslar faqat
nomzodni yuqoriga suradi, hech qachon pastga tortmaydi.
"""

from core.analysis.scoring.bonuses import build_bonus_components, in_session_overlap
from core.analysis.scoring.factors import build_components
from core.analysis.scoring.levels import LevelResult, build_levels
from core.analysis.scoring.scorer import (
    RankedCandidate,
    Scorer,
    breakdown_from_json,
    breakdown_to_json,
    breakdown_to_text,
)

__all__ = [
    "LevelResult",
    "RankedCandidate",
    "Scorer",
    "breakdown_from_json",
    "breakdown_to_json",
    "breakdown_to_text",
    "build_bonus_components",
    "build_components",
    "build_levels",
    "in_session_overlap",
]
