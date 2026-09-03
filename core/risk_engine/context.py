"""Risk Engine qaror qabul qilishi uchun kerakli barcha holat.

Nima uchun alohida obyekt: 4-bo'limdagi 10 ta qoida bir-biriga bog'liq
ma'lumot talab qiladi (bozor salomatligi, ochiq signallar, kunlik zarar,
narx yangiligi). Ularni bitta kontekstga yig'ish qoidalarni SOF funksiyaga
aylantiradi — har biri mustaqil test qilinadi (0.3-band).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.domain.enums import HealthBand
from core.domain.models import MarketHealth, Signal


@dataclass(slots=True)
class RiskContext:
    """Signal nomzodini baholash uchun tizimning hozirgi holati."""

    now: datetime
    open_signals: list[Signal] = field(default_factory=list)

    # 3.7 — markaziy indeks. `None` bo'lsa fail-safe: signal berilmaydi.
    market_health: MarketHealth | None = None

    # 4.1 — bugungi/haftalik realizatsiya qilingan zarar (balansdan foizda,
    # agregat). 5-bo'limdagi kunlik byudjet bilan BITTA manba.
    daily_loss_pct: float = 0.0
    weekly_loss_pct: float = 0.0

    # 4.5 — BTC 24 soatlik o'zgarishi, foizda
    btc_change_24h_pct: float | None = None

    # 4.4/4.6 — nomzod coin bo'yicha bozor rejimi
    adx: float | None = None
    atr_pct: float | None = None

    # 4.7 — kill switch holati (inson tekshirmaguncha o'chmaydi)
    kill_switch_active: bool = False
    kill_switch_reason: str | None = None

    # 3.8 — ketma-ket Stop soni
    consecutive_stops: int = 0
    consecutive_stop_until: datetime | None = None

    # 6.2 — narx oqimi yangiligi (sekundlarda). Eskirgan bo'lsa signal yo'q.
    price_age_seconds: float | None = None

    # 0.3 — nomzod coinning joriy narxi. `None` bo'lsa zona
    # yaxlitligi tekshirilmaydi (fail-safe emas: narx yo'qligi
    # boshqa qoidada `price_age_seconds` orqali ushlanadi).
    current_price: float | None = None

    @property
    def health_band(self) -> HealthBand | None:
        return self.market_health.band if self.market_health else None

    def open_symbols(self) -> set[str]:
        return {s.correlation_symbol for s in self.open_signals}
