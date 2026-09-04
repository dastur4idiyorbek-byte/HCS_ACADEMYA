"""O'lchov coinlari loyihaning HALOL skriningiga mos kelsin.

2026-09-04 da topilgan xato: 12 coinlik barcha o'lchov BNB va XRP
bilan yuritilgan edi. Holbuki config'da BNB — harom ro'yxatida,
XRP — mashbooh ro'yxatida.

Oqibati: PF 3.50 raqami bot HECH QACHON signal bermaydigan
coinlardagi savdolarni ham o'z ichiga olardi. Bu — natijani
biroz o'zgartiradigan kamchilik emas, o'lchovning MA'NOSINI
buzadigan xato: biz boshqa mahsulotni o'lchayotgan edik.

Bu test xatoning qaytarilishini imkonsiz qiladi.
"""

from __future__ import annotations

from core.config.loader import load_config
from scripts.zanjir_umumiy import OLCHOV_12, OLCHOV_24, STANDART_COINLAR

TOPLAMLAR = {
    "STANDART_COINLAR": STANDART_COINLAR,
    "OLCHOV_12": OLCHOV_12,
    "OLCHOV_24": OLCHOV_24,
}


def _taqiqlangan() -> set[str]:
    skrining = load_config().halal_screening
    return {
        *(s.upper() for s in skrining.seed_haram_symbols),
        *(s.upper() for s in skrining.seed_mashbooh_symbols),
    }


def test_olchov_coinlari_harom_yoki_mashbooh_emas() -> None:
    taqiq = _taqiqlangan()
    for nom, toplam in TOPLAMLAR.items():
        buzilgan = sorted({c.upper() for c in toplam} & taqiq)
        assert not buzilgan, f"{nom} da skriningdan o'tmaydigan coin bor: {buzilgan}"


def test_stablecoin_olchovga_kirmaydi() -> None:
    """Stablecoin uchun struktura tahlili ma'nosiz."""
    stabil = {s.upper() for s in load_config().halal_screening.stablecoin_symbols}
    for nom, toplam in TOPLAMLAR.items():
        assert not ({c.upper() for c in toplam} & stabil), nom


def test_toplamlar_ichma_ich() -> None:
    """Kichik to'plam kattasining ichida bo'lsin — solishtirish uchun."""
    assert set(STANDART_COINLAR) <= set(OLCHOV_12) <= set(OLCHOV_24)


def test_takrorlanmaydi() -> None:
    for nom, toplam in TOPLAMLAR.items():
        assert len(toplam) == len(set(toplam)), nom
