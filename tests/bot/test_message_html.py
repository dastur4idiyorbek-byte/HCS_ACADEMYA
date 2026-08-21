"""Telegram HTML rejimi: ma'lumotdan kelgan matn tegga o'xshamasligi kerak.

Bot xabarlari `parse_mode=HTML` bilan yuboriladi. Bunda matndagi ochiq
`<` belgisi teg boshlanishi deb o'qiladi va Telegram butun xabarni rad
etadi: `Bad Request: can't parse entities`. Handler xatolik bilan
tugaydi, tugma esa foydalanuvchi uchun shunchaki "javob bermaydi" —
ekranda hech qanday xato ko'rinmaydi.

Aynan shu ikki joyda sodir bo'lgan:

  • `<1%` — foiz ulushi (dashboardning o'zi yozadi);
  • `Ball 62 < chegara 70` — sikl yozgan rad etish tafsiloti.

Shuning uchun bu test tayyor xabarni tekshiradi, alohida funksiyani
emas: xato aynan qismlar birlashganda tug'iladi.
"""

from __future__ import annotations

import re

import pytest

from bot.handlers.admin import _render_health, _render_silence

#: Telegram qabul qiladigan teglar (boshqasi ham xatoga olib keladi)
TELEGRAM_TEGLARI = (
    "b", "strong", "i", "em", "u", "s", "strike", "del",
    "code", "pre", "a", "tg-spoiler", "blockquote", "span",
)

_TEG = re.compile(r"</?(?:" + "|".join(TELEGRAM_TEGLARI) + r")(?:\s[^<>]*)?>")


def html_xatosi(matn: str) -> str | None:
    """Telegram rad etadigan birinchi joyni qaytaradi (yoki `None`)."""
    tegsiz = _TEG.sub("", matn)
    joy = tegsiz.find("<")
    return None if joy < 0 else tegsiz[joy : joy + 40]


def test_tekshiruvchi_ozi_ishlaydi() -> None:
    """Test qurilmasi buzuq bo'lsa, hamma narsa yashil ko'rinardi."""
    assert html_xatosi("<b>yaxshi</b> matn") is None
    assert html_xatosi("Ball 62 < chegara 70") == "< chegara 70"
    assert html_xatosi("ulush <1%") == "<1%"


# --------------------------------------------------------------------------- #
#  🔇 Nega signal yo'q
# --------------------------------------------------------------------------- #


def test_kichik_ulush_xabarni_buzmaydi() -> None:
    """`<1%` ochiq yozilsa, butun ekran ochilmay qolardi."""
    matn = _render_silence([("classic_ta:levels", 3, False), ("threshold", 900, False)], "uz")

    assert html_xatosi(matn) is None, f"Telegram rad etadi: {html_xatosi(matn)}"
    assert "&lt;1%" in matn, "kichik ulush ko'rsatilishi kerak, faqat xavfsiz shaklda"


@pytest.mark.parametrize(
    "yomon",
    [
        "Ball 62 < chegara 70",
        "narx < support",
        "a & b",
        "<script>",
    ],
)
def test_bosqich_nomi_tegga_oxshasa_ham_ishlaydi(yomon: str) -> None:
    """0.3-band: nomi noma'lum bosqich kodning o'zi bilan ko'rsatiladi."""
    matn = _render_silence([(yomon, 5, False)], "uz")
    assert html_xatosi(matn) is None, f"Telegram rad etadi: {html_xatosi(matn)}"


# --------------------------------------------------------------------------- #
#  💓 Bozor Salomatligi
# --------------------------------------------------------------------------- #


class SoxtaYozuv:
    band = "mid"
    value = 55.0
    is_daily_preview = False

    def __init__(self, detail: str) -> None:
        self.detail = detail


def test_salomatlik_tafsiloti_tegga_oxshasa_ham_ishlaydi() -> None:
    """Tafsilot bazadan keladi — u yerda `<` bo'lishi mumkin."""
    matn = _render_health(SoxtaYozuv("Dominatsiya 52% < chegara 55%\nADX 18 & past"))
    assert html_xatosi(matn) is None, f"Telegram rad etadi: {html_xatosi(matn)}"


# --------------------------------------------------------------------------- #
#  Oxirgi tafsilotlar — matn TAHLILDAN keladi
# --------------------------------------------------------------------------- #


class SoxtaRadEtish:
    def __init__(self, symbol: str | None, detail: str) -> None:
        self.symbol = symbol
        self.detail = detail


def test_tafsilotdagi_kichik_belgi_xabarni_buzmaydi() -> None:
    """Sikl aynan shunday yozadi: `Ball {ball} < chegara {chegara}`.

    Bitta shunday qator butun ekranni ochilmas qilardi.
    """
    from bot.handlers.admin import _render_latest

    matn = _render_latest(
        [
            SoxtaRadEtish("BTC", "Ball 62 < chegara 70"),
            SoxtaRadEtish(None, "Bozor Salomatligi past (38/100)"),
        ],
        "uz",
    )

    assert html_xatosi(matn) is None, f"Telegram rad etadi: {html_xatosi(matn)}"
    assert "Ball 62 &lt; chegara 70" in matn, "tafsilot yo'qolmasligi kerak"


def test_tafsilot_yoq_bolsa_bolim_chiqmaydi() -> None:
    from bot.handlers.admin import _render_latest

    assert _render_latest([], "uz") == ""


# --------------------------------------------------------------------------- #
#  Apostrof — o'zbek matnining har qadamida
# --------------------------------------------------------------------------- #


def test_apostrof_qochirilmaydi() -> None:
    """`html.escape` sukut bo'yicha apostrofni `&#x27;` ga aylantiradi.

    O'zbek matnida u har qadamda uchraydi ("sig'madi", "to'xtagan") —
    qochirilsa ekranni o'qib bo'lmaydi. Matn tanasida uni qochirish
    shart ham emas: faqat `< > &` maxsus ma'noga ega.
    """
    matn = _render_silence([("classic_ta:levels", 3, False)], "uz")
    assert "sig'madi" in matn
    assert "&#x27;" not in matn

    from bot.handlers.admin import _render_latest

    tafsilot = _render_latest([SoxtaRadEtish("BTC", "Narx zonaga yetmadi — o'tkazildi")], "uz")
    assert "o'tkazildi" in tafsilot
    assert "&#x27;" not in tafsilot
