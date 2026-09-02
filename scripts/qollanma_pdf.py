"""Qisqacha qo'llanma PDF: "Tizim qanday ishlaydi".

Nima uchun SKRIPT, tayyor PDF emas: hujjatdagi raqamlar (vaznlar,
chegaralar, limitlar) `config/default.yaml` dan o'zgarishi mumkin.
Skript saqlansa, sozlama o'zgargach hujjatni qayta chiqarish bir
buyruq: `python -m scripts.qollanma_pdf`.

Chiqish: `docs/HALOL_CRYPTO_SAVDO_qollanma.pdf`

DIQQAT — shrift: o'zbek lotinidagi `oʻ`, `gʻ` belgilari ReportLab
ning ichki Helvetica'sida YO'Q va qora kvadrat bo'lib chiqadi.
Shuning uchun DejaVu Sans ro'yxatga olinadi. Emoji ishlatilmaydi —
u ham hech qanday TTF da rangli chiqmaydi.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas

from core.config import load_config

ILDIZ = Path(__file__).resolve().parent.parent
LOGO = ILDIZ / "web" / "public" / "logo.jpg"
CHIQISH = ILDIZ / "docs" / "HALOL_CRYPTO_SAVDO_qollanma.pdf"

# Logotipdan olingan ranglar — `web/src/app/globals.css` bilan bir xil.
TURKUAZ = HexColor("#00bcd5")
APELSIN = HexColor("#f47f16")
KOK = HexColor("#10469c")
KOK_TOQ = HexColor("#0a2450")
SARIQ = HexColor("#f0b02a")
QIZIL = HexColor("#e2402f")
MATN = HexColor("#233043")
MATN_PAST = HexColor("#5d6b80")
CHIZIQ = HexColor("#d6dde8")
FON_YUMSHOQ = HexColor("#f4f7fb")

EN, BALAND = A4
CHET = 48.0

ODDIY = "HCS"
QALIN = "HCS-Bold"


def shriftlar() -> None:
    baza = Path("/usr/share/fonts/truetype/dejavu")
    pdfmetrics.registerFont(TTFont(ODDIY, str(baza / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(QALIN, str(baza / "DejaVuSans-Bold.ttf")))


# --------------------------------------------------------------------------- #
#  Chizish yordamchilari
# --------------------------------------------------------------------------- #


class Sahifa:
    """Joriy sahifa: `y` yuqoridan pastga suriladi."""

    def __init__(self, c: pdfcanvas.Canvas, quyi_sarlavha: str = "Tizim qanday ishlaydi") -> None:
        self.c = c
        self.y = BALAND - CHET
        self.raqam = 0
        # Sarlavha ostidagi qator hujjatga qarab o'zgaradi: qo'llanma
        # va yangilanish hisoboti bitta chizish kodini baham ko'radi.
        self.quyi_sarlavha = quyi_sarlavha

    # -- tuzilma ------------------------------------------------------------ #

    def yangi(self, sarlavha: str) -> None:
        if self.raqam:
            self.c.showPage()
        self.raqam += 1
        self._bosh_qism()
        self._oyoq()
        self.y = BALAND - 108
        self.bolim(sarlavha)

    def _bosh_qism(self) -> None:
        c = self.c
        c.setFillColor(KOK_TOQ)
        c.rect(0, BALAND - 62, EN, 62, stroke=0, fill=1)
        c.drawImage(
            ImageReader(str(LOGO)),
            CHET,
            BALAND - 52,
            width=42,
            height=42,
            mask="auto",
        )
        c.setFont(QALIN, 11)
        c.setFillColor(HexColor("#ffffff"))
        c.drawString(CHET + 54, BALAND - 30, "HALOL CRYPTO SAVDO")
        c.setFont(ODDIY, 8.5)
        c.setFillColor(HexColor("#9ab0d2"))
        c.drawString(CHET + 54, BALAND - 43, self.quyi_sarlavha)

    def _oyoq(self) -> None:
        c = self.c
        c.setStrokeColor(CHIZIQ)
        c.setLineWidth(0.6)
        c.line(CHET, 46, EN - CHET, 46)
        c.setFont(ODDIY, 8)
        c.setFillColor(MATN_PAST)
        c.drawString(CHET, 33, "halolcryptosavdo")
        c.drawRightString(EN - CHET, 33, str(self.raqam))

    # -- matn --------------------------------------------------------------- #

    def bolim(self, matn: str) -> None:
        c = self.c
        c.setFont(QALIN, 19)
        c.setFillColor(KOK)
        c.drawString(CHET, self.y, matn)
        self.y -= 9
        c.setStrokeColor(APELSIN)
        c.setLineWidth(2.4)
        c.line(CHET, self.y, CHET + 46, self.y)
        self.y -= 24

    def sarlavhacha(self, matn: str) -> None:
        self.y -= 6
        self.c.setFont(QALIN, 12)
        self.c.setFillColor(TURKUAZ)
        self.c.drawString(CHET, self.y, matn.upper())
        self.y -= 20

    def matn(self, matn: str, *, olcham: float = 10.8, rang: Color = MATN) -> None:
        for qator in oral(matn, ODDIY, olcham, EN - 2 * CHET):
            self.c.setFont(ODDIY, olcham)
            self.c.setFillColor(rang)
            self.c.drawString(CHET, self.y, qator)
            self.y -= olcham * 1.55
        self.y -= 6

    def bosh(self, hajm: float) -> None:
        self.y -= hajm


def oral(matn: str, shrift: str, olcham: float, kenglik: float) -> list[str]:
    """Matnni berilgan kenglikka sig'adigan qatorlarga bo'ladi."""
    qatorlar: list[str] = []
    joriy = ""
    for soz in matn.split():
        sinov = f"{joriy} {soz}".strip()
        if pdfmetrics.stringWidth(sinov, shrift, olcham) <= kenglik:
            joriy = sinov
        else:
            if joriy:
                qatorlar.append(joriy)
            joriy = soz
    if joriy:
        qatorlar.append(joriy)
    return qatorlar


def qadam(s: Sahifa, raqam: int, nom: str, izoh: str, rang: Color) -> None:
    """Raqamli doira + sarlavha + izoh. Chapda ulovchi chiziq."""
    c = s.c
    markaz_y = s.y - 3
    c.setFillColor(rang)
    c.circle(CHET + 13, markaz_y, 13, stroke=0, fill=1)
    c.setFont(QALIN, 12)
    c.setFillColor(HexColor("#ffffff"))
    c.drawCentredString(CHET + 13, markaz_y - 4.5, str(raqam))

    chap = CHET + 38
    c.setFont(QALIN, 11.5)
    c.setFillColor(MATN)
    c.drawString(chap, s.y - 1, nom)
    s.y -= 18

    for qator in oral(izoh, ODDIY, 10.3, EN - CHET - chap):
        c.setFont(ODDIY, 10.3)
        c.setFillColor(MATN_PAST)
        c.drawString(chap, s.y, qator)
        s.y -= 15
    s.y -= 15


def jadval(
    s: Sahifa,
    boshliqlar: list[str],
    qatorlar: list[list[str]],
    enlar: list[float],
    *,
    ranglar: list[Color] | None = None,
) -> None:
    """Sodda jadval: bo'yalgan sarlavha qatori, nozik ajratgichlar."""
    c = s.c
    balandlik = 24.0
    x0 = CHET

    c.setFillColor(KOK)
    c.rect(x0, s.y - balandlik + 6, sum(enlar), balandlik, stroke=0, fill=1)
    c.setFont(QALIN, 9.4)
    c.setFillColor(HexColor("#ffffff"))
    x = x0 + 9
    for nom, en in zip(boshliqlar, enlar, strict=True):
        c.drawString(x, s.y - 10, nom)
        x += en
    s.y -= balandlik + 2

    for i, qator in enumerate(qatorlar):
        if i % 2 == 0:
            c.setFillColor(FON_YUMSHOQ)
            c.rect(x0, s.y - balandlik + 6, sum(enlar), balandlik, stroke=0, fill=1)
        x = x0 + 9
        for j, (katak, en) in enumerate(zip(qator, enlar, strict=True)):
            belgi = ranglar[i] if (ranglar and j == 0) else None
            if belgi is not None:
                c.setFillColor(belgi)
                c.circle(x + 4, s.y - 6, 4, stroke=0, fill=1)
                c.setFont(ODDIY, 9.6)
                c.setFillColor(MATN)
                c.drawString(x + 14, s.y - 10, katak)
            else:
                c.setFont(QALIN if j == 0 else ODDIY, 9.6)
                c.setFillColor(MATN)
                c.drawString(x, s.y - 10, katak)
            x += en
        s.y -= balandlik
    s.y -= 18


