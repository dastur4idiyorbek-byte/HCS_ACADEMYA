"""1-BO'LIM: ASOSLAR — 1-7 boblar.

O'QUVCHI HECH NARSA BILMAYDI deb yoziladi. "Blokcheyn" so'zini
birinchi marta eshitgan odam ham to'xtamasdan o'qiy olishi kerak.

TADRIJ QOIDASI: har bob avvalgisiga tayanadi. 3-bobda
"markazlashmagan" so'zi ishlatilsa, u 2-bobda tayyorlangan
bo'lishi kerak — ya'ni "markaz" kim ekani allaqachon aytilgan.
"""

from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Spacer

from scripts.kitob import sxema
from scripts.kitob.bloklar import (
    a,
    chizma_bilan,
    h2,
    jadval,
    p,
    royxat,
    savol_bilan_boshla,
    tekshiring,
    xulosa,
)
from scripts.kitob.qolip import bob_sarlavha, bolim_ajratkich

MATN_ENI = 168 * mm


# --------------------------------------------------------------------------- #
#  Chizmalar
# --------------------------------------------------------------------------- #


def _sxema_almashinuv() -> sxema.Drawing:
    """Bevosita almashinuv va pul orqali almashinuv."""
    d = sxema.yangi(boyi=52 * mm)
    sxema.matn(d, 80 * mm, 47 * mm, "1) PULSIZ — bevosita almashinuv", qalin=True, olcham=8.5)
    sxema.quti(d, 12 * mm, 30 * mm, 40 * mm, 12 * mm, ["CHORVADOR", "2 qo'y bor"])
    sxema.quti(d, 108 * mm, 30 * mm, 40 * mm, 12 * mm, ["DEHQON", "bug'doy bor"])
    sxema.oq(d, 53 * mm, 39 * mm, 107 * mm, 39 * mm, yorliq="qo'y")
    sxema.oq(d, 107 * mm, 33 * mm, 53 * mm, 33 * mm, yorliq="bug'doy")
    sxema.matn(
        d, 80 * mm, 25 * mm,
        "Shart: dehqonga AYNAN qo'y kerak bo'lishi kerak. Aks holda almashinuv bo'lmaydi.",
        olcham=7, rang=sxema.MATN_PAST,
    )

    sxema.matn(d, 80 * mm, 17 * mm, "2) PUL BILAN", qalin=True, olcham=8.5)
    sxema.quti(d, 12 * mm, 3 * mm, 34 * mm, 10 * mm, ["CHORVADOR"])
    sxema.quti(d, 63 * mm, 3 * mm, 34 * mm, 10 * mm, ["PUL"], ramka=sxema.SARIQ,
               ichi=sxema.colors.HexColor("#fdf5e3"), sarlavha_rang=sxema.APELSIN)
    sxema.quti(d, 114 * mm, 3 * mm, 34 * mm, 10 * mm, ["DEHQON"])
    sxema.oq(d, 47 * mm, 8 * mm, 62 * mm, 8 * mm)
    sxema.oq(d, 98 * mm, 8 * mm, 113 * mm, 8 * mm)
    return d


def _sxema_daftar() -> sxema.Drawing:
    """Bitta daftar va hammadagi nusxa."""
    d = sxema.yangi(boyi=54 * mm)
    sxema.matn(d, 40 * mm, 49 * mm, "BANK: bitta daftar", qalin=True, olcham=8.5)
    sxema.quti(d, 20 * mm, 26 * mm, 40 * mm, 18 * mm,
               ["BANK DAFTARI", "Ali -> Vali: 100", "Vali -> Sur: 40"],
               ramka=sxema.KOK)
    for i, nom in enumerate(("Ali", "Vali", "Sur")):
        x = 8 * mm + i * 22 * mm
        sxema.quti(d, x, 8 * mm, 18 * mm, 8 * mm, [nom], ichi=sxema.colors.white)
        sxema.oq(d, x + 9 * mm, 17 * mm, x + 9 * mm, 25 * mm, uzuq=True,
                 rang=sxema.MATN_PAST)
    sxema.matn(d, 40 * mm, 3 * mm, "Daftar BITTA joyda. Unga bank egalik qiladi.",
               olcham=7, rang=sxema.MATN_PAST)

    sxema.matn(d, 122 * mm, 49 * mm, "BLOKCHEYN: daftar hammada", qalin=True, olcham=8.5)
    for i in range(3):
        x = 88 * mm + i * 24 * mm
        sxema.quti(d, x, 26 * mm, 22 * mm, 18 * mm,
                   ["NUSXA", "Ali->Vali:100", "Vali->Sur:40"],
                   ramka=sxema.TURKUAZ, ichi=sxema.colors.HexColor("#eef9fb"))
        sxema.quti(d, x + 2 * mm, 8 * mm, 18 * mm, 8 * mm,
                   [("Ali", "Vali", "Sur")[i]], ichi=sxema.colors.white)
        sxema.oq(d, x + 11 * mm, 17 * mm, x + 11 * mm, 25 * mm, uzuq=True,
                 rang=sxema.MATN_PAST)
    sxema.matn(d, 122 * mm, 3 * mm,
               "Har kimda BIR XIL nusxa. Bittasini o'zgartirish yetarli emas.",
               olcham=7, rang=sxema.MATN_PAST)
    return d


