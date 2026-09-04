"""Portfel dashboardining ETALON qiymatlari.

Nima uchun: hisob IKKI joyda ko'rinadi — `core/portfolio/` (Python,
asl) va `web/src/lib/portfel.ts` (sayt). Ikkalasi ham SHU faylga
solishtiriladi, ya'ni biror tomon o'zgarsa test darhol yiqiladi.

Bu 3-promptning "BITTA MANBA, IKKI EKRAN" talabining amaldagi
shakli: bot bilan sayt bir xil raqamni ko'rsatishini IZOH emas,
TEST ushlab turadi.

Yangilash (faqat hisob ATAYLAB o'zgartirilganda):
    python -m scripts.portfel_fixtures
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.portfolio.capital_allocator import Bolak
from core.portfolio.pnl_calculator import OchiqPozitsiya, YopilganQism, xulosa_qur
from core.portfolio.pnl_dashboard import dashboard_qur

FAYL = Path(__file__).resolve().parent.parent / "tests" / "portfel_fixtures.json"

#: Etalon "hozir" — kalendar kun chegarasi barqaror bo'lishi uchun qat'iy.
HOZIR = datetime(2026, 9, 4, 15, 0, tzinfo=UTC)


def _qism(kun_oldin: float, natija: float, signal_id: int) -> YopilganQism:
    return YopilganQism(
        signal_id=signal_id,
        symbol="SINOV",
        yopilgan_vaqt=HOZIR - timedelta(days=kun_oldin),
        miqdor_usd=100.0,
        natija_usd=natija,
    )


#: Har bir holat: nom, balans, yopilgan qismlar, ochiq pozitsiyalar, bo'laklar
HOLATLAR = [
    ("bosh", 1000.0, [], [], [Bolak(1, 333.33), Bolak(2, 333.33), Bolak(3, 333.33)]),
    (
        "bitta_foydali_savdo",
        1000.0,
        [_qism(0.2, 45.0, 1)],
        [],
        [Bolak(1, 333.33), Bolak(2, 333.33), Bolak(3, 333.33)],
    ),
    (
        "davrlar_ichma_ich",
        1000.0,
        [_qism(0.1, 10.0, 1), _qism(3, 20.0, 2), _qism(20, -30.0, 3), _qism(200, 40.0, 4)],
        [],
        [Bolak(1, 333.33), Bolak(2, 333.33), Bolak(3, 333.33)],
    ),
    (
        "ochiq_va_band_bolak",
        900.0,
        [_qism(1, 15.0, 1)],
        [OchiqPozitsiya(2, "SINOV", 100.0, 300.0, joriy_narx=112.0)],
        [Bolak(1, 300.0, 300.0, 30.0), Bolak(2, 300.0), Bolak(3, 300.0)],
    ),
    (
        "narxi_olinmagan_ochiq",
        900.0,
        [],
        [
            OchiqPozitsiya(3, "SINOV", 100.0, 300.0, joriy_narx=105.0),
            OchiqPozitsiya(4, "SINOV2", 50.0, 150.0),
        ],
        [Bolak(1, 300.0, 300.0, 30.0), Bolak(2, 300.0, 150.0, 15.0), Bolak(3, 300.0)],
    ),
    (
        "bitta_signal_ikki_qism",
        1000.0,
        [_qism(1, 10.0, 7), _qism(1, 15.0, 7)],
        [],
        [Bolak(1, 500.0), Bolak(2, 500.0)],
    ),
]


def hisobla() -> list[dict]:
    natijalar = []
    for nom, balans, qismlar, ochiqlar, bolaklar in HOLATLAR:
        xulosa = xulosa_qur(qismlar, ochiqlar, balans_usd=balans, hozir=HOZIR)
        d = dashboard_qur(xulosa, bolaklar)
        natijalar.append(
            {
                "nom": nom,
                "balans": balans,
                "hozir": HOZIR.isoformat(),
                "qismlar": [
                    {
                        "signalId": q.signal_id,
                        "yopilganVaqt": q.yopilgan_vaqt.isoformat(),
                        "natijaUsd": q.natija_usd,
                    }
                    for q in qismlar
                ],
                "ochiqlar": [
                    {
                        "signalId": p.signal_id,
                        "entry": p.entry,
                        "ochiqMiqdorUsd": p.ochiq_miqdor_usd,
                        "joriyNarx": p.joriy_narx,
                    }
                    for p in ochiqlar
                ],
                "bolaklar": [
                    {
                        "raqam": b.raqam,
                        "hajm": b.hajm,
                        "bandKapital": b.band_kapital,
                        "bandXavf": b.band_xavf,
                    }
                    for b in bolaklar
                ],
                "kutilgan": {
                    "qatorlar": [
                        {"nom": q.nom, "usd": round(q.usd, 10), "pct": round(q.pct, 10)}
                        for q in d.qatorlar
                    ],
                    "unrealizedUsd": round(d.unrealized_usd, 10),
                    "ochiqSoni": d.ochiq_soni,
                    "baholanmaganSoni": d.baholanmagan_soni,
                    "bandBolaklar": list(d.band_bolaklar),
                    "boshBolaklar": list(d.bosh_bolaklar),
                    "xavfPct": round(d.xavf_pct, 10),
                    "bosh": d.bosh,
                },
            }
        )
    return natijalar


if __name__ == "__main__":
    FAYL.write_text(json.dumps(hisobla(), indent=2) + "\n", encoding="utf-8")
