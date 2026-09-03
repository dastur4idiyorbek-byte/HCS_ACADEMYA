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
    target_count: int = 150
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
class SupportResistanceConfig:
    swing_lookback: int = 5
    zone_merge_atr_mult: float = 0.5
    min_touches: int = 2
    proximity_atr_mult: float = 1.0
    #: Kirish uchun ruxsat etilgan eng yuqori diapazon foizi.
    #:
    #: Ilgari chegara qat'iy 50% (muvozanat chizig'i) edi va bu JAR
    #: yaratardi: 49.9% — ruxsat, 50.1% — butunlay rad. Jonli
    #: ma'lumotda rad etishlarning 60% i shu bosqichda edi, tafsilotlar
    #: esa "Premium zonada (51%)" deb ko'rsatardi — ya'ni chegaradan
    #: bir foiz narida.
    #:
    #: Ball allaqachon CHUQURLIKNI darajali baholaydi (`depth`): 50% da
    #: 0 ball, Support'da to'liq ball. Ya'ni chuqurroq qaytish baribir
    #: yuqoriroq o'ringa chiqadi. Qat'iy jar esa shunchaki chetdagi
    #: nomzodlarni butunlay yo'q qilardi.
    entry_max_range_pct: float = 55.0
    fibonacci_levels: list[float] = field(default_factory=lambda: [0.382, 0.5, 0.618])


@dataclass(frozen=True, slots=True)
class IndicatorConfig:
    #: Tahlil uchun kerakli minimal sham soni.
    #:
    #: Ilgari bu chegara `ema_slow` (200) edi — EMA200 hisoblash uchun
    #: shuncha sham kerak. EMA olib tashlangach chegara o'z ma'nosini
    #: yo'qotdi: qolgan eng "och" indikator MACD (26+9) va struktura
    #: (bir necha swing). 200 sham talabi haftalik timeframeda ~3.8
    #: yil tarix degani edi va ko'p altcoinlarni jimgina chetlab
    #: o'tardi (`docs/ARXITEKTURA.md`, 58-bo'lim).
    min_candles: int = 60
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    volume_ma_period: int = 20
    atr_period: int = 14
    adx_period: int = 14
    adx_trend_threshold: float = 20.0
    #: Nechta indikator tasdiqlasa "tasdiqlangan" deb hisoblanadi. Endi bu
    #: faqat KO'RSATISH uchun — `require_confirmation` `False` bo'lgani
    #: uchun signalni to'xtatmaydi.
    min_confirmations: int = 2
    #: Indikator tasdig'i signal uchun MAJBURIYmi.
    #:
    #: `False` — indikatorlar faqat ballga ta'sir qiladi, ya'ni ko'p coin
    #: ichidan TANLASH uchun ishlatiladi, "mumkin/mumkin emas" degan
    #: qaror uchun emas.
    #:
    #: Sabab: indikatorlar tabiatan KECHIKADI. Ular narx harakatidan
    #: keyin tasdiqlaydi, o'sha paytda narx allaqachon Discount zonasidan
    #: chiqib ketgan bo'ladi. Ya'ni "indikator tasdiqlasin" talabi
    #: "arzon paytda olma, qimmatlashgach ol" degani bilan barobar —
    #: strategiyaning o'z maqsadiga zid.
    #:
    #: Qaror strukturaga (S/R zonasi) va risk qoidasiga (3.3-band)
    #: qoldiriladi; indikatorlar reytingni belgilaydi.
    require_confirmation: bool = False


@dataclass(frozen=True, slots=True)
class EntryOrderConfig:
    """5.1.0-band: kirish buyurtmasi turi avtomatik tanlanadi.

    - Narx hali Entry zonasiga yetib bormagan  -> LIMIT
    - Narx allaqachon Entry zonasida           -> MARKET
    """

    market_threshold_pct: float = 0.15
    zone_broken_threshold_pct: float = 0.30


@dataclass(frozen=True, slots=True)
class MarketStructureConfig:
    """SMC — struktura tahlili (CryptoSpot3%, 2-qism)."""

    #: Swing tasdiqlash oynasi. `support_resistance.swing_lookback` dan
    #: ALOHIDA: zona qurish uchun ko'p, lekin mayda pivotlar foydali;
    #: struktura uchun esa kamroq va yiriklari kerak.
    swing_lookback: int = 5
    #: Yo'nalish e'lon qilish uchun minimal swing soni (2 cho'qqi + 2 chuqurlik)
    min_swings: int = 4
    #: Swing yetarli bo'lmaganda ZAXIRA o'lchov: oynadagi sof narx
    #: o'zgarishi shu foizdan katta bo'lsa yo'nalish e'lon qilinadi.
    #:
    #: NIMA UCHUN KERAK. Silliq, to'xtovsiz ko'tarilishda burilish
    #: nuqtalari UMUMAN bo'lmaydi — ya'ni HH/HL ketma-ketligi ham yo'q
    #: va struktura "aniq emas" deydi. Bu esa eng kuchli trendning
    #: o'zi. EMA bu holatni ushlab turardi; u olib tashlangach
    #: bo'shliq qoldi (58-bo'lim).
    #:
    #: Bu EMA emas: o'rtacha ham, 200 shamlik tarix ham talab
    #: qilinmaydi — faqat "narx oynaning boshidan balandmi".
    fallback_min_pct: float = 1.0


