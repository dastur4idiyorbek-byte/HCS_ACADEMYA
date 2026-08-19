"""3.1-band: Support/Resistance zonalarini aniqlash — BIRLAMCHI tahlil.

Tahlil aynan shu moduldan boshlanadi, EMA/RSI/MACD'dan emas. Ketma-ketlik:

    1. Swing pivotlar topiladi (pivots.py)
    2. Yaqin pivotlar ZONAGA birlashtiriladi — daraja emas, ORALIQ,
       chunki bozor aniq bir narxda emas, tor oraliqda burildi
    3. Har bir zona necha marta test qilingani sanaladi
    4. Fibonacci darajalari yordamchi sifatida qo'shiladi
    5. Zonalar joriy narxga nisbatan support/resistance deb ajratiladi
    6. Diapazon Discount/Premium zonalariga bo'linadi (range_position.py) —
       narx "arzon"mi yoki "qimmat"mi degan savolga javob

Zonalarning kengligi ATR bilan o'lchanadi — narx miqyosidan qat'i nazar
"yaqin" tushunchasi bir xil ma'no beradi.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.analysis.indicators.volatility import atr
from core.analysis.support_resistance.fibonacci import (
    fibonacci_levels,
    find_swing_range,
)
from core.analysis.support_resistance.pivots import Pivot, count_touches, find_pivots
from core.analysis.support_resistance.range_position import (
    RangePosition,
    compute_range_position,
)
from core.config.schema import SupportResistanceConfig
from core.domain.enums import ZoneKind
from core.domain.models import Candle, SRZone
from core.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ZoneMap:
    """Bitta coin uchun aniqlangan zonalar to'plami."""

    zones: list[SRZone]
    price: float
    atr: float
    #: 3.1-band: narx zonaga shu ATR masofasida bo'lsa "zonada" hisoblanadi.
    #: Qat'iy "ichida" sharti amalda deyarli hech qachon bajarilmaydi —
    #: zona kengligi ATR ning yarmi, narx esa doim harakatda.
    proximity_atr: float = 1.0
    #: Oxirgi muhim harakatning chegaralari. Diapazon uchun ZAXIRA tayanch:
    #: toza ko'tarilish trendida ustda qarshilik zonasi bo'lmaydi (trend
    #: degani aynan shu), lekin joriy harakatning cho'qqisi baribir mavjud.
    swing_low: float | None = None
    swing_high: float | None = None

    @property
    def supports(self) -> list[SRZone]:
        """Narxdan pastdagi zonalar, eng yaqinidan boshlab."""
        return sorted(
            (z for z in self.zones if z.kind is ZoneKind.SUPPORT),
            key=lambda z: self.price - z.high,
        )

    @property
    def resistances(self) -> list[SRZone]:
        """Narxdan yuqoridagi zonalar, eng yaqinidan boshlab."""
        return sorted(
            (z for z in self.zones if z.kind is ZoneKind.RESISTANCE),
            key=lambda z: z.low - self.price,
        )

    def nearest_support(self) -> SRZone | None:
        return self.supports[0] if self.supports else None

    def nearest_resistance(self) -> SRZone | None:
        return self.resistances[0] if self.resistances else None

    def zone_at_price(self) -> SRZone | None:
        """Narx AYNAN qaysi zonaning ichida turibdi (qat'iy tekshiruv)."""
        for zona in self.zones:
            if zona.contains(self.price):
                return zona
        return None

    def active_zone(self, kind: ZoneKind | None = None) -> SRZone | None:
        """Narx qaysi zonaga YAQIN (`proximity_atr` masofasida).

        3.1-band "narx shu muhim zonaga yaqinlashganda" deydi — aynan
        ichida bo'lishini talab qilmaydi. Qat'iy "ichida" sharti amalda
        deyarli hech qachon bajarilmaydi: zona kengligi ATR ning yarmi
        atrofida, narx esa har sahniyada harakat qiladi.

        Args:
            kind: berilsa, faqat shu turdagi zonalar tekshiriladi.
        """
        nomzodlar = [z for z in self.zones if kind is None or z.kind is kind]
        yaqinlar = [z for z in nomzodlar if self.is_price_near(z, self.proximity_atr)]
        if not yaqinlar:
            return None
        return min(yaqinlar, key=lambda z: z.distance_to(self.price))

    def range_position(self) -> RangePosition | None:
        """Narxning Support—Resistance diapazonidagi joylashuvi.

        Bir tomonda zona bo'lmasa, oxirgi muhim swing darajasi tayanch
        sifatida ishlatiladi. Sabab: toza ko'tarilish trendida ustda
        qarshilik zonasi BO'LMAYDI — trend degani aynan shu. Agar bunday
        holatda diapazon umuman qurilmasa, tizim aynan trend filtri talab
        qiladigan sharoitda hech qachon signal bera olmasdi.

        Returns:
            `RangePosition`, yoki `None` — hech qanday tayanch topilmadi.
        """
        support = self.nearest_support() or self._synthetic_zone(
            self.swing_low, ZoneKind.SUPPORT
        )
        resistance = self.nearest_resistance() or self._synthetic_zone(
            self.swing_high, ZoneKind.RESISTANCE
        )
        if support is None or resistance is None:
            return None
        return compute_range_position(self.price, support, resistance)

    def _synthetic_zone(self, level: float | None, kind: ZoneKind) -> SRZone | None:
        """Swing darajasidan tor zaxira zona quradi (diapazon tayanchi uchun)."""
        if level is None:
            return None
        yarim = self.atr * 0.25
        return SRZone(kind=kind, low=level - yarim, high=level + yarim, touches=1)

    def entry_allowed(self) -> bool:
        """Qat'iy qoida: narx Support zonasida VA Discount zonada bo'lsa kirish.

        Support yaqinida turgan narx ham, agar diapazonning yuqori yarmida
        bo'lsa (oraliq tor yoki narx aslida Premium'da), kirish uchun to'liq
        kuchga ega emas.
        """
        joylashuv = self.range_position()
        if joylashuv is None:
            return False
        support_yaqinida = self.active_zone(ZoneKind.SUPPORT) is not None
        return joylashuv.allows_entry(support_yaqinida)

    def distance_in_atr(self, zone: SRZone) -> float:
        """Narxdan zonagacha masofa, ATR birligida."""
        return 0.0 if self.atr <= 0 else zone.distance_to(self.price) / self.atr

    def is_price_near(self, zone: SRZone, max_atr: float) -> bool:
        """Narx zonaga yetarlicha yaqinmi — signal ko'rib chiqilishi uchun shart."""
        return self.distance_in_atr(zone) <= max_atr


