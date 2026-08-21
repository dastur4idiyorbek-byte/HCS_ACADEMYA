"""3.7-band: "nega signal yo'q" dashboardi.

Bu ekranning butun maqsadi — ishlayotgan tizimni buzuq tizimdan
ajratish. Agar u noto'g'ri o'lchov ko'rsatsa, aynan shu maqsadga zid
ish qiladi: admin haqiqiy sababni ko'rmay, boshqasini tuzatishga
kirishadi.
"""

from __future__ import annotations

import re

from bot.handlers.admin import _render_silence, _ulush

TIL = "uz"


def _matn(summary: list[tuple[str, int, bool]]) -> str:
    return re.sub(r"</?b>", "", _render_silence(summary, TIL))


# --------------------------------------------------------------------------- #
#  Foiz
# --------------------------------------------------------------------------- #


def test_kichik_ulush_nol_deb_yozilmaydi() -> None:
    """5 marta sodir bo'lgan sabab "0%" deb ko'rinardi.

    Bitta qatorda "bo'ldi" (5 marta) va "bo'lmadi" (0%) yozilgan edi —
    admin qaysi biriga ishonishini bilmasdi.
    """
    assert _ulush(5, 1943) == "<1%"
    assert _ulush(1, 1943) == "<1%"


def test_katta_ulush_yaxlitlanadi() -> None:
    assert _ulush(945, 1943) == "49%"
    assert _ulush(624, 1943) == "32%"


def test_nolinchi_jami_yiqilmaydi() -> None:
    """0.3-band: hisoblab bo'lmasa ham ekran ochilishi kerak."""
    assert _ulush(0, 0) == "—"


# --------------------------------------------------------------------------- #
#  Guruhlash
# --------------------------------------------------------------------------- #


def test_vaqt_sharti_foiz_hisobiga_kirmaydi() -> None:
    """Skalping oynasi kuniga 45 daqiqa ochiq — 96% vaqtda "yopiq".

    Bu yozuv umumiy ustunga qo'shilganda birinchi o'rinni egallab,
    haqiqiy sabablarni pastga surib yuborardi va ularning foizini ham
    ikki barobar kichraytirardi.
    """
    matn = _matn(
        [
            ("opening_range_scalp:window", 900, False),
            ("classic_ta:zone_position", 60, False),
            ("classic_ta:timeframes", 40, False),
        ]
    )

    assert "Narx support zonasidan uzoq — 60 marta (60%)" in matn
    assert "Timeframelar bir-biriga zid — 40 marta (40%)" in matn
    assert "Skalping oynasi yopiq — 900 marta" in matn
    assert "900 marta (" not in matn, "vaqt shartiga foiz qo'yilmasligi kerak"


def test_sikl_darajasi_alohida_korsatiladi() -> None:
    """Bitta sikl to'xtashi barcha coinlarni to'xtatadi.

    Uni coin darajasidagi yozuvlar bilan bitta ustunga qo'shish — 30 ta
    coinni to'xtatgan sababni bitta coinni to'xtatgani bilan teng deb
    hisoblash demakdir.
    """
    matn = _matn(
        [
            ("classic_ta:zone_position", 60, False),
            ("market_health", 53, True),
        ]
    )

    assert "Bozor Salomatligi past — 53 marta" in matn
    assert "53 marta (" not in matn, "sikl darajasiga foiz qo'yilmasligi kerak"
    assert "Narx support zonasidan uzoq — 60 marta (100%)" in matn


def test_kod_nomi_emas_odam_oqiydigan_nom() -> None:
    matn = _matn([("classic_ta:zone_position", 5, False)])
    assert "classic_ta:zone_position" not in matn
    assert "Narx support zonasidan uzoq" in matn


def test_notanish_bosqich_ekranni_yiqitmaydi() -> None:
    """0.3-band: yangi bosqich qo'shilib, nomi unutilsa ham ishlasin."""
    matn = _matn([("yangi_strategiya:yangi_bosqich", 3, False)])
    assert "yangi_strategiya:yangi_bosqich — 3 marta (100%)" in matn


def test_faqat_vaqt_shartlari_bolsa_tahlil_bolimi_chiqmaydi() -> None:
    """Bo'sh "0 ta tekshiruv" sarlavhasi chalg'itardi."""
    matn = _matn([("opening_range_scalp:window", 900, False)])
    assert "📊" not in matn, "bo'sh tahlil sarlavhasi ko'rsatilmasligi kerak"
    assert "Skalping oynasi yopiq — 900 marta" in matn