@dataclass(frozen=True, slots=True)
class LiquiditySweepConfig:
    """LIT — "yalab o'tib qaytish" naqshi (CryptoSpot3%, 3-qism)."""

    enabled: bool = True
    #: Naqsh shuncha oxirgi sham ichida qidiriladi
    lookback_bars: int = 30
    #: Narx daraja chekkasidan kamida shuncha foiz chuqur kirishi kerak.
    #: BOSHLANG'ICH qiymat — backtest bilan sozlanadi.
    min_sweep_pct: float = 0.3
    #: Qaytish shuncha sham ichida sodir bo'lishi kerak
    max_reclaim_bars: int = 3


@dataclass(frozen=True, slots=True)
class SessionOverlapConfig:
    """ICT Kill Zone — London/Nyu-York kesishuvi (CryptoSpot3%, 4-qism).

    Kripto 24/7 ishlaydi, ya'ni bu QAT'IY FILTR EMAS — faqat ball
    beruvchi qo'shimcha omil. Aniq soatlar backtest bilan tasdiqlanadi.
    """

    enabled: bool = True
    start_hour_utc: int = 13
    end_hour_utc: int = 16


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """3.2-band: asosiy klassik strategiya uchun standart timeframe to'plami."""

    timeframes: list[str] = field(
        default_factory=lambda: ["4h", "1d", "1w"]
    )
    #: Kirish timeframei. 15m dan 1h ga ko'chirildi — sabab
    #: `docs/ARXITEKTURA.md` 42-bo'limda: 15m da ATR narxning ~0.5% i
    #: bo'ladi, ya'ni support zonasigacha masofa ham shuncha. Stop esa
    #: kamida 1% bo'lishi kerak (3.3-band), shuning uchun darajalar
    #: tez-tez "Stop juda yaqin" deb rad etilardi. 1h da ATR ~1-2%,
    #: ya'ni tuzilma va risk qoidasi bir shkalaga tushadi.
    entry_timeframe: str = "4h"
    htf_confirmation: list[str] = field(
        default_factory=lambda: ["1d"]
    )
    #: Bozor Salomatligi kengligi (3.7-band, 2-omil) qaysi timeframeda
    #: o'lchanadi. Alohida e'lon qilinadi, chunki u `htf_confirmation`
    #: dan MUSTAQIL: tasdiq timeframelari qisqarganda ham kenglik kunlik
    #: o'lchovda qolishi kerak — soatlik kenglik kun bo'yi tebranib,
    #: indeksni ma'nosiz qilib qo'yardi.
    market_health_timeframe: str = "1w"
    candles_lookback: int = 500
    #: Yuqori timeframelar muvofiqligi signal uchun MAJBURIYmi (3.2-band).
    #:
    #: `False` — muvofiqlik ball ichida hisobga olinadi, lekin signalni
    #: to'xtatmaydi. Sabab `require_confirmation` bilan bir xil, faqat
    #: kuchliroq: kunlik EMA200 — 200 kunlik o'rtacha, ya'ni eng sekin
    #: kechikuvchi o'lchov. Uni majburiy qilish burilish nuqtasidagi har
    #: qanday kirishni to'sadi.
    require_htf_alignment: bool = False
    #: SMC strukturasi muvofiqligi signal uchun MAJBURIYmi.
    #:
    #: `False` (standart) — struktura faqat BALL BONUSI beradi. Metodika
    #: hujjatining o'z talabi ham shu: yangi omillar qat'iy filtr
    #: sifatida qo'shilmasin, chunki bu loyihada ko'p sonli "VA"
    #: filtri signal voronkasini allaqachon nolga tushirgan (44-bo'lim).
    #:
    #: `True` qilinsa — pasayish strukturasidagi (LH/LL) coin butunlay
    #: rad etiladi. Buni FAQAT backtest tasdiqlagandan keyin yoqing:
    #: voronkada `classic_ta:structure` qatori qancha nomzodni
    #: to'xtatayotganini ko'rsatadi.
    require_structure_alignment: bool = False
    #: Kelajakdagi pozitsion strategiya uchun zaxira — asosiy strategiya
    #: ishlatmaydi (u o'z timeframelarini `required_timeframes()` da e'lon qiladi).
    positional_timeframes: list[str] = field(
        default_factory=lambda: ["1d", "1w", "1M"]
    )
    entry_order: EntryOrderConfig = field(default_factory=EntryOrderConfig)
    support_resistance: SupportResistanceConfig = field(default_factory=SupportResistanceConfig)
    indicators: IndicatorConfig = field(default_factory=IndicatorConfig)
    market_structure: MarketStructureConfig = field(default_factory=lambda: MarketStructureConfig())
    liquidity_sweep: LiquiditySweepConfig = field(default_factory=lambda: LiquiditySweepConfig())
    session_overlap: SessionOverlapConfig = field(default_factory=lambda: SessionOverlapConfig())


# --------------------------------------------------------------------------- #
#  3.5 — Ball tizimi
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    support_resistance: float = 25
    trend: float = 20
    rsi: float = 15
    volume: float = 15
    macd: float = 10
    risk_reward: float = 15

    def total(self) -> float:
        return (
            self.support_resistance
            + self.trend
            + self.rsi
            + self.volume
            + self.macd
            + self.risk_reward
        )


