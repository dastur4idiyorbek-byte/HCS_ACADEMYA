"""BLOK 5 — sun'iy intellekt tekshiruvi (yakuniy filtr).

FAQAT 4 blok o'tgan nomzod uchun ishga tushadi. DeepSeek API orqali
"TASDIQLANDI" yoki "RAD ETILDI" javobini oladi.

QOIDALAR:
  * Noaniqlik yoki API xatosi — RAD ETILDI (signal chiqarilmaydi).
  * `enabled=False` — o'tkazib yuboradi (TASDIQLANDI), chunki bu
    blok qo'shimcha filtr; o'chirilgan bo'lsa 4 blok natijasi o'zi
    yetarli.
  * API kaliti `config.zanjir.ai.api_key_env` nomli muhit
    o'zgaruvchisidan o'qiladi — kodga qattiq yozilmaydi.

So'rov formati (OpenAI-mos):
    POST {base_url}
    Authorization: Bearer {api_key}
    {"model": "...", "messages": [system, user], "temperature": 0,
     "max_tokens": 8}
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import aiohttp

from core.config.schema import AiVerificationConfig
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

TASDIQLANDI = "TASDIQLANDI"
RAD_ETILDI = "RAD ETILDI"

#: Model javobini ikkita so'zga qisqartiruvchi tizim ko'rsatmasi.
#: `temperature=0` bilan birga — aniq, takrorlanuvchi javob uchun.
TIZIM_PROMPT = (
    "Sen halol kripto spot savdo signalini tekshiruvchi mutaxassissan. "
    "Senga 4 blokli texnik tahlil natijasi beriladi. "
    "Signal chiqarishga arziydimi yoki yo'qmi — hal qil. "
    "FAQAT bitta so'z bilan javob ber: 'TASDIQLANDI' yoki 'RAD ETILDI'. "
    "Noaniqlik bo'lsa 'RAD ETILDI' deb javob ber. Boshqa hech narsa yozma."
)


@dataclass(frozen=True, slots=True)
class AiNatija:
    """SI tekshiruvining natijasi."""

    qaror: str
    sabab: str
    xom_javob: str = ""

    @property
    def tasdiqlandi(self) -> bool:
        """Signal chiqarish mumkinmi."""
        return self.qaror == TASDIQLANDI


@dataclass(frozen=True, slots=True)
class AiTekshiruvKirish:
    """SI bloki uchun barcha kerakli ma'lumot."""

    symbol: str
    #: `zanjir.matn()` — 4 blokning inson o'qiydigan xulosasi
    matn: str
    #: `zanjir.ishonch()` — ball asosidagi ishonch (0..1)
    ishonch: float
    narx: float


def foydalanuvchi_prompt(kirish: AiTekshiruvKirish) -> str:
    """SI ga yuboriladigan matn — nomzod haqida qisqa xulosa."""
    return (
        f"Coin: {kirish.symbol}\n"
        f"Narx: {kirish.narx}\n"
        f"Ishonch: {kirish.ishonch:.2f}\n\n"
        f"4 blok tahlili:\n{kirish.matn}\n\n"
        "Signal chiqarishni tasdiqlaysizmi? "
        "Faqat 'TASDIQLANDI' yoki 'RAD ETILDI' deb javob ber."
    )


def _javobni_tani(javob: str) -> str:
    """Model javobini ikkita qarorga aylantiradi.

    Model izoh qo'shib yuborsa ham (masalan "TASDIQLANDI, chunki ...")
    faqat kalit so'z qidiriladi. Ikkalasi ham topilsa — rad etiladi,
    chunki bu noaniqlik.
    """
    xom = javob.strip().upper()
    tasdiq = TASDIQLANDI in xom
    rad = RAD_ETILDI in xom
    if tasdiq and not rad:
        return TASDIQLANDI
    return RAD_ETILDI


async def ai_tekshir(
    kirish: AiTekshiruvKirish,
    config: AiVerificationConfig,
) -> AiNatija:
    """4 blok o'tgan nomzodni DeepSeek orqali tekshiradi.

    Returns:
        `AiNatija` — `TASDIQLANDI` yoki `RAD ETILDI`. Blok o'chirilgan
        bo'lsa `TASDIQLANDI` (o'tkazib yuborish), API xatosi bo'lsa
        `RAD ETILDI` (fail-safe: shubhali signal chiqarilmaydi).
    """
    if not config.enabled:
        return AiNatija(TASDIQLANDI, "SI tekshiruvi o'chirilgan")

    api_key = os.getenv(config.api_key_env, "").strip()
    if not api_key:
        return AiNatija(RAD_ETILDI, f"{config.api_key_env} muhit o'zgaruvchisi topilmadi")

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": TIZIM_PROMPT},
            {"role": "user", "content": foydalanuvchi_prompt(kirish)},
        ],
        "temperature": 0,
        "max_tokens": config.max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)

    try:
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                config.base_url, json=payload, headers=headers, timeout=timeout
            ) as javob,
        ):
            if javob.status != 200:
                return AiNatija(RAD_ETILDI, f"HTTP {javob.status}")
            malumot = await javob.json()
        xom = malumot["choices"][0]["message"]["content"]
    except Exception as xato:  # noqa: BLE001 — fail-safe, sabab qaytariladi
        logger.warning("SI tekshiruvi bajarilmadi: %s", xato)
        return AiNatija(RAD_ETILDI, f"API xatosi: {type(xato).__name__}")

    qaror = _javobni_tani(xom)
    if qaror == TASDIQLANDI:
        return AiNatija(TASDIQLANDI, "SI tasdiqladi", xom)
    return AiNatija(RAD_ETILDI, "SI rad etdi yoki noaniq", xom)
