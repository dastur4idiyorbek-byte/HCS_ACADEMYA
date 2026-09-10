"""Jonli sikl — yangi modulni haqiqiy bozorda yuritadi.

Bu kod REAL PUL bilan bog'liq signal chiqaradi. Uch narsa
kafolatlanishi kerak:

  1. Bitta coinda ikkita ochiq signal bo'lmaydi.
  2. Bitta coindagi xato butun siklni to'xtatmaydi.
  3. Jonli mantiq backtest mantig'i bilan BIR XIL oynada ishlaydi
     — aks holda o'lchangan natija jonli natijaga tegishli emas.
"""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta

import pytest

from core.config.loader import load_config
from core.domain.models import Candle
from core.services.zanjir_sikl import ASOSIY_OYNA, PASTKI_OYNA, SiklNatijasi, ZanjirSikl
from core.storage.zanjir_repository import CoinHolati

BOSH = datetime(2024, 1, 1, tzinfo=UTC)


def seriya(n: int, qadam: timedelta = timedelta(days=1)) -> list[Candle]:
    rnd = random.Random(11)
    narx = 100.0
    out = []
    for i in range(n):
        narx *= 1 + 0.0015 + 0.02 * math.sin(i / 9) + rnd.uniform(-0.012, 0.012)
        out.append(
            Candle(
                open_time=BOSH + qadam * i,
                open=narx,
                high=narx * 1.01,
                low=narx * 0.99,
                close=narx,
                volume=rnd.uniform(500, 2000),
            )
        )
    return out


class SoxtaProvayder:
    """Birjaga chiqmaydigan provayder."""

    def __init__(self, xato_beradigan: set[str] | None = None) -> None:
        self.sorovlar: list[tuple[str, str, int]] = []
        self._xato = xato_beradigan or set()

    async def fetch_candles(self, symbol, timeframe, limit, until=None):  # noqa: ANN001, ANN201
        self.sorovlar.append((symbol, timeframe, limit))
        if symbol in self._xato:
            raise RuntimeError("birja javob bermadi")
        qadam = timedelta(days=1) if timeframe.endswith("d") else timedelta(minutes=15)
        return seriya(limit, qadam)


class BoshNatija:
    """Hech narsa topmagan so'rov natijasi."""

    def scalars(self):  # noqa: ANN201
        return []

    def scalar_one_or_none(self):  # noqa: ANN201
        return None

    def all(self):  # noqa: ANN201
        return []


class SoxtaSessiya:
    async def __aenter__(self):  # noqa: ANN204
        return self

    async def __aexit__(self, *_):  # noqa: ANN002, ANN204
        return False

    async def execute(self, *_):  # noqa: ANN002, ANN202
        return BoshNatija()

    async def flush(self) -> None:
        return None

    def add(self, _obyekt) -> None:  # noqa: ANN001
        return None


class SoxtaBaza:
    """Faqat `session()` beradi — yozish testda tekshirilmaydi."""

    def __init__(self) -> None:
        self._sessiya = SoxtaSessiya()

    def session(self):  # noqa: ANN201
        return self._sessiya


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


def test_oyna_backtest_bilan_bir_xil() -> None:
    """Jonli sikl backtest bilan AYNAN bir xil oynani so'rasin.

    Boshqa oyna — boshqa indikator qiymati — boshqa qaror. U holda
    o'lchangan PF 3.49 jonli tizimga tegishli bo'lmasdi.
    """
    from core.backtest.zanjir_engine import ASOSIY_OYNA as BACKTEST_ASOSIY
    from core.backtest.zanjir_engine import PASTKI_OYNA as BACKTEST_PASTKI

    assert ASOSIY_OYNA == BACKTEST_ASOSIY
    assert PASTKI_OYNA == BACKTEST_PASTKI


def test_kuzatiladigan_coinlar_80_ta_halol(config) -> None:  # noqa: ANN001
    """Jonli ro'yxat 80 ta va o'lchangan 12 coinlik to'plamni qamraydi."""
    from scripts.zanjir_umumiy import OLCHOV_12

    assert len(config.zanjir.kuzatiladigan_coinlar) == 80
    assert set(OLCHOV_12) <= set(config.zanjir.kuzatiladigan_coinlar)