@dataclass(frozen=True, slots=True)
class ScoreThresholds:
    #: YUQORI band chegarasi. 80 dan 70 ga tushirildi — O'LCHOV asosida.
    #:
    #: Salomatlik indeksining shifti bozor KENGLIGIGA bog'liq: kenglik
    #: omili 25 ball turadi, ya'ni kenglik 5% bo'lsa indeks 76 dan
    #: yuqoriga chiqa OLMAYDI (qolgan omillar mukammal bo'lsa ham).
    #: Jonli botda kenglik 5% edi va indeks 70-77 oralig'ida yurdi —
    #: ya'ni o'z shiftida.
    #:
    #: Natijada 80 lik chegara bir marta ham ishlamadi:
    #: `threshold_high_health` (50) hech qachon qo'llanilmadi va
    #: "moslashuvchi chegara" amalda doim 55 bo'lib qoldi.
    #:
    #: 70 qo'yilgan edi, lekin haftalik timeframega o'tgach indeks
    #: 69 ga tushdi — band yana bir ball bilan yopiq qoldi. Kuzatilgan
    #: oraliq: 69..77. 65 — pastki chetdan zaxira bilan.
    health_high_min: float = 65
    health_mid_min: float = 40
    #: Chegaralar O'LCHAB tanlangan — `scripts/kalibrlash.py` ga qarang.
    #: 70/80 qiymatlari 100 ballik shkalaga mo'ljallangan edi, lekin ball
    #: funksiyasi amalda 60 dan oshmaydi (omillar bir vaqtda to'liq bo'la
    #: olmaydi). Natijada birorta signal chiqmasdi.
    threshold_high_health: float = 50
    threshold_mid_health: float = 55
    #: PAST band chegarasi — Correction Entry rejimi uchun.
    #:
    #: Ilgari bu band `None` qaytarardi, ya'ni indeks 40 dan pastga
    #: tushganda tizim coinlarni UMUMAN tahlil qilmasdi. Bu esa
    #: strategiyaning o'z falsafasiga zid edi: past indeks — narxlar
    #: ARZONLASHGAN payt, ya'ni "arzon ol" uchun eng qulay lahza.
    #: Tizim aynan shunda ko'zini yumib, indeks qayta ko'tarilgach —
    #: narx allaqachon o'sgach — signal berardi. Ya'ni doim KECH.
    #:
    #: Endi bu band to'xtatmaydi, REJIMNI almashtiradi: faqat
    #: `correction_entry` ishlaydi va chegara qattiqroq bo'ladi —
    #: pasayishdagi kirish ko'proq dalil talab qiladi.
    threshold_low_health: float = 60


@dataclass(frozen=True, slots=True)
class ScoreBonuses:
    """Bazaviy 100 ball USTIGA qo'shiladigan bonus — faqat VAQT omili.

    NIMA UCHUN BONUS, VAZN EMAS. Bazaviy vaznlar (`ScoreWeights`)
    o'lchab tanlangan: `scripts.kalibrlash` 27 ta sozlamada eng yuqori
    ball 59.7 chiqargan va chegaralar (50/55) shu taqsimotdan olingan.
    Yangi omillarni vazn sifatida kiritish eski omillarni siqib,
    ballarni pastga tushirardi — ya'ni chegaralar yana erishib bo'lmas
    bo'lib qolardi (`docs/ARXITEKTURA.md`, 40- va 46-bo'limlar).

    Bonus esa faqat YUQORIGA suradi: topilmasa nol, topilsa qo'shimcha.
    Chegaralarni qayta kalibrlash shart emas.
    """

    #: ICT Kill Zone. Bu YAGONA bonus bo'lib qoldi: struktura, daraja
    #: turi va sweep endi mavjud omillar ICHIGA kiradi (`ScoreUplift`)
    #: — ular S/R va trend haqidagi DALIL, alohida omil emas. Sessiya
    #: oynasi esa ularning hech biriga tegishli emas: u kirish VAQTI
    #: haqida, tuzilma haqida emas.
    session_overlap: float = 5

    def total(self) -> float:
        return self.session_overlap


@dataclass(frozen=True, slots=True)
class ScoreUplift:
    """CryptoSpot3% dalillari mavjud omillarni QANCHA ko'tara oladi.

    ORALASHIB ISHLASH. Struktura, daraja turi va sweep — alohida
    omillar emas, ular MAVJUD omillar haqidagi qo'shimcha dalil:

      * yalab o'tib qaytilgan va Quasimodo turidagi zona — bu
        SIFATLIROQ S/R zonasi, ya'ni 25 ballik omilning o'zi;
      * HH/HL strukturasi va BOS — bu trendning o'zi, faqat EMA dan
        oldinroq ko'rinadigan ko'rinishi.

    Shuning uchun ular yonma-yon turmaydi, omil ichida qo'shiladi:

        yangi = eski + (1 - eski) * dalil * ulush

    Bu shakl IKKI XOSSANI kafolatlaydi:
      1. hech qachon PASAYTIRMAYDI (dalil yo'q -> eski qiymat qoladi);
      2. hech qachon 1 dan oshmaydi (shkala buzilmaydi).

    Ya'ni yangi bilim ballni faqat KO'TARADI — natijada u signal
    SONIGA ham ta'sir qiladi, nafaqat tartibiga.
    """

    #: Sweep va daraja turi S/R omilini qancha ko'tara oladi.
    #:
    #: Trend uchun ko'tarish YO'Q: EMA olib tashlangandan keyin
    #: struktura trend omilining TO'LIQ HUQUQLI qismiga aylandi
    #: (`TREND_ULUSHLARI`), ya'ni u endi "qo'shimcha dalil" emas.
    support_resistance: float = 0.5


