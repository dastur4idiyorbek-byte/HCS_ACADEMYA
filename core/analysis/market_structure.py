"""SMC — Market Structure: HH/HL/LH/LL, BOS va CHOCH.

CryptoSpot3% (ISC 1.0) metodikasining 2-qismi. Savol bitta: **narx
qaysi tomonga qadam tashlab boryapti** — yuqoriga (har cho'qqi
avvalgisidan baland, har chuqurlik avvalgisidan yuqori) yoki pastga.

    HH  Higher High   — avvalgi cho'qqidan baland cho'qqi
    HL  Higher Low    — avvalgi chuqurlikdan yuqori chuqurlik
    LH  Lower High    — avvalgi cho'qqidan past cho'qqi
    LL  Lower Low     — avvalgi chuqurlikdan past chuqurlik

    BOS   Break of Structure     — trend DAVOM etayotganini tasdiqlaydi
                                   (ko'tarilishda: narx oxirgi HH dan o'tdi)
    CHOCH Change of Character    — trend O'ZGARGANINI bildiradi
                                   (ko'tarilishda: narx oxirgi HL dan tushdi)

NIMA UCHUN BU YOLG'IZ ISHLATILMAYDI. Metodikaning o'zi ta'kidlaydi:
faqat BOS/CHOCH ga qarab kirish kam ishonchli, chunki BOS nuqtasi
ko'pincha aynan likvidlik yig'iladigan joy. Shuning uchun bu modul
YO'NALISHNI aytadi, KIRISH NUQTASINI esa `support_resistance` dagi
Liquidity Sweep qatlami bilan birga aniqlaydi.

NIMA UCHUN TO'SIQ EMAS. Natija ball tizimiga bonus sifatida kiradi
(`scoring/bonuses.py`). Bu loyihada qat'iy "VA" filtrlarini ko'paytirish
allaqachon signal voronkasini nolga tushirgan (`docs/ARXITEKTURA.md`,
44-bo'lim). Yangi bilim ballni KO'TARADI, yo'lni yopmaydi.

SOF MODUL: hech qayerga murojaat qilmaydi, faqat shamlardan hisoblaydi.
Shu sababli backtestda ham bir xil ishlaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.analysis.support_resistance.pivots import Pivot, find_pivots
from core.domain.enums import TrendDirection, ZoneKind
from core.domain.models import Candle

#: Yo'nalish aniqlash uchun kamida shuncha swing kerak (2 cho'qqi + 2 chuqurlik).
MIN_SWINGS = 4


class SwingLabel(str, Enum):
    """Swing nuqtasining avvalgi bir xil turdagi nuqtaga nisbatan holati."""

    HH = "HH"
    HL = "HL"
    LH = "LH"
    LL = "LL"
    #: Turkumdagi BIRINCHI nuqta — solishtiradigan avvalgisi yo'q.
    FIRST = "first"


@dataclass(frozen=True, slots=True)
class Swing:
    """Belgilangan swing nuqtasi."""

    index: int
    price: float
    kind: ZoneKind
    label: SwingLabel

    @property
    def is_high(self) -> bool:
        return self.kind is ZoneKind.RESISTANCE


@dataclass(frozen=True, slots=True)
class StructureBreak:
    """BOS yoki CHOCH — narx qaysi darajani va qachon buzgani."""

    #: `"bos"` yoki `"choch"`
    kind: str
    #: Buzilgan daraja narxi (oxirgi swing high yoki low)
    level: float
    #: Buzilish qayd etilgan sham indeksi
    index: int
    #: Buzilish yo'nalishi: yuqoriga (UP) yoki pastga (DOWN)
    direction: TrendDirection


@dataclass(frozen=True, slots=True)
class MarketStructure:
    """Bitta coin uchun struktura holati."""

    swings: list[Swing]
    direction: TrendDirection
    last_bos: StructureBreak | None = None
    last_choch: StructureBreak | None = None

    @property
    def is_uptrend(self) -> bool:
        return self.direction is TrendDirection.UP

    def describe(self) -> str:
        """Odam o'qiydigan bir qatorli xulosa — "Nega bu signal?" uchun."""
        if not self.swings:
            return "Struktura aniqlanmadi — swing nuqtalari yetarli emas"

        nom = {
            TrendDirection.UP: "Ko'tarilish trendi (HH/HL)",
            TrendDirection.DOWN: "Pasayish trendi (LH/LL)",
            TrendDirection.FLAT: "Struktura aniq emas (aralash swinglar)",
        }[self.direction]

        if self.last_choch is not None and (
            self.last_bos is None or self.last_choch.index >= self.last_bos.index
        ):
            return f"{nom}, so'nggi CHOCH {self.last_choch.level:.6g} da"
        if self.last_bos is not None:
            return f"{nom}, so'nggi BOS {self.last_bos.level:.6g} da tasdiqlangan"
        return nom


