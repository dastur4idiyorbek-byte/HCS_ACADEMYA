"""Jonli tahlil monitori — bosqich ketma-ketligini tiklash.

ASOSIY XATTI-HARAKAT: tahlil kodiga tegilmaydi. Bosqichlar qat'iy
tartibda bajarilgani uchun, coin qaysi bosqichda to'xtaganini bilsak,
undan oldingi bosqichlarni o'tgani ham aniq.
"""

from __future__ import annotations

import inspect
import re
from datetime import UTC, datetime

from core.analysis.strategies.classic_ta import ClassicTaStrategy
from core.analysis.strategies.opening_range_scalp import OpeningRangeScalpStrategy
from core.pipeline.context import CycleResult, RejectedCandidate
from core.pipeline.events import (
    CLASSIC_TA_STAGES,
    SCALP_STAGES,
    EventStatus,
    derive_events,
)

HOZIR = datetime(2026, 8, 29, 12, tzinfo=UTC)


class SoxtaNomzod:
    """`SignalCandidate` ning eng kichik o'rnini bosuvchisi."""

    def __init__(self, symbol: str, score: float) -> None:
        self.symbol = symbol
        self.score = score


def natija(rejected=None, emitted=None, breakdowns=None) -> CycleResult:  # noqa: ANN001
    return CycleResult(
        emitted=emitted or [],
        rejected=rejected or [],
        threshold=55.0,
        market_health=None,
        analyzed_count=3,
        breakdowns=breakdowns or {},
    )


# --------------------------------------------------------------------------- #
#  Ketma-ketlikni tiklash
# --------------------------------------------------------------------------- #


def test_toxtash_nuqtasigacha_hammasi_otgan_deb_belgilanadi() -> None:
    """Coin 4-bosqichda to'xtagan bo'lsa, 1-3 bosqichlarni o'tgan."""
    hodisalar = derive_events(
        natija(rejected=[RejectedCandidate("ETH", "classic_ta:zone_position", "uzoq")]),
        HOZIR,
    )

    otgan = [h.stage for h in hodisalar if h.status is EventStatus.PASSED]
    yiqilgan = [h for h in hodisalar if h.status is EventStatus.FAILED]

    assert otgan == ["classic_ta:halal", "classic_ta:data", "classic_ta:zones"]
    assert len(yiqilgan) == 1
    assert yiqilgan[0].stage == "classic_ta:zone_position"
    assert yiqilgan[0].reason == "uzoq"


def test_birinchi_bosqichda_toxtasa_otgan_bosqich_yoq() -> None:
    hodisalar = derive_events(
        natija(rejected=[RejectedCandidate("XRP", "classic_ta:halal", "halol emas")]),
        HOZIR,
    )
    assert all(h.status is EventStatus.FAILED for h in hodisalar)


def test_signal_chiqqan_coinda_hamma_bosqich_otgan() -> None:
    hodisalar = derive_events(natija(emitted=[SoxtaNomzod("BTC", 68.0)]), HOZIR)

    assert all(h.status is EventStatus.PASSED for h in hodisalar)
    assert hodisalar[-1].stage == "risk_engine"
    assert all(h.score == 68.0 for h in hodisalar)


def test_risk_engine_qoidasi_oxirgi_bosqichda_yiqiladi() -> None:
    """`risk_engine:korrelyatsiya` kabi aniq qoida ham oxirgi bosqich."""
    hodisalar = derive_events(
        natija(
            rejected=[
                RejectedCandidate("SOL", "risk_engine:correlation", "guruhda signal bor", 61.0)
            ]
        ),
        HOZIR,
    )

    yiqilgan = [h for h in hodisalar if h.status is EventStatus.FAILED]
    assert len(yiqilgan) == 1
    assert yiqilgan[0].stage == "risk_engine:correlation"
    # Undan oldingi hamma bosqich o'tgan bo'lishi kerak
    assert "threshold" in [h.stage for h in hodisalar if h.status is EventStatus.PASSED]