def _sxema_tarmoq() -> sxema.Drawing:
    """Kimning ruxsati kerak: bitta markaz yoki tarmoq."""
    d = sxema.yangi(boyi=50 * mm)
    sxema.matn(d, 40 * mm, 45 * mm, "MARKAZLASHGAN", qalin=True, olcham=8.5)
    sxema.quti(d, 24 * mm, 24 * mm, 32 * mm, 12 * mm, ["MARKAZ", "u qaror qiladi"],
               ramka=sxema.APELSIN, ichi=sxema.colors.HexColor("#fff4e8"),
               sarlavha_rang=sxema.APELSIN)
    for i in range(4):
        x = 6 * mm + i * 17 * mm
        sxema.quti(d, x, 8 * mm, 13 * mm, 7 * mm, [f"{i + 1}"], ichi=sxema.colors.white)
        sxema.oq(d, x + 6.5 * mm, 15.5 * mm, 36 * mm, 23 * mm,
                 rang=sxema.MATN_PAST, uzuq=True)
    sxema.matn(d, 40 * mm, 3 * mm,
               "Markaz to'xtatsa — hech narsa bo'lmaydi.",
               olcham=7, rang=sxema.MATN_PAST)

    sxema.matn(d, 120 * mm, 45 * mm, "MARKAZLASHMAGAN", qalin=True, olcham=8.5)
    # Tugunlar halqa bo'lib joylashadi va HAR BIRI boshqasiga ulanadi.
    import math

    markaz_x, markaz_y, radius = 120 * mm, 22 * mm, 14 * mm
    nuqtalar = [
        (markaz_x + radius * math.cos(2 * math.pi * i / 6),
         markaz_y + radius * math.sin(2 * math.pi * i / 6))
        for i in range(6)
    ]
    for i, (x0, y0) in enumerate(nuqtalar):
        for x1, y1 in nuqtalar[i + 1:]:
            d.add(sxema.Line(x0, y0, x1, y1,
                             strokeColor=sxema.colors.HexColor("#cfe6ea"),
                             strokeWidth=0.6))
    for x, y in nuqtalar:
        sxema.quti(d, x - 5 * mm, y - 3 * mm, 10 * mm, 6 * mm, [""],
                   ramka=sxema.TURKUAZ, ichi=sxema.colors.HexColor("#eef9fb"))
    sxema.matn(d, 120 * mm, 3 * mm,
               "Bittasi to'xtasa — qolganlari davom etadi.",
               olcham=7, rang=sxema.MATN_PAST)
    return d


def _sxema_zanjir() -> sxema.Drawing:
    """Bloklar zanjiri va xesh bog'lanishi."""
    d = sxema.yangi(boyi=44 * mm)
    sxema.matn(d, 80 * mm, 39 * mm,
               "Har blok OLDINGISINING barmoq izini ichida saqlaydi",
               qalin=True, olcham=8.5)
    nomlar = [
        ["1-BLOK", "oldingi: —", "yozuvlar: 3 ta"],
        ["2-BLOK", "oldingi: a91f…", "yozuvlar: 5 ta"],
        ["3-BLOK", "oldingi: 7c02…", "yozuvlar: 4 ta"],
    ]
    sxema.zanjir_boglami(d, 14 * mm, 14 * mm, 38 * mm, 20 * mm, 3, nomlar)
    sxema.matn(
        d, 80 * mm, 7 * mm,
        "2-blokdagi bitta raqam o'zgarsa, uning barmoq izi ham o'zgaradi — "
        "va 3-blokdagi yozuv mos kelmay qoladi.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    sxema.matn(d, 80 * mm, 2 * mm, "Ya'ni eski yozuvni jimgina tuzatib bo'lmaydi.",
               olcham=7, rang=sxema.APELSIN)
    return d


def _sxema_birja() -> sxema.Drawing:
    """CEX va DEX: pul kimda turadi."""
    d = sxema.yangi(boyi=52 * mm)
    sxema.matn(d, 40 * mm, 47 * mm, "CEX — markazlashgan birja", qalin=True, olcham=8.5)
    sxema.quti(d, 6 * mm, 32 * mm, 26 * mm, 10 * mm, ["SIZ"], ichi=sxema.colors.white)
    sxema.quti(d, 44 * mm, 28 * mm, 30 * mm, 18 * mm,
               ["BIRJA", "pulingiz", "SHU YERDA"], ramka=sxema.APELSIN,
               ichi=sxema.colors.HexColor("#fff4e8"), sarlavha_rang=sxema.APELSIN)
    sxema.oq(d, 33 * mm, 37 * mm, 43 * mm, 37 * mm, yorliq="pul")
    sxema.quti(d, 6 * mm, 10 * mm, 26 * mm, 10 * mm, ["BOSHQA ODAM"], ichi=sxema.colors.white)
    sxema.oq(d, 33 * mm, 15 * mm, 50 * mm, 27 * mm)
    sxema.matn(d, 40 * mm, 3 * mm, "Birja ishonchli bo'lishi SHART.",
               olcham=7, rang=sxema.MATN_PAST)

    sxema.matn(d, 120 * mm, 47 * mm, "DEX — markazlashmagan birja", qalin=True, olcham=8.5)
    sxema.quti(d, 86 * mm, 32 * mm, 26 * mm, 10 * mm, ["SIZ"], ichi=sxema.colors.white)
    sxema.quti(d, 124 * mm, 28 * mm, 30 * mm, 18 * mm,
               ["DASTUR", "(smart-kontrakt)", "pul SIZDA qoladi"],
               ramka=sxema.TURKUAZ, ichi=sxema.colors.HexColor("#eef9fb"))
    sxema.oq(d, 113 * mm, 37 * mm, 123 * mm, 37 * mm, yorliq="buyruq")
    sxema.quti(d, 86 * mm, 10 * mm, 26 * mm, 10 * mm, ["BOSHQA ODAM"], ichi=sxema.colors.white)
    sxema.oq(d, 113 * mm, 15 * mm, 130 * mm, 27 * mm)
    sxema.matn(d, 120 * mm, 3 * mm, "Ishonch DASTURGA, odamga emas.",
               olcham=7, rang=sxema.MATN_PAST)
    return d


