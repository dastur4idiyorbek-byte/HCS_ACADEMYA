"""CryptoSpot3% (ISC 1.0) omillari — bazaviy ball USTIGA qo'shiladigan bonus.

Uch bonus:

    struktura        SMC yo'nalishi (HH/HL) + BOS + MSNR daraja turi
    liquidity_sweep  LIT: narx darajani "yalab o'tib" qaytdimi
    session_overlap  ICT Kill Zone: London-Nyu-York kesishuvi

NIMA UCHUN BONUS, VAZN EMAS
---------------------------
Bazaviy vaznlar (S/R 25, trend 20, RSI 15, hajm 15, MACD 10, R/R 15)
O'LCHAB tanlangan: `scripts.kalibrlash` 27 ta sozlamada eng yuqori
ballni 59.7 deb topgan va chegaralar (50/55) aynan shu taqsimotdan
olingan. Yangi omillarni vazn sifatida kiritsak, eski omillarning
ulushi siqilardi va ballar chegaradan pastga tushib ketardi — bu
loyihada bot 48 soat jim turgan holat aynan shunday paydo bo'lgan
(`docs/ARXITEKTURA.md`, 40- va 46-bo'limlar).

Bonus esa faqat YUQORIGA suradi: topilmasa nol. Ya'ni yangi bilim
signalni to'sa olmaydi — bu metodika hujjatidagi asosiy ehtiyot
chorasi ham: "hech qanday yangi omil qat'iy to'siq sifatida
qo'shilmasin".
"""

from __future__ import annotations

from datetime import datetime

from core.analysis.level_types import LevelType
from core.analysis.market_structure import MarketStructure, structure_alignment
from core.analysis.support_resistance.liquidity import LiquiditySweep
from core.config.schema import ScoreBonuses, SessionOverlapConfig
from core.domain.models import ScoreComponent

#: Struktura bonusi ichida SMC yo'nalishi va MSNR daraja turining ulushi.
#: Yo'nalish og'irroq: daraja turi — sifat belgisi, yo'nalish esa
#: "umuman shu tomonga savdo qilish to'g'rimi" degan savol.
STRUKTURA_ULUSHLARI = {"yonalish": 0.7, "daraja": 0.3}


def score_structure(
    structure: MarketStructure | None,
    level_type: LevelType,
    weight: float,
) -> ScoreComponent:
    """SMC yo'nalishi va MSNR daraja turi uchun bonus."""
    if structure is None:
        return ScoreComponent(
            "structure", 0.0, weight, "Struktura hisoblanmadi", bonus=True
        )

    moslik = structure_alignment(structure)
    daraja = level_type.confidence
    xom = moslik * STRUKTURA_ULUSHLARI["yonalish"] + daraja * STRUKTURA_ULUSHLARI["daraja"]

    izoh = structure.describe()
    if level_type is not LevelType.PLAIN:
        izoh += f"; {level_type.label}"

    return ScoreComponent("structure", xom * weight, weight, izoh, bonus=True)


def score_liquidity_sweep(sweep: LiquiditySweep | None, weight: float) -> ScoreComponent:
    """LIT bonusi — sweep topilsa to'liq, topilmasa nol.

    "Yangiroq sweep — kuchliroq dalil": qaytishdan keyin ko'p sham
    o'tgan bo'lsa, naqsh allaqachon o'z ishini qilib bo'lgan. Shuning
    uchun ball qaytish YAQINLIGIGA qarab kamayadi.
    """
    if sweep is None:
        return ScoreComponent(
            "liquidity_sweep", 0.0, weight, "Liquidity Sweep topilmadi", bonus=True
        )

    yangilik = max(0.0, 1.0 - sweep.bars_since / 10)
    xom = 0.6 + 0.4 * yangilik
    return ScoreComponent(
        "liquidity_sweep", xom * weight, weight, sweep.describe(), bonus=True
    )


def score_session_overlap(
    moment: datetime | None,
    config: SessionOverlapConfig,
    weight: float,
) -> ScoreComponent:
    """ICT Kill Zone — London/Nyu-York kesishuvidagi qo'shimcha ball.

    Kripto 24/7 ishlaydi, ya'ni bu QAT'IY FILTR EMAS. Boshqa soatlarda
    ham sifatli signal chiqadi — shunchaki bu oynada hajm va likvidlik
    yuqoriroq bo'ladi.
    """
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
    structure: MarketStructure | None,
    level_type: LevelType,
    sweep: LiquiditySweep | None,
    moment: datetime | None,
    bonuses: ScoreBonuses,
    session: SessionOverlapConfig,
) -> list[ScoreComponent]:
    """Uchala bonusni bitta ro'yxatga yig'adi."""
    return [
        score_structure(structure, level_type, bonuses.structure),
        score_liquidity_sweep(sweep, bonuses.liquidity_sweep),
        score_session_overlap(moment, session, bonuses.session_overlap),
    ]
