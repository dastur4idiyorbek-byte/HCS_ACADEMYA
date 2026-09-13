"""Sektor rotatsiyasi va Token Unlock — jonli manbalarni o'qish.

TARMOQQA CHIQMAYDI. `_json` soxta javob bilan almashtiriladi.
Bu testlar HTTP ni emas, MA'LUMOTNI O'QISHNI tekshiradi.
"""

from __future__ import annotations

import asyncio
import time

from core.config.schema import MarketDataConfig
from core.watch_panel.fundamental_manba import FundamentalManba
from core.watch_panel.sektor_xaritasi import SEKTOR, slug
from core.watch_panel.unlock_manba import UZOQ_CHEGARA_KUN, UnlockManba


def yur(korutina):  # noqa: ANN001, ANN201
    return asyncio.run(korutina)


def manba(javoblar: dict[str, object]) -> FundamentalManba:
    m = FundamentalManba(MarketDataConfig())

    async def soxta(manzil: str, parametr: dict | None = None):  # noqa: ANN202, ARG001
        for kalit, javob in javoblar.items():
            if kalit in manzil:
                return javob
        return None

    m._json = soxta  # type: ignore[assignment]
    return m


def unlock_manba(javob: object) -> UnlockManba:
    m = UnlockManba()

    async def soxta(manzil: str):  # noqa: ANN202, ARG001
        return javob

    m._json = soxta  # type: ignore[assignment]
    return m


def kun_keyin(kun: float) -> float:
    return time.time() + kun * 86400.0


# --------------------------------------------------------------------------- #
#  Sektor rotatsiyasi
# --------------------------------------------------------------------------- #


def sektor_javobi() -> dict[str, object]:
    return {
        "coins/categories": [
            {"id": "oracle", "name": "Oracle", "market_cap_change_24h": 5.0},
            {"id": "storage", "name": "Storage", "market_cap_change_24h": -3.0},
        ],
        "global": {"data": {"market_cap_change_percentage_24h_usd": 1.0}},
    }


def test_sektor_bozordan_kuchli_bolsa_HA() -> None:
    jadval = yur(manba(sektor_javobi()).sektor_jadvali())
    # LINK -> oracle: +5% vs bozor +1%
    assert jadval.kuchli("LINK") is True


def test_sektor_bozordan_zaif_bolsa_YOQ() -> None:
    jadval = yur(manba(sektor_javobi()).sektor_jadvali())
    # FIL -> storage: -3% vs bozor +1%
    assert jadval.kuchli("FIL") is False


def test_sektor_MUTLAQ_emas_NISBIY_olchanadi() -> None:
    """Hamma o'sgan kunda sekin o'sgan sektor — ORQADA.

    Agar kod bozor etalonini unutib, faqat "sektor musbatmi" deb
    qarasa, bu test yiqiladi: +2% musbat, lekin bozor +9%.
    """
    javob = {
        "coins/categories": [{"id": "oracle", "market_cap_change_24h": 2.0}],
        "global": {"data": {"market_cap_change_percentage_24h_usd": 9.0}},
    }
    assert yur(manba(javob).sektor_jadvali()).kuchli("LINK") is False


def test_xaritada_yoq_coin_None() -> None:
    jadval = yur(manba(sektor_javobi()).sektor_jadvali())
    assert jadval.kuchli("YOQCOIN") is None


def test_bozor_etaloni_yoq_bolsa_None() -> None:
    """Etalonsiz "kuchli" deyishning ma'nosi yo'q."""
    javob = {"coins/categories": [{"id": "oracle", "market_cap_change_24h": 5.0}]}
    assert yur(manba(javob).sektor_jadvali()).kuchli("LINK") is None


def test_sektor_manbasi_yiqilsa_hammasi_None() -> None:
    for javob in ({}, {"coins/categories": None, "global": None}):
        jadval = yur(manba(javob).sektor_jadvali())
        assert jadval.kuchli("LINK") is None
        assert jadval.ozgarishlar == {}