def _sxema_kalit() -> sxema.Drawing:
    """Ochiq va yopiq kalit."""
    d = sxema.yangi(boyi=46 * mm)
    sxema.quti(d, 10 * mm, 26 * mm, 62 * mm, 15 * mm,
               ["OCHIQ KALIT (manzil)", "hammaga aytsa bo'ladi",
                "bu — pochta qutingizning raqami"],
               ramka=sxema.TURKUAZ, ichi=sxema.colors.HexColor("#eef9fb"))
    sxema.quti(d, 88 * mm, 26 * mm, 62 * mm, 15 * mm,
               ["YOPIQ KALIT (maxfiy)", "HECH KIMGA aytilmaydi",
                "bu — qutining kaliti"],
               ramka=sxema.colors.HexColor("#d8453a"),
               ichi=sxema.colors.HexColor("#fdeeed"),
               sarlavha_rang=sxema.colors.HexColor("#a32f27"))
    sxema.oq(d, 41 * mm, 24 * mm, 41 * mm, 14 * mm, yorliq="pul kiradi")
    sxema.oq(d, 119 * mm, 24 * mm, 119 * mm, 14 * mm, yorliq="pul chiqadi",
             rang=sxema.colors.HexColor("#d8453a"))
    sxema.quti(d, 50 * mm, 3 * mm, 60 * mm, 10 * mm, ["HAMYON"], ramka=sxema.KOK)
    sxema.matn(d, 80 * mm, 43 * mm,
               "Yopiq kalitni bergan odam — pulini bergan bo'ladi.",
               qalin=True, olcham=8, rang=sxema.APELSIN)
    return d


def _sxema_kopruk() -> sxema.Drawing:
    """Ko'prik: bir zanjirdan ikkinchisiga."""
    d = sxema.yangi(boyi=40 * mm)
    sxema.quti(d, 10 * mm, 18 * mm, 42 * mm, 16 * mm,
               ["ETHEREUM", "USDT: 100", "gas: ETH bilan"], ramka=sxema.KOK)
    sxema.quti(d, 108 * mm, 18 * mm, 42 * mm, 16 * mm,
               ["BNB CHAIN", "USDT: 100", "gas: BNB bilan"], ramka=sxema.KOK)
    sxema.quti(d, 62 * mm, 20 * mm, 36 * mm, 12 * mm, ["KO'PRIK"],
               ramka=sxema.APELSIN, ichi=sxema.colors.HexColor("#fff4e8"),
               sarlavha_rang=sxema.APELSIN)
    sxema.oq(d, 53 * mm, 26 * mm, 61 * mm, 26 * mm)
    sxema.oq(d, 99 * mm, 26 * mm, 107 * mm, 26 * mm)
    sxema.matn(
        d, 80 * mm, 10 * mm,
        "Bir xil nomli token har zanjirda ALOHIDA yashaydi. "
        "Ko'prik ularni bog'laydi.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    sxema.matn(
        d, 80 * mm, 4 * mm,
        "Noto'g'ri zanjirga yuborilgan pul — ko'pincha qaytmaydi.",
        olcham=7.5, rang=sxema.APELSIN, qalin=True,
    )
    return d


# --------------------------------------------------------------------------- #
#  Boblar
# --------------------------------------------------------------------------- #


