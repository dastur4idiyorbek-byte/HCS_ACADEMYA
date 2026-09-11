"""6-BO'LIM: RISK MENEJMENT — 21-23 boblar.

BU BO'LIM ENG MUHIMI va u ATAYLAB oxirida turadi. Sabab: risk
qoidalarining ma'nosi faqat oldingi bo'limlarni o'qigandan keyin
ochiladi. "Stop qo'ying" degan gap 12-bobdagi qo'llab-quvvatlash
tushunchasisiz quruq nasihat bo'lib qolardi.

QOIDA: bu yerda ham raqam TAVSIYA qilinmaydi. Formulalar
ko'rsatiladi, qiymatni o'quvchi o'zi tanlaydi.
"""

from __future__ import annotations

from reportlab.platypus import PageBreak, Spacer

from scripts.kitob import chizma as ch
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

mm = sxema.mm


# --------------------------------------------------------------------------- #
#  Chizmalar
# --------------------------------------------------------------------------- #


def _diagramma_tiklanish() -> sxema.Drawing:
    """Zarardan keyin qancha foyda kerak — nomutanosiblik."""
    d = sxema.yangi(boyi=52 * mm)
    sxema.matn(d, 80 * mm, 47 * mm,
               "Zarar va tiklanish MUTANOSIB EMAS", qalin=True, olcham=9)
    juftlar = [(10, 11), (25, 33), (50, 100), (75, 300), (90, 900)]
    x0, boyi = 16 * mm, 26 * mm
    eni_bir = 25 * mm
    for i, (zarar, tiklanish) in enumerate(juftlar):
        x = x0 + i * eni_bir
        hz = boyi * zarar / 100
        ht = boyi * min(tiklanish, 100) / 100
        d.add(sxema.Rect(x, 14 * mm, 8 * mm, hz,
                         fillColor=sxema.colors.HexColor("#f3b0aa"),
                         strokeColor=sxema.colors.HexColor("#d8453a"),
                         strokeWidth=0.7))
        d.add(sxema.Rect(x + 10 * mm, 14 * mm, 8 * mm, ht,
                         fillColor=sxema.colors.HexColor("#a8dcc0"),
                         strokeColor=sxema.colors.HexColor("#12a15f"),
                         strokeWidth=0.7))
        sxema.matn(d, x + 4 * mm, 14 * mm + hz + 1.5 * mm, f"−{zarar}%",
                   olcham=6.8, rang=sxema.colors.HexColor("#a32f27"), qalin=True)
        sxema.matn(d, x + 14 * mm, 14 * mm + ht + 1.5 * mm, f"+{tiklanish}%",
                   olcham=6.8, rang=sxema.colors.HexColor("#0e7a49"), qalin=True)
        sxema.matn(d, x + 9 * mm, 9 * mm, f"{zarar}% yo'qotish",
                   olcham=6.5, rang=sxema.MATN_PAST)
    sxema.matn(
        d, 80 * mm, 3 * mm,
        "50% yo'qotsangiz, tenglashish uchun 100% kerak. 90% yo'qotsangiz — 900%.",
        olcham=7.5, rang=sxema.APELSIN, qalin=True,
    )
    return d


def _grafik_stop_tp() -> sxema.Drawing:
    """Kirish, Stop va TP — bitta savdoning uch darajasi."""
    ketma = ch.shamlar([
        (100, 101, 99.6, 100.6), (100.6, 101.2, 99.8, 100.2),
        (100.2, 100.6, 99.2, 100.4),   # kirish
        (100.4, 102.4, 100.2, 102), (102, 103.6, 101.8, 103.2),
        (103.2, 104.4, 102.8, 104.2), (104.2, 106.2, 104, 106),
        (106, 106.4, 105.2, 105.8),
    ])
    d, k = ch.sham_chizma(ketma, boyi=58 * mm)
    ch.gorizontal(d, k, 100.4, "KIRISH", rang=ch.KOK, uzuq=False)
    ch.gorizontal(d, k, 98.4, "STOP — bu yerdan chiqamiz", rang=ch.SHAM_TUSHDI)
    ch.gorizontal(d, k, 106.4, "TP — nishon", rang=ch.SHAM_OSDI)
    ch.zona(d, k, 0, 7, 98.4, 100.4, "XAVF (1R)", rang=ch.SHAM_TUSHDI,
            shaffoflik=0.10)
    ch.zona(d, k, 0, 7, 100.4, 106.4, "FOYDA (3R)", rang=ch.SHAM_OSDI,
            shaffoflik=0.10)
    return d


