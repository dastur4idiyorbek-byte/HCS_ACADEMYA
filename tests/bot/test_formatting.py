"""5.1.0-band: signal-kartochka shabloni."""

from __future__ import annotations

from bot.formatting import format_pct, format_price, render_signal_card
from core.analysis import decide_entry_plan
from core.config.schema import EntryOrderConfig, PositionSizingConfig
from core.domain.models import SignalLevels
from core.position_sizing import PositionSizer

KONFIG = EntryOrderConfig()


def darajalar() -> SignalLevels:
    return SignalLevels(entry=2450.0, stop=2431.4, tp1=2523.5, tp2=2560.0)


def test_kartochka_spetsifikatsiya_tuzilishiga_mos() -> None:
    reja = decide_entry_plan(2478.0, darajalar(), KONFIG)
    kartochka = render_signal_card("eth", darajalar(), reja)

    assert "ETH/USDT" in kartochka
    assert "KIRISH narxi" in kartochka, "narvon kirish nuqtasini ko'rsatishi kerak"
    assert "OCO" in kartochka, "chiqish buyurtmasi turi aytilishi kerak"
    assert "1-OCO" in kartochka and "2-OCO" in kartochka, (
        "ikkala OCO ham ko'rsatilishi kerak"
    )
    assert "50%" in kartochka, "har bir OCO ning ulushi ko'rsatilishi kerak"
    # Narvon: har bir daraja BIR MARTA ko'rsatiladi, OCO tegishliligi
    # yonida yoziladi — raqamlar takrorlanmaydi.
    assert kartochka.count("🎯") == 2, "ikkita TP"
    assert kartochka.count("🛑") == 1, "Stop bir marta, 'ikkalasida' deb belgilanadi"
    assert "ikkalasida" in kartochka


def test_limit_va_market_kartochkada_korinadi() -> None:
    kutish = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    darhol = render_signal_card("ETH", darajalar(), decide_entry_plan(2451.0, darajalar(), KONFIG))

    assert "📌" in kutish, "Limit uchun 📌 kutilgan"
    assert "⚡" in darhol, "Market uchun ⚡ kutilgan"


def test_limit_kartochkasida_entry_narxi_korsatiladi() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    assert "2,450" in kartochka, "Limit buyurtma Entry narxida qo'yiladi"


def test_market_kartochkasida_joriy_narx_korsatiladi() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2451.0, darajalar(), KONFIG))
    assert "2,451" in kartochka


def test_miqdor_pozitsiya_hisobidan_toladi() -> None:
    """"Miqdor" maydoni core/position_sizing natijasi bilan bog'lanadi."""
    sizer = PositionSizer(PositionSizingConfig())
    byudjet = sizer.budget_for(1200)
    taklif = sizer.suggest("ETH", darajalar(), byudjet)

    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG), taklif)
    assert "$" in kartochka.split("Miqdor")[1].split("\n")[0]


def test_balans_kiritilmagan_bolsa_taklif_korsatiladi() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    assert "balansingizni kiriting" in kartochka


def test_stop_manfiy_foiz_bilan_korsatiladi() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    stop_qatori = next(q for q in kartochka.splitlines() if "🛑" in q)
    assert "-0." in stop_qatori


def test_arzon_coin_narxi_kesilmaydi() -> None:
    arzon = SignalLevels(entry=0.00042, stop=0.0004167, tp1=0.0004347, tp2=0.000441)
    kartochka = render_signal_card("PEPE", arzon, decide_entry_plan(0.00043, arzon, KONFIG))
    assert "0.0004" in kartochka, "arzon coin narxi nolga aylanmasligi kerak"


def test_narx_formatlash() -> None:
    assert format_price(67432.1234) == "67,432.12"
    assert format_price(2.5) == "2.5"
    assert format_price(0.00042) == "0.00042"


def test_foiz_formatlash() -> None:
    assert format_pct(3.0) == "+3.00%"
    assert format_pct(-0.8) == "-0.80%"
    assert format_pct(3.0, signed=False) == "3.00%"


def test_kartochkada_zona_qatori_korsatiladi() -> None:
    """3.1-band davomi: foydalanuvchi narx arzon yoki qimmat ekanini ko'radi."""
    from core.analysis.support_resistance import compute_range_position
    from core.domain.enums import ZoneKind
    from core.domain.models import SRZone

    support = SRZone(ZoneKind.SUPPORT, low=2400, high=2440, touches=3)
    resistance = SRZone(ZoneKind.RESISTANCE, low=2600, high=2640, touches=3)
    joy = compute_range_position(2460, support, resistance)

    kartochka = render_signal_card(
        "ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG), range_position=joy
    )
    assert "📍" in kartochka
    assert "Discount" in kartochka