@dataclass(frozen=True, slots=True)
class SetupRouteConfig:
    """Metodikaning TO'LIQ shartnomasi bajarildimi — BELGI.

    Bu DARVOZA EMAS. Darvoza bitta: ball chegarasi. Shartnoma esa
    "bu signal CryptoSpot3% naqshining to'liq ko'rinishi" degan
    yorliq — u "Nega bu signal?" ekranida ko'rsatiladi va o'lchovda
    sanaladi.

    Nima uchun alohida darvoza QILINMADI: ikkita parallel darvoza
    ikkita mustaqil qoidalar to'plami degani, ya'ni ikki barobar
    sozlash va ikki barobar xato. Dalillar omillar ichiga qo'shilgani
    uchun (`ScoreUplift`) to'liq shartnomali nomzod baribir yuqori
    ball oladi va chegaradan o'z kuchi bilan o'tadi.
    """

    enabled: bool = True
    #: Yalash shuncha shamdan yangi bo'lishi kerak. Eski sweep bugungi
    #: kirish uchun dalil emas.
    max_sweep_age_bars: int = 5
    #: BOS tasdig'i talab qilinsinmi (metodikaning 4-qadami)
    require_bos: bool = True
    #: Daraja turi shu ishonchdan past bo'lsa yo'l yopiq (oddiy daraja
    #: — 0.0, RBS/SBR — 0.6, OCL — 0.8, Qm/OB — 1.0)
    min_level_confidence: float = 0.6


@dataclass(frozen=True, slots=True)
class QualityGateConfig:
    """Kirishga DALIL ruxsat bersin, ball esa faqat tartiblasin.

    HOZIRGI MEXANIZM VA UNING KAMCHILIGI. Yagona darvoza — ball
    chegarasi. Ball esa nomzodlarni bir-biriga NISBATAN o'lchaydi:
    u "eng yaxshisi qaysi" deydi, "shu yetarlimi" demaydi. Natijada
    tizim uyumning eng yuqorisini oladi — uyumning O'ZI yomon
    bo'lsa ham.

    Bu 2026-09-02 dagi o'lchov bilan mos: to'rtta mustaqil kirish
    filtri sinaldi, signal soni 610 dan 884 gacha o'zgardi,
    win-rate esa 36.9-39.1% bo'lib qoldi. Filtrlar uyumga KIM
    kirishini o'zgartirdi, uyum baribir tartiblanib eng yuqorisi
    olinaverdi.

    Yoqilganda kirish sharti almashadi:

        eski:  bazaviy ball >= chegara
        yangi: CryptoSpot3% shartnomasi bajarildi
               VA bazaviy ball xavfsizlik polidan yuqori

    Shartnoma (`setup_route.py`) allaqachon hisoblanadi va
    `SignalCandidate.setup_qualified` da yotibdi — bugungacha u
    faqat YORLIQ edi, qarorga ta'siri yo'q edi. Ya'ni bu yerda
    yangi mantiq yozilmaydi, mavjud dalilga OVOZ beriladi.

    STANDART HOLATDA O'CHIQ: bu gipoteza, fakt emas. Signal soni
    keskin kamayishi kutiladi — u kamayish sifat oshgani bilan
    to'lanadimi yoki yo'qmi, faqat backtest aytadi.
    """

    enabled: bool = False
    #: Shartnoma MAJBURIY bo'lsinmi. `False` bo'lsa faqat pol
    #: ishlaydi — ya'ni chegara pasaygan eski mexanizm.
    require_setup_contract: bool = True
    #: XAVFSIZLIK poli, sifat chegarasi emas. "Tuzilma mukammal,
    #: lekin qolgan hammasi yomon" holatini kesadi.
    min_base_score: float = 35.0


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    bonuses: ScoreBonuses = field(default_factory=ScoreBonuses)
    uplift: ScoreUplift = field(default_factory=ScoreUplift)
    setup_route: SetupRouteConfig = field(default_factory=SetupRouteConfig)
    quality_gate: QualityGateConfig = field(default_factory=QualityGateConfig)
    thresholds: ScoreThresholds = field(default_factory=ScoreThresholds)


