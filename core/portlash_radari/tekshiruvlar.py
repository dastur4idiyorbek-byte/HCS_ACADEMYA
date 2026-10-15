"""7 ta mustaqil tekshiruv — BALL EMAS, SANOQ (`docs/MODUL_4_0_0.md`, 5-6).

Har tekshiruv uch holatdan birini beradi:

    ha            ✅ tasdiqlandi
    yoq           ❌ tasdiqlanmadi
    malumot_yoq   ⚪ ma'lumot yo'q — na plyus, na minus

Natija — nechtasi ✅. Og'irlik, formula, ko'paytirish YO'Q. Bu
loyihaning o'z darsi: ball tizimi ekranda chiroyli ko'ringan, lekin
yaxshi nomzodlarning ~85% ini jimgina chetlab o'tgan.

IKKI GURUH (sanoq hali ham ball emas, faqat bo'lib ko'rsatiladi):

    harakat  — "bo'lyapti":                  hajm, narx, btc
    yoqilgi  — "bo'lishi uchun sharoit bor": funding, oi, long_short, taminot

Bo'linma nima uchun: harakat tekshiruvlari bir-biriga bog'liq — 287%
o'sgan coin narx va BTC tekshiruvidan avtomatik o'tadi. Yoqilg'i esa
"erta" holatni ko'rsatadi: sharoit bor, harakat hali yo'q.

QAT'IY CHEGARA: bu yerda hech qanday narx darajasi hisoblanmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.portlash_radari.sozlama import Chegaralar

HA = "ha"
YOQ = "yoq"
MALUMOT_YOQ = "malumot_yoq"

HARAKAT = "harakat"
YOQILGI = "yoqilgi"

#: Kod -> guruh. TARTIB MUHIM: ekranda shu tartibda chiqadi.
TEKSHIRUVLAR: tuple[tuple[str, str], ...] = (
    ("hajm", HARAKAT),
    ("narx", HARAKAT),
    ("funding", YOQILGI),
    ("oi", YOQILGI),
    ("long_short", YOQILGI),
    ("btc", HARAKAT),
    ("taminot", YOQILGI),
)

#: 30 kunlik o'rtacha kamida shuncha kundan olingan bo'lsin. Kamroq
#: bo'lsa — "yangi listing", o'rtacha ishonchsiz.
MIN_TARIX_KUN = 7

#: Funding standart oralig'i (soat). `fundingInfo` da yo'q coin — 8 soat.
STANDART_FUNDING_SOAT = 8


@dataclass(frozen=True, slots=True)
class CoinMalumoti:
    """Bitta coin haqida yig'ilgan xom ma'lumot. `None` — bilmaymiz."""

    symbol: str
    belgi: str
    narx: float | None = None
    ozgarish_24s: float | None = None
    hajm_24s: float | None = None
    ortacha_30k: float | None = None
    tarix_kunlar: int = 0
    #: `lastFundingRate` — KASR (0.0001 = 0.01%)
    funding_stavka: float | None = None
    funding_oraliq_soat: int = STANDART_FUNDING_SOAT
    #: OI kontrakt sonida, eskidan yangiga
    oi_qatorlar: tuple[float, ...] = ()
    long_short: float | None = None
    btc_ozgarish: float | None = None
    aylanma_pct: float | None = None
    unlock_kun: int | None = None
    unlock_pct: float | None = None
    #: Binance'da yosh coin — 30 kunlik o'rtachasi listing shovqinidan iborat
    yangi_listing: bool = False


@dataclass(frozen=True, slots=True)
class Tekshiruv:
    kod: str
    guruh: str
    holat: str
    qiymat: float | None
    chegara: float | None
    manba: str
    qoshimcha: dict = field(default_factory=dict)

    def lugat(self) -> dict:
        return {
            "kod": self.kod,
            "guruh": self.guruh,
            "holat": self.holat,
            "qiymat": _yaxlit(self.qiymat),
            "chegara": self.chegara,
            "manba": self.manba,
            "qoshimcha": self.qoshimcha,
        }


@dataclass(frozen=True, slots=True)
class Sanoq:
    tasdiq: int
    harakat: int
    yoqilgi: int
    malumot_yoq: int


def _yaxlit(x: float | None) -> float | None:
    return None if x is None else round(float(x), 4)


def _holat(shart: bool) -> str:
    return HA if shart else YOQ


# --------------------------------------------------------------------- #
#  Har bir tekshiruv
# --------------------------------------------------------------------- #


def hajm_nisbati(coin: CoinMalumoti) -> float | None:
    """24s hajm / 30 kunlik o'rtacha. Tarix yetarli bo'lmasa — `None`.

    Yangi listingda ham `None`: uning "o'rtachasi" listing kunlaridagi
    sakrashdan iborat va nisbat hech narsani anglatmaydi
    (`docs/MODUL_4_0_0.md`, 6-bo'lim: "ularda o'rtacha yo'q").
    """
    if (
        coin.yangi_listing
        or coin.hajm_24s is None
        or coin.ortacha_30k is None
        or coin.ortacha_30k <= 0
        or coin.tarix_kunlar < MIN_TARIX_KUN
    ):
        return None
    return coin.hajm_24s / coin.ortacha_30k


def hajm(coin: CoinMalumoti, ch: Chegaralar) -> Tekshiruv:
    nisbat = hajm_nisbati(coin)
    qoshimcha = {"kunlar": coin.tarix_kunlar}
    if nisbat is None:
        return Tekshiruv("hajm", HARAKAT, MALUMOT_YOQ, None, ch.hajm_x, "binance_hajm", qoshimcha)
    return Tekshiruv(
        "hajm", HARAKAT, _holat(nisbat >= ch.hajm_x), nisbat, ch.hajm_x, "binance_hajm", qoshimcha
    )


def narx(coin: CoinMalumoti, ch: Chegaralar) -> Tekshiruv:
    o = coin.ozgarish_24s
    if o is None:
        return Tekshiruv("narx", HARAKAT, MALUMOT_YOQ, None, ch.narx_ozgarish_pct, "binance_ticker")
    return Tekshiruv(
        "narx", HARAKAT, _holat(abs(o) >= ch.narx_ozgarish_pct), o,
        ch.narx_ozgarish_pct, "binance_ticker",
    )


def funding_8s(stavka: float, oraliq_soat: int) -> float:
    """Kasr stavka -> 8 soatlik ekvivalent FOIZ.

    Binance'da oraliq coinga qarab 8, 4 yoki 1 soat. 4 soatlik coinda
    0.1% amalda 8 soatlikdagi 0.2% ga teng — solishtirishdan oldin
    bir o'lchovga keltiriladi.
    """
    soat = oraliq_soat if oraliq_soat and oraliq_soat > 0 else STANDART_FUNDING_SOAT
    return stavka * 100.0 * STANDART_FUNDING_SOAT / soat


def funding(coin: CoinMalumoti, ch: Chegaralar) -> Tekshiruv:
    if coin.funding_stavka is None:
        return Tekshiruv(
            "funding", YOQILGI, MALUMOT_YOQ, None, ch.funding_8s_pct, "binance_premium"
        )
    qiymat = funding_8s(coin.funding_stavka, coin.funding_oraliq_soat)
    return Tekshiruv(
        "funding", YOQILGI, _holat(abs(qiymat) >= ch.funding_8s_pct), qiymat,
        ch.funding_8s_pct, "binance_premium",
        {
            "oraliq_soat": coin.funding_oraliq_soat,
            "xom_pct": _yaxlit(coin.funding_stavka * 100.0),
        },
    )


def oi_ozgarishi(qatorlar: tuple[float, ...]) -> float | None:
    """Birinchi va oxirgi nuqta orasidagi o'sish (%)."""
    if len(qatorlar) < 2 or qatorlar[0] <= 0:
        return None
    return (qatorlar[-1] / qatorlar[0] - 1.0) * 100.0


def oi(coin: CoinMalumoti, ch: Chegaralar) -> Tekshiruv:
    """OI KONTRAKT SONIDA. Dollar qiymati narx bilan o'sadi — u
    pozitsiya o'sishini narx harakatidan ajrata olmasdi.

    OYNA TO'LISHI SHART. 2-3 soatlik coinda birinchi soatning OI si
    deyarli nol bo'ladi va "+800%" chiqardi — deyarli har yangi listing
    yolg'on ✅ olardi. Oyna to'lmasa ⚪.
    """
    soat = max(len(coin.oi_qatorlar) - 1, 0)
    ozgarish = oi_ozgarishi(coin.oi_qatorlar) if soat >= ch.oi_oyna_soat else None
    if ozgarish is None:
        return Tekshiruv(
            "oi", YOQILGI, MALUMOT_YOQ, None, ch.oi_osish_pct, "binance_oi", {"soat": soat}
        )
    return Tekshiruv(
        "oi", YOQILGI, _holat(ozgarish >= ch.oi_osish_pct), ozgarish,
        ch.oi_osish_pct, "binance_oi", {"soat": soat},
    )


def long_short(coin: CoinMalumoti, ch: Chegaralar) -> Tekshiruv:
    """Istalgan tomonga og'ish: 2.5:1 ham, 1:2.5 ham ✅."""
    r = coin.long_short
    if r is None or r <= 0:
        return Tekshiruv(
            "long_short", YOQILGI, MALUMOT_YOQ, None, ch.long_short_nisbat, "binance_long_short"
        )
    ogish = max(r, 1.0 / r)
    return Tekshiruv(
        "long_short", YOQILGI, _holat(ogish >= ch.long_short_nisbat), r,
        ch.long_short_nisbat, "binance_long_short",
    )


def btc(coin: CoinMalumoti, ch: Chegaralar) -> Tekshiruv:
    if coin.ozgarish_24s is None or coin.btc_ozgarish is None:
        return Tekshiruv("btc", HARAKAT, MALUMOT_YOQ, None, ch.btc_farq_pp, "binance_ticker")
    farq = coin.ozgarish_24s - coin.btc_ozgarish
    return Tekshiruv(
        "btc", HARAKAT, _holat(abs(farq) >= ch.btc_farq_pp), farq, ch.btc_farq_pp,
        "binance_ticker",
    )


def taminot(coin: CoinMalumoti, ch: Chegaralar) -> Tekshiruv:
    """Past aylanma YOKI yaqin katta unlock.

    QATTIQ FILTR EMAS. LSK da aylanma ~70.6% edi va qulfdagi qismning
    bo'shatilishi portlash sabablaridan biri bo'lgan. Past aylanma —
    xavf emas, ko'pincha portlash ehtimolini OSHIRADI.

    Aylanma ma'lum, unlock esa yo'q (yoki kichik) bo'lsa — ❌: biz
    ta'minot tarkibini bilamiz va u shartga tushmaydi. Ikkalasi ham
    noma'lum — ⚪.
    """
    aylanma_ha = coin.aylanma_pct is not None and coin.aylanma_pct < ch.aylanma_max_pct
    unlock_ha = (
        coin.unlock_kun is not None
        and coin.unlock_kun <= ch.unlock_kun
        and coin.unlock_pct is not None
        and coin.unlock_pct >= ch.unlock_min_pct
    )
    qoshimcha = {
        "aylanma_pct": _yaxlit(coin.aylanma_pct),
        "unlock_kun": coin.unlock_kun,
        "unlock_pct": _yaxlit(coin.unlock_pct),
    }
    if aylanma_ha or unlock_ha:
        holat = HA
    elif coin.aylanma_pct is not None:
        holat = YOQ
    else:
        holat = MALUMOT_YOQ
    return Tekshiruv(
        "taminot", YOQILGI, holat, coin.aylanma_pct, ch.aylanma_max_pct,
        "coingecko_defillama", qoshimcha,
    )


_FUNKSIYALAR = {
    "hajm": hajm,
    "narx": narx,
    "funding": funding,
    "oi": oi,
    "long_short": long_short,
    "btc": btc,
    "taminot": taminot,
}


def hammasi(coin: CoinMalumoti, ch: Chegaralar) -> list[Tekshiruv]:
    """7 tekshiruv — `TEKSHIRUVLAR` tartibida."""
    return [_FUNKSIYALAR[kod](coin, ch) for kod, _ in TEKSHIRUVLAR]


def sana(tekshiruvlar: list[Tekshiruv]) -> Sanoq:
    return Sanoq(
        tasdiq=sum(t.holat == HA for t in tekshiruvlar),
        harakat=sum(t.holat == HA and t.guruh == HARAKAT for t in tekshiruvlar),
        yoqilgi=sum(t.holat == HA and t.guruh == YOQILGI for t in tekshiruvlar),
        malumot_yoq=sum(t.holat == MALUMOT_YOQ for t in tekshiruvlar),
    )