def test_royxat_hujjat_bilan_bir_xil(config) -> None:  # noqa: ANN001
    """Kod va hujjat ajralib ketmasin.

    `docs/HALOL_ROYXAT.md` har bir coinning NIMA UCHUN shu yerda
    ekanini saqlaydi: manba, sana, chiqarilganlarning sabablari,
    tasdiq holati. Kod esa faqat tickerlarni saqlaydi.

    Ikkalasi qo'lda yangilanadigan bo'lsa, bir kun kelib ular
    ajraladi va hech kim qaysi biri to'g'ri ekanini bilmaydi —
    "halol" deb yozilgan ro'yxatda esa bu jiddiy narsa. Shuning
    uchun ular shu yerda mexanik bog'lanadi.
    """
    import re
    from pathlib import Path

    hujjat = Path(__file__).resolve().parents[2] / "docs" / "HALOL_ROYXAT.md"
    matn = hujjat.read_text(encoding="utf-8")

    bolim = matn.split("## Ro'yxat (80 ta)")[1].split("---")[0]
    hujjatdagi = re.findall(r"\b[A-Z][A-Z0-9]{0,9}\b", bolim)

    kodagi = config.zanjir.kuzatiladigan_coinlar
    assert hujjatdagi == kodagi, (
        "docs/HALOL_ROYXAT.md va schema.py ajralib ketdi. "
        f"Faqat hujjatda: {sorted(set(hujjatdagi) - set(kodagi))}. "
        f"Faqat kodda: {sorted(set(kodagi) - set(hujjatdagi))}."
    )


def test_sikl_soat_musbat(config) -> None:  # noqa: ANN001
    assert config.zanjir.sikl_soat > 0


@pytest.mark.asyncio
async def test_bitta_coin_xatosi_siklni_toxtatmaydi(config) -> None:  # noqa: ANN001
    """ETH birjada yiqilsa, qolgan o'n bir coin baribir tekshirilsin.

    Ansiz bitta coinning vaqtinchalik xatosi butun sikl bo'yi
    signalsiz qoldirardi — va sabab loglarda ko'rinmasdi.
    """
    provayder = SoxtaProvayder(xato_beradigan={"ETH"})
    sikl = ZanjirSikl(config, provayder, SoxtaBaza())
    natija = SiklNatijasi()

    await sikl._bitta_coin("BTC", [], natija)
    with pytest.raises(RuntimeError):
        await sikl._bitta_coin("ETH", [], natija)

    assert natija.tekshirildi == 1


def test_natija_matni_sabab_korsatadi() -> None:
    """"Nega signal yo'q" savoliga hisobot javob bersin."""
    natija = SiklNatijasi(
        tekshirildi=12,
        ochiq_sababli_otkazildi=2,
        uzilishlar={"Struktura": 7},
        daraja_radlari={"stop juda yaqin": 3},
    )
    matn = natija.matn()
    assert "12 coin" in matn
    assert "Struktura" in matn
    assert "stop juda yaqin" in matn


# --------------------------------------------------------------------- #
#  Ekran uchun holat (4-prompt, 3-qism)
# --------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_har_bir_coin_uchun_EKRAN_holati_qaytadi(config) -> None:  # noqa: ANN001
    """Zanjir qayerda to'xtaganini ekran ko'rsata olishi kerak.

    Ilgari bu ma'lumot faqat LOGGA tushardi — ya'ni "hozir qaysi
    coin qaysi blokda to'xtadi" degan savolga javob berish uchun
    serverdagi matn faylni o'qish kerak edi.
    """
    sikl = ZanjirSikl(config, SoxtaProvayder(), SoxtaBaza())
    natija = SiklNatijasi()

    holat = await sikl._bitta_coin("BTC", [], natija)

    assert holat is not None
    assert holat.symbol == "BTC"
    assert holat.natija in {
        "signal",
        "zanjir_uzildi",
        "ishonch_past",
        "daraja_rad",
        "xato",
    }
    # Zanjir yurgan bo'lsa, bloklar ham qaytadi — ekran shulardan chiziladi.
    if holat.natija != "xato":
        assert holat.bloklar, "bloklar bo'sh — ekranda chizadigan narsa qolmaydi"
        for blok in holat.bloklar:
            assert blok.nom
            assert 0 <= blok.kuch <= blok.maxraj or blok.olchanmadi


