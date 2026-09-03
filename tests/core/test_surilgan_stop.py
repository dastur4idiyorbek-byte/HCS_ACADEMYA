"""SURILGAN STOP — chiqish tomonining sinalmagan qismi (9-to'plam).

NIMA UCHUN BU YO'NALISH. O'n besh o'lchov davomida natijani FAQAT
bitta narsa qimirlatdi: TP1 nisbat poli (PF 0.30 -> 0.84). U chiqish
tomonida edi. Kirish tomonida sakkizta g'oya rad etildi va ikkita
butunlay boshqa mexanizm aynan bir xil natija berdi.

Bu testlar "surish foydalimi" degan savolga javob BERMAYDI — buni
faqat backtest aytadi. Ular MEXANIZM to'g'ri ishlashini qulflaydi:
Stop faqat yuqoriga suriladi, erta ishga tushmaydi, va o'chirilganda
hech narsa o'zgarmaydi.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from core.config import load_config
from core.config.schema import TrailingStopConfig
from core.domain.enums import SignalSource, SignalStatus
from core.domain.models import (
    Signal,
    SignalLevels,
    TakeProfit,
    signal_levels,
)
from core.signals import SignalTracker, kuzatuvchi_qur

#: Kirish 100, Stop 90 -> R = 10. Hisoblar shu ustida.
KIRISH = 100.0
STOP = 90.0
R = KIRISH - STOP


def _signal() -> Signal:
    return Signal(
        symbol="BTC",
        levels=signal_levels(KIRISH, STOP, 130.0),
        source=SignalSource.CLASSIC_TA,
        status=SignalStatus.ACTIVE,
    )


def _kuzatuvchi(**ozgarishlar) -> SignalTracker:  # noqa: ANN003
    return SignalTracker(trailing=TrailingStopConfig(enabled=True, **ozgarishlar))


def _narxlar(kuzatuvchi: SignalTracker, signal: Signal, *narxlar: float) -> None:
    kuzatuvchi.track(signal)
    boshi = datetime(2026, 1, 1, tzinfo=UTC)
    for i, narx in enumerate(narxlar):
        kuzatuvchi.on_price(signal.symbol, narx, boshi + timedelta(hours=4 * i))


# --------------------------------------------------------------------------- #
#  Mexanizm
# --------------------------------------------------------------------------- #


def test_ochiq_bolmasa_hech_narsa_ozgarmaydi():
    """Standart holat — surish yo'q, eski xatti-harakat aynan saqlanadi."""
    signal = _signal()
    kuzatuvchi = SignalTracker()
    _narxlar(kuzatuvchi, signal, 105.0, 115.0, 125.0)
    assert signal.trailing_stop is None
    assert signal.effective_stop == STOP


def test_faollashtirishdan_oldin_surilmaydi():
    """1R foydaga yetmagan narx Stopni qimirlatmasin.

    Erta surish oddiy shovqinni Stopga aylantiradi — bu tuzatish
    emas, savdoni erta o'ldirish bo'lardi.
    """
    signal = _signal()
    # 1R = 110. 109 hali yetarli emas.
    _narxlar(_kuzatuvchi(), signal, 105.0, 109.0)
    assert signal.trailing_stop is None
    assert signal.effective_stop == STOP


def test_faollashgach_choqqidan_orqada_turadi():
    signal = _signal()
    _narxlar(_kuzatuvchi(), signal, 110.0)
    # cho'qqi 110, trail 1R -> Stop 100
    assert signal.trailing_stop == pytest.approx(KIRISH)
    assert signal.effective_stop == pytest.approx(KIRISH)


def test_choqqi_osgan_sari_stop_ham_osadi():
    signal = _signal()
    _narxlar(_kuzatuvchi(), signal, 110.0, 120.0, 135.0)
    assert signal.peak_price == pytest.approx(135.0)
    assert signal.trailing_stop == pytest.approx(125.0)


def test_stop_HECH_QACHON_pastga_tushmaydi():
    """ENG MUHIM QOIDA.

    Stopni pastga tushirish foydalanuvchi rozi bo'lgan xavfni
    kattalashtirardi — ya'ni signal berilgandagi va'dani buzardi.
    """
    signal = _signal()
    kuzatuvchi = _kuzatuvchi()
    _narxlar(kuzatuvchi, signal, 130.0)
    eng_yuqori = signal.trailing_stop
    assert eng_yuqori == pytest.approx(120.0)

    # Narx qaytdi, lekin Stopga tegmadi.
    kuzatuvchi.on_price("BTC", 122.0, datetime(2026, 1, 2, tzinfo=UTC))
    assert signal.trailing_stop == pytest.approx(eng_yuqori)