def namuna_kartochka(s: Sahifa) -> None:
    """Signal kartochkasining namunasi — botda va saytda aynan shu ko'rinish."""
    c = s.c
    balandlik = 146.0
    kenglik = EN - 2 * CHET
    tepa = s.y + 6

    c.setFillColor(KOK_TOQ)
    c.roundRect(CHET, tepa - balandlik, kenglik, balandlik, 10, stroke=0, fill=1)
    c.setStrokeColor(APELSIN)
    c.setLineWidth(1.2)
    c.roundRect(CHET, tepa - balandlik, kenglik, balandlik, 10, stroke=1, fill=0)

    c.setFont(QALIN, 12)
    c.setFillColor(TURKUAZ)
    c.drawString(CHET + 18, tepa - 24, "DOT/USDT")
    c.setFont(ODDIY, 8.6)
    c.setFillColor(HexColor("#9ab0d2"))
    c.drawRightString(
        EN - CHET - 18, tepa - 23, "Buyurtma qoldiring - narx shu yerga kelganda ochiladi"
    )

    c.setStrokeColor(HexColor("#2a4373"))
    c.setLineWidth(0.7)
    c.line(CHET + 18, tepa - 34, EN - CHET - 18, tepa - 34)

    qatorlar = [
        ("Kirish", "0.869", "", "", HexColor("#ffffff")),
        ("Stop", "0.829", "-4.55%", "", QIZIL),
        ("TP1", "0.917", "+5.59%", "50%", TURKUAZ),
        ("TP2", "0.928", "+6.83%", "50%", TURKUAZ),
    ]
    y = tepa - 52
    for nom, narx, ozgarish, ulush, rang in qatorlar:
        c.setFont(ODDIY, 9.6)
        c.setFillColor(HexColor("#9ab0d2"))
        c.drawString(CHET + 18, y, nom)
        c.setFont(QALIN, 9.6)
        c.setFillColor(rang)
        c.drawRightString(CHET + 210, y, narx)
        c.setFont(ODDIY, 9)
        c.drawRightString(CHET + 290, y, ozgarish)
        c.setFillColor(HexColor("#9ab0d2"))
        c.drawRightString(CHET + 350, y, ulush)
        y -= 17

    c.setStrokeColor(HexColor("#2a4373"))
    c.setLineWidth(0.7)
    c.line(CHET + 18, tepa - balandlik + 32, EN - CHET - 18, tepa - balandlik + 32)
    c.setFont(ODDIY, 8.8)
    c.setFillColor(HexColor("#9ab0d2"))
    c.drawString(
        CHET + 18,
        tepa - balandlik + 15,
        "Stop butun pozitsiyani yopadi. TP larda ulush bo'yicha qismli sotiladi.",
    )
    s.y = tepa - balandlik - 20