def _diagramma_rr() -> sxema.Drawing:
    """R:R va kerakli g'alaba foizi."""
    d = sxema.yangi(boyi=48 * mm)
    sxema.matn(d, 80 * mm, 43 * mm,
               "Qanchalik uzoq nishon — shunchalik kam g'alaba yetarli",
               qalin=True, olcham=8.5)
    juftlar = [("1:1", 50), ("1:2", 33.3), ("1:3", 25), ("1:5", 16.7)]
    x0, eni = 20 * mm, 30 * mm
    for i, (nisbat, foiz) in enumerate(juftlar):
        x = x0 + i * eni
        boyi = 26 * mm * foiz / 50
        d.add(sxema.Rect(x, 12 * mm, 14 * mm, boyi,
                         fillColor=sxema.colors.HexColor("#cfe2f7"),
                         strokeColor=sxema.KOK, strokeWidth=0.8))
        sxema.matn(d, x + 7 * mm, 12 * mm + boyi + 2 * mm, f"{foiz:.0f}%",
                   olcham=8, rang=sxema.KOK_TOQ, qalin=True)
        sxema.matn(d, x + 7 * mm, 7 * mm, f"R:R = {nisbat}", olcham=7.5,
                   rang=sxema.MATN)
    sxema.matn(
        d, 80 * mm, 2 * mm,
        "Ustun — nolda qolish uchun kerak bo'lgan eng kam g'alaba foizi "
        "(komissiyasiz).",
        olcham=7, rang=sxema.MATN_PAST,
    )
    return d


def _sxema_hajm() -> sxema.Drawing:
    """Pozitsiya hajmi formulasi."""
    d = sxema.yangi(boyi=44 * mm)
    sxema.matn(d, 80 * mm, 39 * mm, "Pozitsiya hajmi — TAXMIN emas, HISOB",
               qalin=True, olcham=9)
    sxema.quti(d, 8 * mm, 22 * mm, 40 * mm, 12 * mm,
               ["1. XAVF PULI", "balans × xavf %"], ramka=sxema.KOK)
    sxema.quti(d, 60 * mm, 22 * mm, 40 * mm, 12 * mm,
               ["2. STOP MASOFASI", "kirish − stop (%)"], ramka=sxema.KOK)
    sxema.quti(d, 112 * mm, 22 * mm, 40 * mm, 12 * mm,
               ["3. HAJM", "1 ÷ 2"], ramka=sxema.APELSIN,
               ichi=sxema.colors.HexColor("#fff4e8"),
               sarlavha_rang=sxema.APELSIN)
    sxema.oq(d, 49 * mm, 28 * mm, 59 * mm, 28 * mm)
    sxema.oq(d, 101 * mm, 28 * mm, 111 * mm, 28 * mm)
    sxema.matn(
        d, 80 * mm, 13 * mm,
        "Misol: balans $1 000, xavf 1% = $10. Stop 4% uzoqda. "
        "Hajm = 10 ÷ 0.04 = $250.",
        olcham=7.5, rang=sxema.MATN,
    )
    sxema.matn(
        d, 80 * mm, 6 * mm,
        "DIQQAT: $250 — bu pozitsiya hajmi. Xavf ostidagi pul esa faqat $10.",
        olcham=7.5, rang=sxema.APELSIN, qalin=True,
    )
    return d