@pytest.mark.asyncio
async def test_xato_bergan_coin_ham_ekranga_tushadi(config) -> None:  # noqa: ANN001
    """Xato ham HOLAT — ekranda "sabab noma'lum" bo'lib qolmasin."""
    sikl = ZanjirSikl(config, SoxtaProvayder(xato_beradigan={"ETH"}), SoxtaBaza())

    yozilgan: list = []

    async def yozishni_kuzat(holatlar):  # noqa: ANN001, ANN202
        yozilgan.extend(holatlar)

    sikl._holatlarni_yoz = yozishni_kuzat  # type: ignore[method-assign]
    natija = await sikl.yur()

    symbollar = {h.symbol for h in yozilgan}
    assert "ETH" in symbollar, "xato bergan coin ekranga tushmadi"
    eth = next(h for h in yozilgan if h.symbol == "ETH")
    assert eth.natija == "xato"
    assert "birja javob bermadi" in eth.izoh
    assert natija.xatolar["ETH"]


@pytest.mark.asyncio
async def test_holat_yozilmasa_ham_sikl_TUGAYDI(config) -> None:  # noqa: ANN001
    """Ekran ma'lumoti signalni yo'qotmasin.

    Holat yozuvi — faqat ko'rsatish uchun. Baza bilan muammo bo'lsa
    ekran eskiroq raqam ko'rsatadi, lekin sikl to'xtamasligi kerak.
    """

    class YiqiladiganBaza(SoxtaBaza):
        def session(self):  # noqa: ANN201
            raise RuntimeError("baza javob bermadi")

    sikl = ZanjirSikl(config, SoxtaProvayder(), YiqiladiganBaza())
    # `yur()` ochiq signallarni ham bazadan o'qiydi, shuning uchun
    # bu yerda faqat yozuv qismini sinaymiz.
    await sikl._holatlarni_yoz(
        [
            CoinHolati(
                symbol="BTC",
                bloklar=(),
                toliq=False,
                uzildi_blokda=None,
                ishonch=0.0,
                natija="xato",
            )
        ]
    )  # xato ko'tarilmasligi kerak


# --------------------------------------------------------------------------- #
#  O'sha zona ikkinchi marta signal bo'lmaydi (2026-09-10)
# --------------------------------------------------------------------------- #


def test_bir_xil_daraja_takrorlanmaydi() -> None:
    """Sikl 4 soatda bir marta yuradi, struktura esa o'zgarmaydi.

    Ochiq signal tekshiruvi buni to'smasdi: signal YOPILGAN bo'lsa
    (masalan bekor qilingan), coin darrov yana "bo'sh" bo'lib
    qolardi va o'sha signal qaytadan tug'ilardi.

    2026-09-10 da loyiha egasining ekranida bitta coin bitta foiz
    bilan o'nlab marta turardi.
    """
    from core.position.entry_stop_tp import Darajalar
    from core.services.zanjir_sikl import _bir_xil_daraja

    d = Darajalar(entry=100.0, stop=95.0, tplar=(110.0, 120.0))

    # AYNAN o'sha darajalar — takror
    assert _bir_xil_daraja(d, (100.0, 110.0))
    # Suzuvchi nuqta xatosi ham takror deb hisoblanadi
    assert _bir_xil_daraja(d, (100.00001, 110.00002))


