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


# --------------------------------------------------------------------------- #
#  Enum qiymatlaridan quriladigan kalitlar
# --------------------------------------------------------------------------- #

#: Kodda `t(f"...{enum.value}")` ko'rinishida ishlatiladigan har bir enum.
#: Bunday kalit YO'Q bo'lsa, xato faqat foydalanuvchi tugmani bosganda
#: chiqadi — testda emas. Shu sababli hammasi shu yerda ro'yxatga olinadi.
#:
#: Yangi shunday chaqiruv qo'shsangiz, uni SHU RO'YXATGA ham qo'shing.
ENUM_KALITLARI: list[tuple[str, type]] = []


def _enum_kalitlarini_yig() -> None:
    from core.domain.enums import SignalStatus, SubscriptionPeriod, SubscriptionTier

    ENUM_KALITLARI.extend(
        [
            ("signal.holat_{}", SignalStatus),
            ("obuna.{}", SubscriptionTier),
            ("obuna.{}", SubscriptionPeriod),
        ]
    )


_enum_kalitlarini_yig()


@pytest.mark.parametrize(("shablon", "enum_turi"), ENUM_KALITLARI)
def test_enum_qiymatlari_uchun_tarjima_bor(shablon: str, enum_turi: type) -> None:
    """Kalitlar enum QIYMATLARIGA aynan mos bo'lishi kerak.

    Bu xato ikki marta yuz bergan: avval `SignalStatus` bilan, keyin
    `SubscriptionPeriod` bilan (kalit `kunlik` edi, enum qiymati esa
    `daily`). Ikkalasida ham bot ishga tushgan, testlar yashil bo'lgan,
    lekin foydalanuvchi tugmani bosganda yiqilgan.

    Sabab: kalitlar qo'lda o'zbekcha yozilgan, enum qiymatlari esa
    inglizcha. Ular bir-biriga bog'lanmagan, shuning uchun faqat shunday
    test ushlab qoladi.
    """
    for element in enum_turi:
        kalit = shablon.format(element.value)
        assert t(kalit), f"{kalit} uchun matn yo'q"


def test_barcha_enum_chaqiruvlari_royxatga_olingan() -> None:
    """Kodda `t(f"...")` bor, lekin yuqoridagi ro'yxatda yo'q — bo'lmasin.

    Ro'yxat qo'lda to'ldiriladi, shuning uchun u eskirib qolishi mumkin.
    Bu test kodni skanerlab, hisobga olinmagan chaqiruvni topadi.
    """
    import re
    from pathlib import Path

    bot_papkasi = Path(__file__).resolve().parents[2] / "bot"
    topilgan = set()

    for fayl in bot_papkasi.rglob("*.py"):
        for moslik in re.finditer(r't\(f"([^"]*\{[^"]*)"', fayl.read_text(encoding="utf-8")):
            topilgan.add(re.sub(r"\{[^}]*\}", "{}", moslik.group(1)))

    royxatdagi = {shablon for shablon, _ in ENUM_KALITLARI}
    hisobga_olinmagan = topilgan - royxatdagi

    assert not hisobga_olinmagan, (
        "Bu kalitlar enumdan quriladi, lekin ENUM_KALITLARI ro'yxatida yo'q:\n"
        f"  {sorted(hisobga_olinmagan)}\n"
        "Har birini ro'yxatga qo'shing — aks holda yetishmayotgan tarjima "
        "faqat ish paytida bilinadi."
    )
