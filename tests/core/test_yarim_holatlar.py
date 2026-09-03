"""YARIM HOLATLAR — kod bir narsa qiladi, izoh boshqasini aytadi (audit, 3-bosqich).

Uchtasi ham gipoteza sifatida emas, NOMUVOFIQLIK sifatida topilgan.
Shuning uchun bu yerdagi testlar "qaysi variant yaxshi" degan
savolga javob bermaydi — ular MUAMMONING BORLIGINI va bayroq uni
haqiqatan o'zgartirishini qulflaydi. Qaysi biri yoqilishini
backtest hal qiladi.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.analysis.scoring.levels import build_levels
from core.analysis.support_resistance.detector import ZoneMap
from core.analysis.support_resistance.range_position import EQUILIBRIUM_PCT
from core.config import load_config
from core.domain.enums import ZoneKind
from core.domain.models import SRZone


@pytest.fixture
def config():
    return load_config()


# --------------------------------------------------------------------------- #
#  3.1 — TP1 poli tuzilmaviy zonaga
# --------------------------------------------------------------------------- #


def _xarita(resistance_low: float, price: float = 108_000.0) -> ZoneMap:
    zonalar = [
        SRZone(ZoneKind.SUPPORT, 105_800, 106_600, touches=4),
        SRZone(ZoneKind.RESISTANCE, resistance_low, resistance_low + 1_200, touches=3),
        SRZone(ZoneKind.RESISTANCE, 130_000, 131_000, touches=2),
    ]
    return ZoneMap(zones=zonalar, price=price, atr=1_600.0, proximity_atr=1.0)


def _qoidalar(config, **ozgarishlar):  # noqa: ANN001, ANN201
    from core.analysis.strategies.classic_ta import classic_ta_rules

    return dataclasses.replace(classic_ta_rules(config), **ozgarishlar)


def test_pol_yakuniy_nishondan_yuqori(config):
    """MUAMMONING ILDIZI: 2.0 > 1.5.

    Shu sababdan polga bo'ysungan TP1 doim yakuniy nishondan
    uzoqroq chiqadi va kod har safar BITTA TP li signal quradi.
    """
    assert (
        config.trade_rules.tp1_min_risk_reward
        > config.strategies.classic_ta.min_risk_reward
    )


def test_hozirgi_holatda_doim_bitta_tp(config):
    """Yaqin qarshilik zonasi TASHLAB YUBORILADI, TP bitta bo'lib qoladi."""
    natija = build_levels(_xarita(111_000), _qoidalar(config))
    assert natija.ok, natija.reason
    assert natija.levels.tp_count == 1


def test_pol_ochirilganda_ikkita_tp_qaytadi(config):
    """Bayroq HAQIQATAN o'zgartiradimi — shuni qulflaydi."""
    qoidalar = _qoidalar(config, tp1_ratio_tuzilmaviy_zonaga=False)
    natija = build_levels(_xarita(111_000), qoidalar)
    assert natija.ok, natija.reason
    assert natija.levels.tp_count == 2
    # Birinchi nishon endi haqiqiy zonaning pastki chetida.
    assert natija.levels.takes[0].price == pytest.approx(111_000)


def test_pol_ochirilsa_ham_olchangan_tarmoqda_ishlaydi(config):
    """Qarshilik topilmasa, o'lchangan TP baribir polga bo'ysunadi.

    Bayroq FAQAT tuzilmaviy filtrni o'chiradi — o'lchangan tarmoq
    tegilmaydi. Aks holda "TP1 juda yaqin" muammosi qaytardi.
    """
    qoidalar = _qoidalar(config, tp1_ratio_tuzilmaviy_zonaga=False)
    qarshiliksiz = ZoneMap(
        zones=[SRZone(ZoneKind.SUPPORT, 105_800, 106_600, touches=4)],
        price=108_000.0,
        atr=1_600.0,
        proximity_atr=1.0,
        swing_high=120_000.0,
    )
    natija = build_levels(qarshiliksiz, qoidalar)
    assert natija.ok, natija.reason
    stop_pct = (natija.levels.entry - natija.levels.stop) / natija.levels.entry * 100
    tp_pct = (
        (natija.levels.takes[0].price - natija.levels.entry)
        / natija.levels.entry
        * 100
    )
    assert tp_pct >= stop_pct * qoidalar.tp1_min_risk_reward - 1e-6


# --------------------------------------------------------------------------- #
#  3.2 — chuqurlik darvozadan
# --------------------------------------------------------------------------- #


def _joylashuv(equilibrium: float, price: float):  # noqa: ANN202
    zonalar = [
        SRZone(ZoneKind.SUPPORT, 96.0, 98.0, touches=3),
        SRZone(ZoneKind.RESISTANCE, 110.0, 112.0, touches=2),
    ]
    xarita = ZoneMap(
        zones=zonalar,
        price=price,
        atr=1.0,
        proximity_atr=5.0,
        equilibrium_pct=equilibrium,
    )
    return xarita.range_position()


