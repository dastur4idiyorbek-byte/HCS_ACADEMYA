"""Backtest taqqoslash rejimi — brief talab qilgan MAJBURIY sinov.

`bozor_salomatligi_asosiy_tuzatish.md`: "hech qanday yangi qoida
sinovsiz jonli ishga tushirilmasin". Correction Entry shu sababdan
konfiguratsiyada o'chirilgan turibdi, uni faqat taqqoslash natijasi
yoqishi mumkin.

Bu testlar taqqoslashning O'ZINI tekshiradi — strategiyani emas.
Chunki oldingi versiyada taqqoslash butunlay ishlamas edi: variantlar
EMA davridan qolgan, allaqachon olib tashlangan sozlamaga murojaat
qilardi va `--compare` birinchi qadamda `TypeError` bilan tushardi.
Xato faqat tarmoqli mashinada, ma'lumot yuklab bo'lingandan keyin
ko'rinardi — ya'ni eng noqulay joyda.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from core.config import load_config
from scripts.backtest import (
    KeshYetishmaydi,
    _kerakli_timeframelar,
    _keshdan_yigish,
    _variantlar,
)


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


# --------------------------------------------------------------------------- #
#  Variantlar
# --------------------------------------------------------------------------- #


def test_variantlar_quriladi(config) -> None:  # noqa: ANN001
    """Har bir variant haqiqiy `AppConfig` bo'lishi kerak.

    Eski `_variantlar()` mavjud bo'lmagan maydonni o'zgartirmoqchi
    bo'lardi va aynan shu yerda tushardi.
    """
    variantlar = _variantlar(config)

    assert len(variantlar) >= 2
    for nom, variant in variantlar:
        assert nom, "har bir variantning nomi bo'lishi kerak"
        assert dataclasses.is_dataclass(variant)


def test_eski_va_yangi_tizim_taqqoslanadi(config) -> None:  # noqa: ANN001
    """Asosiy savol: past bandda to'xtashmi yoki Correction Entry?"""
    holatlar = {
        nom: variant.strategies.correction_entry.enabled
        for nom, variant in _variantlar(config)
    }

    assert any(not yoqilgan for yoqilgan in holatlar.values()), "eski tizim yo'q"
    assert any(holatlar.values()), "yangi tizim yo'q"


def test_variantlar_bir_biriga_tasir_qilmaydi(config) -> None:  # noqa: ANN001
    """Sozlama nusxalanadi, umumiy obyekt o'zgartirilmaydi.

    Aks holda ro'yxatdagi keyingi variant oldingisining sozlamasi
    bilan ishlab ketardi va taqqoslash yolg'on natija berardi.
    """
    variantlar = dict(_variantlar(config))
    rr = {
        nom: variant.strategies.correction_entry.min_risk_reward
        for nom, variant in variantlar.items()
    }

    assert len(set(rr.values())) > 1, "R/R variantlari o'lchanmayapti"
    assert config.strategies.correction_entry.min_risk_reward == 2.0, (
        "asos sozlama o'zgarmasligi kerak"
    )


def test_boshqa_sozlamalar_tegilmaydi(config) -> None:  # noqa: ANN001
    """Faqat `correction_entry` o'zgaradi — taqqoslash halol bo'lsin."""
    for _nom, variant in _variantlar(config):
        assert variant.strategies.classic_ta == config.strategies.classic_ta
        assert variant.trade_rules == config.trade_rules
        assert variant.market_health == config.market_health


# --------------------------------------------------------------------------- #
#  Ma'lumot: o'chirilgan strategiya ham timeframe talab qiladi
# --------------------------------------------------------------------------- #


def test_ochirilgan_strategiyaning_timeframei_ham_yuklanadi(config) -> None:  # noqa: ANN001
    """Bu — tizimdagi tuzoq.

    `correction_entry` konfiguratsiyada o'chirilgan. Agar ma'lumot
    faqat YOQILGAN strategiyalarga qarab yuklansa, taqqoslashda yangi
    variant uchun 4h/15m/1d shamlari umuman bo'lmasdi — u nol savdo
    qaytarardi va biz buni "strategiya yomon" deb o'qib qo'yardik.
    """
    ce = config.strategies.correction_entry
    assert not ce.enabled, "sinov shartini tekshiradi: strategiya o'chirilgan"

    timeframelar = _kerakli_timeframelar(config)

    assert ce.zone_timeframe in timeframelar
    assert ce.confirm_timeframe in timeframelar
    assert ce.trend_timeframe in timeframelar


