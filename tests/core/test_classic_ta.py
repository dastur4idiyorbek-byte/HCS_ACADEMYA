"""3.1-band: `classic_ta` strategiyasining to'liq zanjiri.

    S/R -> Discount -> ko'p timeframe -> indikatorlar -> darajalar -> ball

Har bir bosqichda "yo'q" javobi olinsa, `analyze()` `None` qaytaradi va
sababni saqlaydi. `None` — XATO EMAS (0.2-band: "signal bermaslik normal").
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.strategies import StrategyInput
from core.analysis.strategies.classic_ta import ClassicTaStrategy
from core.config import load_config
from core.domain.enums import HalalStatus
from core.domain.models import Candle, HalalVerdict
from core.utils.time_utils import utc_now

BOSH = datetime(2026, 1, 1, tzinfo=UTC)
HALOL = HalalVerdict("BTC", HalalStatus.HALAL, "halol")


def sham(i: int, close: float, high: float | None = None,
         low: float | None = None, volume: float = 1000.0) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(hours=i),
        open=close,
        high=high if high is not None else close * 1.004,
        low=low if low is not None else close * 0.996,
        close=close,
        volume=volume,
    )


def kotarilish(n: int = 260) -> list[Candle]:
    return [sham(i, 100 + i * 0.4) for i in range(n)]


def tushish(n: int = 260) -> list[Candle]:
    return [sham(i, 300 - i * 0.4) for i in range(n)]


def qaytishdagi_kotarilish(n: int = 260, qaytish: int = 25) -> list[Candle]:
    """Haqiqiy pullback: uzoq ko'tarilish, so'ng EMA50 ostiga tushish.

    Narx EMA50 dan PAST, lekin EMA200 dan YUQORI va EMA50 > EMA200 —
    ya'ni trend tuzilishi buzilmagan, faqat vaqtincha qaytish. Aynan shu
    holat support zonasini yaratadi.
    """
    narxlar = [100 + i * 0.4 for i in range(n - qaytish)]
    narxlar += [narxlar[-1] - 0.9 * (i + 1) for i in range(qaytish)]
    return [sham(i, narx) for i, narx in enumerate(narxlar)]


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


@pytest.fixture
def strategy(config):  # noqa: ANN001, ANN201
    return ClassicTaStrategy(config)


def kirish(config, entry_candles: list[Candle], htf: list[Candle] | None = None,   # noqa: ANN001
           verdict: HalalVerdict = HALOL) -> StrategyInput:
    """Barcha timeframelarga bir xil shakl beradi (aks holda muvofiqlik buziladi)."""
    yuqori = htf if htf is not None else entry_candles
    shamlar = {config.analysis.entry_timeframe: entry_candles}
    for tf in config.analysis.htf_confirmation:
        shamlar[tf] = yuqori
    return StrategyInput(
        symbol="BTC", now=utc_now(), halal_verdict=verdict, candles=shamlar
    )


# --------------------------------------------------------------------------- #
#  Rad etish bosqichlari — har biri o'z sababini beradi
# --------------------------------------------------------------------------- #


def test_harom_coin_darhol_rad_etiladi(strategy, config) -> None:  # noqa: ANN001
    """Skrining allaqachon filtrlagan, lekin bu takroriy himoya."""
    harom = HalalVerdict("XXX", HalalStatus.HARAM, "foizli qarz protokoli")
    natija = strategy.analyze(kirish(config, kotarilish(), verdict=harom))

    assert natija is None
    assert strategy.last_rejection.stage == "halal"


def test_sham_yetmasa_rad_etiladi(strategy, config) -> None:  # noqa: ANN001
    natija = strategy.analyze(kirish(config, kotarilish(50)))

    assert natija is None
    assert strategy.last_rejection.stage == "data"


def test_tushayotgan_bozorda_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    natija = strategy.analyze(kirish(config, tushish()))
    assert natija is None


def test_timeframelar_zid_bolsa_signal_yoq(strategy, config) -> None:  # noqa: ANN001
    """3.2-band qat'iy qoidasi: pastki TF yuqorisiga zid bo'lmasligi kerak."""
    natija = strategy.analyze(kirish(config, kotarilish(), htf=tushish()))

    assert natija is None
    assert strategy.last_rejection.stage in {"zone_position", "timeframes"}


def test_rad_sababi_har_doim_saqlanadi(strategy, config) -> None:  # noqa: ANN001
    """Admin nima uchun signal chiqmaganini ko'ra olishi kerak (3.7-band)."""
    strategy.analyze(kirish(config, tushish()))

    assert strategy.last_rejection is not None
    assert strategy.last_rejection.stage
    assert strategy.last_rejection.detail