def _sxema_hissiyot() -> sxema.Drawing:
    """Qo'rquv va ochko'zlik aylanasi."""
    d = sxema.yangi(boyi=48 * mm)
    sxema.matn(d, 80 * mm, 43 * mm, "Eng ko'p takrorlanadigan halqa",
               qalin=True, olcham=9)
    bosqichlar = [
        ("Narx o'sdi", "«kech qolyapman»"),
        ("Shoshib kirdim", "reja yo'q"),
        ("Narx tushdi", "«biroz kutaman»"),
        ("Stop yo'q edi", "zarar kattalashdi"),
    ]
    for i, (nom, izoh) in enumerate(bosqichlar):
        x = 8 * mm + i * 37 * mm
        rang = sxema.KOK if i < 2 else sxema.colors.HexColor("#d8453a")  # noqa: PLR2004
        sxema.quti(d, x, 18 * mm, 32 * mm, 15 * mm, [nom, izoh], ramka=rang,
                   sarlavha_rang=rang)
        if i:
            sxema.oq(d, x - 4.5 * mm, 25 * mm, x - 1 * mm, 25 * mm)
    sxema.oq(d, 140 * mm, 17 * mm, 140 * mm, 11 * mm, rang=sxema.MATN_PAST)
    sxema.oq(d, 140 * mm, 11 * mm, 24 * mm, 11 * mm, rang=sxema.MATN_PAST,
             uzuq=True)
    sxema.oq(d, 24 * mm, 11 * mm, 24 * mm, 17 * mm, rang=sxema.MATN_PAST)
    sxema.matn(d, 80 * mm, 6 * mm, "va yana boshidan",
               olcham=7, rang=sxema.MATN_PAST)
    sxema.matn(
        d, 80 * mm, 1 * mm,
        "Halqani REJA uzadi: kirish, Stop va hajm OLDINDAN yozilsa, "
        "his-tuyg'uga o'rin qolmaydi.",
        olcham=7.5, rang=sxema.APELSIN, qalin=True,
    )
    return d


# --------------------------------------------------------------------------- #
#  Boblar
# --------------------------------------------------------------------------- #


def _bob21(u: dict) -> list:
    return [
        *bob_sarlavha(u, "21-BOB", "Risk menejment — nega bu ENG MUHIM bob"),
        *savol_bilan_boshla(
            u,
            "Ikki savdogar bir xil tahlil qildi va bir xil savdoga kirdi. "
            "Bir yildan keyin biri foydada, ikkinchisi hisobini yo'qotdi. "
            "Farq nimada edi?",
        ),
        p(u, "Farq tahlilda emas. Farq — <b>har savdoga qancha pul "
             "qo'yganlarida</b> va <b>qachon chiqqanlarida</b>."),
        h2(u, "Matematik haqiqat"),
        p(u, "Bu bo'limning butun asosi bitta nomutanosiblikda: zarar va "
             "tiklanish teng emas."),
        chizma_bilan(
            _diagramma_tiklanish(),
            "21.1-chizma. Yo'qotish qanchalik katta bo'lsa, tiklanish "
            "shunchalik tez imkonsizga aylanadi.",
            u,
        ),
        p(u, "Hisoblab ko'ring: 50% yo'qotgan odam hisobini tiklash uchun "
             "<b>100% foyda</b> ko'rishi kerak. 90% yo'qotgan odamga esa "
             "900% kerak."),
        p(u, "Aynan shuning uchun risk menejment qoidasi bitta gapda "
             "ifodalanadi: <b>avval yo'qotmaslikni o'rgan, keyin "
             "yutishni.</b>"),
        h2(u, "\"Yaxshi tahlil, yomon risk\" nima demak"),
        p(u, "Tasavvur qiling: savdolaringizning 60 foizi foydali. Bu — "
             "yaxshi ko'rsatkich."),
        p(u, "Lekin har foydali savdoda kichik foyda olib, har zararli "
             "savdoda kattaroq zarar ko'rsangiz, yakuniy natija "
             "<b>manfiy</b> bo'ladi. 60% g'alaba bilan ham pul yo'qotish "
             "mumkin."),
        p(u, "Va aksincha: 35% g'alaba bilan ham foyda ko'rish mumkin — "
             "agar foydalar zararlardan sezilarli katta bo'lsa."),
        h3(u, "Nima uchun bu bob oxirida turibdi"),
        p(u, "Chunki uning ma'nosi oldingi bo'limlarsiz ochilmaydi. "
             "\"Stop qo'ying\" degan gap qo'llab-quvvatlash tushunchasisiz "
             "quruq nasihat. Endi siz Stop ni <b>qayerga</b> qo'yishni "
             "bilasiz."),
        xulosa(u, [
            "Bir xil tahlil — turli natija: farq risk boshqaruvida.",
            "50% yo'qotish 100% foyda talab qiladi; 90% yo'qotish — 900%.",
            "Yuqori g'alaba foizi bilan ham pul yo'qotish mumkin.",
            "Past g'alaba foizi bilan ham foyda ko'rish mumkin.",
            "Avval yo'qotmaslikni o'rganing, keyin yutishni.",
        ]),
        tekshiring(u, [
            "40% yo'qotsangiz, tenglashish uchun necha foiz kerak? "
            "Taxminan hisoblang.",
            "60% g'alaba bilan qanday qilib pul yo'qotish mumkin?",
            "Nega risk menejment kitobning oxirida berilgan?",
        ]),
        PageBreak(),
    ]


