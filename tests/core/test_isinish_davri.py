"""Isinish davri indeksning ASOSIY omilini qamrab olsin.

MUAMMO. `_warmup_steps()` faqat `htf_confirmation` ni ko'rardi.
Bozor Salomatligi timeframei (`1w`) unda yo'q — indeks
strategiyadan tashqarida hisoblanadi. Natijada 730 kunlik sinovda
haftalik qatorda `min_candles` (60) shamga sinovning yarmidan
keyin yetilardi, undan oldin esa:

    universe_facts() -> bo'sh
    halal_structure_breadth -> 0.0  (vazn 45)
    volatility_regime       -> 0.0  (vazn 15)

Ya'ni indeksning 60 balli qismi ERISHIB BO'LMAYDIGAN edi va u
26-32 bandida qotib qolardi. Tizim ko'tarilayotgan bozorda
(tayanch +33.0%) "kasal" degan qarorni o'qirdi.

Bu 68, 69 va 79-bo'limlardagi backtest/jonli farqlarining
davomi. Test uni qaytib kelmasligi uchun qo'yilgan.
"""

from __future__ import annotations

import dataclasses

from core.backtest.warmup import warmup_days, warmup_steps, warmup_timeframes
from core.config import load_config
from core.utils.time_utils import TIMEFRAME_MINUTES


def test_salomatlik_timeframei_isinishda_bor() -> None:
    config = load_config()

    assert config.analysis.market_health_timeframe in warmup_timeframes(config)


def test_isinish_eng_yuqori_timeframega_yetadi() -> None:
    """Isinishdan keyin HAR BIR timeframeda `min_candles` sham bo'lsin."""
    config = load_config()
    kirish_daqiqa = TIMEFRAME_MINUTES[config.analysis.entry_timeframe]
    qadam = warmup_steps(config)

    for tf in warmup_timeframes(config):
        shamlar = qadam * kirish_daqiqa // TIMEFRAME_MINUTES[tf]
        assert shamlar >= config.analysis.indicators.min_candles, (
            f"{tf} timeframeda isinishdan keyin {shamlar} sham — "
            f"{config.analysis.indicators.min_candles} kerak"
        )


def test_isinish_kunlari_qadamlarni_qoplaydi() -> None:
    """Skript yuklaydigan qo'shimcha kun dvigatel tashlaydiganidan kam bo'lmasin.

    Kam bo'lsa `--days 730` jimgina 730 dan kichik oynaga aylanardi.
    """
    config = load_config()
    kirish_daqiqa = TIMEFRAME_MINUTES[config.analysis.entry_timeframe]

    kerakli_daqiqa = warmup_steps(config) * kirish_daqiqa
    yuklanadigan_daqiqa = warmup_days(config) * 1440

    assert yuklanadigan_daqiqa >= kerakli_daqiqa


def test_salomatlik_timeframei_ozgarsa_isinish_ham_ozgaradi() -> None:
    """Sozlama o'zgarsa hisob ergashsin — qotib qolgan raqam emas."""
    config = load_config()
    haftalik = warmup_steps(config)

    kunlik = warmup_steps(
        dataclasses.replace(
            config,
            analysis=dataclasses.replace(config.analysis, market_health_timeframe="1d"),
        )
    )

    assert haftalik > kunlik


def test_dvigatel_shu_hisobni_ishlatadi() -> None:
    """Dvigatel o'z nusxasini emas, shu funksiyani chaqirsin.

    Ikki joyda alohida hisoblanganda ular ajralib ketardi — 68-bo'lim
    aynan shundan tug'ilgan.
    """
    from core.backtest.engine import Backtester

    config = load_config()

    assert Backtester(config)._warmup_steps() == warmup_steps(config)
