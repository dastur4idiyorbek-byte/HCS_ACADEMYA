"""3.1-band davomi: Discount / Premium zonalari.

Qat'iy qoida sinovi: Support yaqinida turgan narx ham, agar diapazonning
yuqori yarmida bo'lsa, kirish uchun to'liq kuchga ega EMAS.
"""

from __future__ import annotations

import pytest

from core.analysis.support_resistance import (
    EQUILIBRIUM_PCT,
    RangeBand,
    SupportResistanceDetector,
    compute_range_position,
)
from core.config.schema import SupportResistanceConfig
from core.domain.enums import ZoneKind
from core.domain.models import Candle, SRZone
from tests.core.test_support_resistance import sham


def diapazon_ichida_tugaydigan_qator() -> list[Candle]:
    """Narx 95 va 110 orasida bir necha marta tebranib, o'rtada tugaydi.

    Bunday shakl kerak, chunki `range_position` ikkala tomonda ham zona
    bo'lishini talab qiladi.
    """
    shamlar: list[Candle] = []
    index = 0
    for _ in range(3):
        for narx in (95, 99, 104, 108, 110, 108, 104, 99):
            shamlar.append(sham(index, narx + 1, narx - 1, narx))
            index += 1
    for narx in (101, 102, 101):
        shamlar.append(sham(index, narx + 1, narx - 1, narx))
        index += 1
    return shamlar

SUPPORT = SRZone(ZoneKind.SUPPORT, low=95, high=97, touches=3)      # markaz 96
RESISTANCE = SRZone(ZoneKind.RESISTANCE, low=113, high=115, touches=4)  # markaz 114


def joylashuv(price: float):  # noqa: ANN201
    return compute_range_position(price, SUPPORT, RESISTANCE)


# --------------------------------------------------------------------------- #
#  Foizni hisoblash
# --------------------------------------------------------------------------- #


def test_support_markazi_nol_foiz() -> None:
    assert joylashuv(96).percent == pytest.approx(0.0)


def test_resistance_markazi_yuz_foiz() -> None:
    assert joylashuv(114).percent == pytest.approx(100.0)


def test_orta_chiziq_ellik_foiz() -> None:
    assert joylashuv(105).percent == pytest.approx(EQUILIBRIUM_PCT)


def test_zonalar_markazi_boyicha_olchanadi() -> None:
    """Chekkalarni olish diapazonni zona kengligiga bog'liq qilib qo'yardi."""
    keng_support = SRZone(ZoneKind.SUPPORT, low=90, high=102, touches=3)  # markaz ham 96
    assert compute_range_position(105, keng_support, RESISTANCE).percent == pytest.approx(
        joylashuv(105).percent
    )


# --------------------------------------------------------------------------- #
#  Zona tasnifi
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("narx", "kutilgan"),
    [
        (96, RangeBand.DISCOUNT),
        (100, RangeBand.DISCOUNT),
        (104.9, RangeBand.DISCOUNT),
        (105, RangeBand.PREMIUM),
        (110, RangeBand.PREMIUM),
        (114, RangeBand.PREMIUM),
    ],
)
def test_zona_tasnifi(narx: float, kutilgan: RangeBand) -> None:
    assert joylashuv(narx).band is kutilgan


def test_chuqurlik_supportga_yaqinlashganda_oshadi() -> None:
    """Ball hisoblashda (3.5-band) chuqurroq Discount — yuqoriroq ball."""
    assert joylashuv(96).depth == pytest.approx(1.0)
    assert joylashuv(105).depth == pytest.approx(0.0)
    assert joylashuv(100).depth > joylashuv(103).depth


def test_premium_chuqurligi_resistancega_yaqinlashganda_oshadi() -> None:
    assert joylashuv(114).depth == pytest.approx(1.0)
    assert joylashuv(110).depth > joylashuv(106).depth


# --------------------------------------------------------------------------- #
#  Diapazondan chiqish
# --------------------------------------------------------------------------- #


def test_supportdan_pastga_tushish_yashirilmaydi() -> None:
    past = joylashuv(90)
    assert past.percent < 0
    assert past.is_outside_range
    assert "buzilgan" in past.describe()


def test_resistancedan_yuqoriga_chiqish_yashirilmaydi() -> None:
    baland = joylashuv(120)
    assert baland.percent > 100
    assert baland.is_outside_range
    assert "yorib o'tilgan" in baland.describe()


def test_diapazon_ichida_chiqish_belgilanmaydi() -> None:
    assert not joylashuv(100).is_outside_range


# --------------------------------------------------------------------------- #
#  QAT'IY QOIDA — kirish sharti
# --------------------------------------------------------------------------- #