def test_eng_ILGOR_natija_korsatiladi() -> None:
    """Coin ikki strategiyada har xil joyda to'xtagan bo'lishi mumkin.

    Kartochkada u haqiqatan qanchalik uzoq borgani ko'rsatilishi kerak,
    eng erta to'xtash emas.
    """
    hodisalar = derive_events(
        natija(
            rejected=[
                RejectedCandidate("SOL", "classic_ta:data", "sham kam"),
                RejectedCandidate("SOL", "classic_ta:levels", "Stop juda uzoq"),
            ]
        ),
        HOZIR,
    )

    yiqilgan = [h for h in hodisalar if h.status is EventStatus.FAILED]
    assert len(yiqilgan) == 1
    assert yiqilgan[0].stage == "classic_ta:levels"


def test_signal_chiqqan_coin_rad_royxatida_bolsa_ham_signal_deb_korinadi() -> None:
    """Bir strategiyada rad etilgan, boshqasida signal bergan holat."""
    hodisalar = derive_events(
        natija(
            rejected=[RejectedCandidate("BTC", "opening_range_scalp:window", "oyna yopiq")],
            emitted=[SoxtaNomzod("BTC", 70.0)],
        ),
        HOZIR,
    )

    btc = [h for h in hodisalar if h.symbol == "BTC"]
    assert all(h.status is EventStatus.PASSED for h in btc)


def test_sikl_darajasidagi_toxtash_alohida_yoziladi() -> None:
    """Bozor Salomatligi past — bu bitta coinniki emas, butun siklniki."""
    hodisalar = derive_events(
        natija(rejected=[RejectedCandidate("*", "market_health", "indeks 32/100")]),
        HOZIR,
    )

    assert len(hodisalar) == 1
    assert hodisalar[0].symbol == "*"
    assert hodisalar[0].status is EventStatus.FAILED


def test_bosh_natijada_hodisa_yoq() -> None:
    assert derive_events(natija(), HOZIR) == []


def test_vaqt_har_bir_hodisaga_yoziladi() -> None:
    hodisalar = derive_events(natija(emitted=[SoxtaNomzod("BTC", 60.0)]), HOZIR)
    assert all(h.at == HOZIR for h in hodisalar)


def test_belgilar_kartochka_uchun_tayyor() -> None:
    assert EventStatus.PASSED.icon == "✅"
    assert EventStatus.FAILED.icon == "❌"
    assert EventStatus.PENDING.icon == "⏳"


# --------------------------------------------------------------------------- #
#  Zanjir STRATEGIYA bilan bir xil bo'lishi SHART
# --------------------------------------------------------------------------- #


def _manbadagi_tartib(funksiya) -> list[str]:  # noqa: ANN001
    """`analyze()` ichidagi `_reject("...")` chaqiruvlari — tartibi bilan."""
    manba = inspect.getsource(funksiya)
    topilgan: list[str] = []
    for nom in re.findall(r'self\._reject\(\s*"([a-z_]+)"', manba):
        if nom not in topilgan:
            topilgan.append(nom)
    return topilgan


def test_bosqichlar_tartibi_strategiya_bilan_mos() -> None:
    """1-naqsh: "bitta qiymat ikki joyda yozilgan".

    `CLASSIC_TA_STAGES` — strategiyadagi tekshiruvlar tartibining
    NUSXASI. Strategiyaga yangi bosqich qo'shilsa yoki tartib
    o'zgarsa, bu ro'yxat eskirib qoladi va monitor noto'g'ri
    ketma-ketlik ko'rsatardi.

    Shuning uchun bu yerda `analyze()` manbasidan haqiqiy tartib
    o'qib olinadi va solishtiriladi.
    """
    topilgan = _manbadagi_tartib(ClassicTaStrategy.analyze)

    # `levels` bosqichi `daraja_natijasi.stage` orqali keladi —
    # u `_reject("...")` ko'rinishida yozilmagan, shuning uchun
    # solishtirishdan chiqariladi (o'rni alohida tekshiriladi).
    kutilgan = [n for n in CLASSIC_TA_STAGES if n != "levels"]

    assert topilgan == kutilgan, (
        f"strategiyadagi tartib: {topilgan}\n"
        f"monitordagi tartib:    {kutilgan}\n"
        "CLASSIC_TA_STAGES ni yangilang"
    )


