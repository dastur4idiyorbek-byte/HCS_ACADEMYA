"""5-blok SI tekshiruvi uchun testlar.

Tarmoq chaqiruvi bu yerda sinmaydi — faqat sof mantiq, o'chirilgan
blok va kalitsiz fail-safe holat tekshiriladi.
"""

from __future__ import annotations

from core.analysis.ai_verification.ai_verifier import (
    RAD_ETILDI,
    TASDIQLANDI,
    AiTekshiruvKirish,
    AiVerificationConfig,
    _javobni_tani,
    ai_tekshir,
    foydalanuvchi_prompt,
)


def test_aniq_tasdiq_taniladi() -> None:
    assert _javobni_tani("TASDIQLANDI") == TASDIQLANDI
    assert _javobni_tani("Tasdiqlandi, zona kuchli") == TASDIQLANDI


def test_rad_va_noaniq_rad_buladi() -> None:
    assert _javobni_tani("RAD ETILDI") == RAD_ETILDI
    assert _javobni_tani("tushunarsiz javob") == RAD_ETILDI
    # Ikkala so'z ham bo'lsa — noaniqlik, rad etiladi
    assert _javobni_tani("TASDIQLANDI RAD ETILDI") == RAD_ETILDI


def test_prompt_ichida_nomzod_malumoti() -> None:
    matn = foydalanuvchi_prompt(AiTekshiruvKirish("BTC", "zanjir xulosasi", 0.8, 64000.0))
    assert "BTC" in matn
    assert "zanjir xulosasi" in matn


async def test_ochirilgan_blok_otkazib_yuboradi() -> None:
    config = AiVerificationConfig(enabled=False)
    natija = await ai_tekshir(AiTekshiruvKirish("BTC", "m", 0.5, 1.0), config)
    assert natija.tasdiqlandi


async def test_kalitsiz_fail_safe_rad(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv("SINALMAYDIGAN_KALIT", raising=False)
    config = AiVerificationConfig(enabled=True, api_key_env="SINALMAYDIGAN_KALIT")
    natija = await ai_tekshir(AiTekshiruvKirish("BTC", "m", 0.5, 1.0), config)
    assert natija.qaror == RAD_ETILDI
