"""Signal xabarlarini Telegram uchun formatlash.

Shablon `bot/i18n/uz.json` -> `signal.kartochka` da saqlanadi (1.1-band:
matnlar kodga qattiq yozilmaydi). Bu modul faqat qiymatlarni tayyorlaydi.

"Miqdor" maydoni `core/position_sizing/` natijasi bilan to'g'ridan-to'g'ri
bog'lanadi: foydalanuvchi balansini kiritgach avtomatik to'ladi, kiritmagan
bo'lsa o'rniga taklif matni ko'rsatiladi.
"""

from __future__ import annotations

from bot.i18n import DEFAULT_LANGUAGE, t
from core.analysis.support_resistance import RangePosition
from core.domain.models import EntryPlan, PositionSuggestion, SignalLevels


def format_price(value: float) -> str:
    """Narxni coin miqyosiga mos aniqlikda ko'rsatadi.

    Arzon coinlarda (masalan $0.00042) ikki xona yetarli emas, qimmatlarida
    (masalan $67,000) esa olti xona ortiqcha.
    """
    if value >= 1000:
        return f"{value:,.2f}"
    if value >= 1:
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return f"{value:.8f}".rstrip("0").rstrip(".")


def format_pct(value: float, signed: bool = True) -> str:
    return f"{value:+.2f}%" if signed else f"{value:.2f}%"


def render_signal_card(
    symbol: str,
    levels: SignalLevels,
    entry_plan: EntryPlan,
    suggestion: PositionSuggestion | None = None,
    quote_asset: str = "USDT",
    language: str = DEFAULT_LANGUAGE,
    range_position: RangePosition | None = None,
    tp1_close_pct: float = 50.0,
) -> str:
    """5.1.0-banddagi signal-kartochkani chiqaradi.

    Args:
        suggestion: pozitsiya hajmi tavsiyasi. `None` bo'lsa (foydalanuvchi
            balansini kiritmagan) "Miqdor" o'rniga taklif matni ko'rsatiladi.
        range_position: Discount/Premium joylashuvi (3.1-band). Berilsa,
            kartochka oxiriga zona qatori qo'shiladi — foydalanuvchi narx
            arzon yoki qimmat ekanini ko'radi.
    """
    if suggestion is not None and suggestion.position_size_usd > 0:
        amount = f"${format_price(suggestion.position_size_usd)}"
    else:
        amount = t("signal.miqdor_hisoblanmagan", language)

    kartochka = t(
        "signal.kartochka",
        language,
        symbol=symbol.upper(),
        quote=quote_asset.upper(),
        order_emoji=entry_plan.order_type.emoji,
        order_label=entry_plan.order_type.label_uz,
        entry=format_price(entry_plan.entry_price),
        amount=amount,
        tp1=format_price(levels.tp1),
        tp1_pct=format_pct(levels.tp1_distance_pct),
        tp2=format_price(levels.tp2),
        tp2_pct=format_pct(levels.tp2_distance_pct),
        stop=format_price(levels.stop),
        stop_pct=format_pct(-levels.stop_distance_pct),
        share=f"{tp1_close_pct:.0f}",
    )
    # Xavfni PUL bilan ko'rsatish — foizdan ko'ra tushunarli. Balans
    # kiritilmagan bo'lsa hisoblab bo'lmaydi, o'shanda qator qo'shilmaydi.
    if suggestion is not None and suggestion.risk_amount_usd > 0:
        kartochka += "\n\n" + t(
            "signal.xavf_puli",
            language,
            risk=f"−${suggestion.risk_amount_usd:,.2f}",
        )

    if range_position is not None:
        kartochka += f"\n📍 {range_position.describe()}"
    return kartochka
