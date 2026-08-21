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
from core.domain.enums import SignalStatus
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


def render_price_ladder(
    levels: SignalLevels,
    current_price: float | None = None,
    language: str = DEFAULT_LANGUAGE,
    tp1_close_pct: float = 50.0,
) -> str:
    """Narx narvoni — barcha darajalar tartib bilan, yuqoridan pastga.

    Nima uchun kerak: raqamlar ro'yxati "narx qayerda turibdi" degan
    savolga javob bermaydi. Narvon buni bir qarashda ko'rsatadi —
    ayniqsa narx hali kirish nuqtasiga yetmagan bo'lsa.

    Joriy narx berilsa, u o'z o'rniga qo'yiladi va strelka bilan
    belgilanadi.
    """
    ulush = f"{tp1_close_pct:.0f}%"
    qatorlar: list[tuple[float, str, str]] = [
        (levels.tp2, "🎯", f"TP2  {format_pct(levels.tp2_distance_pct):>6}  2-OCO {ulush}"),
        (levels.tp1, "🎯", f"TP1  {format_pct(levels.tp1_distance_pct):>6}  1-OCO {ulush}"),
        (levels.entry, "▪", t("signal.narvon_kirish", language)),
        (
            levels.stop,
            "🛑",
            f"Stop {format_pct(-levels.stop_distance_pct):>6}  "
            + t("signal.narvon_ikkala_oco", language),
        ),
    ]

    # Joriy narx kirish narxidan sezilarli farq qilsagina ko'rsatiladi —
    # aks holda ikkita bir xil qator chiqadi.
    if current_price is not None and abs(current_price - levels.entry) > levels.entry * 1e-4:
        qatorlar.append((current_price, "▶", t("signal.narvon_hozir", language)))

    qatorlar.sort(key=lambda q: q[0], reverse=True)
    eng_uzun = max(len(format_price(narx)) for narx, _, _ in qatorlar)

    return "\n".join(
        f"<code>{belgi} {format_price(narx):>{eng_uzun}}  {izoh}</code>"
        for narx, belgi, izoh in qatorlar
    )


def render_signal_card(
    symbol: str,
    levels: SignalLevels,
    entry_plan: EntryPlan,
    suggestion: PositionSuggestion | None = None,
    quote_asset: str = "USDT",
    language: str = DEFAULT_LANGUAGE,
    range_position: RangePosition | None = None,
    tp1_close_pct: float = 50.0,
    status: SignalStatus | None = None,
) -> str:
    """5.1.0-banddagi signal-kartochkani chiqaradi.

    Args:
        suggestion: pozitsiya hajmi tavsiyasi. `None` bo'lsa (foydalanuvchi
            balansini kiritmagan) "Miqdor" o'rniga taklif matni ko'rsatiladi.
        range_position: Discount/Premium joylashuvi (3.1-band). Berilsa,
            kartochka oxiriga zona qatori qo'shiladi — foydalanuvchi narx
            arzon yoki qimmat ekanini ko'radi.
        status: signal holati. Berilsa, harakat qatori AYNAN SHUNDAN
            olinadi. Nima uchun muhim: avval harakat qatori ("Hozir
            oling") buyurtma turidan, holat esa ("Kutilmoqda")
            kuzatuvchidan kelardi — ikki alohida manba, natijada bitta
            xabarda ikkita qarama-qarshi gap chiqardi. Endi holat
            ma'lum bo'lsa u YAGONA manba.
    """
    if suggestion is not None and suggestion.position_size_usd > 0:
        amount = f"${format_price(suggestion.position_size_usd)}"
    else:
        amount = t("signal.miqdor_hisoblanmagan", language)

    # Harakat qatori: holat ma'lum bo'lsa — o'shandan, aks holda (yangi
    # signal, hali kuzatilmagan) buyurtma turidan.
    if status is not None:
        # Holat matnining o'zida belgi bor — takrorlanmasin.
        harakat_emoji = ""
        harakat_matni = t(f"signal.holat_{status.value}", language)
    else:
        harakat_emoji = f"{entry_plan.order_type.emoji} "
        harakat_matni = entry_plan.order_type.label_uz

    kartochka = t(
        "signal.kartochka",
        language,
        symbol=symbol.upper(),
        quote=quote_asset.upper(),
        order_emoji=harakat_emoji,
        order_label=harakat_matni,
        amount=amount,
        ladder=render_price_ladder(
            levels,
            current_price=entry_plan.current_price,
            language=language,
            tp1_close_pct=tp1_close_pct,
        ),
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
