"""3.10-band: Correction Entry — pasayishdagi tuzilmaviy kirish.

Bu strategiya AYNAN o'sha paytda ishlaydi, qachonki eski tizim ko'zini
yumardi. Ya'ni uning darvozalari nozik: bittasi bo'shashsa, tizim
tushayotgan bozorda xarid qila boshlaydi.

Shuning uchun har bir darvoza alohida sinaladi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.analysis.strategies.base import StrategyInput
from core.analysis.strategies.correction_entry import CorrectionEntryStrategy
from core.config import load_config
from core.domain.enums import HalalStatus, SignalSource
from core.domain.models import Candle, HalalVerdict

BOSH = datetime(2026, 9, 1, tzinfo=UTC)
HALOL = HalalVerdict("BTC", HalalStatus.HALAL, "halol")


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


@pytest.fixture
def strategiya(config):  # noqa: ANN001, ANN201
    return CorrectionEntryStrategy(config)


def sham(i: int, o: float, h: float, low: float, c: float) -> Candle:
    return Candle(
        open_time=BOSH + timedelta(hours=i),
        open=o,
        high=h,
        low=low,
        close=c,
        volume=1000.0,
    )


def kotarilish(n: int = 30, boshi: float = 100.0, qadam: float = 2.0) -> list[Candle]:
    """Aniq ko'tarilish — HH/HL ketma-ketligi."""
    shamlar = []
    narx = boshi
    for i in range(n):
        # Har uchinchi sham kichik qaytish beradi — swinglar hosil bo'lsin
        yuqori = narx + qadam if i % 3 else narx + qadam * 0.4
        shamlar.append(sham(i, narx, yuqori + 0.5, narx - 0.5, yuqori))
        narx = yuqori
    return shamlar


def pasayish(n: int = 30, boshi: float = 200.0, qadam: float = 2.0) -> list[Candle]:
    shamlar = []
    narx = boshi
    for i in range(n):
        past = narx - qadam if i % 3 else narx - qadam * 0.4
        shamlar.append(sham(i, narx, narx + 0.5, past - 0.5, past))
        narx = past
    return shamlar


def korreksiyali_zona() -> list[Candle]:
    """Impuls + korreksiya: Fibonacci va Order Block bir joyda.

    100 dan 145 gacha ko'tarilish, impuls oldida Order Block
    (tanasi 121-124). Fibonacci "oltin zonasi" va OB kesishmasi
    121-124 — kirish zonasi. Narx shu zonaga qaytadi.

    Cho'qqi NEGA 145: TP2 aynan cho'qqiga qo'yiladi va u kirishdan
    `max_tp_distance_pct` (20%) dan uzoq bo'lmasligi kerak. Ilgari
    bu yerda 150 turardi — ya'ni "ijobiy yo'l" testi haqiqatda
    Risk Engine'dan o'tolmaydigan signalni tekshirardi.
    """
    return [
        sham(0, 100, 110, 99.5, 110),
        sham(1, 110, 120.5, 109, 120),
        # ORDER BLOCK: tushuvchi sham, tanasi 121-124
        sham(2, 124, 124.6, 120.4, 121),
        # Impuls yuqoriga
        sham(3, 121, 133, 120.9, 132),
        sham(4, 132, 143, 131, 142),
        sham(5, 142, 145, 141, 144),   # cho'qqi 145
        # Korreksiya pastga — zonaga qaytadi
        sham(6, 144, 144.5, 140, 141),
        sham(7, 141, 142, 130, 131),
        sham(8, 131, 131.5, 123.5, 124),
        sham(9, 124, 124.4, 123.2, 123.8),  # zona ichida, tepasiga yaqin
    ]


def pastki_tf_tasdigi() -> list[Candle]:
    """15m: zona ichida mini Order Block — qaytish belgisi.

    Yuqori TF zonasi katta (121-124), aniq nuqta esa faqat shu yerda
    ko'rinadi: narx zona ichida tushib, o'sha yerdan qaytgan.
    """
    return [
        sham(0, 124, 124.2, 123.6, 123.8),
        sham(1, 123.8, 124.0, 123.4, 123.5),
        # mini OB: tushuvchi sham
        sham(2, 123.5, 123.6, 122.8, 123.0),
        # keyin qaytish (0.5% dan katta harakat)
        sham(3, 123.0, 124.2, 122.9, 124.0),
        sham(4, 124.0, 124.5, 123.7, 123.8),
    ]