# --------------------------------------------------------------------------- #
#  Offline rejim
# --------------------------------------------------------------------------- #


def test_offline_yetishmagan_fayllarni_aytadi(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    """Tarmoqsiz muhitda xato ANIQ bo'lishi kerak.

    "Yuklab bo'lmadi" degan umumiy xabar foydasiz — qaysi fayl
    yetishmayotgani aytilsa, uni boshqa mashinada yig'ib ko'chirish
    mumkin.
    """
    import scripts.backtest as bt

    monkeypatch.setattr(bt, "KESH", tmp_path / "candles")

    with pytest.raises(KeshYetishmaydi) as xato:
        _keshdan_yigish(["BTC", "ETH"], ["4h"])

    matn = str(xato.value)
    assert "BTC_4h.json" in matn
    assert "ETH_4h.json" in matn


def test_offline_keshdan_oqiydi(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    from datetime import UTC, datetime, timedelta

    import scripts.backtest as bt
    from core.domain.models import Candle

    kesh = tmp_path / "candles"
    monkeypatch.setattr(bt, "KESH", kesh)

    bosh = datetime(2025, 1, 1, tzinfo=UTC)
    shamlar = [
        Candle(
            open_time=bosh + timedelta(hours=4 * i),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
        )
        for i in range(5)
    ]
    bt._keshga_yozish("BTC", "4h", shamlar)

    dataset = _keshdan_yigish(["BTC"], ["4h"])

    assert dataset.symbols == ["BTC"]
    assert len(dataset.series["BTC"].candles["4h"]) == 5


# --------------------------------------------------------------------------- #
#  Uchidan uchiga: taqqoslash haqiqatda ishga tushadimi
# --------------------------------------------------------------------------- #


def test_har_bir_variant_backtestda_ishga_tushadi() -> None:
    """MEXANIZM sinovi — strategiyani baholash EMAS.

    Sun'iy qatorda chiqqan raqamlar hech narsani isbotlamaydi va ular
    tekshirilmaydi ham. Tekshiriladigan narsa bitta: `--compare`
    zanjiri boshidan oxirigacha uziladimi yoki yo'q. Eski versiyada
    aynan shu uzilardi va buni bilish uchun avval bir soatlik ma'lumot
    yuklash kerak bo'lardi.
    """
    import dataclasses as dc

    from core.analysis.strategies import build_strategies, required_timeframes
    from core.backtest import Backtester, build_dataset
    from tests.core.test_backtest import savdo_beradigan_qator, tez_config

    asos = tez_config()
    # Korreksiya strategiyasining timeframelari ham sinov qatoriga
    # moslashtiriladi, aks holda u ma'lumot yo'qligidan to'xtardi.
    ce = dc.replace(
        asos.strategies.correction_entry,
        zone_timeframe="15m",
        confirm_timeframe="15m",
        trend_timeframe="30m",
        impulse_lookback=30,
        confirm_lookback=10,
    )
    asos = dc.replace(
        asos, strategies=dc.replace(asos.strategies, correction_entry=ce)
    )

    kerakli = required_timeframes(build_strategies(asos, enabled_only=False))
    kerakli |= {asos.analysis.entry_timeframe, asos.analysis.market_health_timeframe}
    kerakli |= set(asos.analysis.htf_confirmation)
    dataset = build_dataset({"BTC": savdo_beradigan_qator()}, "15m", sorted(kerakli))

    for nom, variant in _variantlar(asos):
        natija = Backtester(variant, label=nom).run(dataset, max_steps=300)
        assert natija.label == nom
        assert natija.steps > 0, f"{nom}: birorta qadam bajarilmadi"
