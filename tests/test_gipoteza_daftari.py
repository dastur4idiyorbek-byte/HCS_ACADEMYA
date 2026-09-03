"""Gipoteza daftari kod bilan bir qadamda yursin.

MUAMMO. Tizimda uch xil raqam yonma-yon yashaydi va bir xil
ko'rinadi: FAKT (birja tarifi), QOIDA (loyiha egasining qarori) va
GIPOTEZA (hech kim o'lchamagan taxmin). Uchalasi ham
`config/default.yaml` da bir xil yotibdi.

Shuning uchun gipoteza jimgina "haqiqat"ga aylanib qoladi. Bugun
rad etilgan oltita gipoteza aynan shu sababdan tug'ilgan, va
loyihada bundan oldin ham xuddi shunday bo'lgan: BTC Dominance
vazni, Kill Zone bonusi, Correction Entry nisbati
(`docs/ARXITEKTURA.md`, 33, 67 va 77-bo'limlar).

Bu test daftarni MAJBURIY qiladi: yangi sozlama qo'shilsa, u
daftarda ham paydo bo'lishi kerak.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

LOYIHA = Path(__file__).resolve().parent.parent
DAFTAR = LOYIHA / "docs" / "GIPOTEZA_DAFTARI.md"

#: Daftarda BO'LMASLIGI mumkin bo'lgan sozlamalar.
#:
#: Bular raqam emas: nom, manzil, bayroq yoki tizimning ichki
#: tuzilishi. Ular haqida "to'g'rimi" degan savol qo'yilmaydi.
DAFTARSIZ = {
    # nom va manzillar
    "name", "default_language", "supported_languages", "quote_asset",
    "exchange", "ws_base_url", "rest_base_url", "ranking_source",
    "coinmarketcap_base_url", "coingecko_base_url", "level", "dir",
    "reference_symbol", "timezone", "allocation_method",
    # ro'yxatlar
    "stablecoin_symbols", "seed_haram_symbols", "seed_mashbooh_symbols",
    "timeframes", "htf_confirmation", "positional_timeframes",
    "exclude_health_factors", "fib_ratios", "fibonacci_levels",
    "correlation_groups", "symbols", "risk_tiers", "currencies",
    "tiers", "expiry_reminder_days", "suspend_risk_rules",
    # yoq/och bayroqlari — o'lchov emas, qaror
    "enabled", "exclude_stablecoins", "allow_measured_tp",
    "require_htf_alignment", "require_confirmation",
    "require_structure_alignment", "require_bos", "tp2_from_structure",
    # texnik chegaralar — bozor haqida emas
    "max_scan_depth", "refresh_interval_hours", "candles_lookback",
    "min_candles", "max_concurrent_candle_requests",
    "candle_page_pause_seconds", "stale_price_seconds",
    "max_candle_age_seconds",
    "stale_candle_multiplier", "reconnect_backoff_seconds",
    "retention_hours", "rotate_mb", "backups", "target_count",
    # timeframe tanlovi — qaror
    "entry_timeframe", "market_health_timeframe", "zone_timeframe",
    "confirm_timeframe", "trend_timeframe", "timeframe",
    # sana va muddat
    "boshlandi", "kunlar", "session_open_utc", "start_date",
    # post jadvali — bozor haqida emas, e'lon vaqti haqida
    "kunlik_soat_utc", "haftalik_kun", "haftalik_soat_utc",
}


def daftar_matni() -> str:
    assert DAFTAR.exists(), f"{DAFTAR} yo'q — gipoteza daftari ochilmagan"
    return DAFTAR.read_text(encoding="utf-8")


def config_kalitlari() -> set[str]:
    """`config/default.yaml` dagi barcha sozlama nomlari."""
    matn = (LOYIHA / "config" / "default.yaml").read_text(encoding="utf-8")
    kalitlar = set()
    for satr in matn.splitlines():
        moslik = re.match(r"^\s{2,}([a-z][a-z0-9_]*):", satr)
        if moslik:
            kalitlar.add(moslik.group(1))
    return kalitlar


# --------------------------------------------------------------------------- #
#  Daftar mavjud va o'qiladi
# --------------------------------------------------------------------------- #


def test_daftar_mavjud() -> None:
    matn = daftar_matni()

    assert "GIPOTEZA" in matn
    assert "rad etildi" in matn.lower() or "rad etilgan" in matn.lower()


def test_rad_etilganlar_yozilgan() -> None:
    """Bugungi oltita rad etish daftarda qolsin.

    Aks holda ular unutiladi va qaytadan sinaladi.
    """
    matn = daftar_matni()

    for gipoteza in (
        "correction_entry.enabled",
        "tp2_from_structure",
        "require_htf_alignment",
        "require_confirmation",
        "adx_trend_threshold",
        "entry_max_range_pct",
    ):
        assert gipoteza in matn, f"rad etilgan gipoteza daftarda yo'q: {gipoteza}"


def test_rad_etilgan_gipotezalar_yoqilmagan() -> None:
    """Daftar "rad etildi" desa, sozlama ham o'chiq turishi kerak.

    Ikkisi ajralib ketsa, daftar yolg'on gapiradigan hujjatga
    aylanadi.
    """
    from core.config import load_config

    config = load_config()

    # 2026-09-03 — eski tahlil moduli o'chirildi va u bilan birga
    # `strategies`, `trade_rules`, `analysis` bloklari ham ketdi.
    # Ular tekshiradigan rad etilgan gipotezalar endi KODDA emas,
    # faqat daftarda yashaydi: qayta yoqib bo'lmaydi, chunki qayta
    # yoqadigan sozlama yo'q.
    for eski in ("strategies", "trade_rules", "analysis", "market_health"):
        assert not hasattr(config, eski), (
            f"{eski} bloki qaytib kelibdi — rad etilgan gipotezalar "
            "bilan birga tekshiruv ham tiklanishi kerak"
        )


# --------------------------------------------------------------------------- #
#  Yangi raqam daftarsiz qo'shilmasin
# --------------------------------------------------------------------------- #


def test_har_bir_sozlama_daftarda_yoki_ro_yxatdan_tashqarida() -> None:
    """Config'ga yangi RAQAM qo'shilsa, u daftarda ham paydo bo'lsin.

    Bu test noqulay — shundayligicha qoladi. Yozilmagan taxmin bir
    oydan keyin haqiqatga o'xshab qoladi, va tuzatish o'shanda
    ancha qimmatga tushadi.
    """
    matn = daftar_matni()
    yetishmayapti = sorted(
        kalit
        for kalit in config_kalitlari()
        if kalit not in DAFTARSIZ and kalit not in matn
    )

    assert not yetishmayapti, (
        "Bu sozlamalar gipoteza daftarida yo'q:\n  "
        + "\n  ".join(yetishmayapti)
        + "\n\nHar birini `docs/GIPOTEZA_DAFTARI.md` ga qo'shing "
        "(🔴 o'lchanmagan), yoki raqam bo'lmasa `DAFTARSIZ` ga."
    )


@pytest.mark.parametrize(
    "belgi", ["\U0001f534", "\U0001f7e1", "\U0001f7e2", "\u26ab"]
)
def test_barcha_holatlar_ishlatilgan(belgi: str) -> None:
    """To'rt holatning har biri kamida bir marta uchrasin.

    Biri yo'qolsa — daftar bir tomonlama bo'lib qolgan degani.
    """
    assert daftar_matni().count(belgi) >= 2, (
        f"'{belgi}' holati faqat izohda bor, jadvalda ishlatilmagan"
    )
