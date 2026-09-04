"""O'lchov skriptlarining tuzilishi — ular natijaga TA'SIR QILMASLIGI kerak.

Skript strategiyani o'zgartirsa, o'lchov o'z-o'zini o'lchagan bo'lardi.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.zanjir_ablatsiya import SEZILARSIZ, TEKSHIRUVLAR
from scripts.zanjir_backtest import BLOK_TEKSHIRUVLARI
from scripts.zanjir_umumiy import Olchov, csv_saqla, jadval
from scripts.zanjir_walk_forward import bolaklar

ILDIZ = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
#  Ablatsiya ro'yxati kod bilan MOS kelishi kerak
# --------------------------------------------------------------------------- #


def test_ablatsiya_royxati_16_ta() -> None:
    """4 blok × 4 ichki tekshiruv (2-prompt, 8-qism, 3-band)."""
    assert len(TEKSHIRUVLAR) == 16


def test_ablatsiya_kalitlari_kodda_mavjud() -> None:
    """Nomi noto'g'ri yozilgan kalit JIMGINA hech narsani o'chirmasdi.

    Natijada "bu tekshiruv hissa qo'shmaydi" degan YOLG'ON xulosa
    chiqardi — aslida u umuman o'chirilmagan edi.
    """
    manba = ""
    for papka in ("fundamental", "structure", "zone_quality", "confirmation"):
        for fayl in (ILDIZ / "core" / "analysis" / papka).glob("*.py"):
            manba += fayl.read_text(encoding="utf-8")

    yetishmayotgan = [k for _, k in TEKSHIRUVLAR if f'"{k}"' not in manba]
    assert not yetishmayotgan, f"Kodda topilmadi: {yetishmayotgan}"


def test_ablatsiya_kalitlari_takrorlanmaydi() -> None:
    kalitlar = [k for _, k in TEKSHIRUVLAR]
    assert len(kalitlar) == len(set(kalitlar))


def test_sezilarsiz_chegara_promptdagidek() -> None:
    """Promptda "PF 0.00-0.03 farq qilsa" deyilgan."""
    assert pytest.approx(0.03) == SEZILARSIZ


def test_blok_tekshiruvlari_ablatsiya_bilan_mos() -> None:
    """Bosqichma-bosqich backtest AYNAN shu 16 tani biladi."""
    hammasi = set().union(*BLOK_TEKSHIRUVLARI.values())
    ablatsiya = {k for _, k in TEKSHIRUVLAR}
    # `yangi_coin_naqshi` — 17-chi, faqat yangi coinlarda
    assert ablatsiya <= hammasi
    assert hammasi - ablatsiya == {"yangi_coin_naqshi"}


# --------------------------------------------------------------------------- #
#  Skriptlar strategiyaga tegmaydi
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "skript",
    ["zanjir_backtest.py", "zanjir_ablatsiya.py", "zanjir_walk_forward.py"],
)
def test_skript_config_qiymatlarini_ozgartirmaydi(skript: str) -> None:
    """Bu uch skript sozlamani QO'LDA o'zgartirmasligi kerak.

    Ular STRATEGIYANI o'lchaydi, ya'ni strategiya o'zgarmas bo'lishi
    shart. Yagona ruxsat etilgan o'zgarish — `ochirilgan_tekshiruvlar`
    orqali ablatsiya.

    `zanjir_chegara.py` bu ro'yxatda YO'Q va bu ataylab: uning
    butun vazifasi — chegarani surib o'lchash. Uning o'zi
    `test_chegara_faqat_darajalarni_suradi` bilan qulflangan.
    """
    manba = (ILDIZ / "scripts" / skript).read_text(encoding="utf-8")
    daraxt = ast.parse(manba)
    for tugun in ast.walk(daraxt):
        if isinstance(tugun, ast.Call):
            nom = getattr(tugun.func, "attr", getattr(tugun.func, "id", ""))
            assert nom != "replace", (
                f"{skript} `dataclasses.replace` ishlatmoqda — "
                "o'lchov sozlamani o'zgartirmasligi kerak"
            )


def test_chegara_faqat_darajalarni_suradi() -> None:
    """Chegara skripti FAQAT `zanjir.darajalar` ni o'zgartirsin.

    U bloklarga yoki chiqish rejasiga tegsa, o'lchov "qaysi
    o'zgarish ta'sir qildi" savolini javobsiz qoldirardi.
    """
    from core.config.loader import load_config
    from scripts.zanjir_chegara import _variantlar

    asos = load_config()
    for nom, variant in _variantlar(asos):
        assert variant.zanjir.bloklar == asos.zanjir.bloklar, nom
        assert variant.zanjir.chiqish == asos.zanjir.chiqish, nom
        assert variant.zanjir.timeframelar == asos.zanjir.timeframelar, nom
        assert variant.risk_engine == asos.risk_engine, nom
        assert variant.backtest == asos.backtest, nom


def test_chegara_variantlari_bittadan_ozgaradi() -> None:
    """Ikkala raqam BIRGA surilmaydi — aks holda sabab noma'lum qolardi."""
    from core.config.loader import load_config
    from scripts.zanjir_chegara import _variantlar

    asos = load_config().zanjir.darajalar
    for nom, variant in _variantlar(load_config())[1:]:
        d = variant.zanjir.darajalar
        farqlar = sum([
            d.stop_eng_kam_pct != asos.stop_eng_kam_pct,
            d.tp1_eng_kam_nisbat != asos.tp1_eng_kam_nisbat,
            d.stop_eng_kop_pct != asos.stop_eng_kop_pct,
            d.tp_eng_kop != asos.tp_eng_kop,
        ])
        assert farqlar == 1, f"{nom}: {farqlar} ta raqam o'zgardi"


