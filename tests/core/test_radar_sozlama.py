"""Modul 4.0.0 — chegaralar: YAML + admin o'zgarishi, sayt bilan bir xil oraliq."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.config.loader import _build, radar_muammolari, validate
from core.config.schema import RADAR_BUTUN_KALITLAR, RADAR_ORALIQLARI, AppConfig, RadarConfig
from core.portlash_radari.sozlama import chegaralar_qur, qiymat_xatosi

ILDIZ = Path(__file__).resolve().parents[2]
SAYT = ILDIZ / "web" / "src" / "lib" / "radar.ts"


def test_yaml_standart_hujjat_bilan_bir_xil(config: AppConfig) -> None:
    """`docs/MODUL_4_0_0.md` 15-bo'lim jadvali."""
    r = config.radar
    assert (r.min_kapitalizatsiya_usd, r.min_hajm_24s_usd) == (10e6, 500e3)
    assert (r.elak_hajm_x, r.hajm_x, r.narx_ozgarish_pct, r.funding_8s_pct) == (3, 5, 20, 0.1)
    assert (r.oi_osish_pct, r.oi_oyna_soat, r.long_short_nisbat, r.btc_farq_pp) == (
        30, 8, 2.5, 15
    )
    assert (r.aylanma_max_pct, r.unlock_kun, r.unlock_min_pct) == (60, 7, 5)
    assert (r.nomzod_min, r.top_n, r.namuna_soni) == (4, 10, 10)
    assert (r.kashfiyot_daqiqa, r.tasdiq_daqiqa) == (60, 15)
    assert r.vaqt_zonasi == "Asia/Bishkek"


def test_ozgarish_standartni_bosadi_yaroqsizi_tashlanadi() -> None:
    ch, ogohlar = chegaralar_qur(
        RadarConfig(),
        {"hajm_x": 7.0, "nomzod_min": 4.5, "top_n": 1000, "begona": 1.0},
    )
    assert ch.hajm_x == 7.0
    assert ch.nomzod_min == 4 and isinstance(ch.nomzod_min, int)
    assert ch.top_n == 10
    assert len(ogohlar) == 3


@pytest.mark.parametrize("qiymat", [float("nan"), float("inf"), "abc", None])
def test_son_bolmagan_qiymat_rad_etiladi(qiymat: object) -> None:
    assert qiymat_xatosi("hajm_x", qiymat) is not None  # type: ignore[arg-type]


def test_yaml_oraliqdan_chiqsa_radar_tekshiruvi_ushlaydi() -> None:
    assert any("radar.nomzod_min" in m for m in radar_muammolari(
        _build(AppConfig, {"radar": {"nomzod_min": 9}})
    ))
    assert any("tasdiq_daqiqa" in m for m in radar_muammolari(
        _build(AppConfig, {"radar": {"tasdiq_daqiqa": 70}})
    ))
    assert radar_muammolari(_build(AppConfig, {})) == []


def test_radar_xatosi_bot_va_seedni_toxtatmaydi() -> None:
    """Radar faqat sayt uchun va mustaqil: uning sozlama xatosi umumiy
    `validate()` ni yiqitmasligi kerak — aks holda `start.sh` dagi seed
    qadami yiqilib, bot va sayt ham ko'tarilmasdi."""
    validate(_build(AppConfig, {"radar": {"nomzod_min": 9, "kashfiyot_kechikish_daqiqa": 45}}))


async def test_radar_jarayoni_xato_sozlamada_1_qaytaradi(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    from core.portlash_radari import __main__ as kirish

    yaml_fayl = tmp_path / "c.yaml"
    yaml_fayl.write_text("radar:\n  nomzod_min: 9\n", encoding="utf-8")
    monkeypatch.setenv("HCS_CONFIG_FILE", str(yaml_fayl))
    assert await kirish.ishga_tushir() == 1


def test_sayt_oraliqlari_bilan_bir_xil() -> None:
    """Admin saytda kiritgan qiymatni sayt ham, bot ham BIR XIL oraliqqa
    qarab tekshirishi kerak. Ikki joyda yozilgan ro'yxat ajralib ketmasin."""
    matn = SAYT.read_text(encoding="utf-8")
    blok = re.search(r"SOZLAMA_ORALIQLARI[^=]*=\s*\{(.*?)\};", matn, re.S)
    assert blok, "radar.ts da SOZLAMA_ORALIQLARI topilmadi"
    sayt = {
        k: (float(a), float(b))
        for k, a, b in re.findall(r"(\w+):\s*\[\s*([\d.e+-]+)\s*,\s*([\d.e+-]+)\s*\]", blok.group(1))
    }
    assert sayt == RADAR_ORALIQLARI

    butun = re.search(r"BUTUN_KALITLAR[^=]*=\s*\[(.*?)\]", matn, re.S)
    assert butun, "radar.ts da BUTUN_KALITLAR topilmadi"
    assert set(re.findall(r'"(\w+)"', butun.group(1))) == RADAR_BUTUN_KALITLAR