# --------------------------------------------------------------------------- #
#  Asosiy kirish nuqtasi
# --------------------------------------------------------------------------- #


def analyze_structure(
    candles: list[Candle],
    lookback: int = 5,
    min_swings: int = MIN_SWINGS,
    fallback_min_pct: float = 1.0,
) -> MarketStructure:
    """Sham tarixidan struktura holatini quradi.

    Args:
        candles: shamlar, eng eskisidan eng yangisiga.
        lookback: swing tasdiqlash oynasi (`find_pivots` bilan bir xil).
        min_swings: yo'nalish e'lon qilish uchun minimal swing soni.

        fallback_min_pct: swing yetarli bo'lmaganda ishlatiladigan sof
            narx o'zgarishi chegarasi (foizda).

    Ma'lumot yetarli bo'lmasa `FLAT` qaytadi — XATO EMAS. 0.3-band:
    "aniqlab bo'lmadi" jazoga aylanmaydi, u shunchaki ball bermaydi.
    """
    if not candles:
        return MarketStructure(swings=[], direction=TrendDirection.FLAT)

    swings = label_swings(find_pivots(candles, lookback))
    if len(swings) < min_swings:
        # ZAXIRA O'LCHOV. Swing yo'qligi "trend yo'q" degani EMAS:
        # silliq, to'xtovsiz ko'tarilishda burilish nuqtalari umuman
        # bo'lmaydi — bu esa eng kuchli trendning o'zi. EMA bu holatni
        # ushlab turardi; u olib tashlangach bo'shliq qoldi.
        #
        # Bu EMA emas: o'rtacha ham, uzoq tarix ham kerak emas — faqat
        # "narx oynaning boshidan balandmi" degan to'g'ridan-to'g'ri
        # savol.
        return MarketStructure(
            swings=swings, direction=_net_direction(candles, fallback_min_pct)
        )

    yonalish = _direction_from(swings)
    bos, choch = _find_breaks(candles, swings, yonalish)
    return MarketStructure(
        swings=swings, direction=yonalish, last_bos=bos, last_choch=choch
    )


def label_swings(pivots: list[Pivot]) -> list[Swing]:
    """Har bir pivotni avvalgi BIR XIL TURDAGI pivotga qarab belgilaydi.

    Cho'qqi cho'qqi bilan, chuqurlik chuqurlik bilan solishtiriladi —
    aks holda "cho'qqi avvalgi chuqurlikdan baland" degan ma'nosiz
    taqqoslash chiqadi.

    Bir xil narxdagi ketma-ket swing (`==`) pasayish deb qaralmaydi:
    u avvalgi belgini SAQLAYDI. Ikki marta bir xil cho'qqi — bu
    qo'sh cho'qqi, trend buzilishi emas; uni LH deb belgilash tekis
    bozorni sun'iy ravishda "pasayish" ko'rsatardi.
    """
    natija: list[Swing] = []
    oxirgi_cho_qqi: float | None = None
    oxirgi_chuqurlik: float | None = None
    oxirgi_belgi: dict[ZoneKind, SwingLabel] = {}

    for pivot in sorted(pivots, key=lambda p: p.index):
        if pivot.is_high:
            avvalgi = oxirgi_cho_qqi
            if avvalgi is None:
                belgi = SwingLabel.FIRST
            elif pivot.price > avvalgi:
                belgi = SwingLabel.HH
            elif pivot.price < avvalgi:
                belgi = SwingLabel.LH
            else:
                belgi = oxirgi_belgi.get(ZoneKind.RESISTANCE, SwingLabel.FIRST)
            oxirgi_cho_qqi = pivot.price
            oxirgi_belgi[ZoneKind.RESISTANCE] = belgi
        else:
            avvalgi = oxirgi_chuqurlik
            if avvalgi is None:
                belgi = SwingLabel.FIRST
            elif pivot.price > avvalgi:
                belgi = SwingLabel.HL
            elif pivot.price < avvalgi:
                belgi = SwingLabel.LL
            else:
                belgi = oxirgi_belgi.get(ZoneKind.SUPPORT, SwingLabel.FIRST)
            oxirgi_chuqurlik = pivot.price
            oxirgi_belgi[ZoneKind.SUPPORT] = belgi

        natija.append(Swing(pivot.index, pivot.price, pivot.kind, belgi))

    return natija