# --------------------------------------------------------------------------- #
#  Jadval va CSV
# --------------------------------------------------------------------------- #


def _olchov(nom: str = "test", pf: float = 1.5) -> Olchov:
    return Olchov(
        nom=nom, signal=100, foydali_pct=40.0, profit_factor=pf,
        ortacha_pct=0.5, jami_pct=50.0, pasayish_pct=10.0,
    )


def test_jadval_barcha_qatorlarni_chizadi() -> None:
    matn = jadval([_olchov("a"), _olchov("b")])
    assert "a" in matn
    assert "b" in matn
    assert "PF" in matn


def test_cheksiz_pf_belgi_bilan() -> None:
    """Zararsiz variantda PF cheksiz — `inf` deb chizilmasin."""
    assert "∞" in jadval([_olchov(pf=float("inf"))])


def test_csv_saqlanadi(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr("scripts.zanjir_umumiy.HISOBOT_PAPKA", tmp_path)
    yol = csv_saqla("sinov.csv", [_olchov()])
    assert yol.exists()
    matn = yol.read_text(encoding="utf-8")
    assert "konfiguratsiya" in matn
    assert "test" in matn


# --------------------------------------------------------------------------- #
#  Walk-forward bo'laklari
# --------------------------------------------------------------------------- #


def test_bolaklar_kesishmaydi() -> None:
    """Bitta savdo ikki oynaga tushmasligi kerak."""
    from datetime import UTC, datetime, timedelta

    vaqtlar = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=i) for i in range(90)]
    qismlar = bolaklar(vaqtlar, 3)
    assert len(qismlar) == 3
    for a, b in zip(qismlar, qismlar[1:], strict=False):
        assert a.oxiri < b.boshi


def test_bolaklar_butun_oynani_qamraydi() -> None:
    from datetime import UTC, datetime, timedelta

    vaqtlar = [datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=i) for i in range(90)]
    qismlar = bolaklar(vaqtlar, 3)
    assert qismlar[0].boshi == vaqtlar[0]
    assert qismlar[-1].oxiri == vaqtlar[-1]


def test_kam_malumotda_bolak_yoq() -> None:
    from datetime import UTC, datetime

    assert bolaklar([datetime(2024, 1, 1, tzinfo=UTC)], 3) == []


