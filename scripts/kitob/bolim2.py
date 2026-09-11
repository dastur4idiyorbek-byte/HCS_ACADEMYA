"""2-BO'LIM: FUNDAMENTAL TAHLIL — 8-10 boblar.

1-bo'limda "kripto nima" degan savolga javob berdik. Bu bo'lim
boshqa savolga javob beradi: NARXNI NIMA HARAKATLANTIRADI.

QOIDA: bu yerda ham birorta coin tavsiya qilinmaydi. Asboblar
ko'rsatiladi, ulardan qanday foydalanish — o'quvchining ishi.
"""

from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Spacer

from scripts.kitob import sxema
from scripts.kitob.bloklar import (
    a,
    chizma_bilan,
    h2,
    h3,
    jadval,
    p,
    real_misol,
    royxat,
    savol_bilan_boshla,
    tekshiring,
    xulosa,
)
from scripts.kitob.qolip import bob_sarlavha, bolim_ajratkich

# --------------------------------------------------------------------------- #
#  Chizmalar
# --------------------------------------------------------------------------- #


def _sxema_ikki_savol() -> sxema.Drawing:
    """Fundamental va texnik tahlil qaysi savolga javob beradi."""
    d = sxema.yangi(boyi=48 * mm)
    sxema.quti(d, 10 * mm, 26 * mm, 64 * mm, 16 * mm,
               ["FUNDAMENTAL TAHLIL", "«NIMA UCHUN harakatlanadi?»",
                "sabab: talab va taklif"],
               ramka=sxema.KOK)
    sxema.quti(d, 86 * mm, 26 * mm, 64 * mm, 16 * mm,
               ["TEXNIK TAHLIL", "«QAYERDA va QACHON?»",
                "natija: grafikdagi iz"],
               ramka=sxema.TURKUAZ, ichi=sxema.colors.HexColor("#eef9fb"))
    sxema.oq(d, 42 * mm, 24 * mm, 70 * mm, 14 * mm)
    sxema.oq(d, 118 * mm, 24 * mm, 90 * mm, 14 * mm, rang=sxema.TURKUAZ)
    sxema.quti(d, 55 * mm, 4 * mm, 50 * mm, 10 * mm, ["NARX"],
               ramka=sxema.APELSIN, ichi=sxema.colors.HexColor("#fff4e8"),
               sarlavha_rang=sxema.APELSIN)
    sxema.matn(d, 80 * mm, 45 * mm,
               "Ikkalasi bitta narsaga qaraydi, lekin boshqa savol bilan",
               qalin=True, olcham=8.5)
    return d


def _sxema_talab_taklif() -> sxema.Drawing:
    """Narx nega harakatlanadi — sotib oluvchi va sotuvchi bosimi."""
    d = sxema.yangi(boyi=46 * mm)
    sxema.matn(d, 80 * mm, 41 * mm,
               "Narx — hozirgi paytda kelishilgan NUQTA", qalin=True, olcham=8.5)
    sxema.quti(d, 8 * mm, 22 * mm, 44 * mm, 12 * mm, ["SOTIB OLUVCHILAR", "talab"],
               ramka=sxema.colors.HexColor("#12a15f"),
               ichi=sxema.colors.HexColor("#eaf6ef"),
               sarlavha_rang=sxema.colors.HexColor("#0e7a49"))
    sxema.quti(d, 108 * mm, 22 * mm, 44 * mm, 12 * mm, ["SOTUVCHILAR", "taklif"],
               ramka=sxema.colors.HexColor("#d8453a"),
               ichi=sxema.colors.HexColor("#fdeeed"),
               sarlavha_rang=sxema.colors.HexColor("#a32f27"))
    sxema.quti(d, 62 * mm, 20 * mm, 36 * mm, 16 * mm, ["NARX"], ramka=sxema.KOK)
    sxema.oq(d, 53 * mm, 28 * mm, 61 * mm, 28 * mm,
             rang=sxema.colors.HexColor("#12a15f"), yorliq="bosim")
    sxema.oq(d, 107 * mm, 28 * mm, 99 * mm, 28 * mm,
             rang=sxema.colors.HexColor("#d8453a"), yorliq="bosim")
    sxema.matn(
        d, 80 * mm, 12 * mm,
        "Qaysi tomon kuchli bo'lsa, narx o'sha tomonga suriladi.",
        olcham=7.5, rang=sxema.MATN_PAST,
    )
    sxema.matn(
        d, 80 * mm, 5 * mm,
        "Fundamental tahlil aynan SHU BOSIMNING sababini qidiradi.",
        olcham=7.5, rang=sxema.APELSIN, qalin=True,
    )
    return d


