"""NARX HARAKATI naqshlari — kitobning takrorlanuvchi yadrosi.

MANBA: "PRICE ACTION STRATEGIES — TOP 15" (o'zbek tilida,
nurinvest.uz tarjimasi). To'liq tasnif va iqtiboslar
`docs/NARX_HARAKATI_STRATEGIYALARI.md` da.

LOYIHA EGASINING SHARTI: faqat XARID. Kitobdagi sotish
strategiyalari (4, 6, 12, 13, 14, 15) bu yerda umuman
qurilmaydi — ular faqat bozor yo'nalishini o'qish uchun.
Kitobning o'zi ham ularni "nojoiz savdo" deb belgilaydi.

TAKRORLANUVCHI YADRO. To'qqizta xarid strategiyasidan oltitasi
(1, 2, 3, 7, 8, 10) AYNAN bir xil uch qadamni takrorlaydi:

    1. daraja YORIB o'tiladi          (sham daraja USTIDA yopiladi)
    2. narx unga QAYTA SINOVGA keladi  (retest)
    3. o'sha yerda BUQASIMON sham      -> KIRISH

Kitob buni bir necha marta ta'kidlaydi:

    "Ba'zan biz ham xato qilamizki, biz narx kritik zonaga
     yaqin bo'lganda savdoga kiramiz va stoploss tezda uriladi."

    "Hech qachon figura to'liq shakllanmasdan savdoga kirish
     juda katta xato bo'ladi."

BIZDA BU YO'Q EDI. `classic_ta` narx Discount zonasida bo'lsa
kiradi — qaytishni KUTMAYDI, tasdiq SO'RAMAYDI. Yettita
gipoteza to'plamidan keyin ham win-rate 27-29% da qotib
turibdi, va bu farq eng yaqin izoh.

STOP QAYERDA. Kitobda bitta javob bor va u har safar
takrorlanadi: "stoploss oldingi pastki nuqtadan pastroqda
bo'lishi kerak". Ya'ni Stop NAQSHDAN keladi, formuladan emas.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config.schema import NarxHarakatiConfig
from core.domain.models import Candle


@dataclass(frozen=True, slots=True)
class QaytaSinov:
    """Yorish → qayta sinov → tasdiq naqshi.

    Barcha indekslar berilgan sham ro'yxatiga nisbatan.
    """

    daraja: float
    yorish_index: int
    sinov_index: int
    tasdiq_index: int
    #: Naqshning eng past nuqtasi — Stop shundan pastga qo'yiladi
    eng_past: float

    @property
    def bar_soni(self) -> int:
        return self.tasdiq_index - self.yorish_index

    def izoh(self) -> str:
        return (
            f"{self.daraja:.6g} darajasi yorildi, {self.bar_soni} shamdan "
            "keyin qayta sinovdan o'tdi va buqasimon sham bilan tasdiqlandi"
        )


def _buqasimon(sham: Candle) -> bool:
    """Yashil sham — yopilish ochilishdan yuqori.

    Kitobda "buqasimon shamtayoq" aynan shu: yashil tus.
    """
    return sham.close > sham.open


def qayta_sinov_topilsinmi(
    candles: list[Candle],
    daraja: float,
    config: NarxHarakatiConfig,
    atr: float,
) -> QaytaSinov | None:
    """Berilgan daraja uchun naqshni qidiradi.

    NAQSH OXIRGI SHAMDA TUGASHI SHART. Aks holda tarixdagi eski
    naqshlar ham "signal" bo'lib chiqardi va bot allaqachon
    o'tib ketgan imkoniyatga kirardi — kitob buni "kech kirish"
    deb ogohlantiradi.

    Args:
        candles: shamlar, eng eskisidan eng yangisiga.
        daraja: qarshilik darajasi (yoriladigan chiziq).
        config: kutish oynalari va tolerans.
        atr: qayta sinov "darajaga yaqin"ligini o'lchash birligi.
            Foiz emas — ATR: loyiha egasining qoidasi bo'yicha
            foizlar majburiy emas, o'lchov bozorning o'z
            volatilligiga bog'lanadi.
    """
    if daraja <= 0 or atr <= 0 or len(candles) < 3:
        return None

    tasdiq_index = len(candles) - 1
    tasdiq = candles[tasdiq_index]

    # 3-qadam: tasdiq shami BUQASIMON va daraja USTIDA yopilgan
    if config.tasdiq_shami_shart and not _buqasimon(tasdiq):
        return None
    if tasdiq.close <= daraja:
        return None

    tolerans = atr * config.qayta_sinov_tolerans_atr

    # 1-qadam: DARAJA YORILGAN bo'lishi kerak.
    #
    # Yorish = narx daraja OSTIDAN USTIGA o'tgan: sham daraja
    # ustida yopilgan, undan OLDINGISI esa ostida. Shunchaki
    # "daraja ustida yopilgan" yetarli emas — narx allaqachon
    # tepada bo'lsa hech narsa yorilmagan.
    #
    # Soya bilan tegib o'tish ham yorish emas: kitob "yorib
    # o'tish" deydi, ya'ni YOPILISH.
    yorish_index: int | None = None
    eng_erta = max(1, tasdiq_index - config.yorish_oynasi)
    for i in range(tasdiq_index - 1, eng_erta - 1, -1):
        if candles[i].close > daraja and candles[i - 1].close <= daraja:
            yorish_index = i
            break
    if yorish_index is None:
        return None

    # 2-qadam: yorishdan KEYIN narx darajaga QAYTGAN bo'lishi kerak.
    #
    # Qaytish = shamning QUYI nuqtasi darajaga yetgan. Yopilish
    # emas, quyi nuqta: qayta sinov aynan soya bilan sodir bo'ladi.
    #
    # Kutish oynasi cheklangan: yorishdan yigirma sham keyingi
    # "qayta sinov" — qayta sinov emas, boshqa hodisa.
    sinov_index: int | None = None
    oxiri = min(tasdiq_index - 1, yorish_index + config.qayta_sinov_oynasi)
    for i in range(yorish_index + 1, oxiri + 1):
        if candles[i].low <= daraja + tolerans:
            sinov_index = i
            break
    if sinov_index is None:
        return None

    eng_past = min(s.low for s in candles[sinov_index : tasdiq_index + 1])

    return QaytaSinov(
        daraja=daraja,
        yorish_index=yorish_index,
        sinov_index=sinov_index,
        tasdiq_index=tasdiq_index,
        eng_past=eng_past,
    )


@dataclass(frozen=True, slots=True)
class IkkitaPastlik:
    """Ikkita pastlik (double bottom) — kitobning 2 va 10-strategiyasi.

    Ikki marta deyarli bir xil darajadan qaytish. Ular orasidagi
    cho'qqi — BO'YIN CHIZIG'I. Kirish o'sha chiziq yorilib qayta
    sinovdan o'tganda bo'ladi.
    """

    birinchi_tub: int
    ikkinchi_tub: int
    boyin_chizigi: float
    tub_narxi: float


def ikkita_pastlik_topilsinmi(
    candles: list[Candle],
    config: NarxHarakatiConfig,
    atr: float,
) -> IkkitaPastlik | None:
    """Oxirgi oynada ikkita pastlik figurasini qidiradi.

    Ikki tub bir-biriga YAQIN bo'lishi kerak (ATR birligida).
    Ular orasida aniq cho'qqi bo'lishi shart — aks holda bu
    ikkita tub emas, bitta uzun tub.
    """
    oyna = candles[-config.figura_oynasi :]
    if len(oyna) < 5 or atr <= 0:
        return None

    ofset = len(candles) - len(oyna)
    tolerans = atr * config.tub_tolerans_atr

    # Eng past ikkita LOKAL tub
    tublar = [
        i
        for i in range(1, len(oyna) - 1)
        if oyna[i].low < oyna[i - 1].low and oyna[i].low < oyna[i + 1].low
    ]
    if len(tublar) < 2:
        return None

    # Oxirgi tubdan orqaga qarab, unga YAQIN bo'lgan oldingi tubni
    # qidiramiz.
    oxirgi = tublar[-1]
    for oldingi in reversed(tublar[:-1]):
        if abs(oyna[oxirgi].low - oyna[oldingi].low) > tolerans:
            continue
        # Cho'qqi ikki tub ORASIDA bo'lishi kerak — tublarning
        # o'zi kirmaydi, aks holda tubning uzun soyasi "bo'yin
        # chizig'i" bo'lib chiqardi.
        oraliq = oyna[oldingi + 1 : oxirgi]
        if not oraliq:
            continue
        choqqi = max(s.high for s in oraliq)
        # Cho'qqi ikkala tubdan sezilarli baland bo'lishi kerak
        if choqqi - max(oyna[oxirgi].low, oyna[oldingi].low) < tolerans:
            continue
        return IkkitaPastlik(
            birinchi_tub=ofset + oldingi,
            ikkinchi_tub=ofset + oxirgi,
            boyin_chizigi=choqqi,
            tub_narxi=min(oyna[oxirgi].low, oyna[oldingi].low),
        )
    return None
