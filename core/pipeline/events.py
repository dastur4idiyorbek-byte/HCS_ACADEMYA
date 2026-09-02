"""Jonli tahlil monitori — "oshxona ko'rinishi" uchun hodisalar.

Admin tizimning ishlayotganini KO'ZI BILAN ko'rishi kerak: qaysi coin
qaysi bosqichda, nima uchun to'xtadi. Restoran metaforasi bilan: taom
(signal) qanday tayyorlanayotganini oynadan kuzatish.

    Oshxona            -> `core/pipeline`
    Retsept bosqichlari -> S/R -> SMC -> LIT -> Ball -> Risk Engine
    Tayyor taom        -> chiqarilgan signal
    Qaytarilgan        -> rad etilgan nomzod VA SABABI

ASOSIY G'OYA: TAHLIL KODIGA UMUMAN TEGILMAYDI
---------------------------------------------
Bosqichlar QAT'IY TARTIBDA bajariladi. Demak coin qaysi bosqichda
to'xtaganini bilsak, undan OLDINGI bosqichlarni o'tgani ham aniq —
aks holda u o'sha yergacha yetib bormasdi.

Shuning uchun bu modul `CycleResult` dan butun ketma-ketlikni QAYTA
TIKLAYDI. Strategiya ichiga hech qanday "hodisa yozish" chaqiruvi
qo'shilmaydi: tahlil yo'li o'zgarmaydi, tezligi ham.

Bu modul SOF: bazaga ham, tarmoqqa ham murojaat qilmaydi (0.1-band).
Yozish `bot/services/runner.py` da, ko'rsatish esa saytda.
"""

from __future__ import annotations

from datetime import datetime

from core.domain.enums import EventStatus
from core.domain.models import PipelineEvent
from core.pipeline.context import ROUTINE_STAGES, CycleResult

__all__ = [
    "CLASSIC_TA_STAGES",
    "CYCLE_STAGES",
    "EventStatus",
    "PipelineEvent",
    "SCALP_STAGES",
    "STRATEGY_STAGES",
    "derive_events",
]

#: Sikl darajasidagi bosqichlar — BITTA yozuv barcha coinlarni to'xtatadi.
#: Ular coin kartochkasiga tegishli emas.
CYCLE_STAGES = frozenset({"market_health"})


#: Strategiya bosqichlari — QAT'IY TARTIBDA.
#:
#: Manba: `core/analysis/strategies/*.py` -> `analyze()`.
#: Tartib o'sha yerdagi tekshiruvlar ketma-ketligi bilan bir xil
#: bo'lishi SHART — `tests/core/test_pipeline_events.py` buni qulflaydi.
CLASSIC_TA_STAGES: tuple[str, ...] = (
    "halal",
    "data",
    "zones",
    "zone_position",
    "timeframes",
    "indicators",
    "confirmation",
    "levels",
    "structure",
)

#: 3.9 — kunlik sham ochilishi skalping. Uning yo'li BUTUNLAY BOSHQA:
#: unda `zones` ham, `confirmation` ham yo'q. Klassik zanjirni unga
#: qo'llasak, monitor mavjud bo'lmagan bosqichlarni "✅ o'tdi" deb
#: ko'rsatardi — ya'ni yolg'on gapirardi.
SCALP_STAGES: tuple[str, ...] = (
    "halal",
    "data",
    "session",
    "window",
    "range",
    "volume",
    "breakout",
    "levels",
)

#: Strategiya prefiksi -> uning bosqichlar zanjiri.
STRATEGY_STAGES: dict[str, tuple[str, ...]] = {
    "classic_ta": CLASSIC_TA_STAGES,
    "opening_range_scalp": SCALP_STAGES,
}

#: Strategiyadan KEYINGI umumiy bosqichlar (sikl darajasida).
FINAL_STAGES: tuple[str, ...] = ("threshold", "risk_engine")


def _strategy_stages(prefix: str) -> tuple[str, ...]:
    return tuple(f"{prefix}:{nom}" for nom in STRATEGY_STAGES.get(prefix, ()))


def _matches(stage: str, zanjir_bandi: str) -> bool:
    """Bosqich zanjirdagi shu bandmi.

    Rad etish kodi aniqroq bo'lishi mumkin: `classic_ta:levels` o'rniga
    `classic_ta:levels:stop_too_close` keladi. Aynan tenglik bilan
    solishtirsak, bunday kod zanjirda umuman topilmasdi va monitor
    undan KEYINGI bosqichlarni ham "o'tgan" deb chizib yuborardi.
    """
    return stage == zanjir_bandi or stage.startswith(f"{zanjir_bandi}:")


