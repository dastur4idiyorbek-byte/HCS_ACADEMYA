"""3.7-band: Bozor Salomatligi Indeksi — markaziy muvofiqlashtiruvchi mexanizm.

Muammo (spetsifikatsiyadan): har omil alohida-alohida tekshirilsa, ular
orasida nomuvofiqlik chiqadi — bitta modul "bozor yaxshi" desa, boshqasi
"balans yo'q" deydi.

Yechim: bitta yagona, markaziy 0-100 indeks. Har sham yopilganda qayta
hisoblanadi.

    🟢 80-100 — signal chegarasi past (erkin)
    🟡 40-79  — signal beriladi, lekin ehtiyotkorroq
    🔴 0-39   — yangi signal to'xtatiladi, faqat kuzatuv

Kelajakda yangi omil (masalan Fear & Greed Index) qo'shilsa, `factors.py` ga
funksiya qo'shiladi va vazn beriladi — butun tizim qayta qurilmaydi.
"""

from __future__ import annotations

from core.analysis.market_health.factors import build_factors
from core.analysis.market_health.inputs import HealthInputs
from core.config.schema import AppConfig
from core.domain.models import HealthFactor, MarketHealth
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


class MarketHealthCalculator:
    """Indeksni hisoblaydi. Sof: hech qayerga murojaat qilmaydi."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def compute(self, inputs: HealthInputs) -> MarketHealth:
        """Besh omildan yagona 0-100 indeks quradi."""
        omillar = build_factors(
            inputs=inputs,
            weights=self._config.market_health.weights,
            dominance_config=self._config.market_health.btc_dominance,
            adx_threshold=self._config.analysis.indicators.adx_trend_threshold,
        )
        qiymat = sum(omil.weighted for omil in omillar)
        salomatlik = MarketHealth(
            value=qiymat, factors=omillar, computed_at=inputs.computed_at
        )

        logger.info(
            "Bozor Salomatligi: %.1f/100 (%s)", salomatlik.value, salomatlik.band.value
        )
        return salomatlik

    def daily_preview(self, inputs: HealthInputs) -> MarketHealth:
        """3.7-band: kunlik oldindan tahlil (UTC 00:00 atrofida).

        Yangi sham ochilishidan oldin tizim BTC Dominance asosida kunning
        umumiy yo'nalishini taxmin qiladi. Bu — indeksning BOSHLANG'ICH
        qiymati, aniq o'lchov emas.

        Boshqa omillar hali ma'lum emas, shuning uchun ular NEYTRAL (0.5)
        deb olinadi — nol qo'yilsa kun boshida tizim har doim "qizil"
        bo'lardi va hech qachon ishga tushmasdi.
        """
        vaznlar = self._config.market_health.weights
        dominance = build_factors(
            inputs=inputs,
            weights=vaznlar,
            dominance_config=self._config.market_health.btc_dominance,
            adx_threshold=self._config.analysis.indicators.adx_trend_threshold,
        )[0]

        neytral = [
            HealthFactor(
                name=nom,
                score=0.5,
                weight=vazn,
                explanation="Kun boshi — hali o'lchanmagan (neytral)",
            )
            for nom, vazn in (
                ("halal_trend_breadth", vaznlar.halal_trend_breadth),
                ("volatility_regime", vaznlar.volatility_regime),
                ("aggregate_user_capacity", vaznlar.aggregate_user_capacity),
                ("signal_saturation", vaznlar.signal_saturation),
            )
        ]

        omillar = [dominance, *neytral]
        salomatlik = MarketHealth(
            value=sum(omil.weighted for omil in omillar),
            factors=omillar,
            computed_at=inputs.computed_at,
        )
        logger.info(
            "Kunlik oldindan tahlil: %.1f/100 (%s)",
            salomatlik.value,
            salomatlik.band.value,
        )
        return salomatlik


def describe(health: MarketHealth) -> str:
    """Admin dashboardi uchun matn (3.7-band: "tizim nega sokin?").

    Bitta raqam savolga javob beradi, omillar esa sababni ko'rsatadi.
    """
    band_izohi = {
        "high": "signal chegarasi past — erkin rejim",
        "mid": "signal beriladi, lekin ehtiyotkorroq",
        "low": "yangi signal to'xtatilgan — faqat kuzatuv",
    }[health.band.value]

    qatorlar = [
        f"{health.band.emoji} Bozor Salomatligi: {health.value:.0f}/100",
        f"   {band_izohi}",
        "",
    ]
    for omil in sorted(health.factors, key=lambda f: f.weighted, reverse=True):
        ulush = round(omil.score * 5)
        chizgi = "▰" * ulush + "▱" * (5 - ulush)
        qatorlar.append(f"{chizgi} {omil.weighted:4.1f}/{omil.weight:<4.0f} {omil.explanation}")

    return "\n".join(qatorlar)
