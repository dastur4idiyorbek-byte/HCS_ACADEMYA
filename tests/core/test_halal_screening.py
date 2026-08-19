"""3.4-band: "Top 30 HALOL" mantig'i.

Asosiy talab: ro'yxat 1-o'rindan pastga qarab tekshiriladi, harom/shubhali
o'tkazib yuboriladi, va natija ANIQ `target_count` ta halol coin bo'ladi —
kerak bo'lsa 31, 32, 33... o'ringacha tushib.
"""

from __future__ import annotations

from core.config.schema import HalalScreeningConfig
from core.domain.enums import HalalStatus
from core.domain.models import MarketRankEntry
from core.halal_screening import HalalScreener, StaticRulingRegistry


def reyting(n: int, hajm: float = 100_000_000) -> list[MarketRankEntry]:
    """N ta soxta coin: C1 (eng yuqori kapitalizatsiya) ... CN."""
    return [
        MarketRankEntry(
            rank=i,
            symbol=f"C{i}",
            name=f"Coin {i}",
            market_cap_usd=1_000_000_000 / i,
            volume_24h_usd=hajm,
        )
        for i in range(1, n + 1)
    ]


def konfig(**kwargs) -> HalalScreeningConfig:
    asosiy = {"target_count": 5, "max_scan_depth": 100, "min_daily_volume_usd": 50_000_000}
    return HalalScreeningConfig(**{**asosiy, **kwargs})


def test_hech_narsa_chetlatilmasa_birinchi_n_ta_olinadi() -> None:
    screener = HalalScreener(konfig(), StaticRulingRegistry())
    natija = screener.screen(reyting(20))

    assert natija.symbols == ["C1", "C2", "C3", "C4", "C5"]
    assert natija.complete
    assert natija.scanned_depth == 5


def test_harom_coinlar_otkazib_yuboriladi_va_royxat_toladi() -> None:
    """C2 va C4 harom -> ular o'rniga C6 va C7 olinadi, ro'yxat baribir 5 ta."""
    registry = StaticRulingRegistry(haram={"C2": "riba", "C4": "qimor"})
    screener = HalalScreener(konfig(), registry)
    natija = screener.screen(reyting(20))

    assert natija.symbols == ["C1", "C3", "C5", "C6", "C7"]
    assert natija.count == 5
    assert natija.complete
    assert natija.scanned_depth == 7, "ro'yxat to'lguncha pastga tushishi kerak"


def test_shubhali_ham_harom_kabi_chetlatiladi() -> None:
    """Shubhali (mashbooh) narsadan yiroqlashish — brend tamoyili."""
    registry = StaticRulingRegistry(mashbooh={"C1": "meme, noaniq tabiat"})
    screener = HalalScreener(konfig(), registry)
    natija = screener.screen(reyting(20))

    assert "C1" not in natija.symbols
    chetlatilgan = {v.symbol: v.status for v in natija.skipped}
    assert chetlatilgan["C1"] is HalalStatus.MASHBOOH


def test_likvidligi_past_coin_chetlatiladi() -> None:
    past = reyting(10)
    past[1] = MarketRankEntry(2, "C2", "Coin 2", 500_000_000, volume_24h_usd=1_000_000)
    screener = HalalScreener(konfig(), StaticRulingRegistry())
    natija = screener.screen(past)

    assert "C2" not in natija.symbols
    sabab = next(v.reason for v in natija.skipped if v.symbol == "C2")
    assert "likvidlik" in sabab.lower()


def test_stablecoinlar_avtomatik_chiqariladi() -> None:
    ro_yxat = [
        MarketRankEntry(1, "BTC", "Bitcoin", 1e12, 1e10),
        MarketRankEntry(2, "USDT", "Tether", 1e11, 1e11),
        MarketRankEntry(3, "ETH", "Ethereum", 4e11, 1e10),
        MarketRankEntry(4, "USDC", "USD Coin", 3e10, 1e10),
        MarketRankEntry(5, "SOL", "Solana", 8e10, 1e9),
    ]
    registry = StaticRulingRegistry(stablecoins={"USDT", "USDC", "DAI"})
    screener = HalalScreener(konfig(target_count=3), registry)
    natija = screener.screen(ro_yxat)

    assert natija.symbols == ["BTC", "ETH", "SOL"]


def test_yetarli_halol_topilmasa_toliqsiz_deb_belgilanadi() -> None:
    """0.3-band fail-safe: to'liqsiz ro'yxat jim o'tmasligi kerak."""
    registry = StaticRulingRegistry(haram={f"C{i}": "harom" for i in range(1, 9)})
    screener = HalalScreener(konfig(target_count=5), registry)
    natija = screener.screen(reyting(8))

    assert not natija.complete
    assert natija.count == 0


def test_skan_chuqurligi_chegarasi_hurmat_qilinadi() -> None:
    registry = StaticRulingRegistry(haram={f"C{i}": "harom" for i in range(1, 100)})
    screener = HalalScreener(konfig(target_count=5, max_scan_depth=10), registry)
    natija = screener.screen(reyting(50))

    assert natija.scanned_depth == 10
    assert not natija.complete


def test_haqiqiy_konfiguratsiya_bilan_30_ta_yigiladi(config) -> None:
    """Loyihaning haqiqiy `seed_haram_symbols` ro'yxati bilan ishlaydimi."""
    registry = StaticRulingRegistry.from_config(config.halal_screening)
    screener = HalalScreener(config.halal_screening, registry)
    natija = screener.screen(reyting(200, hajm=100_000_000))

    assert natija.count == 30
    assert natija.complete


def test_juftlik_nomi_toplanadi(config) -> None:
    screener = HalalScreener(config.halal_screening, StaticRulingRegistry())
    assert screener.pair_for("btc") == "BTCUSDT"


def test_admin_qorini_ustidan_yozadi() -> None:
    """1.4-band: admin istalgan vaqtda coinni harom deb belgilay oladi."""
    registry = StaticRulingRegistry()
    assert registry.verdict_for("C1").status is HalalStatus.HALAL

    registry.set_ruling("C1", HalalStatus.HARAM, "admin qarori")
    assert registry.verdict_for("C1").status is HalalStatus.HARAM

    registry.set_ruling("C1", HalalStatus.HALAL, "qayta ko'rib chiqildi")
    assert registry.verdict_for("C1").status is HalalStatus.HALAL
