"""Modul 4.0.0 — to'liq sessiya: soxta Binance + haqiqiy SQLite.

Tarmoq yo'q: `BinanceFutures._json` va `CoinGeckoTaminot._json`
almashtiriladi, qolgan hamma narsa (ajratish, darvoza, elak,
tekshiruv, o'rin, baza) haqiqiy kod.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from core.config.schema import AppConfig
from core.portlash_radari.manba import BinanceFutures, CoinGeckoTaminot
from core.portlash_radari.repository import RadarRepository
from core.portlash_radari.sessiya import RadarSessiyasi
from core.portlash_radari.vaqt import KASHFIYOT, QOLDA, TASDIQ, ms
from core.storage import Database
from core.storage.models import CoinRuling, RadarNatija, RadarSessiya, RadarYashirin

SHAM = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
HOZIR = SHAM - timedelta(minutes=15)


@dataclass
class Coin:
    symbol: str
    asosiy: str
    hajm: float
    ortacha: float | None
    ozgarish: float
    narx: float = 1.0
    funding: float | None = 0.0
    funding_soat: int | None = None
    oi: tuple[float, ...] = (100.0, 100.0)
    ls: float | None = 1.0
    onboard_kun: int = 400
    turi: str = "COIN"
    cg_cap: float | None = 50e6
    cg_aylanma: float | None = 90.0
    cg_narx: float | None = None


def bozor() -> dict[str, Coin]:
    coinlar = [
        Coin("BTCUSDT", "BTC", 10e9, 9e9, 1.0, narx=60000.0, cg_cap=1e12),
        # 5/7: hajm, narx, funding, oi, btc ✅ | long/short, ta'minot ❌
        Coin("LSKUSDT", "LSK", 82e6, 10e6, 287.0, narx=1.2, funding=-0.0034,
             oi=(100.0, 120.0, 141.0), ls=1.8, cg_cap=200e6, cg_aylanma=70.6),
        # 5/7, lekin YASHIRILADI
        Coin("ABCUSDT", "ABC", 4e6, 1e6, 25.0, narx=2.0, funding=0.0002, funding_soat=4,
             oi=(100.0, 135.0), ls=3.0, cg_aylanma=50.0),
        # elakdan o'tadi, lekin kapitalizatsiya $2 mln -> chetlatiladi
        Coin("TINYUSDT", "TINY", 6e6, 1e6, 40.0, cg_cap=2e6),
        # yangi listing: tarix yo'q, o'rtachasiz o'tadi
        Coin("NEWUSDT", "NEW", 3e6, None, 60.0, onboard_kun=5, cg_cap=None, cg_aylanma=None),
        # ko'paytirgichli nom, elakdan o'tadi
        Coin("1000PEPEUSDT", "1000PEPE", 35e6, 10e6, 5.0, narx=0.0101,
             cg_narx=0.0000101, cg_cap=4e9, cg_aylanma=99.0),
        # hajm darvozasidan o'tmaydi
        Coin("LOWUSDT", "LOW", 100e3, 10e3, 90.0),
        # stablecoin va coin bo'lmagan kontrakt — universumda yo'q
        Coin("USDCUSDT", "USDC", 500e6, 500e6, 0.0),
        Coin("XAUUSDT", "XAU", 900e6, 100e6, 1.0, turi="COMMODITY"),
    ]
    coinlar += [Coin(f"Q{i}USDT", f"Q{i}", 5e6, 5e6, 1.0) for i in range(15)]
    return {c.symbol: c for c in coinlar}


class SoxtaBinance(BinanceFutures):
    def __init__(self, coinlar: dict[str, Coin], soat: datetime) -> None:
        super().__init__("https://fapi.test", ["USDT", "USDC"], parallel=3)
        self.coinlar = coinlar
        self.soat = soat
        self.sorovlar: list[str] = []
        self.kodlar: dict[str, int] = {}

    async def _json(self, manzil, parametr=None):  # noqa: ANN001, ANN202
        yol = manzil.replace("https://fapi.test", "")
        self.sorovlar.append(yol)
        if yol in self.kodlar:
            return None, self.kodlar[yol]
        p = parametr or {}
        c = self.coinlar
        if yol == "/fapi/v1/exchangeInfo":
            return {"symbols": [
                {"symbol": x.symbol, "baseAsset": x.asosiy, "quoteAsset": "USDT",
                 "contractType": "PERPETUAL", "status": "TRADING", "underlyingType": x.turi,
                 "onboardDate": ms(self.soat - timedelta(days=x.onboard_kun))}
                for x in c.values()
            ] + [{"symbol": "BTCUSDT_261225", "baseAsset": "BTC", "quoteAsset": "USDT",
                  "contractType": "CURRENT_QUARTER", "status": "TRADING"}]}, 200
        if yol == "/fapi/v1/ticker/24hr":
            return [{"symbol": x.symbol, "lastPrice": str(x.narx),
                     "priceChangePercent": str(x.ozgarish), "quoteVolume": str(x.hajm)}
                    for x in c.values()], 200
        if yol == "/fapi/v1/premiumIndex":
            return [{"symbol": x.symbol, "lastFundingRate": str(x.funding)}
                    for x in c.values() if x.funding is not None], 200
        if yol == "/fapi/v1/fundingInfo":
            return [{"symbol": x.symbol, "fundingIntervalHours": x.funding_soat}
                    for x in c.values() if x.funding_soat], 200
        if yol == "/futures/data/openInterestHist":
            x = c[p["symbol"]]
            return [{"symbol": x.symbol, "sumOpenInterest": str(v), "timestamp": 1000 + i}
                    for i, v in enumerate(x.oi)], 200
        if yol == "/futures/data/globalLongShortAccountRatio":
            x = c[p["symbol"]]
            return ([{"longShortRatio": str(x.ls), "timestamp": 1}] if x.ls else []), 200
        if yol == "/fapi/v1/klines":
            x = c[p["symbol"]]
            boshi = self.soat - timedelta(days=31)
            yop = timedelta(days=1)
            return [[ms(boshi + yop * i), "1", "1", "1", "1", "0",
                     ms(boshi + yop * (i + 1)) - 1, str(x.ortacha or 0)]
                    for i in range(31)], 200
        raise AssertionError(f"kutilmagan so'rov: {yol}")


class SoxtaCoinGecko(CoinGeckoTaminot):
    def __init__(self, coinlar: dict[str, Coin]) -> None:
        super().__init__("https://cg.test")
        self.coinlar = coinlar
        self.sorovlar: list[dict] = []

    async def _json(self, manzil, parametr=None):  # noqa: ANN001, ANN202
        self.sorovlar.append(parametr or {})
        kerak = set((parametr or {}).get("symbols", "").split(","))
        javob = []
        for x in self.coinlar.values():
            from core.portlash_radari.belgi import ajrat

            belgi = ajrat(x.asosiy)[0]
            if belgi.lower() not in kerak:
                continue
            javob.append({
                "symbol": belgi.lower(),
                "market_cap": x.cg_cap,
                "current_price": x.cg_narx if x.cg_narx is not None else x.narx,
                "circulating_supply": x.cg_aylanma,
                "total_supply": 100.0 if x.cg_aylanma is not None else None,
                "max_supply": None,
            })
        return javob, 200


@dataclass
class Hodisa:
    kun_qoldi: int
    pct: float | None


class SoxtaUnlock:
    def __init__(self) -> None:
        self.jadval_qiymati = {"NEW": Hodisa(3, 12.0)}

    async def jadval(self) -> dict:
        return self.jadval_qiymati


@pytest.fixture
async def db(tmp_path):  # noqa: ANN001, ANN201
    baza = Database(f"sqlite+aiosqlite:///{tmp_path / 'radar.db'}")
    await baza.init_models()
    yield baza
    await baza.dispose()


async def _kesh(db: Database, coinlar: dict[str, Coin]) -> None:
    async with db.session() as s:
        await RadarRepository(s).ortachalarni_yoz(
            {x.symbol: (x.ortacha, 30) for x in coinlar.values() if x.ortacha is not None},
            HOZIR,
        )


def _sessiya(config: AppConfig, db: Database, coinlar: dict[str, Coin], soat: datetime):  # noqa: ANN202
    b = SoxtaBinance(coinlar, soat)
    cg = SoxtaCoinGecko(coinlar)
    return RadarSessiyasi(config, db, b, cg, SoxtaUnlock(), lambda: soat), b, cg


async def _qatorlar(db: Database, sessiya_id: int) -> dict[str, RadarNatija]:
    async with db.session() as s:
        return {n.symbol: n for n in await RadarRepository(s).natijalar(sessiya_id)}


async def test_a_va_b_sessiyalari_zanjiri(config: AppConfig, db: Database) -> None:
    coinlar = bozor()
    await _kesh(db, coinlar)
    async with db.session() as s:
        s.add(RadarYashirin(symbol="ABCUSDT", sabab="shovqin"))
        s.add(CoinRuling(symbol="LSK", status="halal", reason="test"))

    # --- A (kashfiyot) ---
    sessiya, b, cg = _sessiya(config, db, coinlar, SHAM - timedelta(hours=1))
    a = await sessiya.yur(KASHFIYOT, SHAM)
    assert a.holat == "tugadi"
    qa = await _qatorlar(db, a.sessiya_id)

    # universum: stablecoin, oltin va kvartal kontrakt yo'q
    assert "USDCUSDT" not in qa and "XAUUSDT" not in qa
    # pool: LSK, ABC (yashirin), NEW (yangi listing), PEPE. TINY — kap darvozasi.
    pool = {s for s, n in qa.items() if n.turi == "elak"}
    assert pool == {"LSKUSDT", "ABCUSDT", "NEWUSDT", "1000PEPEUSDT"}
    assert "LOWUSDT" not in qa and "TINYUSDT" not in qa

    lsk = qa["LSKUSDT"]
    assert (lsk.tasdiq_soni, lsk.harakat_soni, lsk.yoqilgi_soni) == (5, 3, 2)
    assert lsk.nomzod and lsk.holat == "nomzod" and lsk.halol == "halol"
    assert lsk.ketma_ket == 1
    assert lsk.orin == 1
    assert qa["ABCUSDT"].yashirin and qa["ABCUSDT"].orin is None
    assert qa["ABCUSDT"].nomzod
    assert qa["NEWUSDT"].yangi_listing
    assert qa["1000PEPEUSDT"].belgi == "PEPE"
    assert qa["1000PEPEUSDT"].market_cap == 4e9  # narx mos keldi (ko'paytirgich)

    tekshiruv = {t["kod"]: t for t in json.loads(lsk.tekshiruvlar_json)}
    assert tekshiruv["funding"]["holat"] == "ha"
    assert tekshiruv["taminot"]["qoshimcha"]["aylanma_pct"] == 70.6
    # NEW: aylanma noma'lum, lekin 3 kunda 12% unlock -> ✅
    new_t = {t["kod"]: t for t in json.loads(qa["NEWUSDT"].tekshiruvlar_json)}
    assert new_t["taminot"]["holat"] == "ha"
    assert new_t["hajm"]["holat"] == "malumot_yoq"

    # nazorat guruhi: elakdan o'tmagan Q coinlardan 10 ta, o'rinsiz
    namuna = [n for n in qa.values() if n.turi == "namuna"]
    assert len(namuna) == 10 and all(n.orin is None for n in namuna)
    assert all(n.symbol.startswith("Q") or n.symbol == "BTCUSDT" for n in namuna)

    # coin boshiga so'rov faqat pool + namuna uchun
    oi_sorovlari = b.sorovlar.count("/futures/data/openInterestHist")
    assert oi_sorovlari == len(pool) + len(namuna)
    # CoinGecko — bitta so'rov
    assert len(cg.sorovlar) == 1

    async with db.session() as s:
        sess = await s.get(RadarSessiya, a.sessiya_id)
    assert (sess.kun, sess.tartib) == ("2026-10-14", 3)
    assert sess.elakdan == 4 and sess.nomzod == 2
    manbalar = json.loads(sess.manbalar_json)
    assert manbalar["ticker"]["holat"] == "ok"
    assert manbalar["oi"]["izoh"].startswith(f"{oi_sorovlari}/{oi_sorovlari}")
    assert json.loads(sess.sozlama_json)["nomzod_min"] == 4

    # --- B (tasdiq): ABC endi nomzod emas, LSK hamon nomzod ---
    coinlar["ABCUSDT"].ls = 1.0
    coinlar["ABCUSDT"].oi = (100.0, 101.0)
    async with db.session() as s:
        await s.execute(RadarYashirin.__table__.delete())
    sessiya, _, _ = _sessiya(config, db, coinlar, SHAM - timedelta(minutes=15))
    bx = await sessiya.yur(TASDIQ, SHAM)
    qb = await _qatorlar(db, bx.sessiya_id)
    assert qb["LSKUSDT"].holat == "tasdiqlangan"
    assert qb["LSKUSDT"].ketma_ket == 2  # A dan davom etyapti
    assert qb["ABCUSDT"].holat == "vaqtinchalik"
    assert qb["ABCUSDT"].ketma_ket == 0
    assert qb["ABCUSDT"].orin is not None  # endi yashirin emas
    assert qb["LSKUSDT"].orin == 1

    # --- Keyingi B: LSK elakdan ham tushdi -> "chiqdi", faqat narx ---
    coinlar["LSKUSDT"].hajm = 10e6
    coinlar["LSKUSDT"].narx = 1.5
    keyingi = SHAM + timedelta(hours=4)
    sessiya, _, _ = _sessiya(config, db, coinlar, keyingi - timedelta(minutes=15))
    cx = await sessiya.yur(TASDIQ, keyingi)
    qc = await _qatorlar(db, cx.sessiya_id)
    assert qc["LSKUSDT"].turi == "chiqdi"
    assert qc["LSKUSDT"].narx == 1.5
    assert qc["LSKUSDT"].orin is None
    # A sessiyasi yo'q -> tasdiqni bilib bo'lmaydi
    assert all(n.holat in ("nomzod", "oddiy") for n in qc.values() if n.turi == "elak")


async def test_451_sessiyani_xato_bilan_yopadi_va_sababini_yozadi(
    config: AppConfig, db: Database
) -> None:
    sessiya, b, _ = _sessiya(config, db, bozor(), HOZIR)
    b.kodlar["/fapi/v1/exchangeInfo"] = 451
    natija = await sessiya.yur(TASDIQ, SHAM)
    assert natija.holat == "xato"
    async with db.session() as s:
        sess = await s.get(RadarSessiya, natija.sessiya_id)
    assert sess.holat == "xato" and "451" in sess.izoh
    assert json.loads(sess.manbalar_json)["juftliklar"] == {
        "holat": "xato", "kod": 451, "izoh": ""
    }


async def test_funding_yiqilsa_qolgan_tekshiruvlar_ishlaydi(
    config: AppConfig, db: Database
) -> None:
    coinlar = bozor()
    await _kesh(db, coinlar)
    sessiya, b, _ = _sessiya(config, db, coinlar, HOZIR)
    b.kodlar["/fapi/v1/premiumIndex"] = 500
    natija = await sessiya.yur(TASDIQ, SHAM)
    assert natija.holat == "tugadi"
    q = await _qatorlar(db, natija.sessiya_id)
    t = {x["kod"]: x for x in json.loads(q["LSKUSDT"].tekshiruvlar_json)}
    assert t["funding"]["holat"] == "malumot_yoq"
    assert t["narx"]["holat"] == "ha"


async def test_kesh_bosh_bolsa_hamma_coin_yangi_listing_bolib_qolmaydi(
    config: AppConfig, db: Database
) -> None:
    """Kesh qurilmagan bo'lsa faqat Binance sanasi bo'yicha yangi coin o'tadi."""
    sessiya, b, _ = _sessiya(config, db, bozor(), HOZIR)
    natija = await sessiya.yur(TASDIQ, SHAM)
    q = await _qatorlar(db, natija.sessiya_id)
    assert {s for s, n in q.items() if n.turi == "elak"} == {"NEWUSDT"}