def structure_alignment(structure: MarketStructure) -> float:
    """Struktura xarid yo'nalishiga qanchalik mos (0..1).

    Spot savdo faqat uzun (long) — shuning uchun o'lchov "ko'tarilish
    strukturasi bormi" degan savolga javob beradi:

        1.0  ko'tarilish (HH/HL) va so'nggi hodisa BOS — trend davom etmoqda
        0.7  ko'tarilish, lekin BOS yo'q yoki CHOCH keyinroq bo'lgan
        0.4  struktura aniq emas (aralash)
        0.0  pasayish (LH/LL) — bu yerda xarid strukturaga qarshi

    Nol ham TO'SIQ EMAS: u shunchaki bonus bermaydi. Nomzod bazaviy
    100 ballik tizimda baholanishda davom etadi.
    """
    if structure.direction is TrendDirection.DOWN:
        return 0.0
    if structure.direction is TrendDirection.FLAT:
        return 0.4

    keyingi_choch = (
        structure.last_choch is not None
        and structure.last_choch.direction is TrendDirection.DOWN
        and (structure.last_bos is None or structure.last_choch.index > structure.last_bos.index)
    )
    if keyingi_choch:
        return 0.7
    return 1.0 if structure.last_bos is not None else 0.7


# --------------------------------------------------------------------------- #
#  Ichki yordamchilar
# --------------------------------------------------------------------------- #


def _net_direction(candles: list[Candle], min_pct: float) -> TrendDirection:
    """Oynadagi sof narx o'zgarishi bo'yicha yo'nalish — ZAXIRA o'lchov.

    Faqat swing yetarli bo'lmaganda ishlatiladi. Chegara shovqinni
    kesadi: bir foizlik tebranish trend emas.
    """
    if len(candles) < 2:
        return TrendDirection.FLAT
    boshi, oxiri = candles[0].close, candles[-1].close
    if boshi <= 0:
        return TrendDirection.FLAT

    ozgarish = (oxiri - boshi) / boshi * 100
    if ozgarish >= min_pct:
        return TrendDirection.UP
    if ozgarish <= -min_pct:
        return TrendDirection.DOWN
    return TrendDirection.FLAT


def _direction_from(swings: list[Swing]) -> TrendDirection:
    """Oxirgi cho'qqi va oxirgi chuqurlik belgisiga qarab yo'nalish.

    Ikkalasi ham ko'tarilishni ko'rsatsa — UP, ikkalasi ham pasayishni
    ko'rsatsa — DOWN, aralash bo'lsa — FLAT. "Uchtadan ikkitasi" kabi
    yumshoq qoida ataylab olinmadi: struktura aniq bo'lmagan joyda
    "aniq" deb ko'rsatish eng qimmat xato.
    """
    oxirgi_cho_qqi = next((s for s in reversed(swings) if s.is_high), None)
    oxirgi_chuqurlik = next((s for s in reversed(swings) if not s.is_high), None)
    if oxirgi_cho_qqi is None or oxirgi_chuqurlik is None:
        return TrendDirection.FLAT

    yuqoriga = oxirgi_cho_qqi.label is SwingLabel.HH and oxirgi_chuqurlik.label is SwingLabel.HL
    pastga = oxirgi_cho_qqi.label is SwingLabel.LH and oxirgi_chuqurlik.label is SwingLabel.LL
    if yuqoriga:
        return TrendDirection.UP
    if pastga:
        return TrendDirection.DOWN
    return TrendDirection.FLAT


