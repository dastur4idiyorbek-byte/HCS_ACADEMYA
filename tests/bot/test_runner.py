"""15-bosqich: jonli ma'lumotni siklga ulash — uchdan-uchgacha.

Soxta provayderlar bilan sinaladi: haqiqiy tarmoq va Telegram kerak emas,
chunki barcha tashqi bog'liqliklar abstraksiya orqali ulangan.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from bot.services.runner import PipelineRunner, cycle_interval
from core.config import load_config
from core.domain.enums import HalalStatus, SubscriptionTier
from core.domain.models import Candle, MarketRankEntry, signal_levels
from core.market_data import CandleProvider, PriceCache, RankingProvider
from core.storage import Database
from core.storage.repositories import (
    CoinRulingRepository,
    MarketHealthRepository,
    RiskBlockRepository,
    SignalRepository,
    SubscriptionRepository,
    UserRepository,
)

BOSH = datetime(2026, 8, 19, tzinfo=UTC)


class SoxtaCandles(CandleProvider):
    """Barcha coinlar uchun bir xil ko'tarilish shakli."""

    def __init__(self, candles: list[Candle] | None = None, fail_on: set[str] | None = None):
        self._candles = candles if candles is not None else self._default()
        self._fail_on = fail_on or set()
        self.calls: list[tuple[str, str]] = []

    @staticmethod
    def _default() -> list[Candle]:
        return [
            Candle(BOSH + timedelta(hours=i), 100 + i, 100 + i + 0.5, 100 + i - 0.5, 100 + i, 1000)
            for i in range(260)
        ]

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        self.calls.append((symbol, timeframe))
        if symbol in self._fail_on:
            raise RuntimeError("sinov uchun ataylab buzilgan")
        return self._candles

    async def close(self) -> None:
        pass


class SoxtaRanking(RankingProvider):
    def __init__(self, symbols: list[str] | None = None, fail: bool = False):
        # `symbols or [...]` yozilsa, BO'SH ro'yxat ham standartga tushib
        # ketardi — aynan shu holatni sinamoqchi edik.
        self._symbols = symbols if symbols is not None else ["BTC", "ETH", "SOL"]
        self._fail = fail

    async def fetch_ranking(self, limit: int) -> list[MarketRankEntry]:
        if self._fail:
            raise RuntimeError("reyting olinmadi")
        return [
            MarketRankEntry(i + 1, s, s, 1e10 / (i + 1), 1e9)
            for i, s in enumerate(self._symbols)
        ]


class SoxtaWatcher:
    def __init__(self) -> None:
        self.prices = PriceCache()
        self.kill_switch_active = False
        self.kill_switch_reason = None
        self.added: list[int] = []

    def add_signal(self, signal_id: int) -> None:
        self.added.append(signal_id)


class SoxtaBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str, **_: object) -> None:
        self.messages.append((chat_id, text))


@pytest.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.init_models()
    yield database
    await database.dispose()


@pytest.fixture
def config():  # noqa: ANN201
    return load_config()


def runner(db, config, candles=None, ranking=None, bot=None, watcher=None):  # noqa: ANN001, ANN201
    return PipelineRunner(
        bot or SoxtaBot(),
        db,
        config,
        candles or SoxtaCandles(),
        ranking or SoxtaRanking(),
        watcher or SoxtaWatcher(),
    )


# --------------------------------------------------------------------------- #
#  3.4 — Halol ro'yxat
# --------------------------------------------------------------------------- #


async def test_halol_royxat_yigiladi(db: Database, config) -> None:  # noqa: ANN001
    natija = await runner(db, config).refresh_universe()

    assert natija.symbols == ["BTC", "ETH", "SOL"]
    assert not natija.is_empty


async def test_admin_qarorlari_hisobga_olinadi(db: Database, config) -> None:  # noqa: ANN001
    """1.4-band: admin coinni harom deb belgilasa, u ro'yxatga kirmaydi."""
    async with db.session() as session:
        await CoinRulingRepository(session).set_ruling(
            "ETH", HalalStatus.HARAM, "sinov uchun"
        )

    natija = await runner(db, config).refresh_universe()
    assert "ETH" not in natija.symbols