def eslatma(s: Sahifa, matn: str, rang: Color = APELSIN) -> None:
    """Chap chekkasi bo'yalgan quticha — muhim izoh."""
    qatorlar = oral(matn, ODDIY, 10.2, EN - 2 * CHET - 30)
    balandlik = len(qatorlar) * 15 + 20
    c = s.c
    c.setFillColor(FON_YUMSHOQ)
    c.rect(CHET, s.y - balandlik + 8, EN - 2 * CHET, balandlik, stroke=0, fill=1)
    c.setFillColor(rang)
    c.rect(CHET, s.y - balandlik + 8, 3.5, balandlik, stroke=0, fill=1)
    y = s.y - 6
    for qator in qatorlar:
        c.setFont(ODDIY, 10.2)
        c.setFillColor(MATN)
        c.drawString(CHET + 18, y, qator)
        y -= 15
    s.y -= balandlik + 14


# --------------------------------------------------------------------------- #
#  Sahifalar
# --------------------------------------------------------------------------- #


def muqova(c: pdfcanvas.Canvas) -> None:
    c.setFillColor(KOK_TOQ)
    c.rect(0, 0, EN, BALAND, stroke=0, fill=1)

    # Logotipdagi burchak shakllarining ishorasi
    c.setFillColor(SARIQ)
    c.roundRect(EN - 96, BALAND - 96, 150, 150, 34, stroke=0, fill=1)
    c.setFillColor(KOK)
    c.roundRect(-54, -54, 150, 150, 34, stroke=0, fill=1)

    # Logotip OQ KARTOCHKADA: rasm foni deyarli oq, to'q ko'k ustiga
    # to'g'ridan qo'yilsa "tasodifan qolgan kvadrat" bo'lib ko'rinadi.
    olcham = 130
    ramka = olcham + 22
    c.setFillColor(HexColor("#ffffff"))
    c.roundRect((EN - ramka) / 2, BALAND - 322, ramka, ramka, 26, stroke=0, fill=1)
    c.drawImage(
        ImageReader(str(LOGO)),
        (EN - olcham) / 2,
        BALAND - 311,
        width=olcham,
        height=olcham,
        mask="auto",
    )

    c.setFont(QALIN, 28)
    c.setFillColor(HexColor("#ffffff"))
    c.drawCentredString(EN / 2, BALAND - 380, "HALOL CRYPTO SAVDO")

    c.setStrokeColor(APELSIN)
    c.setLineWidth(2.6)
    c.line(EN / 2 - 46, BALAND - 400, EN / 2 + 46, BALAND - 400)

    c.setFont(ODDIY, 16)
    c.setFillColor(TURKUAZ)
    c.drawCentredString(EN / 2, BALAND - 432, "Tizim qanday ishlaydi")

    c.setFont(ODDIY, 11)
    c.setFillColor(HexColor("#9ab0d2"))
    for i, qator in enumerate(
        [
            "Qisqacha qo'llanma: bozor qanday tahlil qilinadi,",
            "Bozor Salomatligi nima va ish qanday ketma-ketlikda boradi.",
        ]
    ):
        c.drawCentredString(EN / 2, BALAND - 462 - i * 18, qator)

    # Ichidagi bo'limlar — muqovaning pastki bo'shlig'i ish qiladi
    c.setFont(ODDIY, 10)
    for i, qator in enumerate(
        [
            "1.  Bir qarashda",
            "2.  Bozor Salomatligi",
            "3.  Ishning ketma-ketligi",
            "4.  Signal chiqqandan keyin",
        ]
    ):
        y = BALAND - 560 - i * 22
        c.setFillColor(APELSIN)
        c.circle(EN / 2 - 96, y + 3.5, 3, stroke=0, fill=1)
        c.setFillColor(HexColor("#c7d4ea"))
        c.drawString(EN / 2 - 82, y, qator)

    c.setFont(ODDIY, 9)
    c.setFillColor(HexColor("#6b83a8"))
    c.drawCentredString(EN / 2, 84, datetime.now(UTC).strftime("%d.%m.%Y") + " · ichki hujjat")
    c.drawCentredString(EN / 2, 68, "Spot savdo · leverage yo'q · qarz yo'q")