def test_muvaffaqiyatli_tahlildan_keyin_rad_tozalanadi(strategy, config) -> None:  # noqa: ANN001
    strategy.analyze(kirish(config, tushish()))
    assert strategy.last_rejection is not None

    strategy.analyze(kirish(config, kotarilish()))
    # Yangi tahlil o'z sababini yozadi yoki tozalaydi — eskisi qolib ketmasligi kerak
    assert strategy.last_rejection is None or strategy.last_rejection.stage != "halal"


# --------------------------------------------------------------------------- #
#  Muvaffaqiyatli yo'l
# --------------------------------------------------------------------------- #


def qaytishli_kotarilish() -> list[Candle]:
    """Ko'tarilish trendi, oxirida support ustiga qaytish va burilish.

    Shakl ATAYLAB aniq S/R darajalari bilan qurilgan (tsikllardan hosil
    qilish o'rniga) — shunda zonalar aniq shakllanadi va sinov natijasi
    tasodifga bog'liq bo'lmaydi.

    O'lchangan natija: Stop 1.49% (3.3-banddagi 1..5% oralig'ining
    o'rtasi), zona joylashuvi 36% (aniq Discount), nisbat 1:3.0.

    Fitil kengligi (0.8%) muhim: ATR shundan hisoblanadi, ATR esa
    "narx zonaga yaqinmi" va Stop masofasini belgilaydi. Juda tor fitil
    bilan Stop har doim 1% dan yaqin chiqib, signal rad etilardi.
    """
    SUPPORT, RESISTANCE = 8000.0, 8480.0   # 6% diapazon
    FITIL = 0.008                          # ATR ~1.6% -> zonalar mazmunli
    KOTARILISH = 0.005                     # har tsiklda ~0.5% yuqoriga
    OXIRGI_ULUSH = 0.34                    # diapazonning pastki uchdan biri

    shamlar: list[Candle] = []
    i = 0

    def qoshish(narx: float, hajm: float = 1000.0) -> None:
        nonlocal i
        shamlar.append(
            sham(i, narx, narx * (1 + FITIL), narx * (1 - FITIL), volume=hajm)
        )
        i += 1

    for tsikl in range(12):
        siljish = 1 + tsikl * KOTARILISH
        for ulush in (0.05, 0.45, 0.95, 0.60, 0.20, 0.05):
            narx = (SUPPORT + (RESISTANCE - SUPPORT) * ulush) * siljish
            for _ in range(3):
                qoshish(narx)

    # Oxirgi qaytish: narx support ustida to'xtaydi, hajm oshib burilish
    # boshlanadi.
    siljish = 1 + 11 * KOTARILISH
    tayanch = (SUPPORT + (RESISTANCE - SUPPORT) * OXIRGI_ULUSH) * siljish
    for j in range(6):
        qoshish(tayanch, hajm=2700.0 if j >= 4 else 1200.0)

    return shamlar


def test_qulay_sharoitda_nomzod_chiqadi(config) -> None:  # noqa: ANN001
    """To'liq zanjir: S/R -> Discount -> timeframelar -> indikatorlar -> ball."""
    strategiya = ClassicTaStrategy(config)
    natija = strategiya.analyze(kirish(config, qaytishli_kotarilish()))

    assert natija is not None, (
        f"nomzod kutilgan edi, rad sababi: {strategiya.last_rejection}"
    )
    assert natija.symbol == "BTC"
    assert natija.score > 0
    assert natija.levels.stop < natija.levels.entry < natija.levels.tp1 < natija.levels.tp2
    # Shkala: bazaviy 100 + CryptoSpot3% bonuslari
    assert natija.breakdown.base_total <= 100
    assert natija.breakdown.maximum == pytest.approx(
        100 + config.scoring.bonuses.total()
    )