# --------------------------------------------------------------------------- #
#  3.3 — Universal savdo qoidalari
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class TradeRulesConfig:
    """3.3-band: universal risk qoidasi.

    ASOSIY SHART — NISBAT, masofa emas. Stop 1% dan 5% gacha erkin
    joylashishi mumkin (S/R zonasi qayerda ekaniga qarab), lekin
    TP/Stop nisbati kamida `min_risk_reward` bo'lishi SHART.

    Nima uchun shunday: qat'iy 1% chegara narxni majburlab siqardi —
    aynan 1% masofada mos S/R zonasi bo'ladigan holat kam uchraydi,
    natijada signal deyarli chiqmasdi. Nisbat esa har qanday masofada
    ma'noga ega.

    Stop kattalashsa xavf oshmaydi: pozitsiya hajmi
    (xavf puli / Stop%) avtomatik kichrayadi — 5.1-band.
    """

    #: Stop shu masofadan yaqin bo'lsa — bozor shovqini uni yeb qo'yadi
    #: Stop masofasi = ATR × shu ko'paytma.
    #:
    #: Qat'iy foiz BARCHA coinlarga bir xil qo'llanardi, holbuki Stopning
    #: maqsadi bozor shovqinidan himoya — shovqin esa ATR bilan
    #: o'lchanadi. 1% stop BTC uchun ~1.2 ATR (mantiqiy), volatil
    #: altcoin uchun ~0.3 ATR (shovqin yeb qo'yadi), barqaror coin
    #: uchun ~3 ATR (keraksiz keng, yaxshi setuplarni rad etadi).
    stop_atr_mult: float = 1.75
    #: FOIZ ORALIQLARI MAJBURIYMI.
    #:
    #: Loyiha egasining qarori (2026-09-02): "TP STOP FOIZLARI
    #: MAJBURIY EMAS — RISK 1/3". Ya'ni bog'lovchi shart bitta —
    #: `min_risk_reward`. Quyidagi foizlar esa MASOFA haqida, nisbat
    #: haqida emas, va ular signalni to'sib qo'yishi mumkin:
    #: haqiqiy support 5% dan uzoqroqda, haqiqiy resistance esa 3%
    #: dan yaqinroqda bo'lishi butunlay normal.
    #:
    #: `False` bo'lganda oraliqlar SAQLANADI, lekin faqat izoh
    #: sifatida — signal ular tufayli rad etilmaydi.
    #:
    #: DIQQAT: `min_stop_distance_pct` himoya vazifasini ham
    #: bajarardi — juda tor Stop bozor shovqinida bekorga ishlaydi.
    #: Bu himoya endi `stop_atr_mult` ga qoladi: Stop ATR ning
    #: ko'paytmasi bilan qo'yiladi, ya'ni shovqin o'z birligida
    #: o'lchanadi. Bu qat'iy foizdan to'g'riroq, lekin o'lchanmagan.
    enforce_distance_bands: bool = False
    #: Ikkinchi darajali xavfsizlik chegarasi (faqat
    #: `enforce_distance_bands` yoqilganda ishlaydi).
    min_stop_distance_pct: float = 1.0
    #: Stop shu masofadan uzoq bo'lsa — pozitsiya juda kichrayib ketadi
    max_stop_distance_pct: float = 5.0
    #: TP Stop bilan bog'liq: `min_risk_reward` orqali hisoblanadi
    min_tp_distance_pct: float = 3.0
    max_tp_distance_pct: float = 20.0
    #: NOMZODGA MUDDAT. Signal faol bo'lgach shu soat ichida na
    #: yakuniy nishonga, na Stopga bormasa — bozor narxida yopiladi.
    #:
    #: NIMA UCHUN. Sanoat naqshida (QuantConnect LEAN) Alpha
    #: `Insight` chiqaradi: yo'nalish, ISHONCH va MUDDAT. Bizda
    #: muddat umuman yo'q edi: chiqish faqat TP yoki Stop, ya'ni
    #: "bozor qachon bo'lmasin, bir kun bularning biriga boradi"
    #: degan jimgina taxmin.
    #:
    #: Oqibati o'lchangan: o'rtacha ushlash 45.2 soat, bozor esa
    #: ikki yilda +31.5% o'sgan (natija #6). Ya'ni kapital foydasiz
    #: pozitsiyalarda BAND turadi va o'sha vaqtda boshqa hech narsa
    #: qila olmaydi.
    #:
    #: 0 — muddat yo'q (hozirgi xatti-harakat). Bu GIPOTEZA:
    #: muddat foydasiz savdolarni erta yopadimi yoki kuchayishga
    #: ulgurmagan yaxshi savdolarni kesib qo'yadimi — o'lchanmagan.
    max_holding_hours: float = 0.0
    #: Nechtagacha TP qurilsin — 1, 2 yoki 3.
    #:
    #: TP SONI QAT'IY EMAS. Bu yerdagi son — YUQORI CHEGARA, majburiy
    #: miqdor emas: bozorda nechta haqiqiy nishon bo'lsa, shuncha TP
    #: quriladi. Toza ko'tarilishda ustda bitta ham qarshilik
    #: bo'lmasligi mumkin (u holda bitta o'lchangan TP), keng
    #: diapazonda esa uchtasi bo'lishi mumkin.
    max_take_profits: int = 2
    #: QAT'IY SHART: TP2/Stop nisbati shundan past bo'lsa signal yo'q
    min_risk_reward: float = 3.0
    #: TP1 uchun eng past nisbat. TP1 da pozitsiyaning bir qismi
    #: yopiladi — agar u 1:1 dan past bo'lsa, o'sha qism o'rtacha
    #: zarar keltiradi.
    #:
    #: 2.0 IKKI OYNADA O'LCHANDI (natija #8 va #9): PF bo'yicha
    #: 1.5 dan yaxshi, hech bir o'lchov bo'yicha yomon emas.
    tp1_min_risk_reward: float = 2.0
    #: Shu nisbat TUZILMAVIY TP1 ga ham qo'llanilsinmi.
    #:
    #: MUAMMO (natija #7). `tp1_min_risk_reward` faqat "qarshilik
    #: topilmadi" tarmog'ida ishlardi. Zona topilganda TP1 o'sha
    #: zonaga qo'yilardi va hech qanday pol tekshirilmasdi.
    #:
    #: Foiz oraliqlari majburiy bo'lganda buni `min_tp_distance_pct`
    #: (3%) yashirib turardi. Oraliqlar o'chirilgach TP1 eng yaqin
    #: qarshilikka tushdi — u +0.5% bo'lishi mumkin — va savdo
    #: shunday ko'rinish oldi:
    #:
    #:     TP1 +0.5% da   -> yarmi sotiladi   -> +0.25%
    #:     Stop breakeven -> qolgani nolda    ->  0.00%
    #:     komissiya                          -> -0.30%
    #:                                           -------
    #:                                            -0.05%
    #:
    #: Ya'ni "g'alaba" deb yozilgan savdo amalda nolga yaqin, Stop
    #: esa keng qoladi: kichkina yutuqlar, katta zararlar. Profit
    #: factor 0.64 dan 0.30 ga tushdi.
    #:
    #: Yoqilganda nisbat poliga yetmagan zona O'TKAZIB YUBORILADI
    #: va keyingisi qidiriladi. Hech biri yetmasa o'lchangan TP ga
    #: qaytiladi — u allaqachon shu nisbatga bo'ysunadi.
    #:
    #: Bu FOIZ emas, NISBAT poli: loyiha egasining "TP STOP FOIZLARI
    #: MAJBURIY EMAS — RISK 1/3" qoidasiga zid emas.
    #:
    #: YOQILGAN — ikkita kesishmaydigan oynada o'lchandi:
    #:
    #:                              PF, baza   PF, pol bilan
    #:     oyna A (2024-09..2026-09)   0.30         0.82
    #:     oyna B (2022-09..2024-09)   0.34         1.01
    #:
    #: Nazorat variantlari ham ikkalasida bir xil javob berdi.
    #: Tizim shunda ham tayanchdan yomon — bu bayroq bitta
    #: teshikni yopdi, tizimni foydali qilmadi (natija #9).
    enforce_tp1_ratio: bool = True
    allow_measured_tp: bool = True
    #: TP2 TUZILMADAN olinsinmi (ikkinchi resistance zonasi).
    #:
    #: HOZIRCHA O'CHIRILGAN — backtest tugagach hal qilinadi.
    #:
    #: MUAMMO (2026-09-02 backtesti). TP1 haqiqiy resistance
    #: zonasidan olinadi, TP2 esa FORMULADAN: stop masofasi x
    #: `min_risk_reward`. Ya'ni TP2 bozorda nima borligiga umuman
    #: qaramaydi — stop keng bo'lsa u uzoqqa uchib ketadi, o'sha
    #: yerda qarshilik bormi yoki yo'qmi, ahamiyatsiz.
    #:
    #: O'LCHANGAN OQIBAT: TP2 gacha savdolarning atigi 29.9% i
    #: yetadi, stop esa to'liq ishlaydi. 1:1.5 nisbatda foydali
    #: bo'lish uchun 40% kerak edi. Ana shu 10 punktlik farq
    #: butun tizimni zararga olib boradi (-0.43% har savdoda).
    #:
    #: YECHIM SINALADI, DARHOL QO'LLANMAYDI: tuzilmaviy TP2 nisbatni
    #: PASAYTIRADI, lekin yetib borish ehtimolini oshiradi. Qaysi
    #: tomon og'irroq — buni faqat backtest aytadi.
    tp2_from_structure: bool = False
    #: Tuzilmaviy TP2 uchun eng past nisbat.
    #:
    #: Formuladagidan PAST bo'lishi shart, aks holda tuzilmaviy TP2
    #: hech qachon o'tmaydi va bayroq hech narsani o'zgartirmaydi —
    #: e'lon qilingan, lekin ulanmagan sozlama bo'lib qolardi.
    #: 1:1 dan past bo'lsa esa savdoning o'zi ma'nosiz.
    tp2_structural_min_rr: float = 1.0
    #: KECH KIRISH ogohlantirishi: narx kirish nuqtasidan shu foizdan
    #: ko'p uzoqlashgan bo'lsa, hali kirmagan foydalanuvchiga
    #: "xavf kattalashdi, kirish tavsiya etilmaydi" deb aytiladi.
    #:
    #: IKKALA TOMONGA ham: yuqoriga ketgan bo'lsa TP gacha masofa
    #: qisqargan va Stop uzoqlashgan (nisbat buzilgan); pastga ketgan
    #: bo'lsa Stop yaqinlashgan. Ikkalasida ham kirish signal
    #: berilgan paytdagidan yomonroq.
    #:
    #: Bu TO'SIQ EMAS — ogohlantirish. Qaror foydalanuvchiniki.
    late_entry_warn_pct: float = 1.2


