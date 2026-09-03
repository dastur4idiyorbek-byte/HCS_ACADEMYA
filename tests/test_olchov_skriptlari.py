"""Ablation va walk-forward skriptlarining ARIFMETIKASI.

Backtestning o'zi bu yerda ishga tushirilmaydi — u tarixiy ma'lumot va
daqiqalar talab qiladi. Tekshiriladigan narsa boshqa: vazn almashtirish
to'g'ri hisoblanadimi, parametr to'ri to'liqmi, bo'laklar kesishmaydimi
va isinish har bo'lakka yetadimi.

Aynan shu joylarda jimgina xato bo'lishi mumkin: masalan ikkinchi bo'lak
birinchisining savdolarini ham sanab yuborsa, walk-forward "out-of-sample"
bo'lishdan to'xtaydi va hisobot yolg'on chiqadi.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.backtest import Dataset
from core.backtest.warmup import warmup_steps
from core.config import load_config
from core.domain.models import Candle
from scripts.ablation_test import OMILLAR, _nolga, _qayta_taqsim, _variantlar
from scripts.sinov_umumiy import USTUNLAR, Olchov, bolaklar, csv_saqla, jadval, kesim
from scripts.walk_forward import TOR_KICHIK, _joriy_nomzod, _qolla, _tor


@pytest.fixture
def config():
    return load_config()


# --------------------------------------------------------------------------- #
#  Ablation — vazn arifmetikasi
# --------------------------------------------------------------------------- #


def test_nolga_faqat_bitta_omilni_ochiradi(config):
    vaznlar = config.scoring.weights
    yangi = _nolga(vaznlar, "rsi")
    assert yangi.rsi == 0.0
    assert yangi.trend == vaznlar.trend
    assert yangi.total() == pytest.approx(vaznlar.total() - vaznlar.rsi)


@pytest.mark.parametrize("omil", list(OMILLAR))
def test_qayta_taqsim_shkalani_saqlaydi(config, omil):
    """Qayta taqsimlashda umumiy shkala 100 bo'lib qolishi SHART.

    Aks holda chegara (50/55) boshqa ma'no kasb etadi va ablation
    omilning o'rniga chegarani o'lchagan bo'lardi.
    """
    vaznlar = config.scoring.weights
    yangi = _qayta_taqsim(vaznlar, omil)
    assert getattr(yangi, omil) == 0.0
    assert yangi.total() == pytest.approx(vaznlar.total())


def test_qayta_taqsim_nisbatni_saqlaydi(config):
    """Qolgan omillarning BIR-BIRIGA nisbati o'zgarmaydi."""
    vaznlar = config.scoring.weights
    yangi = _qayta_taqsim(vaznlar, "macd")
    eski_nisbat = vaznlar.trend / vaznlar.rsi
    assert yangi.trend / yangi.rsi == pytest.approx(eski_nisbat)


def test_variantlar_tayanchdan_boshlanadi_va_hammasini_qamraydi(config):
    variantlar = _variantlar(config)
    assert variantlar[0][0] == "TAYANCH"
    assert variantlar[0][2] is config
    # tayanch + har bir omil uchun ikkita usul
    assert len(variantlar) == 1 + 2 * len(OMILLAR)


def test_ablation_faqat_vaznga_tegadi(config):
    """Chegaralar, risk qoidalari va strategiyalar o'zgarmasligi shart."""
    for _, _, variant in _variantlar(config):
        assert variant.scoring.thresholds == config.scoring.thresholds
        assert variant.trade_rules == config.trade_rules
        assert variant.strategies == config.strategies
        assert variant.analysis == config.analysis


# --------------------------------------------------------------------------- #
#  Walk-forward — parametr to'ri
# --------------------------------------------------------------------------- #


def test_tor_hajmi():
    assert len(_tor("kichik")) == 3 * 2 * 2
    assert len(_tor("toliq")) == 4 * 3 * 3
    assert len(set(_tor("toliq"))) == len(_tor("toliq"))


def test_joriy_qiymat_torda_bor(config):
    """Tayanch sozlama to'r ichida bo'lsin.

    Bo'lmasa qidiruv hozirgi sozlamani hech qachon tanlay olmaydi va
    "qidiruv tayanchdan yaxshi" degan xulosa noto'g'ri chiqardi.
    """
    joriy = _joriy_nomzod(config)
    assert joriy.tp1_min_risk_reward in TOR_KICHIK["tp1_min_risk_reward"]
    assert joriy.min_risk_reward in TOR_KICHIK["min_risk_reward"]
    assert joriy.entry_max_range_pct in TOR_KICHIK["entry_max_range_pct"]
    assert joriy in _tor("toliq")