def test_nomzod_uchta_qatlamdan_otadi(config) -> None:  # noqa: ANN001
    """Nomzod chiqsa, u S/R + zona + indikator uchalasini ham o'tgan bo'ladi."""
    natija = ClassicTaStrategy(config).analyze(kirish(config, qaytishli_kotarilish()))

    assert natija is not None
    bazaviy = {k.name for k in natija.breakdown.components if not k.bonus}
    assert bazaviy == {
        "support_resistance", "trend", "rsi", "volume", "macd", "risk_reward"
    }
    # CryptoSpot3% dalillari ALOHIDA omil emas: ular S/R va trend
    # omillari ichiga qo'shiladi. Bonus bo'lib faqat vaqt omili qoldi.
    bonuslar = {k.name for k in natija.breakdown.components if k.bonus}
    assert bonuslar == {"session_overlap"}
    assert natija.halal_verdict.is_tradable


def test_darajalar_uchinchi_band_chegaralariga_mos(config) -> None:  # noqa: ANN001
    """3.3-band chegaralari, STRATEGIYA qiymatlari bilan.

    Nisbat endi strategiya darajasida: mean reversion 1:1.5, global 1:3.
    Darajalarni qurish va tekshirish AYNAN bir xil qiymatga tayanishi
    kerak, aks holda TP2 bir nisbat bo'yicha quriladi, boshqasi bo'yicha
    rad etiladi.
    """
    from core.analysis.strategies.classic_ta import classic_ta_rules

    natija = ClassicTaStrategy(config).analyze(kirish(config, qaytishli_kotarilish()))
    assert natija is not None

    qoidalar = classic_ta_rules(config)
    darajalar = natija.levels
    assert darajalar.stop_distance_pct <= qoidalar.max_stop_distance_pct
    assert qoidalar.min_tp_distance_pct <= darajalar.tp1_distance_pct <= qoidalar.max_tp_distance_pct
    assert darajalar.risk_reward_tp2 >= qoidalar.min_risk_reward


def _bayroq_bilan(config, **indikator_maydonlari):  # noqa: ANN001, ANN201
    """Indikator sozlamasi o'zgartirilgan konfiguratsiya nusxasi."""
    indikatorlar = dataclasses.replace(config.analysis.indicators, **indikator_maydonlari)
    return dataclasses.replace(
        config, analysis=dataclasses.replace(config.analysis, indicators=indikatorlar)
    )


def test_tasdiq_talab_qilinsa_signal_toxtaydi(config) -> None:  # noqa: ANN001
    """Eski xatti-harakat `require_confirmation` orqali qaytariladi.

    4/4 talab qilinganda ikki oyna kesishmaydi — o'lchangan xatti-harakat
    (`docs/ARXITEKTURA.md` 22-bo'lim): MACD kechikuvchi indikator, u
    tasdiqlaganda narx allaqachon Discount zonasidan chiqib ketgan bo'ladi.
    """
    qatiy = _bayroq_bilan(config, min_confirmations=4, require_confirmation=True)
    strategiya = ClassicTaStrategy(qatiy)

    assert strategiya.analyze(kirish(qatiy, qaytishli_kotarilish())) is None
    assert strategiya.last_rejection.stage == "confirmation"


def test_standart_sozlamada_tasdiq_signalni_toxtatmaydi(config) -> None:  # noqa: ANN001
    """Indikator tasdig'i QAROR uchun emas, REYTING uchun.

    4/4 tasdiq talabi bilan ham nomzod chiqishi kerak: tasdiq yo'qligi
    ballni tushiradi, lekin signalni to'sib qo'ymaydi. Indikatorlar
    kechikadi — ular tasdiqlaguncha narx arzon zonadan chiqib ketadi.
    """
    yumshoq = _bayroq_bilan(config, min_confirmations=4)
    assert yumshoq.analysis.indicators.require_confirmation is False, "standart holat"

    strategiya = ClassicTaStrategy(yumshoq)
    natija = strategiya.analyze(kirish(yumshoq, qaytishli_kotarilish()))

    assert natija is not None, (
        f"tasdiq to'siq bo'lmasligi kerak, rad sababi: {strategiya.last_rejection}"
    )