def test_torroq_surish_stopni_yuqoriroq_qoyadi():
    keng, tor = _signal(), _signal()
    _narxlar(_kuzatuvchi(trail_r=1.0), keng, 130.0)
    _narxlar(_kuzatuvchi(trail_r=0.5), tor, 130.0)
    assert tor.trailing_stop > keng.trailing_stop


def test_kechroq_faollashish_surishni_kechiktiradi():
    erta, kech = _signal(), _signal()
    _narxlar(_kuzatuvchi(activate_at_r=1.0), erta, 112.0)
    _narxlar(_kuzatuvchi(activate_at_r=2.0), kech, 112.0)
    assert erta.trailing_stop is not None
    assert kech.trailing_stop is None


def test_surilgan_stopga_tegsa_savdo_yopiladi():
    # Nishon ataylab uzoqda: savdo TP bilan emas, SURILGAN STOP
    # bilan yopilishi kerak — aynan shu o'lchanayotgan mexanizm.
    signal = Signal(
        symbol="BTC",
        levels=signal_levels(KIRISH, STOP, 200.0),
        source=SignalSource.CLASSIC_TA,
        status=SignalStatus.ACTIVE,
    )
    kuzatuvchi = _kuzatuvchi()
    _narxlar(kuzatuvchi, signal, 130.0)
    assert signal.status is SignalStatus.ACTIVE

    hodisalar = kuzatuvchi.on_price("BTC", 119.0, datetime(2026, 1, 3, tzinfo=UTC))
    assert signal.status is SignalStatus.STOPPED
    assert hodisalar, "Stop hodisasi qayd etilsin"
    # Foyda bilan yopildi: surilgan Stop kirishdan yuqorida edi.
    assert signal.effective_stop > KIRISH


def test_kutilayotgan_signalda_surilmaydi():
    """Narx hali kirishga yetmagan — surishning ma'nosi yo'q."""
    signal = _signal()
    signal.status = SignalStatus.PENDING
    kuzatuvchi = _kuzatuvchi()
    kuzatuvchi.track(signal)
    kuzatuvchi.on_price("BTC", 130.0, datetime(2026, 1, 1, tzinfo=UTC))
    assert signal.trailing_stop is None


def test_buzuq_daraja_umuman_qurilmaydi():
    """R = 0 holati MODELNING O'ZIDA to'sib qo'yilgan.

    `_stopni_sur()` dagi `xavf <= 0` tekshiruvi shu sababdan
    HIMOYA QATLAMI: uni ishga tushiradigan daraja qurib bo'lmaydi.
    Test buni ochiq qayd etadi — aks holda keyingi o'quvchi
    tekshiruvni "keraksiz" deb olib tashlashi mumkin.
    """
    with pytest.raises(ValueError, match="Stop"):
        SignalLevels(entry=100.0, stop=100.0, takes=(TakeProfit(130.0, 100.0),))


# --------------------------------------------------------------------------- #
#  Sozlama bilan ulanish
# --------------------------------------------------------------------------- #


def test_standart_holatda_ochiq():
    config = load_config()
    assert config.trade_rules.trailing_stop.enabled is False


def test_fabrika_sozlamani_uzatadi():
    """Jonli tizim ham, backtest ham AYNI fabrikadan quriladi."""
    config = load_config()
    yoqilgan = dataclasses.replace(
        config,
        trade_rules=dataclasses.replace(
            config.trade_rules,
            trailing_stop=TrailingStopConfig(enabled=True, trail_r=0.5),
        ),
    )
    kuzatuvchi = kuzatuvchi_qur(yoqilgan)
    assert kuzatuvchi._trailing.enabled is True
    assert kuzatuvchi._trailing.trail_r == 0.5


def test_r_birligi_foizdan_mustaqil():
    """Narx miqyosi o'zgarsa ham natija AYNI R da bo'lsin.

    Foiz coinga bog'liq: BTC ning 3% i va meme coinning 3% i boshqa
    narsa. R esa har doim "bitta savdodagi xavf".
    """
    arzon = Signal(
        symbol="A",
        levels=signal_levels(1.0, 0.9, 1.3),
        source=SignalSource.CLASSIC_TA,
        status=SignalStatus.ACTIVE,
    )
    _narxlar(_kuzatuvchi(), arzon, 1.3)
    # R = 0.1, cho'qqi 1.3 -> Stop 1.2
    assert arzon.trailing_stop == pytest.approx(1.2)
