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
    davomiylik_daqiqa: int = 60,
) -> ScoreComponent:
    """ICT Kill Zone — London/Nyu-York kesishuvidagi qo'shimcha ball.

    `davomiylik_daqiqa` — qaror qamrab oladigan oyna (kirish
    timeframei). Qarang: `in_session_overlap`.
    """
    if not config.enabled or moment is None:
        return ScoreComponent(
            "session_overlap", 0.0, weight, "Sessiya oynasi hisobga olinmadi", bonus=True
        )

    ichida = in_session_overlap(moment, config, davomiylik_daqiqa)
    oyna = f"{config.start_hour_utc:02d}:00-{config.end_hour_utc:02d}:00 UTC"
    izoh = (
        f"London-NY sessiya kesishuvi ({oyna})"
        if ichida
        else f"Sessiya kesishuvidan tashqarida ({moment:%H:%M} UTC, oyna {oyna})"
    )
    return ScoreComponent(
        "session_overlap", weight if ichida else 0.0, weight, izoh, bonus=True
    )


def in_session_overlap(
    moment: datetime,
    config: SessionOverlapConfig,
    davomiylik_daqiqa: int = 60,
) -> bool:
    """Qaror QAMRAB OLGAN oyna Kill Zone bilan kesishadimi.

    NIMA UCHUN NUQTA EMAS, ORALIQ. Ilgari bu yerda `moment.hour`
    tekshirilardi va bonus AMALDA HECH QACHON BERILMASDI:

        4 soatlik panjara:  00, 04, 08, 12, 16, 20 UTC
        Kill Zone oynasi:   13 <= soat < 16
        kesishma:           BO'SH

    Ya'ni "yoqilgan" bonus nol marta ishlagan. Sozlama bor edi,
    kod bor edi, natija yo'q edi.

    Endi qaror bir NUQTA emas, u qamrab oladigan ORALIQ deb
    qaraladi: `[moment, moment + davomiylik)`. 12:00 dagi 4 soatlik
    sham 12:00-16:00 ni qamraydi va Kill Zone (13:00-16:00) to'liq
    uning ichida — ya'ni bonus kuniga bir marta, aynan kerakli
    shamda beriladi.

    Oyna yarim tunni kesib o'tishi mumkin (22:00-02:00), shuning
    uchun tekshiruv daqiqa o'qida, sutka bo'yicha aylantirib
    bajariladi.
    """
    boshi, oxiri = config.start_hour_utc, config.end_hour_utc
    if boshi == oxiri:
        return False

    kun = 24 * 60
    davomiylik = max(1, min(davomiylik_daqiqa, kun))
    qaror_boshi = moment.hour * 60 + moment.minute
    oyna_boshi, oyna_oxiri = boshi * 60, oxiri * 60

    # Yarim tundan o'tuvchi oyna ikkiga bo'linadi.
    oynalar = (
        [(oyna_boshi, oyna_oxiri)]
        if oyna_boshi < oyna_oxiri
        else [(oyna_boshi, kun), (0, oyna_oxiri)]
    )
    # Qaror oralig'i ham sutkadan chiqib ketishi mumkin.
    qarorlar = [(qaror_boshi, qaror_boshi + davomiylik)]
    if qaror_boshi + davomiylik > kun:
        qarorlar = [(qaror_boshi, kun), (0, qaror_boshi + davomiylik - kun)]

    return any(
        q_boshi < o_oxiri and o_boshi < q_oxiri
        for q_boshi, q_oxiri in qarorlar
        for o_boshi, o_oxiri in oynalar
    )


def build_bonus_components(
    moment: datetime | None,
    bonuses: ScoreBonuses,
    session: SessionOverlapConfig,
    davomiylik_daqiqa: int = 60,
) -> list[ScoreComponent]:
    """Bonus omillari — hozircha bittasi.

    `davomiylik_daqiqa` — kirish timeframei. Ansiz Kill Zone tekshiruvi
    nuqta bo'lib qolardi va 4 soatlik panjarada hech qachon ishlamasdi.
    """
    return [
        score_session_overlap(
            moment, session, bonuses.session_overlap, davomiylik_daqiqa
        )
    ]