# --------------------------------------------------------------------------- #
#  4 — Risk Engine
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
class BtcFilterConfig:
    reference_symbol: str = "BTC"
    max_drop_pct_24h: float = -5.0
    #: Qaysi timeframedagi shamlardan 24 soatlik o'zgarish hisoblanadi.
    #:
    #: Kirish timeframei bilan mos bo'lishi kerak — aks holda bu seriya
    #: umuman yuklanmaydi. "1h" qolib ketgan edi va kirish 4h ga
    #: o'tgach filtr jimgina "BTC holati noma'lum" holatiga tushardi
    #: (`test_timeframe_izchilligi` shu sinfni qulflaydi).
    timeframe: str = "4h"


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
class RotationConfig:
    min_score_gap: float = 30
    cooldown_minutes: int = 120


@dataclass(frozen=True, slots=True)
class WeakeningConfig:
    score_drop_points: float = 25


@dataclass(frozen=True, slots=True)
class RiskEngineConfig:
    daily_loss_limit_pct: float = 3.0
    weekly_loss_limit_pct: float = 8.0
    max_open_signals: int = 5
    max_open_signals_by_health: OpenSignalLimits = field(default_factory=OpenSignalLimits)
    correlation_groups: list[CorrelationGroup] = field(default_factory=list)
    max_signals_per_correlation_group: int = 1
    btc_filter: BtcFilterConfig = field(default_factory=BtcFilterConfig)
    kill_switch: KillSwitchConfig = field(default_factory=KillSwitchConfig)
    consecutive_loss: ConsecutiveLossConfig = field(default_factory=ConsecutiveLossConfig)
    friday_filter: FridayFilterConfig = field(default_factory=FridayFilterConfig)
    rotation: RotationConfig = field(default_factory=RotationConfig)
    weakening: WeakeningConfig = field(default_factory=WeakeningConfig)

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
class MarketHealthWeights:
    """Indeks omillarining vazni (jami 100).

    BTC DOMINANCE 20 DAN 5 GA TUSHIRILDI. Tajribali treyderlar bilan
    maslahat natijasi: dominance foydali, lekin ikkinchi darajali
    ko'rsatkich — ko'pchilik uchun qaror mezoni emas. Uning o'rniga
    ASOSIY omil sifatida halol ro'yxatning STRUKTURA holati
    (`market_structure.py` dan: nechta coin HH/HL ko'tarilishda) keldi.
    Bu — real narx harakatiga asoslangan o'lchov.
    """

    #: ASOSIY OMIL: SMC strukturasi bo'yicha ko'tarilishdagi coinlar ulushi.
    #:
    #: Vazni 30 dan 45 ga oshdi: EMA olib tashlangach eski
    #: `halal_trend_breadth` (15) o'z ma'nosini yo'qotdi — u ham aynan
    #: SHU savolni ("nechta coin ko'tarilishda") o'lchardi, faqat
    #: kechikuvchi vosita bilan. Ikkita bir xil omil o'rniga bitta.
    halal_structure_breadth: float = 45
    volatility_regime: float = 15
    aggregate_user_capacity: float = 20
    signal_saturation: float = 10
    #: Kamaytirilgan: qo'shimcha kontekst, hal qiluvchi omil emas
    btc_dominance_stability: float = 5
    #: QT (AMDX) davri — BOSHLANG'ICH vazn, backtest bilan tasdiqlanadi
    quarterly_phase: float = 5

    def total(self) -> float:
        return (
            self.halal_structure_breadth
            + self.volatility_regime
            + self.aggregate_user_capacity
            + self.signal_saturation
            + self.btc_dominance_stability
            + self.quarterly_phase
        )