def test_discount_va_support_zonasida_kirish_mumkin() -> None:
    assert joylashuv(96).allows_entry(price_in_support_zone=True)


def test_premium_zonada_kirish_rad_etiladi() -> None:
    """Narx Support yaqinida bo'lsa ham, Premium'da bo'lsa signal zaif."""
    assert not joylashuv(110).allows_entry(price_in_support_zone=True)


def test_support_zonasidan_tashqarida_kirish_rad_etiladi() -> None:
    """Discount'da bo'lish yetarli emas — narx aynan Support zonasida bo'lishi kerak."""
    assert not joylashuv(100).allows_entry(price_in_support_zone=False)


def test_diapazondan_chiqqanda_kirish_rad_etiladi() -> None:
    """Qo'llab-quvvatlash buzilgan — kirish asosi yo'qolgan (0.3-band)."""
    assert not joylashuv(90).allows_entry(price_in_support_zone=True)


def test_tor_oraliqda_narx_premiumda_bolishi_mumkin() -> None:
    """Spetsifikatsiyadagi aniq holat: oraliq juda tor.

    Narx Support zonasi ichida (97.5), lekin diapazon shunchalik torki, u
    allaqachon Premium yarmida turibdi -> kirish rad etiladi.
    """
    tor_support = SRZone(ZoneKind.SUPPORT, low=96, high=99, touches=3)   # markaz 97.5
    tor_resistance = SRZone(ZoneKind.RESISTANCE, low=99, high=101, touches=3)  # markaz 100

    joy = compute_range_position(98.9, tor_support, tor_resistance)
    assert joy.band is RangeBand.PREMIUM
    assert not joy.allows_entry(price_in_support_zone=True)


# --------------------------------------------------------------------------- #
#  Yaroqsiz diapazon
# --------------------------------------------------------------------------- #


def test_teskari_diapazon_none_qaytaradi() -> None:
    """Resistance Support'dan past — tahlil davom etmaydi (0.3-band)."""
    assert compute_range_position(100, RESISTANCE, SUPPORT) is None


def test_ustma_ust_zonalar_none_qaytaradi() -> None:
    bir_xil = SRZone(ZoneKind.SUPPORT, low=99, high=101, touches=2)
    assert compute_range_position(100, bir_xil, bir_xil) is None


# --------------------------------------------------------------------------- #
#  ZoneMap bilan birgalikda
# --------------------------------------------------------------------------- #


def test_zonemap_joylashuvni_hisoblaydi() -> None:
    detektor = SupportResistanceDetector(
        SupportResistanceConfig(swing_lookback=3, min_touches=2)
    )
    xarita = detektor.detect(diapazon_ichida_tugaydigan_qator())

    joy = xarita.range_position()
    assert joy is not None, f"ikkala tomonda zona kutilgan: {xarita.zones}"
    assert joy.support.center < xarita.price < joy.resistance.center
    assert 0 <= joy.percent <= 100


def test_zonemap_kirish_shartini_qollaydi() -> None:
    """Narx diapazon o'rtasida — Support zonasida emas, kirish rad etiladi."""
    detektor = SupportResistanceDetector(
        SupportResistanceConfig(swing_lookback=3, min_touches=2)
    )
    xarita = detektor.detect(diapazon_ichida_tugaydigan_qator())

    if xarita.zone_at_price() is None:
        assert not xarita.entry_allowed()


def test_bir_tomonda_zona_yoq_bolsa_swing_tayanchi_ishlatiladi() -> None:
    """Toza ko'tarilishda ustda qarshilik zonasi bo'lmaydi — trend degani shu.

    Bunday holatda diapazon chegarasi oxirgi muhim swing darajasidan
    olinadi. Aks holda tizim aynan trend filtri talab qiladigan sharoitda
    Discount/Premium ni umuman hisoblay olmasdi.
    """
    detektor = SupportResistanceDetector(
        SupportResistanceConfig(swing_lookback=3, min_touches=2)
    )
    shamlar = [sham(i, 100 + i * 2, 98 + i * 2, 99 + i * 2) for i in range(60)]
    xarita = detektor.detect(shamlar)

    assert xarita is not None
    if xarita.nearest_resistance() is None:
        assert xarita.swing_high is not None, "swing tayanchi saqlanishi kerak"
        assert xarita.range_position() is not None, "swing tayanchi bilan diapazon quriladi"


def test_swing_tayanchlari_saqlanadi() -> None:
    detektor = SupportResistanceDetector(
        SupportResistanceConfig(swing_lookback=3, min_touches=2)
    )
    xarita = detektor.detect(diapazon_ichida_tugaydigan_qator())

    assert xarita.swing_low is not None
    assert xarita.swing_high is not None
    assert xarita.swing_low < xarita.swing_high