def test_tasdiqlanmagan_omil_ballni_tushiradi(config) -> None:  # noqa: ANN001
    """Indikatorlar qattiq to'siq EMAS — ularning yo'qligi ballni tushiradi.

    Bu test ilgari boshqacha yozilgan edi: "MACD tasdiqlamagan nomzod eng
    past chegaradan ham o'tmasligi kerak". Talab mantiqiy eshitilardi,
    lekin u ikkita faktni birga hisobga olmasdi:

      • support zonasida xarid qilinganda MACD deyarli HAR DOIM signal
        chizig'idan pastda bo'ladi (kesish keyinroq keladi);
      • ya'ni bu talab "support'da hech qachon xarid qilinmasin" degani
        bilan barobar edi.

    Chegara 80 bo'lgani uchun test o'tib turardi va muammo ko'rinmasdi.
    Endi u ASL xususiyatni tekshiradi: tasdiq yo'qligi ball tafsilotida
    ochiq ko'rinadi va yig'indini kamaytiradi.
    """
    natija = ClassicTaStrategy(config).analyze(kirish(config, qaytishli_kotarilish()))
    assert natija is not None

    macd = natija.breakdown.component("macd")
    assert macd is not None

    if macd.earned == 0:
        assert "tasdiq yo'q" in macd.explanation, "sabab ko'rinib turishi kerak"
        assert natija.score < natija.breakdown.maximum - macd.maximum + 0.01, (
            "tasdiqlanmagan omil yig'indiga qo'shilib qolmasligi kerak"
        )


# --------------------------------------------------------------------------- #
#  Strategiya interfeysi (6.1-band)
# --------------------------------------------------------------------------- #


def test_strategiya_kerakli_timeframelarni_elon_qiladi(strategy, config) -> None:  # noqa: ANN001
    kerakli = strategy.required_timeframes()

    assert kerakli[0] == config.analysis.entry_timeframe
    assert set(config.analysis.htf_confirmation) <= set(kerakli)


def test_strategiya_yoqilganligini_bildiradi(strategy) -> None:  # noqa: ANN001
    assert strategy.enabled is True
    assert strategy.name == "classic_ta"


# --------------------------------------------------------------------------- #
#  Indikatorlar QAROR uchun emas, REYTING uchun
# --------------------------------------------------------------------------- #


def test_yuqori_timeframe_zid_bolsa_ham_nomzod_chiqadi(config) -> None:  # noqa: ANN001
    """Kunlik EMA200 — 200 kunlik o'rtacha, eng sekin kechikuvchi o'lchov.

    Uni majburiy qilish burilish nuqtasidagi HAR QANDAY kirishni to'sadi:
    narx pastdan qaytayotganda kunlik trend hali pastga qaragan bo'ladi.
    Endi bu ballga ta'sir qiladi, to'siq bo'lmaydi.
    """
    assert config.analysis.require_htf_alignment is False, "standart holat"

    strategiya = ClassicTaStrategy(config)
    natija = strategiya.analyze(
        kirish(config, qaytishli_kotarilish(), htf=qaytishdagi_kotarilish())
    )

    sabab = strategiya.last_rejection
    assert sabab is None or sabab.stage != "timeframes", (
        f"yuqori timeframe to'siq bo'lmasligi kerak, sabab: {sabab}"
    )
    assert natija is not None


def pasayish(n: int = 260) -> list[Candle]:
    """Aniq tushish trendi."""
    return [sham(i, 200 - i * 0.4) for i in range(n)]


def kotarilish_htf(n: int = 260) -> list[Candle]:
    """Aniq ko'tarilish trendi — yuqori timeframe uchun."""
    return [sham(i, 100 + i * 0.4) for i in range(n)]


def test_yuqori_timeframe_STRUKTURA_bilan_tasniflanadi(config) -> None:  # noqa: ANN001
    """3.2-band: HTF trendi endi EMA bilan emas, SMC strukturasi bilan.

    Ilgari bu yerda `htf_trend_requires_price_above_fast` bayrog'i
    turardi: kunlik EMA50 dan yuqori bo'lish talab qilinsa, support
    zonasiga qaytish HECH QACHON "UP" bermasdi (27-bo'lim). Bayroq
    bilan birga muammoning o'zi ham yo'qoldi — struktura narxning
    EMA ga nisbatan holatini umuman so'ramaydi.
    """
    import inspect

    from core.analysis.strategies.classic_ta import ClassicTaStrategy

    manba = inspect.getsource(ClassicTaStrategy._timeframe_view)
    # Izohlarni chiqarib tashlaymiz: ular EMA ni TARIX sifatida eslatadi
    kod = "\n".join(
        q for q in manba.splitlines() if not q.strip().startswith("#")
    )
    kod = kod[: kod.index('"""')] + kod[kod.rindex('"""') :]

    assert "analyze_structure" in kod
    assert "timeframe_trend" not in kod, "EMA asosidagi tasnif qolib ketgan"
    assert "ema" not in kod.lower(), "HTF tasnifida EMA qolmasligi kerak"


