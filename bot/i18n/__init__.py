"""1.1-band: ko'p tillilikka tayyor matnlar qatlami.

Matnlar kod ichiga QATTIQ YOZILMAYDI — shu papkadagi JSON fayllarda
saqlanadi. Boshlang'ich versiyada faqat o'zbek tili, lekin yangi til qo'shish
uchun `ru.json` faylini qo'shish va konfiguratsiyadagi
`project.supported_languages` ga qo'shish kifoya.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

I18N_DIR = Path(__file__).parent
DEFAULT_LANGUAGE = "uz"


class TranslationError(KeyError):
    """So'ralgan matn kaliti topilmadi."""


@lru_cache(maxsize=8)
def load_translations(language: str) -> dict[str, Any]:
    """Til faylini yuklaydi (keshlanadi)."""
    path = I18N_DIR / f"{language}.json"
    if not path.exists():
        if language == DEFAULT_LANGUAGE:
            raise FileNotFoundError(f"Standart til fayli topilmadi: {path}")
        return load_translations(DEFAULT_LANGUAGE)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def t(key: str, language: str = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    """Matnni kalit bo'yicha oladi va o'rin egallovchilarni to'ldiradi.

    Kalit nuqta bilan ajratiladi, masalan ``"signal.nega_halol"``.

    Yetishmayotgan kalit jim o'tmasligi kerak — bu foydalanuvchiga bo'sh
    xabar ko'rsatilishiga olib keladi.
    """
    data: Any = load_translations(language)
    for qism in key.split("."):
        if not isinstance(data, dict) or qism not in data:
            raise TranslationError(f"Tarjima kaliti topilmadi: {key!r} ({language})")
        data = data[qism]

    if not isinstance(data, str):
        raise TranslationError(f"Tarjima kaliti matn emas: {key!r}")

    # Formatlash DOIM bajariladi — aks holda o'rin egallovchili matn
    # (masalan "{name}") kwargs berilmaganda foydalanuvchiga xom holda
    # ko'rinib ketardi.
    try:
        return data.format(**kwargs)
    except (KeyError, IndexError) as exc:
        raise TranslationError(f"{key!r} uchun o'rin egallovchi berilmadi: {exc}") from exc


def available_languages() -> list[str]:
    return sorted(path.stem for path in I18N_DIR.glob("*.json"))
