"""MSNR — S/R daraja turlarini tasniflash (CryptoSpot3%, 1-qism).

Oddiy Support/Resistance dan tashqari metodika olti turni ajratadi:

    RBS   Resistance Broken as Support — buzib o'tilgan qarshilik endi
          qo'llab-quvvatlash vazifasini bajaradi
    SBR   Support Broken as Resistance — aksincha
    OCL   Order block + Change of Level — struktura o'zgargan nuqta
          bilan ustma-ust tushgan daraja
    Qm    Quasimodo — struktura buzilishidan oldingi YOLG'ON breakout
    OB    Engulfing + Strong Order Block — qamrab oluvchi sham bilan
          tasdiqlangan daraja

NIMA UCHUN ALOHIDA MODUL, `support_resistance/` ICHIDA EMAS. Tasnif
ikki manbaga qaraydi: ZONALARGA (`support_resistance`) va STRUKTURAGA
(`market_structure`). `market_structure` esa o'z navbatida pivotlarni
`support_resistance` dan oladi. Tasnifni zonalar paketi ichiga
qo'ysak, aylanma import chiqadi. Shuning uchun u ikkalasidan YUQORIDA
turadi — bog'liqlik yo'nalishi bir tomonlama qoladi.

Natija ball tizimiga BONUS sifatida kiradi, to'siq sifatida emas.
"""

from __future__ import annotations

from enum import Enum

from core.analysis.market_structure import MarketStructure, SwingLabel
from core.domain.enums import ZoneKind
from core.domain.models import Candle, SRZone


class LevelType(str, Enum):
    """Daraja turi — MSNR tasnifi."""

    PLAIN = "plain"
    RBS = "rbs"
    SBR = "sbr"
    OCL = "ocl"
    QUASIMODO = "quasimodo"
    STRONG_OB = "strong_ob"

    @property
    def confidence(self) -> float:
        """Tur bo'yicha ishonch ulushi (0..1) — bonus ballga ko'paytiriladi.

        Qiymatlar BOSHLANG'ICH: metodika turlarni sifat jihatidan
        tartiblaydi, lekin raqamli vazn bermaydi. Ular backtest bilan
        tasdiqlanishi kerak (`docs/ARXITEKTURA.md`, 57-bo'lim).
        """
        return {
            "plain": 0.0,
            "rbs": 0.6,
            "sbr": 0.6,
            "ocl": 0.8,
            "quasimodo": 1.0,
            "strong_ob": 1.0,
        }[self.value]

    @property
    def label(self) -> str:
        return {
            "plain": "oddiy daraja",
            "rbs": "RBS — buzilgan qarshilik endi qo'llab-quvvatlash",
            "sbr": "SBR — buzilgan qo'llab-quvvatlash endi qarshilik",
            "ocl": "OCL — struktura o'zgargan nuqtadagi daraja",
            "quasimodo": "Quasimodo — yolg'on breakout naqshi",
            "strong_ob": "Kuchli order block (engulfing bilan)",
        }[self.value]


# --------------------------------------------------------------------------- #
#  MSNR — daraja turini aniqlash
# --------------------------------------------------------------------------- #


def classify_level_type(
    zone: SRZone,
    candles: list[Candle],
    atr_value: float,
    structure: MarketStructure | None = None,
) -> LevelType:
    """Zonani MSNR turlaridan biriga tasniflaydi.

    Tartib MUHIM: bir zona bir vaqtda bir necha shartga mos kelishi
    mumkin (masalan ham RBS, ham order block). Kuchliroq belgi
    ustunlik qiladi, chunki tasnif ishonch darajasini bildiradi.
    """
    if not candles or atr_value <= 0:
        return LevelType.PLAIN

    if _is_quasimodo(zone, candles, structure):
        return LevelType.QUASIMODO
    if _is_strong_order_block(zone, candles, atr_value):
        return LevelType.STRONG_OB
    if _is_change_of_level(zone, structure):
        return LevelType.OCL
    if _is_flipped(zone, candles):
        return LevelType.RBS if zone.kind is ZoneKind.SUPPORT else LevelType.SBR
    return LevelType.PLAIN


