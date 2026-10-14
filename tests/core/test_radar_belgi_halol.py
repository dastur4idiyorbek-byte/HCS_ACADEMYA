"""Modul 4.0.0 — belgi ajratish va halol reestr holati."""

from __future__ import annotations

import pytest

from core.config.schema import AppConfig
from core.portlash_radari import belgi
from core.portlash_radari.halol import BAHOLANMAGAN, HALOL, HAROM, SHUBHALI, Reestr


@pytest.mark.parametrize(
    ("asosiy", "kutilgan"),
    [
        ("1000PEPE", ("PEPE", 1000)),
        ("1000000MOG", ("MOG", 1_000_000)),
        ("1MBABYDOGE", ("BABYDOGE", 1_000_000)),
        ("1INCH", ("1INCH", 1)),
        ("LSK", ("LSK", 1)),
        ("1000", ("1000", 1)),
    ],
)
def test_kopaytirgich_ajratiladi(asosiy: str, kutilgan: tuple[str, int]) -> None:
    assert belgi.ajrat(asosiy) == kutilgan


def test_symbol_normallashadi() -> None:
    assert belgi.binance_symbol("lsk") == "LSKUSDT"
    assert belgi.binance_symbol(" LSKUSDT ") == "LSKUSDT"
    assert belgi.binance_symbol("lsk; drop table") is None
    assert belgi.binance_symbol("") is None
    assert belgi.symboldan_asosiy("1000PEPEUSDT") == "1000PEPE"


def test_reestr_yozilmaganni_halol_demaydi(config: AppConfig) -> None:
    """`verdict_for()` noma'lum coinga HALAL beradi — radar bermaydi."""
    r = Reestr({}, config)
    assert r.holati("NOMALUMCOIN") == BAHOLANMAGAN


def test_reestr_ustunlik_tartibi(config: AppConfig) -> None:
    """Haqiqiy `config/default.yaml` bilan — urug'lar va 80 talik o'sha yerdan."""
    r = Reestr({"LSK": "halal", "SOL": "haram", "ARB": "mashbooh"}, config)
    assert r.holati("lsk") == HALOL
    assert r.holati("SOL") == HAROM  # baza 80 talikdan ustun
    assert r.holati("ARB") == SHUBHALI
    assert r.holati("USDC") == SHUBHALI  # stablecoin
    assert r.holati("AAVE") == HAROM  # YAML urug'i
    assert r.holati("DOGE") == SHUBHALI  # YAML urug'i
    assert r.holati("ETH") == HALOL  # 80 talik ro'yxat