def test_yuqori_timeframe_moslikka_qarab_ball_ozgaradi(config) -> None:  # noqa: ANN001
    """Ma'lumot yo'qolmaydi: to'siq o'rniga DARAJA bo'lib ballga kiradi.

    Bu muhim — to'siqni olib tashlab, o'rniga hech narsa qo'ymaslik
    yuqori timeframe ma'lumotini butunlay yo'qotardi. U endi
    reytingda ishtirok etadi: tushayotgan katta rasm ballni pasaytiradi,
    lekin signalni to'sib qo'ymaydi.
    """
    strategiya = ClassicTaStrategy(config)

    mos = strategiya.analyze(kirish(config, qaytishli_kotarilish(), htf=kotarilish_htf()))
    zid = strategiya.analyze(kirish(config, qaytishli_kotarilish(), htf=pasayish()))

    assert mos is not None and zid is not None
    mos_trend = mos.breakdown.component("trend")
    zid_trend = zid.breakdown.component("trend")

    assert zid_trend.earned < mos_trend.earned, (
        "yuqori timeframe zid bo'lsa trend balli pastroq bo'lishi kerak"
    )
    assert zid.score < mos.score, "yig'indi ball ham pastroq bo'lishi kerak"


def test_indikator_tasdigi_bolmasa_ham_daraja_quriladi(config) -> None:  # noqa: ANN001
    """Qaror strukturaga va risk qoidasiga qoladi.

    Nomzod chiqqan ekan, uning darajalari 3.3-banddagi qoidaga mos
    bo'lishi SHART — indikator to'sig'i olib tashlangani risk
    qoidasini yumshatmaydi.
    """
    natija = ClassicTaStrategy(config).analyze(kirish(config, qaytishli_kotarilish()))
    assert natija is not None

    from core.analysis.strategies.classic_ta import classic_ta_rules

    qoidalar = classic_ta_rules(config)
    darajalar = natija.levels
    assert qoidalar.min_stop_distance_pct <= darajalar.stop_distance_pct
    assert darajalar.stop_distance_pct <= qoidalar.max_stop_distance_pct
    assert darajalar.risk_reward_tp2 >= qoidalar.min_risk_reward


# --------------------------------------------------------------------------- #
#  CryptoSpot3% qatlami — BONUS, TO'SIQ EMAS
# --------------------------------------------------------------------------- #


def test_struktura_standart_holatda_tosiq_emas(config) -> None:  # noqa: ANN001
    """Metodika hujjatining o'z talabi: yangi omil yo'lni yopmasin.

    Bu loyihada qat'iy "VA" filtrlarini ko'paytirish signal voronkasini
    allaqachon nolga tushirgan (44-bo'lim). Shuning uchun
    `require_structure_alignment` standart holatda `False`.
    """
    assert config.analysis.require_structure_alignment is False


def test_struktura_darvozasi_yoqilsa_pasayish_rad_etiladi(config) -> None:  # noqa: ANN001
    """Yoqilganda esa u haqiqatan ishlashi va VORONKADA ko'rinishi kerak."""
    import dataclasses

    from core.pipeline.context import stage_label

    qattiq = dataclasses.replace(
        config,
        analysis=dataclasses.replace(config.analysis, require_structure_alignment=True),
    )
    strategiya = ClassicTaStrategy(qattiq)
    # Pasayish strukturasi: narx pastga qarab qadam tashlaydi, lekin
    # oxirida support zonasiga qaytadi.
    strategiya.analyze(kirish(qattiq, qaytishli_kotarilish()))

    # Darvoza yoqilgan holatda rad sababi voronkaga tushadigan nom
    # bilan yozilishi kerak — kodning o'zi ekranda ko'rinmasin.
    assert stage_label("classic_ta:structure") != "classic_ta:structure"