def test_yangi_zona_signal_berishga_ruxsat_etiladi() -> None:
    """Bu QAT'IY FILTR EMAS: zona o'zgarsa, signal beriladi."""
    from core.position.entry_stop_tp import Darajalar
    from core.services.zanjir_sikl import _bir_xil_daraja

    d = Darajalar(entry=100.0, stop=95.0, tplar=(110.0, 120.0))

    assert not _bir_xil_daraja(d, (103.0, 110.0)), "entry o'zgardi — yangi signal"
    assert not _bir_xil_daraja(d, (100.0, 115.0)), "TP1 o'zgardi — yangi signal"
    # Oldingi signalda TP1 yo'q (eski yozuv) — to'smaydi
    assert not _bir_xil_daraja(d, (100.0, None))


@pytest.mark.asyncio
async def test_oxirgi_signallar_har_coindan_bittadan_beradi(tmp_path) -> None:  # noqa: ANN001
    """Repozitoriy har coin uchun ENG YANGI yozuvni qaytaradi."""
    from core.domain.enums import SignalSource
    from core.domain.models import signal_levels
    from core.storage import Database
    from core.storage.repositories import SignalRepository

    db = Database(f"sqlite+aiosqlite:///{tmp_path}/sinov.db")
    await db.init_models()

    async with db.session() as session:
        repo = SignalRepository(session)
        for tp1 in (110.0, 111.0, 112.0):
            await repo.create(
                symbol="TEST",
                levels=signal_levels(entry=100.0, stop=95.0, tp1=tp1, tp2=tp1 + 10),
                source=SignalSource.ZANJIR,
            )
        await repo.create(
            symbol="BOSHQA",
            levels=signal_levels(entry=50.0, stop=45.0, tp1=60.0, tp2=70.0),
            source=SignalSource.ZANJIR,
        )
        await session.commit()

    async with db.session() as session:
        oxirgi = await SignalRepository(session).oxirgi_signallar()

    assert set(oxirgi) == {"TEST", "BOSHQA"}
    # Uchtasidan ENG OXIRGISI — eng katta id
    assert oxirgi["TEST"].tp1 == 112.0
    await db.dispose()


# --------------------------------------------------------------------------- #
#  AVTOMATIK SIGNAL TO'XTATILGAN (2026-09-10)
# --------------------------------------------------------------------------- #

#: Zanjirni oxirigacha olib boradigan soxta natija.
#:
#: NIMA UCHUN QO'LDA QURILADI. `SoxtaProvayder` ning shamlari
#: Struktura blokida uziladi va SIGNAL YOZISH joyiga umuman
#: yetib bormaydi. Ya'ni oddiy sikl testi bu qarorni
#: TEKSHIRMAGAN bo'lardi — u har doim o'tardi, tekshiruv
#: o'chirilgan bo'lsa ham. Shuning uchun zanjir shu yerda
#: majburan "to'liq" qilinadi.


class _SoxtaZanjir:
    toliq = True
    uzildi_blokda = None
    bloklar = ()

    def ishonch(self) -> float:
        return 0.9

    def matn(self) -> str:
        return "sinov"


class _SoxtaNatija:
    def __init__(self, zona) -> None:  # noqa: ANN001
        self.zanjir = _SoxtaZanjir()
        self.zona_natija = type("ZonaNatija", (), {"zona": zona})()


def _zanjirni_toliq_qil(monkeypatch, zona) -> None:  # noqa: ANN001
    """Zanjir, darajalar va SI — hammasi "o'tdi" deb qaytsin."""
    from core.position.entry_stop_tp import Darajalar

    monkeypatch.setattr(
        "core.services.zanjir_sikl.zanjir_yur_alternativ",
        lambda _kirish: _SoxtaNatija(zona),
    )
    monkeypatch.setattr("core.services.zanjir_sikl._blok_holatlari", lambda _z: ())
    monkeypatch.setattr("core.services.zanjir_sikl.swinglar", lambda _s: ())
    monkeypatch.setattr(
        "core.services.zanjir_sikl.darajalar_qur",
        # `yaroqli` — hisoblanadigan xossa: `rad_sababi is None`.
        lambda *_a, **_k: Darajalar(entry=100.0, stop=97.0, tplar=(104.0, 110.0)),
    )

    async def _tasdiq(_kirish, _sozlama):  # noqa: ANN001, ANN202
        return type("AiNatija", (), {"tasdiqlandi": True, "sabab": ""})()

    monkeypatch.setattr("core.services.zanjir_sikl.ai_tekshir", _tasdiq)