def test_kategoriya_NOMI_bilan_ham_topiladi() -> None:
    """Javobda `id` bo'lmasa, nomdan yasalgan slug ishlaydi."""
    javob = {
        "coins/categories": [{"name": "Oracle", "market_cap_change_24h": 7.0}],
        "global": {"data": {"market_cap_change_percentage_24h_usd": 1.0}},
    }
    assert yur(manba(javob).sektor_jadvali()).kuchli("LINK") is True


def test_nomalum_idlar_manba_yiqilganda_BOSH() -> None:
    """Tarmoq yo'qligi "xarita xato" degan ogohlantirishga aylanmasin."""
    assert yur(manba({}).sektor_jadvali()).nomalum_idlar == ()


def test_nomalum_idlar_haqiqatan_topilmaganini_koorsatadi() -> None:
    jadval = yur(manba(sektor_javobi()).sektor_jadvali())
    nomalum = jadval.nomalum_idlar
    assert "oracle" not in nomalum
    assert "storage" not in nomalum
    assert "layer-1" in nomalum


def test_slug_nomni_identifikatorga_aylantiradi() -> None:
    assert slug("Layer 2 (L2)") == "layer-2-l2"
    assert slug("  Oracle  ") == "oracle"


def test_xaritadagi_idlar_TASDIQLANGAN_royxatdan_olinadi() -> None:
    """Identifikator o'ylab topilmasin.

    Loyihada allaqachon ishlaydigan ro'yxat bor:
    `web/src/lib/sektorlar.ts` dagi `KORSATILADIGAN_SEKTORLAR`.
    U bozor ko'rinishi sahifasida CoinGecko javobiga tushadi, ya'ni
    bu identifikatorlar HAQIQATAN mavjud ekani tasdiqlangan.

    Agar xaritaga o'ylab topilgan identifikator yozilsa, u jimgina
    MALUMOT_YOQ berardi va coin sektorsiz qolardi — hech kim
    sezmasdi. Shuning uchun test.
    """
    import re
    from pathlib import Path

    manba = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "sektorlar.ts"
    tasdiqlangan = set(re.findall(r'\{\s*id:\s*"([^"]+)"', manba.read_text()))
    assert tasdiqlangan, "sektorlar.ts dan identifikatorlar o'qilmadi"

    begona = sorted(set(SEKTOR.values()) - tasdiqlangan)
    assert begona == [], f"tasdiqlanmagan identifikator: {begona}"


def test_xarita_faqat_kuzatiladigan_coinlarni_ozida_saqlaydi() -> None:
    """Xaritada begona symbol qolib ketmasin."""
    from core.config.schema import ZanjirConfig

    coinlar = set(ZanjirConfig().kuzatiladigan_coinlar)
    ortiqcha = sorted(set(SEKTOR) - coinlar)
    assert ortiqcha == [], f"ro'yxatda yo'q symbol: {ortiqcha}"


# --------------------------------------------------------------------------- #
#  Token Unlock
# --------------------------------------------------------------------------- #


def test_unlock_kun_va_foiz_hisoblanadi() -> None:
    javob = [
        {
            "name": "Aptos",
            "tSymbol": "APT",
            "circSupply": 1000.0,
            "upcomingEvent": [{"timestamp": kun_keyin(3), "noOfTokens": [60.0]}],
        }
    ]
    jadval = yur(unlock_manba(javob).jadval())
    assert jadval["APT"].kun_qoldi == 3
    assert jadval["APT"].pct == 6.0


def test_unlock_bir_hodisadagi_ULUSHLAR_qoshiladi() -> None:
    """`noOfTokens` ro'yxat: jamoa + investor + ekotizim."""
    javob = [
        {
            "tSymbol": "SUI",
            "circSupply": 1000.0,
            "upcomingEvent": [{"timestamp": kun_keyin(2), "noOfTokens": [10.0, 20.0, 5.0]}],
        }
    ]
    assert yur(unlock_manba(javob).jadval())["SUI"].pct == 3.5