# --------------------------------------------------------------------------- #
#  Xulosa YASHIRMASLIGI kerak
# --------------------------------------------------------------------------- #


def test_walk_forward_chetlatilgan_oynani_aytadi(capsys) -> None:  # noqa: ANN001
    """Kam savdoli oyna xulosadan chiqariladi, lekin YASHIRILMAYDI.

    Bir marta bu funksiya uchinchi oynani (7 savdo, PF 0.59) jimgina
    tashlab, "barcha oynada PF ≥ 1.0" deb yozgan edi — o'z jadvaliga
    zid gap.
    """
    from scripts.zanjir_walk_forward import _xulosa

    _xulosa([
        Olchov("oyna 1", 21, 47.6, 1.72, 1.98, 41.5, 17.3),
        Olchov("oyna 2", 16, 56.2, 2.35, 3.00, 48.0, 21.4),
        Olchov("oyna 3", 7, 42.9, 0.59, -1.00, -7.0, 9.8),
    ])
    chiqish = capsys.readouterr().out

    assert "oyna 3" in chiqish
    assert "0.59" in chiqish
    # Eski, YOLG'ON da'vo qaytmasin
    assert "🟢 Barcha oynada" not in chiqish
    # Va o'quvchi chetlatish bo'lganini bilsin
    assert "DIQQAT" in chiqish


def test_ablatsiya_kam_savdoda_xulosa_chiqarmaydi(capsys) -> None:  # noqa: ANN001
    """35 savdoda "hissa qo'shmaydi" degan gap tasodifdan farq qilmaydi."""
    from scripts.zanjir_ablatsiya import ISHONCHLI_SAVDO, _xulosa

    _xulosa(
        Olchov("TAYANCH", 35, 48.6, 1.83, 2.10, 73.5, 30.7),
        [Olchov("— 1.1", 35, 48.6, 1.83, 2.10, 73.5, 30.7)],
    )
    chiqish = capsys.readouterr().out

    assert str(ISHONCHLI_SAVDO) in chiqish
    assert "HISSA QO'SHMAYDI" not in chiqish


def test_rad_sababi_raqamsiz_guruhlanadi() -> None:
    """Ansiz voronka o'nlab "1 × ..." qatoriga aylanardi."""
    from core.backtest.zanjir_engine import _sabab_turi

    assert _sabab_turi("stop juda yaqin (2.60%)") == "stop juda yaqin"
    assert _sabab_turi("TP1/Stop nisbati past (0.71)") == "TP1/Stop nisbati past"
    assert _sabab_turi(None) == "nomalum"


# --------------------------------------------------------------------------- #
#  Nomzod chegara — faqat BAYROQ bilan
# --------------------------------------------------------------------------- #


def test_bayroqsiz_chegara_ozgarmaydi() -> None:
    """Bayroq berilmasa sozlama TEGILMAYDI.

    Bu — `test_skript_config_qiymatlarini_ozgartirmaydi` bilan bitta
    qoidaning ikki tomoni: o'lchov strategiyani jimgina o'zgartira
    olmaydi. O'zgarish faqat ATAYLAB, komanda qatorida ko'rinib
    turgan holda bo'ladi.
    """
    from core.config.loader import load_config
    from scripts.zanjir_umumiy import chegara_qolla, umumiy_argumentlar

    asos = load_config()
    bosh = umumiy_argumentlar("x").parse_args([])
    assert chegara_qolla(asos, bosh) is asos


def test_bayroq_faqat_darajalarga_tegadi() -> None:
    from core.config.loader import load_config
    from scripts.zanjir_umumiy import chegara_qolla, umumiy_argumentlar

    asos = load_config()
    argumentlar = umumiy_argumentlar("x").parse_args(
        ["--stop-eng-kam", "0.5", "--tp1-nisbat", "1.5"]
    )
    yangi = chegara_qolla(asos, argumentlar)

    assert yangi.zanjir.darajalar.stop_eng_kam_pct == pytest.approx(0.5)
    assert yangi.zanjir.darajalar.tp1_eng_kam_nisbat == pytest.approx(1.5)
    assert yangi.zanjir.bloklar == asos.zanjir.bloklar
    assert yangi.zanjir.chiqish == asos.zanjir.chiqish
    assert yangi.risk_engine == asos.risk_engine