@pytest.mark.asyncio
async def test_avtomatik_signal_ochiq_bolsa_signal_YOZILMAYDI(  # noqa: ANN201
    config, monkeypatch  # noqa: ANN001
):
    """Bayroq o'chiq — zanjir to'liq o'tsa ham signal yozilmaydi.

    2026-09-10 dagi qaror: to'rtta mustaqil o'lchov signallar zarar
    keltirishini ko'rsatdi, shuning uchun avtomatik yo'l to'sildi.

    Bu test o'sha qarorning QOROVULI: kimdir `SignalRepository.create`
    ni tekshiruvdan oldinga surib qo'ysa, shu yerda yiqiladi.
    """
    import dataclasses

    _zanjirni_toliq_qil(monkeypatch, zona=object())

    chaqirildi: list[str] = []

    async def _create(_self, **kwargs):  # noqa: ANN001, ANN202
        chaqirildi.append(kwargs["symbol"])
        return type("Yozuv", (), {"id": 1})()

    monkeypatch.setattr(
        "core.services.zanjir_sikl.SignalRepository.create", _create, raising=True
    )

    z = dataclasses.replace(
        config.zanjir, kuzatiladigan_coinlar=["BTC", "ETH"], avtomatik_signal=False
    )
    sikl = ZanjirSikl(dataclasses.replace(config, zanjir=z), SoxtaProvayder(), SoxtaBaza())
    natija = await sikl.yur()

    assert chaqirildi == [], f"signal yozildi: {chaqirildi}"
    assert natija.yangi_signallar == []
    # Va bu JIM o'tmasin — sanoq yuritilsin.
    assert natija.avtomatik_ochiq == 2, natija.matn()  # noqa: PLR2004
    assert "AVTOMATIK SIGNAL O'CHIQ" in natija.matn().upper()


@pytest.mark.asyncio
async def test_bayroq_yoqilsa_signal_yoziladi(config, monkeypatch) -> None:  # noqa: ANN001
    """Yuqoridagi test BEKORGA o'tmasin.

    Aynan shu soxta ma'lumot bilan, bayroq YOQILGANDA signal
    yozilishi kerak. Aks holda birinchi test hech narsani
    tekshirmagan bo'lardi — zanjir baribir uzilib ketardi.
    """
    import dataclasses

    _zanjirni_toliq_qil(monkeypatch, zona=object())

    chaqirildi: list[str] = []

    async def _create(_self, **kwargs):  # noqa: ANN001, ANN202
        chaqirildi.append(kwargs["symbol"])
        return type("Yozuv", (), {"id": len(chaqirildi)})()

    monkeypatch.setattr(
        "core.services.zanjir_sikl.SignalRepository.create", _create, raising=True
    )

    z = dataclasses.replace(
        config.zanjir, kuzatiladigan_coinlar=["BTC", "ETH"], avtomatik_signal=True
    )
    sikl = ZanjirSikl(dataclasses.replace(config, zanjir=z), SoxtaProvayder(), SoxtaBaza())
    natija = await sikl.yur()

    assert chaqirildi == ["BTC", "ETH"], f"signal yozilmadi: {natija.matn()}"
    assert len(natija.yangi_signallar) == 2  # noqa: PLR2004
    assert natija.avtomatik_ochiq == 0


def test_avtomatik_signal_OCHIQ_turibdi(config) -> None:  # noqa: ANN001
    """Qaror KODDA qulflangan bo'lsin.

    Bayroq tasodifan yoqib qo'yilsa — masalan sozlama fayli
    tahrirlansa — shu test aytadi. Qayta yoqishdan oldin o'lchov
    musbat natija berishi kerak.
    """
    assert config.zanjir.avtomatik_signal is False, (
        "Avtomatik signal yoqilgan. O'lchov musbat natija berdimi? "
        "docs/BACKTEST_NATIJA_2026-09-10_model2.md ga qarang."
    )
