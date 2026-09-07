"""Alternativ yo'llar uchun umumiy tip.

Yangi alternativ zanjir: blok ZAIF bo'lsa (1/N) — alternativ yo'llar
KETMA-KET sinab ko'riladi. Har bir alternativ shu tipda javob qaytaradi.

`zona` — faqat zona beruvchi alternativlar to'ldiradi (Blok 3: qo'sh
tub, oldingi swing). Struktura va tasdiq alternativlari zona bermaydi —
ular blokni faqat qutqaradi, kirish darajalari baribir Blok 3 zonasidan
(`darajalar_qur`) quriladi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.zone_quality.fibonacci import Zona


@dataclass(frozen=True, slots=True)
class AlternativNatija:
    """Bitta alternativ yo'lning natijasi."""

    nom: str
    otdi: bool
    izoh: str = ""
    zona: Zona | None = None
