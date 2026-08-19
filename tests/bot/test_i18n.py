"""1.1-band: matnlar kodga qattiq yozilmasligi va ko'p tillilikka tayyorligi."""

from __future__ import annotations

import json

import pytest

from bot.i18n import I18N_DIR, TranslationError, available_languages, t


def test_ozbek_tili_mavjud() -> None:
    assert "uz" in available_languages()


def test_matn_olinadi() -> None:
    assert t("umumiy.menyu") == "📋 Asosiy menyu"


def test_orin_egallovchilar_toldiriladi() -> None:
    assert "Diyorbek" in t("umumiy.salom", name="Diyorbek")


def test_qoidabuzarlik_matni_spetsifikatsiyaga_mos() -> None:
    """1.3-banddagi matn AYNAN shu ko'rinishda bo'lishi kerak."""
    kutilgan = (
        "❗️❗️ Diqqat! Siz bizning qoidalarimizni buzmoqdasiz. "
        "Shu sababli tarifingiz vaqtincha to'xtatildi."
    )
    assert t("qoidabuzarlik.ogohlantirish") == kutilgan


def test_yetishmayotgan_kalit_xato_beradi() -> None:
    """Bo'sh xabar foydalanuvchiga ko'rsatilmasligi kerak."""
    with pytest.raises(TranslationError):
        t("mavjud.emas.kalit")


def test_orin_egallovchi_berilmasa_xato_beradi() -> None:
    with pytest.raises(TranslationError):
        t("umumiy.salom")


def test_barcha_til_fayllari_bir_xil_kalitlarga_ega() -> None:
    """Yangi til qo'shilganda kalit tushib qolmasligi uchun."""

    def kalitlar(data: dict, prefiks: str = "") -> set[str]:
        natija: set[str] = set()
        for kalit, qiymat in data.items():
            toliq = f"{prefiks}.{kalit}" if prefiks else kalit
            natija |= kalitlar(qiymat, toliq) if isinstance(qiymat, dict) else {toliq}
        return natija

    fayllar = sorted(I18N_DIR.glob("*.json"))
    assert fayllar, "kamida bitta til fayli bo'lishi kerak"

    asos = kalitlar(json.loads(fayllar[0].read_text(encoding="utf-8")))
    for fayl in fayllar[1:]:
        boshqa = kalitlar(json.loads(fayl.read_text(encoding="utf-8")))
        assert boshqa == asos, f"{fayl.name} kalitlari {fayllar[0].name} dan farq qiladi"
