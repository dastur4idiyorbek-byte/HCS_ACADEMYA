"""Signal xabarlarini Telegram uchun formatlash.

Shablon `bot/i18n/uz.json` -> `signal.kartochka` da saqlanadi (1.1-band:
matnlar kodga qattiq yozilmaydi). Bu modul faqat qiymatlarni tayyorlaydi.

"Miqdor" maydoni `core/position_sizing/` natijasi bilan to'g'ridan-to'g'ri
bog'lanadi: foydalanuvchi balansini kiritgach avtomatik to'ladi, kiritmagan
bo'lsa o'rniga taklif matni ko'rsatiladi.
"""

from __future__ import annotations

from datetime import datetime

from bot.i18n import DEFAULT_LANGUAGE, t
from core.domain.enums import SignalStatus
from core.domain.models import EntryPlan, PositionSuggestion, SignalLevels
from core.utils.time_utils import utc_now


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


def render_levels(
    levels: SignalLevels,
    language: str = DEFAULT_LANGUAGE,
    tp1_close_pct: float = 50.0,
) -> str:
    """Narx darajalari — bitta blok, ustunlari tekislangan.

    TARTIB YUQORIDAN PASTGA EMAS, MANTIQIY: avval nima qilish kerak
    (Kirish), keyin qayerda to'xtash (Stop), keyin qayerda sotish
    (TP1, TP2). Avval narvon narx bo'yicha saralanardi va o'rtasiga
    "hozirgi narx" qatori tushardi — o'quvchi qaysi raqam nima ekanini
    ajrata olmasdi.

    Har bir TP yonida QANCHA ULUSH sotilishi turadi. Avval bu joyda
    "1-OCO 50%" degan jargon bor edi: OCO — birja atamasi, uni signal
    o'quvchining bilishi shart emas.

    TP SONI QAT'IY EMAS — 1, 2 yoki 3 bo'lishi mumkin. Kartochka
    ro'yxatni o'zi bo'ylab yuradi: ilgari bu yerda aynan ikkita qator
    yozib qo'yilgan edi va uchinchi TP jimgina ko'rinmay qolardi.

    `tp1_close_pct` faqat ZAXIRA: ulush endi darajalarning o'zida
    (`TakeProfit.close_pct`) yotadi, ya'ni ekranda ko'ringan raqam
    savdoda ishlatilgani bilan bir xil.
    """
    ulush = lambda x: f"{x:.0f}%"  # noqa: E731

    qatorlar: list[tuple[str, str, float, str, str]] = [
        ("💠", t("signal.daraja_kirish", language), levels.entry, "", ""),
        ("🛑", t("signal.daraja_stop", language), levels.stop,
         format_pct(-levels.stop_distance_pct), ""),
    ]
    for nomer, tp in enumerate(levels.takes, start=1):
        masofa = (tp.price - levels.entry) / levels.entry * 100
        qatorlar.append(
            ("🎯", f"TP{nomer}", tp.price, format_pct(masofa), ulush(tp.close_pct))
        )

    nom_eni = max(len(nom) for _, nom, _, _, _ in qatorlar)
    narx_eni = max(len(format_price(narx)) for _, _, narx, _, _ in qatorlar)
    foiz_eni = max(len(foiz) for _, _, _, foiz, _ in qatorlar)

    return "\n".join(
        "<code>"
        + f"{belgi} {nom:<{nom_eni}}  {format_price(narx):>{narx_eni}}"
        + (f"  {foiz:>{foiz_eni}}" if foiz else "")
        + (f"  {ulushi}" if ulushi else "")
        + "</code>"
        for belgi, nom, narx, foiz, ulushi in qatorlar
    )