def _is_flipped(zone: SRZone, candles: list[Candle]) -> bool:
    """Daraja avval QARAMA-QARSHI tomondan sinalganmi (RBS / SBR).

    Support uchun: tarixda narx bu zonadan YUQORIDAN pastga emas,
    pastdan yuqoriga o'tgan bo'lishi kerak — ya'ni zona qachondir
    qarshilik bo'lgan va buzib o'tilgan.

    Buzilish yopilish narxi bilan o'lchanadi (soya bilan emas) va
    kamida bitta to'liq o'tish talab qilinadi.
    """
    yuqorida = False
    pastda = False
    otish = False

    for sham in candles:
        if sham.close > zone.high:
            if pastda:
                otish = True
            yuqorida, pastda = True, False
        elif sham.close < zone.low:
            if yuqorida:
                otish = True
            yuqorida, pastda = False, True

    if not otish:
        return False

    # Support uchun narx HOZIR zonadan yuqorida bo'lishi kerak (aks holda
    # u hali ham qarshilik), resistance uchun aksincha.
    oxirgi = candles[-1].close
    if zone.kind is ZoneKind.SUPPORT:
        return oxirgi > zone.low
    return oxirgi < zone.high


def _is_change_of_level(zone: SRZone, structure: MarketStructure | None) -> bool:
    """Zona BOS yoki CHOCH darajasi bilan ustma-ust tushadimi (OCL)."""
    if structure is None:
        return False
    for hodisa in (structure.last_choch, structure.last_bos):
        if hodisa is not None and zone.contains(hodisa.level):
            return True
    return False


def _is_quasimodo(
    zone: SRZone, candles: list[Candle], structure: MarketStructure | None
) -> bool:
    """Yolg'on breakout naqshi: yangi ekstremum, keyin keskin qaytish.

    Support zonasi uchun: zona ichida (yoki undan pastda) YANGI PAST
    nuqta (LL) yasalgan, lekin narx keyin zonadan yuqoriga qaytib
    yopilgan. Ya'ni "pastga chiqish" ushlanmagan.
    """
    if structure is None or not structure.swings:
        return False

    izlanadigan = SwingLabel.LL if zone.kind is ZoneKind.SUPPORT else SwingLabel.HH
    for swing in reversed(structure.swings):
        if swing.label is not izlanadigan:
            continue
        # Ekstremum zonaga tegishlimi
        tegishli = (
            swing.price <= zone.high if zone.kind is ZoneKind.SUPPORT
            else swing.price >= zone.low
        )
        if not tegishli:
            continue
        keyingi = candles[swing.index + 1 :]
        if not keyingi:
            return False
        if zone.kind is ZoneKind.SUPPORT:
            return any(s.close > zone.high for s in keyingi)
        return any(s.close < zone.low for s in keyingi)
    return False


def _is_strong_order_block(zone: SRZone, candles: list[Candle], atr_value: float) -> bool:
    """Qamrab oluvchi sham bilan tasdiqlangan order block.

    Support uchun: zona ichida tushuvchi sham, undan keyin uni QAMRAB
    OLGAN ko'tariluvchi sham, va shundan so'ng narx kamida bir ATR
    yuqoriga siljigan. Uchalasi birga — "bu yerda yirik buyurtma
    turgan" degan belgi.
    """
    if len(candles) < 3:
        return False

    for i in range(len(candles) - 2):
        oldingi, keyingi = candles[i], candles[i + 1]
        if not _overlaps(zone, oldingi):
            continue

        if zone.kind is ZoneKind.SUPPORT:
            if oldingi.is_bullish or not keyingi.is_bullish:
                continue
            qamrab = keyingi.close > oldingi.open and keyingi.open <= oldingi.close
            siljish = max(s.high for s in candles[i + 1 :]) - oldingi.low
        else:
            if not oldingi.is_bullish or keyingi.is_bullish:
                continue
            qamrab = keyingi.close < oldingi.open and keyingi.open >= oldingi.close
            siljish = oldingi.high - min(s.low for s in candles[i + 1 :])

        if qamrab and siljish >= atr_value:
            return True
    return False


def _overlaps(zone: SRZone, candle: Candle) -> bool:
    return candle.low <= zone.high and candle.high >= zone.low