async def test_reyting_olinmasa_eski_royxat_saqlanadi(db: Database, config) -> None:  # noqa: ANN001
    """0.3-band: bo'sh ro'yxat "halol coin yo'q" degan xato xulosaga olib kelardi."""
    ish = runner(db, config)
    await ish.refresh_universe()

    ish._ranking = SoxtaRanking(fail=True)
    natija = await ish.refresh_universe()

    assert natija.symbols == ["BTC", "ETH", "SOL"], "eski ro'yxat kuchda qolishi kerak"


# --------------------------------------------------------------------------- #
#  Ma'lumot yuklash
# --------------------------------------------------------------------------- #


async def test_barcha_timeframelar_yuklanadi(db: Database, config) -> None:  # noqa: ANN001
    """YOQILGAN strategiyalar so'ragan har bir qator yuklansin.

    RO'YXAT EMAS, TALAB tekshiriladi. Ilgari bu yerda `"15m"` deb
    qattiq yozilgan edi va u strategiya o'chirilishi bilan
    yiqildi. Undan ham yomoni teskarisi bo'lardi: strategiya
    yangi qator so'rasa, test buni sezmasdi va qator jimgina
    yuklanmay qolardi — bu loyihada BESH marta uchragan xato turi
    (`docs/ARXITEKTURA.md`, 80-bo'lim).

    Bozor Salomatligi timeframei ham shu ro'yxatda: u hech bir
    strategiyaning ro'yxatida yo'q, lekin usiz indeks o'lik
    bo'lib qoladi.
    """
    from core.analysis.strategies import build_strategies, required_timeframes

    shamlar = SoxtaCandles()
    ish = runner(db, config, candles=shamlar)
    await ish.refresh_universe()
    await ish.run_once()

    so_ralganlar = {tf for _, tf in shamlar.calls}
    kerakli = set(required_timeframes(build_strategies(config)))
    kerakli.add(config.analysis.market_health_timeframe)

    yetishmayapti = kerakli - so_ralganlar
    assert not yetishmayapti, (
        f"bu qatorlar so'ralmadi: {sorted(yetishmayapti)} "
        f"(so'ralganlari: {sorted(so_ralganlar)})"
    )


async def test_bitta_coin_xatosi_siklni_toxtatmaydi(db: Database, config) -> None:  # noqa: ANN001
    ish = runner(db, config, candles=SoxtaCandles(fail_on={"ETH"}))
    await ish.refresh_universe()

    natija = await ish.run_once()
    assert natija is not None, "sikl ishlashi kerak"


# --------------------------------------------------------------------------- #
#  Sikl va Bozor Salomatligi
# --------------------------------------------------------------------------- #


async def test_salomatlik_hisoblanib_bazaga_yoziladi(db: Database, config) -> None:  # noqa: ANN001
    ish = runner(db, config)
    await ish.refresh_universe()
    await ish.run_once()

    async with db.session() as session:
        yozuv = await MarketHealthRepository(session).latest()

    assert yozuv is not None
    assert 0 <= yozuv.value <= 100


async def test_rad_etish_sabablari_bazaga_yoziladi(db: Database, config) -> None:  # noqa: ANN001
    """3.7-band: signal chiqmasa, SABABI admin uchun saqlanishi kerak.

    Jurnal yetarli emas — u aylanadi va Telegram'dan ochib bo'lmaydi.
    """
    ish = runner(db, config)
    await ish.refresh_universe()
    natija = await ish.run_once()

    assert natija is not None
    assert natija.rejected, "bu sinov ma'lumotida rad etish kutilgan edi"

    async with db.session() as session:
        xulosa = await RiskBlockRepository(session).summary_since(
            datetime.now(UTC) - timedelta(hours=1)
        )

    assert xulosa, "rad etish sabablari yozilmagan"
    assert sum(soni for _, soni, _ in xulosa) == len(natija.rejected)