def sahifa_umumiy(s: Sahifa) -> None:
    s.yangi("1. Bir qarashda")
    s.matn(
        "Tizim mustaqil ishlaydi: har sham yopilganda quyidagi besh qadam "
        "boshidan takrorlanadi. Har qadam avvalgisidan o'tgan nomzodni "
        "oladi — birortasida to'xtasa, signal chiqmaydi.",
        rang=MATN_PAST,
    )
    s.bosh(8)

    qadam(
        s,
        1,
        "HALOL SARALASH",
        "Kuzatuvdagi 150 coin tekshiriladi. Ribo (foiz), qimor, garov va "
        "noaniq faoliyatga asoslangan loyihalar chiqarib tashlanadi. "
        "Qolgani — halol ro'yxat. Faqat shu ro'yxat tahlil qilinadi.",
        TURKUAZ,
    )
    qadam(
        s,
        2,
        "BOZOR SALOMATLIGI",
        "Savol: bugun umuman savdo qilsa bo'ladimi? Olti omil bitta 0-100 "
        "raqamga jamlanadi. Raqam pastligicha tizim yangi signal bermaydi — "
        "coinlarni tahlil qilib ham o'tirmaydi.",
        APELSIN,
    )
    qadam(
        s,
        3,
        "TAHLIL",
        "Har bir halol coin ikki strategiya bilan tekshiriladi: klassik "
        "texnik tahlil (support zonasidan xarid) va kunlik ochilish "
        "skalpingi. Har nomzodga 0-100 ball qo'yiladi.",
        KOK,
    )
    qadam(
        s,
        4,
        "RISK ENGINE",
        "Oxirgi va majburiy to'siq: 13 ta qoida. Kunlik zarar chegarasi, "
        "ochiq signallar soni, korrelyatsiya, BTC yo'nalishi, juma namozi "
        'vaqti va boshqalar. Bittasi ham "yo\'q" desa, signal chiqmaydi.',
        SARIQ,
    )
    qadam(
        s,
        5,
        "SIGNAL VA KUZATUV",
        "Telegram va saytga bir xil kartochka tushadi: Kirish, Stop, TP1, "
        "TP2. Shundan keyin narx uzluksiz kuzatiladi va natija yoziladi.",
        QIZIL,
    )

    eslatma(
        s,
        'Har bir "yo\'q" javobi saqlanadi. Shuning uchun saytdagi '
        "\"Nega signal yo'q?\" bo'limi jim turgan kunni ham izohlay oladi — "
        "tizim ishlamayotgani emas, aynan qaysi shart bajarilmagani ko'rinadi.",
    )
    eslatma(
        s,
        "Tizim ba'zan bir necha kun signal bermasligi MUMKIN va bu normal. "
        "Signal soni emas, signal sifati muhim: shart bajarilmagan joyda "
        "majburan savdo ochish - eng qimmat xato.",
        rang=TURKUAZ,
    )