def render_summary(  # noqa: PLR0913
    levels: SignalLevels,
    amount: str,
    risk: str | None,
    price: float | None,
    price_is_live: bool,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Kartochkaning pastki bloki — qaror uchun kerakli raqamlar.

    Risk/Foyda nisbati TP2 bo'yicha: signal 3.3-bandda aynan shu
    nisbat bilan tekshiriladi, ya'ni o'quvchi ko'radigan raqam
    tizim qaror qabul qilgan raqam bilan bir xil bo'lishi kerak.

    Narx qatorining NOMI kontekstga qarab o'zgaradi va bu ataylab:

      - yangi signal tarqatilayotganda narx signal berilgan lahzaniki,
        ya'ni "Signal narxi";
      - foydalanuvchi eski signalni ochganda esa narx SHU LAHZADA
        birjadan olinadi, ya'ni "Hozirgi narx".

    Ikkalasini bitta nom bilan atash — bitta maydonni ikki ma'noda
    ishlatish bo'lardi: o'quvchi ko'rgan raqam qachonga tegishli ekanini
    bilmasdi.
    """
    qatorlar: list[tuple[str, str, str]] = [
        ("⚖️", t("signal.xulosa_nisbat", language), f"1 : {levels.risk_reward:.2f}"),
        ("💵", t("signal.xulosa_miqdor", language), amount),
    ]
    if risk is not None:
        qatorlar.append(("📉", t("signal.xulosa_zarar", language), risk))
    if price is not None:
        kalit = "signal.xulosa_hozirgi" if price_is_live else "signal.xulosa_narx"
        qatorlar.append(("📊", t(kalit, language), format_price(price)))

    nom_eni = max(len(nom) for _, nom, _ in qatorlar)
    return "\n".join(
        f"<code>{belgi} {nom:<{nom_eni}}  {qiymat}</code>"
        for belgi, nom, qiymat in qatorlar
    )


def render_signal_card(  # noqa: PLR0913
    symbol: str,
    levels: SignalLevels,
    entry_plan: EntryPlan,
    suggestion: PositionSuggestion | None = None,
    quote_asset: str = "USDT",
    language: str = DEFAULT_LANGUAGE,
    tp1_close_pct: float = 50.0,
    status: SignalStatus | None = None,
    created_at: datetime | None = None,
) -> str:
    """5.1.0-banddagi signal-kartochka.

    TUZILISHI (yuqoridan pastga — o'qish tartibi ham shu):

        📡 COIN/USDT              — nima haqida
        📌 harakat qatori         — nima qilish kerak
        ─────────
        💠 Kirish / 🛑 Stop / 🎯 TP1 / 🎯 TP2 — qaysi narxda
        ─────────
        ⚖️ Risk/Foyda, 💵 Miqdor, 📉 Stop ishlasa — qaror uchun raqamlar
        🔸 Stop butun pozitsiyani yopadi
        🗓 sana va vaqt

    Avvalgi ko'rinish "narx narvoni" edi: darajalar NARX bo'yicha
    saralanardi va o'rtasiga hozirgi narx qatori tushardi. Natijada
    Kirish, Stop va TP bir xil ko'rinishdagi to'rt qatorga aralashib
    ketardi va qaysi raqam nima ekani darrov bilinmasdi.

    Args:
        suggestion: pozitsiya hajmi tavsiyasi. `None` bo'lsa (foydalanuvchi
            balansini kiritmagan) "Miqdor" o'rniga taklif matni ko'rsatiladi.
        status: signal holati. Berilsa, harakat qatori AYNAN SHUNDAN
            olinadi. Nima uchun muhim: avval harakat qatori ("Hozir
            oling") buyurtma turidan, holat esa ("Kutilmoqda")
            kuzatuvchidan kelardi — ikki alohida manba, natijada bitta
            xabarda ikkita qarama-qarshi gap chiqardi. Endi holat
            ma'lum bo'lsa u YAGONA manba.
        created_at: signal berilgan vaqt. Berilmasa — hozir.
    """
    if suggestion is not None and suggestion.position_size_usd > 0:
        amount = f"${format_price(suggestion.position_size_usd)}"
    else:
        amount = t("signal.miqdor_hisoblanmagan", language)

    # Xavfni PUL bilan ko'rsatish — foizdan ko'ra tushunarli. Balans
    # kiritilmagan bo'lsa hisoblab bo'lmaydi, o'shanda qator chiqmaydi.
    if suggestion is not None and suggestion.risk_amount_usd > 0:
        risk = f"−${suggestion.risk_amount_usd:,.2f}"
    else:
        risk = None

    # Harakat qatori: holat ma'lum bo'lsa — o'shandan, aks holda (yangi
    # signal, hali kuzatilmagan) buyurtma turidan.
    if status is not None:
        # Holat matnining o'zida belgi bor — takrorlanmasin.
        harakat_emoji = ""
        harakat_matni = t(f"signal.holat_{status.value}", language)
    else:
        harakat_emoji = f"{entry_plan.order_type.emoji} "
        harakat_matni = entry_plan.order_type.label_uz

    # Joriy narx kirish narxiga juda yaqin bo'lsa ko'rsatilmaydi —
    # ikkita bir xil raqam foyda bermaydi.
    narx = entry_plan.current_price
    if narx is not None and abs(narx - levels.entry) <= levels.entry * 1e-4:
        narx = None

    kartochka = t(
        "signal.kartochka",
        language,
        symbol=symbol.upper(),
        quote=quote_asset.upper(),
        order_emoji=harakat_emoji,
        order_label=harakat_matni,
        levels=render_levels(levels, language=language, tp1_close_pct=tp1_close_pct),
        xulosa=render_summary(
            levels, amount, risk, narx, price_is_live=status is not None,
            language=language,
        ),
    )

    kartochka += "\n\n" + t("signal.izoh_stop", language)

    vaqt = created_at or utc_now()
    kartochka += "\n" + t(
        "signal.sana", language, sana=vaqt.strftime("%d.%m.%Y · %H:%M UTC")
    )
    return kartochka
