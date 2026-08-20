"""15-bosqich: avtomatik signal sikli — barcha modullarni bog'laydi.

Zanjir:
    Top 30 Halal  ->  strategiyalar (parallel)  ->  ball va reyting
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
from core.pipeline.context import CycleInput, CycleResult, RejectedCandidate, SymbolData
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

    def run(self, data: CycleInput) -> CycleResult:
        """Siklni bir marta bajaradi."""
        rad_etilganlar: list[RejectedCandidate] = []

        # 1) Chegara — Bozor Salomatligiga qarab (3.5-band)
        salomatlik_qiymati = data.market_health.value if data.market_health else None
        chegara = self._risk_engine.score_threshold(salomatlik_qiymati)

        if chegara is None:
            # 4.9-band: indeks past yoki hisoblanmagan — yangi signal yo'q.
            # Coinlarni tahlil qilishning ma'nosi yo'q, resurs tejaladi.
            sabab = (
                f"Bozor Salomatligi past ({salomatlik_qiymati:.0f}/100)"
                if salomatlik_qiymati is not None
                else "Bozor Salomatligi hisoblanmagan"
            )
            logger.info("Sikl to'xtatildi: %s", sabab)
            return CycleResult(
                emitted=[],
                rejected=[RejectedCandidate("*", "market_health", sabab)],
                threshold=None,
                market_health=data.market_health,
                analyzed_count=0,
            )

        # 2) Strategiyalarni har bir coinga qo'llash
        nomzodlar = []
        tafsilotlar = {}
        for coin in data.symbols:
            for strategiya in self._strategies:
                nomzod = self._analyze(strategiya, coin, data, rad_etilganlar)
                if nomzod is not None:
                    nomzodlar.append(nomzod)
                    tafsilotlar[nomzod.symbol] = nomzod.breakdown

        # 3) Reytinglash va chegara
        reyting = self._scorer.rank(nomzodlar, chegara)
        otganlar = self._scorer.passed(reyting)

        for element in reyting:
            if not element.passed_threshold:
                rad_etilganlar.append(
                    RejectedCandidate(
                        symbol=element.candidate.symbol,
                        stage="threshold",
                        detail=f"Ball {element.score:.0f} < chegara {chegara:.0f}",
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
                rad_etilganlar.append(
                    RejectedCandidate(
                        symbol=nomzod.symbol,
                        stage="risk_engine",
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
        coin: SymbolData,
        data: CycleInput,
        rejected: list[RejectedCandidate],
    ):  # noqa: ANN202
        """Bitta strategiyani bitta coinga qo'llaydi.

        0.3-band: strategiyaning nosozligi butun siklni to'xtatmaydi.
        """
        kirish = StrategyInput(
            symbol=coin.symbol,
            now=data.now,
            halal_verdict=coin.halal_verdict,
            candles=coin.candles,
            market_health=data.market_health,
        )
        try:
            nomzod = strategy.analyze(kirish)
        except Exception:  # noqa: BLE001
            logger.exception("Strategiya xato berdi: %s / %s", strategy.name, coin.symbol)
            rejected.append(
                RejectedCandidate(
                    coin.symbol, f"{strategy.name}:error", "Strategiya ichki xatosi"
                )
            )
            return None

        if nomzod is None:
            sabab = getattr(strategy, "last_rejection", None)
            rejected.append(
                RejectedCandidate(
                    symbol=coin.symbol,
                    stage=f"{strategy.name}:{sabab.stage if sabab else 'no_setup'}",
                    detail=sabab.detail if sabab else "Shart bajarilmadi",
                )
            )
        return nomzod

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