def _diagramma_funding() -> sxema.Drawing:
    d = sxema.yangi(boyi=52 * mm)
    sxema.ustunli(
        d, 14 * mm, 14 * mm, 62 * mm, 28 * mm,
        [0.01, 0.03, 0.06, 0.09, 0.05, -0.02, -0.05, -0.01],
        sarlavha="Funding Rate (%)",
    )
    sxema.matn(d, 45 * mm, 7 * mm, "musbat = long lar to'laydi",
               olcham=7, rang=sxema.MATN_PAST)
    sxema.matn(d, 45 * mm, 2 * mm, "manfiy = short lar to'laydi",
               olcham=7, rang=sxema.MATN_PAST)

    sxema.ustunli(
        d, 88 * mm, 14 * mm, 62 * mm, 28 * mm,
        [-120, -80, 40, 150, 210, 90, -60, -140],
        sarlavha="Exchange Netflow (mln $)",
    )
    sxema.matn(d, 119 * mm, 7 * mm, "musbat = birjaga KIRMOQDA (sotuv bosimi?)",
               olcham=7, rang=sxema.MATN_PAST)
    sxema.matn(d, 119 * mm, 2 * mm, "manfiy = birjadan CHIQMOQDA (saqlashga?)",
               olcham=7, rang=sxema.MATN_PAST)
    return d