def sahifa_salomatlik(s: Sahifa, konfig) -> None:  # noqa: ANN001
    s.yangi("2. Bozor Salomatligi")
    s.matn(
        "Muammo: omillar alohida-alohida tekshirilsa, ular bir-biriga zid "
        'javob beradi — bitta o\'lchov "bozor yaxshi" desa, boshqasi '
        '"balans yo\'q" deydi. Yechim: oltitasini BITTA 0-100 raqamga '
        "jamlash. Raqam har sham yopilganda qayta hisoblanadi.",
        rang=MATN_PAST,
    )

    # RAQAMLAR KONFIGURATSIYADAN. Ilgari ular qo'lda yozilgan edi va
    # vaznlar o'zgargach hujjat jimgina eskirib qoldi.
    v = konfig.market_health.weights
    s.sarlavhacha("Omillar va ularning vazni")
    jadval(
        s,
        ["Omil", "Vazn", "Nimani o'lchaydi"],
        [
            [
                "Struktura kengligi",
                f"{v.halal_structure_breadth:.0f}",
                "Ro'yxatdagi nechta coin ko'tarilish strukturasida",
            ],
            [
                "Volatillik rejimi",
                f"{v.volatility_regime:.0f}",
                "Bozorda trend bormi (o'rtacha ADX)",
            ],
            [
                "Foydalanuvchi sig'imi",
                f"{v.aggregate_user_capacity:.0f}",
                "Odamlarning puli allaqachon bandmi",
            ],
            [
                "Signal to'yinganligi",
                f"{v.signal_saturation:.0f}",
                "Ochiq signallar soni ko'p emasmi",
            ],
            [
                "BTC dominatsiyasi",
                f"{v.btc_dominance_stability:.0f}",
                "Qo'shimcha kontekst - qaror mezoni emas",
            ],
            [
                "QT davri (AMDX)",
                f"{v.quarterly_phase:.0f}",
                "Sutkaning qaysi davri - yig'ish yoki harakat",
            ],
        ],
        [152, 40, 255],
    )

    ch = konfig.scoring.thresholds
    lim = konfig.risk_engine.max_open_signals_by_health
    s.sarlavhacha("Raqam nimani boshqaradi")
    jadval(
        s,
        ["Indeks", "Rejim", "Ball chegarasi", "Ochiq signal limiti"],
        [
            [
                f"{ch.health_high_min:.0f} - 100",
                "Erkin",
                f"{ch.threshold_high_health:.0f}",
                f"{lim.high} ta",
            ],
            [
                f"{ch.health_mid_min:.0f} - {ch.health_high_min - 1:.0f}",
                "Ehtiyotkor",
                f"{ch.threshold_mid_health:.0f}",
                f"{lim.mid} ta",
            ],
            [
                f"0 - {ch.health_mid_min - 1:.0f}",
                "Yopiq",
                "signal berilmaydi",
                f"{lim.low}",
            ],
        ],
        [92, 100, 130, 125],
        ranglar=[TURKUAZ, SARIQ, QIZIL],
    )

    eslatma(
        s,
        "Ma'lumot yo'q bo'lsa omil NOL ball oladi, ya'ni indeks pasayadi. "
        '"Bilmayman" holati "yaxshi" deb hisoblanmaydi — bu ataylab: '
        "shubha bo'lganda tizim jim turishi kerak.",
    )
    eslatma(
        s,
        "Eng ko'rgazmali holat: bozor yaxshi, lekin foydalanuvchilarning "
        "10 tadan 9 tasining puli band. Indeks tushadi va chegara "
        'qattiqlashadi. Tajribali treyderning "odamlar allaqachon band, '
        'yana signal keraksiz" degan fikri shu tarzda avtomatlashtirilgan.',
        rang=TURKUAZ,
    )

    s.sarlavhacha("Kun boshida")
    s.matn(
        "UTC 00:00 atrofida, yangi kunlik sham ochilishidan oldin tizim "
        "halol ro'yxatning STRUKTURA holatiga qarab kunning umumiy "
        "yo'nalishini oldindan baholaydi. Bu - boshlang'ich qiymat, aniq "
        "o'lchov emas: kun davomida har sham yopilganda raqam qayta "
        "hisoblanadi.",
        rang=MATN_PAST,
    )


