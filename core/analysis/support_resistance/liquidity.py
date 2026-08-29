"""LIT — Liquidity Sweep (CryptoSpot3%, 3-qism).

Metodikaning asosiy g'oyasi: narx muhim darajani BIROZ buzib o'tib,
stop-losslarni yig'ib oladi va keyin qaytadi. Aynan shu "yalab o'tib
qaytish" — haqiqiy kirish nuqtasining belgisi. Mavjud tizim faqat
"narx zonaga yaqin" ekanini tekshirardi; bu qatlam qo'shimcha ravishda
"buzdi va qaytdi" naqshini qidiradi.

HECH BIRI TO'SIQ EMAS
---------------------
Ikkalasining natijasi ham ball tizimiga BONUS sifatida kiradi
(`scoring/bonuses.py`). Topilmasa — bonus yo'q, xolos; nomzod bazaviy
100 ballik tizimda baholanishda davom etadi. Bu loyihada qat'iy "VA"
filtrlarini ko'paytirish allaqachon voronkani nolga tushirgan
(`docs/ARXITEKTURA.md`, 40- va 44-bo'limlar).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config.schema import LiquiditySweepConfig
from core.domain.enums import ZoneKind
from core.domain.models import Candle, SRZone


@dataclass(frozen=True, slots=True)
class LiquiditySweep:
    """Aniqlangan "yalab o'tib qaytish" naqshi."""

    #: Eng chuqur kirib borilgan narx (soyaning uchi)
    swept_price: float
    #: Yalash sodir bo'lgan sham indeksi
    index: int
    #: Zona chekkasidan qancha chuqur kirilgani, foizda
    depth_pct: float
    #: Narx zona ichiga qaytib YOPILGAN sham indeksi
    reclaim_index: int
    #: Qaytishdan beri necha sham o'tgan
    bars_since: int

    def describe(self) -> str:
        return (
            f"Narx {self.swept_price:.6g} darajasini {self.depth_pct:.2f}% "
            f"buzib qaytdi (Liquidity Sweep, {self.bars_since} sham oldin)"
        )


# --------------------------------------------------------------------------- #
#  LIT — Liquidity Sweep
# --------------------------------------------------------------------------- #


def detect_liquidity_sweep(
    candles: list[Candle],
    zone: SRZone,
    config: LiquiditySweepConfig,
) -> LiquiditySweep | None:
    """Zona chekkasini "yalab o'tib qaytish" naqshini qidiradi.

    Support uchun: sham SOYASI zona pastidan kamida `min_sweep_pct`
    chuqur kirgan, lekin `max_reclaim_bars` ichida narx zona ichiga
    qaytib YOPILGAN.

    Nima uchun soya va yopilish AJRATILADI: yalash — bu aynan soya
    bilan sodir bo'ladigan hodisa (stop-losslar yig'ib olinadi), qaytish
    esa yopilish bilan tasdiqlanadi. Ikkalasini bir xil o'lchov bilan
    qarasak, naqsh umuman topilmasdi.

    ENG SO'NGGISI qaytariladi: eski yalash bugungi kirish uchun dalil
    emas.
    """
    if not config.enabled or not candles:
        return None

    oyna = candles[-config.lookback_bars :] if config.lookback_bars > 0 else candles
    ofset = len(candles) - len(oyna)

    chekka = zone.low if zone.kind is ZoneKind.SUPPORT else zone.high
    if chekka <= 0:
        return None
    eng_kam = chekka * config.min_sweep_pct / 100

    natija: LiquiditySweep | None = None
    for i, sham in enumerate(oyna):
        chuqurlik = (
            chekka - sham.low if zone.kind is ZoneKind.SUPPORT else sham.high - chekka
        )
        if chuqurlik < eng_kam:
            continue
        if not _is_excursion(oyna, i, zone):
            continue

        qaytish = _reclaim_index(oyna, i, zone, config.max_reclaim_bars)
        if qaytish is None:
            continue

        natija = LiquiditySweep(
            swept_price=sham.low if zone.kind is ZoneKind.SUPPORT else sham.high,
            index=ofset + i,
            depth_pct=chuqurlik / chekka * 100,
            reclaim_index=ofset + qaytish,
            bars_since=len(oyna) - 1 - qaytish,
        )

    return natija


def _is_excursion(candles: list[Candle], index: int, zone: SRZone) -> bool:
    """Yalash IChKARIDAN chiqishmi yoki allaqachon tashqarida turganmi.

    Nima uchun kerak: narx darajani buzib tushib, bir necha sham pastda
    turib, keyin qaytsa — bu LIT emas, bu oddiy buzilish va tiklanish.
    Bunday holatda pastda turgan HAR BIR sham "yalash" shartiga mos
    kelardi va qaytishdan oldingi oxirgisi doim topilardi. Ya'ni
    `max_reclaim_bars` cheklovi amalda ishlamasdi.

    Metodikadagi naqsh esa TEZ: narx ichkaridan chiqib, soya tashlab,
    darhol qaytadi. Shuning uchun yalashdan OLDINGI sham daraja ichida
    (yoki undan narigi tomonda) yopilgan bo'lishi kerak.
    """
    if index == 0:
        return True
    oldingi = candles[index - 1].close
    if zone.kind is ZoneKind.SUPPORT:
        return oldingi >= zone.low
    return oldingi <= zone.high


def _reclaim_index(
    candles: list[Candle], sweep_index: int, zone: SRZone, max_bars: int
) -> int | None:
    """Yalashdan keyin zona ichiga qaytib yopilgan birinchi sham.

    Yalagan shamning O'ZI ham hisobga olinadi: uzun soyali, lekin zona
    ichida yopilgan sham — naqshning eng toza ko'rinishi.
    """
    oxiri = min(len(candles), sweep_index + max_bars + 1)
    for j in range(sweep_index, oxiri):
        yopilish = candles[j].close
        if zone.kind is ZoneKind.SUPPORT and yopilish >= zone.low:
            return j
        if zone.kind is ZoneKind.RESISTANCE and yopilish <= zone.high:
            return j
    return None