def _bob1(u: dict) -> list:
    return [
        *bob_sarlavha(u, "1-BOB", "Pul o'zi nima?"),
        *savol_bilan_boshla(
            u,
            "Har kuni pul ishlatasiz. Lekin pul — bu nima? "
            "Nega bir parcha qog'oz yoki telefondagi raqam evaziga "
            "sizga non berishadi?",
        ),
        p(u, "Javob oddiy: <b>chunki hamma unga ishonadi.</b> Pulning qiymati "
             "qog'ozning o'zida emas — odamlarning kelishuvida."),
        h2(u, "Puldan oldin nima bo'lgan"),
        p(u, "Pul ixtiro qilinmasdan oldin odamlar narsalarni bevosita almashgan. "
             "Buni " + a("barter") + " deyiladi. Bir chorvador qo'yini dehqonning "
             "bug'doyiga almashadi."),
        p(u, "Muammo shunda: bu ish faqat <b>ikkala tomonga ham</b> kerakli narsa "
             "bo'lgandagina yuradi. Chorvadorga bug'doy kerak, lekin dehqonga qo'y "
             "kerak emas — poyabzal kerak, deylik. Unda almashinuv bo'lmaydi."),
        chizma_bilan(
            _sxema_almashinuv(),
            "1.1-chizma. Barter ikkala tomonning ehtiyoji to'g'ri kelgandagina "
            "ishlaydi. Pul bu shartni olib tashlaydi.",
            u,
        ),
        p(u, "Pul aynan shu muammoni yechdi. U — <b>oraliq narsa</b>: hamma uni "
             "qabul qiladi, shuning uchun hech kim bir-birining ehtiyojini "
             "kutib o'tirmaydi."),
        h2(u, "Pulning uch vazifasi"),
        p(u, "Iqtisodda pulga uchta vazifa bo'yicha baho beriladi. Bu uchta o'lchov "
             "keyinchalik bizga kriptovalyutani baholashda ham kerak bo'ladi."),
        *royxat(u, [
            a("Almashinuv vositasi") + " — uni hamma qabul qiladi. Non ham, "
            "kvartira ham shu bilan sotib olinadi.",
            a("Qiymat saqlash") + " — bugun ishlagan pulingiz bir yildan keyin ham "
            "taxminan shuncha narsaga arziydi. Agar pul tez qadrsizlansa, bu vazifa "
            "buziladi.",
            a("Hisob birligi") + " — narxlarni bir xil o'lchovda solishtirish imkonini "
            "beradi. \"Bu mashina 40 ta qo'yga arziydi\" emas, \"5 000 dollar\" deymiz.",
        ]),
        p(u, "Diqqat qiling: uchala vazifa ham <b>ishonchga</b> tayanadi. Ertaga "
             "hech kim bu qog'ozni olmayman desa, u shu zahoti oddiy qog'ozga "
             "aylanadi. Shuning uchun pul tarixi — aslida ishonch tarixi."),
        h2(u, "Oltindan qog'ozgacha"),
        p(u, "Uzoq vaqt pul sifatida oltin ishlatilgan. Sababi ravshan: uni "
             "ko'paytirib bo'lmaydi, u chirimaydi va bo'laklarga bo'linadi. Keyin "
             "og'ir oltinni tashish noqulay bo'lgani uchun banklar tilxat bera "
             "boshladi: \"bu qog'oz egasida bizda shuncha oltin bor\"."),
        p(u, "Vaqt o'tib qog'oz oltindan uzildi. Bugungi dollar yoki so'm hech qanday "
             "oltinga bog'lanmagan — ularning qiymati faqat davlat kafolati va "
             "odamlarning ishonchiga tayanadi. Bunday pul " + a("fiat") + " deb "
             "ataladi (lotincha \"shunday bo'lsin\")."),
        xulosa(u, [
            "Pul — qiymatning o'zi emas, u haqidagi <b>kelishuv</b>.",
            "Barter faqat ikkala tomonning ehtiyoji mos kelganda ishlaydi; "
            "pul bu cheklovni olib tashlaydi.",
            "Pulning uch vazifasi: almashinuv vositasi, qiymat saqlash, hisob birligi.",
            "Bugungi pul (fiat) oltinga bog'lanmagan — u ishonch va davlat "
            "kafolatiga tayanadi.",
        ]),
        tekshiring(u, [
            "Barter nima uchun katta iqtisod uchun yaramaydi?",
            "Pulning qaysi vazifasi juda tez inflyatsiya paytida birinchi bo'lib buziladi?",
            "\"Fiat pul\" nimaga tayanadi?",
        ]),
        PageBreak(),
    ]


def _bob2(u: dict) -> list:
    return [
        *bob_sarlavha(u, "2-BOB", "Valyuta va raqamli valyuta"),
        *savol_bilan_boshla(
            u,
            "Kartangizdagi pulni oxirgi marta qachon qo'lingizda ushlagansiz? "
            "Agar u qog'oz emas, ekrandagi raqam bo'lsa — u qayerda turibdi?",
        ),
        p(u, "Bu savolning javobi ko'pchilikni ajablantiradi: <b>bugungi pulning "
             "katta qismi allaqachon raqamli.</b> Kriptovalyuta \"pulni raqamli "
             "qilgan\" narsa emas — u boshqacha narsani o'zgartirgan. Nimani "
             "o'zgartirganini tushunish uchun avval oddiy bank qanday ishlashini "
             "ko'ramiz."),
        h2(u, "Bankdagi pul — bu yozuv"),
        p(u, "Bankka 1 000 000 so'm qo'ysangiz, bank uni seyfga alohida solib "
             "qo'ymaydi. U shunchaki o'z " + a("daftariga") + " (bazasiga) yozadi: "
             "\"bu odamning hisobida 1 000 000 bor\"."),
        p(u, "Boshqa odamga pul o'tkazsangiz, hech qanday qog'oz qimirlamaydi. "
             "Bank bitta raqamni kamaytiradi, ikkinchisini ko'paytiradi. Hammasi shu."),
        p(u, "Demak bankdagi pul — <b>jismoniy narsa emas, yozuv</b>. Va bu yozuvni "
             "kim yuritadi? Bank. Ya'ni bitta tashkilot."),
        chizma_bilan(
            _sxema_daftar(),
            "2.1-chizma. Chapda: daftar bitta joyda turadi va unga bank egalik qiladi. "
            "O'ngda: daftarning nusxasi hammada bor — bu 4-bobda ko'radigan blokcheyn.",
            u,
        ),
        h2(u, "Bitta daftarning kuchli va zaif tomoni"),
        p(u, "Bitta tashkilot daftar yuritishi qulay: xato bo'lsa tuzatadi, karta "
             "yo'qolsa bloklaydi, firibgarlikni tekshiradi. Buning uchun unga "
             "ishonasiz."),
        p(u, "Lekin xuddi shu narsa zaiflik ham: hamma yozuv bitta joyda. U tashkilot "
             "hisobingizni to'xtatishi, daftarni o'zgartirishi yoki bankrot bo'lishi "
             "mumkin. Siz bunga ta'sir qila olmaysiz."),
        p(u, "Bu — yaxshi yoki yomon degan gap emas. Bu shunchaki <b>tuzilma</b>: "
             "ishonch bitta markazga qo'yilgan. Keyingi bobda aynan shu nuqta "
             "o'zgaradi."),
        h2(u, "Valyuta va valyuta kursi"),
        p(u, a("Valyuta") + " — muayyan davlat ishlatadigan pul: so'm, dollar, yevro. "
             "Bir valyutani ikkinchisiga almashtirish narxi " + a("valyuta kursi") +
             " deyiladi. Kurs doim o'zgarib turadi, chunki valyutaga bo'lgan talab "
             "va taklif o'zgaradi."),
        p(u, "Kripto dunyosida ham xuddi shunday: bitta coinning narxi boshqasiga "
             "nisbatan o'lchanadi. Odatda o'lchov birligi sifatida dollarga "
             "bog'langan token ishlatiladi — bu haqda 5-bobda gaplashamiz."),
        xulosa(u, [
            "Bankdagi pul jismoniy narsa emas — bu <b>daftardagi yozuv</b>.",
            "O'tkazma — qog'oz harakati emas, ikkita raqamning o'zgarishi.",
            "Daftarni bitta tashkilot yuritadi: bu qulay, lekin ishonch bitta "
            "markazga bog'lanadi.",
            "Kriptovalyutaning yangiligi \"raqamli bo'lishi\" emas — daftarni "
            "KIM yuritishi.",
        ]),
        tekshiring(u, [
            "Kartangizdagi pul jismonan qayerda turibdi?",
            "Bitta tashkilot daftar yuritishining bitta afzalligi va bitta "
            "kamchiligini ayting.",
            "\"Raqamli pul\" va \"kriptovalyuta\" bir xil narsami?",
        ]),
        PageBreak(),
    ]