async def test_sabab_yozilmasa_sikl_toxtamaydi(db: Database, config, monkeypatch) -> None:  # noqa: ANN001
    """0.3-band: kuzatuv yozuvi asosiy ishni to'xtatmasligi kerak."""

    async def yiqiladi(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("baza band")

    monkeypatch.setattr(RiskBlockRepository, "record_many", yiqiladi)

    ish = runner(db, config)
    await ish.refresh_universe()

    assert await ish.run_once() is not None


async def test_bosh_royxatda_sikl_otkazib_yuboriladi(db: Database, config) -> None:  # noqa: ANN001
    ish = runner(db, config, ranking=SoxtaRanking(symbols=[], fail=False))
    assert await ish.run_once() is None


async def test_sikl_natija_qaytaradi(db: Database, config) -> None:  # noqa: ANN001
    ish = runner(db, config)
    await ish.refresh_universe()
    natija = await ish.run_once()

    assert natija is not None
    assert natija.analyzed_count >= 0
    assert "coin tahlil qilindi" in natija.summary()


# --------------------------------------------------------------------------- #
#  Signal chiqarish
# --------------------------------------------------------------------------- #


async def test_chiqarilgan_signal_bazaga_yoziladi_va_kuzatuvga_qoshiladi(
    db: Database, config
) -> None:  # noqa: ANN001
    """Signal chiqsa, u bazaga yozilishi VA kuzatuvga qo'shilishi kerak."""

    kuzatuvchi = SoxtaWatcher()
    bot = SoxtaBot()
    ish = runner(db, config, bot=bot, watcher=kuzatuvchi)
    await ish.refresh_universe()

    # Obunachi qo'shamiz
    async with db.session() as session:
        user = await UserRepository(session).get_or_create(555)
        await SubscriptionRepository(session).create(
            user.id, SubscriptionTier.PREMIUM, period_days=30, is_trial=False
        )

    # Nomzodni qo'lda chiqaramiz (strategiya sun'iy ma'lumotda signal bermasligi mumkin)
    from core.domain.enums import SignalSource
    from core.domain.models import (
        HalalVerdict,
        MarketHealth,
        ScoreBreakdown,
        ScoreComponent,
        SignalCandidate,
    )

    nomzod = SignalCandidate(
        symbol="BTC",
        levels=signal_levels(entry=100, stop=99.2, tp1=103.5, tp2=104.5),
        source=SignalSource.CLASSIC_TA,
        breakdown=ScoreBreakdown("BTC", [ScoreComponent("jami", 88, 100, "sinov")]),
        halal_verdict=HalalVerdict("BTC", HalalStatus.HALAL, "halol"),
    )
    await ish._emit(nomzod, MarketHealth(85.0, [], BOSH))

    async with db.session() as session:
        yozuvlar = await SignalRepository(session).open_signals()

    assert len(yozuvlar) == 1
    assert yozuvlar[0].symbol == "BTC"
    assert yozuvlar[0].score == 88
    assert yozuvlar[0].score_breakdown, "ball tafsiloti saqlanishi kerak (3.6-band)"
    assert yozuvlar[0].market_health_at_entry == 85.0, "kontekst saqlanishi kerak (3.8-band)"
    assert kuzatuvchi.added == [yozuvlar[0].id], "kuzatuvga qo'shilishi kerak"
    assert any(chat == 555 for chat, _ in bot.messages), "obunachiga yetkazilishi kerak"


async def test_obunasiz_foydalanuvchiga_signal_bormaydi(db: Database, config) -> None:  # noqa: ANN001
    from core.domain.enums import SignalSource
    from core.domain.models import (
        HalalVerdict,
        MarketHealth,
        ScoreBreakdown,
        ScoreComponent,
        SignalCandidate,
    )

    bot = SoxtaBot()
    ish = runner(db, config, bot=bot)
    async with db.session() as session:
        await UserRepository(session).get_or_create(999)  # obunasiz

    nomzod = SignalCandidate(
        symbol="BTC",
        levels=signal_levels(entry=100, stop=99.2, tp1=103.5, tp2=104.5),
        source=SignalSource.CLASSIC_TA,
        breakdown=ScoreBreakdown("BTC", [ScoreComponent("jami", 88, 100, "sinov")]),
        halal_verdict=HalalVerdict("BTC", HalalStatus.HALAL, "halol"),
    )
    await ish._emit(nomzod, MarketHealth(85.0, [], BOSH))

    assert bot.messages == []


# --------------------------------------------------------------------------- #
#  Sikl oralig'i
# --------------------------------------------------------------------------- #


def test_sikl_oraligi_timeframega_mos(config) -> None:  # noqa: ANN001
    """Sham yopilmaguncha tahlil natijasi o'zgarmaydi — tez-tez ishlash foydasiz.

    Kutilgan qiymat konfiguratsiyadan olinadi: kirish timeframei
    o'zgarganda bu test jimgina eskirmasligi kerak.
    """
    kutilgan = {"15m": 15, "30m": 30, "1h": 60, "4h": 240}[config.analysis.entry_timeframe]
    assert cycle_interval(config) == timedelta(minutes=kutilgan)


def test_notanish_timeframe_uchun_standart_oraliq(config) -> None:  # noqa: ANN001
    import dataclasses

    yangi = dataclasses.replace(
        config,
        analysis=dataclasses.replace(config.analysis, entry_timeframe="7m"),
    )
    assert cycle_interval(yangi) == timedelta(minutes=15)


# --------------------------------------------------------------------------- #
#  Kengaytirilgan ro'yxat: parallellik chegarasi
# --------------------------------------------------------------------------- #


class SanovchiCandles(SoxtaCandles):
    """Bir vaqtda nechta so'rov ochiq turganini o'lchaydi."""

    def __init__(self) -> None:
        super().__init__()
        self.hozir = 0
        self.eng_kop = 0

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        self.hozir += 1
        self.eng_kop = max(self.eng_kop, self.hozir)
        try:
            # Boshqa vazifalarga navbat berish uchun — ansiz hech qanday
            # parallellik yuzaga kelmaydi va test hech narsani o'lchamaydi.
            await asyncio.sleep(0)
            return await super().fetch_candles(symbol, timeframe, limit)
        finally:
            self.hozir -= 1


async def test_sorovlar_soni_chegaralanadi(db: Database, config) -> None:  # noqa: ANN001
    """150 ta coinda chegarasiz parallellik birjadan IP ban keltiradi.

    Ilgari sikl barcha coin × barcha timeframe so'rovini bir zumda
    yuborardi: 30 ta coinda 90 ta so'rov (birja chidardi), 150 tada esa
    450 ta — Binance avval 429, keyin 418 qaytaradi. Ya'ni ro'yxat
    kengaygani sari tizim ko'proq emas, KAMROQ ma'lumot olardi.
    """
    coinlar = [f"C{i}" for i in range(60)]
    candles = SanovchiCandles()
    ish = runner(db, config, candles=candles, ranking=SoxtaRanking(coinlar))
    await ish.refresh_universe()

    shamlar = await ish._load_candles(coinlar)

    chegara = config.market_data.max_concurrent_candle_requests
    assert candles.eng_kop <= chegara, (
        f"bir vaqtda {candles.eng_kop} ta so'rov ochilgan, chegara {chegara}"
    )
    assert candles.eng_kop > 1, "chegara ishlayapti, lekin parallellik umuman yo'qolmasin"
    assert len(shamlar) == len(coinlar), "chegara birorta coinni tushirib qoldirmasligi kerak"


async def test_bitta_coin_yiqilsa_qolganlari_yuklanadi(db: Database, config) -> None:  # noqa: ANN001
    """0.3-band: chegara qo'yilgach ham bitta xato siklni to'xtatmasin."""
    coinlar = [f"C{i}" for i in range(20)]
    candles = SoxtaCandles(fail_on={"C5"})
    ish = runner(db, config, candles=candles, ranking=SoxtaRanking(coinlar))
    await ish.refresh_universe()

    shamlar = await ish._load_candles(coinlar)

    assert shamlar["C5"] == {}, "yiqilgan coin bo'sh qoladi"
    assert shamlar["C6"], "qolganlari yuklanishi kerak"


# --------------------------------------------------------------------------- #
#  Deadlock: 0 ta ochiq signal -> narx yo'q -> signal yo'q
# --------------------------------------------------------------------------- #


async def test_ochiq_signalsiz_ham_narx_yoshi_bor(db: Database, config) -> None:  # noqa: ANN001
    """Tizim BIRINCHI signalini chiqara olishi kerak.

    Narx yoshi faqat tik keshidan olinardi, tik keshini esa kuzatuvchi
    to'ldiradi va u FAQAT ochiq signallar coinlariga obuna bo'ladi:

        0 ochiq signal -> obuna bo'sh -> kesh bo'sh -> yosh None
        -> FreshDataRule bloklaydi -> yangi signal yo'q -> 0 ochiq signal

    Jonli o'lchovda bu 72 soat davomida "Risk Engine to'xtatdi" bo'lib
    ko'rinardi. Endi shamdan hisoblanadi — signal qarori baribir
    shamdan olingan narxga tayanadi.
    """
    ish = runner(db, config, ranking=SoxtaRanking(["BTC"]))
    await ish.refresh_universe()

    assert ish._watcher.prices.price_of("BTC") is None, "tik keshi bo'sh (obuna yo'q)"

    shamlar = await ish._load_candles(["BTC"])
    seriya = shamlar["BTC"][config.analysis.entry_timeframe]

    yosh = ish._narx_yoshi("BTC", seriya)
    assert yosh is not None, "sham bor ekan, yosh hisoblanishi kerak"


async def test_tik_mavjud_bolsa_undan_olinadi(db: Database, config) -> None:  # noqa: ANN001
    """Tik aniqroq — bor bo'lsa u afzal."""
    from core.domain.models import PriceTick

    ish = runner(db, config)
    ish._watcher.prices.update(PriceTick("BTC", 100.0, datetime.now(UTC)))

    yosh = ish._narx_yoshi("BTC", [])
    assert yosh is not None
    assert yosh < 5, "yangi tik — yosh kichik bo'lishi kerak"


async def test_sham_ham_tik_ham_bolmasa_none(db: Database, config) -> None:  # noqa: ANN001
    """0.3-band: hech narsa yo'q bo'lsa — noaniqlik, signal berilmaydi."""
    assert runner(db, config)._narx_yoshi("BTC", []) is None


# --------------------------------------------------------------------------- #
#  4.5 — BTC filtri: e'lon qilingan, lekin ulanmagan edi
# --------------------------------------------------------------------------- #


async def test_btc_ozgarishi_siklga_uzatiladi(db: Database, config) -> None:  # noqa: ANN001
    """`BtcMarketRule` bor edi, lekin uni to'ldiradigan kod YO'Q edi.

    `CycleInput.btc_change_24h_pct` doim `None` bo'lib qolardi va qoida
    fail-safe tarmog'iga tushardi ("BTC holati noma'lum"). Ya'ni ball
    chegarasidan o'tgan HAR BIR nomzod shu yerda to'xtardi — jonli
    o'lchovda 119 tadan 119 tasi.
    """
    ish = runner(db, config, ranking=SoxtaRanking(["BTC", "ETH"]))
    await ish.refresh_universe()

    shamlar = await ish._load_candles(["BTC", "ETH"])
    kirish = ish._build_input(shamlar, salomatlik(75.0), [], 0)

    assert kirish.btc_change_24h_pct is not None, (
        "BTC o'zgarishi hisoblanmasa, 4.5-band filtri hamma signalni bloklaydi"
    )


async def test_btc_shamlari_royxatda_bolmasa_ham_yuklanadi(db: Database, config) -> None:  # noqa: ANN001
    """BTC halol ro'yxatda bo'lmasligi mumkin, lekin filtr unga tayanadi."""
    ish = runner(db, config, ranking=SoxtaRanking(["ETH", "SOL"]))
    await ish.refresh_universe()
    assert "BTC" not in ish._universe.symbols

    natija = await ish.run_once()

    assert natija is not None
    # Filtr "noma'lum" tarmog'iga tushmasligi kerak
    noaniq = [r for r in natija.rejected if "BTC holati noma'lum" in (r.detail or "")]
    assert not noaniq, f"BTC shamlari yuklanmagan: {noaniq[:2]}"


def salomatlik(qiymat: float):  # noqa: ANN201
    from core.domain.models import MarketHealth

    return MarketHealth(value=qiymat, factors=[], computed_at=datetime.now(UTC))


# --------------------------------------------------------------------------- #
#  4.1 — Kunlik zarar chegarasi: e'lon qilingan, lekin ulanmagan edi
# --------------------------------------------------------------------------- #


async def test_kunlik_zarar_siklga_uzatiladi(db: Database, config) -> None:  # noqa: ANN001
    """`DailyLossLimitRule` bor edi, lekin qiymat HECH QACHON hisoblanmasdi.

    `daily_loss_pct` standart `0.0` bo'lib qolardi, ya'ni chegara hech
    qachon to'lmasdi — strategiya qancha zarar keltirsa ham signal
    berishda davom etardi. Bu signal to'smaydi, lekin HIMOYANI
    o'chirib qo'yadi.
    """
    from core.domain.enums import SignalSource, SignalStatus
    from core.storage.repositories import SignalRepository

    async with db.session() as session:
        repo = SignalRepository(session)
        for i in range(2):
            yozuv = await repo.create(
                symbol=f"C{i}",
                levels=signal_levels(entry=100.0, stop=97.0, tp1=104.0, tp2=110.0),
                source=SignalSource.MANUAL,
            )
            # Har biri -2% zarar bilan yopiladi
            await repo.apply_event(
                yozuv.id, SignalStatus.STOPPED, 98.0, datetime.now(UTC), "stopped"
            )

    async with db.session() as session:
        kunlik, haftalik = await PipelineRunner._zarar_ulushlari(SignalRepository(session))

    assert kunlik > 0, "kunlik zarar hisoblanmasa 4.1-band qoidasi o'lik"
    assert haftalik >= kunlik
    assert kunlik == pytest.approx(4.0, abs=0.1), "ikkita -2% savdo -> 4% zarar"


async def test_foydali_kun_zarar_deb_hisoblanmaydi(db: Database, config) -> None:  # noqa: ANN001
    """Kun +5% va -2% bilan o'tgan bo'lsa, kun yomon o'tmagan.

    Gross zarar bilan hisoblash foydali kunni ham to'xtatib qo'yardi.
    """
    from core.domain.enums import SignalSource, SignalStatus
    from core.storage.repositories import SignalRepository

    async with db.session() as session:
        repo = SignalRepository(session)
        yutuq = await repo.create(
            symbol="WIN",
            levels=signal_levels(entry=100.0, stop=97.0, tp1=104.0, tp2=110.0),
            source=SignalSource.MANUAL,
        )
        await repo.apply_event(
            yutuq.id, SignalStatus.TP2_HIT, 105.0, datetime.now(UTC), "tp2_hit"
        )
        zarar = await repo.create(
            symbol="LOSS",
            levels=signal_levels(entry=100.0, stop=97.0, tp1=104.0, tp2=110.0),
            source=SignalSource.MANUAL,
        )
        await repo.apply_event(
            zarar.id, SignalStatus.STOPPED, 98.0, datetime.now(UTC), "stopped"
        )

    async with db.session() as session:
        kunlik, _ = await PipelineRunner._zarar_ulushlari(SignalRepository(session))

    assert kunlik == 0.0, "sof natija musbat — zarar chegarasi ishlamasligi kerak"
