"""5.1.0-band: signal-kartochka shabloni."""

from __future__ import annotations

from bot.formatting import format_pct, format_price, render_signal_card
from core.analysis import decide_entry_plan
from core.config.schema import EntryOrderConfig, PositionSizingConfig
from core.domain.models import SignalLevels, signal_levels
from core.position_sizing import PositionSizer

KONFIG = EntryOrderConfig()


def darajalar() -> SignalLevels:
    return signal_levels(entry=2450.0, stop=2431.4, tp1=2523.5, tp2=2560.0)


def test_kartochka_shabloni_toliq() -> None:
    """Shablon: coin -> harakat -> darajalar -> xulosa -> sana."""
    reja = decide_entry_plan(2478.0, darajalar(), KONFIG)
    kartochka = render_signal_card("eth", darajalar(), reja)

    assert "ETH/USDT" in kartochka
    assert "Kirish" in kartochka
    assert "Stop" in kartochka
    assert "TP1" in kartochka and "TP2" in kartochka
    assert "Risk/Foyda" in kartochka, "qaror uchun asosiy raqam"
    assert "50%" in kartochka, "har bir TP da qancha sotilishi"
    assert kartochka.count("🎯") == 2, "ikkita TP"
    assert kartochka.count("🛑") == 1, "Stop bir marta"


def test_kartochkada_birja_jargoni_yoq() -> None:
    """"OCO" — birja atamasi. Signal o'quvchi uni bilishi shart emas,
    shuning uchun kartochkadan olib tashlangan: uning o'rniga "Stop
    butun pozitsiyani yopadi" degan oddiy gap turadi."""
    kartochka = render_signal_card(
        "ETH", darajalar(), decide_entry_plan(2478.0, darajalar(), KONFIG)
    )
    assert "OCO" not in kartochka
    assert "butun pozitsiyani yopadi" in kartochka


def test_kartochkada_sana_va_vaqt_bor() -> None:
    """Foydalanuvchi signal QACHON berilganini ko'rishi kerak."""
    from datetime import UTC, datetime

    kartochka = render_signal_card(
        "ETH",
        darajalar(),
        decide_entry_plan(2478.0, darajalar(), KONFIG),
        created_at=datetime(2026, 8, 28, 10, 45, tzinfo=UTC),
    )
    assert "28.08.2026" in kartochka
    assert "10:45 UTC" in kartochka


def test_narx_qatori_kontekstga_qarab_nomlanadi() -> None:
    """Bitta maydon, ikki ma'no bo'lib qolmasin.

    Yangi signalda narx — signal berilgan lahzaniki. Foydalanuvchi eski
    signalni ochganda esa narx shu lahzada birjadan olinadi. Ikkalasini
    bir xil nomlash o'quvchini adashtirardi: raqam qachonga tegishli
    ekani bilinmasdi.
    """
    from core.domain.enums import SignalStatus

    lv = darajalar()
    reja = decide_entry_plan(lv.entry * 1.01, lv, KONFIG)

    yangi = render_signal_card("ETH", lv, reja)
    ochilgan = render_signal_card("ETH", lv, reja, status=SignalStatus.PENDING)

    assert "Signal narxi" in yangi and "Hozirgi narx" not in yangi
    assert "Hozirgi narx" in ochilgan and "Signal narxi" not in ochilgan


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
    arzon = signal_levels(entry=0.00042, stop=0.0004167, tp1=0.0004347, tp2=0.000441)
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


def test_darajalar_mantiqiy_tartibda() -> None:
    """Kirish -> Stop -> TP1 -> TP2.

    Avval narvon NARX bo'yicha saralanardi (TP2 -> TP1 -> kirish ->
    Stop) va o'rtasiga "hozirgi narx" qatori tushardi. Natijada to'rt
    bir xil ko'rinishdagi qator aralashib ketardi va qaysi raqam nima
    ekani darrov bilinmasdi. Endi tartib O'QISH tartibi: avval nima
    qilish, keyin qayerda to'xtash, keyin qayerda sotish.
    """
    from bot.formatting import render_levels

    qatorlar = render_levels(darajalar()).splitlines()

    assert len(qatorlar) == 4
    assert "Kirish" in qatorlar[0]
    assert "Stop" in qatorlar[1]
    assert "TP1" in qatorlar[2]
    assert "TP2" in qatorlar[3]


def test_darajalar_ustunlari_tekislanadi() -> None:
    """Raqamlar bir ustunda tursin — telefonda shunda o'qiladi."""
    from bot.formatting import render_levels

    # Narx uzunliklari har xil: 2,450 / 2,431.4 / 2,523.5 / 2,560
    qatorlar = [q.replace("<code>", "").replace("</code>", "")
                for q in render_levels(darajalar()).splitlines()]
    joylar = [q.index(".") for q in qatorlar]
    assert len(set(joylar)) == 1, f"kasr nuqtasi bir ustunda emas: {qatorlar}"


def test_tp_ulushlari_darajalardan_oqiladi() -> None:
    """Ulush DARAJALARNING O'ZIDA turadi, kartochkada hisoblanmaydi.

    Ilgari kartochka "TP2 = 100 dan qolgani" deb o'zi hisoblardi —
    ya'ni TP har doim ikkita degan taxminni yana bir joyda
    takrorlardi. Uchta TP bo'lganda o'sha ayirma noto'g'ri chiqardi.
    """
    from bot.formatting import render_levels
    from core.domain.models import signal_levels

    lv = signal_levels(100.0, 99.0, 103.0, 106.0, shares=(70.0, 30.0))
    blok = render_levels(lv)

    assert "70%" in next(q for q in blok.splitlines() if "TP1" in q)
    assert "30%" in next(q for q in blok.splitlines() if "TP2" in q)


def test_uchta_tp_ham_korinadi() -> None:
    """TP soni qat'iy emas — kartochka uchtasini ham ko'rsatsin."""
    from bot.formatting import render_levels
    from core.domain.models import signal_levels

    blok = render_levels(signal_levels(100.0, 99.0, 102.0, 104.0, 107.0))

    assert any("TP3" in q for q in blok.splitlines())


def test_bitta_tp_bolsa_faqat_bittasi_korinadi() -> None:
    from bot.formatting import render_levels
    from core.domain.models import signal_levels

    blok = render_levels(signal_levels(100.0, 99.0, 105.0))

    assert any("TP1" in q for q in blok.splitlines())
    assert not any("TP2" in q for q in blok.splitlines())