def _bob22(u: dict) -> list:
    return [
        *bob_sarlavha(u, "22-BOB", "Asosiy tushunchalar"),
        *savol_bilan_boshla(
            u,
            "Savdoga kirishdan oldin javob berish kerak bo'lgan uchta "
            "savol bor. Ularni bilasizmi?",
        ),
        p(u, "Uchala savol ham <b>kirishdan oldin</b> javob topishi kerak: "
             "qayerda chiqaman agar xato bo'lsa, qayerda chiqaman agar "
             "to'g'ri bo'lsa, va qancha qo'yaman."),
        h2(u, "Stop Loss va Take Profit"),
        p(u, a("Stop Loss") + " (Stop) — oldindan qo'yilgan chiqish "
             "darajasi. Narx u yerga yetsa, savdo <b>avtomatik</b> "
             "yopiladi va zarar chegaralanadi."),
        p(u, a("Take Profit") + " (TP) — foyda olish darajasi. Narx unga "
             "yetsa, savdo foyda bilan yopiladi."),
        chizma_bilan(
            _grafik_stop_tp(),
            "22.1-chizma. Uch daraja: kirish, Stop va TP. Stopgacha "
            "bo'lgan masofa — <b>1R</b>, ya'ni bitta xavf birligi.",
            u,
        ),
        p(u, "Stop <b>tasodifiy joyga</b> qo'yilmaydi. U strukturaga "
             "qo'yiladi: masalan oxirgi swing low ostiga (13-bob) yoki "
             "qo'llab-quvvatlash zonasi ortiga (12-bob)."),
        p(u, "Eng keng tarqalgan xato — Stopni \"qulay\" joyga qo'yish: "
             "\"$50 yo'qotmoqchi emasman, shuning uchun Stopni yaqinroq "
             "qo'yaman\". Bunday Stop tez ishlaydi, chunki u "
             "<b>bozorga emas, hamyonga</b> qarab qo'yilgan."),
        h2(u, "Risk/Reward nisbati"),
        p(u, a("Risk/Reward") + " (R:R) — xavf va kutilayotgan foyda "
             "nisbati. Stopgacha 2%, TP gacha 6% bo'lsa — R:R = 1:3."),
        p(u, "Bu nisbat qanchalik muhim? U <b>qancha g'alaba kerakligini</b> "
             "belgilaydi."),
        chizma_bilan(
            _diagramma_rr(),
            "22.2-chizma. R:R 1:3 bo'lsa, savdolaringizning atigi 25 "
            "foizi foydali bo'lsa ham nolda qolasiz.",
            u,
        ),
        p(u, "Diqqat: bu <b>komissiyasiz</b> hisob. Haqiqiy savdoda har "
             "kirish va chiqishda to'lov bor, shuning uchun amaldagi "
             "chegara biroz yuqoriroq bo'ladi."),
        h2(u, "Position Sizing — pozitsiya hajmi"),
        p(u, "Endi eng amaliy qism: <b>qancha pul qo'yish kerak?</b>"),
        p(u, "Javob taxmin bilan emas, hisob bilan topiladi. Uch qadam:"),
        chizma_bilan(
            _sxema_hajm(),
            "22.3-chizma. Hajm Stop masofasidan kelib chiqadi — "
            "aksincha emas.",
            u,
        ),
        p(u, "Formulaning mantiqi shunda: siz <b>qancha yo'qotishga "
             "tayyorligingizni</b> oldin belgilaysiz, hajm esa shundan "
             "kelib chiqadi."),
        jadval(
            u,
            ["Balans", "Xavf %", "Xavf puli", "Stop masofasi", "Pozitsiya hajmi"],
            [
                ["$1 000", "1%", "$10", "2%", "$500"],
                ["$1 000", "1%", "$10", "4%", "$250"],
                ["$1 000", "1%", "$10", "8%", "$125"],
                ["$1 000", "2%", "$20", "4%", "$500"],
            ],
            [24 * mm, 20 * mm, 24 * mm, 34 * mm, 46 * mm],
        ),
        Spacer(1, 3 * mm),
        p(u, "Jadvalda muhim naqsh bor: <b>Stop uzoqroq bo'lsa, hajm "
             "kichrayadi.</b> Xavf ostidagi pul esa o'zgarmaydi. Aynan "
             "shu narsa hisobni himoya qiladi."),
        h3(u, "Qancha foiz xavf qilish kerak"),
        p(u, "Bu kitob raqam <b>tavsiya qilmaydi</b> — bu sizning "
             "qaroringiz. Faqat matematikani eslatamiz: ketma-ket 10 ta "
             "zarar har qanday strategiyada bo'lishi mumkin."),
        p(u, "Har savdoda 10% xavf qilsangiz, 10 ta ketma-ket zarar "
             "hisobingizni deyarli tugatadi. 1% xavf bilan esa siz "
             "o'yinda qolasiz."),
        real_misol(
            u,
            "Bitta savdoning ekrandagi ko'rinishi: kirish, Stop va TP "
            "buyruqlari qo'yilgan holat, R:R hisobi bilan.",
        ),
        xulosa(u, [
            "Stop, TP va hajm — uchalasi ham <b>kirishdan oldin</b> "
            "belgilanadi.",
            "Stop strukturaga qo'yiladi, hamyonga emas.",
            "R:R qancha g'alaba kerakligini belgilaydi: 1:3 da 25% yetadi.",
            "Hajm = xavf puli ÷ Stop masofasi.",
            "Stop uzoqroq — hajm kichikroq; xavf ostidagi pul o'zgarmaydi.",
            "Ketma-ket 10 ta zarar har qanday strategiyada bo'lishi mumkin.",
        ]),
        tekshiring(u, [
            "Balans $2 000, xavf 1%, Stop 5% uzoqda. Pozitsiya hajmi qancha?",
            "R:R = 1:2 bo'lsa, nolda qolish uchun necha foiz g'alaba kerak?",
            "Nega Stopni \"yaqinroq\" qo'yish yomon fikr?",
        ]),
        PageBreak(),
    ]


