"""Ishonch darajasi filtri.

Ishonch — zanjir bloklarining ball asosidagi o'lchovi (0..1). Bu filtr
QO'SHIMCHA darvoza: bloklar o'tgan bo'lsa ham, ishonch minimal
chegaradan past bo'lsa signal chiqarilmaydi.

Chegara TAXMIN QILINMAYDI: backtest topgunga qadar `PENDING` turadi va
filtr passiv bo'ladi (hammani o'tkazadi). Bu — eski tizimning
"taxminiy 0.6" xatosini qaytarmaslik uchun.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Chegara hali backtest orqali topilmaganligini bildiruvchi belgi.
PENDING = "PENDING"


@dataclass(frozen=True, slots=True)
class IshonchFiltri:
    """Ishonch darajasini minimal chegaraga solishtiradi.

    Args:
        eng_kam: Minimal ishonch (0..1) yoki `PENDING`. `PENDING`
            holatda filtr passiv — hech kimni kesmaydi.
    """

    eng_kam: float | str = PENDING

    def faol(self) -> bool:
        """Filtr ishlayaptimi (chegara raqam va noldan katta)."""
        return isinstance(self.eng_kam, float) and self.eng_kam > 0

    def otkazadi(self, ishonch: float) -> bool:
        """Signal chiqarishga ruxsat bormi."""
        if not self.faol():
            return True
        return ishonch >= float(self.eng_kam)

    def rad_sababi(self, ishonch: float) -> str:
        """Nima uchun o'tkazildi yoki rad etildi — jurnal uchun."""
        if not self.faol():
            return "chegara PENDING — filtr passiv"
        if self.otkazadi(ishonch):
            return "ishonch yetarli"
        return f"ishonch {ishonch:.2f} < chegara {self.eng_kam}"
