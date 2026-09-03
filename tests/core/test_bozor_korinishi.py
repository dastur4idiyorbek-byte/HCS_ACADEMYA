"""BOZOR KO'RINISHI — sayt uchun haftalik va kunlik qarash.

LOYIHA EGASINING SHARTI: bu SIGNALGA BOG'LANMAYDI. Asosiy
tahlil 4 soatlikda qoladi, haftalik va kunlik esa faqat
saytdagi post.

Shuning uchun birinchi test — eng muhimi: bu modul hech bir
strategiyadan chaqirilmasligi kerak. Aks holda u jimgina
darvozaga aylanardi, va aynan shu narsa bir marta o'lchanib
RAD ETILGAN (natija #11: PF 0.84 -> 0.75).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.analysis.bozor_korinishi import (
    ASBOBLAR,
    KorinishTuri,
    korinish_qur,
)
from core.domain.enums import TrendDirection
from core.domain.models import Candle

ILDIZ = Path(__file__).resolve().parents[2]
SANA = datetime(2026, 9, 7, tzinfo=UTC)


def sham(i: int, narx: float) -> Candle:
    return Candle(
        open_time=SANA + timedelta(days=i),
        open=narx,
        high=narx * 1.01,
        low=narx * 0.99,
        close=narx,
        volume=100.0,
        closed=True,
    )


def kotarilish(n: int = 12) -> list[Candle]:
    return [sham(i, 100 + i * 3) for i in range(n)]


# --------------------------------------------------------------------------- #
#  ENG MUHIMI: signalga bog'lanmagan
# --------------------------------------------------------------------------- #


def test_hech_bir_strategiya_bu_modulni_chaqirmaydi() -> None:
    """Loyiha egasining sharti kod bilan qulflanadi.

    "Haftalik va kunlik shunchaki qarash... san uni 4 soatlikka
    bog'lama."

    Agar kimdir uni strategiyaga ulasa, bu test yiqiladi. Izoh
    yozib qo'yish yetarli emas — loyihada izoh bir necha marta
    koddan ajralib ketgan.
    """
    ayblanuvchilar = []
    for papka in ("strategies", "scoring"):
        for fayl in (ILDIZ / "core" / "analysis" / papka).glob("*.py"):
            if "bozor_korinishi" in fayl.read_text(encoding="utf-8"):
                ayblanuvchilar.append(str(fayl.relative_to(ILDIZ)))

    for fayl in (ILDIZ / "core" / "pipeline").glob("*.py"):
        if "bozor_korinishi" in fayl.read_text(encoding="utf-8"):
            ayblanuvchilar.append(str(fayl.relative_to(ILDIZ)))

    assert not ayblanuvchilar, (
        "Bozor ko'rinishi signal yo'liga ulangan: "
        f"{ayblanuvchilar}. Loyiha egasining sharti — u faqat sayt uchun."
    )


def test_modul_faqat_fakt_beradi_taxmin_yozmaydi() -> None:
    """"Kutilma" qatori KAFOLAT EMAS deb belgilanishi shart."""
    matn = (ILDIZ / "core" / "analysis" / "bozor_korinishi.py").read_text(
        encoding="utf-8"
    )
    kutilmalar = re.findall(r'return \(\s*\n\s*"([^"]*an\'anaviy[^"]*)"', matn)

    assert matn.count("Kafolat emas.") >= 3, (
        "Har bir an'anaviy o'qish 'kafolat emas' deb belgilanishi kerak"
    )
    assert kutilmalar or "an'anaviy" in matn


# --------------------------------------------------------------------------- #
#  Qatorlar
# --------------------------------------------------------------------------- #


def test_narx_qatoridan_yonalish_oqiladi() -> None:
    korinish = korinish_qur(
        KorinishTuri.HAFTALIK, SANA, {"BTC": kotarilish()}, {}
    )

    btc = korinish.asbob("BTC")
    assert btc is not None
    assert btc.yonalish is TrendDirection.UP
    assert btc.qiymat == 133.0


def test_kesim_tarixidan_yonalish_oqiladi() -> None:
    """BTC.D va TOTAL birjadan sham sifatida kelmaydi.

    Ular har kuni O'ZIMIZ saqlaydigan qiymatlardan yig'iladi.
    """
    korinish = korinish_qur(
        KorinishTuri.KUNLIK,
        SANA,
        {},
        {"BTC.D": [50.0, 52.0, 54.0], "USDT.D": [6.0, 5.5, 5.0]},
    )

    assert korinish.asbob("BTC.D").yonalish is TrendDirection.UP
    assert korinish.asbob("USDT.D").yonalish is TrendDirection.DOWN


def test_tarix_yetarli_bolmasa_FLAT_va_ochiq_aytiladi() -> None:
    """Ikkita nuqta yo'nalish e'lon qilish uchun yetarli emas.

    Bo'sh sahifa ko'rsatishdan ko'ra ochiq aytish yaxshiroq —
    qator chiqadi, lekin yo'nalish e'lon qilinmaydi.
    """
    korinish = korinish_qur(KorinishTuri.KUNLIK, SANA, {}, {"TOTAL": [1.0, 2.0]})

    total = korinish.asbob("TOTAL")
    assert total is not None
    assert total.yonalish is TrendDirection.FLAT


def test_malumot_yoq_asbob_qatorga_qoshilmaydi() -> None:
    korinish = korinish_qur(KorinishTuri.KUNLIK, SANA, {}, {})

    assert korinish.asboblar == []


def test_asboblar_royxati_loyiha_egasi_bergani() -> None:
    """Ro'yxat va TARTIB — loyiha egasining xabaridan."""
    kodlar = [kod for kod, _ in ASBOBLAR]

    assert kodlar == [
        "BTC",
        "ETH",
        "BTC.D",
        "USDT.D",
        "TOTAL",
        "TOTAL2",
        "TOTAL3",
        "OTHERS",
    ]


# --------------------------------------------------------------------------- #
#  Xulosa va kutilma
# --------------------------------------------------------------------------- #


def test_xulosa_faqat_faktlardan_yigiladi() -> None:
    korinish = korinish_qur(
        KorinishTuri.HAFTALIK,
        SANA,
        {"BTC": kotarilish()},
        {"USDT.D": [6.0, 5.5, 5.0]},
    )

    xulosa = korinish.xulosa
    assert "BTC" in xulosa
    assert "USDT.D" in xulosa


def test_usdt_ustunligi_ossa_ogohlantiriladi() -> None:
    korinish = korinish_qur(
        KorinishTuri.KUNLIK,
        SANA,
        {},
        {"BTC.D": [50.0, 50.1, 50.2], "USDT.D": [5.0, 5.5, 6.0]},
    )

    assert "kutish holatiga" in korinish.kutilma
    assert "Kafolat emas" in korinish.kutilma


def test_ikkala_ustunlik_pasaysa_altcoin_davri() -> None:
    korinish = korinish_qur(
        KorinishTuri.KUNLIK,
        SANA,
        {},
        {"BTC.D": [54.0, 52.0, 50.0], "USDT.D": [6.0, 5.5, 5.0]},
    )

    assert "altcoinlar uchun qulay" in korinish.kutilma
    assert "Kafolat emas" in korinish.kutilma


def test_ustunlik_malumoti_yoq_bolsa_oqish_berilmaydi() -> None:
    """Taxmin o'ylab topilmaydi — ma'lumot yo'q bo'lsa shunday deyiladi."""
    korinish = korinish_qur(KorinishTuri.KUNLIK, SANA, {"BTC": kotarilish()}, {})

    assert "o'qish berilmaydi" in korinish.kutilma