def test_bitta_bayroq_ikkinchisiga_tegmaydi() -> None:
    from core.config.loader import load_config
    from scripts.zanjir_umumiy import chegara_qolla, umumiy_argumentlar

    asos = load_config()
    argumentlar = umumiy_argumentlar("x").parse_args(["--stop-eng-kam", "1.0"])
    yangi = chegara_qolla(asos, argumentlar)

    assert yangi.zanjir.darajalar.stop_eng_kam_pct == pytest.approx(1.0)
    assert (
        yangi.zanjir.darajalar.tp1_eng_kam_nisbat
        == asos.zanjir.darajalar.tp1_eng_kam_nisbat
    )


def test_pasayish_1_dan_pastga_otmasa_qizil_emas(capsys) -> None:  # noqa: ANN001
    """3.18 → 2.78 va 1.00 → 0.69 — BIR XIL BELGI bilan atalmasin.

    Birinchisida uchala oyna ham foydali, ikkinchisida ustunlik
    yo'qolgan. Ikkalasini "sozlama o'tmishga moslashgan" deb
    belgilash — yolg'on.
    """
    from scripts.zanjir_walk_forward import _xulosa

    _xulosa([
        Olchov("oyna 1", 79, 62.0, 3.18, 2.14, 169.4, 20.4),
        Olchov("oyna 2", 62, 64.5, 3.07, 1.81, 112.3, 22.4),
        Olchov("oyna 3", 79, 67.1, 2.78, 1.05, 83.2, 7.8),
    ])
    chiqish = capsys.readouterr().out

    assert "🟡" in chiqish
    assert "o'tmishga moslashgan" not in chiqish
    # Bitta savdodagi natija ham ko'rsatilsin — u PF dan tezroq pasaygan
    assert "+2.14%" in chiqish and "+1.05%" in chiqish


def test_ustunlik_yoqolsa_qizil(capsys) -> None:  # noqa: ANN001
    """Eski tizimni o'ldirgan naqsh — 1.0 dan PASTGA o'tish."""
    from scripts.zanjir_walk_forward import _xulosa

    _xulosa([
        Olchov("oyna 1", 50, 40.0, 1.00, 0.0, 0.0, 10.0),
        Olchov("oyna 2", 50, 38.0, 0.84, -0.4, -20.0, 15.0),
        Olchov("oyna 3", 50, 35.0, 0.69, -0.8, -40.0, 25.0),
    ])
    chiqish = capsys.readouterr().out

    assert "🔴" in chiqish
    assert "o'ldirgan naqsh" in chiqish


def test_bosh_tekshiruvlar_ablatsiya_royxatida_bor() -> None:
    """11 ta "bo'sh" tekshiruv nomi ablatsiya kalitlariga MOS kelsin.

    Nomi noto'g'ri yozilgan kalit jimgina hech narsani o'chirmasdi va
    "birga o'chirilganda ham natija bir xil" degan YOLG'ON xulosa
    chiqardi.
    """
    from scripts.zanjir_backtest import BOSH_TEKSHIRUVLAR

    kalitlar = {k for _, k in TEKSHIRUVLAR}
    assert kalitlar >= BOSH_TEKSHIRUVLAR
    assert len(BOSH_TEKSHIRUVLAR) == 11


def test_chegara_yorligi_configdan_oqiladi() -> None:
    """Yorliq qotib qolmasin — config o'zgarsa jadval yolg'on gapirardi."""
    from core.config.loader import load_config
    from scripts.zanjir_chegara import _variantlar

    config = load_config()
    nom = _variantlar(config)[0][0]
    assert str(config.zanjir.darajalar.stop_eng_kam_pct) in nom