def _find_breaks(
    candles: list[Candle],
    swings: list[Swing],
    direction: TrendDirection,
) -> tuple[StructureBreak | None, StructureBreak | None]:
    """So'nggi BOS va CHOCH ni topadi — swinglar bo'ylab yurib.

    NIMA UCHUN "YURIB". BOS — bu HODISA, holat emas: u aynan narx
    avvalgi cho'qqidan o'tib YANGI HH yasagan paytda sodir bo'lgan.
    Ya'ni buzilgan daraja — OXIRGI cho'qqi emas, undan OLDINGISI.
    Birinchi yozuvda oxirgi cho'qqiga qaralgan edi va oxirgi swing
    aynan cho'qqining o'zi bo'lganda (ko'tarilish trendida bu odatiy
    holat) BOS hech qachon topilmasdi.

    Qoida (standart SMC):
        ko'tarilish holatida  HH -> BOS (davomiylik),  LL -> CHOCH
        pasayish  holatida    LL -> BOS (davomiylik),  HH -> CHOCH

    Buzilish YOPILISH narxi bilan tasdiqlanadi, soya bilan emas: soya
    ko'pincha aynan likvidlik ovi (LIT modulida alohida ko'riladi) va
    uni struktura o'zgarishi deb hisoblash yolg'on signal berardi.
    """
    bos: StructureBreak | None = None
    choch: StructureBreak | None = None

    # Yurish davomidagi holat — u yakuniy `direction` dan farq qilishi
    # mumkin: CHOCH aynan holat O'ZGARGAN paytda qayd etiladi.
    joriy = TrendDirection.FLAT
    avvalgi_cho_qqi: Swing | None = None
    avvalgi_chuqurlik: Swing | None = None

    for swing in swings:
        if swing.is_high:
            if swing.label is SwingLabel.HH and avvalgi_cho_qqi is not None:
                hodisa = _crossing_above(candles, avvalgi_cho_qqi, swing)
                if hodisa is not None:
                    if joriy is TrendDirection.DOWN:
                        choch = StructureBreak("choch", *hodisa, TrendDirection.UP)
                    else:
                        bos = StructureBreak("bos", *hodisa, TrendDirection.UP)
                    joriy = TrendDirection.UP
            avvalgi_cho_qqi = swing
        else:
            if swing.label is SwingLabel.LL and avvalgi_chuqurlik is not None:
                hodisa = _crossing_below(candles, avvalgi_chuqurlik, swing)
                if hodisa is not None:
                    if joriy is TrendDirection.UP:
                        choch = StructureBreak("choch", *hodisa, TrendDirection.DOWN)
                    else:
                        bos = StructureBreak("bos", *hodisa, TrendDirection.DOWN)
                    joriy = TrendDirection.DOWN
            avvalgi_chuqurlik = swing

    # Yakuniy yo'nalishga ZID BOS saqlanmaydi: pasayishga o'tgan coinda
    # eski ko'tarilish BOS'i "trend davom etmoqda" degan yolg'on
    # taassurot berardi.
    if bos is not None and direction is not TrendDirection.FLAT and bos.direction is not direction:
        bos = None
    return bos, choch


def _crossing_above(
    candles: list[Candle], broken: Swing, made_by: Swing
) -> tuple[float, int] | None:
    """`broken` cho'qqisidan yuqoriga birinchi YOPILISH — daraja va indeks."""
    chegara = min(len(candles), made_by.index + 1)
    for i in range(broken.index + 1, chegara):
        if candles[i].close > broken.price:
            return broken.price, i
    return None


def _crossing_below(
    candles: list[Candle], broken: Swing, made_by: Swing
) -> tuple[float, int] | None:
    chegara = min(len(candles), made_by.index + 1)
    for i in range(broken.index + 1, chegara):
        if candles[i].close < broken.price:
            return broken.price, i
    return None