def test_zona_qatori_ixtiyoriy() -> None:
    kartochka = render_signal_card("ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG))
    assert "📍" not in kartochka


# --------------------------------------------------------------------------- #
#  Belgi tizimi — bitta belgi, bitta ma'no
# --------------------------------------------------------------------------- #


def test_bitta_belgi_bitta_manoda() -> None:
    """Avval 🎯 ham TP, ham Limit buyurtma edi — kartochka o'qilmasdi.

    Bu test aynan shu chalkashlikni qaytib kelishidan saqlaydi.
    """
    from core.domain.enums import OrderType, SignalStatus

    buyurtma_belgilari = {tur.emoji for tur in OrderType}
    holat_belgilari = {holat.emoji for holat in SignalStatus}

    assert "🎯" not in buyurtma_belgilari, "🎯 faqat foyda nuqtasi uchun"
    assert len(buyurtma_belgilari) == len(OrderType), "har bir tur o'z belgisiga ega"
    assert len(holat_belgilari) == len(SignalStatus), "har bir holat o'z belgisiga ega"


def test_kartochka_nima_qilishni_aytadi() -> None:
    """Foydalanuvchi raqamlarni emas, HARAKATNI ko'rishi kerak."""
    from core.domain.enums import OrderType

    assert "oling" in OrderType.MARKET.label_uz.lower()
    assert "buyurtma" in OrderType.LIMIT.label_uz.lower()


def test_xavf_pul_bilan_korsatiladi() -> None:
    """Foiz mavhum — pul aniq."""
    from core.domain.models import PositionSuggestion

    lv = darajalar()
    kartochka = render_signal_card(
        "ETH",
        lv,
        decide_entry_plan(lv.entry, lv, KONFIG),
        suggestion=PositionSuggestion(
            symbol="ETH",
            balance=1000.0,
            daily_risk_pct=3.0,
            daily_budget_usd=30.0,
            remaining_budget_usd=27.28,
            risk_amount_usd=2.72,
            position_size_usd=340.0,
            entry=lv.entry,
            stop_distance_pct=0.76,
            units=0.1388,
            within_daily_limit=True,
        ),
    )

    assert "2.72" in kartochka
    assert "Stop ishlasa" in kartochka


# --------------------------------------------------------------------------- #
#  Sarlavha va holat — BITTA manba (34.1-bo'lim)
# --------------------------------------------------------------------------- #


def test_holat_berilsa_harakat_qatori_shundan_olinadi() -> None:
    """ENG MUHIM: bitta xabarda ikkita qarama-qarshi gap bo'lmasin.

    Avval harakat qatori buyurtma turidan ("Hozir oling"), holat esa
    kuzatuvchidan ("Kutilmoqda") kelardi — ikki alohida manba. Natijada
    narx kirish nuqtasiga yetmagan bo'lsa ham kartochka "Hozir oling"
    derdi.
    """
    from core.domain.enums import SignalStatus

    lv = darajalar()
    # Narx Entry'dan YUQORIDA -> buyurtma turi Limit bo'lishi kerak edi,
    # lekin holat aniq: kutilmoqda.
    reja = decide_entry_plan(lv.entry * 1.02, lv, KONFIG)

    kutilmoqda = render_signal_card("ETH", lv, reja, status=SignalStatus.PENDING)
    sotib_olingan = render_signal_card("ETH", lv, reja, status=SignalStatus.ACTIVE)

    assert "Kutilmoqda" in kutilmoqda
    assert "Hozir oling" not in kutilmoqda, "zid gap bo'lmasligi kerak"
    assert "sotib olingan" in sotib_olingan.lower()


def test_holat_berilmasa_buyurtma_turidan_olinadi() -> None:
    """Yangi signal — hali kuzatilmagan, holat yo'q."""
    lv = darajalar()

    darhol = render_signal_card("ETH", lv, decide_entry_plan(lv.entry, lv, KONFIG))
    kutish = render_signal_card(
        "ETH", lv, decide_entry_plan(lv.entry * 1.02, lv, KONFIG)
    )

    assert "⚡" in darhol
    assert "📌" in kutish


def test_belgi_takrorlanmaydi() -> None:
    """Holat matnida belgi bor — kartochka uni ikkinchi marta qo'ymaydi."""
    from core.domain.enums import SignalStatus

    lv = darajalar()
    kartochka = render_signal_card(
        "ETH", lv, decide_entry_plan(lv.entry, lv, KONFIG), status=SignalStatus.PENDING
    )

    assert "⏳ ⏳" not in kartochka


# --------------------------------------------------------------------------- #
#  Narx narvoni
# --------------------------------------------------------------------------- #


def test_narvon_darajalarni_tartib_bilan_korsatadi() -> None:
    """Yuqoridan pastga: TP2 -> TP1 -> kirish -> Stop."""
    from bot.formatting import render_price_ladder

    lv = darajalar()
    qatorlar = render_price_ladder(lv).splitlines()

    assert len(qatorlar) == 4
    assert "TP2" in qatorlar[0]
    assert "TP1" in qatorlar[1]
    assert "KIRISH" in qatorlar[2]
    assert "Stop" in qatorlar[3]


def test_narvon_hozirgi_narxni_oz_orniga_qoyadi() -> None:
    """Narx qayerda turgani bir qarashda ko'rinishi kerak."""
    from bot.formatting import render_price_ladder

    lv = darajalar()

    yuqorida = render_price_ladder(lv, current_price=lv.entry * 1.01).splitlines()
    pastda = render_price_ladder(lv, current_price=(lv.entry + lv.stop) / 2).splitlines()

    # Narx kirishdan yuqorida -> narvonda kirishdan OLDIN turadi
    assert "hozirgi" in yuqorida[2] and "KIRISH" in yuqorida[3]
    # Narx kirishdan pastda -> kirishdan KEYIN turadi
    assert "KIRISH" in pastda[2] and "hozirgi" in pastda[3]


def test_narvon_kirish_narxida_takrorlanmaydi() -> None:
    """Joriy narx kirish narxiga teng bo'lsa, ikkita bir xil qator chiqmaydi."""
    from bot.formatting import render_price_ladder

    lv = darajalar()
    qatorlar = render_price_ladder(lv, current_price=lv.entry).splitlines()

    assert len(qatorlar) == 4