async def test_admin_sozlamasi_keyingi_sessiyada_ishlaydi(
    config: AppConfig, db: Database
) -> None:
    from core.storage.models import RadarSozlama

    coinlar = bozor()
    await _kesh(db, coinlar)
    async with db.session() as s:
        s.add(RadarSozlama(kalit="nomzod_min", qiymat=6))
        s.add(RadarSozlama(kalit="top_n", qiymat=99999))  # oraliqdan tashqari -> tashlanadi
    sessiya, _, _ = _sessiya(config, db, coinlar, HOZIR)
    natija = await sessiya.yur(TASDIQ, SHAM)
    q = await _qatorlar(db, natija.sessiya_id)
    assert not q["LSKUSDT"].nomzod  # 5/7 < 6
    async with db.session() as s:
        sess = await s.get(RadarSessiya, natija.sessiya_id)
    assert json.loads(sess.sozlama_json)["nomzod_min"] == 6
    assert json.loads(sess.sozlama_json)["top_n"] == 10
    assert "top_n" in sess.izoh


async def test_qolda_tekshiruv_rasmiy_zanjirga_kirmaydi(
    config: AppConfig, db: Database
) -> None:
    coinlar = bozor()
    await _kesh(db, coinlar)
    sessiya, _, _ = _sessiya(config, db, coinlar, HOZIR)
    natija = await sessiya.yur(QOLDA, SHAM)
    q = await _qatorlar(db, natija.sessiya_id)
    assert q["LSKUSDT"].nomzod and q["LSKUSDT"].ketma_ket == 0
    assert all(n.turi != "chiqdi" for n in q.values())
    async with db.session() as s:
        turlar = (await s.execute(select(RadarSessiya.turi))).scalars().all()
    assert turlar == [QOLDA]


async def test_cg_narxi_mos_kelmasa_boshqa_loyiha_deb_tashlanadi(
    config: AppConfig, db: Database
) -> None:
    coinlar = bozor()
    coinlar["LSKUSDT"].cg_narx = 50.0  # bir xil belgili boshqa coin
    await _kesh(db, coinlar)
    sessiya, _, _ = _sessiya(config, db, coinlar, HOZIR)
    natija = await sessiya.yur(TASDIQ, SHAM)
    q = await _qatorlar(db, natija.sessiya_id)
    assert q["LSKUSDT"].market_cap is None
    t = {x["kod"]: x for x in json.loads(q["LSKUSDT"].tekshiruvlar_json)}
    assert t["taminot"]["holat"] == "malumot_yoq"
