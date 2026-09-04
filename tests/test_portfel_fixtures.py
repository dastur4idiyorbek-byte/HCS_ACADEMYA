"""Portfel dashboardining etaloni Python hisobiga mos ekanini tekshiradi.

Juftligi: `web/tests/portfel.test.ts` — u AYNAN SHU faylni o'qib,
TypeScript nusxasini solishtiradi. Ikkalasi bitta etalonga qaraydi,
ya'ni biror tomon o'zgarsa testlardan biri yiqiladi.

3-promptning "BITTA MANBA, IKKI EKRAN" talabini shu juftlik
ushlab turadi.
"""

from __future__ import annotations

import json

from scripts.portfel_fixtures import FAYL, hisobla


def test_etalon_fayl_yangi() -> None:
    """Hisob o'zgargan bo'lsa, etalon ham yangilanishi kerak.

    Yiqilsa: `python -m scripts.portfel_fixtures` ni ishga tushiring VA
    saytdagi `web/src/lib/portfel.ts` ni ham tekshiring — ehtimol u ham
    o'zgarishi kerak.
    """
    saqlangan = json.loads(FAYL.read_text(encoding="utf-8"))
    assert saqlangan == hisobla(), (
        "Etalon eskirgan: `python -m scripts.portfel_fixtures` ni ishga tushiring"
    )


def test_etalon_muhim_holatlarni_qamraydi() -> None:
    saqlangan = json.loads(FAYL.read_text(encoding="utf-8"))
    nomlar = {h["nom"] for h in saqlangan}

    # Bo'sh ekran — eng ko'p uchraydigan va eng oson buziladigan holat.
    assert "bosh" in nomlar
    # Narxi olinmagan ochiq savdo "+$0.00" bo'lib ko'rinmasligi kerak.
    assert "narxi_olinmagan_ochiq" in nomlar
    # Bitta signalning ikki qismi BITTA savdo sanaladi.
    assert "bitta_signal_ikki_qism" in nomlar

    bosh = next(h for h in saqlangan if h["nom"] == "bosh")
    assert bosh["kutilgan"]["bosh"] is True
    assert all(q["usd"] == 0 for q in bosh["kutilgan"]["qatorlar"])