def _bob3(u: dict) -> list:
    return [
        *bob_sarlavha(u, "3-BOB", "Kriptovalyuta — bu nima, va nima EMAS"),
        *savol_bilan_boshla(
            u,
            "Agar bankdagi pul ham raqamli bo'lsa, kriptovalyutaning farqi nimada? "
            "Nega u haqida shuncha gapiriladi?",
        ),
        p(u, "2-bobda ko'rdik: bank daftarini bitta tashkilot yuritadi. "
             "Kriptovalyutaning butun g'oyasi bitta jumlaga sig'adi: "
             "<b>daftarni hech kim yolg'iz yuritmaydi.</b>"),
        h2(u, "Markazlashmaganlik"),
        p(u, "Daftarning nusxasi minglab kompyuterda turadi. Yangi yozuv qo'shilishi "
             "uchun ular o'zaro kelishadi. Bitta kompyuterni o'chirsangiz ham, "
             "egasini qamasangiz ham, daftar yashashda davom etadi."),
        p(u, "Buni " + a("markazlashmaganlik") + " (ingliz tilida "
             "<i>decentralization</i>) deyiladi. Eng muhim oqibati: tizimni "
             "boshqaradigan bitta odam yoki tashkilot yo'q."),
        p(u, "Bu narsaning narxi ham bor va u kam aytiladi: <b>xatoni tuzatadigan "
             "ham yo'q.</b> Pulni noto'g'ri manzilga yuborsangiz, murojaat "
             "qiladigan qo'llab-quvvatlash xizmati bo'lmaydi."),
        chizma_bilan(
            _sxema_tarmoq(),
            "3.1-chizma. Chapda bitta markaz qaror qiladi. O'ngda qaror "
            "tarmoqda tarqalgan — bitta tugunni to'xtatish hech narsani "
            "o'zgartirmaydi.",
            u,
        ),
        h2(u, "Kriptovalyuta NIMA EMAS"),
        p(u, "Bu ro'yxat ataylab kiritilgan — noto'g'ri tasavvurlar ko'pincha "
             "to'g'risidan oldin o'rnashib qoladi."),
        *royxat(u, [
            "<b>Bu \"tez boyish\" usuli emas.</b> Narx tushishi ham, ko'tarilishi "
            "ham mumkin, va u ko'pincha kutilganidan keskinroq harakat qiladi.",
            "<b>Bu anonimlik emas.</b> Aksincha: Bitcoin yozuvlari butunlay ochiq, "
            "har bir o'tkazmani istagan odam ko'rishi mumkin.",
            "<b>Bu bitta narsa emas.</b> Minglab turli loyiha bor va ularning "
            "sifati yer bilan osmoncha farq qiladi.",
            "<b>Bu davlat pulining o'rnini bosgani yo'q.</b> Bugun u asosan "
            "investitsiya va o'tkazma vositasi sifatida ishlatiladi.",
        ]),
        h2(u, "Bitcoin qayerdan paydo bo'lgan"),
        p(u, "2008-yilda dunyoda katta moliyaviy inqiroz bo'ldi: yirik banklar "
             "qulab tushdi, ularni davlat pulga ko'mib qutqardi. Ko'p odam "
             "\"nega bizning pulimiz begona qarorga bog'liq?\" degan savolni berdi."),
        p(u, "O'sha yili " + a("Satoshi Nakamoto") + " degan taxallus bilan qisqa "
             "hujjat e'lon qilindi. Unda bankdan mustaqil ishlaydigan elektron pul "
             "tizimi tasvirlangan edi. 2009-yil yanvarda birinchi " + a("Bitcoin") +
             " bloki yaratildi."),
        p(u, "Satoshi kimligi bugungacha noma'lum va u 2011-yildan beri jim. "
             "Qiziq tomoni shundaki, bu tizimning ishlashiga xalaqit bermaydi — "
             "chunki u hech kimga bog'liq emas."),
        xulosa(u, [
            "Kriptovalyutaning yangiligi — raqamliligi emas, "
            "<b>markazlashmaganligi</b>.",
            "Daftar nusxasi minglab kompyuterda turadi; ularsiz yangi yozuv qo'shilmaydi.",
            "Markazi yo'qligi — erkinlik ham, javobgarlik ham: xatoni tuzatib "
            "beradigan odam yo'q.",
            "Bitcoin 2008-yilgi inqirozdan keyin, banklarga bog'liqlikka javob "
            "sifatida paydo bo'ldi.",
        ]),
        tekshiring(u, [
            "\"Markazlashmagan\" so'zi amalda nimani anglatadi?",
            "Kriptovalyuta anonimmi? Javobingizni asoslang.",
            "Markazi yo'qligining bitta jiddiy kamchiligini ayting.",
        ]),
        PageBreak(),
    ]


