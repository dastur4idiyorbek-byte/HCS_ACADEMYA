"""Signal grafigi rasmi — "uzun pozitsiya" ko'rinishi.

NIMA UCHUN O'ZIMIZ CHIZAMIZ, TradingView SKRINSHOTI EMAS:

  - TradingView'da grafik rasmini olishning OCHIQ API si yo'q.
    "Snapshot" tugmasi — sayt interfeysining bir qismi, xizmat emas.
  - Uni brauzer bilan avtomatlashtirish TradingView shartlariga zid,
    konteynerga ~400 MB Chromium qo'shadi va interfeys o'zgargan kuni
    sinadi.
  - Bepul embed widget'da CHIZISH API si umuman yo'q: "Long Position"
    asbobini dastur orqali qo'yib bo'lmaydi. U faqat litsenziyalangan
    Charting Library da bor.
  - Uchinchi tomon xizmatlari (chart-img va sh.k.) buni qila oladi,
    lekin pullik va ular yiqilsa rasm ham yo'qoladi.

Shuning uchun grafik BIZNING ma'lumotimizdan chiziladi: shamlar
allaqachon Binance'dan olinadi (`core/market_data`), darajalar esa
signalning o'zida. Natija — tashqi xizmatga bog'liq bo'lmagan,
brendimizdagi rasm.

Ranglar `web/src/app/globals.css` dagi bilan bir xil — ular logotipdan
piksel darajasida o'lchangan (`scripts/logo_ranglari.py`).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from core.domain.models import Candle, SignalLevels
from core.utils.time_utils import utc_now

# --- Logotipdan olingan ranglar ------------------------------------------ #
FON = "#0a2450"
PANEL = "#133c7c"
RAMKA = "#f47f16"
SARLAVHA = "#00bcd5"
MATN = "#c7d4ea"
MATN_PAST = "#9ab0d2"
YAXSHI = "#00bcd5"
PAST = "#f2695a"

#: Zonalarning shaffofligi (0-255). Shamlar ostidan ko'rinib tursin.
ZONA_ALFA = 46

ENI = 1000
BOYI = 620
CHAP = 24
ONG_USTUN = 176  # narx yorliqlari uchun
TEPA = 74
PAST_CHET = 34

#: Pozitsiya qutisi grafikning o'ng qismida turadi — TradingView'dagi
#: asbob ham signal lahzasidan o'ngga qarab chiziladi.
QUTI_BOSHI = 0.62


@dataclass(frozen=True, slots=True)
class Olcham:
    """Narx <-> piksel almashinuvi.

    Alohida turadi, chunki bu — SOF MATEMATIKA va uni rasm chizmasdan
    sinab ko'rish mumkin. Chizish kodidagi xatoni ko'z bilan topish
    qiyin, hisobdagini esa test tutadi.
    """

    eng_past: float
    eng_yuqori: float
    tepa: int
    past: int

    def y(self, narx: float) -> float:
        """Narxni piksel qatoriga aylantiradi (yuqori narx — kichik y)."""
        oraliq = self.eng_yuqori - self.eng_past
        if oraliq <= 0:
            return (self.tepa + self.past) / 2
        ulush = (narx - self.eng_past) / oraliq
        return self.past - ulush * (self.past - self.tepa)


def olcham_hisobla(
    candles: list[Candle], levels: SignalLevels, chekka: float = 0.06
) -> Olcham:
    """Narx oralig'i — shamlar VA darajalar sig'adigan qilib.

    Darajalar ham kiritiladi: Stop yoki TP shamlar oralig'idan tashqarida
    bo'lsa (ko'pincha shunday), ular rasmdan chiqib ketardi.
    """
    narxlar: list[float] = [levels.stop, levels.entry, levels.tp1, levels.tp2]
    for sham in candles:
        narxlar.append(sham.high)
        narxlar.append(sham.low)

    past, yuqori = min(narxlar), max(narxlar)
    bosh_joy = (yuqori - past) * chekka or max(yuqori * 0.01, 1e-8)
    return Olcham(past - bosh_joy, yuqori + bosh_joy, TEPA, BOYI - PAST_CHET)


def _shrift(olcham: int) -> ImageFont.FreeTypeFont:
    """Pillow'ning O'Z shrifti — tizimda shrift fayli bo'lmasligi mumkin.

    Railway konteynerida `fonts-dejavu` o'rnatilmagan. `load_default(size)`
    esa Pillow bilan birga keladigan masshtablanadigan shriftni beradi,
    ya'ni hech qanday tashqi faylga bog'liq emasmiz.
    """
    return ImageFont.load_default(size=olcham)


def _punktir(
    rasm: ImageDraw.ImageDraw,
    x1: float,
    y: float,
    x2: float,
    rang: str,
    bulak: int = 9,
    organ: int = 7,
) -> None:
    x = x1
    while x < x2:
        rasm.line([(x, y), (min(x + bulak, x2), y)], fill=rang, width=2)
        x += bulak + organ


def _narx_matni(qiymat: float) -> str:
    if qiymat >= 1000:
        return f"{qiymat:,.2f}"
    if qiymat >= 1:
        return f"{qiymat:,.4f}".rstrip("0").rstrip(".")
    return f"{qiymat:.8f}".rstrip("0").rstrip(".")


#: Yorliq qutisi balandligi (38) + eng kichik oraliq.
YORLIQ_ORALIQ = 42


def _yorliqlarni_joylashtir(ylar: list[float]) -> list[float]:
    """Ustma-ust tushadigan yorliqlarni bir-biridan ajratadi.

    Kirish YUQORIDAN PASTGA tartiblangan deb hisoblanadi (TP2, TP1,
    Kirish, Stop). Har bir yorliq oldingisidan kamida `YORLIQ_ORALIQ`
    piksel pastda turadi; keyin butun ustun rasm ichiga qaytariladi.

    NEGA ALOHIDA FUNKSIYA: bu sof hisob va uni rasm chizmasdan sinash
    mumkin. TP1 bilan TP2 orasidagi masofa ko'p signalda 1-2% bo'ladi,
    ya'ni ustma-ust tushish ODATIY hol, istisno emas.
    """
    if not ylar:
        return []

    natija = [ylar[0]]
    for y in ylar[1:]:
        natija.append(max(y, natija[-1] + YORLIQ_ORALIQ))

    # Pastga chiqib ketgan bo'lsa — hammasini yuqoriga suramiz.
    chekka_past = BOYI - PAST_CHET
    ortiqcha = natija[-1] + 19 - chekka_past
    if ortiqcha > 0:
        natija = [y - ortiqcha for y in natija]
    # Tepadan chiqib ketmasin.
    kamomad = TEPA - (natija[0] - 19)
    if kamomad > 0:
        natija = [y + kamomad for y in natija]
    return natija


def render_signal_chart(  # noqa: PLR0913, PLR0915
    symbol: str,
    candles: list[Candle],
    levels: SignalLevels,
    quote_asset: str = "USDT",
    timeframe: str = "4h",
    created_at: datetime | None = None,
) -> bytes:
    """Signal grafigini PNG bayt sifatida qaytaradi.

    Ko'rinishi TradingView'ning "Long Position" asbobiga o'xshaydi:
    kirish chizig'i, undan pastda Stop'gacha QIZIL zona (xavf), tepada
    TP1 va TP2 gacha YASHIL zonalar (foyda).

    Args:
        candles: eng eskisidan eng yangisiga tartiblangan shamlar.

    Raises:
        ValueError: sham berilmagan bo'lsa — bo'sh grafik chizishning
            ma'nosi yo'q, chaqiruvchi buni bilishi kerak.
    """
    if not candles:
        raise ValueError("Grafik uchun sham yo'q")

    rasm = Image.new("RGB", (ENI, BOYI), FON)
    ch = ImageDraw.Draw(rasm)
    olch = olcham_hisobla(candles, levels)

    maydon_chap = CHAP
    maydon_ong = ENI - ONG_USTUN
    maydon_eni = maydon_ong - maydon_chap

    # --- Sarlavha --------------------------------------------------------- #
    ch.text(
        (CHAP, 20),
        f"{symbol.upper()}/{quote_asset.upper()}",
        font=_shrift(30),
        fill=SARLAVHA,
    )
    ch.text((CHAP + 14 + ch.textlength(
        f"{symbol.upper()}/{quote_asset.upper()}", font=_shrift(30)
    ), 29), f"· {timeframe}", font=_shrift(20), fill=MATN_PAST)

    vaqt = (created_at or utc_now()).strftime("%d.%m.%Y · %H:%M UTC")
    ch.text((maydon_ong - ch.textlength(vaqt, font=_shrift(18)), 30),
            vaqt, font=_shrift(18), fill=MATN_PAST)
    ch.line([(CHAP, TEPA - 12), (ENI - CHAP, TEPA - 12)], fill=PANEL, width=2)

    # --- Zonalar (shamlardan OLDIN: ular fon bo'lib qolsin) --------------- #
    qatlam = Image.new("RGBA", (ENI, BOYI), (0, 0, 0, 0))
    qz = ImageDraw.Draw(qatlam)
    quti_x = maydon_chap + maydon_eni * QUTI_BOSHI

    y_entry = olch.y(levels.entry)
    # Foyda zonasi BITTA: kirishdan TP2 gacha. Avval TP1 va TP2 uchun
    # ikkita ustma-ust to'rtburchak chizilardi va ular "ikki qavat"
    # bo'lib ko'rinardi — TradingView asbobida ham zona bitta.
    for narx_, rang, alfa in (
        (levels.stop, PAST, ZONA_ALFA + 14),
        (levels.tp2, YAXSHI, ZONA_ALFA),
    ):
        qz.rectangle(
            [quti_x, min(y_entry, olch.y(narx_)), maydon_ong, max(y_entry, olch.y(narx_))],
            fill=(*Image.new("RGB", (1, 1), rang).getpixel((0, 0)), alfa),
        )
    rasm = Image.alpha_composite(rasm.convert("RGBA"), qatlam).convert("RGB")
    ch = ImageDraw.Draw(rasm)

    # --- Shamlar ---------------------------------------------------------- #
    qadam = maydon_eni / len(candles)
    tana = max(2.0, qadam * 0.62)
    for i, sham in enumerate(candles):
        x = maydon_chap + qadam * (i + 0.5)
        rang = YAXSHI if sham.close >= sham.open else PAST
        ch.line([(x, olch.y(sham.high)), (x, olch.y(sham.low))], fill=rang, width=1)
        yuqori, quyi = olch.y(max(sham.open, sham.close)), olch.y(min(sham.open, sham.close))
        # Doji: ochilish va yopilish teng bo'lsa tana ko'rinmay qolardi.
        if quyi - yuqori < 1:
            quyi = yuqori + 1
        ch.rectangle([x - tana / 2, yuqori, x + tana / 2, quyi], fill=rang)

    # --- Darajalar va yorliqlar ------------------------------------------- #
    qatorlar = [
        (levels.tp2, YAXSHI, "TP2", (levels.tp2 - levels.entry) / levels.entry * 100),
        (levels.tp1, YAXSHI, "TP1", (levels.tp1 - levels.entry) / levels.entry * 100),
        (levels.entry, RAMKA, "Kirish", None),
        (levels.stop, PAST, "Stop", (levels.stop - levels.entry) / levels.entry * 100),
    ]
    kichik, orta = _shrift(17), _shrift(20)
    # Chiziq HAR DOIM o'z narxida, YORLIQ esa siljishi mumkin: TP1 va TP2
    # bir-biriga yaqin bo'lsa (ko'p signalda shunday) ular ustma-ust
    # tushib, narx umuman ko'rinmay qolardi.
    yorliq_y = _yorliqlarni_joylashtir([olch.y(n) for n, _, _, _ in qatorlar])

    for (narx_, rang, nom, foiz), yy in zip(qatorlar, yorliq_y, strict=True):
        y = olch.y(narx_)
        _punktir(ch, maydon_chap, y, maydon_ong, rang)

        yorliq_x = maydon_ong + 10
        # Yorliq siljigan bo'lsa, uni chizig'iga bog'lab qo'yamiz.
        if abs(yy - y) > 2:
            ch.line([(maydon_ong, y), (yorliq_x, yy)], fill=rang, width=1)
        ch.rectangle([yorliq_x, yy - 19, ENI - 8, yy + 19], fill=PANEL, outline=rang, width=2)
        ch.text((yorliq_x + 10, yy - 15), nom, font=kichik, fill=MATN_PAST)
        ch.text((yorliq_x + 10, yy + 1), _narx_matni(narx_), font=kichik, fill=rang)
        if foiz is not None:
            matn = f"{foiz:+.2f}%"
            ch.text((ENI - 16 - ch.textlength(matn, font=kichik), yy - 15),
                    matn, font=kichik, fill=rang)

    # --- Pastki izoh ------------------------------------------------------ #
    ch.text((CHAP, BOYI - 26), "HALOL CRYPTO SAVDO", font=orta, fill=MATN_PAST)
    izoh = "Spot · faqat long · kredit yelkasi yo'q"
    ch.text((maydon_ong - ch.textlength(izoh, font=kichik), BOYI - 24),
            izoh, font=kichik, fill=MATN_PAST)

    chiqish = io.BytesIO()
    rasm.save(chiqish, format="PNG", optimize=True)
    return chiqish.getvalue()