def sahifa_ketma_ketlik(s: Sahifa) -> None:
    s.yangi("3. Ishning ketma-ketligi")
    s.matn(
        "Bitta coin signalga aylanishi uchun quyidagi tekshiruvlardan "
        "SHU TARTIBDA o'tishi kerak. Qaysi bosqichda to'xtagani yozib "
        "boriladi.",
        rang=MATN_PAST,
    )

    jadval(
        s,
        ["#", "Tekshiruv", "To'xtash sababi"],
        [
            ["1", "Halol ro'yxatda bormi", "Halol ro'yxatda emas"],
            ["2", "Sham ma'lumoti yetarlimi", "Tarix qisqa yoki eskirgan"],
            ["3", "Support / Resistance zonasi", "Zona topilmadi"],
            ["4", "Narx zonaga yaqinmi", "Narx support zonasidan uzoq"],
            ["5", "Timeframelar mos keladimi", "Timeframelar bir-biriga zid"],
            ["6", "Indikatorlar tasdiqlaydimi", "Trend, RSI, MACD, hajm - yetarli emas"],
            ["7", "Stop va TP joylashadimi", "Darajalar risk qoidasiga sig'madi"],
            ["8", "Ball chegaradan yuqorimi", "Ball past (chegara indeksdan)"],
            ["9", "Risk Engine 13 ta qoidasi", "Qaysi qoida to'xtatgani yoziladi"],
        ],
        [26, 205, 268],
    )

    s.sarlavhacha("Ikki strategiya - bir xil tekshiruvdan o'tadi")
    jadval(
        s,
        ["Strategiya", "Qachon ishlaydi", "Asosi"],
        [
            ["Klassik texnik tahlil", "Doim", "Support zonasidan xarid"],
            ["Ochilish skalpingi", "Kuniga 45 daqiqa", "Kunlik diapazon buzilishi"],
        ],
        [150, 130, 219],
    )

    s.sarlavhacha("Indikatorlar o'zicha signal bermaydi")
    s.matn(
        "Trend, RSI, MACD va hajm — TASDIQLOVCHI qatlam. Signalning asosi "
        "har doim narxning support zonasidagi holati. Indikatorlar faqat "
        '"ha" yoki "yo\'q" deydi, o\'zi kirish nuqtasini tanlamaydi.',
        rang=MATN_PAST,
    )

    eslatma(
        s,
        "Skalping oynasi kuniga atigi 45 daqiqa ochiq. Qolgan vaqtda "
        "\"oyna yopiq\" yozuvi juda ko'p yig'iladi, shuning uchun u "
        'alohida ajratilgan va "sabablar" foiziga qo\'shilmaydi — aks '
        "holda haqiqiy sabablarni ko'rsatmay qo'yardi.",
    )