def derive_events(result: CycleResult, at: datetime) -> list[PipelineEvent]:
    """`CycleResult` dan har bir coin uchun bosqich ketma-ketligini tiklaydi.

    Har bir coin uchun:
      * to'xtagan joyigacha bo'lgan bosqichlar — `PASSED`;
      * to'xtagan bosqich — `FAILED` va sababi;
      * signal chiqqan bo'lsa — hammasi `PASSED`.

    Sikl darajasidagi rad etish (`market_health`) alohida qaytariladi:
    u bitta coinniki emas, butun siklniki.
    """
    hodisalar: list[PipelineEvent] = []

    # 1) Sikl darajasi — butun siklni to'xtatgan sabab
    for rad in result.rejected:
        if rad.stage in CYCLE_STAGES:
            hodisalar.append(
                PipelineEvent("*", rad.stage, EventStatus.FAILED, rad.detail, at=at)
            )

    # 2) Coin bo'yicha ENG UZOQ borgan nuqta.
    #
    # Bir coin bir necha strategiyadan o'tishi mumkin va har biri o'z
    # rad sababini yozadi. Kartochkada eng ILG'OR natija ko'rsatiladi:
    # coin bitta strategiyada 2-bosqichda, boshqasida 7-bosqichda
    # to'xtagan bo'lsa, u haqiqatan 7-bosqichgacha borgan.
    #
    # VAQT DARVOZALARI ALOHIDA. Skalping oynasi kuniga atigi 45 daqiqa
    # ochiq, ya'ni qolgan vaqtda "oyna yopiq" yozuvi HAR SIKLDA, HAR
    # COIN uchun keladi. U zanjirda chuqurroq turgani uchun klassik
    # tahlilning haqiqiy sababini bosib ketardi va monitor har kuni
    # bir xil "oyna yopiq" ni ko'rsatardi.
    rad_holati: dict[str, tuple[int, str, str]] = {}
    darvoza_holati: dict[str, tuple[int, str, str]] = {}
    for rad in result.rejected:
        if rad.stage in CYCLE_STAGES or rad.symbol == "*":
            continue
        qayerga = darvoza_holati if rad.stage in ROUTINE_STAGES else rad_holati
        tartib = _stage_index(rad.stage)
        joriy = qayerga.get(rad.symbol)
        if joriy is None or tartib > joriy[0]:
            qayerga[rad.symbol] = (tartib, rad.stage, rad.detail)

    # Darvoza yozuvi faqat BOSHQA sabab bo'lmaganda ishlatiladi
    for symbol, holat in darvoza_holati.items():
        rad_holati.setdefault(symbol, holat)

    chiqqanlar = {n.symbol for n in result.emitted}

    for symbol, (_, bosqich, sabab) in sorted(rad_holati.items()):
        if symbol in chiqqanlar:
            # Bir strategiyada rad etilgan, boshqasida signal bergan —
            # foydalanuvchi uchun bu SIGNAL chiqqan coin.
            continue
        ball = _score_of(result, symbol)
        hodisalar.extend(_upto(symbol, bosqich, sabab, ball, at))

    for nomzod in result.emitted:
        hodisalar.extend(_all_passed(nomzod.symbol, nomzod.score, at))

    return hodisalar


def _stage_index(stage: str) -> int:
    """Bosqichning zanjirdagi o'rni. Noma'lum bosqich oxiriga qo'yiladi."""
    barcha = _ordered_stages(stage)
    for i, band in enumerate(barcha):
        if _matches(stage, band):
            return i
    return len(barcha)


def _ordered_stages(stage: str) -> list[str]:
    """Shu bosqich tegishli bo'lgan to'liq zanjir.

    Noma'lum strategiya uchun zanjir TO'QIB CHIQARILMAYDI: faqat
    yakuniy bosqichlar qaytadi. Monitorning butun qiymati rostgo'yligida
    — ko'rsatilgan har bir ✅ haqiqatan bajarilgan bo'lishi kerak.
    """
    prefiks = stage.split(":", 1)[0] if ":" in stage else stage

    # Yakuniy bosqich (`threshold`, `risk_engine:*`) — bu yerga coin
    # allaqachon BIROR strategiyadan o'tib kelgan. Qaysinisidan ekani
    # rad yozuvida yo'q, shuning uchun asosiy zanjir — klassik tahlil
    # ko'rsatiladi: amalda signal yo'lining deyarli hammasi shu.
    if prefiks in FINAL_STAGES:
        prefiks = "classic_ta"

    return [*_strategy_stages(prefiks), *FINAL_STAGES]


def _upto(
    symbol: str, failed_stage: str, reason: str, score: float | None, at: datetime
) -> list[PipelineEvent]:
    """To'xtash nuqtasigacha `PASSED`, o'sha nuqtada `FAILED`."""
    zanjir = _ordered_stages(failed_stage)
    if not any(_matches(failed_stage, nom) for nom in zanjir):
        # Zanjirda yo'q bosqich (yangi strategiya, ichki xato kodi).
        # Undan OLDINGI bosqichlarni "o'tgan" deb yozish taxmin bo'lardi
        # — monitor faqat aniq bilgan narsasini ko'rsatadi.
        return [PipelineEvent(symbol, failed_stage, EventStatus.FAILED, reason, score, at)]

    natija: list[PipelineEvent] = []
    for nom in zanjir:
        if _matches(failed_stage, nom):
            natija.append(
                PipelineEvent(symbol, failed_stage, EventStatus.FAILED, reason, score, at)
            )
            return natija
        natija.append(PipelineEvent(symbol, nom, EventStatus.PASSED, score=score, at=at))
    return natija  # bu yerga yetib bo'lmaydi — bosqich zanjirda bor


def _all_passed(symbol: str, score: float, at: datetime) -> list[PipelineEvent]:
    zanjir = _ordered_stages("classic_ta:halal")
    return [
        PipelineEvent(symbol, nom, EventStatus.PASSED, score=score, at=at)
        for nom in zanjir
    ]


def _score_of(result: CycleResult, symbol: str) -> float | None:
    tafsilot = result.breakdowns.get(symbol)
    if tafsilot is not None:
        return tafsilot.total
    for rad in result.rejected:
        if rad.symbol == symbol and rad.score is not None:
            return rad.score
    return None
