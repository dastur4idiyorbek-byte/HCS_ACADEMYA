"""Ishonch filtri uchun testlar."""

from __future__ import annotations

from core.utils.confidence_filter import PENDING, IshonchFiltri


def test_pending_passiv() -> None:
    filtr = IshonchFiltri(PENDING)
    assert not filtr.faol()
    assert filtr.otkazadi(0.0)
    assert filtr.otkazadi(1.0)


def test_chegara_bilan_filtrlaydi() -> None:
    filtr = IshonchFiltri(0.6)
    assert filtr.faol()
    assert filtr.otkazadi(0.6)
    assert filtr.otkazadi(0.9)
    assert not filtr.otkazadi(0.59)


def test_nol_chegara_passiv() -> None:
    filtr = IshonchFiltri(0.0)
    assert not filtr.faol()
    assert filtr.otkazadi(0.0)