def test_qolla_faqat_uchta_maydonni_ozgartiradi(config):
    nomzod = _tor("kichik")[0]
    yangi = _qolla(config, nomzod)
    assert yangi.trade_rules.tp1_min_risk_reward == nomzod.tp1_min_risk_reward
    assert yangi.strategies.classic_ta.min_risk_reward == nomzod.min_risk_reward
    assert (
        yangi.analysis.support_resistance.entry_max_range_pct
        == nomzod.entry_max_range_pct
    )
    # Ball tizimi va chegaralar tegilmagan
    assert yangi.scoring == config.scoring


def test_joriy_nomzodni_qollash_hech_narsani_ozgartirmaydi(config):
    """Tayanch yugurish AYNAN hozirgi sozlama bo'lsin."""
    assert _qolla(config, _joriy_nomzod(config)) == config


# --------------------------------------------------------------------------- #
#  Bo'laklar va kesim
# --------------------------------------------------------------------------- #


def _soxta_dataset(config, shamlar_soni: int) -> Dataset:
    """Faqat vaqt o'qi muhim — narxlar tekshiruvga ta'sir qilmaydi."""
    dataset = Dataset()
    boshi = datetime(2024, 1, 1, tzinfo=UTC)
    shamlar = [
        Candle(
            open_time=boshi + timedelta(hours=4 * i),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=10.0,
        )
        for i in range(shamlar_soni)
    ]
    dataset.add("BTC", config.analysis.entry_timeframe, shamlar)
    return dataset


def test_bolaklar_kesishmaydi(config):
    isinish = warmup_steps(config)
    dataset = _soxta_dataset(config, isinish + 300)
    qismlar = bolaklar(config, dataset, 3)

    assert len(qismlar) == 3
    for oldingi, keyingi in zip(qismlar, qismlar[1:], strict=False):
        assert oldingi.tahlil_oxiri < keyingi.tahlil_boshi


def test_har_bolakka_toliq_isinish_yetadi(config):
    """Kesim boshidan tahlil boshigacha AYNAN isinish qadamlari bo'lsin.

    Kam bo'lsa dvigatel bo'lakning boshini yeb qo'yadi, ko'p bo'lsa
    oldingi bo'lakning savdolari shu bo'lakka qo'shilib ketadi.
    """
    isinish = warmup_steps(config)
    dataset = _soxta_dataset(config, isinish + 300)
    entry_tf = config.analysis.entry_timeframe
    vaqtlar = dataset.timeline(entry_tf)

    for bolak in bolaklar(config, dataset, 3):
        qism = kesim(dataset, bolak.kesim_boshi, bolak.tahlil_oxiri)
        oyna = qism.timeline(entry_tf)
        assert oyna[isinish] == bolak.tahlil_boshi
        assert oyna[-1] == bolak.tahlil_oxiri
        assert bolak.kesim_boshi in vaqtlar


def test_bolaklar_malumot_yetmasa_toxtaydi(config):
    dataset = _soxta_dataset(config, warmup_steps(config) + 4)
    with pytest.raises(SystemExit):
        bolaklar(config, dataset, 3)


# --------------------------------------------------------------------------- #
#  Hisobot
# --------------------------------------------------------------------------- #


def _olchov(nom: str, pf: float | None) -> Olchov:
    return Olchov(
        nom=nom,
        izoh="sinov",
        signal=42,
        foydali_pct=28.9,
        profit_factor=pf,
        ortacha_savdo_pct=-0.46,
        jami_pct=-19.3,
        pasayish_pct=45.1,
    )


def test_jadval_bosh_qiymatlarda_yiqilmaydi():
    matn = jadval([_olchov("a", None)], "omil", "usul")
    assert "—" in matn
    assert "a" in matn


def test_csv_ustunlari_qatorga_mos():
    qator = _olchov("a", 0.84).csv_qatori()
    assert tuple(qator) == USTUNLAR


def test_csv_saqlanadi(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.sinov_umumiy.HISOBOT_PAPKA", tmp_path / "reports")
    yol = csv_saqla("sinov.csv", [_olchov("a", 0.84), _olchov("b", None)])
    satrlar = yol.read_text(encoding="utf-8").strip().splitlines()
    assert satrlar[0] == ",".join(USTUNLAR)
    assert len(satrlar) == 3
    # PF yo'q bo'lsa katak BO'SH qoladi, 0 emas — nol PF boshqa ma'no.
    assert satrlar[2].split(",")[4] == ""