def test_otib_ketgan_hodisa_olinmaydi() -> None:
    javob = [
        {
            "tSymbol": "APT",
            "circSupply": 1000.0,
            "events": [
                {"timestamp": kun_keyin(-5), "noOfTokens": [900.0]},
                {"timestamp": kun_keyin(20), "noOfTokens": [10.0]},
            ],
        }
    ]
    jadval = yur(unlock_manba(javob).jadval())
    assert jadval["APT"].kun_qoldi == 20
    assert jadval["APT"].pct == 1.0


def test_juda_uzoqdagi_unlock_tashlanadi() -> None:
    javob = [
        {
            "tSymbol": "APT",
            "circSupply": 1000.0,
            "upcomingEvent": [
                {"timestamp": kun_keyin(UZOQ_CHEGARA_KUN + 10), "noOfTokens": [10.0]}
            ],
        }
    ]
    assert yur(unlock_manba(javob).jadval()) == {}


def test_eng_yaqin_hodisa_qoladi() -> None:
    javob = [
        {
            "tSymbol": "APT",
            "circSupply": 1000.0,
            "events": [{"timestamp": kun_keyin(40), "noOfTokens": [10.0]}],
        },
        {
            "tSymbol": "apt",
            "circSupply": 1000.0,
            "events": [{"timestamp": kun_keyin(4), "noOfTokens": [10.0]}],
        },
    ]
    assert yur(unlock_manba(javob).jadval())["APT"].kun_qoldi == 4


def test_supply_yoq_bolsa_sana_qoladi_foiz_None() -> None:
    """Sana bor, hajm yo'q — to'siq ishlamaydi, lekin belgi ko'rinadi."""
    javob = [{"tSymbol": "APT", "upcomingEvent": [{"timestamp": kun_keyin(3)}]}]
    hodisa = yur(unlock_manba(javob).jadval())["APT"]
    assert hodisa.kun_qoldi == 3
    assert hodisa.pct is None


def test_javob_lugat_korinishida_ham_oqiladi() -> None:
    """DefiLlama javobni `{"protocols": [...]}` qilib ham beradi."""
    ichki = [
        {
            "tSymbol": "APT",
            "circSupply": 100.0,
            "upcomingEvent": [{"timestamp": kun_keyin(1), "noOfTokens": [1.0]}],
        }
    ]
    assert yur(unlock_manba({"protocols": ichki}).jadval())["APT"].kun_qoldi == 1


def test_buzuq_javob_bosh_jadval() -> None:
    for javob in (None, [], {}, "matn", [1, 2, 3], [{"tSymbol": "APT"}]):
        assert yur(unlock_manba(javob).jadval()) == {}


# --------------------------------------------------------------------------- #
#  Blokka ulanishi
# --------------------------------------------------------------------------- #


def test_yaqin_va_katta_unlock_QATTIQ_TOSIQ_beradi() -> None:
    """Endi to'siq haqiqatan ishlaydi — ilgari kalendar yo'q edi."""
    from core.analysis.fundamental.catalyst_watch import Katalizator, katalizator

    _, tosiq = katalizator(Katalizator(unlock_kun=3, unlock_ulush_pct=12.0))
    assert tosiq is not None


def test_sektor_kayfiyat_ovoziga_qoshiladi() -> None:
    """F&G yolg'iz qolmaydi: endi 2 ta o'lchangan ovoz bor."""
    from core.analysis.fundamental.sentiment_sector import Kayfiyat, kayfiyat

    natija = kayfiyat(Kayfiyat(fear_greed=30, sektor_kuchli=True))
    assert natija.olchandi
    assert "sektor kuchli" in natija.izoh