class SupportResistanceDetector:
    """Shamlardan S/R zonalarini quradi."""

    def __init__(self, config: SupportResistanceConfig, atr_period: int = 14) -> None:
        self._config = config
        self._atr_period = atr_period

    def detect(self, candles: list[Candle]) -> ZoneMap | None:
        """Zonalarni aniqlaydi.

        Returns:
            `ZoneMap`, yoki `None` — ma'lumot yetarli emas. `None` qaytishi
            0.3-band bo'yicha signal berilmasligiga olib keladi.
        """
        if len(candles) < self._config.swing_lookback * 2 + 2:
            return None

        atr_qiymati = atr(candles, self._atr_period)
        if atr_qiymati is None or atr_qiymati <= 0:
            logger.debug("ATR hisoblanmadi — zonalar qurilmadi")
            return None

        narx = candles[-1].close
        tolerans = atr_qiymati * self._config.zone_merge_atr_mult

        pivotlar = find_pivots(candles, self._config.swing_lookback)
        zonalar = self._cluster(pivotlar, candles, tolerans, narx)
        zonalar.extend(self._fibonacci_zones(candles, zonalar, tolerans, narx))
        harakat = find_swing_range(candles)

        # Ko'p marta test qilinmagan zonalar chiqarib tashlanadi — ular
        # tasodifiy tebranish bo'lishi mumkin.
        muhimlar = [z for z in zonalar if z.touches >= self._config.min_touches]

        return ZoneMap(
            zones=muhimlar,
            price=narx,
            atr=atr_qiymati,
            proximity_atr=self._config.proximity_atr_mult,
            swing_low=harakat.low if harakat else None,
            swing_high=harakat.high if harakat else None,
        )

    # ------------------------------------------------------------------ #

    def _cluster(
        self,
        pivots: list[Pivot],
        candles: list[Candle],
        tolerance: float,
        price: float,
    ) -> list[SRZone]:
        """Yaqin pivotlarni bitta zonaga birlashtiradi."""
        if not pivots:
            return []

        tartiblangan = sorted(pivots, key=lambda p: p.price)
        guruhlar: list[list[Pivot]] = [[tartiblangan[0]]]

        for pivot in tartiblangan[1:]:
            oxirgi_guruh = guruhlar[-1]
            markaz = sum(p.price for p in oxirgi_guruh) / len(oxirgi_guruh)
            if abs(pivot.price - markaz) <= tolerance:
                oxirgi_guruh.append(pivot)
            else:
                guruhlar.append([pivot])

        zonalar: list[SRZone] = []
        for guruh in guruhlar:
            narxlar = [p.price for p in guruh]
            past, baland = min(narxlar), max(narxlar)

            # Bitta pivotdan iborat zona kengliksiz qolmasligi kerak —
            # narx aniq bir nuqtaga tegishini kutish real emas.
            if baland - past < tolerance:
                markaz = (past + baland) / 2
                past, baland = markaz - tolerance / 2, markaz + tolerance / 2

            testlar, oxirgi_test = count_touches(candles, past, baland)
            zonalar.append(
                SRZone(
                    kind=self._classify(past, baland, price),
                    low=past,
                    high=baland,
                    touches=max(testlar, len(guruh)),
                    last_touch=oxirgi_test,
                )
            )
        return zonalar

    def _fibonacci_zones(
        self,
        candles: list[Candle],
        existing: list[SRZone],
        tolerance: float,
        price: float,
    ) -> list[SRZone]:
        """Mavjud zonalarga to'g'ri kelmagan Fibonacci darajalarini qo'shadi."""
        diapazon = find_swing_range(candles)
        if diapazon is None:
            return []

        yangi: list[SRZone] = []
        for _, daraja in fibonacci_levels(diapazon, self._config.fibonacci_levels):
            if any(z.contains(daraja) for z in existing):
                continue  # allaqachon pivot zonasi qamrab olgan — takrorlamaymiz

            past, baland = daraja - tolerance / 2, daraja + tolerance / 2
            testlar, oxirgi_test = count_touches(candles, past, baland)
            yangi.append(
                SRZone(
                    kind=self._classify(past, baland, price),
                    low=past,
                    high=baland,
                    touches=testlar,
                    last_touch=oxirgi_test,
                    from_fibonacci=True,
                )
            )
        return yangi

    @staticmethod
    def _classify(low: float, high: float, price: float) -> ZoneKind:
        """Zona joriy narxdan pastdami (support) yoki yuqoridami (resistance)."""
        markaz = (low + high) / 2
        return ZoneKind.SUPPORT if markaz <= price else ZoneKind.RESISTANCE
