"""2-bo'lim: signal holatini avtomatik kuzatish.

Holatlar:
    ⏳ Kutilmoqda  — narx Entry'ga yetmagan
    ✅ Faol        — narx Entry'ga yetgan
    🎯 TP1 olindi  — signal faol, TP2 kutilmoqda
    🎯🎯 TP2 olindi — signal to'liq yopiladi
    🛑 Stop bo'ldi — signal yopiladi

Cheksiz miqdordagi coin/signal MUSTAQIL kuzatiladi — bittasi boshqasiga
ta'sir qilmaydi.

Bu modul SOF: tarmoqqa, bazaga yoki Telegram'ga murojaat qilmaydi. Narx
nuqtasini qabul qiladi, hodisalar ro'yxatini qaytaradi. Shu sababli
backtestda ham xuddi shu kod ishlaydi.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from core.domain.enums import SignalStatus
from core.domain.models import Signal
from core.signals.events import SignalEvent, SignalEventKind
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)

#: Faol bo'lgach shu vaqt ichida Stop yesa — "yolg'on signal" (3.8-band)
DEFAULT_FALSE_SIGNAL_WINDOW = timedelta(hours=1)

#: Narx Entry'ga yetmasdan shu muddat o'tsa, signal bekor qilinadi
DEFAULT_PENDING_EXPIRY = timedelta(hours=24)


class SignalTracker:
    """Bir nechta signalni bir vaqtda, mustaqil kuzatadi."""

    def __init__(
        self,
        false_signal_window: timedelta = DEFAULT_FALSE_SIGNAL_WINDOW,
        pending_expiry: timedelta = DEFAULT_PENDING_EXPIRY,
    ) -> None:
        self._signals: dict[int, Signal] = {}
        self._next_local_id = -1
        self._false_signal_window = false_signal_window
        self._pending_expiry = pending_expiry

    # ------------------------------------------------------------------ #
    #  Boshqaruv
    # ------------------------------------------------------------------ #

    def track(self, signal: Signal) -> int:
        """Signalni kuzatuvga qo'shadi va uning kalitini qaytaradi."""
        if signal.signal_id is None:
            # Bazaga yozilmagan signal (masalan backtestda) uchun lokal kalit
            key = self._next_local_id
            self._next_local_id -= 1
        else:
            key = signal.signal_id
        self._signals[key] = signal
        return key

    def untrack(self, key: int) -> None:
        self._signals.pop(key, None)

    @property
    def open_signals(self) -> list[Signal]:
        """Hali yopilmagan signallar (Risk Engine shu ro'yxatga tayanadi)."""
        return [s for s in self._signals.values() if s.status.is_open]

    def symbols(self) -> set[str]:
        """Kuzatilishi kerak bo'lgan coinlar — WebSocket obunasi shu asosda."""
        return {s.symbol.upper() for s in self._signals.values() if s.status.is_open}

    def get(self, key: int) -> Signal | None:
        return self._signals.get(key)

    # ------------------------------------------------------------------ #
    #  Narx oqimi
    # ------------------------------------------------------------------ #

    def on_price(self, symbol: str, price: float, at: datetime) -> list[SignalEvent]:
        """Yangi narx keldi — shu coinning barcha ochiq signallarini yangilaydi.

        Args:
            symbol: coin belgisi (masalan `"BTC"`).
            price: joriy narx.
            at: narx vaqti (timezone-aware).

        Returns:
            Sodir bo'lgan hodisalar. Bo'sh ro'yxat — o'zgarish yo'q.
        """
        if price <= 0:
            logger.warning("Noto'g'ri narx e'tiborsiz qoldirildi: %s = %s", symbol, price)
            return []
        if at.tzinfo is None:
            raise ValueError("Narx vaqti timezone-aware bo'lishi kerak")

        upper = symbol.upper()
        hodisalar: list[SignalEvent] = []

        for key, signal in self._signals.items():
            if signal.symbol.upper() != upper or signal.status.is_closed:
                continue
            hodisalar.extend(self._advance(key, signal, price, at))

        return hodisalar

    def check_expiry(self, now: datetime) -> list[SignalEvent]:
        """Entry'ga yetmasdan eskirgan signallarni bekor qiladi."""
        hodisalar: list[SignalEvent] = []
        for key, signal in self._signals.items():
            if signal.status is not SignalStatus.PENDING or signal.created_at is None:
                continue
            if now - signal.created_at < self._pending_expiry:
                continue
            signal.status = SignalStatus.CANCELLED
            signal.closed_at = now
            hodisalar.append(
                SignalEvent(
                    signal_id=key if key > 0 else None,
                    symbol=signal.symbol,
                    kind=SignalEventKind.CANCELLED,
                    price=signal.levels.entry,
                    at=now,
                    new_status=SignalStatus.CANCELLED,
                    detail=(
                        f"Narx {self._pending_expiry.total_seconds() / 3600:.0f} soat ichida "
                        "kirish nuqtasiga yetmadi — signal bekor qilindi."
                    ),
                )
            )
        return hodisalar

    def mark_weakening(self, key: int, at: datetime, detail: str) -> SignalEvent | None:
        """4.1-band: ball keskin pasaydi — "⚠️ Zaiflashmoqda".

        Bu TAVSIYA, majburiy avtomatik yopish EMAS: signal ochiq qoladi va
        TP/Stop kuzatuvi davom etadi.
        """
        signal = self._signals.get(key)
        if signal is None or signal.status.is_closed:
            return None
        if signal.status is SignalStatus.WEAKENING:
            return None  # takror ogohlantirmaymiz

        oldingi = signal.status
        signal.status = SignalStatus.WEAKENING
        return SignalEvent(
            signal_id=key if key > 0 else None,
            symbol=signal.symbol,
            kind=SignalEventKind.WEAKENING,
            price=signal.levels.entry,
            at=at,
            new_status=SignalStatus.WEAKENING,
            detail=f"{detail} (oldingi holat: {oldingi.value})",
        )

    # ------------------------------------------------------------------ #
    #  Ichki mantiq
    # ------------------------------------------------------------------ #

    def _advance(
        self, key: int, signal: Signal, price: float, at: datetime
    ) -> list[SignalEvent]:
        """Bitta signalni yangi narx bo'yicha oldinga suradi."""
        levels = signal.levels
        hodisalar: list[SignalEvent] = []
        signal_id = key if key > 0 else None

        def qayd(kind: SignalEventKind, status: SignalStatus, detail: str) -> None:
            signal.status = status
            hodisalar.append(
                SignalEvent(
                    signal_id=signal_id,
                    symbol=signal.symbol,
                    kind=kind,
                    price=price,
                    at=at,
                    new_status=status,
                    detail=detail,
                )
            )

        # --- ⏳ Kutilmoqda: narx Entry'ga tushdimi? ---
        if signal.status is SignalStatus.PENDING:
            if price > levels.entry:
                return []
            signal.activated_at = at
            qayd(
                SignalEventKind.ACTIVATED,
                SignalStatus.ACTIVE,
                f"Narx kirish nuqtasiga yetdi ({price:g}).",
            )
            # Narx bir sakrashda Stop'dan ham pastga tushgan bo'lishi mumkin
            # (gap). Bunday holatda buyurtma bajarilib, darhol Stop yegan
            # deb qaraladi — bu eng ehtiyotkor talqin (0.3-band).

        # --- 🛑 Stop (TP'dan OLDIN tekshiriladi — ehtiyotkor talqin) ---
        if price <= levels.stop:
            signal.closed_at = at
            yolgon = self._is_false_signal(signal, at)
            qayd(
                SignalEventKind.STOPPED,
                SignalStatus.STOPPED,
                f"Narx Stop darajasiga tushdi ({price:g}).",
            )
            if yolgon:
                hodisalar.append(
                    SignalEvent(
                        signal_id=signal_id,
                        symbol=signal.symbol,
                        kind=SignalEventKind.FALSE_SIGNAL,
                        price=price,
                        at=at,
                        new_status=SignalStatus.STOPPED,
                        detail=(
                            "Signal faol bo'lgach "
                            f"{self._false_signal_window.total_seconds() / 60:.0f} daqiqa ichida "
                            "Stop yedi — zaif kirish nuqtasi belgisi (3.8-band)."
                        ),
                    )
                )
            return hodisalar

        # --- 🎯 TP1 ---
        if signal.status in {SignalStatus.ACTIVE, SignalStatus.WEAKENING} and price >= levels.tp1:
            qayd(
                SignalEventKind.TP1_HIT,
                SignalStatus.TP1_HIT,
                f"TP1 darajasiga yetdi ({price:g}).",
            )

        # --- 🎯🎯 TP2 (signal yopiladi) ---
        if signal.status is SignalStatus.TP1_HIT and price >= levels.tp2:
            signal.closed_at = at
            qayd(
                SignalEventKind.TP2_HIT,
                SignalStatus.TP2_HIT,
                f"TP2 darajasiga yetdi ({price:g}) — signal yopildi.",
            )

        return hodisalar

    def _is_false_signal(self, signal: Signal, at: datetime) -> bool:
        """3.8-band: faol bo'lgach tez Stop yeganmi."""
        if signal.activated_at is None:
            return False
        return at - signal.activated_at <= self._false_signal_window