@dataclass(frozen=True, slots=True)
class BtcDominanceConfig:
    stable_change_pct: float = 0.5
    sharp_change_pct: float = 2.0


@dataclass(frozen=True, slots=True)
class MarketHealthConfig:
    #: 3-omil to'liq ball oladigan O'RTACHA ADX (bitta coin emas, 30 ta
    #: coinning o'rtachasi — sabab `docs/ARXITEKTURA.md`, 32-bo'lim)
    strong_trend_adx: float = 30.0
    weights: MarketHealthWeights = field(default_factory=MarketHealthWeights)
    recompute_on_candle_close: bool = True
    daily_preview_utc_hour: int = 0
    btc_dominance: BtcDominanceConfig = field(default_factory=BtcDominanceConfig)


# --------------------------------------------------------------------------- #
#  5 — Pozitsiya hajmi
# --------------------------------------------------------------------------- #


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
class ClassicTaConfig:
    enabled: bool = True
    #: Mean reversion uchun eng kam TP2/Stop nisbati.
    #:
    #: Global 1:3 qiymati trend/breakout strategiyalariga xos. Mean
    #: reversion tabiiy ravishda diapazon o'rtasiga yoki resistance'ga
    #: qaytganda yopiladi — bu odatda 1:1..1:1.5 beradi. 1:3 talab qilish
    #: bu strategiya uchun deyarli hech qachon bajarilmaydigan shart edi.
    #:
    #: Qiymat STRATEGIYA darajasida: boshqa turdagi strategiya qo'shilsa,
    #: u o'zining tabiiy nisbatini saqlaydi.
    min_risk_reward: float = 1.5


@dataclass(frozen=True, slots=True)
class ScalpWeights:
    """3.9-band strategiyasining ball vaznlari (jami 100).

    Asosiy strategiyanikidan farq qiladi: bu yerda S/R zonasi yo'q, hajm
    sakrashi va yo'nalish aniqligi hal qiluvchi omillar.
    """

    volume_surge: float = 35
    range_quality: float = 25
    direction_clarity: float = 25
    risk_reward: float = 15

    def total(self) -> float:
        return (
            self.volume_surge
            + self.range_quality
            + self.direction_clarity
            + self.risk_reward
        )


@dataclass(frozen=True, slots=True)
class OpeningRangeScalpConfig:
    enabled: bool = True
    session_open_utc: str = "00:00"
    range_minutes: int = 15
    timeframe: str = "15m"
    volume_surge_mult: float = 2.0
    volume_ma_period: int = 20
    min_move_pct: float = 1.0
    max_move_pct: float = 2.0
    #: Ochilishdan keyin signal oynasi necha daqiqa ochiq turadi.
    #:
    #: 45 daqiqadan bir kunga (1440) uzaytirildi. Sabab: 45 daqiqa
    #: kunning 3% i, ya'ni oyna vaqtning 97% ida yopiq turardi va
    #: dashboardda "Skalping oynasi yopiq" yozuvi hamma narsadan ko'p
    #: chiqardi (5114 marta).
    #:
    #: Diqqat: kech kirish yomonroq kirish. Diapazon kun boshida
    #: qurilgani uchun kunning oxirida buzilish "eskirgan" diapazonga
    #: nisbatan o'lchanadi. Buni ball qoplaydi — buzilish kuchi va hajm
    #: baribir talab qilinadi — lekin bu almashuv ONGLI ravishda
    #: qabul qilingan.
    signal_window_minutes: int = 1440
    min_range_pct: float = 0.15
    max_range_pct: float = 1.2
    daily_risk_share_pct: float = 30.0
    weights: ScalpWeights = field(default_factory=ScalpWeights)

    @property
    def session_open_time(self) -> time:
        return parse_hhmm(self.session_open_utc)


