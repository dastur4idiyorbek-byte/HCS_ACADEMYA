"""Struktura — coin yoshi bo'yicha timeframe tanlash."""

from __future__ import annotations

from core.analysis.structure.structure_block import timeframelar_yosh_uchun


def test_yangi_coin_faqat_4h() -> None:
    assert timeframelar_yosh_uchun(30) == ["4h", "15m"]


def test_yarim_yetuk_1d_4h() -> None:
    assert timeframelar_yosh_uchun(200) == ["1d", "4h", "15m"]


def test_yetuk_toliq_4_tf() -> None:
    assert timeframelar_yosh_uchun(400) == ["1w", "1d", "4h", "15m"]


def test_yosh_nomalum_yetuk_deb_qaraladi() -> None:
    assert timeframelar_yosh_uchun(None) == ["1w", "1d", "4h", "15m"]
