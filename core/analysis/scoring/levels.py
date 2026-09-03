"""Stop va TP darajalarini qurish (3.1 va 3.3-band birgalikda).

3.1-band tuzilmani belgilaydi:
    Stop — eng yaqin support/ATR asosida
    TP1  — eng yaqin resistance
    TP2  — kamida 1:3 R/R ta'minlaydigan masofa

3.3-band esa qat'iy chegaralar qo'yadi:
    Stop masofasi narxning 1%idan oshmasligi shart
    TP 3%–5% oralig'ida bo'lishi shart

Bu ikkisi tez-tez ZIDDIYATGA kiradi: haqiqiy support 1% dan uzoqroqda
bo'lishi mumkin, yoki eng yaqin resistance 3% dan yaqinroqda. Bunday
holatda daraja "majburlab" qurilmaydi — signal umuman berilmaydi
(0.2-band: "signal bermaslik normal holat").

Shuning uchun `build_levels()` sababni ham qaytaradi: admin nima uchun
signal chiqmaganini ko'ra olishi kerak (3.7-band dashboardi).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.support_resistance import ZoneMap
from core.config.schema import TradeRulesConfig
from core.domain.models import SignalLevels, signal_levels

#: Stop support zonasining pastidan shu ulushdagi ATR masofasida qo'yiladi.
#: Aynan chegaraga qo'yilsa, zonaga tegib qaytish ham Stop'ni ishga tushirardi.
STOP_BUFFER_ATR = 0.25

#: Uchinchi TP TP1 va yakuniy nishonga shu ulushdan yaqin bo'lsa
#: qo'shilmaydi — bir-biriga tiqilgan TP lar alohida ma'no bermaydi.
ORALIQ_TP_CHEKKA = 0.2


@dataclass(frozen=True, slots=True)
class LevelResult:
    """Darajalarni qurish natijasi.

    `levels is None` — qurib bo'lmadi, sababi `reason` da.
    """

    levels: SignalLevels | None
    reason: str
    #: Rad etish bosqichi. Ilgari hammasi bitta "levels" edi va dashboard
    #: "Darajalar risk qoidasiga sig'madi" deb yozardi — Stop JUDA YAQIN
    #: bo'lgani uchunmi yoki JUDA UZOQ bo'lgani uchunmi, ko'rinmasdi.
    #: Ikkalasi qarama-qarshi tuzatish talab qiladi.
    stage: str = "levels"
    #: TP1 haqiqiy resistance zonasidan olinganmi (tuzilmaviy) yoki
    #: o'lchangan masofadan (qarshilik topilmaganda). Bu farq signal
    #: tafsilotida ko'rsatiladi — 3.6-band shaffofligi.
    tp_from_structure: bool = True

    @property
    def ok(self) -> bool:
        return self.levels is not None


def build_levels(
    zone_map: ZoneMap,
    rules: TradeRulesConfig,
    entry_price: float | None = None,
    shares: tuple[float, ...] | None = None,
) -> LevelResult:
    """S/R zonalari va ATR asosida Entry/Stop va TP ro'yxatini quradi.

    TP SONI QAT'IY EMAS. `rules.max_take_profits` — yuqori chegara:
    bozorda nechta haqiqiy nishon bo'lsa, shuncha TP quriladi.

        1 ta — toza ko'tarilish, ustda qarshilik yo'q
        2 ta — odatiy holat
        3 ta — keng diapazon, ketma-ket zonalar

    Args:
        zone_map: aniqlangan zonalar (6-bosqich).
        rules: 3.3-banddagi universal chegaralar.
        entry_price: kirish narxi. Berilmasa joriy narx ishlatiladi.
        shares: har bir TP da yopiladigan ulush
            (`portfolio.tp_close_shares`). Berilmasa domendagi
            standart jadval ishlatiladi.
    """
    entry = entry_price if entry_price is not None else zone_map.price
    if entry <= 0:
        return LevelResult(None, "Kirish narxi musbat bo'lishi kerak")

    support = zone_map.nearest_support()
    if support is None:
        return LevelResult(None, "Narxdan pastda support zonasi topilmadi")

    stop_natija = _build_stop(entry, support.low, zone_map.atr, rules)
    if stop_natija is None:
        masofa = (entry - _stop_narxi(entry, support.low, zone_map.atr, rules)) / entry * 100
        yaqinmi = masofa < rules.min_stop_distance_pct
        tomon = "yaqin" if yaqinmi else "uzoq"
        return LevelResult(
            None,
            f"Stop juda {tomon}: {masofa:.2f}% da qolardi "
            f"(ATR×{rules.stop_atr_mult} va support tuzilmasidan), "
            f"ruxsat {rules.min_stop_distance_pct}–{rules.max_stop_distance_pct}%",
            stage="levels:stop_too_close" if yaqinmi else "levels:stop_too_far",
        )
    return build_levels_with_stop(
        zone_map, rules, entry, stop_natija, shares=shares
    )


def build_levels_with_stop(
    zone_map: ZoneMap,
    rules: TradeRulesConfig,
    entry: float,
    stop: float,
    shares: tuple[float, ...] | None = None,
) -> LevelResult:
    """Stop TASHQARIDAN berilganda TP larni quradi.

    NIMA UCHUN AJRATILDI. `build_levels` Stop'ni support zonasidan
    hisoblaydi — bu `classic_ta` ning usuli. Narx harakati
    strategiyasida esa Stop NAQSHDAN keladi: "oldingi pastki
    nuqtadan pastroqda" (kitobning qoidasi).

    Ikki joyda alohida TP qurilsa ular ajralib ketardi — loyihada
    bu xato besh marta uchragan (`docs/ARXITEKTURA.md`, 68-bo'lim).
    Shuning uchun TP mantig'i BITTA joyda qoladi, faqat Stop
    manbai boshqacha.
    """
    if entry <= 0 or stop <= 0 or stop >= entry:
        return LevelResult(None, "Stop kirish narxidan past bo'lishi kerak")

    stop_masofa_pct = (entry - stop) / entry * 100

    tp1_natija = _build_tp1(entry, zone_map, rules, stop_masofa_pct)
    tuzilmaviy_tp = tp1_natija is not None

    if tp1_natija is None:
        if not rules.allow_measured_tp:
            return LevelResult(
                None,
                f"Mos resistance topilmadi: TP1 {rules.min_tp_distance_pct}–"
                f"{rules.max_tp_distance_pct}% oralig'ida bo'lishi kerak",
                tp_from_structure=False,
            )
        # Toza ko'tarilish trendida ustda qarshilik bo'lmaydi — TP1
        # o'lchangan masofa bo'yicha qo'yiladi.
        #
        # Masofa STOP bilan bog'lanadi: TP1 da pozitsiyaning bir qismi
        # yopiladi, shuning uchun uning o'zi ham foydali nisbatda
        # bo'lishi kerak. Aks holda Stop 5% bo'lganda TP1 3% da qolib,
        # o'sha qism 1:0.6 nisbatda — zararli savdo bo'lardi.
        olchangan_pct = max(
            rules.min_tp_distance_pct if rules.enforce_distance_bands else 0.0,
            stop_masofa_pct * rules.tp1_min_risk_reward,
        )
        tp1_natija = entry * (1 + olchangan_pct / 100)
    tp1 = tp1_natija

    if rules.tp2_from_structure:
        yakuniy = _build_tp2_tuzilmadan(entry, tp1, stop_masofa_pct, zone_map, rules)
        if yakuniy is None:
            return LevelResult(
                None,
                "TP1 dan yuqorida mos resistance zonasi yo'q "
                f"(1:{rules.tp2_structural_min_rr:g} nisbat va "
                f"{rules.max_tp_distance_pct}% chegarasi ichida)",
                stage="levels:tp2_no_structure",
                tp_from_structure=tuzilmaviy_tp,
            )
        yakuniy_tuzilmaviy = True
    else:
        # TP1 ning O'ZI 1:N shartini bajarsa, IKKINCHI nishon yo'q.
        #
        # Ilgari bu yerda `tp1 * 1.001` turardi — ya'ni TP2 TP1 dan
        # 0.1% yuqoriga qo'yilardi. Bunday "ikkinchi nishon" mavjud
        # emas: 0.1% yo'l kelib-ketish xarajatini (0.3%) ham
        # qoplamaydi, kartochkada esa ikkita deyarli bir xil narx
        # ko'rinardi (TP1 130.00, TP2 130.13).
        #
        # Loyiha egasining qoidasi shu holatga aynan mos keladi:
        # "2 TP MAJBURIY EMAS — 1, 2 yoki 3 bo'lishi mumkin,
        # SHAROITGA QARAB". Sharoit shu: nishon bitta.
        #
        # TP1 nisbat poli yoqilgach bu holat tez-tez uchraydi —
        # tuzilmaviy TP1 ko'pincha 1:3 darajasidan ham uzoqda
        # bo'ladi.
        kerakli_nishon = entry * (1 + stop_masofa_pct * rules.min_risk_reward / 100)
        if kerakli_nishon <= tp1:
            return _bitta_nishon(entry, stop, tp1, tuzilmaviy_tp, rules)

        yakuniy = _build_tp2(entry, tp1, stop_masofa_pct, rules)
        if yakuniy is None:
            kerak = rules.min_risk_reward * stop_masofa_pct
            return LevelResult(
                None,
                f"1:{rules.min_risk_reward:.0f} R/R uchun TP {kerak:.2f}% da bo'lishi kerak, "
                f"lekin chegara {rules.max_tp_distance_pct}%",
                tp_from_structure=tuzilmaviy_tp,
            )
        yakuniy_tuzilmaviy = False

    narxlar, manbalar = _tp_royxati(
        entry, tp1, yakuniy, tuzilmaviy_tp, yakuniy_tuzilmaviy, zone_map, rules
    )

    try:
        levels = signal_levels(
            entry,
            stop,
            *narxlar,
            shares=tuple(shares) if shares else None,
            from_structure=manbalar,
        )
    except ValueError as exc:
        # NOMLI argument SHART: uchinchi pozitsion argument `stage`,
        # unga bool uzatilsa bosqich "classic_ta:True" bo'lib chiqadi
        # va voronkada umuman sanalmaydi.
        return LevelResult(
            None,
            f"Darajalar tartibi buzildi: {exc}",
            stage="levels:tartib_buzildi",
            tp_from_structure=tuzilmaviy_tp,
        )

    izoh = (
        f"Darajalar S/R va ATR asosida qurildi ({len(narxlar)} ta TP)"
        if tuzilmaviy_tp
        else "Stop S/R asosida; TP ustda qarshilik yo'qligi sababli o'lchangan masofa bo'yicha"
    )
    return LevelResult(levels, izoh, tp_from_structure=tuzilmaviy_tp)


def _tp_royxati(
    entry: float,
    tp1: float,
    yakuniy: float,
    tp1_tuzilmaviy: bool,
    yakuniy_tuzilmaviy: bool,
    zone_map: ZoneMap,
    rules: TradeRulesConfig,
) -> tuple[list[float], tuple[bool, ...]]:
    """Birinchi va yakuniy nishondan TP ro'yxatini quradi.

    Uchta holat:

        1 ta — `max_take_profits == 1`. Qismli sotish yo'q, butun
               pozitsiya yakuniy nishonda yopiladi. Shuning uchun
               TP1 emas, YAKUNIY nishon olinadi: aks holda savdo
               1:3 o'rniga 1:1.5 da tugardi.
        2 ta — odatiy holat, o'zgarishsiz.
        3 ta — TP1 va yakuniy nishon ORASIDA haqiqiy zona bo'lsa, u
               ham qo'shiladi. Bo'lmasa ikkitasi qoladi — raqam
               o'ylab topilmaydi.
    """
    if rules.max_take_profits <= 1:
        return [yakuniy], (yakuniy_tuzilmaviy,)

    if rules.max_take_profits >= 3:
        oraliq = _oraliq_zona(tp1, yakuniy, zone_map)
        if oraliq is not None:
            return [tp1, oraliq, yakuniy], (tp1_tuzilmaviy, True, yakuniy_tuzilmaviy)

    return [tp1, yakuniy], (tp1_tuzilmaviy, yakuniy_tuzilmaviy)


def _oraliq_zona(tp1: float, yakuniy: float, zone_map: ZoneMap) -> float | None:
    """TP1 bilan yakuniy nishon orasidagi HAQIQIY qarshilik zonasi.

    Ikkalasiga ham juda yaqin zona qo'shilmaydi: uchta TP bir-biriga
    tiqilib qolsa, ular alohida ma'no bermaydi va faqat kartochkani
    uzaytiradi.
    """
    oraliq = yakuniy - tp1
    if oraliq <= 0:
        return None
    chekka = oraliq * ORALIQ_TP_CHEKKA

    for zona in zone_map.resistances:
        nishon = zona.low
        if tp1 + chekka <= nishon <= yakuniy - chekka:
            return nishon
    return None


def _build_stop(
    entry: float,
    support_low: float,
    atr: float,
    rules: TradeRulesConfig,
) -> float | None:
    """Stop support zonasidan pastda, ruxsat etilgan oraliqda bo'lishi kerak.

    Oraliq IKKI tomonlama (3.3-band tuzatilgan):

    - juda YAQIN (< `min_stop_distance_pct`) — bozor shovqini Stop'ni
      bekorga yeb qo'yadi;
    - juda UZOQ (> `max_stop_distance_pct`) — pozitsiya hajmi shunchalik
      kichrayadiki, savdoning ma'nosi qolmaydi.

    Stop sun'iy ravishda yaqinlashtirilmaydi: bu support zonasi ICHIDA
    Stop qo'yish demakdir — narx zonaga tegib qaytsa ham Stop ishlardi.
    """
    stop = _stop_narxi(entry, support_low, atr, rules)
    if stop <= 0 or stop >= entry:
        return None

    if not rules.enforce_distance_bands:
        # Loyiha egasining qarori: foizlar majburiy emas, bog'lovchi
        # shart — nisbat (1:3). Stop shovqindan ATR bilan
        # himoyalanadi (`stop_atr_mult`), ya'ni himoya yo'qolmaydi,
        # faqat qat'iy foizdan ATR birligiga ko'chadi.
        return stop

    masofa_pct = (entry - stop) / entry * 100
    if masofa_pct < rules.min_stop_distance_pct:
        return None
    if masofa_pct > rules.max_stop_distance_pct:
        return None
    return stop


def _stop_narxi(
    entry: float, support_low: float, atr: float, rules: TradeRulesConfig
) -> float:
    """Stop narxi: ATR masofasi VA support tuzilmasi — ikkalasidan uzoqrog'i.

    ATR qismi (`stop_atr_mult`) bozor shovqinidan himoya qiladi: shovqin
    foizda emas, ATR birligida o'lchanadi. Qat'iy foiz barcha coinlarga
    bir xil qo'llanardi va barqaror coinda keraksiz keng, volatilda esa
    juda tor bo'lardi.

    Tuzilmaviy qism (support zonasidan past) saqlanadi: Stop zona ICHIDA
    qolsa, narx zonaga tegib qaytganda ham Stop ishlardi — ya'ni
    strategiyaning o'z asosini buzardi.

    Shuning uchun ikkalasidan UZOQROG'I olinadi: shovqin uchun ham joy
    bor, tuzilma ham himoyalangan.
    """
    atr_stop = entry - atr * rules.stop_atr_mult
    tuzilmaviy = support_low - atr * STOP_BUFFER_ATR
    return min(atr_stop, tuzilmaviy)


def _build_tp1(
    entry: float,
    zone_map: ZoneMap,
    rules: TradeRulesConfig,
    stop_distance_pct: float = 0.0,
) -> float | None:
    """TP1 — eng yaqin MAZMUNLI resistance.

    Ikkita mustaqil shart bor va ular boshqa-boshqa savolga javob
    beradi:

        foiz oralig'i   MASOFA haqida. Faqat `enforce_distance_bands`
                        yoqilganda qo'llanadi (loyiha egasining
                        qarori: foizlar majburiy emas).

        nisbat poli     NISBAT haqida. `enforce_tp1_ratio` yoqilganda
                        zona `tp1_min_risk_reward` dan past nisbatda
                        bo'lsa O'TKAZIB YUBORILADI.

    NIMA UCHUN NISBAT POLI KERAK (natija #7). TP1 da pozitsiyaning
    bir qismi sotiladi va Stop kirish narxiga ko'tariladi. TP1 juda
    yaqin bo'lsa o'sha qism arzimas foyda beradi, qolgani esa nolda
    yopiladi — komissiyadan keyin savdo manfiy chiqadi. Turkum
    "g'alaba", pul esa kamaygan.

    Zona rad etilsa KEYINGISI qidiriladi: uzoqroqdagi qarshilik
    ham haqiqiy nishon. Hech biri yetmasa `None` qaytadi va
    chaqiruvchi o'lchangan TP ga o'tadi — u allaqachon shu
    nisbatga bo'ysunadi.
    """
    eng_past_nisbat = (
        stop_distance_pct * rules.tp1_min_risk_reward
        if rules.enforce_tp1_ratio
        else 0.0
    )

    for zona in zone_map.resistances:
        # Zonaning PASTKI chegarasi — narx u yerga yetganda sotish boshlanadi
        nishon = zona.low
        if nishon <= entry:
            continue
        if (nishon - entry) / entry * 100 < eng_past_nisbat:
            continue  # nisbat past — qismli sotish ma'nosiz bo'lardi
        if not rules.enforce_distance_bands:
            return nishon
        eng_past = entry * (1 + rules.min_tp_distance_pct / 100)
        eng_baland = entry * (1 + rules.max_tp_distance_pct / 100)
        if eng_past <= nishon <= eng_baland:
            return nishon

    return None


def _build_tp2_tuzilmadan(
    entry: float,
    tp1: float,
    stop_distance_pct: float,
    zone_map: ZoneMap,
    rules: TradeRulesConfig,
) -> float | None:
    """TP2 — TP1 dan keyingi HAQIQIY resistance zonasi.

    NIMA UCHUN. Formuladagi TP2 (`_build_tp2`) bozorda nima borligiga
    umuman qaramaydi: u faqat stop masofasidan hisoblanadi. Stop keng
    bo'lsa TP2 uzoqqa uchib ketadi, o'sha yerda qarshilik bormi yoki
    yo'qmi — ahamiyatsiz. 2026-09-02 backtesti buni raqam bilan
    ko'rsatdi: TP2 gacha savdolarning atigi 29.9% i yetadi.

    Bu yerda TP2 narx haqiqatan to'xtashi mumkin bo'lgan joyga
    qo'yiladi. Nisbat PASAYADI, lekin yetib borish ehtimoli oshadi.
    Qaysi tomon og'irroq — buni backtest aytadi, shuning uchun bu
    yo'l bayroq ostida (`tp2_from_structure`).

    Zona chekkasi PASTKI chegarasidan olinadi: narx o'sha yerga
    yetganda sotuv bosimi boshlanadi, zona o'rtasida emas.
    """
    eng_baland = (
        entry * (1 + rules.max_tp_distance_pct / 100)
        if rules.enforce_distance_bands
        else float("inf")
    )
    eng_past_nisbat = stop_distance_pct * rules.tp2_structural_min_rr

    for zona in zone_map.resistances:
        nishon = zona.low
        if nishon <= tp1:
            continue  # TP1 ning o'zi yoki undan past — TP2 bo'la olmaydi
        if nishon > eng_baland:
            break  # ro'yxat yaqindan uzoqqa tartiblangan, keyingilari ham uzoq
        if (nishon - entry) / entry * 100 < eng_past_nisbat:
            continue  # nisbat juda past — savdoning ma'nosi qolmaydi
        return nishon

    return None


def _bitta_nishon(
    entry: float,
    stop: float,
    tp1: float,
    tuzilmaviy: bool,
    rules: TradeRulesConfig,
) -> LevelResult:
    """Yagona TP li signal — qismli sotish yo'q.

    TP1 allaqachon 1:N nisbatidan uzoqda bo'lsa, undan yuqoriga
    yasama ikkinchi nishon qo'yilmaydi. Butun pozitsiya shu
    yerda yopiladi.
    """
    try:
        levels = signal_levels(entry, stop, tp1, from_structure=(tuzilmaviy,))
    except ValueError as exc:
        return LevelResult(
            None,
            f"Darajalar tartibi buzildi: {exc}",
            stage="levels:tartib_buzildi",
            tp_from_structure=tuzilmaviy,
        )

    return LevelResult(
        levels,
        f"Bitta TP: TP1 ning o'zi 1:{rules.min_risk_reward:g} nisbatidan uzoqda",
        tp_from_structure=tuzilmaviy,
    )


def _build_tp2(
    entry: float,
    tp1: float,
    stop_distance_pct: float,
    rules: TradeRulesConfig,
) -> float | None:
    """YAKUNIY nishon — kamida 1:N R/R.

    BOG'LOVCHI SHART SHU YERDA. Loyiha egasining qoidasi: "TP STOP
    FOIZLARI MAJBURIY EMAS — RISK 1/3". Ya'ni nishonni foiz emas,
    `min_risk_reward` belgilaydi; yuqori chegara faqat
    `enforce_distance_bands` yoqilganda qo'llanadi.
    """
    kerakli_pct = stop_distance_pct * rules.min_risk_reward
    nishon = entry * (1 + kerakli_pct / 100)
    eng_baland = (
        entry * (1 + rules.max_tp_distance_pct / 100)
        if rules.enforce_distance_bands
        else float("inf")
    )

    if nishon > eng_baland:
        return None
    # `nishon <= tp1` holati bu yerga yetib kelmaydi — chaqiruvchi
    # uni oldin ushlaydi va BITTA TP li signal quradi.
    return nishon