def test_levels_strukturadan_OLDIN_turadi() -> None:
    """`levels` regexga tushmaydi — o'rni manbadan alohida o'qiladi.

    Bu real xato edi: ro'yxatda `levels` oxirida turardi, kodda esa
    darajalar STRUKTURADAN OLDIN tekshiriladi. Natijada strukturada
    to'xtagan coin uchun monitor "darajalar tekshirilmadi" deb
    ko'rsatardi — holbuki ular allaqachon o'tgan edi.
    """
    manba = inspect.getsource(ClassicTaStrategy.analyze)
    darajalar = manba.index("daraja_natijasi.stage")
    struktura = manba.index('self._reject(\n                "structure"')
    assert darajalar < struktura, "kodda tartib o'zgargan"

    tartib = list(CLASSIC_TA_STAGES)
    assert tartib.index("levels") < tartib.index("structure")


def test_skalping_zanjiri_ozining_bosqichlaridan_iborat() -> None:
    """Skalpingning yo'li BOSHQA — unda `zones` ham, `confirmation` ham yo'q.

    Klassik zanjir unga qo'llansa, monitor mavjud bo'lmagan
    bosqichlarni "✅ o'tdi" deb ko'rsatardi, ya'ni yolg'on gapirardi.
    """
    topilgan = _manbadagi_tartib(OpeningRangeScalpStrategy.analyze)
    assert topilgan == list(SCALP_STAGES)[: len(topilgan)]

    hodisalar = derive_events(
        natija(rejected=[RejectedCandidate("BTC", "opening_range_scalp:breakout", "yo'q")]),
        HOZIR,
    )
    otgan = [h.stage for h in hodisalar if h.status is EventStatus.PASSED]
    assert otgan == [
        "opening_range_scalp:halal",
        "opening_range_scalp:data",
        "opening_range_scalp:session",
        "opening_range_scalp:window",
        "opening_range_scalp:range",
        "opening_range_scalp:volume",
    ]
    assert not any("zones" in nom for nom in otgan)


def test_aniqroq_rad_kodi_zanjirda_tanib_olinadi() -> None:
    """`classic_ta:levels:stop_too_close` — bu `levels` bosqichi.

    Aynan tenglik bilan solishtirilganda bu kod zanjirda topilmasdi va
    monitor undan KEYINGI bosqichni (`structure`) ham "o'tgan" deb
    chizib yuborardi.
    """
    hodisalar = derive_events(
        natija(
            rejected=[
                RejectedCandidate("BTC", "classic_ta:levels:stop_too_close", "stop yaqin")
            ]
        ),
        HOZIR,
    )
    otgan = [h.stage for h in hodisalar if h.status is EventStatus.PASSED]
    assert "classic_ta:structure" not in otgan
    assert otgan[-1] == "classic_ta:confirmation"


def test_notanish_strategiya_uchun_zanjir_toqib_chiqarilmaydi() -> None:
    """Monitorning qiymati rostgo'yligida: har bir ✅ haqiqiy bo'lsin."""
    hodisalar = derive_events(
        natija(rejected=[RejectedCandidate("BTC", "yangi_strategiya:nimadir", "sabab")]),
        HOZIR,
    )
    assert [h.status for h in hodisalar] == [EventStatus.FAILED]


def test_vaqt_darvozasi_haqiqiy_sababni_bosib_ketmaydi() -> None:
    """Skalping oynasi kuniga 45 daqiqa ochiq — qolgan vaqtda u HAR
    COIN uchun yoziladi. Zanjirda chuqurroq turgani uchun u klassik
    tahlilning haqiqiy sababini bosib ketardi va monitor har kuni
    bir xil "oyna yopiq" ni ko'rsatardi.
    """
    hodisalar = derive_events(
        natija(
            rejected=[
                RejectedCandidate("BTC", "classic_ta:data", "sham yetarli emas"),
                RejectedCandidate("BTC", "opening_range_scalp:window", "oyna yopiq"),
            ]
        ),
        HOZIR,
    )
    yiqilgan = [h for h in hodisalar if h.status is EventStatus.FAILED]
    assert [h.stage for h in yiqilgan] == ["classic_ta:data"]


def test_boshqa_sabab_bolmasa_darvoza_korsatiladi() -> None:
    """Yashirmaymiz: boshqa sabab yo'q bo'lsa, kutish ham ma'lumot."""
    hodisalar = derive_events(
        natija(rejected=[RejectedCandidate("BTC", "opening_range_scalp:window", "oyna yopiq")]),
        HOZIR,
    )
    yiqilgan = [h for h in hodisalar if h.status is EventStatus.FAILED]
    assert [h.stage for h in yiqilgan] == ["opening_range_scalp:window"]
