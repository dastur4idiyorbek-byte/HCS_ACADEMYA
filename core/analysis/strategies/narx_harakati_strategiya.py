"""NARX HARAKATI strategiyasi — kitobning yadrosi kod sifatida.

MANBA: "PRICE ACTION STRATEGIES — TOP 15"
(`docs/NARX_HARAKATI_STRATEGIYALARI.md`).

NIMA UCHUN YANGI STRATEGIYA KERAK EDI.

`classic_ta` narx Discount zonasida bo'lsa kiradi. U qaytishni
KUTMAYDI va tasdiq SO'RAMAYDI. Yettita gipoteza to'plami
sinaldi — ball, filtr, chiqish, nisbat, rejim — va win-rate
har safar 27-29% da qoldi.

Kitob esa aynan shu xatoni bir necha marta ogohlantiradi:

    "Ba'zan biz ham xato qilamizki, biz narx kritik zonaga
     yaqin bo'lganda savdoga kiramiz va stoploss tezda uriladi."

    "Hech qachon figura to'liq shakllanmasdan savdoga kirish
     juda katta xato bo'ladi."

Ya'ni bu strategiya `classic_ta` ning yana bir filtri emas —
BOSHQA kirish mexanizmi. Shuning uchun u alohida strategiya:
ikkalasi yonma-yon o'lchanadi va qaysi biri yaxshiroq degan
savolga raqam javob beradi.

FAQAT XARID. Kitobdagi sotish naqshlari umuman qurilmagan —
loyiha egasining sharti va kitobning o'z qoidasi ("nojoiz
savdo").
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.narx_harakati import (
    QaytaSinov,
    ikkita_pastlik_topilsinmi,
    qayta_sinov_topilsinmi,
)
from core.analysis.scoring import build_levels_with_stop
from core.analysis.strategies.base import Strategy, StrategyInput
from core.analysis.strategies.classic_ta import RejectionReason, classic_ta_rules
from core.analysis.support_resistance import SupportResistanceDetector
from core.config.schema import AppConfig
from core.domain.enums import SignalSource
from core.domain.models import ScoreBreakdown, ScoreComponent, SignalCandidate
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Stop naqshning eng past nuqtasidan shuncha ATR pastga qo'yiladi.
#:
#: Kitob "oldingi pastki nuqtadan PASTROQDA" deydi, lekin qancha
#: pastroqligini aytmaydi. Aynan tubga qo'yilsa, narx bir tiyin
#: pastga tegib qaytganda ham Stop ishlardi.
STOP_ZAXIRA_ATR = 0.25


@dataclass(frozen=True, slots=True)
class _Naqsh:
    """Topilgan naqsh — kirish uchun yetarli ma'lumot."""

    nomi: str
    daraja: float
    eng_past: float
    izoh: str