def test_darvoza_va_ball_ajralgan(config):
    """50-55% oralig'idagi nomzod darvozadan o'tadi, ballda esa NOL oladi."""
    darvoza = config.analysis.support_resistance.entry_max_range_pct
    assert darvoza > EQUILIBRIUM_PCT, "muammo aynan shu farqda"

    # Diapazon 97 -> 111, ya'ni 14 birlik. 52% = 97 + 7.28
    joylashuv = _joylashuv(EQUILIBRIUM_PCT, 97.0 + 14.0 * 0.52)
    assert joylashuv.percent < darvoza, "darvozadan o'tadi"
    # `factors.py` chuqurlikni FAQAT Discount bo'lganda oladi:
    #     chuqurlik = joylashuv.depth if joylashuv.is_discount else 0.0
    # Ya'ni bu nomzod S/R omilining 35% ulushini butunlay yo'qotadi.
    assert not joylashuv.is_discount, "ballda Premium deb belgilanadi"


def test_darvozadan_hisoblanganda_chuqurlik_qoladi(config):
    darvoza = config.analysis.support_resistance.entry_max_range_pct
    joylashuv = _joylashuv(darvoza, 97.0 + 14.0 * 0.52)
    assert joylashuv.is_discount
    assert joylashuv.depth > 0.0


def test_chuqurlik_chegaralari_buzilmaydi(config):
    """Support'da 1.0, chegarada 0.0 — shkala o'zgarmasin."""
    for chegara in (EQUILIBRIUM_PCT, config.analysis.support_resistance.entry_max_range_pct):
        supportda = _joylashuv(chegara, 97.0)
        assert supportda.depth == pytest.approx(1.0)
        chegarada = _joylashuv(chegara, 97.0 + 14.0 * chegara / 100)
        assert chegarada.depth == pytest.approx(0.0, abs=1e-9)


def test_standart_holatda_eski_xatti_harakat(config):
    """Bayroq o'chiq — hech narsa o'zgarmasin."""
    assert config.analysis.support_resistance.chuqurlik_darvozadan is False


# --------------------------------------------------------------------------- #
#  3.3 — zona yagona manba
# --------------------------------------------------------------------------- #


def test_ikki_zona_ajralishi_mumkin():
    """`active_zone` va `nearest_support` boshqa zonani tanlashi mumkin.

    Saralash kalitlari boshqa: biri masofa bo'yicha eng yaqinini,
    ikkinchisi narxdan pastdagi eng yuqorisini oladi. Narx zonaning
    ICHIDA bo'lsa masofa nol bo'ladi va tartib ajraladi.
    """
    ichida = SRZone(ZoneKind.SUPPORT, 99.0, 101.0, touches=2)
    pastda = SRZone(ZoneKind.SUPPORT, 95.0, 96.0, touches=5)
    xarita = ZoneMap(
        zones=[ichida, pastda],
        price=100.0,
        atr=1.0,
        proximity_atr=1.0,
    )
    assert xarita.active_zone(ZoneKind.SUPPORT) is ichida
    assert xarita.nearest_support() is ichida
    # Narx zonadan chiqib ketganda ular ajralishi mumkin.
    tashqarida = dataclasses.replace(xarita, price=102.0)
    assert tashqarida.nearest_support() is ichida


def test_support_argumenti_stopni_ozgartiradi(config):
    """Uzatilgan zona HAQIQATAN Stopga ta'sir qilsin."""
    xarita = ZoneMap(
        zones=[
            SRZone(ZoneKind.SUPPORT, 99.0, 101.0, touches=2),
            SRZone(ZoneKind.SUPPORT, 90.0, 91.0, touches=5),
            SRZone(ZoneKind.RESISTANCE, 130.0, 131.0, touches=2),
        ],
        price=104.0,
        atr=1.0,
        proximity_atr=5.0,
    )
    qoidalar = _qoidalar(config)
    yaqin = build_levels(xarita, qoidalar)
    uzoq = build_levels(
        xarita, qoidalar, support=SRZone(ZoneKind.SUPPORT, 90.0, 91.0, touches=5)
    )
    assert yaqin.ok and uzoq.ok
    assert uzoq.levels.stop < yaqin.levels.stop


def test_standart_holatda_zona_qaytadan_qidiriladi(config):
    assert config.analysis.support_resistance.zona_yagona_manba is False


# --------------------------------------------------------------------------- #
#  3.4 — o'lik kod olib tashlandi
# --------------------------------------------------------------------------- #


def test_korreksiya_manbalari_olib_tashlandi():
    """Frozenset e'lon qilingan edi, kod esa satr taqqoslashdan foydalanardi."""
    from core.pipeline.cycle import SignalCycle

    assert not hasattr(SignalCycle, "KORREKSIYA_MANBALARI")


def test_past_band_hozirgi_sozlamada_erishib_bolmaydi(config):
    """`threshold_low_health` o'qilishi uchun `correction_entry` yoqilishi shart.

    Bu o'lik kod EMAS — o'chiq strategiya ostidagi kod. Farqi
    izohda ochiq yozilgan bo'lishi kerak, aks holda keyingi
    auditda yana "yarim holat" bo'lib qaytadi.
    """
    from pathlib import Path

    assert config.strategies.correction_entry.enabled is False
    manba = Path("core/pipeline/cycle.py").read_text(encoding="utf-8")
    assert "threshold_low_health" in manba, (
        "past bandning erishib bo'lmasligi izohda ochiq aytilsin"
    )
