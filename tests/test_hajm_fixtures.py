"""Etalon qiymatlar Python hisobiga mos ekanini tekshiradi.

Juftligi: `web/tests/hajm.test.ts` — u AYNAN SHU faylni o'qib,
TypeScript nusxasini solishtiradi. Ikkalasi bitta etalonga qaraydi,
ya'ni biror tomon o'zgarsa testlardan biri yiqiladi.
"""

from __future__ import annotations

import json

from scripts.hajm_fixtures import FAYL, hisobla


def test_etalon_fayl_yangi() -> None:
    """Hisob o'zgargan bo'lsa, etalon ham yangilanishi kerak.

    Yiqilsa: `python -m scripts.hajm_fixtures` ni ishga tushiring VA
    saytdagi `web/src/lib/hajm.ts` ni ham tekshiring — ehtimol u ham
    o'zgarishi kerak.
    """
    saqlangan = json.loads(FAYL.read_text(encoding="utf-8"))
    assert saqlangan == hisobla(), (
        "Etalon eskirgan: `python -m scripts.hajm_fixtures` ni ishga tushiring"
    )


def test_etalon_bosh_emas() -> None:
    saqlangan = json.loads(FAYL.read_text(encoding="utf-8"))
    assert len(saqlangan) >= 5, "turli pog'ona va Stop masofalari qamralsin"
    assert any(h["hajm"] > 0 for h in saqlangan)
