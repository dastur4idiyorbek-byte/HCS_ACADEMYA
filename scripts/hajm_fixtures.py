"""Pozitsiya hajmi tavsiyalarining ETALON qiymatlari.

Nima uchun: hisob IKKI joyda bor — `core/position_sizing/` (Python,
asl) va `web/src/lib/hajm.ts` (sayt). Ikkalasi ham SHU faylga
solishtiriladi, ya'ni biror tomon o'zgarsa test darhol yiqiladi.

Yangilash (faqat hisob ATAYLAB o'zgartirilganda):
    python -m scripts.hajm_fixtures
"""

from __future__ import annotations

import json
from pathlib import Path

from core.config.loader import load_config
from core.domain.models import SignalLevels
from core.position_sizing import PositionSizer

FAYL = Path(__file__).resolve().parent.parent / "tests" / "hajm_fixtures.json"

#: (balans, kirish, stop) — turli pog'ona va Stop masofalari
HOLATLAR = [
    (500.0, 100.0, 97.0),
    (1000.0, 100.0, 99.0),
    (1000.0, 0.869, 0.8294),
    (5000.0, 61250.5, 59800.0),
    (10000.0, 100.0, 95.0),
    (50000.0, 100.0, 99.5),
    (100.0, 2.5, 2.4),
]


def hisobla() -> list[dict]:
    config = load_config()
    sizer = PositionSizer(config.position_sizing)
    natijalar = []
    for balans, entry, stop in HOLATLAR:
        taklif = sizer.suggest(
            "SINOV",
            SignalLevels(entry=entry, stop=stop, tp1=entry * 1.05, tp2=entry * 1.1),
            sizer.budget_for(balans),
            commit=False,
        )
        natijalar.append(
            {
                "balans": balans,
                "entry": entry,
                "stop": stop,
                "kunlikXavfFoiz": round(taklif.daily_risk_pct, 10),
                "kunlikByudjet": round(taklif.daily_budget_usd, 10),
                "hajm": round(taklif.position_size_usd, 10),
                "xavf": round(taklif.risk_amount_usd, 10),
            }
        )
    return natijalar


if __name__ == "__main__":
    FAYL.write_text(json.dumps(hisobla(), indent=2) + "\n", encoding="utf-8")
    print(f"Yozildi: {FAYL}")
