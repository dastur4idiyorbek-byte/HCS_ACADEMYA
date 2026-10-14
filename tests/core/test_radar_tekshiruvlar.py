"""Modul 4.0.0 — 7 tekshiruv: ball emas, sanoq (`docs/MODUL_4_0_0.md`, 5-6)."""

from __future__ import annotations

import dataclasses

from core.config.schema import RadarConfig
from core.portlash_radari import tekshiruvlar as tk
from core.portlash_radari.sozlama import standart
from core.portlash_radari.tekshiruvlar import HA, MALUMOT_YOQ, YOQ, CoinMalumoti

CH = standart(RadarConfig())


def coin(**kw: object) -> CoinMalumoti:
    return CoinMalumoti(symbol="LSKUSDT", belgi="LSK", **kw)  # type: ignore[arg-type]


def test_lsk_namunasi_5_dan_7() -> None:
    """Spetsifikatsiyadagi LSK misoli: 5/7, harakat 3/3, yoqilg'i 2/4."""
    c = coin(
        narx=1.2, ozgarish_24s=287.0, hajm_24s=82e6, ortacha_30k=10e6, tarix_kunlar=30,
        funding_stavka=-0.0034, funding_oraliq_soat=8,
        oi_qatorlar=(100.0, 110.0, 141.0), long_short=1.8, btc_ozgarish=-0.7,
        aylanma_pct=70.6,
    )
    natija = tk.hammasi(c, CH)
    assert [x.kod for x in natija] == [k for k, _ in tk.TEKSHIRUVLAR]
    holatlar = {x.kod: x.holat for x in natija}
    assert holatlar == {
        "hajm": HA, "narx": HA, "funding": HA, "oi": HA,
        "long_short": YOQ, "btc": HA, "taminot": YOQ,
    }
    sanoq = tk.sana(natija)
    assert (sanoq.tasdiq, sanoq.harakat, sanoq.yoqilgi, sanoq.malumot_yoq) == (5, 3, 2, 0)


def test_hech_narsa_bilinmasa_hammasi_malumot_yoq() -> None:
    natija = tk.hammasi(coin(), CH)
    assert all(x.holat == MALUMOT_YOQ for x in natija)
    assert tk.sana(natija).tasdiq == 0


def test_hajm_yangi_listingda_malumot_yoq() -> None:
    t = tk.hajm(coin(hajm_24s=9e6, ortacha_30k=1e6, tarix_kunlar=3), CH)
    assert t.holat == MALUMOT_YOQ
    assert t.qoshimcha == {"kunlar": 3}
    assert tk.hajm(coin(hajm_24s=5e6, ortacha_30k=1e6, tarix_kunlar=30), CH).holat == HA
    assert tk.hajm(coin(hajm_24s=4.9e6, ortacha_30k=1e6, tarix_kunlar=30), CH).holat == YOQ


def test_narx_ikkala_tomonga() -> None:
    assert tk.narx(coin(ozgarish_24s=-25.0), CH).holat == HA
    assert tk.narx(coin(ozgarish_24s=19.9), CH).holat == YOQ


def test_funding_8_soatga_keltiriladi() -> None:
    """4 soatlik oraliqda 0.06% = 8 soatlikda 0.12% -> ✅ (chegara 0.1%)."""
    t = tk.funding(coin(funding_stavka=0.0006, funding_oraliq_soat=4), CH)
    assert t.holat == HA
    assert round(t.qiymat, 6) == 0.12
    assert t.qoshimcha == {"oraliq_soat": 4, "xom_pct": 0.06}
    # 8 soatlikda o'sha stavka chegaradan past
    assert tk.funding(coin(funding_stavka=0.0006, funding_oraliq_soat=8), CH).holat == YOQ
    # salbiy funding ham
    assert tk.funding(coin(funding_stavka=-0.002), CH).holat == HA


def test_funding_oraligi_nol_bolsa_standart() -> None:
    assert tk.funding_8s(0.001, 0) == tk.funding_8s(0.001, 8)


def test_oi_faqat_osish_va_kontrakt_sonida() -> None:
    assert tk.oi(coin(oi_qatorlar=(100.0, 130.0)), CH).holat == HA
    assert tk.oi(coin(oi_qatorlar=(100.0, 60.0)), CH).holat == YOQ
    t = tk.oi(coin(oi_qatorlar=(100.0,)), CH)
    assert t.holat == MALUMOT_YOQ
    assert tk.oi(coin(oi_qatorlar=(0.0, 50.0)), CH).holat == MALUMOT_YOQ
    assert tk.oi(coin(oi_qatorlar=tuple(range(1, 10))), CH).qoshimcha == {"soat": 8}


def test_long_short_istalgan_tomonga() -> None:
    assert tk.long_short(coin(long_short=2.5), CH).holat == HA
    assert tk.long_short(coin(long_short=0.4), CH).holat == HA  # 1:2.5
    assert tk.long_short(coin(long_short=1.8), CH).holat == YOQ
    assert tk.long_short(coin(long_short=0.0), CH).holat == MALUMOT_YOQ


def test_btc_farqi() -> None:
    assert tk.btc(coin(ozgarish_24s=10.0, btc_ozgarish=-6.0), CH).holat == HA
    assert tk.btc(coin(ozgarish_24s=10.0, btc_ozgarish=-4.0), CH).holat == YOQ
    assert tk.btc(coin(ozgarish_24s=10.0), CH).holat == MALUMOT_YOQ


def test_taminot_past_aylanma_yoki_unlock() -> None:
    assert tk.taminot(coin(aylanma_pct=55.0), CH).holat == HA
    assert tk.taminot(coin(aylanma_pct=70.6), CH).holat == YOQ
    # aylanma noma'lum, lekin yaqin katta unlock
    assert tk.taminot(coin(unlock_kun=3, unlock_pct=6.0), CH).holat == HA
    # aylanma noma'lum, unlock kichik -> xulosa yo'q
    assert tk.taminot(coin(unlock_kun=3, unlock_pct=1.0), CH).holat == MALUMOT_YOQ
    # aylanma yuqori, lekin unlock uzoq
    assert tk.taminot(coin(aylanma_pct=90.0, unlock_kun=30, unlock_pct=20.0), CH).holat == YOQ


def test_qattiq_90_foiz_filtri_yoq() -> None:
    """LSK darsi: 70.6% aylanma coinni CHETLATMAYDI, faqat ❌ bo'ladi."""
    natija = tk.hammasi(coin(aylanma_pct=70.6, ozgarish_24s=50.0, btc_ozgarish=0.0), CH)
    assert tk.sana(natija).tasdiq == 2


def test_chegara_sozlamadan_olinadi() -> None:
    ch = dataclasses.replace(CH, narx_ozgarish_pct=50.0)
    assert tk.narx(coin(ozgarish_24s=40.0), ch).holat == YOQ
    assert tk.narx(coin(ozgarish_24s=40.0), ch).chegara == 50.0


def test_lugat_json_ga_tayyor() -> None:
    import json

    t = tk.hajm(coin(hajm_24s=8.21234567e6, ortacha_30k=1e6, tarix_kunlar=30), CH)
    d = t.lugat()
    assert set(d) == {"kod", "guruh", "holat", "qiymat", "chegara", "manba", "qoshimcha"}
    assert d["qiymat"] == 8.2123
    json.dumps(d)
