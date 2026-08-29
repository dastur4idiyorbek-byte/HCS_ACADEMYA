"""ICT Kill Zone — yagona qolgan bonus omili.

NIMA UCHUN FAQAT BITTASI QOLDI. Boshida CryptoSpot3% ning uchala
dalili ham (struktura, sweep, sessiya) bonus edi — ya'ni mavjud
omillar YONIDA turardi. Bu ikki muammo tug'dirardi:

  1. Bitta narsa ikki joyda o'lchanardi: "yalab o'tib qaytilgan
     Quasimodo zonasi" — bu boshqa bir omil emas, bu SIFATLIROQ S/R
     zonasi. Ular ajratilganda ikkalasi ham yarim kuch bilan ishlardi.
  2. Bonus chegaraga ta'sir qilmagani uchun yangi modul signal SONINI
     o'zgartira olmasdi — u faqat mavjud nomzodlarni qayta tartiblardi.

Endi struktura, daraja turi va sweep MAVJUD OMILLAR ICHIGA qo'shiladi
(`factors.py`, `_uplift`). Ular S/R va trend haqidagi dalil, alohida
omil emas.

Sessiya oynasi esa boshqacha: u tuzilma haqida emas, kirish VAQTI
haqida — ya'ni na S/R ga, na trendga tegishli. Shuning uchun u bonus
bo'lib qoladi. Kripto 24/7 ishlagani uchun bu QAT'IY FILTR EMAS:
boshqa soatlarda ham sifatli signal chiqadi, shunchaki bu oynada
hajm va likvidlik yuqoriroq.
"""

from __future__ import annotations

from datetime import datetime

from core.config.schema import ScoreBonuses, SessionOverlapConfig
from core.domain.models import ScoreComponent


def score_session_overlap(
    moment: datetime | None,
    config: SessionOverlapConfig,
    weight: float,
) -> ScoreComponent:
    """ICT Kill Zone — London/Nyu-York kesishuvidagi qo'shimcha ball."""
    if not config.enabled or moment is None:
        return ScoreComponent(
            "session_overlap", 0.0, weight, "Sessiya oynasi hisobga olinmadi", bonus=True
        )

    ichida = in_session_overlap(moment, config)
    oyna = f"{config.start_hour_utc:02d}:00-{config.end_hour_utc:02d}:00 UTC"
    izoh = (
        f"London-NY sessiya kesishuvi ({oyna})"
        if ichida
        else f"Sessiya kesishuvidan tashqarida ({moment:%H:%M} UTC, oyna {oyna})"
    )
    return ScoreComponent(
        "session_overlap", weight if ichida else 0.0, weight, izoh, bonus=True
    )


def in_session_overlap(moment: datetime, config: SessionOverlapConfig) -> bool:
    """Vaqt Kill Zone oynasi ichidami.

    Oyna yarim tunni kesib o'tishi mumkin (masalan 22:00-02:00) —
    shuning uchun oddiy `start <= soat < end` yetarli emas.
    """
    soat = moment.hour
    boshi, oxiri = config.start_hour_utc, config.end_hour_utc
    if boshi == oxiri:
        return False
    if boshi < oxiri:
        return boshi <= soat < oxiri
    return soat >= boshi or soat < oxiri


def build_bonus_components(
    moment: datetime | None,
    bonuses: ScoreBonuses,
    session: SessionOverlapConfig,
) -> list[ScoreComponent]:
    """Bonus omillari — hozircha bittasi."""
    return [score_session_overlap(moment, session, bonuses.session_overlap)]