def sahifa_signal(s: Sahifa) -> None:
    s.yangi("4. Signal chiqqandan keyin")

    s.sarlavhacha("Kartochka - bot va saytda bir xil")
    s.matn(
        "Kirish, Stop, TP1, TP2 va har bir TP da sotiladigan ulush. "
        "Telegramdagi va saytdagi ko'rinish ataylab bir xil: foydalanuvchi "
        "\"qaysi biri to'g'ri?\" deb o'ylamasligi kerak.",
        rang=MATN_PAST,
    )
    namuna_kartochka(s)

    s.sarlavhacha("Hisob-kitob zanjiri")
    jadval(
        s,
        ["Qadam", "Nima bo'ladi"],
        [
            ["1. Balans", "Foydalanuvchi balansini kiritadi (faqat hisob uchun)"],
            ["2. Taklif", "Tizim Stop masofasidan hajmni hisoblab beradi"],
            ["3. Kalkulyator", "O'sha summa avtomatik qo'yiladi, tahrirlash mumkin"],
            ["4. Men sotib oldim", "Narx signaldan olinadi va o'zgartirilmaydi"],
            ["5. Portfel", "Haqiqiy foyda-zarar shu yozuvlardan hisoblanadi"],
        ],
        [128, 319],
    )

    s.sarlavhacha("Kuzatuv")
    s.matn(
        "Narx uzluksiz kuzatiladi. Stop butun pozitsiyani yopadi; TP larda "
        "esa pozitsiya ulushlar bo'yicha qismli sotiladi. Saytda har bir "
        "signal kirish narxidan qancha uzoqlashgani jonli ko'rinadi: "
        "yuqorida yashil, pastda qizil.",
        rang=MATN_PAST,
    )

    s.sarlavhacha("Natija esda qoladi")
    s.matn(
        "Har bir yopilgan signal saqlanadi: qaysi strategiya, qanday ball, "
        "qanday yakun. Shundan haftalik hisobot va statistika chiqadi — "
        "tizim o'z xatosini ko'rishi uchun.",
        rang=MATN_PAST,
    )

    s.bosh(6)
    eslatma(
        s,
        'Tizim hech qachon "shuncha oling" demaydi. Barcha raqamlar — '
        "hisob-kitob va tavsiya. Qaror foydalanuvchiniki, mas'uliyat ham "
        "foydalanuvchiniki. Bu moliyaviy maslahat emas.",
        rang=QIZIL,
    )


def main() -> None:
    konfig = load_config()
    shriftlar()
    CHIQISH.parent.mkdir(parents=True, exist_ok=True)
    c = pdfcanvas.Canvas(str(CHIQISH), pagesize=A4)
    c.setTitle("HALOL CRYPTO SAVDO - Tizim qanday ishlaydi")
    c.setAuthor("HALOL CRYPTO SAVDO")

    muqova(c)
    c.showPage()  # muqovadan keyin yangi varaq
    s = Sahifa(c)
    sahifa_umumiy(s)
    sahifa_salomatlik(s, konfig)
    sahifa_ketma_ketlik(s)
    sahifa_signal(s)

    c.showPage()
    c.save()
    print(f"Tayyor: {CHIQISH}")


if __name__ == "__main__":
    main()