class NarxHarakatiStrategy(Strategy):
    """Yorish → qayta sinov → buqasimon sham."""

    name = "narx_harakati"

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._detector = SupportResistanceDetector(
            config.analysis.support_resistance,
            config.analysis.indicators.atr_period,
        )
        self._last_rejection: RejectionReason | None = None

    @property
    def enabled(self) -> bool:
        return self._config.strategies.narx_harakati.enabled

    def required_timeframes(self) -> list[str]:
        return [self._config.analysis.entry_timeframe]

    @property
    def last_rejection(self) -> RejectionReason | None:
        return self._last_rejection

    # ------------------------------------------------------------------ #

    def analyze(self, data: StrategyInput) -> SignalCandidate | None:
        self._last_rejection = None
        analysis = self._config.analysis
        qoidalar_nh = self._config.strategies.narx_harakati

        if not data.halal_verdict.is_tradable:
            return self._reject("halal", f"{data.symbol}: {data.halal_verdict.reason}")

        shamlar = data.series(analysis.entry_timeframe)
        if len(shamlar) < analysis.indicators.min_candles:
            return self._reject(
                "data",
                f"{analysis.entry_timeframe} uchun sham yetarli emas "
                f"({len(shamlar)} < {analysis.indicators.min_candles})",
            )

        zona_xaritasi = self._detector.detect(shamlar)
        if zona_xaritasi is None:
            return self._reject("zones", "S/R zonalari aniqlanmadi")

        atr = zona_xaritasi.atr
        naqsh = self._naqsh_qidir(shamlar, zona_xaritasi, qoidalar_nh, atr)
        if naqsh is None:
            return self._reject(
                "naqsh",
                "Yorish → qayta sinov → buqasimon sham naqshi topilmadi",
            )

        # Stop NAQSHDAN keladi — kitobning qoidasi: "oldingi pastki
        # nuqtadan pastroqda". Formuladan emas.
        kirish = shamlar[-1].close
        stop = naqsh.eng_past - atr * STOP_ZAXIRA_ATR

        daraja_natijasi = build_levels_with_stop(
            zona_xaritasi,
            classic_ta_rules(self._config),
            kirish,
            stop,
            portfolio=self._config.portfolio,
        )
        if not daraja_natijasi.ok:
            return self._reject(daraja_natijasi.stage, daraja_natijasi.reason)

        tafsilot = self._ball(data.symbol, naqsh, daraja_natijasi.levels, atr, kirish)

        logger.info(
            "Narx harakati nomzodi: %s naqsh=%s ball=%.1f daraja=%.6g",
            data.symbol,
            naqsh.nomi,
            tafsilot.total,
            naqsh.daraja,
        )
        return SignalCandidate(
            symbol=data.symbol,
            levels=daraja_natijasi.levels,
            source=SignalSource.NARX_HARAKATI,
            breakdown=tafsilot,
            halal_verdict=data.halal_verdict,
        )

    # ------------------------------------------------------------------ #

    def _naqsh_qidir(self, shamlar, zona_xaritasi, qoidalar, atr):  # noqa: ANN001, ANN202
        """Ikkita manba, bitta yadro.

        1. QARSHILIK ZONALARI — kitobning 1, 3, 5, 7, 8-strategiyalari
           hammasi "daraja yorildi" bilan boshlanadi va daraja
           qayerdan kelgani ahamiyatsiz.
        2. IKKITA PASTLIK — 2 va 10-strategiya. Bu yerda daraja
           figuraning BO'YIN CHIZIG'I bo'ladi.

        Ikkalasi ham bir xil uch qadamdan o'tadi.
        """
        # Narxdan PASTDA qolgan qarshiliklar — ya'ni allaqachon
        # yorilganlari. Yorilmagan qarshilikni "yorildi" deb
        # qidirishning ma'nosi yo'q.
        joriy = shamlar[-1].close
        darajalar = [
            (z.high, "qarshilik yorildi")
            for z in zona_xaritasi.zones
            if z.high < joriy
        ]

        figura = ikkita_pastlik_topilsinmi(shamlar, qoidalar, atr)
        if figura is not None and figura.boyin_chizigi < joriy:
            darajalar.append((figura.boyin_chizigi, "ikkita pastlik"))

        # Eng YAQIN darajadan boshlanadi: yaqin daraja bugungi
        # savdoga tegishli, uzoqdagisi esa eski tarix.
        eng_yaxshi: _Naqsh | None = None
        for daraja, nomi in sorted(darajalar, key=lambda x: -x[0]):
            sinov: QaytaSinov | None = qayta_sinov_topilsinmi(
                shamlar, daraja, qoidalar, atr
            )
            if sinov is not None:
                eng_yaxshi = _Naqsh(nomi, daraja, sinov.eng_past, sinov.izoh())
                break
        return eng_yaxshi

    def _ball(self, symbol, naqsh, darajalar, atr, kirish) -> ScoreBreakdown:  # noqa: ANN001
        """Ball faqat TARTIBLAYDI — qaror naqshning o'zida.

        Uchta omil, uchalasi ham naqshning SIFATI haqida:
        nisbat, darajaga yaqinlik va Stop masofasi.
        """
        rr = darajalar.risk_reward
        rr_ulushi = min(1.0, rr / 3.0)

        # Kirish darajaga qanchalik yaqin bo'lsa shunchalik yaxshi:
        # kitob "kech kirmang" deb ogohlantiradi.
        uzoqlik = (kirish - naqsh.daraja) / atr if atr > 0 else 0.0
        yaqinlik_ulushi = max(0.0, 1.0 - uzoqlik / 2.0)

        # Stop masofasi o'rtacha bo'lsa yaxshi: juda tor — shovqin,
        # juda keng — pozitsiya kichrayadi.
        stop_pct = darajalar.stop_distance_pct
        stop_ulushi = max(0.0, 1.0 - abs(stop_pct - 3.0) / 5.0)

        return ScoreBreakdown(
            symbol=symbol,
            components=[
                ScoreComponent(
                    name="Risk/Reward",
                    earned=round(rr_ulushi * 45, 1),
                    maximum=45.0,
                    explanation=f"1:{rr:.1f} nisbat",
                ),
                ScoreComponent(
                    name="Darajaga yaqinlik",
                    earned=round(yaqinlik_ulushi * 35, 1),
                    maximum=35.0,
                    explanation=f"kirish darajadan {uzoqlik:.1f} ATR yuqorida",
                ),
                ScoreComponent(
                    name="Stop masofasi",
                    earned=round(stop_ulushi * 20, 1),
                    maximum=20.0,
                    explanation=f"{stop_pct:.2f}% ({naqsh.izoh})",
                ),
            ],
        )

    def _reject(self, stage: str, detail: str) -> None:
        self._last_rejection = RejectionReason(stage, detail)
        logger.debug("Narx harakati signal bermadi (%s): %s", stage, detail)
        return None