def kirish(
    zona: list[Candle],
    trend: list[Candle],
    tasdiq: list[Candle] | None = None,
) -> StrategyInput:
    return StrategyInput(
        symbol="BTC",
        now=BOSH + timedelta(days=1),
        halal_verdict=HALOL,
        candles={
            "4h": zona,
            "1d": trend,
            "15m": tasdiq if tasdiq is not None else pastki_tf_tasdigi(),
        },
    )


# --------------------------------------------------------------------------- #
#  YO'NALISH DARVOZASI — yagona murosasiz shart
# --------------------------------------------------------------------------- #


def test_pasayishdagi_bozorda_signal_berilmaydi(strategiya) -> None:  # noqa: ANN001
    """Tushayotgan bozorda "arzon" degan narsa yo'q: narx yana ham
    arzonlashaveradi. Spot xaridida bu eng qimmat xato."""
    natija = strategiya.analyze(kirish(korreksiyali_zona(), pasayish()))

    assert natija is None
    assert strategiya.last_rejection.stage == "trend"
    assert "ko'tarilishda emas" in strategiya.last_rejection.detail


def test_harom_coin_otmaydi(strategiya) -> None:  # noqa: ANN001
    data = kirish(korreksiyali_zona(), kotarilish())
    data.halal_verdict = HalalVerdict("BTC", HalalStatus.HARAM, "harom")

    assert strategiya.analyze(data) is None
    assert strategiya.last_rejection.stage == "halal"


def test_malumot_yetmasa_toxtaydi(strategiya) -> None:  # noqa: ANN001
    assert strategiya.analyze(kirish([], kotarilish())) is None
    assert strategiya.last_rejection.stage == "data"


# --------------------------------------------------------------------------- #
#  KORREKSIYA VA CONFLUENCE
# --------------------------------------------------------------------------- #


def test_narx_hali_choqqida_bolsa_kirilmaydi(strategiya) -> None:  # noqa: ANN001
    """Korreksiya boshlanmagan bo'lsa, kirish nuqtasi ham yo'q —
    bu strategiyaning butun mazmuni korreksiyani KUTISHDA."""
    natija = strategiya.analyze(kirish(kotarilish(), kotarilish()))

    assert natija is None
    assert strategiya.last_rejection.stage in {"retracement", "confluence", "impulse"}


def test_bitta_manba_yetarli_emas(config) -> None:  # noqa: ANN001
    """Beshta usuldan bittasi har doim mos keladi — bu tarixga
    moslashib qolish bo'lardi. Kamida ikki mustaqil manba kerak."""
    import dataclasses

    qattiq = dataclasses.replace(
        config,
        strategies=dataclasses.replace(
            config.strategies,
            correction_entry=dataclasses.replace(
                config.strategies.correction_entry, min_confluence=3
            ),
        ),
    )
    yumshoq = dataclasses.replace(
        config,
        strategies=dataclasses.replace(
            config.strategies,
            correction_entry=dataclasses.replace(
                config.strategies.correction_entry, min_confluence=1
            ),
        ),
    )

    data = kirish(korreksiyali_zona(), kotarilish())
    natija_qattiq = CorrectionEntryStrategy(qattiq).analyze(data)
    s2 = CorrectionEntryStrategy(yumshoq)
    s2.analyze(kirish(korreksiyali_zona(), kotarilish()))

    # Qattiq talab bilan o'tmaydi; bosqich nomi confluence bo'lishi kerak
    assert natija_qattiq is None


# --------------------------------------------------------------------------- #
#  PASTKI TF TASDIG'I
# --------------------------------------------------------------------------- #


def test_pastki_tf_malumoti_yoq_bolsa_kirilmaydi(strategiya) -> None:  # noqa: ANN001
    """Noaniqlikda kirmaymiz (0.3-band): zona katta, aniq nuqta esa
    faqat pastki TF da ko'rinadi."""
    natija = strategiya.analyze(
        kirish(korreksiyali_zona(), kotarilish(), tasdiq=[])
    )

    assert natija is None
    assert strategiya.last_rejection.stage in {"confirm", "confluence", "zone_position"}