@dataclass(frozen=True, slots=True)
class CorrectionEntryConfig:
    """Bozor pasayganda ishlaydigan kirish usuli.

    NIMA UCHUN KERAK. Bozor Salomatligi past bo'lgan payt — narxlar
    ARZONLASHGAN payt, ya'ni "arzon ol" strategiyasi uchun eng qulay
    lahza. Eski tizim esa aynan shunda qidirishni to'xtatardi va
    indeks qayta ko'tarilganda — narx allaqachon o'sib bo'lgach —
    signal berardi. Ya'ni doim KECH kirardi.

    Bu strategiya o'sha bo'shliqni to'ldiradi: pasayishda ham qaraydi,
    lekin FAQAT tuzilma ruxsat bergan joyda.

    QAT'IY DARVOZA: yuqori timeframe KO'TARILISHDA bo'lishi shart.
    Tushayotgan bozorda "arzon" degan narsa yo'q — narx yana ham
    arzonlashaveradi. Spot xaridida bu eng qimmat xato.
    """

    enabled: bool = True
    #: Kirish nuqtasi qidiriladigan timeframe (zona shu yerda topiladi)
    zone_timeframe: str = "4h"
    #: Aniq nuqtani tasdiqlaydigan PASTKI timeframe
    confirm_timeframe: str = "15m"
    #: Yo'nalish darvozasi shu timeframedan olinadi
    trend_timeframe: str = "1d"
    #: Impuls qidiriladigan oyna (sham soni)
    impulse_lookback: int = 60
    #: Fibonacci korreksiya oralig'i — "oltin zona"
    fib_ratios: list[float] = field(default_factory=lambda: [0.382, 0.618])
    #: Order block deb hisoblash uchun keyingi harakat shu foizdan katta
    ob_min_move_pct: float = 1.0
    #: FVG shu foizdan tor bo'lsa e'tiborga olinmaydi
    fvg_min_gap_pct: float = 0.1
    #: KAMIDA shuncha TURLI manba bir joyga tushishi shart.
    #:
    #: Nima uchun 2: beshta usuldan "eng mosini" tanlash har doim
    #: qandaydir usul topiladi degani — bu tarixga moslashib qolish
    #: (overfitting). Ikki mustaqil manbaning bir joyda uchrashuvi
    #: esa tasodif bo'lish ehtimoli ancha past.
    min_confluence: int = 2
    #: Pastki TF tasdig'i shuncha oxirgi sham ichida qidiriladi
    confirm_lookback: int = 20
    #: Stop zona chekkasidan shuncha foiz pastda (shovqin uchun zaxira)
    stop_buffer_pct: float = 0.15
    #: Eng kam TP2/Stop nisbati. BOSHLANG'ICH qiymat — backtest bilan
    #: aniqlanadi (metodika hujjati "taxminan 1:2" deydi, lekin uni
    #: raqam bilan tasdiqlash shart).
    min_risk_reward: float = 2.0
    #: RSI shu qiymatdan pastga tushib QAYTGAN bo'lsa — qo'shimcha dalil
    rsi_reversal_max: float = 45.0


@dataclass(frozen=True, slots=True)
class StrategiesConfig:
    classic_ta: ClassicTaConfig = field(default_factory=ClassicTaConfig)
    correction_entry: CorrectionEntryConfig = field(
        default_factory=CorrectionEntryConfig
    )
    opening_range_scalp: OpeningRangeScalpConfig = field(default_factory=OpeningRangeScalpConfig)


# --------------------------------------------------------------------------- #
#  5.4 — Shaxsiy portfel
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
class PostmortemConfig:
    """3.8-band: o'z-o'zini tekshirish sozlamalari."""

    #: Naqsh e'lon qilish uchun minimal namuna — halollik chegarasi
    min_sample_size: int = 12
    #: Naqsh "kuchli" bo'lishi uchun natijalar farqi (foiz punkti)
    min_effect_pct: float = 15.0
    lookback_days: int = 30
    report_weekday: int = 0
    report_hour_utc: int = 6
    false_signal_window_minutes: int = 60


# --------------------------------------------------------------------------- #
#  1.2 — Obuna
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
class PipelineEventsConfig:
    """Jonli tahlil monitori — "oshxona ko'rinishi" (59-bo'lim)."""

    enabled: bool = True
    #: Yozuvlar shuncha soatdan keyin tozalanadi.
    #:
    #: Bu JONLI ko'rinish, doimiy arxiv emas: doimiy statistika
    #: `risk_blocks` da va Signal Xotirasi modulida bor. Tozalash
    #: bo'lmasa jadval cheksiz o'sardi — har sikl har coin uchun
    #: 9-11 qator, ya'ni kuniga o'n minglab.
    retention_hours: int = 6


@dataclass(frozen=True, slots=True)
class MonitoringConfig:
    """Kuzatuv vositalari — savdo qaroriga ta'sir qilmaydi."""

    pipeline_events: PipelineEventsConfig = field(default_factory=PipelineEventsConfig)


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


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Butun tizimning yagona konfiguratsiya obyekti."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    #: Sinov davri — BIZGA tegishli omillar va tormozlar vaqtincha chetda
    sinov: SinovDavriConfig = field(default_factory=SinovDavriConfig)
    halal_screening: HalalScreeningConfig = field(default_factory=HalalScreeningConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    trade_rules: TradeRulesConfig = field(default_factory=TradeRulesConfig)
    risk_engine: RiskEngineConfig = field(default_factory=RiskEngineConfig)
    market_health: MarketHealthConfig = field(default_factory=MarketHealthConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    postmortem: PostmortemConfig = field(default_factory=PostmortemConfig)
    position_sizing: PositionSizingConfig = field(default_factory=PositionSizingConfig)
    strategies: StrategiesConfig = field(default_factory=StrategiesConfig)
    subscriptions: SubscriptionsConfig = field(default_factory=SubscriptionsConfig)
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