def _bob4(u: dict) -> list:
    return [
        *bob_sarlavha(u, "4-BOB", "Blokcheyn — asosiy tushuncha"),
        *savol_bilan_boshla(
            u,
            "Agar daftarni hamma yuritsa, nega birov unga yolg'on yozib "
            "qo'ymaydi? \"Menda million bor\" deb yozsa bo'lmaydimi?",
        ),
        p(u, "Bu — eng to'g'ri savol va butun texnologiya aynan shunga javob "
             "berish uchun o'ylab topilgan. Javob ikki qismdan iborat: "
             "yozuvlar <b>bloklarga</b> yig'iladi va bloklar bir-biriga "
             "<b>zanjir</b> bo'lib bog'lanadi."),
        h2(u, "Blok nima"),
        p(u, a("Blok") + " — bu bir necha daqiqa ichida yig'ilgan o'tkazmalar "
             "to'plami. Daftarning bitta sahifasi deb tasavvur qiling: unga "
             "o'nlab yozuv sig'adi, sahifa to'lgach yangisi ochiladi."),
        h2(u, "Zanjir nima"),
        p(u, "Har bir yangi blok ichiga oldingi blokning <b>barmoq izi</b> "
             "yoziladi. Texnik tilda bu " + a("xesh") + " deyiladi: har qanday "
             "ma'lumotdan hisoblanadigan qisqa, takrorlanmaydigan belgi."),
        p(u, "Xeshning muhim xossasi: ma'lumotda bitta harf o'zgarsa ham, xesh "
             "butunlay boshqacha bo'lib qoladi."),
        chizma_bilan(
            _sxema_zanjir(),
            "4.1-chizma. Har blok oldingisining barmoq izini saqlaydi. Eski "
            "yozuvni o'zgartirish — undan keyingi barcha bloklarni ham qayta "
            "qurish demak.",
            u,
        ),
        p(u, "Endi yolg'on yozishga urinib ko'ring. Ikkinchi blokdagi raqamni "
             "o'zgartirsangiz, uning xeshi o'zgaradi. Uchinchi blokda esa eski "
             "xesh yozilgan — mos kelmaydi. Demak to'rtinchi, beshinchi... "
             "barcha bloklarni qayta qurishingiz kerak."),
        p(u, "Va buni <b>minglab kompyuterdan tezroq</b> qilishingiz kerak, chunki "
             "ular shu orada yangi bloklar qo'shishda davom etadi. Amalda bu deyarli "
             "imkonsiz."),
        h2(u, "Demak ishonch qayerdan keladi"),
        p(u, "Bank holatida ishonch <b>tashkilotga</b> qo'yiladi: \"ular halol "
             "yuritadi\". Blokcheynda ishonch <b>tuzilmaga</b> qo'yiladi: "
             "\"yolg'on yozish shunchaki qimmatga tushadi\"."),
        p(u, "Bu farqni tushunish muhim. Blokcheyn odamlarni halol qilmaydi — "
             "u nohalollikni foydasiz qilib qo'yadi."),
        xulosa(u, [
            "Blok — bir necha daqiqadagi o'tkazmalar to'plami, daftarning "
            "bitta sahifasi.",
            "Har blok oldingisining <b>xeshini</b> (barmoq izini) saqlaydi.",
            "Bitta eski yozuvni o'zgartirish undan keyingi barcha bloklarni "
            "qayta qurishni talab qiladi.",
            "Ishonch tashkilotga emas, tuzilmaga qo'yiladi: yolg'on yozish "
            "imkonsiz emas, shunchaki foydasiz.",
        ]),
        tekshiring(u, [
            "Xesh nima va uning qaysi xossasi zanjirni himoya qiladi?",
            "Nega eski blokni o'zgartirish qiyin?",
            "\"Blokcheyn odamlarni halol qiladi\" — bu gap to'g'rimi?",
        ]),
        PageBreak(),
    ]