# --------------------------------------------------------------------------- #
#  DARAJALAR — Entry va Stop BIR XIL manbadan
# --------------------------------------------------------------------------- #


def test_signal_chiqadi_va_stop_zona_ostida_turadi(strategiya) -> None:  # noqa: ANN001
    """ASOSIY TAMOYIL: Stop qat'iy foiz emas, zonaning tashqi chekkasi.

    Zona buzilsa, uni yaratgan tuzilma ham buzilgan va kirish sababi
    qolmaydi — Stop aynan shu yerda bo'lishi kerak.
    """
    natija = strategiya.analyze(kirish(korreksiyali_zona(), kotarilish()))

    assert natija is not None, f"signal kutilgandi: {strategiya.last_rejection}"
    assert natija.source is SignalSource.CORRECTION_ENTRY

    lv = natija.levels
    # Kirish zonasi 121-124, ya'ni Stop 121 dan sal pastda
    assert 120.0 < lv.stop < 121.0
    assert lv.entry > lv.stop
    assert lv.tp1 < lv.final_tp
    # TP2 — impuls cho'qqisi (tuzilmadan, o'ylab topilgan foiz emas)
    assert lv.final_tp == 145.0


def test_ball_confluence_va_korreksiyadan_chiqadi(strategiya) -> None:  # noqa: ANN001
    natija = strategiya.analyze(kirish(korreksiyali_zona(), kotarilish()))
    assert natija is not None

    nomlar = {c.name for c in natija.breakdown.components}
    assert nomlar == {"confluence", "retracement", "risk_reward", "rsi"}

    conf = next(c for c in natija.breakdown.components if c.name == "confluence")
    assert "Fibonacci" in conf.explanation
    assert "Order Block" in conf.explanation


def test_juda_tor_tuzilmaviy_stop_rad_etiladi(config) -> None:  # noqa: ANN001
    """Stop TUZILMADAN chiqadi — bu o'zgarmaydi. Lekin tuzilma juda
    tor bo'lsa (masalan 0.5%), uni oddiy bozor shovqini yeb qo'yadi.

    Bunday holatda Stop KENGAYTIRILMAYDI — kengaytirilgan Stop endi
    hech narsani anglatmaydi. Nomzod rad etiladi.
    """
    import dataclasses

    # Chegarani ko'tarib, mavjud 2.41% lik Stopni "juda yaqin" qilamiz
    qattiq = dataclasses.replace(
        config,
        trade_rules=dataclasses.replace(config.trade_rules, min_stop_distance_pct=5.0),
    )
    s = CorrectionEntryStrategy(qattiq)
    natija = s.analyze(kirish(korreksiyali_zona(), kotarilish()))

    assert natija is None
    assert s.last_rejection.stage == "levels:stop_too_close"


def test_juda_uzoq_stop_ham_rad_etiladi(config) -> None:  # noqa: ANN001
    import dataclasses

    qattiq = dataclasses.replace(
        config,
        trade_rules=dataclasses.replace(config.trade_rules, max_stop_distance_pct=1.0),
    )
    s = CorrectionEntryStrategy(qattiq)
    natija = s.analyze(kirish(korreksiyali_zona(), kotarilish()))

    assert natija is None
    assert s.last_rejection.stage == "levels:stop_too_far"


def test_nisbat_yetmasa_signal_yoq(config) -> None:  # noqa: ANN001
    """R/R talabini juda baland qo'ysak, signal chiqmasligi kerak —
    ya'ni nisbat HAQIQATAN tekshirilyapti."""
    import dataclasses

    imkonsiz = dataclasses.replace(
        config,
        strategies=dataclasses.replace(
            config.strategies,
            correction_entry=dataclasses.replace(
                config.strategies.correction_entry, min_risk_reward=100.0
            ),
        ),
    )
    s = CorrectionEntryStrategy(imkonsiz)
    natija = s.analyze(kirish(korreksiyali_zona(), kotarilish()))

    assert natija is None


