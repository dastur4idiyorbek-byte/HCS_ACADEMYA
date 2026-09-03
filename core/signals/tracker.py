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

from collections.abc import Callable
from datetime import datetime, timedelta

from core.config.schema import AppConfig, TrailingStopConfig
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
        max_holding: timedelta | None = None,
        trailing: TrailingStopConfig | None = None,
    ) -> None:
        self._signals: dict[int, Signal] = {}
        self._next_local_id = -1
        self._false_signal_window = false_signal_window
        self._pending_expiry = pending_expiry
        self._max_holding = max_holding
        self._trailing = trailing or TrailingStopConfig()

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

    def check_expiry(
        self, now: datetime, price_of: Callable[[str], float | None] | None = None
    ) -> list[SignalEvent]:
        """Muddati o'tgan signallarni yopadi.

        IKKI XIL MUDDAT, IKKI XIL MA'NO:

            kutish muddati  — narx Entry'ga umuman yetmadi. Pozitsiya
                              OCHILMAGAN, ya'ni natija yo'q -> CANCELLED
            ushlash muddati — pozitsiya ochilgan, lekin na nishonga,
                              na Stopga bordi -> TIMED_OUT, bozor
                              narxida yopiladi va natija HISOBGA
                              KIRADI

        Ikkinchisini "bekor qilish" deb belgilash raqamlarni
        buzardi: yopilgan pozitsiyaning foyda/zarari bor, u
        statistikadan chiqib ketmasligi kerak.

        Args:
            now: joriy vaqt.
            price_of: coin -> joriy narx. Ushlash muddati faqat shu
                berilganda ishlaydi: narxsiz pozitsiyani yopib
                bo'lmaydi va raqam o'ylab topilmaydi.
        """
        hodisalar = self._kutish_muddati(now)
        if self._max_holding is not None and price_of is not None:
            hodisalar.extend(self._ushlash_muddati(now, price_of))
        return hodisalar

    def _ushlash_muddati(
        self, now: datetime, price_of: Callable[[str], float | None]
    ) -> list[SignalEvent]:
        """Faol pozitsiya muddati tugasa — bozor narxida yopiladi."""
        hodisalar: list[SignalEvent] = []
        for key, signal in self._signals.items():
            if signal.status.is_closed or signal.status is SignalStatus.PENDING:
                continue
            boshlangan = signal.activated_at or signal.created_at
            if boshlangan is None or now - boshlangan < self._max_holding:
                continue

            narx = price_of(signal.symbol)
            if narx is None or narx <= 0:
                continue

            signal.status = SignalStatus.TIMED_OUT
            signal.closed_at = now
            soat = self._max_holding.total_seconds() / 3600
            hodisalar.append(
                SignalEvent(
                    signal_id=key if key > 0 else None,
                    symbol=signal.symbol,
                    kind=SignalEventKind.TIMED_OUT,
                    price=narx,
                    at=now,
                    new_status=SignalStatus.TIMED_OUT,
                    detail=(
                        f"Muddat tugadi: {soat:.0f} soat ichida na nishonga, "
                        f"na Stopga bordi. Bozor narxida yopildi ({narx:g}) — "
                        "kapital band turmasin."
                    ),
                )
            )
        return hodisalar

    def _kutish_muddati(self, now: datetime) -> list[SignalEvent]:
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

    def cancel(
        self, key: int, at: datetime, detail: str, price: float | None = None
    ) -> SignalEvent | None:
        """Signalni qo'lda bekor qiladi (admin qarori).

        Nima uchun bekor qilish, o'chirish emas: yopilgan signal statistika
        va postmortem uchun tarixda qolishi kerak (3.8-band). `CANCELLED`
        holati esa natija hisobiga umuman kirmaydi — ya'ni sinov signali
        raqamlarni buzmaydi.

        Allaqachon yopilgan signal qayta bekor qilinmaydi: TP yoki Stop
        bilan tugagan natijani keyin o'zgartirib bo'lmaydi.

        Args:
            key: `track()` qaytargan kalit (bazadagi signal id).
            at: bekor qilish vaqti.
            detail: sabab — foydalanuvchiga shu matn ko'rsatiladi.
            price: yopilish narxi. `None` bo'lsa kirish narxi olinadi
                (narx ma'lum bo'lmasa foyda/zarar nolga teng deb qaraladi).

        Returns:
            Hodisa, yoki `None` — signal kuzatuvda yo'q/allaqachon yopilgan.
        """
        signal = self._signals.get(key)
        if signal is None or signal.status.is_closed:
            return None

        signal.status = SignalStatus.CANCELLED
        signal.closed_at = at
        return SignalEvent(
            signal_id=key if key > 0 else None,
            symbol=signal.symbol,
            kind=SignalEventKind.CANCELLED,
            price=price if price is not None else signal.levels.entry,
            at=at,
            new_status=SignalStatus.CANCELLED,
            detail=detail,
        )

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

        # --- 📈 Stopni orqadan surish ---
        #
        # Stop TEKSHIRUVIDAN OLDIN yangilanadi, lekin faqat narx
        # cho'qqidan yuqoriga chiqqanda ko'tariladi. Tartib muhim:
        # avval tekshirilsa, o'sha shamning o'zida surilgan Stop
        # ishlab ketardi va bir sham ichida ham ko'tarilib, ham
        # tegib qolgandek bo'lardi.
        self._stopni_sur(signal, price)

        # --- 🛑 Stop (TP'dan OLDIN tekshiriladi — ehtiyotkor talqin) ---
        #
        # AMALDAGI Stop ishlatiladi: TP1 olingach u kirish narxiga
        # ko'tariladi (breakeven), surilgan Stop undan ham yuqori
        # bo'lishi mumkin. Eski `levels.stop` ni ishlatsak, olingan
        # foyda qaytib ketishi mumkin bo'lardi.
        amaldagi_stop = signal.effective_stop
        if price <= amaldagi_stop:
            signal.closed_at = at
            yolgon = self._is_false_signal(signal, at)
            breakeven = signal.stop_at_breakeven
            qayd(
                SignalEventKind.STOPPED,
                SignalStatus.STOPPED,
                (
                    f"Narx kirish narxiga qaytdi ({price:g}) — Stop kirish "
                    "darajasida edi, TP1 dagi foyda saqlanib qoldi."
                    if breakeven
                    else f"Narx Stop darajasiga tushdi ({price:g})."
                ),
            )
            if yolgon and not breakeven:
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

        # --- 🎯 TP lar ---
        #
        # TP SONI QAT'IY EMAS: 1, 2 yoki 3 bo'lishi mumkin. Narx bir
        # sakrashda bir nechtasidan o'tib ketishi ham mumkin, shuning
        # uchun ro'yxat BOSHIDAN oxirigacha yuriladi.
        #
        # Uch bosqich ajratiladi:
        #   birinchi TP  -> Stop kirish narxiga (breakeven)
        #   oraliq TP    -> qismli sotish, signal ochiq qoladi
        #   YAKUNIY TP   -> signal yopiladi
        yuruvchi = {
            SignalStatus.ACTIVE,
            SignalStatus.WEAKENING,
            SignalStatus.TP1_HIT,
        }
        while (
            signal.status in yuruvchi
            and signal.reached_tps < levels.tp_count
            and price >= levels.takes[signal.reached_tps].price
        ):
            nomer = signal.reached_tps + 1
            tp = levels.takes[signal.reached_tps]
            signal.reached_tps = nomer
            oxirgimi = nomer == levels.tp_count

            if oxirgimi:
                signal.closed_at = at
                qayd(
                    SignalEventKind.TP2_HIT,
                    SignalStatus.TP2_HIT,
                    f"TP{nomer} — yakuniy nishonga yetdi ({price:g}), signal yopildi.",
                )
            elif nomer == 1:
                qayd(
                    SignalEventKind.TP1_HIT,
                    SignalStatus.TP1_HIT,
                    (
                        f"TP1 darajasiga yetdi ({price:g}), "
                        f"pozitsiyaning {tp.close_pct:g}% i yopildi. "
                        f"🛡 Stopni kirish narxiga ko'taring ({levels.entry:g}) — "
                        "shundan keyin eng yomon holat nolga chiqish bo'ladi."
                    ),
                )
            else:
                qayd(
                    SignalEventKind.TP_PARTIAL,
                    SignalStatus.TP1_HIT,
                    (
                        f"TP{nomer} darajasiga yetdi ({price:g}), "
                        f"yana {tp.close_pct:g}% yopildi. "
                        f"Yakuniy nishon: {levels.final_tp:g}."
                    ),
                )

        return hodisalar

    def _stopni_sur(self, signal: Signal, price: float) -> None:
        """Cho'qqini yangilaydi va Stopni orqadan suradi.

        R = kirish - DASTLABKI Stop. Barcha masofalar shu birlikda:
        foiz coinga bog'liq, R esa har doim "bitta savdodagi xavf".

        Uch qoida:

            1. Surish `activate_at_r` foydadan keyin boshlanadi —
               erta surish oddiy shovqinni Stopga aylantiradi.
            2. Stop cho'qqidan `trail_r` pastda ergashadi.
            3. Stop FAQAT YUQORIGA harakat qiladi. Pastga tushirish
               foydalanuvchi rozi bo'lgan xavfni kattalashtirardi —
               ya'ni signal berilgandagi va'dani buzardi.
        """
        if not self._trailing.enabled or signal.status is SignalStatus.PENDING:
            return

        signal.peak_price = (
            price if signal.peak_price is None else max(signal.peak_price, price)
        )

        levels = signal.levels
        xavf = levels.entry - levels.stop
        if xavf <= 0:
            return

        if signal.peak_price - levels.entry < xavf * self._trailing.activate_at_r:
            return

        yangi = signal.peak_price - xavf * self._trailing.trail_r
        if signal.trailing_stop is None or yangi > signal.trailing_stop:
            signal.trailing_stop = yangi

    def _is_false_signal(self, signal: Signal, at: datetime) -> bool:
        """3.8-band: faol bo'lgach tez Stop yeganmi."""
        if signal.activated_at is None:
            return False
        return at - signal.activated_at <= self._false_signal_window


def kuzatuvchi_qur(config: AppConfig) -> SignalTracker:
    """Sozlamadan `SignalTracker` quradi — JONLI TIZIM VA BACKTEST UCHUN.

    NIMA UCHUN FABRIKA. Ilgari kuzatuvchi ikki joyda alohida
    qurilardi: `bot/services/watcher.py` va `core/backtest/engine.py`.
    Ikkalasi ham `max_holding` ni o'zi hisoblar, `false_signal_window`
    ni esa IKKALASI HAM uzatmasdi — `postmortem.false_signal_window_minutes`
    sozlamasi butunlay o'lik edi va tracker qattiq yozilgan bir soatni
    ishlatardi.

    Endi manba bitta: sozlama o'zgarsa ikkala tomon ham o'zgaradi.
    """
    soat = config.trade_rules.max_holding_hours
    return SignalTracker(
        false_signal_window=timedelta(
            minutes=config.postmortem.false_signal_window_minutes
        ),
        max_holding=timedelta(hours=soat) if soat > 0 else None,
        trailing=config.trade_rules.trailing_stop,
    )
