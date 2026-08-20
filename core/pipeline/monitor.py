"""4.1 va 4.2-band: faol signallarni qayta baholash.

4.1 — Dinamik chiqish: signal "faol" bo'lganidan keyin ham, har yangi sham
yopilganda o'sha coin uchun qayta to'liq tahlil ishga tushadi. Ball keskin
pasaysa, "⚠️ Zaiflashmoqda" holati qo'shiladi.

    Bu — TAVSIYA, majburiy avtomatik yopish EMAS. Sabab: bot foydalanuvchi
    hisobiga ulanmagan (5-bo'lim chegarasi), shuning uchun u pozitsiyani
    yopa olmaydi ham. Qaror foydalanuvchiniki.

4.2 — Signal almashtirish (rotatsiya): faol signal zaiflashayotgan bo'lsa VA
boshqa coin sezilarli yuqori ball bilan imkoniyat ko'rsatsa, tizim FAQAT
ENG ZAIF faol signalni almashtirish tavsiyasini beradi.

    Whipsaw himoyasi: sovutish davri va minimal ball farqi MAJBURIY.
    Ansiz tizim har sham yopilganda "u yaxshiroq, yo'q bu yaxshiroq" deb
    foydalanuvchini charchatardi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from core.config.schema import RiskEngineConfig
from core.domain.models import Signal, SignalCandidate
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class WeakeningAlert:
    """4.1-band: signal zaiflashmoqda."""

    signal: Signal
    previous_score: float
    current_score: float

    @property
    def drop(self) -> float:
        return self.previous_score - self.current_score


@dataclass(frozen=True, slots=True)
class RotationSuggestion:
    """4.2-band: almashtirish tavsiyasi."""

    weak_signal: Signal
    replacement: SignalCandidate
    score_gap: float

    def describe(self) -> str:
        return (
            f"📉 {self.weak_signal.symbol} signali zaiflashmoqda → "
            f"📈 {self.replacement.symbol} da yaxshi imkoniyat paydo bo'ldi. "
            "Almashtirish tavsiya etiladi."
        )


class SignalMonitor:
    """Faol signallarni kuzatib, zaiflashish va rotatsiyani aniqlaydi."""

    def __init__(self, config: RiskEngineConfig) -> None:
        self._config = config
        #: symbol -> oxirgi rotatsiya tavsiyasi vaqti (whipsaw himoyasi)
        self._last_rotation: dict[str, datetime] = {}

    def check_weakening(
        self,
        signal: Signal,
        current_score: float,
    ) -> WeakeningAlert | None:
        """4.1-band: ball keskin pasaydimi.

        Signalning boshlang'ich balli yo'q bo'lsa (masalan qo'lda kiritilgan),
        taqqoslash imkonsiz — ogohlantirish berilmaydi.
        """
        if signal.score is None:
            return None

        pasayish = signal.score - current_score
        if pasayish < self._config.weakening.score_drop_points:
            return None

        logger.info(
            "Signal zaiflashmoqda: %s %.0f -> %.0f", signal.symbol, signal.score, current_score
        )
        return WeakeningAlert(
            signal=signal, previous_score=signal.score, current_score=current_score
        )

    def suggest_rotation(
        self,
        weak_signals: list[tuple[Signal, float]],
        candidates: list[SignalCandidate],
        now: datetime,
    ) -> RotationSuggestion | None:
        """4.2-band: eng zaif signalni almashtirish tavsiyasi.

        Args:
            weak_signals: `(signal, hozirgi_ball)` juftliklari.
            candidates: yangi imkoniyatlar.

        Returns:
            FAQAT BITTA tavsiya — eng zaif signal uchun. Bir vaqtda bir
            nechta almashtirish taklif qilish foydalanuvchini chalg'itardi.
        """
        if not weak_signals or not candidates:
            return None

        zaif_signal, zaif_ball = min(weak_signals, key=lambda pair: pair[1])
        eng_yaxshi = max(candidates, key=lambda c: c.score)

        farq = eng_yaxshi.score - zaif_ball
        if farq < self._config.rotation.min_score_gap:
            return None

        if not self._cooldown_passed(zaif_signal.symbol, now):
            logger.debug("Rotatsiya sovutish davrida: %s", zaif_signal.symbol)
            return None

        self._last_rotation[zaif_signal.symbol] = now
        logger.info(
            "Rotatsiya tavsiyasi: %s (%.0f) -> %s (%.0f)",
            zaif_signal.symbol,
            zaif_ball,
            eng_yaxshi.symbol,
            eng_yaxshi.score,
        )
        return RotationSuggestion(
            weak_signal=zaif_signal, replacement=eng_yaxshi, score_gap=farq
        )

    def _cooldown_passed(self, symbol: str, now: datetime) -> bool:
        """Whipsaw himoyasi: bir xil signal uchun tez-tez tavsiya berilmaydi."""
        oxirgi = self._last_rotation.get(symbol)
        if oxirgi is None:
            return True
        sovutish = timedelta(minutes=self._config.rotation.cooldown_minutes)
        return now - oxirgi >= sovutish

    def reset_cooldown(self, symbol: str) -> None:
        """Signal yopilganda sovutish tarixi tozalanadi."""
        self._last_rotation.pop(symbol, None)