# --------------------------------------------------------------------------- #
#  Shartnoma
# --------------------------------------------------------------------------- #


def test_strategiya_plugin_shartnomasiga_mos(strategiya, config) -> None:  # noqa: ANN001
    """6.1-band: barcha strategiyalar bir xil interfeysga ega."""
    assert strategiya.name == "correction_entry"
    assert strategiya.enabled is config.strategies.correction_entry.enabled

    tf = strategiya.required_timeframes()
    assert len(tf) == len(set(tf)), "timeframelar takrorlanmasligi kerak"
    assert config.strategies.correction_entry.confirm_timeframe in tf


# --------------------------------------------------------------------------- #
#  Risk Engine bilan bir xil raqamga tayanadimi
# --------------------------------------------------------------------------- #


def test_risk_engine_strategiyaning_nisbatini_qollaydi(config) -> None:  # noqa: ANN001
    """Darajalarni QURGAN va TEKSHIRGAN raqam bitta bo'lishi SHART.

    Bu ulanish yo'q edi: strategiya `min_risk_reward=2.0` deb ishlardi,
    Risk Engine esa unga global 3.0 ni qo'llardi. Ya'ni 1:2 va 1:3
    orasidagi HAR BIR nomzod strategiyadan o'tib, keyingi qadamda
    jimgina yo'q qilinardi — sozlamadagi 2.0 raqami mavjud, lekin
    hech qachon amalda ishlamasdi.
    """
    from core.domain.enums import SignalSource
    from core.risk_engine.engine import build_default_rules

    qoida = next(q for q in build_default_rules(config) if q.name == "trade_rules")
    _min_tp, _max_tp, min_rr, _min_stop = qoida._bounds_for(SignalSource.CORRECTION_ENTRY)

    assert min_rr == config.strategies.correction_entry.min_risk_reward


def test_tuzilmaviy_signal_risk_engineda_bloklanmaydi(strategiya, config) -> None:  # noqa: ANN001
    """Uchidan uchiga: strategiya bergan nomzod Risk Engine'dan o'tadi.

    Alohida-alohida to'g'ri ishlaydigan ikki qism birga ishlamasligi
    mumkin. Bu yerda aynan shu tekshiriladi — chunki ilgari ishlamasdi.
    """
    from core.domain.enums import SignalSource
    from core.risk_engine.engine import build_default_rules

    nomzod = strategiya.analyze(kirish(korreksiyali_zona(), kotarilish()))
    assert nomzod is not None, "sinov shartini tekshiradi: nomzod bo'lishi kerak"
    assert nomzod.source is SignalSource.CORRECTION_ENTRY

    qoida = next(q for q in build_default_rules(config) if q.name == "trade_rules")
    qaror = qoida.check(nomzod, None)

    assert qaror.allowed, "; ".join(qaror.details)


def test_tp_quyi_chegarasi_tuzilmadan_hisoblanadi(config) -> None:  # noqa: ANN001
    """TP chegarasi o'ylab topilmaydi — sozlamadan CHIQARIB olinadi.

    Global 3% `classic_ta` uchun (TP 3–5%). Bu yerda TP2 impuls
    cho'qqisi, TP1 esa yo'lning yarmida — demak eng kichik TP1 =
    eng kichik Stop x nisbat / 2. Sozlama o'zgarsa chegara ergashadi.
    """
    import dataclasses

    from core.analysis.strategies.correction_entry import correction_entry_trade_rules

    min_tp, _max_tp, _rr, _min_stop = correction_entry_trade_rules(config)
    kutilgan = (
        config.trade_rules.min_stop_distance_pct
        * config.strategies.correction_entry.min_risk_reward
        / 2
    )
    assert min_tp == kutilgan

    qattiqroq = dataclasses.replace(
        config,
        strategies=dataclasses.replace(
            config.strategies,
            correction_entry=dataclasses.replace(
                config.strategies.correction_entry, min_risk_reward=4.0
            ),
        ),
    )
    yangi_min_tp, _, yangi_rr, _ = correction_entry_trade_rules(qattiqroq)

    assert yangi_rr == 4.0
    assert yangi_min_tp > min_tp, "chegara sozlamaga ergashishi kerak"