def _bob5(u: dict) -> list:
    return [
        *bob_sarlavha(u, "5-BOB", "Birjalar — CEX va DEX"),
        *savol_bilan_boshla(
            u,
            "Kriptoni qayerdan olasiz? Va uni sotib olganingizda pulingiz "
            "aslida kimda turadi?",
        ),
        p(u, "Ikkinchi savol birinchisidan muhimroq, lekin uni kamdan-kam "
             "beradi. Javob birja turiga qarab butunlay boshqacha bo'ladi."),
        h2(u, "CEX — markazlashgan birja"),
        p(u, a("CEX") + " (<i>Centralized Exchange</i>) — Binance, Bybit, OKX "
             "kabi kompaniyalar. Ular 2-bobdagi bank bilan bir xil tuzilmada "
             "ishlaydi: sizning mablag'ingiz <b>ularning</b> hisobida turadi, "
             "ekranda esa siz o'z raqamingizni ko'rasiz."),
        p(u, "Bu qulay: ro'yxatdan o'tish oson, xarid tez, parolni unutsangiz "
             "tiklanadi. Lekin bitta shart bor — birja ishonchli bo'lishi kerak. "
             "Tarixda bir necha yirik birja mijoz pulini yo'qotgan."),
        h2(u, "DEX — markazlashmagan birja"),
        p(u, a("DEX") + " (<i>Decentralized Exchange</i>) — kompaniya emas, "
             "blokcheynda ishlaydigan dastur. Uni " + a("smart-kontrakt") +
             " deyiladi: oldindan yozilgan, o'zgartirib bo'lmaydigan shartlar "
             "to'plami."),
        p(u, "Bu yerda mablag' hech kimga o'tmaydi: u sizning hamyoningizda "
             "qoladi (hamyon — keyingi bob), almashinuv esa to'g'ridan-to'g'ri "
             "dastur orqali bo'ladi."),
        chizma_bilan(
            _sxema_birja(),
            "5.1-chizma. Asosiy farq bitta savolda: savdo paytida pul KIMDA "
            "turadi.",
            u,
        ),
        h2(u, "Solishtiruv"),
        jadval(
            u,
            ["", "CEX (markazlashgan)", "DEX (markazlashmagan)"],
            [
                ["Pul kimda", "Birjada", "Sizning hamyoningizda"],
                ["Ro'yxatdan o'tish", "Hujjat bilan (KYC)", "Kerak emas"],
                ["Parolni tiklash", "Bor", "YO'Q — kalit yo'qolsa tamom"],
                ["Tezlik va narx", "Tez, komissiya past", "Sekinroq, gas to'lanadi"],
                ["Asosiy xavf", "Birja qulashi yoki bloklashi",
                 "O'z xatoyingiz, dasturdagi kamchilik"],
            ],
            [24 * mm, 62 * mm, 62 * mm],
        ),
        Spacer(1, 4 * mm),
        p(u, "Yangi boshlovchilar odatda CEX dan boshlaydi — u soddaroq. Lekin "
             "\"pul birjada turibdi\" degan faktni yodda tutish kerak."),
        xulosa(u, [
            "CEX — kompaniya; mablag' uning hisobida turadi, u ishonchli bo'lishi shart.",
            "DEX — blokcheyndagi dastur; mablag' hamyoningizda qoladi.",
            "CEX qulayroq va tezroq, DEX mustaqilroq.",
            "Asosiy savol har doim bitta: <b>hozir pul kimda?</b>",
        ]),
        tekshiring(u, [
            "CEX da savdo qilayotganingizda pulingiz kimning ixtiyorida?",
            "DEX da parolni unutsangiz nima bo'ladi?",
            "Nega KYC faqat CEX da so'raladi?",
        ]),
        PageBreak(),
    ]


def _bob6(u: dict) -> list:
    return [
        *bob_sarlavha(u, "6-BOB", "Hamyonlar (Wallets)"),
        *savol_bilan_boshla(
            u,
            "\"Kripto hamyoni\" deganda nimani tasavvur qilasiz? Ichida coin "
            "turadigan qutinimi?",
        ),
        p(u, "Bu — eng keng tarqalgan xato. Hamyon ichida <b>hech qanday coin "
             "yo'q.</b> Coinlar blokcheyn daftarida turadi. Hamyon esa faqat "
             "<b>kalitlarni</b> saqlaydi."),
        h2(u, "Ikkita kalit"),
        p(u, "Har bir hamyonda juft kalit bo'ladi va ular butunlay boshqa "
             "vazifani bajaradi."),
        *royxat(u, [
            a("Ochiq kalit") + " (public key) — undan " + a("manzil") + " "
            "hosil qilinadi. Bu — sizga pul yuborish uchun kerak bo'lgan raqam. "
            "Uni istagan odamga berish mumkin.",
            a("Yopiq kalit") + " (private key) — mablag'ni harakatlantirish "
            "huquqi. Uni hech kimga, hech qanday sababga ko'ra bermaysiz.",
        ]),
        chizma_bilan(
            _sxema_kalit(),
            "6.1-chizma. Ochiq kalit — pochta qutingizning raqami: hammaga "
            "aytsa bo'ladi. Yopiq kalit — o'sha qutining kaliti.",
            u,
        ),
        p(u, "Amalda yopiq kalit ko'pincha 12 yoki 24 ta so'z ko'rinishida "
             "beriladi — bu " + a("seed-fraza") + ". Uni yozib, xavfsiz joyda "
             "saqlash kerak. Suratga olib telefonda saqlash — eng ko'p "
             "uchraydigan xato."),
        h2(u, "Issiq va sovuq hamyon"),
        p(u, a("Issiq hamyon") + " — internetga ulangan: telefon ilovasi, "
             "brauzer kengaytmasi. Qulay, tez, kundalik ishlatishga mos. "
             "Lekin kompyuteringiz zararlansa, kalit ham xavf ostida."),
        p(u, a("Sovuq hamyon") + " — internetdan uzilgan: maxsus qurilma yoki "
             "oddiygina qog'ozga yozilgan seed-fraza. Noqulayroq, lekin uzoq "
             "muddatli saqlash uchun ancha xavfsiz."),
        p(u, "Oddiy qoida: kundalik miqdor issiqda, jiddiy miqdor sovuqda."),
        jadval(
            u,
            ["", "Issiq hamyon", "Sovuq hamyon"],
            [
                ["Internet", "Ulangan", "Uzilgan"],
                ["Qulaylik", "Yuqori", "Past"],
                ["Xavfsizlik", "O'rtacha", "Yuqori"],
                ["Nimaga mos", "Kundalik, kichik miqdor", "Uzoq saqlash, katta miqdor"],
            ],
            [26 * mm, 61 * mm, 61 * mm],
        ),
        Spacer(1, 4 * mm),
        xulosa(u, [
            "Hamyon coin saqlamaydi — u <b>kalit</b> saqlaydi.",
            "Ochiq kalit (manzil) hammaga aytiladi; yopiq kalit hech kimga aytilmaydi.",
            "Seed-fraza — yopiq kalitning so'z ko'rinishi. Uni raqamli holda "
            "saqlash xavfli.",
            "Issiq hamyon qulay, sovuq hamyon xavfsiz; miqdorga qarab tanlanadi.",
        ]),
        tekshiring(u, [
            "Hamyoningiz ichida aslida nima turadi?",
            "Manzilingizni notanish odamga berish xavflimi?",
            "Nega seed-frazani suratga olish tavsiya etilmaydi?",
        ]),
        PageBreak(),
    ]