def _diagramma_dxy() -> sxema.Drawing:
    d = sxema.yangi(boyi=50 * mm)
    sxema.chiziqli(
        d, 14 * mm, 12 * mm, 62 * mm, 28 * mm,
        [100, 102, 105, 107, 106, 108, 110, 109],
        rang=sxema.colors.HexColor("#12a15f"),
        yorliq="DXY — dollar indeksi",
    )
    sxema.chiziqli(
        d, 88 * mm, 12 * mm, 62 * mm, 28 * mm,
        [100, 97, 93, 90, 92, 88, 85, 87],
        rang=sxema.APELSIN,
        yorliq="Risk aktivlari (odatda)",
    )
    sxema.matn(
        d, 80 * mm, 5 * mm,
        "Ko'p hollarda teskari: dollar kuchaysa, risk aktivlariga bosim tushadi. "
        "Bu QOIDA emas, KUZATUV.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    return d


def _shkala_qorquv() -> sxema.Drawing:
    d = sxema.yangi(boyi=32 * mm)
    sxema.shkala(
        d, 25 * mm, 12 * mm, 110 * mm, 22,
        chap_yorliq="0 — Haddan tashqari QO'RQUV",
        ong_yorliq="100 — Haddan tashqari OCHKO'ZLIK",
        sarlavha="Fear & Greed Index",
    )
    sxema.matn(
        d, 80 * mm, 4 * mm,
        "Bu — kayfiyat o'lchovi, bashorat emas. U «hamma nima his qilyapti» "
        "degan savolga javob beradi.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    return d


def _sxema_unlock() -> sxema.Drawing:
    """Token unlock — taklifning oldindan ma'lum oshishi."""
    d = sxema.yangi(boyi=44 * mm)
    sxema.matn(d, 80 * mm, 39 * mm, "Token Unlock — taklif OLDINDAN ma'lum oshadi",
               qalin=True, olcham=8.5)
    d.add(sxema.Line(14 * mm, 20 * mm, 148 * mm, 20 * mm,
                     strokeColor=sxema.CHIZIQ, strokeWidth=1))
    nuqtalar = [(30 * mm, "1-oy", 5), (60 * mm, "4-oy", 12),
                (95 * mm, "8-oy", 9), (128 * mm, "12-oy", 18)]
    for x, yorliq, foiz in nuqtalar:
        boyi = foiz * 0.7 * mm
        d.add(sxema.Rect(x - 5 * mm, 20 * mm, 10 * mm, boyi,
                         fillColor=sxema.colors.HexColor("#f5c9a0"),
                         strokeColor=sxema.APELSIN, strokeWidth=0.8))
        sxema.matn(d, x, 21 * mm + boyi, f"+{foiz}%", olcham=7, rang=sxema.APELSIN,
                   qalin=True)
        sxema.matn(d, x, 15 * mm, yorliq, olcham=7, rang=sxema.MATN_PAST)
    sxema.matn(
        d, 80 * mm, 8 * mm,
        "Sana jadvalda yozilgan. Ya'ni bu — kutilmagan hodisa EMAS, "
        "lekin bozor unga har doim ham tayyor bo'lmaydi.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    return d


def _sxema_rotatsiya() -> sxema.Drawing:
    """Sektor rotatsiyasi — pul qayerdan qayerga oqadi."""
    d = sxema.yangi(boyi=42 * mm)
    sxema.matn(d, 80 * mm, 37 * mm, "Pul bozorni tark etmaydi — ICHIDA ko'chadi",
               qalin=True, olcham=8.5)
    bosqichlar = [
        ("BTC", "pul birinchi shu yerga kiradi"),
        ("ETH", "keyin kattalarga tarqaladi"),
        ("Yirik alt", "so'ng o'rta hajmga"),
        ("Kichik alt", "oxirida eng xatarliga"),
    ]
    for i, (nom, izoh) in enumerate(bosqichlar):
        x = 8 * mm + i * 37 * mm
        sxema.quti(d, x, 16 * mm, 31 * mm, 14 * mm, [nom, izoh],
                   ramka=sxema.KOK if i < 2 else sxema.APELSIN)  # noqa: PLR2004
        if i:
            sxema.oq(d, x - 5.5 * mm, 23 * mm, x - 1 * mm, 23 * mm)
    sxema.matn(
        d, 80 * mm, 8 * mm,
        "Bu tartib HAR DOIM shunday bo'lmaydi. U — ko'p marta kuzatilgan "
        "naqsh, qonun emas.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    return d


def _sxema_sayt_sahifasi() -> sxema.Drawing:
    """Coin sahifasida aslida nimaga qaraladi."""
    d = sxema.yangi(boyi=54 * mm)
    sxema.matn(d, 80 * mm, 49 * mm,
               "Coin sahifasi: to'rtta raqam qolganidan muhimroq",
               qalin=True, olcham=8.5)
    # Sahifa maketi
    d.add(sxema.Rect(10 * mm, 6 * mm, 68 * mm, 38 * mm,
                     fillColor=sxema.colors.white, strokeColor=sxema.CHIZIQ,
                     strokeWidth=0.8))
    qatorlar = [
        ("Narx", "$1.24", True),
        ("24s o'zgarish", "+3.1%", False),
        ("Kapitalizatsiya", "$820 mln", True),
        ("24s hajm", "$41 mln", True),
        ("Muomaladagi soni", "660 mln / 1 mlrd", True),
        ("Reyting", "#142", False),
    ]
    for i, (nom, qiymat, muhim) in enumerate(qatorlar):
        y = 39 * mm - i * 6 * mm
        rang = sxema.KOK_TOQ if muhim else sxema.MATN_PAST
        sxema.matn(d, 14 * mm, y, nom, olcham=7, rang=rang, markaz=False,
                   qalin=muhim)
        sxema.matn(d, 74 * mm, y, qiymat, olcham=7, rang=rang, markaz=False)
        if muhim:
            sxema.oq(d, 80 * mm, y + 1.5, 88 * mm, y + 1.5)
    izohlar = [
        "KAPITALIZATSIYA — loyiha qanchalik katta.",
        "HAJM — sotish osonmi (likvidlik).",
        "MUOMALADAGI SONI — yana qancha token chiqadi?",
    ]
    for i, izoh in enumerate(izohlar):
        sxema.matn(d, 90 * mm, 36 * mm - i * 7 * mm, izoh, olcham=7,
                   rang=sxema.MATN, markaz=False)
    sxema.matn(
        d, 80 * mm, 2 * mm,
        "Narx va 24 soatlik o'zgarish — eng ko'p qaraladigan, lekin "
        "eng kam narsa aytadigan raqamlar.",
        olcham=7, rang=sxema.APELSIN,
    )
    return d


# --------------------------------------------------------------------------- #
#  Boblar
# --------------------------------------------------------------------------- #


def _bob8(u: dict) -> list:
    return [
        *bob_sarlavha(u, "8-BOB", "Fundamental tahlil — ta'rifi va nega kerak"),
        *savol_bilan_boshla(
            u,
            "Grafikda narx ko'tarildi. Siz buni ko'rdingiz. Lekin "
            "NEGA ko'tarildi — buni grafik aytmaydi. Javobni qayerdan "
            "topasiz?",
        ),
        p(u, a("Fundamental tahlil") + " — narx harakatining <b>sababini</b> "
             "qidiradigan yondashuv. U grafikka emas, grafik ortidagi "
             "voqealarga qaraydi: pul qayerga oqmoqda, kim sotmoqda, "
             "qanday qoidalar o'zgardi."),
        h2(u, "Texnik tahlildan farqi"),
        p(u, a("Texnik tahlil") + " esa faqat grafikka qaraydi: narx va hajm. "
             "Uning savoli boshqacha — \"qayerda va qachon\"."),
        p(u, "Ikkalasi raqib emas. Ular bir hodisaga ikki tomondan qaraydi: "
             "fundamental tahlil <b>sabab</b>ni, texnik tahlil <b>izni</b> "
             "o'rganadi."),
        chizma_bilan(
            _sxema_ikki_savol(),
            "8.1-chizma. Fundamental tahlil «nima uchun» deb so'raydi, "
            "texnik tahlil «qayerda va qachon» deb so'raydi.",
            u,
        ),
        h2(u, "Narxni nima harakatlantiradi"),
        p(u, "Javob bitta jumlada: <b>talab va taklif</b>. Narx — hozirgi "
             "paytda sotib oluvchi va sotuvchi kelishgan nuqta. Sotib "
             "oluvchilar bosimi kuchaysa, narx ko'tariladi; sotuvchilar "
             "bosimi kuchaysa, tushadi."),
        chizma_bilan(
            _sxema_talab_taklif(),
            "8.2-chizma. Narx — bosimlar muvozanati. Fundamental tahlil "
            "shu bosimning sababini qidiradi.",
            u,
        ),
        p(u, "Shuning uchun fundamental tahlildagi har bir asbob — aslida "
             "bitta savolga javob: <b>hozir qaysi tomon kuchliroq?</b>"),
        h3(u, "Muhim ogohlantirish"),
        p(u, "Fundamental tahlil narxning <b>qachon</b> harakatlanishini "
             "aytmaydi. Sabab bugun paydo bo'lib, narx uch oy keyin "
             "harakatlanishi mumkin. Aynan shu sababdan ko'p savdogar "
             "ikkala tahlilni birga ishlatadi."),
        xulosa(u, [
            "Fundamental tahlil <b>sababni</b>, texnik tahlil <b>izni</b> o'rganadi.",
            "Narxni harakatlantiradigan yagona narsa — talab va taklif "
            "muvozanati.",
            "Har bir fundamental asbob bitta savolga javob beradi: hozir "
            "qaysi tomon kuchliroq?",
            "Fundamental tahlil <b>vaqtni aytmaydi</b> — sabab va harakat "
            "orasida oylab tafovut bo'lishi mumkin.",
        ]),
        tekshiring(u, [
            "Fundamental va texnik tahlil qaysi savollarga javob beradi?",
            "Narx nega harakatlanadi — bir jumlada ayting.",
            "Nega faqat fundamental tahlil bilan savdo qilish qiyin?",
        ]),
        PageBreak(),
    ]


def _bob9(u: dict) -> list:
    return [
        *bob_sarlavha(u, "9-BOB", "Fundamental tahlil instrumentlari"),
        *savol_bilan_boshla(
            u,
            "\"Bosim qaysi tomonda\" degan savolga qanday qilib RAQAM bilan "
            "javob beriladi? Ko'ngil sezgisi emas, o'lchov kerak.",
        ),
        p(u, "Quyida oltita asbob. Har birida bitta qoida amal qiladi: "
             "<b>bitta ko'rsatkich yolg'iz o'zi qaror qilmaydi.</b> Ular "
             "birgalikda manzara chizadi."),
        h2(u, "Funding Rate va Open Interest"),
        p(u, a("Funding Rate") + " — fyuchers bozorida long va short "
             "tomonlar bir-biriga to'laydigan kichik to'lov. U bozorni "
             "muvozanatda ushlab turish uchun ishlaydi."),
        *royxat(u, [
            "<b>Musbat</b> — long lar ko'p, ular short larga to'laydi. "
            "Ya'ni ko'pchilik o'sishga tikkan.",
            "<b>Manfiy</b> — short lar ko'p, ular long larga to'laydi.",
        ]),
        p(u, "Juda yuqori musbat qiymat ko'pincha <b>ehtiyotkorlik belgisi</b>: "
             "hamma bir tomonga tikkan bo'lsa, keskin teskari harakat "
             "ko'proq odamni zarar ko'rsatadi."),
        p(u, a("Open Interest") + " — ochiq turgan shartnomalar soni. U "
             "\"bozorda qancha pul band\" degan savolga javob beradi. "
             "Narx o'ssa-yu Open Interest ham o'ssa — harakat ortida "
             "yangi pul bor demakdir."),
        h2(u, "Exchange Netflow — kitlar harakati"),
        p(u, a("Exchange Netflow") + " — birjalarga kirayotgan va chiqayotgan "
             "coin farqi. Mantiq oddiy: coinni sotish uchun avval birjaga "
             "yuborish kerak."),
        chizma_bilan(
            _diagramma_funding(),
            "9.1-chizma. Ikkala ko'rsatkichda ham ISHORA (musbat/manfiy) "
            "kattalikdan ko'ra ko'proq narsa aytadi.",
            u,
        ),
        p(u, "Diqqat: bu ham qat'iy qoida emas. Birjaga kelgan coin "
             "sotilmasligi ham mumkin — masalan garov sifatida qo'yiladi."),
        h2(u, "DXY — dollar indeksi"),
        p(u, a("DXY") + " — dollarning boshqa yirik valyutalarga nisbatan "
             "kuchi. Kripto bilan bevosita aloqasi yo'q, lekin kuzatish "
             "ko'rsatadi: dollar kuchayganda risk aktivlariga bosim tushadi."),
        chizma_bilan(
            _diagramma_dxy(),
            "9.2-chizma. Teskari bog'liqlik ko'p kuzatilgan, lekin u "
            "doimiy emas — ba'zi davrlarda ikkalasi birga harakatlanadi.",
            u,
        ),
        h2(u, "Fear & Greed Index"),
        p(u, a("Fear & Greed Index") + " — bozor kayfiyatini 0 dan 100 gacha "
             "o'lchaydigan ko'rsatkich. U narx, hajm, ijtimoiy tarmoq "
             "faolligi kabi bir necha manbadan yig'iladi."),
        chizma_bilan(
            _shkala_qorquv(),
            "9.3-chizma. Shkala kayfiyatni ko'rsatadi, kelajakni emas.",
            u,
        ),
        p(u, "Bu ko'rsatkich ko'pincha <b>teskari</b> o'qiladi: haddan "
             "tashqari ochko'zlik — ehtiyotkorlik vaqti, haddan tashqari "
             "qo'rquv — diqqat bilan qarash vaqti. Lekin \"qo'rquv bor, "
             "demak sotib olaman\" degan mexanik qoida ishlamaydi."),
        h2(u, "Token Unlock va Listing"),
        p(u, a("Token Unlock") + " — loyiha yaratilganda bloklangan "
             "tokenlarning jadval bo'yicha ochilishi. Bu — taklifning "
             "oldindan ma'lum oshishi."),
        chizma_bilan(
            _sxema_unlock(),
            "9.4-chizma. Unlock sanasi va miqdori oldindan e'lon qilinadi. "
            "Uni tekshirmaslik — o'z aybingiz.",
            u,
        ),
        p(u, a("Listing") + " — coinning yangi birjaga qo'shilishi (odatda "
             "yangi xaridorlar demak), " + a("delisting") + " esa aksincha: "
             "birjadan chiqarilishi. Ikkinchisi ko'pincha keskin tushish "
             "bilan kechadi."),
        h2(u, "Sektor rotatsiyasi"),
        p(u, a("Sektor rotatsiyasi") + " — pulning bozor ichida bir turdan "
             "ikkinchisiga ko'chishi."),
        chizma_bilan(
            _sxema_rotatsiya(),
            "9.5-chizma. Ko'p marta kuzatilgan tartib — lekin u qonun emas.",
            u,
        ),
        real_misol(
            u,
            "BTC/USDT kunlik grafik: Funding Rate keskin yuqori bo'lgan "
            "davr va undan keyingi harakat. Ostida Funding Rate "
            "diagrammasi ko'rinsin.",
        ),
        xulosa(u, [
            "Funding Rate — kim kimga to'layotgani; haddan tashqari bir "
            "tomonlamalik ehtiyotkorlik belgisi.",
            "Exchange Netflow — coin birjaga kirmoqdami yoki chiqmoqdami.",
            "DXY bilan teskari bog'liqlik ko'p kuzatilgan, lekin doimiy emas.",
            "Fear & Greed — kayfiyat o'lchovi, bashorat emas.",
            "Token Unlock oldindan e'lon qilinadi — uni tekshirmaslik "
            "o'z aybingiz.",
        ]),
        tekshiring(u, [
            "Funding Rate musbat bo'lsa, kim kimga to'laydi?",
            "Exchange Netflow musbat bo'lishi nimani anglatishi mumkin — "
            "va nega bu aniq xulosa emas?",
            "Fear & Greed 85 ni ko'rsatdi. Bu \"soting\" degan buyruqmi?",
        ]),
        PageBreak(),
    ]


def _bob10(u: dict) -> list:
    return [
        *bob_sarlavha(u, "10-BOB", "Fundamental ma'lumot uchun veb-saytlar"),
        *savol_bilan_boshla(
            u,
            "Yuqoridagi barcha raqamlarni qayerdan olasiz? Va ulardan "
            "qaysilari uchun pul to'lash kerak?",
        ),
        p(u, "Yaxshi xabar: boshlanish uchun kerak bo'lgan narsaning "
             "deyarli hammasi <b>bepul</b>."),
        h2(u, "Asosiy manbalar"),
        jadval(
            u,
            ["Sayt", "Nima ko'rsatadi", "Nimaga qaraysiz"],
            [
                ["CoinGecko", "Narx, kapitalizatsiya, hajm, muomaladagi soni",
                 "Loyihaning hajmi va likvidligi"],
                ["CoinMarketCap", "Yuqoridagiga o'xshash + birjalar ro'yxati",
                 "Coin qaysi birjalarda savdo qilinadi"],
                ["alternative.me", "Fear & Greed Index",
                 "Bugungi kayfiyat va uning tarixi"],
                ["DeFiLlama", "DeFi loyihalaridagi umumiy mablag' (TVL)",
                 "Loyihada haqiqiy pul bormi"],
                ["CryptoPanic", "Yangiliklar to'plami",
                 "Keskin harakat ortida yangilik bormi"],
                ["TradingView", "Grafiklar, DXY, indekslar",
                 "Texnik tahlil va bozorlararo bog'liqlik"],
            ],
            [30 * mm, 66 * mm, 52 * mm],
        ),
        Spacer(1, 4 * mm),
        chizma_bilan(
            _sxema_sayt_sahifasi(),
            "10.1-chizma. Har qanday coin sahifasida eng ko'p qaraladigan "
            "raqam (narx) eng kam narsa aytadi.",
            u,
        ),
        h2(u, "Raqamni qanday o'qish kerak"),
        p(u, "Sayt raqam beradi, ma'no bermaydi. Uchta savol yordam beradi:"),
        *royxat(u, [
            "<b>Bu raqam nimaga nisbatan?</b> \"Hajm 500 mln\" — bu ko'pmi? "
            "Faqat o'sha coinning o'tgan oydagi hajmi bilan solishtirganda "
            "ma'no chiqadi.",
            "<b>Bu raqam qachondan beri shunday?</b> Bir kunlik sakrash va "
            "uch oylik yo'nalish — ikki xil narsa.",
            "<b>Bu raqam kimga foydali?</b> Ba'zi ko'rsatkich loyihaning "
            "o'zi tomonidan e'lon qilinadi — mustaqil manba emas.",
        ]),
        h2(u, "Bepul va pullik manbalar"),
        p(u, "Pullik xizmatlar odatda uch narsani beradi: <b>tezroq</b> "
             "ma'lumot, <b>chuqurroq</b> on-chain tahlil va <b>tayyor "
             "signal</b>. Birinchi ikkitasi foydali bo'lishi mumkin."),
        p(u, "Uchinchisiga esa ehtiyot bo'ling: tayyor signal sizga "
             "<b>tushunish</b> bermaydi. Bu kitobning butun maqsadi esa "
             "aynan tushunish."),
        h3(u, "Ma'lumotni tekshirish odati"),
        p(u, "Bitta manbaga suyanmang. Muhim raqamni ikkinchi saytda "
             "tekshiring — ular ba'zan jiddiy farq qiladi, chunki "
             "hisoblash usuli boshqacha bo'lishi mumkin."),
        real_misol(
            u,
            "CoinGecko va DeFiLlama dan bitta loyihaning bir sanadagi "
            "ko'rsatkichlari yonma-yon — farqni ko'rsatish uchun.",
        ),
        xulosa(u, [
            "Boshlash uchun kerakli ma'lumotning deyarli hammasi bepul.",
            "Sayt raqam beradi, ma'noni siz chiqarasiz — nimaga nisbatan, "
            "qachondan beri, kimga foydali.",
            "Bir kunlik sakrash va uch oylik yo'nalish ikki xil narsa.",
            "Pullik \"tayyor signal\" tushunish o'rnini bosmaydi.",
        ]),
        tekshiring(u, [
            "\"Hajm 500 mln dollar\" — bu ko'pmi yoki kammi? Javob berish "
            "uchun yana nima bilishingiz kerak?",
            "Nega bitta manbaga suyanish xavfli?",
            "Pullik xizmatning qaysi qismi haqiqatan foydali bo'lishi mumkin?",
        ]),
        PageBreak(),
    ]


def bolim2(u: dict) -> list:
    return [
        *bolim_ajratkich(u, "2-BO‘LIM", "FUNDAMENTAL TAHLIL"),
        *_bob8(u),
        *_bob9(u),
        *_bob10(u),
    ]
