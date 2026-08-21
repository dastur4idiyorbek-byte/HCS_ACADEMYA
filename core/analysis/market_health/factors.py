"""3.7-band: Bozor Salomatligi Indeksining besh omili.

Har bir omil 0..1 oralig'ida baholanadi va vazniga ko'paytiriladi.
Vaznlar `config/default.yaml` -> `market_health.weights` da (jami 100).

MA'LUMOT YO'Q BO'LGANDA nima bo'ladi — har bir omil uchun alohida qaror,
chunki "ma'lumot yo'q" har doim ham "yomon" degani emas:

  BTC dominance   -> 0.0  (bozor holati noma'lum — ehtiyotkorlik)
  Trend kengligi  -> 0.0  (halol ro'yxat tahlil qilinmagan — signal bermaslik)
  Volatillik      -> 0.0  (tekis bozorni ajratib bo'lmaydi)
  Sig'im          -> 1.0  (foydalanuvchi yo'q -> tizim o'zini cheklamasin)
  To'yinganlik    -> hisoblanadi (ochiq signal soni doim ma'lum)

Birinchi uchtasi 0.0 bo'lgani uchun ma'lumotsiz indeks 40 dan past chiqadi
va 4.9-band bo'yicha yangi signal berilmaydi — bu ataylab (0.3-band).
"""

from __future__ import annotations

from core.analysis.market_health.inputs import HealthInputs
from core.config.schema import BtcDominanceConfig, MarketHealthWeights
from core.domain.models import HealthFactor


def btc_dominance_factor(
    inputs: HealthInputs,
    config: BtcDominanceConfig,
    weight: float,
) -> HealthFactor:
    """1-omil: BTC Dominance barqarormi yoki keskin o'zgaryaptimi.

    Keskin o'zgarish — bozorda kapital oqimi almashayotganini bildiradi:
    dominance keskin oshsa altcoinlardan chiqish, keskin tushsa esa
    beqaror "altseason" boshlanishi mumkin. Ikkalasi ham spot savdo uchun
    xavfli.
    """
    ozgarish = inputs.btc_dominance_change_24h
    if ozgarish is None:
        return HealthFactor(
            "btc_dominance_stability", 0.0, weight, "BTC Dominance ma'lumoti yo'q"
        )

    kattalik = abs(ozgarish)
    if kattalik <= config.stable_change_pct:
        ball = 1.0
        holat = "barqaror"
    elif kattalik >= config.sharp_change_pct:
        ball = 0.0
        holat = "keskin o'zgarmoqda"
    else:
        oraliq = config.sharp_change_pct - config.stable_change_pct
        ball = 1.0 - (kattalik - config.stable_change_pct) / oraliq
        holat = "o'zgarmoqda"

    return HealthFactor(
        "btc_dominance_stability",
        ball,
        weight,
        f"BTC Dominance {holat} ({ozgarish:+.2f} p.p. / 24s)",
    )


def trend_breadth_factor(inputs: HealthInputs, weight: float) -> HealthFactor:
    """2-omil: Halol ro'yxatdagi coinlarning necha foizi ko'tarilish trendida.

    Bu — bozorning "kengligi" (breadth). Bir nechta coin ko'tarilib, qolgani
    tushayotgan bo'lsa, bu haqiqiy ko'tarilish emas.
    """
    ulush = inputs.uptrend_ratio
    if ulush is None:
        return HealthFactor(
            "halal_trend_breadth", 0.0, weight, "Halol ro'yxat tahlil qilinmagan"
        )

    return HealthFactor(
        "halal_trend_breadth",
        ulush,
        weight,
        f"Halol coinlarning {ulush:.0%}i ko'tarilish trendida "
        f"({inputs.universe_size} tadan)",
    )


def volatility_regime_factor(
    inputs: HealthInputs,
    adx_threshold: float,
    weight: float,
    strong_trend_adx: float = 30.0,
) -> HealthFactor:
    """3-omil: bozor trendda mi yoki tekis (sideways).

    ADX chegaradan past — tekis bozor, S/R zonalari ishonchsiz ishlaydi.

    Diqqat, bu yerda o'lchov birligi boshqa: ADX 30 ta coinning
    O'RTACHASI. Bitta coinda ADX 40 — kuchli trend, lekin 30 ta coin
    o'rtachasi bunga deyarli chiqmaydi: coinlar har xil vaqtda trendga
    kiradi va o'rtacha hammasini silliqlaydi. Shu sababli to'liq ball
    chegarasi bitta coin uchun emas, O'RTACHA uchun sozlanadi
    (`docs/ARXITEKTURA.md`, 32-bo'lim).
    """
    ortacha = inputs.average_adx
    if ortacha is None:
        return HealthFactor("volatility_regime", 0.0, weight, "ADX hisoblanmagan")

    if ortacha <= adx_threshold:
        ball = 0.0
        holat = "tekis (sideways)"
    elif ortacha >= strong_trend_adx:
        ball = 1.0
        holat = "kuchli trend"
    else:
        ball = (ortacha - adx_threshold) / (strong_trend_adx - adx_threshold)
        holat = "trend shakllanmoqda"

    return HealthFactor(
        "volatility_regime", ball, weight, f"Bozor rejimi: {holat} (ADX {ortacha:.0f})"
    )


def user_capacity_factor(inputs: HealthInputs, weight: float) -> HealthFactor:
    """4-omil: agregat foydalanuvchi sig'imi (5.2-band).

    "Odamlarning ko'pchiligi allaqachon band, hozir yana signal tashlashning
    keragi yo'q." Foydalanuvchi umuman bo'lmasa — to'liq ball: tizim o'zini
    sun'iy cheklamasligi kerak, boshqa filtrlar baribir ishlaydi.
    """
    sigim = inputs.capacity
    if sigim is None:
        return HealthFactor(
            "aggregate_user_capacity",
            1.0,
            weight,
            "Foydalanuvchi ma'lumoti yo'q — sig'im cheklovi qo'llanilmaydi",
        )

    return HealthFactor(
        "aggregate_user_capacity", sigim.headroom_ratio, weight, sigim.describe()
    )


def saturation_factor(inputs: HealthInputs, weight: float) -> HealthFactor:
    """5-omil: faol signallar Risk Engine limitiga qanchalik yaqin.

    Limit to'lgan bo'lsa yangi signal baribir o'tmaydi (4.2-band), shuning
    uchun indeks buni oldindan aks ettiradi.
    """
    band = inputs.saturation_ratio
    bo_sh = 1.0 - band

    return HealthFactor(
        "signal_saturation",
        bo_sh,
        weight,
        f"Faol signallar: {inputs.open_signals}/{inputs.max_open_signals} "
        f"({bo_sh:.0%} joy bo'sh)",
    )


def build_factors(
    inputs: HealthInputs,
    weights: MarketHealthWeights,
    dominance_config: BtcDominanceConfig,
    adx_threshold: float,
    strong_trend_adx: float = 30.0,
) -> list[HealthFactor]:
    """Barcha besh omilni hisoblaydi."""
    return [
        btc_dominance_factor(inputs, dominance_config, weights.btc_dominance_stability),
        trend_breadth_factor(inputs, weights.halal_trend_breadth),
        volatility_regime_factor(
            inputs, adx_threshold, weights.volatility_regime, strong_trend_adx
        ),
        user_capacity_factor(inputs, weights.aggregate_user_capacity),
        saturation_factor(inputs, weights.signal_saturation),
    ]
