"""6-qism — holat saqlash va BOSQICHMA-BOSQICH yangilash.

MUAMMO. Zanjirni har sham yopilganda to'liq qayta hisoblash qimmat
va — muhimrog'i — MA'NOSIZ: fundamental holat 4 soatda o'zgarmaydi,
struktura esa kunlab bir xil qoladi.

YECHIM (promptdagi tartib, AYNAN shu ketma-ketlikda):

    1. AVVAL — "to'liq" deb belgilangan bloklar QAYTA TASDIQLANADI
       (hali ham to'g'rimi — TEZ tekshiruv, to'liq hisoblash emas)
    2. Agar eski blok BUZILGAN bo'lsa — zanjir O'SHA YERDAN uziladi,
       undan keyingi bloklar BEKOR QILINADI
    3. Faqat SHUNDAN KEYIN — hali to'liq bo'lmagan blok yangilanadi

TARTIB NIMA UCHUN MUHIM. Teskarisi bo'lsa: 4-blok tasdiqlanadi,
signal chiqadi, va faqat keyin 2-blokning buzilgani ma'lum bo'ladi.
Ya'ni signal ALLAQACHON yuborilgan bo'lardi.

"TEZ TEKSHIRUV" NIMA. Blokni qayta hisoblash o'rniga uning BITTA
hal qiluvchi shartiga qaraymiz:

    Struktura  — qarshi CHOCH paydo bo'ldimi
    Zona       — narx zonadan chiqib ketdimi
    Fundamental— qattiq to'siq paydo bo'ldimi

Bu uchtasi buzilishning 90% ini ushlaydi va har biri bir necha
amalda hisoblanadi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.analysis.turlar import Blok, Zanjir
from core.analysis.zone_quality.fibonacci import Zona


@dataclass(slots=True)
class NomzodHolati:
    """Bitta coinning zanjirdagi joriy holati."""

    symbol: str
    bloklar: dict[str, Blok] = field(default_factory=dict)
    zona: Zona | None = None
    yangilangan: datetime | None = None

    def matn(self) -> str:
        """Jonli Oshxona monitori uchun (2-prompt, 6-qism)."""
        tartib = ["Fundamental", "Struktura", "Zona Sifati", "Tasdiqlash"]
        qatorlar = [f"{self.symbol}:"]
        for i, nom in enumerate(tartib):
            belgi = "🔷" if i == 0 else "🔗"
            b = self.bloklar.get(nom)
            if b is None:
                qatorlar.append(f"  {belgi} {nom}: tekshirilmagan")
            else:
                qatorlar.append(f"  {belgi} {b}")
        return "\n".join(qatorlar)


class HolatKuzatuvchi:
    """Barcha nomzodlarning holatini saqlaydi va bosqichma-bosqich yangilaydi."""

    def __init__(self) -> None:
        self._holatlar: dict[str, NomzodHolati] = {}

    def holat(self, symbol: str) -> NomzodHolati:
        if symbol not in self._holatlar:
            self._holatlar[symbol] = NomzodHolati(symbol=symbol)
        return self._holatlar[symbol]

    def barchasi(self) -> list[NomzodHolati]:
        return list(self._holatlar.values())

    def yoz(self, symbol: str, zanjir: Zanjir, zona: Zona | None, vaqt: datetime) -> None:
        """Zanjir natijasini holatga yozadi."""
        h = self.holat(symbol)
        h.bloklar = {b.nom: b for b in zanjir.bloklar}
        h.zona = zona
        h.yangilangan = vaqt

    def bekor_qil(self, symbol: str, blokdan: str) -> None:
        """Berilgan blokdan KEYINGI hamma narsani o'chiradi.

        Blokning o'zi ham o'chiriladi: u buzilgan, ya'ni eski natija
        endi yaroqsiz. Undan OLDINGI bloklar qoladi — ular hamon
        to'g'ri va qayta hisoblash shart emas.
        """
        tartib = ["Fundamental", "Struktura", "Zona Sifati", "Tasdiqlash"]
        if blokdan not in tartib:
            return
        boshlanish = tartib.index(blokdan)
        h = self.holat(symbol)
        for nom in tartib[boshlanish:]:
            h.bloklar.pop(nom, None)
        if boshlanish <= tartib.index("Zona Sifati"):
            h.zona = None

    def tez_tekshir(
        self,
        symbol: str,
        *,
        qarshi_choch: bool = False,
        narx: float | None = None,
        qattiq_tosiq: bool = False,
    ) -> str | None:
        """1 va 2-qadam: eski bloklar hali ham to'g'rimi.

        Returns:
            Buzilgan blok nomi, yoki `None` — hammasi joyida.
        """
        h = self.holat(symbol)

        if qattiq_tosiq and "Fundamental" in h.bloklar:
            self.bekor_qil(symbol, "Fundamental")
            return "Fundamental"

        if qarshi_choch and "Struktura" in h.bloklar:
            self.bekor_qil(symbol, "Struktura")
            return "Struktura"

        if (
            narx is not None
            and h.zona is not None
            and "Zona Sifati" in h.bloklar
            and not h.zona.ichida(narx)
            # Narx zonadan YUQORIGA chiqishi — buzilish emas, harakat
            # boshlangani. Faqat PASTGA tushish zonani bekor qiladi.
            and narx < h.zona.past
        ):
            self.bekor_qil(symbol, "Zona Sifati")
            return "Zona Sifati"

        return None