def _bob7(u: dict) -> list:
    return [
        *bob_sarlavha(u, "7-BOB", "Ko'priklar va boshqa asosiy atamalar"),
        *savol_bilan_boshla(
            u,
            "Blokcheyn bitta emas. Ularning har biri o'z daftariga ega. "
            "Unda bir daftardagi pulni ikkinchisiga qanday o'tkazasiz?",
        ),
        p(u, "Shu paytgacha \"blokcheyn\" deganda bitta narsani nazarda tutdik. "
             "Aslida ular ko'p: Bitcoin, Ethereum, BNB Chain, Solana va "
             "boshqalar. Har biri — alohida daftar, alohida qoidalar."),
        h2(u, "Tranzaksiya va gas"),
        p(u, a("Tranzaksiya") + " — daftarga yozilgan bitta o'tkazma. U yozilishi "
             "uchun tarmoqdagi kompyuterlar ish bajaradi, va bu ish tekin emas."),
        p(u, "To'lovni " + a("gas") + " (yoki komissiya) deyiladi. Uning miqdori "
             "qat'iy emas: tarmoq band bo'lsa oshadi, bo'sh bo'lsa tushadi — "
             "xuddi tirbandlikdagi taksi narxi kabi."),
        p(u, "Muhim tafsilot: gas <b>o'sha zanjirning o'z valyutasida</b> "
             "to'lanadi. Ethereumda — ETH bilan, BNB Chainda — BNB bilan. "
             "Hamyoningizda USDT bor-u, ETH yo'q bo'lsa, o'tkazma amalga oshmaydi."),
        h2(u, "Ko'prik nima uchun kerak"),
        p(u, "Har bir zanjir o'z daftarini yuritadi va boshqasini ko'rmaydi. "
             "Ethereumdagi USDT va BNB Chaindagi USDT — nomi bir xil, lekin "
             "ikki xil daftardagi ikki xil yozuv."),
        p(u, a("Ko'prik") + " (bridge) — shu ikkisini bog'laydigan xizmat. U "
             "bir tomonda mablag'ni bloklaydi, ikkinchi tomonda shunga teng "
             "miqdorni chiqaradi."),
        chizma_bilan(
            _sxema_kopruk(),
            "7.1-chizma. Ko'prik ikki alohida daftarni bog'laydi. Noto'g'ri "
            "zanjirga yuborilgan mablag' odatda qaytmaydi.",
            u,
        ),
        h2(u, "Yana bir necha atama"),
        jadval(
            u,
            ["Atama", "Ma'nosi"],
            [
                ["Token", "Mavjud blokcheyn ustida chiqarilgan aktiv. O'z "
                          "zanjiri yo'q — mehmon."],
                ["Coin", "O'z blokcheyniga ega aktiv (BTC, ETH). Gas shu bilan "
                         "to'lanadi."],
                ["Stablecoin", "Narxi dollarga bog'langan token (USDT, USDC). "
                               "Narx o'lchovi sifatida ishlatiladi."],
                ["Spot savdo", "Aktivni haqiqatan sotib olish. Bu kitob faqat "
                               "shu haqda."],
                ["Bozor kapitalizatsiyasi", "Narx × muomaladagi soni. \"Bu loyiha "
                                            "qanchalik katta\" degan savolga javob."],
                ["Likvidlik", "Aktivni narxni qimirlatmasdan sotish qanchalik oson."],
            ],
            [38 * mm, 110 * mm],
        ),
        Spacer(1, 4 * mm),
        p(u, "Ushbu ro'yxatdagi oxirgi ikkitasi — likvidlik va kapitalizatsiya — "
             "kitobning 2-bo'limida yana uchraydi va u yerda chuqurroq ochiladi."),
        xulosa(u, [
            "Blokcheyn bitta emas: har biri alohida daftar va alohida qoidalar.",
            "Gas — o'tkazma uchun to'lov; u <b>o'sha zanjirning o'z valyutasida</b> "
            "to'lanadi.",
            "Ko'prik ikki zanjirni bog'laydi: bir tomonda bloklaydi, "
            "ikkinchisida chiqaradi.",
            "Coin o'z zanjiriga ega, token esa begona zanjirda yashaydi.",
        ]),
        tekshiring(u, [
            "Hamyoningizda USDT bor, ETH yo'q. Ethereumda o'tkazma qila olasizmi?",
            "Coin va token orasidagi farq nimada?",
            "Ko'prik nima uchun kerak bo'ladi?",
        ]),
        PageBreak(),
    ]


def bolim1(u: dict) -> list:
    """1-bo'lim: ajratkich + 7 bob."""
    return [
        *bolim_ajratkich(u, "1-BO‘LIM", "ASOSLAR"),
        *_bob1(u),
        *_bob2(u),
        *_bob3(u),
        *_bob4(u),
        *_bob5(u),
        *_bob6(u),
        *_bob7(u),
    ]