def _bob23(u: dict) -> list:
    return [
        *bob_sarlavha(u, "23-BOB", "Hissiy intizom"),
        *savol_bilan_boshla(
            u,
            "Qoidalarni bilasiz. Formulani ham bilasiz. Unda nega o'sha "
            "qoidalar aynan kerak bo'lgan paytda buziladi?",
        ),
        p(u, "Chunki bozorda pul bilan birga <b>his-tuyg'u</b> ham "
             "harakat qiladi. Va u qoidadan tezroq ishlaydi."),
        h2(u, "Qo'rquv va ochko'zlik"),
        p(u, a("Ochko'zlik") + " ko'pincha shunday ko'rinadi: narx o'sdi, "
             "siz \"kech qolyapman\" deb o'ylab, rejasiz kirdingiz. "
             "Bu holat " + a("FOMO") + " (Fear Of Missing Out — o'tkazib "
             "yuborish qo'rquvi) deb ataladi."),
        p(u, a("Qo'rquv") + " esa teskari ishlaydi: zarar ko'rsatgan "
             "savdoni yopmaysiz, chunki yopish — xatoni tan olish demak. "
             "\"Biroz kutaman, qaytadi\" degan fikr aynan shu."),
        chizma_bilan(
            _sxema_hissiyot(),
            "23.1-chizma. Halqa har safar bir xil takrorlanadi. Uni "
            "faqat oldindan yozilgan reja uzadi.",
            u,
        ),
        h2(u, "Nima yordam beradi"),
        *royxat(u, [
            "<b>Rejani OLDIN yozing.</b> Kirish, Stop, TP va hajm — "
            "savdoga kirishdan oldin. Kirgandan keyin miya sizni "
            "ishontira boshlaydi.",
            "<b>Stopni buyruq qilib qo'ying.</b> \"Yodimda turadi\" "
            "ishlamaydi. Buyruq qo'yilgan bo'lsa, uni o'zgartirish uchun "
            "alohida harakat kerak — bu esa to'xtab o'ylashga majbur qiladi.",
            "<b>Zararni chegaralang, davrni ham.</b> Ketma-ket bir necha "
            "zarardan keyin to'xtash — zaiflik emas, qoida.",
            "<b>Ekranga doim qaramang.</b> Har daqiqada narx ko'rish "
            "qaror sifatini oshirmaydi, faqat hissiyotni kuchaytiradi.",
        ]),
        h2(u, "Savdo jurnali"),
        p(u, a("Savdo jurnali") + " — har bir savdoni yozib borish odati. "
             "Bu — eng arzon va eng kam ishlatiladigan vosita."),
        p(u, "Nega u ishlaydi: xotira tanlab eslaydi. Yaxshi savdolar "
             "yodda qoladi, yomonlari \"omadsizlik\" deb hisobdan "
             "chiqariladi. Yozuv esa hech narsani unutmaydi."),
        jadval(
            u,
            ["Nima yoziladi", "Nega kerak"],
            [
                ["Sana, coin, timeframe", "Naqshlarni keyin topish uchun"],
                ["Kirish sababi (qoidaga ko'ra)",
                 "\"Shunchaki ko'nglim tortdi\" ham halol javob"],
                ["Kirish, Stop, TP va hajm", "Reja bajarildimi yoki yo'qmi"],
                ["Natija (R bilan)",
                 "Dollar emas, R: turli hajmdagi savdolar solishtiriladi"],
                ["Savdo paytidagi holatingiz",
                 "Charchaganda yoki asabiy paytda qilingan savdolar "
                 "alohida ko'rinadi"],
            ],
            [48 * mm, 100 * mm],
        ),
        Spacer(1, 4 * mm),
        p(u, "Bir oy yozib borsangiz, o'zingiz haqingizda ajablanarli "
             "narsa bilib olasiz. Ko'pchilik uchun bu — eng ko'p zarar "
             "<b>rejadan tashqari</b> qilingan savdolardan kelishi."),
        h3(u, "Yakuniy qoida"),
        p(u, "Savdo — bir savdo emas, <b>ko'p savdoning yig'indisi</b>. "
             "Bitta savdoning natijasi deyarli hech narsa aytmaydi; "
             "yuztasining natijasi esa hamma narsani aytadi."),
        p(u, "Shuning uchun har bir savdoni g'alaba yoki mag'lubiyat deb "
             "emas, <b>qoidaga rioya qilindimi yoki yo'qmi</b> deb "
             "baholang. Qoidaga rioya qilib zarar ko'rish — yaxshi savdo. "
             "Qoidani buzib foyda ko'rish — yomon savdo."),
        real_misol(
            u,
            "Bir oylik savdo jurnalining namunasi: qoidaga rioya qilingan "
            "va qilinmagan savdolar ajratilgan jadval.",
        ),
        xulosa(u, [
            "FOMO — o'tkazib yuborish qo'rquvi; u rejasiz kirishga olib "
            "keladi.",
            "Zararli savdoni yopmaslik — xatoni tan olmaslik istagi.",
            "Reja <b>kirishdan oldin</b> yoziladi; Stop buyruq qilib "
            "qo'yiladi.",
            "Savdo jurnali xotira aldayolmaydigan yagona joy.",
            "Savdoni natija bilan emas, <b>qoidaga rioya</b> bilan "
            "baholang.",
        ]),
        tekshiring(u, [
            "FOMO qanday paydo bo'ladi va u qanday savdoga olib keladi?",
            "Nega natija R bilan yoziladi, dollar bilan emas?",
            "\"Qoidani buzib foyda ko'rdim\" — bu yaxshi savdomi?",
        ]),
        PageBreak(),
    ]


def bolim6(u: dict) -> list:
    return [
        *bolim_ajratkich(u, "6-BO‘LIM", "RISK MENEJMENT"),
        *_bob21(u),
        *_bob22(u),
        *_bob23(u),
    ]
