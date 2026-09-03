"""6.1-band: plug-in arxitekturasi — strategiyalar registri.

Asosiy talab: yangi strategiya qo'shish uchun bitta fayl va bitta ro'yxat
yozuvi kifoya bo'lishi kerak. Signal sikli va Risk Engine o'zgarmaydi.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.analysis.strategies import (
    ClassicTaStrategy,
    OpeningRangeScalpStrategy,
    Strategy,
    StrategyInput,
    build_strategies,
    required_timeframes,
)
from core.config import load_config
from core.domain.models import SignalCandidate


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


def test_barcha_strategiyalar_quriladi(config) -> None:  # noqa: ANN001
    """YOQILGANLARI — konfiguratsiyaga qarab.

    Hozir bitta: `opening_range_scalp` o'chirildi (loyiha
    egasining qarori). O'LCHOV asos bo'ldi — oxirgi backtestda
    eng ko'p rad etish aynan o'sha strategiyadan chiqdi (16 473
    marta hajm sharti), signal esa deyarli bermasdi. 15 daqiqalik
    shamda narx chorak foiz yuradi, kelib-ketish xarajati esa
    0.3% — harakatning o'zi xarajatdan kichik.

    Registrda qoladi, faqat yoqilmaydi.
    """
    nomlar = {s.name for s in build_strategies(config)}
    assert nomlar == {"classic_ta"}


def test_skalp_registrda_bor_lekin_ochirilgan(config) -> None:  # noqa: ANN001
    """Kod o'chirilmaydi — bayroq o'chiriladi.

    Qaror o'lchovga tayangan va o'lchov qaytarilishi mumkin.
    Kodni o'chirib tashlasak, qaytarish uchun uni qaytadan yozish
    kerak bo'lardi.
    """
    hammasi = {s.name for s in build_strategies(config, enabled_only=False)}
    assert "opening_range_scalp" in hammasi
    assert config.strategies.opening_range_scalp.enabled is False


def test_correction_entry_registrda_bor_lekin_ochirilgan(config) -> None:  # noqa: ANN001
    """Brief talabi: "hech qanday yangi qoida sinovsiz jonli ishga
    tushirilmasin". Kod tayyor va registrda, lekin YOQILMAGAN."""
    hammasi = {s.name for s in build_strategies(config, enabled_only=False)}
    assert "correction_entry" in hammasi
    assert config.strategies.correction_entry.enabled is False, (
        "backtest tugamaguncha yoqilmasligi kerak"
    )


def test_ochirilgan_strategiya_royxatga_kirmaydi(config) -> None:  # noqa: ANN001
    ochiq = dataclasses.replace(config.strategies.opening_range_scalp, enabled=False)
    yangi = dataclasses.replace(
        config, strategies=dataclasses.replace(config.strategies, opening_range_scalp=ochiq)
    )

    assert {s.name for s in build_strategies(yangi)} == {"classic_ta"}
    # Registrda o'chirilganlari ham turadi: `correction_entry`,
    # `opening_range_scalp` va `narx_harakati`. Kod o'chirilmaydi —
    # bayroq o'chiriladi, chunki qaror O'LCHOVGA tayanadi va o'lchov
    # qaytarilishi mumkin.
    hammasi = {s.name for s in build_strategies(yangi, enabled_only=False)}
    assert hammasi == {
        "classic_ta",
        "opening_range_scalp",
        "correction_entry",
        "narx_harakati",
    }


def test_timeframelar_birlashtiriladi(config) -> None:  # noqa: ANN001
    """Har bir strategiya uchun alohida so'rov yuborilmasligi kerak."""
    strategiyalar = build_strategies(config)
    kerakli = required_timeframes(strategiyalar)

    for strategiya in strategiyalar:
        assert set(strategiya.required_timeframes()) <= kerakli


def test_barcha_strategiyalar_bir_xil_interfeysga_ega(config) -> None:  # noqa: ANN001
    """Risk Engine strategiya turini bilmasligi kerak."""
    for strategiya in build_strategies(config, enabled_only=False):
        assert isinstance(strategiya, Strategy)
        assert isinstance(strategiya.name, str)
        assert strategiya.required_timeframes()
        assert hasattr(strategiya, "analyze")


def test_yangi_strategiya_qoshish_bitta_faylda(config) -> None:  # noqa: ANN001
    """Interfeys yetarli darajada soddami — sinov strategiyasi bilan tekshiramiz."""

    class SinovStrategiyasi(Strategy):
        name = "sinov"

        def __init__(self, cfg) -> None:  # noqa: ANN001
            self._cfg = cfg

        @property
        def enabled(self) -> bool:
            return True

        def required_timeframes(self) -> list[str]:
            return ["1h"]

        def analyze(self, data: StrategyInput) -> SignalCandidate | None:
            return None

    strategiya = SinovStrategiyasi(config)
    assert isinstance(strategiya, Strategy)
    assert strategiya.analyze(
        StrategyInput(symbol="BTC", now=None, halal_verdict=None)  # type: ignore[arg-type]
    ) is None


def test_strategiyalar_bir_biriga_boglanmagan(config) -> None:  # noqa: ANN001
    """3.9-band: skalping asosiy strategiyadan MUSTAQIL."""
    klassik = ClassicTaStrategy(config)
    skalp = OpeningRangeScalpStrategy(config)

    assert set(klassik.required_timeframes()) != set(skalp.required_timeframes())
    assert skalp.daily_risk_share_pct > 0
    assert not hasattr(klassik, "daily_risk_share_pct"), (
        "asosiy strategiya alohida byudjet ulushiga ega emas"
    )
