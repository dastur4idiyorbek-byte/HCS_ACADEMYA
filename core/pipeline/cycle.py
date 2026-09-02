"""15-bosqich: avtomatik signal sikli — barcha modullarni bog'laydi.

Zanjir:
    Halol ro'yxat  ->  strategiyalar (parallel)  ->  ball va reyting
                  ->  chegara (Bozor Salomatligiga qarab)
                  ->  Risk Engine (majburiy)  ->  signal

Har bir bosqichda rad etilganlar sababi bilan qayd etiladi — 3.7-banddagi
"tizim nega sokin?" savoliga to'liq javob shu yerdan chiqadi.

MUHIM: bu modul tarmoqqa ham, bazaga ham murojaat qilmaydi. U tayyor
`CycleInput` ni oladi va `CycleResult` qaytaradi. Shu sababli butun zanjir
backtestda o'zgarishsiz ishlaydi (6.3-band).
"""

from __future__ import annotations

from core.analysis.scoring import Scorer
from core.analysis.strategies import Strategy, StrategyInput
from core.config.schema import AppConfig
from core.domain.enums import MarketRegime, SignalSource
from core.pipeline.context import CycleInput, CycleResult, RejectedCandidate
from core.risk_engine import RiskContext, RiskEngine
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


class SignalCycle:
    """Bir marta ishga tushganda barcha halol coinlarni ko'rib chiqadi."""

    def __init__(
        self,
        config: AppConfig,
        strategies: list[Strategy],
        risk_engine: RiskEngine | None = None,
        scorer: Scorer | None = None,
    ) -> None:
        self._config = config
        self._strategies = strategies
        self._risk_engine = risk_engine or RiskEngine(config)
        self._scorer = scorer or Scorer(config)

    #: Korreksiya rejimida FAQAT shu manba ishlaydi.
    #:
    #: Qolgan strategiyalar pasayish uchun mo'ljallanmagan: ular
    #: S/R zonasi yoki ochilish diapazoniga tayanadi va past indeksda
    #: ularning taxminlari ishlamaydi.
    KORREKSIYA_MANBALARI = frozenset({SignalSource.CORRECTION_ENTRY})

    def _for_regime(self, regime: MarketRegime | None) -> list[Strategy]:
        """Rejimga mos strategiyalar.

        Odatiy rejimda HAMMASI ishlaydi — `correction_entry` ham,
        chunki korreksiya kirishi o'rta bandda ham to'g'ri bo'lishi
        mumkin. Korreksiya rejimida esa faqat o'sha bitta strategiya:
        boshqalarning taxminlari past indeksda ishlamaydi.
        """
        if regime is not MarketRegime.CORRECTION:
            return list(self._strategies)
        return [
            s
            for s in self._strategies
            if getattr(s, "name", "") == SignalSource.CORRECTION_ENTRY.value
        ]

    def run(self, data: CycleInput) -> CycleResult:
        """Siklni bir marta bajaradi."""
        rad_etilganlar: list[RejectedCandidate] = []

        # 1) Chegara — Bozor Salomatligiga qarab (3.5-band)
        salomatlik_qiymati = data.market_health.value if data.market_health else None
        chegara = self._risk_engine.score_threshold(salomatlik_qiymati)

        if chegara is None:
            # Indeks HISOBLANMAGAN — bu yagona to'xtash sababi.
            # Noaniqlikda signal berilmaydi (0.3-band).
            logger.info("Sikl to'xtatildi: Bozor Salomatligi hisoblanmagan")
            return CycleResult(
                emitted=[],
                rejected=[
                    RejectedCandidate(
                        "*", "market_health", "Bozor Salomatligi hisoblanmagan"
                    )
                ],
                threshold=None,
                market_health=data.market_health,
                analyzed_count=0,
            )

        # 1a) REJIM — indeks QAYSI KIRISH USULI ishlashini belgilaydi.
        #
        # Ilgari past indeks siklni butunlay to'xtatardi. Bu
        # strategiyaning falsafasiga zid edi: past indeks aynan
        # narxlar ARZONLASHGAN payt. Endi u rejimni almashtiradi.
        rejim = self._risk_engine.market_regime(salomatlik_qiymati)
        faol_strategiyalar = self._for_regime(rejim)
        if not faol_strategiyalar:
            sabab = (
                f"Bozor Salomatligi past ({salomatlik_qiymati:.0f}/100), lekin "
                "korreksiya strategiyasi o'chirilgan"
            )
            logger.info("Sikl to'xtatildi: %s", sabab)
            return CycleResult(
                emitted=[],
                rejected=[RejectedCandidate("*", "market_health", sabab)],
                threshold=chegara,
                market_health=data.market_health,
                analyzed_count=0,
            )
        if rejim is MarketRegime.CORRECTION:
            logger.info(
                "Korreksiya rejimi (indeks %.0f): %s",
                salomatlik_qiymati or 0,
                ", ".join(s.name for s in faol_strategiyalar),
            )

        # 2) Strategiyalarni har bir coinga qo'llash
        nomzodlar = []
        tafsilotlar = {}
        for coin in data.symbols:
            # Kirish BITTA COIN uchun bir marta quriladi va barcha
            # strategiyalarga beriladi. Shu sababdan struktura kabi
            # faktlar bir marta hisoblanadi — ikki strategiya bir xil
            # sham qatori haqida boshqa-boshqa javob bera olmaydi.
            kirish = StrategyInput(
                symbol=coin.symbol,
                now=data.now,
                halal_verdict=coin.halal_verdict,
                candles=coin.candles,
                market_health=data.market_health,
                structure_config=self._config.analysis.market_structure,
            )
            for strategiya in faol_strategiyalar:
                nomzod = self._analyze(strategiya, kirish, rad_etilganlar)
                if nomzod is not None:
                    nomzodlar.append(nomzod)
                    tafsilotlar[nomzod.symbol] = nomzod.breakdown

        # 3) Reytinglash va chegara
        reyting = self._scorer.rank(nomzodlar, chegara)
        otganlar = self._scorer.passed(reyting)

        darvoza = self._config.scoring.quality_gate
        for element in reyting:
            if element.admitted:
                continue
            # Bosqich kodi Scorer'dan keladi — u qaysi shart
            # to'xtatganini biladi. Ilgari hammasi "threshold" deb
            # yozilardi va sifat darvozasi yoqilganda dashboard
            # "ball past" deb noto'g'ri sabab ko'rsatardi.
            rad_etilganlar.append(
                RejectedCandidate(
                    symbol=element.candidate.symbol,
                    stage=element.rejection or "threshold",
                    detail=self._rad_izohi(element, chegara, darvoza),
                    score=element.score,
                )
            )

        # 4) Risk Engine — MAJBURIY qatlam (4-bo'lim)
        chiqarilganlar = []
        ochiq_signallar = list(data.open_signals)

        for nomzod in otganlar:
            kontekst = self._risk_context(data, nomzod.symbol, ochiq_signallar)
            qaror = self._risk_engine.evaluate(nomzod, kontekst)

            if not qaror.allowed:
                # Bosqich nomiga QAYSI qoida to'xtatgani qo'shiladi.
                # Ilgari hammasi bitta "risk_engine" qatoriga yig'ilardi:
                # dashboard "Risk Engine to'xtatdi — 103 marta" derdi va
                # 13 ta qoidadan qaysi biri ekanini aytmasdi. Sababi
                # ko'rinmagan to'siqni tuzatib ham bo'lmaydi (3.7-band).
                rad_etilganlar.append(
                    RejectedCandidate(
                        symbol=nomzod.symbol,
                        stage=f"risk_engine:{qaror.reasons[0].value}"
                        if qaror.reasons
                        else "risk_engine",
                        detail="; ".join(qaror.details),
                        score=nomzod.score,
                    )
                )
                continue

            chiqarilganlar.append(nomzod)
            # Yangi signal keyingi nomzodlar uchun "ochiq" hisoblanadi —
            # aks holda korrelyatsiya va limit qoidalari bir siklda
            # bir necha marta buzilardi.
            ochiq_signallar.append(self._as_open_signal(nomzod, data))

        natija = CycleResult(
            emitted=chiqarilganlar,
            rejected=rad_etilganlar,
            threshold=chegara,
            market_health=data.market_health,
            analyzed_count=len(data.symbols),
            breakdowns=tafsilotlar,
        )
        logger.info(natija.summary())
        return natija

    # ------------------------------------------------------------------ #

    def _analyze(
        self,
        strategy: Strategy,
        kirish: StrategyInput,
        rejected: list[RejectedCandidate],
    ):  # noqa: ANN202
        """Bitta strategiyani tayyor kirishga qo'llaydi.

        Kirish TASHQARIDA quriladi — bitta coin uchun bir marta. Shu
        sababdan fakt qatlami (struktura) barcha strategiyalar uchun
        umumiy bo'ladi.

        0.3-band: strategiyaning nosozligi butun siklni to'xtatmaydi.
        """
        try:
            nomzod = strategy.analyze(kirish)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Strategiya xato berdi: %s / %s", strategy.name, kirish.symbol
            )
            rejected.append(
                RejectedCandidate(
                    kirish.symbol, f"{strategy.name}:error", "Strategiya ichki xatosi"
                )
            )
            return None

        if nomzod is None:
            sabab = getattr(strategy, "last_rejection", None)
            rejected.append(
                RejectedCandidate(
                    symbol=kirish.symbol,
                    stage=f"{strategy.name}:{sabab.stage if sabab else 'no_setup'}",
                    detail=sabab.detail if sabab else "Shart bajarilmadi",
                )
            )
        return nomzod

    @staticmethod
    def _rad_izohi(element, chegara: float | None, darvoza) -> str:  # noqa: ANN001
        """Rad etish sababini odam o'qiydigan qilib yozadi."""
        if element.rejection == "setup_contract":
            return (
                "CryptoSpot3% shartnomasi to'liq emas — kirish uchun "
                "yo'nalish, yalash va daraja turi birgalikda talab qilinadi"
            )
        if element.rejection == "score_floor":
            return (
                f"Ball {element.base_score:.0f} < xavfsizlik poli "
                f"{darvoza.min_base_score:.0f}"
            )
        if chegara is None:
            return "Bozor Salomatligi past — chegara yopiq"
        return f"Ball {element.base_score:.0f} < chegara {chegara:.0f}"

    def _risk_context(
        self,
        data: CycleInput,
        symbol: str,
        open_signals: list,  # noqa: ANN001
    ) -> RiskContext:
        return RiskContext(
            now=data.now,
            open_signals=open_signals,
            market_health=data.market_health,
            daily_loss_pct=data.daily_loss_pct,
            weekly_loss_pct=data.weekly_loss_pct,
            btc_change_24h_pct=data.btc_change_24h_pct,
            adx=data.adx_values.get(symbol),
            atr_pct=data.atr_values.get(symbol),
            kill_switch_active=data.kill_switch_active,
            kill_switch_reason=data.kill_switch_reason,
            consecutive_stops=data.consecutive_stops,
            consecutive_stop_until=data.consecutive_stop_until,
            price_age_seconds=data.price_ages.get(symbol),
        )

    def _as_open_signal(self, candidate, data: CycleInput):  # noqa: ANN001, ANN202
        """Yangi chiqarilgan nomzodni "ochiq signal" sifatida ifodalaydi."""
        from core.domain.enums import SignalStatus
        from core.domain.models import Signal

        return Signal(
            symbol=candidate.symbol,
            levels=candidate.levels,
            source=candidate.source,
            status=SignalStatus.PENDING,
            score=candidate.score,
            created_at=data.now,
        )
