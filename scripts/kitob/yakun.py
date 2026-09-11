"""YAKUNIY BOB — 24-bob: keyingi qadamlar.

Kitob "hammasini bilib oldingiz" degan taassurot bilan tugamasligi
kerak. Aksincha: bu yerda o'quvchiga nima o'rganilgani va nima
HALI o'rganilmagani ochiq aytiladi.
"""

from __future__ import annotations

from reportlab.platypus import PageBreak, Spacer

from scripts.kitob import sxema
from scripts.kitob.bloklar import (
    a,
    chizma_bilan,
    h2,
    h3,
    jadval,
    p,
    royxat,
    savol_bilan_boshla,
    tekshiring,
    xulosa,
)
from scripts.kitob.qolip import bob_sarlavha

mm = sxema.mm


def _sxema_yol() -> sxema.Drawing:
    """O'rganish yo'li — kitobdan keyin nima."""
    d = sxema.yangi(boyi=46 * mm)
    sxema.matn(d, 80 * mm, 41 * mm, "Kitobdan keyingi yo'l", qalin=True, olcham=9)
    bosqichlar = [
        ("1", "QAYTA O'QISH", "3-6 bo'limlar,\ngrafik ochiq holda"),
        ("2", "KUZATISH", "savdosiz, faqat\nbelgilash"),
        ("3", "DEMO", "haqiqiy qoida,\nsoxta pul"),
        ("4", "KICHIK HAJM", "haqiqiy pul,\nyo'qotsa og'rimaydigan"),
    ]
    for i, (raqam, nom, izoh) in enumerate(bosqichlar):
        x = 8 * mm + i * 37 * mm
        rang = [sxema.KOK, sxema.TURKUAZ, sxema.APELSIN,
                sxema.colors.HexColor("#12a15f")][i]
        sxema.quti(d, x, 16 * mm, 32 * mm, 18 * mm,
                   [f"{raqam}. {nom}", *izoh.split("\n")], ramka=rang,
                   sarlavha_rang=rang)
        if i:
            sxema.oq(d, x - 4.5 * mm, 25 * mm, x - 1 * mm, 25 * mm)
    sxema.matn(
        d, 80 * mm, 9 * mm,
        "Bosqichni o'tkazib yuborish — eng ko'p uchraydigan va eng "
        "qimmat xato.",
        olcham=7.5, rang=sxema.APELSIN, qalin=True,
    )
    sxema.matn(
        d, 80 * mm, 3 * mm,
        "Har bosqichda kamida bir necha hafta turish tavsiya etiladi.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    return d


def yakun(u: dict) -> list:
    return [
        *bob_sarlavha(u, "24-BOB", "Keyingi qadamlar"),
        *savol_bilan_boshla(
            u,
            "Kitob tugadi. Endi nima qilish kerak — darhol savdo "
            "boshlashmi?",
        ),
        p(u, "Yo'q. Va bu javob jiddiy."),
        p(u, "Siz hozir <b>tushunchalarni</b> bilasiz. Lekin tushunish "
             "va qila olish — ikki xil narsa. Suzishni kitobdan o'qigan "
             "odam hali suzolmaydi."),
        h2(u, "Nima o'rgandingiz"),
        p(u, "Qisqacha sanab o'tamiz — bu ro'yxat qayta o'qish uchun "
             "yo'riqnoma ham bo'ladi."),
        jadval(
            u,
            ["Bo'lim", "Asosiy savol", "Nima qoldi"],
            [
                ["1 — Asoslar", "Kripto qanday ishlaydi?",
                 "Blokcheyn, hamyon, birja, gas"],
                ["2 — Fundamental", "Narxni nima harakatlantiradi?",
                 "Talab/taklif, Funding, Netflow, DXY"],
                ["3 — Texnik", "Grafik nima deyapti?",
                 "Sham, S/R, struktura, Fibonacci"],
                ["4 — SMC", "Iz kimniki?",
                 "BOS/CHOCH, Order Block, FVG, likvidlik"],
                ["5 — ICT", "Qachon?", "Kill Zone, AMDX"],
                ["6 — Risk", "Qanday omon qolish?",
                 "Stop, R:R, hajm, intizom"],
            ],
            [30 * mm, 46 * mm, 72 * mm],
        ),
        Spacer(1, 4 * mm),
        h2(u, "Keyingi to'rt bosqich"),
        chizma_bilan(
            _sxema_yol(),
            "24.1-chizma. Har bosqich oldingisini mustahkamlaydi. "
            "Uchinchisiga o'tmasdan to'rtinchisiga sakramang.",
            u,
        ),
        h3(u, "1. Kitobni qayta o'qing — grafik ochiq holda"),
        p(u, "3, 4 va 5-bo'limlarni ikkinchi marta o'qing, lekin bu safar "
             "yoningizda haqiqiy grafik turgan holda. Har bir tushunchani "
             "<b>o'zingiz topishga</b> harakat qiling."),
        h3(u, "2. Savdosiz kuzating"),
        p(u, "Kamida bir necha hafta: har kuni grafikni oching, "
             "strukturani belgilang, zonalarni chizing — lekin "
             "<b>hech narsa sotib olmang</b>."),
        p(u, "Bu bosqich zerikarli, va aynan shuning uchun ko'pchilik "
             "uni o'tkazib yuboradi. U esa eng arzon tajriba."),
        h3(u, "3. Demo hisob"),
        p(u, a("Demo hisob") + " — soxta pul bilan haqiqiy bozorda savdo. "
             "Deyarli har bir birja uni bepul beradi."),
        p(u, "Qoida: demo hisobda <b>haqiqiy qoidalar</b> bilan ishlang. "
             "Agar demoda 1% xavf qilsangiz, jonlida ham shunday "
             "qilasiz. Demoda \"baribir soxta pul\" deb o'ynagan odam "
             "hech narsa o'rganmaydi."),
        h3(u, "4. Kichik hajm"),
        p(u, "Jonli savdoga o'tganda — yo'qotsangiz hayotingizga ta'sir "
             "qilmaydigan miqdordan boshlang. Maqsad foyda emas, "
             "<b>o'zingizni kuzatish</b>: haqiqiy pul bilan qoidaga "
             "rioya qila olasizmi?"),
        h2(u, "Yana nimalarni o'rganish mumkin"),
        *royxat(u, [
            "<b>On-chain tahlil</b> — blokcheyn ma'lumotidan foydalanish "
            "(2-bo'limning davomi).",
            "<b>Bozorlararo bog'liqlik</b> — aksiya bozori, obligatsiya "
            "daromadliligi, tovar narxlari.",
            "<b>Statistika</b> — o'z natijangizni to'g'ri o'lchash: "
            "kutilayotgan qiymat, eng katta pasayish, namuna hajmi.",
            "<b>Psixologiya</b> — 23-bobning chuqurroq versiyasi.",
        ]),
        h2(u, "HCS Academy materiallari"),
        p(u, "Bu kitob akademiyaning asosi, lekin yagona materiali emas."),
        *royxat(u, [
            "<b>Video darsliklar</b> — kitobdagi tushunchalar harakatda "
            "ko'rsatiladi. Grafikni jonli tahlil qilish matn bilan "
            "tushuntirib bo'lmaydigan narsani beradi.",
            "<b>Bilimlar bo'limi</b> — qisqa maqolalar va yangilanishlar.",
            "<b>Trading kalkulyator</b> — 22-bobdagi hisobni qo'lda "
            "qilmaslik uchun: kirish, Stop va nishonlarni yozasiz, "
            "natijani darhol ko'rasiz.",
        ]),
        h3(u, "Oxirgi gap"),
        p(u, "Bu kitob sizga tayyor javob bermadi — ataylab. Tayyor javob "
             "beradigan material ko'p, va ular odatda bir narsani sotadi."),
        p(u, "Siz esa endi <b>savol berishni</b> bilasiz. \"Bu daraja "
             "nega ishlaydi?\", \"Bu ko'rsatkich nimani o'lchaydi?\", "
             "\"Bu savdoda qancha yo'qotaman?\" — mana shu savollar "
             "sizni har qanday tayyor signaldan uzoqroqqa olib boradi."),
        p(u, "Sabr qiling. Bozor hech qayerga ketmaydi."),
        xulosa(u, [
            "Tushunish va qila olish — ikki xil narsa.",
            "To'rt bosqich: qayta o'qish, kuzatish, demo, kichik hajm.",
            "Demoda haqiqiy qoidalar bilan ishlang — aks holda bosqich "
            "foydasiz.",
            "Jonli savdoning birinchi maqsadi foyda emas, <b>o'zingizni "
            "kuzatish</b>.",
            "Tayyor javob emas, <b>to'g'ri savol</b> — bu kitobning "
            "asosiy natijasi.",
        ]),
        tekshiring(u, [
            "Nega kitobdan keyin darhol jonli savdo boshlash tavsiya "
            "etilmaydi?",
            "Demo hisobda qanday qoidalar bilan ishlash kerak va nega?",
            "Jonli savdoning birinchi bosqichida asosiy maqsad nima?",
        ]),
        PageBreak(),
    ]
