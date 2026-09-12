"""Konfiguratsiya sxemasi — `config/default.yaml` ning tiplashtirilgan aksi.

6.4-band: barcha "sehrli raqamlar" shu yerdagi maydonlar orqali o'qiladi.
Kodning hech bir joyida raqam qattiq yozilmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from core.utils.time_utils import parse_hhmm

# --------------------------------------------------------------------------- #
#  Loyiha
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    name: str = "HALOL CRYPTO SAVDO"
    default_language: str = "uz"
    supported_languages: list[str] = field(default_factory=lambda: ["uz"])


# --------------------------------------------------------------------------- #
#  3.4 — Halol skrining
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class HalalScreeningConfig:
    target_count: int = 200
    max_scan_depth: int = 500
    min_daily_volume_usd: float = 50_000_000
    quote_asset: str = "USDT"
    exclude_stablecoins: bool = True
    stablecoin_symbols: list[str] = field(default_factory=list)
    refresh_interval_hours: int = 12
    seed_haram_symbols: list[str] = field(default_factory=list)
    seed_mashbooh_symbols: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  3.1 / 3.2 — Tahlil
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class OpenSignalLimits:
    high: int = 5
    mid: int = 3
    low: int = 0


@dataclass(frozen=True, slots=True)
class CorrelationGroup:
    name: str
    symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class KillSwitchConfig:
    price_spike_pct: float = 5.0
    price_spike_window_seconds: int = 60
    requires_manual_reset: bool = True


@dataclass(frozen=True, slots=True)
class ConsecutiveLossConfig:
    max_consecutive_stops: int = 5
    cooldown_hours: int = 24


@dataclass(frozen=True, slots=True)
class FridayFilterConfig:
    """4.8-band — Juma namozi vaqti filtri."""

    enabled: bool = True
    timezone: str = "Asia/Tashkent"
    weekday: int = 4
    start: str = "11:00"
    end: str = "15:00"

    @property
    def start_time(self) -> time:
        return parse_hhmm(self.start)

    @property
    def end_time(self) -> time:
        return parse_hhmm(self.end)


@dataclass(frozen=True, slots=True)
class RiskEngineConfig:
    """Portfel chegaralari — SOZLAMA, modul emas.

    2026-09-04: `core/risk_engine/` MODULI o'chirildi. U qurilgan edi,
    lekin hech qayerdan chaqirilmasdi — bot uni yaratib, faqat
    jurnalga yozardi.

    Bu SOZLAMA esa qoladi va YANGI modul ishlatadi:

        correlation_group_of()  -> `core/services/zanjir_sikl.py`
        max_open_signals        -> sig'im o'lchovi
        friday_filter           -> `core/config/loader.py`

    Ya'ni bu eski modulning qoldig'i emas. Pulni taqsimlash qoidalari
    alohida modul sifatida qayta quriladi — o'shanda bu bo'lim ham
    qayta ko'rib chiqiladi.
    """

    daily_loss_limit_pct: float = 3.0
    weekly_loss_limit_pct: float = 8.0
    max_open_signals: int = 5
    max_open_signals_by_health: OpenSignalLimits = field(default_factory=OpenSignalLimits)
    correlation_groups: list[CorrelationGroup] = field(default_factory=list)
    max_signals_per_correlation_group: int = 1
    kill_switch: KillSwitchConfig = field(default_factory=KillSwitchConfig)
    consecutive_loss: ConsecutiveLossConfig = field(default_factory=ConsecutiveLossConfig)
    friday_filter: FridayFilterConfig = field(default_factory=FridayFilterConfig)
    #: Sham ma'lumoti necha soniyagacha eski bo'lishi mumkin. Ilgari
    #: `analysis.entry_timeframe` dan hisoblanardi.
    max_candle_age_seconds: float = 28800.0

    def correlation_group_of(self, symbol: str) -> str | None:
        """Coin qaysi korrelyatsiya guruhiga tegishli (4.3-band, statik ro'yxat)."""
        upper = symbol.upper()
        for group in self.correlation_groups:
            if upper in {s.upper() for s in group.symbols}:
                return group.name
        return None


# --------------------------------------------------------------------------- #
#  3.7 — Bozor Salomatligi Indeksi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class BtcDominanceConfig:
    stable_change_pct: float = 0.5
    sharp_change_pct: float = 2.0


@dataclass(frozen=True, slots=True)
class RiskTier:
    """Pog'onali kunlik xavf foizi. `max_balance is None` — eng yuqori pog'ona."""

    max_balance: float | None
    daily_risk_pct: float


@dataclass(frozen=True, slots=True)
class AggregateConfig:
    capacity_used_threshold: float = 0.8
    active_user_days: int = 7


def _default_risk_tiers() -> list[RiskTier]:
    """5.1-band standart pog'onalari — konfiguratsiya fayli bo'lmasa ham
    tizim yaroqli holatda ishga tushishi kerak."""
    return [
        RiskTier(max_balance=1000, daily_risk_pct=3.0),
        RiskTier(max_balance=10000, daily_risk_pct=2.0),
        RiskTier(max_balance=None, daily_risk_pct=1.5),
    ]


@dataclass(frozen=True, slots=True)
class PositionSizingConfig:
    risk_tiers: list[RiskTier] = field(default_factory=_default_risk_tiers)
    allocation_method: str = "sequential_decay"
    sequential_decay_fraction: float = 0.34
    equal_split_expected_slots: int = 3
    min_allocation_usd: float = 1.0
    max_position_pct_of_balance: float = 100.0
    aggregate: AggregateConfig = field(default_factory=AggregateConfig)


# --------------------------------------------------------------------------- #
#  3.9 — Strategiyalar
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PortfolioConfig:
    """5.4-band: "Men kirdim" va foyda/zarar hisobi."""

    #: Har bir TP da yopiladigan ulush — TP SONIGA qarab.
    #:
    #: Indeks = TP soni - 1, ya'ni birinchi qator bitta TP uchun,
    #: ikkinchisi ikkita uchun va hokazo. Har bir qatorning
    #: yig'indisi 100 bo'lishi shart.
    #:
    #: NIMA UCHUN JADVAL. Ilgari bu yerda bitta `tp1_close_pct: 50`
    #: turardi va u "TP har doim ikkita" degan taxminni ichiga
    #: yashirgan edi. TP soni 1 yoki 3 bo'lganda o'sha 50 raqami
    #: ma'nosini yo'qotardi.
    tp_close_shares: tuple[tuple[float, ...], ...] = (
        (100.0,),                # bitta TP — hammasi shu yerda
        (50.0, 50.0),            # ikkita — yarim-yarim
        (40.0, 30.0, 30.0),      # uchta — birinchisi kattaroq
    )
    min_position_usd: float = 1.0

    #: Balans nechta TENG bo'lakka bo'linadi (3-prompt, 1-qism).
    #:
    #: 3 — BOSHLANG'ICH qiymat, qat'iy qoida emas. Promptning o'zi
    #: shuni ta'kidlaydi, shuning uchun raqam kodda emas, shu yerda.
    bolak_soni: int = 3

    #: Bitta bo'lakning ichki zarar chegarasi, foizda.
    #:
    #: BO'LAKNING O'ZIDAN hisoblanadi, umumiy balansdan emas. Stop
    #: shu chegaradan uzoq bo'lsa, bo'lakning bir qismi ishlatiladi
    #: va xavf baribir chegarada qoladi.
    bolak_chegara_pct: float = 10.0

    def shares_for(self, count: int) -> tuple[float, ...]:
        """`count` ta TP uchun ulushlar.

        Jadvalda yo'q son so'ralsa teng bo'linadi — bu himoya
        qatlami: noto'g'ri sozlama signalni yo'qotmasin, lekin
        raqam ham o'ylab topilmasin.
        """
        if 1 <= count <= len(self.tp_close_shares):
            return tuple(self.tp_close_shares[count - 1])
        if count < 1:
            raise ValueError("TP soni kamida 1 bo'lishi kerak")
        return tuple(100.0 / count for _ in range(count))

    @property
    def tp1_close_pct(self) -> float:
        """Ikkita TP bo'lganda BIRINCHISIDA yopiladigan ulush.

        Eski nom saqlanadi, chunki u ko'p joyda parametr sifatida
        uzatiladi. Lekin endi u mustaqil raqam emas — jadvaldan
        o'qiladi, ya'ni manba bitta.
        """
        return self.shares_for(2)[0]


# --------------------------------------------------------------------------- #
#  3.8 — Signal Xotirasi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class SubscriptionPeriods:
    daily: int = 1
    monthly: int = 30


@dataclass(frozen=True, slots=True)
class SubscriptionsConfig:
    tiers: list[str] = field(default_factory=lambda: ["lite", "pro", "premium"])
    periods: SubscriptionPeriods = field(default_factory=SubscriptionPeriods)
    expiry_reminder_days: list[int] = field(default_factory=lambda: [2, 1])
    currencies: list[str] = field(default_factory=lambda: ["KGS", "USDT"])


# --------------------------------------------------------------------------- #
#  6.2 — Bozor ma'lumotlari
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class MarketDataConfig:
    exchange: str = "binance"
    ws_base_url: str = "wss://stream.binance.com:9443/stream"
    rest_base_url: str = "https://api.binance.com"
    ranking_source: str = "coinmarketcap"
    coinmarketcap_base_url: str = "https://pro-api.coinmarketcap.com/v1"
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    reconnect_backoff_seconds: list[int] = field(default_factory=lambda: [2, 4, 8, 16, 32])
    stale_price_seconds: int = 90
    #: Bir vaqtda nechta OHLCV so'rovi yuborilsin.
    #:
    #: Ilgari chegara umuman yo'q edi: sikl BARCHA coin × BARCHA timeframe
    #: so'rovini bir zumda yuborardi. 30 ta coinda bu 90 ta parallel so'rov
    #: — birja chidadi. 150 ta coinda 450 ta bo'ladi va Binance avval 429,
    #: keyin 418 (IP ban) qaytaradi. Ya'ni ro'yxatni kengaytirish
    #: chegarasiz ishlamaydi.
    max_concurrent_candle_requests: int = 8
    #: Sahifalab yuklashda ikki so'rov orasidagi pauza (soniya).
    #:
    #: Backtest 730 kunlik 15 daqiqalik qatorni so'raganda bu ~70 ta
    #: KETMA-KET so'rov bo'ladi (har biri 1000 sham). Pauzasiz ular bir
    #: zumda ketadi va Binance avval 429, keyin 418 (IP ban) qaytaradi.
    #: Jonli botga ta'siri yo'q: u 1000 dan kam so'raydi, ya'ni bitta
    #: sahifa — pauza umuman ishlamaydi.
    candle_page_pause_seconds: float = 0.25
    #: Sham ma'lumoti necha "timeframe" gacha eski bo'lishi mumkin.
    #:
    #: `stale_price_seconds` (90s) TIK oqimi uchun — u kuzatuvchida
    #: ishlatiladi va u yerda to'g'ri. Lekin SIGNAL QARORI shamdan
    #: olingan narxga tayanadi (`_joriy_narx()` oxirgi sham yopilishini
    #: qaytaradi), shuning uchun bu yerda sham yoshi o'lchanadi. 1
    #: soatlik sham tabiatan 1 soatgacha "eski" bo'ladi — 90 soniyalik
    #: chegara unga umuman to'g'ri kelmaydi.
    stale_candle_multiplier: float = 2.0


# --------------------------------------------------------------------------- #
#  6.4 — Logging
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str = "INFO"
    dir: str = "logs"
    rotate_mb: int = 20
    backups: int = 5


# --------------------------------------------------------------------------- #
#  Ildiz
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class MonitoringConfig:
    """Kuzatuv vositalari — savdo qaroriga ta'sir qilmaydi.

    Eski tahlil moduli olib tashlanganda `pipeline_events` ham ketdi —
    u eski siklning bosqichlarini yozardi. Yangi modul o'z kuzatuvini
    olib keladi.
    """

    enabled: bool = True


@dataclass(frozen=True, slots=True)
class SinovDavriConfig:
    """Sinov davri — tizim FAQAT bozorga qarab baholanadi.

    NIMA UCHUN. `aggregate_user_capacity` omili bozorni emas, BIZNING
    holatimizni o'lchaydi: obunachilarning balansi va kunlik xavf
    sig'imi. Sinov paytida obunachi yo'q, ya'ni bu omil bozor haqida
    HECH NARSA aytmaydi — u yo tekin 20 ball beradi, yo (bitta test
    foydalanuvchisi limitga yaqinlashsa) indeksni tushiradi. Ikkala
    holat ham sinov natijasini buzadi.

    Halollik talabi ham shuni aytadi: ommaga "tizim shu natijani
    berdi" deb ko'rsatilganda, o'sha natijaga bizning obunachilar soni
    aralashmagan bo'lishi kerak.

    VAZN YO'QOLMAYDI, QAYTA TAQSIMLANADI. Omil shunchaki olib
    tashlansa, indeksning yuqori chegarasi 100 dan 80 ga tushardi va
    barcha chegaralar (55, 70) jimgina boshqa ma'no olardi — bu
    loyihadagi 1-naqsh ("shkala mos kelmasligi"). Shuning uchun qolgan
    omillar vazni ulushiga qarab kattalashtiriladi.

    Muddat tugagach omil O'ZI qaytadi — hech kim hech narsani yoqishi
    shart emas.
    """

    enabled: bool = True
    #: ISO sana: "YYYY-MM-DD". Sinov shu kundan boshlanadi.
    start_date: str = "2026-08-29"
    days: int = 100
    #: Indeksdan chiqariladigan omillar (nomi `factors.py` dagidek)
    exclude_health_factors: list[str] = field(
        default_factory=lambda: ["aggregate_user_capacity"]
    )
    #: Sinov davrida TO'XTATIB TURILADIGAN Risk Engine qoidalari.
    #:
    #: Bular BOZORNI emas, BIZNING holatimizni o'lchaydi: bugungi
    #: zararimiz, nechta signalimiz ochiq, ketma-ket nechta Stop
    #: yedik. Ular signal berishni to'xtatsa, sinov namunasi
    #: qiyshayadi: yomon ertalakdan keyin tizim o'zini o'chiradi va
    #: qolgan kunni umuman ko'rmaymiz — "bu strategiya nima qiladi?"
    #: degan savolga javob yarim qoladi.
    #:
    #: BOZORGA oid qoidalar (BTC filtri, tekis bozor, volatillik,
    #: Bozor Salomatligi) va DINIY qoidalar (halol ro'yxat, juma
    #: namozi) hech qachon to'xtatilmaydi.
    suspend_risk_rules: list[str] = field(
        default_factory=lambda: [
            "daily_loss_limit",
            "max_open_signals",
            "correlation",
            "consecutive_loss",
        ]
    )

    def boshlanish(self) -> date:
        """YAML'da tirnoqsiz yozilsa PyYAML uni `date` qilib beradi —
        ikkala ko'rinish ham qabul qilinadi."""
        if isinstance(self.start_date, date):
            return self.start_date
        return date.fromisoformat(str(self.start_date))

    def tugash(self) -> date:
        return self.boshlanish() + timedelta(days=self.days)

    def faolmi(self, moment: datetime) -> bool:
        kun = moment.date()
        return self.enabled and self.boshlanish() <= kun < self.tugash()

    def qolgan_kun(self, moment: datetime) -> int:
        return max(0, (self.tugash() - moment.date()).days)


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """6.3-band: backtestni HAQIQATGA yaqinlashtiruvchi xarajatlar.

    Ilgari bular umuman modellashtirilmagan edi va bu natijani
    tizimli ravishda CHIROYLIROQ ko'rsatardi. Spot savdoda har bir
    pozitsiya ikki marta to'laydi: kirishda ham, chiqishda ham.
    649 ta savdoda 0.1% lik komissiya ~130% ni yeb qo'yadi — ya'ni
    xulosa o'zgarishi mumkin bo'lgan hajm.

    Bu raqamlar TAXMIN emas, birjaning e'lon qilgan tarifi:
    Binance spot taker 0.1%. Slippage esa o'lchanmagan, shuning
    uchun ehtiyotkor (yuqoriroq) qiymat olinadi — natijani
    yaxshiroq ko'rsatgandan ko'ra yomonroq ko'rsatgan afzal.
    """

    #: Bir tomonlama komissiya, foizda (Binance spot taker = 0.1)
    fee_pct: float = 0.1
    #: Har bir bajarilishdagi kutilayotgan sirg'anish, foizda.
    #:
    #: Stop va TP darajalari LIMIT emas: narx daraja orqali o'tib
    #: ketadi va to'ldirish undan narida bo'ladi. Aniq qiymat
    #: coinga va vaqtga bog'liq — bu ehtiyotkor o'rtacha.
    slippage_pct: float = 0.05

    @property
    def round_trip_cost_pct(self) -> float:
        """Bitta savdoning to'liq xarajati (kirish + chiqish), foizda.

        Pozitsiya IKKI marta to'laydi: sotib olishda va sotishda.
        TP1 da yarmi yopilsa ham jami hajm o'zgarmaydi — yarmi TP1 da,
        yarmi keyin sotiladi — shuning uchun xarajat baribir ikki
        tomonlama.

        EHTIYOTKOR TOMONGA OG'DIRILGAN. Kirish ko'pincha LIMIT
        buyurtma bo'ladi (5.1.0-band), ya'ni undagi komissiya
        pastroq va sirg'anish yo'q. Bu yerda ikkalasiga ham to'liq
        xarajat qo'yiladi: natijani yaxshiroq ko'rsatgandan ko'ra
        yomonroq ko'rsatgan afzal.
        """
        return 2 * (self.fee_pct + self.slippage_pct)


# --------------------------------------------------------------------------- #
#  Yangi tahlil moduli — TO'RT BLOKLI ZANJIR (2026-09-03)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ZanjirTimeframeConfig:
    """3-qism: to'rt qavatli timeframe tizimi.

    Qiymatlar backtest orqali o'zgartiriladi (masalan 4h o'rniga 6h).
    """

    #: Faqat yo'nalish filtri
    yonalish: str = "1w"
    #: ASOSIY struktura va zona — o'rta muddat gorizontiga mos
    asosiy: str = "1d"
    #: Asosiy zona ichida aniqroq OB/FVG
    aniqlik: str = "4h"
    #: Pastki TF tasdig'i (aniq Entry narxi)
    tasdiq: str = "15m"


@dataclass(frozen=True, slots=True)
class NomzodFiltrConfig:
    """1-qism: zanjirdan OLDINGI oddiy ha/yo'q filtrlar.

    QAT'IY COIN SONI YO'Q (2-prompt, 0-qism, 1-tamoyil). "Top 30"
    kabi cheklov qo'yilmaydi — barcha halol, likvidlik shartidan
    o'tgan coinlar nomzod.
    """

    #: Minimal kunlik savdo hajmi (USD)
    eng_kam_hajm_usd: float = 50_000_000.0
    #: Coin yetukligi chegaralari (kunda)
    yangi_coin_kun: int = 90
    yarim_yetuk_kun: int = 365


@dataclass(frozen=True, slots=True)
class BloklarConfig:
    """Ichki tekshiruvlarning chegaralari.

    HAMMASI 🔴 O'LCHANMAGAN. Ular ablatsiya va backtest orqali
    topiladi (2-prompt, 0-qism, 3-tamoyil). Bu yerdagi qiymatlar —
    BOSHLANG'ICH nuqta, yakuniy javob emas.
    """

    #: 1.1 — funding shu qiymatdan manfiy bo'lsa ijobiy
    funding_sovugan: float = -0.0001
    #: 1.4 — Fear & Greed shundan past bo'lsa xaridga qulay
    fng_yuqori_chegara: int = 55
    #: 1.3 — unlock qattiq to'sig'i
    unlock_yaqin_kun: int = 7
    unlock_katta_pct: float = 5.0
    #: 2.1 — fraktal yarim kengligi
    fraktal_qanot: int = 2
    #: 2.4 — nisbiy kuch oynasi (sham)
    nisbiy_kuch_oyna: int = 20
    #: 3.1 — Fibonacci zona chegaralari
    fib_yuqori: float = 0.382
    fib_past: float = 0.618
    #: 3.2 — Order Block ta'rifi: "last_opposite" yoki "sweep_candle"
    ob_tarifi: str = "last_opposite"
    #: 3.4 — Volume Profile
    poc_savatlar: int = 50
    poc_yaqinlik_pct: float = 2.0
    #: 4.1 — Liquidity Sweep
    sweep_eng_kam_pct: float = 0.1
    sweep_qaytish_sham: int = 3
    #: 4.3 — RSI
    rsi_davr: int = 14
    rsi_past_zona: float = 35.0
    #: Ikki birja wick farqi shundan oshsa — sham shubhali
    wick_farq_chegara_pct: float = 1.0


@dataclass(frozen=True, slots=True)
class DarajalarConfig:
    """5-qism: Entry/Stop/TP xavfsizlik chegaralari.

    Bular Stop ni BELGILAMAYDI — u zona chetidan olinadi. Bular
    faqat RAD ETADI: chegaradan tashqaridagi signal berilmaydi.
    """

    #: 🟢 O'LCHANDI — `config/default.yaml` dagi izohga qarang.
    stop_eng_kam_pct: float = 1.5
    stop_eng_kop_pct: float = 15.0
    tp1_eng_kam_nisbat: float = 1.2
    tp_eng_kop: int = 3

    #: Ikki TP orasidagi ENG KAM masofa (entry'ga nisbatan foizda).
    #:
    #: 🔴 O'LCHANMAGAN.
    #:
    #: Struktura ba'zan bir-biriga juda yaqin ikkita swing yuqori
    #: beradi — ular BITTA qarshilik. 2026-09-04 da LTC signalida
    #: TP2 = 54.70, TP3 = 54.78 bo'lib chiqdi: orasi 0.16%.
    #: Pozitsiyani shu yerda 30/30 qilib bo'lish ma'nosiz — ikkinchi
    #: sotuvning komissiyasi (0.1% + 0.05% sirg'anish) farqning katta
    #: qismini yeydi.
    tp_eng_kam_oraliq_pct: float = 1.0

    #: Stop LIKVIDLIKDAN shuncha foiz pastga qo'yiladi. `0` — o'chiq.
    #:
    #: 🔴 O'LCHANMAGAN.
    #:
    #: Stop zona chetiga qo'yilardi va boshqa hech narsaga
    #: qaralmasdi. Lekin zona cheti oxirgi swing PAST ustiga
    #: tushishi mumkin — ya'ni to'plangan likvidlikning ichiga.
    #: Stop-hunt aynan o'sha yerda bo'ladi.
    #:
    #: FAQAT KERAK BO'LGANDA uzaytiriladi: zona pasti allaqachon
    #: likvidlikdan past bo'lsa, hech narsa o'zgarmaydi (loyiha
    #: egasining tanlovi, 2026-09-05).
    stop_likvidlik_bufer_pct: float = 0.3


@dataclass(frozen=True, slots=True)
class ChiqishConfig:
    """5-qism: masshtablab sotish va vaqt chegaralari.

    `trailing_yoqilgan` STANDART HOLATDA FALSE. Bu — o'lchangan
    qaror: eski tizimda surilgan Stop PF ni 0.84 dan 0.36 ga
    tushirgan (`GIPOTEZA_DAFTARI.md`, 9-to'plam natijasi). Yangi
    tizimda u faqat TP2 dan keyingi qoldiqqa tegadi, lekin baribir
    backtest ruxsat bermaguncha yoqilmaydi.
    """

    ulushlar: list[float] = field(default_factory=lambda: [50.0, 30.0])
    tp1_breakeven: bool = True
    trailing_yoqilgan: bool = False
    trailing_r: float = 1.0
    qoldiq_muddat_kun: int = 14
    umumiy_muddat_kun: int = 28


@dataclass(frozen=True, slots=True)
class AiVerificationConfig:
    """5-blok — sun'iy intellekt tekshiruvi (yakuniy filtr).

    FAQAT 4 blok o'tgan nomzod uchun ishga tushadi. DeepSeek API
    orqali "TASDIQLANDI" yoki "RAD ETILDI" javobini oladi. Noaniqlik
    yoki API xatosi — RAD ETILDI (signal chiqarilmaydi).
    """

    enabled: bool = False
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/chat/completions"
    api_key_env: str = "DEEPSEEK_API_KEY"
    timeout_seconds: float = 20.0
    max_tokens: int = 8


@dataclass(frozen=True, slots=True)
class ZanjirConfig:
    """Yangi tahlil modulining butun sozlamasi."""

    timeframelar: ZanjirTimeframeConfig = field(default_factory=ZanjirTimeframeConfig)
    nomzod: NomzodFiltrConfig = field(default_factory=NomzodFiltrConfig)
    bloklar: BloklarConfig = field(default_factory=BloklarConfig)
    darajalar: DarajalarConfig = field(default_factory=DarajalarConfig)
    chiqish: ChiqishConfig = field(default_factory=ChiqishConfig)
    ai: AiVerificationConfig = field(default_factory=AiVerificationConfig)
    #: JONLI tizim kuzatadigan coinlar — 80 ta.
    #:
    #: NIMA UCHUN 80. Ilgari bu yerda 200 ta turardi, lekin ularni
    #: HECH KIM halollikka tekshirmagan edi: loyihaning halol testi
    #: atigi ~30 ta urug' nomni bilardi, qolgani jimgina o'tib
    #: ketardi. Orasida ONDO (obligatsiya — foiz), ALPACA (leverage),
    #: FUN (qimor), XVS/KAVA (qarz berish) kabilar bor edi — ya'ni
    #: mahsulotning eng asosiy va'dasiga zid coinlar.
    #:
    #: Ro'yxat mustaqil skrining manbasi bilan kesishtirildi va
    #: faqat IKKALASIDA ham bor 80 tasi qoldi. Manba, sana, chiqarish
    #: sabablari va tasdiq holati: `docs/HALOL_ROYXAT.md`.
    #: `tests/core/test_zanjir_sikl.py` shu ikkisi ajralib
    #: ketmasligini tekshiradi.
    #:
    #: ⚠️ Ro'yxat DINIY HUJJAT EMAS — bilimli kishi tasdig'i
    #: kutilmoqda.
    #:
    #: O'LCHANMAGAN: o'lchov 12 coinlik to'plamda o'tkazilgan (4 yil,
    #: 498 savdo, PF 3.49). 80 coinda tizim qanday ishlashi
    #: o'lchanmagan — `docs/GIPOTEZA_DAFTARI.md`. O'sha 12 tasi shu
    #: ro'yxatning ichida.
    kuzatiladigan_coinlar: list[str] = field(
        default_factory=lambda: [
            "BTC", "ETH", "SOL", "ADA", "AVAX", "LINK",
            "DOT", "BCH", "LTC", "NEAR", "ETC", "FIL",
            "APT", "SUI", "POL", "XLM", "HBAR", "VET",
            "ATOM", "OP", "ARB", "TAO", "TIA", "STX",
            "IMX", "GRT", "RENDER", "ALGO", "EGLD", "THETA",
            "S", "PYTH", "FLOW", "MINA", "AR", "CKB",
            "ZIL", "ONE", "KSM", "CELO", "BAT", "IOTA",
            "XTZ", "QTUM", "NEO", "STORJ", "SC", "RVN",
            "MASK", "API3", "TRB", "ICX", "ONT", "ASTR",
            "MOVR", "STRAX", "PHA", "REQ", "BICO", "RARE",
            "JASMY", "STRK", "XEC", "TFUEL", "HOT", "IOST",
            "STEEM", "HIVE", "ACH", "RIF", "CTSI", "EDU",
            "DYM", "SAGA", "TWT", "CHR", "AVA", "CVC",
            "QKC", "DGB",
        ]
    )
    #: Sikl necha soatda bir marta yuradi.
    #:
    #: Zanjirning asosiy timeframei — 1 kun. Kunlik sham
    #: yopilishini kutib o'tirish signalni 24 soatgacha
    #: kechiktirardi; 4 soat — oraliq yechim: struktura
    #: kunlik shamdan o'qiladi, lekin zona ichiga narx
    #: kirganda 4 soat ichida ushlanadi.
    sikl_soat: int = 4
    #: Signal chiqishi uchun minimal ishonch (0..1).
    #:
    #: 🔴 O'LCHANMAGAN va ATAYLAB 0.0. Zanjirning O'ZI darvoza:
    #: to'rtala blok ham o'tishi kerak. Ishonch chegarasi — QO'SHIMCHA
    #: filtr, va uni taxminan qo'yish aynan eski tizimning xatosi
    #: bo'lardi. Backtest topguncha 0.0 turadi.
    eng_kam_ishonch: float = 0.0
    #: Sikl SIGNAL YOZADIMI.
    #:
    #: ⛔ 2026-09-10 DAN BERI O'CHIQ — loyiha egasining qarori.
    #:
    #: NIMA UCHUN. To'rtta mustaqil o'lchov bir xil javob berdi:
    #:
    #:   1. Ablatsiya — birorta ichki tekshiruvni olib tashlash
    #:      natijani na yaxshiladi, na yomonlashtirdi;
    #:   2. Zanjirsiz backtest PF 0.84, to'liq zanjir bilan 0.83;
    #:   3. Chegara supurgisi — R:R 1.2 dan 3.0 ga ko'tarilganda
    #:      g'alaba foizi deyarli aynan mutanosib tushdi, ya'ni
    #:      kirish nuqtalari tasodifiy;
    #:   4. XGBoost — 16 486 qatorda ham foydali chegara topilmadi
    #:      (`docs/BACKTEST_NATIJA_2026-09-10_model2.md`).
    #:
    #: Ya'ni signallar o'lchov bo'yicha ZARAR keltiradi. Obunachiga
    #: zarar keltiradigan signal yuborish — mahsulotning eng asosiy
    #: va'dasiga zid.
    #:
    #: NIMA TO'XTAYDI: faqat SIGNAL YOZISH. Sikl o'zi 4 soatda
    #: yugurishda davom etadi va har bir coin holatini
    #: `zanjir_holatlari` ga yozadi — ya'ni "nega signal yo'q"
    #: voronkasi, admin monitori va kelajakdagi o'lchovlar uchun
    #: yozuv YO'QOLMAYDI. Mavjud ochiq signallar ham odatdagidek
    #: kuzatiladi (TP/Stop belgilanadi).
    #:
    #: Admin panelidan QO'LDA signal yozish ishlashda davom etadi —
    #: bu bayroq faqat AVTOMATIK yo'lni to'sadi.
    #:
    #: QAYTA YOQISH: shu qiymatni `True` qilish yetarli. Lekin
    #: undan oldin o'lchov MUSBAT natija berishi kerak — aks holda
    #: to'xtatishning ma'nosi yo'q.
    avtomatik_signal: bool = False


@dataclass(frozen=True, slots=True)
class KuzatuvConfig:
    """Kuzatuv paneli — 80 coin, SIGNAL BERMAYDI (9-prompt).

    Signal moduli (`zanjir`) bilan ALOHIDA sozlama. Ular bir xil
    coin ro'yxatini o'qiydi, lekin timeframe va oraliqlari
    mustaqil: biri o'zgarganda ikkinchisi jimgina o'zgarmasin.
    """

    #: Skan necha soatda bir marta o'zi yuradi.
    #:
    #: Admin istalgan paytda BITTA skanni qo'lda ishga tushira
    #: oladi (`kuzatuv_skani.sorov`). "To'xtatish" tugmasi yo'q:
    #: skan tugagach o'zi to'xtaydi (loyiha egasining qarori,
    #: 2026-09-12).
    skan_soat: int = 4

    #: Struktura va Uptrend filtri qaysi grafikdan o'qiladi
    tf_struktura: str = "4h"
    #: Zona, Liquidity Sweep va RSI qaysi grafikdan
    tf_zona: str = "1h"
    #: Pastki TF tasdig'i qaysi grafikdan
    tf_pastki: str = "15m"

    #: Kunlik coin qidiruv chegarasi — obunaga qarab.
    #:
    #: 🔴 O'LCHANMAGAN, boshlang'ich qiymat. Admin panelda
    #: o'zgartiriladi; kodda qattiq yozilmagan.
    qidiruv_obunasiz: int = 1
    qidiruv_lite: int = 3
    qidiruv_pro: int = 10
    qidiruv_premium: int = 30


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Butun tizimning yagona konfiguratsiya obyekti."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    #: Sinov davri — BIZGA tegishli omillar va tormozlar vaqtincha chetda
    sinov: SinovDavriConfig = field(default_factory=SinovDavriConfig)
    halal_screening: HalalScreeningConfig = field(default_factory=HalalScreeningConfig)
    risk_engine: RiskEngineConfig = field(default_factory=RiskEngineConfig)
    zanjir: ZanjirConfig = field(default_factory=ZanjirConfig)
    kuzatuv: KuzatuvConfig = field(default_factory=KuzatuvConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    position_sizing: PositionSizingConfig = field(default_factory=PositionSizingConfig)
    subscriptions: SubscriptionsConfig = field(default_factory=SubscriptionsConfig)
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
