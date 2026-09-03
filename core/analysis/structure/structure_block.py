"""BLOK 2 — to'rt struktura tekshiruvini yig'adi."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.analysis.structure.bos_choch import bos_choch_topish
from core.analysis.structure.new_coin_pattern import yangi_coin_naqshi
from core.analysis.structure.relative_strength import nisbiy_kuch
from core.analysis.structure.swing_detector import ketma_ketlik_kotarilish, swinglar
from core.analysis.turlar import Blok, blok, ha, malumot_yoq, yoq
from core.domain.models import Candle

BLOK_NOMI = "Struktura"

#: Coin shundan yosh bo'lsa — soddalashtirilgan naqsh (1-qism)
YANGI_COIN_KUN = 90


@dataclass(frozen=True, slots=True)
class StrukturaKirish:
    """Blok 2 uchun ma'lumot."""

    #: ASOSIY timeframe shamlari (yetuk coin uchun 1D)
    shamlar: list[Candle] = field(default_factory=list)
    #: BTC shamlari — nisbiy kuch uchun, AYNAN shu timeframeda
    btc_shamlar: list[Candle] = field(default_factory=list)
    #: Coin necha kunlik. `None` — noma'lum, yetuk deb qaraladi.
    yosh_kun: int | None = None
    #: Coinning o'zi BTC mi (nisbiy kuch o'lchanmaydi)
    etalon: bool = False
    #: `price_reconciliation` belgilagan shubhali sham vaqtlari
    shubhali: set[datetime] = field(default_factory=set)


def struktura_blok(kirish: StrukturaKirish) -> Blok:
    """Coin yoshiga qarab to'liq yoki soddalashtirilgan tekshiruv."""
    nuqtalar = swinglar(kirish.shamlar, shubhali=kirish.shubhali)

    if kirish.yosh_kun is not None and kirish.yosh_kun < YANGI_COIN_KUN:
        return _yangi_coin(kirish, nuqtalar)

    holat = bos_choch_topish(kirish.shamlar, nuqtalar)
    kuchli = nisbiy_kuch(kirish.shamlar, kirish.btc_shamlar, etalon=kirish.etalon)

    tekshiruvlar = [
        _bayroq("swing_ketma_ketligi", ketma_ketlik_kotarilish(nuqtalar), "HH/HL"),
        _bayroq("bos_tasdiqlangan", holat.bos_tasdiqlangan, "BOS"),
        (
            malumot_yoq("qarshi_choch_yoq", "yo'nalish aniqlanmagan")
            if holat.qarshi_choch_yoq is None
            else _bayroq("qarshi_choch_yoq", holat.qarshi_choch_yoq, "CHOCH")
        ),
        (
            malumot_yoq("nisbiy_kuch", "BTC etaloni yoki tarix yetmaydi")
            if kuchli is None
            else _bayroq("nisbiy_kuch", kuchli, "coin/BTC")
        ),
    ]
    return blok(BLOK_NOMI, tekshiruvlar)


def _yangi_coin(kirish: StrukturaKirish, nuqtalar: list) -> Blok:  # noqa: ANN001
    """Soddalashtirilgan naqsh — IKKI tekshiruv, to'rtta emas.

    Maxraj kichik bo'lgani uchun blokning nisbati (kuch/maxraj)
    yetuk coinnikiga TENG SHKALADA qoladi: 2/2 = 1.0, xuddi
    4/4 kabi. Lekin ishonch pasayishi kerak degan talab bor
    (2-prompt), shuning uchun naqsh topilsa ham "nisbiy kuch"
    alohida tekshiriladi va u ko'pincha ma'lumotsiz chiqadi.
    """
    naqsh = yangi_coin_naqshi(kirish.shamlar, nuqtalar)
    kuchli = nisbiy_kuch(kirish.shamlar, kirish.btc_shamlar, etalon=kirish.etalon)

    tekshiruvlar = [
        _bayroq("yangi_coin_naqshi", naqsh, "cho'qqi->korreksiya->BOS"),
        (
            malumot_yoq("nisbiy_kuch", "tarix yetmaydi")
            if kuchli is None
            else _bayroq("nisbiy_kuch", kuchli, "coin/BTC")
        ),
    ]
    return blok(BLOK_NOMI, tekshiruvlar)


def _bayroq(nom: str, qiymat: bool, izoh: str):  # noqa: ANN202
    return ha(nom, f"{izoh} ✓") if qiymat else yoq(nom, f"{izoh} ✗")
