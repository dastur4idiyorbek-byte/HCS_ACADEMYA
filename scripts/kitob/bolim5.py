"""5-BO'LIM: ICT KONSEPSIYALARI — 19-20 boblar.

4-bo'lim "kim" degan savolga javob berdi. Bu bo'lim "QACHON"
degan savolni qo'shadi: vaqt va sessiyalar.

Bo'lim ATAYLAB qisqa. ICT keng tizim va uni to'liq yoritish
alohida kitob bo'lardi; bu yerda faqat asosiy g'oya va eng ko'p
ishlatiladigan ikki tushuncha beriladi.
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


def _sxema_sessiyalar() -> sxema.Drawing:
    """Uch sessiya vaqt o'qida."""
    d = sxema.yangi(boyi=56 * mm)
    sxema.matn(d, 80 * mm, 51 * mm, "Sutka — uchta savdo sessiyasi (UTC)",
               qalin=True, olcham=8.5)
    x0, eni, y, boyi = 12 * mm, 136 * mm, 22 * mm, 11 * mm
    d.add(sxema.Rect(x0, y, eni, boyi, fillColor=sxema.colors.white,
                     strokeColor=sxema.CHIZIQ, strokeWidth=0.7))
    sessiyalar = [
        (0, 9, "OSIYO", "00:00–09:00", sxema.colors.HexColor("#e8f0fb"), sxema.KOK),
        (7, 16, "LONDON", "07:00–16:00", sxema.colors.HexColor("#eef9fb"),
         sxema.TURKUAZ),
        (12, 21, "NYU-YORK", "12:00–21:00", sxema.colors.HexColor("#fff4e8"),
         sxema.APELSIN),
    ]
    for i, (bosh, oxir, nom, vaqt, ichi, ramka) in enumerate(sessiyalar):
        bx = x0 + eni * bosh / 24
        bw = eni * (oxir - bosh) / 24
        yy = y + boyi + 3 * mm + i * 6.5 * mm
        d.add(sxema.Rect(bx, yy, bw, 5 * mm, fillColor=ichi,
                         strokeColor=ramka, strokeWidth=0.9))
        sxema.matn(d, bx + bw / 2, yy + 1.6 * mm, f"{nom}  {vaqt}",
                   olcham=6.8, rang=ramka, qalin=True)
    # Soat belgilari
    for soat in range(0, 25, 4):
        x = x0 + eni * soat / 24
        d.add(sxema.Line(x, y, x, y - 1.5 * mm, strokeColor=sxema.MATN_PAST,
                         strokeWidth=0.6))
        sxema.matn(d, x, y - 5.5 * mm, f"{soat:02d}", olcham=6.5,
                   rang=sxema.MATN_PAST)
    # Kesishuv
    kx0 = x0 + eni * 12 / 24
    kx1 = x0 + eni * 16 / 24
    d.add(sxema.Rect(kx0, y, kx1 - kx0, boyi,
                     fillColor=sxema.colors.Color(0.96, 0.5, 0.09, alpha=0.18),
                     strokeColor=sxema.APELSIN, strokeWidth=0.9))
    sxema.matn(d, (kx0 + kx1) / 2, y + boyi / 2 - 1.5 * mm, "KESISHUV",
               olcham=7, rang=sxema.APELSIN, qalin=True)
    sxema.matn(
        d, 80 * mm, 8 * mm,
        "London va Nyu-York kesishgan payt — odatda sutkadagi eng "
        "faol oraliq.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    sxema.matn(
        d, 80 * mm, 3 * mm,
        "Kripto 24/7 ishlaydi, lekin ODAMLAR 24/7 ishlamaydi.",
        olcham=7.5, rang=sxema.MATN, qalin=True,
    )
    return d


def _grafik_killzone() -> sxema.Drawing:
    """Sessiya boshida hajm va harakat."""
    ketma = ch.shamlar([
        (100, 100.4, 99.8, 100.2), (100.2, 100.5, 100, 100.3),  # tinch (Osiyo)
        (100.3, 100.6, 100.1, 100.4),
        (100.4, 103.6, 100.2, 103.2),   # London ochilishi
        (103.2, 104.2, 102.4, 102.8), (102.8, 103.2, 102.2, 103),
        (103, 106.8, 102.8, 106.4),     # NY ochilishi
        (106.4, 107, 105.4, 105.8), (105.8, 106.2, 105.2, 105.6),
    ])
    d, k = ch.sham_chizma(ketma, boyi=56 * mm)
    ch.zona(d, k, 3, 3, 99.6, 107.6, "", rang=ch.TURKUAZ, shaffoflik=0.12)
    ch.zona(d, k, 6, 6, 99.6, 107.6, "", rang=ch.APELSIN, shaffoflik=0.12)
    ch.izoh_matni(d, k.x(1), k.y(101.4), "Osiyo — tor oraliq", markaz=True)
    ch.izoh_matni(d, k.x(3), k.y(108.4), "London", markaz=True, rang=ch.TURKUAZ)
    ch.izoh_matni(d, k.x(6), k.y(108.4), "Nyu-York", markaz=True, rang=ch.APELSIN)
    ch.izoh_matni(d, k.x(4.5), k.y(98.6),
                  "Harakatning katta qismi sessiya OCHILISHIDA tug'iladi",
                  markaz=True)
    return d


def _sxema_amdx() -> sxema.Drawing:
    """Quarterly Theory — to'rt bosqich."""
    d = sxema.yangi(boyi=46 * mm)
    sxema.matn(d, 80 * mm, 41 * mm,
               "Quarterly Theory (AMDX) — takrorlanadigan to'rt bosqich",
               qalin=True, olcham=8.5)
    bosqichlar = [
        ("A", "Accumulation", "to'planish — tor oraliq", sxema.KOK),
        ("M", "Manipulation", "yolg'on harakat", sxema.APELSIN),
        ("D", "Distribution", "asosiy harakat", sxema.colors.HexColor("#12a15f")),
        ("X", "Continuation", "davom yoki tugash", sxema.MATN_PAST),
    ]
    for i, (harf, nom, izoh, rang) in enumerate(bosqichlar):
        x = 8 * mm + i * 37 * mm
        sxema.quti(d, x, 16 * mm, 32 * mm, 17 * mm, [harf, nom, izoh],
                   ramka=rang, sarlavha_rang=rang)
        if i:
            sxema.oq(d, x - 4.5 * mm, 24 * mm, x - 1 * mm, 24 * mm)
    sxema.matn(
        d, 80 * mm, 9 * mm,
        "Bu bosqichlar sutka ichida ham, hafta ichida ham kuzatilishi mumkin.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    sxema.matn(
        d, 80 * mm, 3 * mm,
        "MUHIM: bu — kuzatuv naqshi, jadval emas. Har sutka shunday "
        "bo'lmaydi.",
        olcham=7.5, rang=sxema.APELSIN, qalin=True,
    )
    return d


# --------------------------------------------------------------------------- #
#  Boblar
# --------------------------------------------------------------------------- #


def _bob19(u: dict) -> list:
    return [
        *bob_sarlavha(u, "19-BOB", "ICT — umumiy kirish"),
        *savol_bilan_boshla(
            u,
            "Kripto bozori 24 soat ishlaydi. Unda nega ba'zi soatlarda "
            "harakat kuchli, boshqalarida grafik deyarli qimirlamaydi?",
        ),
        p(u, "Javob oddiy: <b>bozor 24/7, lekin odamlar emas.</b> Yirik "
             "kapital ish vaqtida harakat qiladi, va ish vaqti — geografiya "
             "masalasi."),
        h2(u, "ICT nima"),
        p(u, a("ICT") + " (Inner Circle Trader) — Maykl Hadldston tarqatgan "
             "yondashuvlar to'plami. Uning asosiy qo'shgan hissasi — "
             "<b>vaqt</b>."),
        p(u, "SMC \"narx qayerda\" deb so'raydi. ICT unga \"va QACHON\" "
             "degan savolni qo'shadi."),
        chizma_bilan(
            _sxema_sessiyalar(),
            "19.1-chizma. Uch asosiy sessiya va ularning kesishuvi. "
            "Vaqtlar UTC da — o'z mintaqangizga o'girishni unutmang.",
            u,
        ),
        h2(u, "SMC bilan bog'liqligi"),
        p(u, "ICT va SMC ko'p atamani baham ko'radi: Order Block, FVG, "
             "likvidlik. Amalda SMC — ICT g'oyalarining soddalashtirilgan "
             "va ommalashgan ko'rinishi."),
        p(u, "Farq urg'uda: ICT vaqtga ancha ko'proq e'tibor beradi va "
             "\"qaysi soatda, qaysi sessiyada\" degan savolni tahlilning "
             "ajralmas qismi deb hisoblaydi."),
        h3(u, "Ogohlantirish — 17-bobdagi bilan bir xil"),
        p(u, "ICT atrofida juda ko'p murakkab atama va juda ko'p "
             "va'da bor. Murakkablik <b>aniqlik degani emas</b>."),
        p(u, "Bu kitob ICT ni ikki tushuncha bilan cheklaydi: ular eng "
             "ko'p ishlatiladigan va eng oson tekshiriladiganlari."),
        real_misol(
            u,
            "Bir haftalik 1 soatlik grafik: sessiya chegaralari vertikal "
            "chiziq bilan belgilangan — Osiyo oralig'ining torligi va "
            "London ochilishidagi harakat ko'rinsin.",
        ),
        xulosa(u, [
            "Kripto 24/7 ishlaydi, lekin kapital odamlar ish vaqtida "
            "harakat qiladi.",
            "ICT ning asosiy qo'shimchasi — <b>vaqt</b> o'lchovi.",
            "SMC bilan ko'p atamani baham ko'radi; farq urg'uda.",
            "Murakkab atama aniqlik kafolati emas.",
        ]),
        tekshiring(u, [
            "Nega 24/7 bozorda ham \"faol soatlar\" bo'ladi?",
            "ICT SMC ga qanday savol qo'shadi?",
            "Vaqtlar UTC da berilsa, siz nima qilishingiz kerak?",
        ]),
        PageBreak(),
    ]


def _bob20(u: dict) -> list:
    return [
        *bob_sarlavha(u, "20-BOB", "ICT asosiy tushunchalari"),
        *savol_bilan_boshla(
            u,
            "Agar vaqt muhim bo'lsa — sutkaning qaysi qismiga qarash "
            "kerak? Va u yerda aynan nimani kutish mumkin?",
        ),
        h2(u, "Kill Zone"),
        p(u, a("Kill Zone") + " — sessiya ochilishidagi bir necha soatlik "
             "oraliq, unda harakat odatda eng kuchli bo'ladi."),
        jadval(
            u,
            ["Kill Zone", "Vaqt (UTC)", "Xarakteri"],
            [
                ["Osiyo", "23:00–04:00",
                 "Odatda tor oraliq. Ko'pincha kun davomida sinaladigan "
                 "yuqori va quyi nuqtalarni qo'yadi."],
                ["London", "06:00–09:00",
                 "Kuchli harakat boshlanadi. Osiyo oralig'ining chekkalari "
                 "ko'pincha shu yerda sinaladi."],
                ["Nyu-York", "12:00–15:00",
                 "Eng katta hajm. London yo'nalishini davom ettirishi yoki "
                 "keskin teskari burishi mumkin."],
            ],
            [24 * mm, 26 * mm, 98 * mm],
        ),
        Spacer(1, 4 * mm),
        chizma_bilan(
            _grafik_killzone(),
            "20.1-chizma. Osiyo — tinch, tor oraliq. London va Nyu-York "
            "ochilishi — harakatning katta qismi shu yerda tug'iladi.",
            u,
        ),
        p(u, "Amaliy foydasi shunda: agar siz kunduzi ishlasangiz va "
             "grafikni faqat kechqurun ochsangiz — qaysi sessiyani "
             "ko'rayotganingizni bilish kerak. Tinch Osiyo oralig'ida "
             "\"harakat yo'q\" deb xafa bo'lishning ma'nosi yo'q."),
        h2(u, "Quarterly Theory (AMDX)"),
        p(u, a("Quarterly Theory") + " — vaqtni to'rt bosqichga bo'lish "
             "g'oyasi. Bosh harflari bilan " + a("AMDX") + " deb ataladi."),
        chizma_bilan(
            _sxema_amdx(),
            "20.2-chizma. To'rt bosqich: to'planish, manipulyatsiya, "
            "taqsimlash va davom.",
            u,
        ),
        *royxat(u, [
            a("Accumulation") + " — tor oraliq, pozitsiya to'planadi.",
            a("Manipulation") + " — qisqa yolg'on harakat (18-bobdagi "
            "sweep ni eslang).",
            a("Distribution") + " — asosiy harakat, aksariyat yo'l shu yerda "
            "bosib o'tiladi.",
            a("Continuation") + " — harakat davom etadi yoki tugaydi.",
        ]),
        p(u, "Bu naqsh sutka ichida ham, hafta ichida ham kuzatilishi "
             "mumkin. Lekin takrorlaymiz: <b>u jadval emas</b>. Har "
             "sutka shu tartibda o'tmaydi."),
        h2(u, "Yana bir necha atama"),
        jadval(
            u,
            ["Atama", "Qisqacha ma'nosi"],
            [
                ["Judas Swing", "Sessiya boshidagi yolg'on harakat — "
                                "asosiy yo'nalishga TESKARI."],
                ["Silver Bullet", "Kun ichidagi tor vaqt oynasi (odatda "
                                  "1 soat), unda ko'p imkoniyat kuzatilgan."],
                ["Power of 3", "AMDX ning uch bosqichli qisqa ko'rinishi: "
                               "to'planish, manipulyatsiya, taqsimlash."],
                ["Draw on Liquidity", "Narx qaysi likvidlikka \"tortilayotgani\" "
                                      "— keyingi maqsad qayerda."],
            ],
            [32 * mm, 116 * mm],
        ),
        Spacer(1, 4 * mm),
        h3(u, "Bu bo'limni qanday ishlatish kerak"),
        p(u, "Vaqtni tahlilga qo'shish foydali. Lekin <b>faqat vaqtga "
             "tayanib</b> savdo qilish — xuddi faqat indikatorga tayanish "
             "kabi xato."),
        p(u, "To'g'ri tartib: avval struktura (13-bob), keyin zona "
             "(18-bob), so'ngra vaqt (shu bob). Vaqt — <b>oxirgi</b> "
             "filtr, birinchisi emas."),
        real_misol(
            u,
            "Bir sutkalik 15 daqiqalik grafik: Osiyo oralig'i, London "
            "ochilishidagi harakat va Nyu-York kesishuvi belgilangan.",
        ),
        xulosa(u, [
            "Kill Zone — sessiya ochilishidagi eng faol oraliq.",
            "Osiyo tor oraliq qo'yadi, London uni sinaydi, Nyu-York eng "
            "katta hajm keltiradi.",
            "AMDX — to'planish, manipulyatsiya, taqsimlash, davom.",
            "Bu naqshlar <b>kuzatuv</b>, jadval emas.",
            "Vaqt — oxirgi filtr: avval struktura, keyin zona, so'ng vaqt.",
        ]),
        tekshiring(u, [
            "Uchta Kill Zone ni va ularning xarakterini ayting.",
            "AMDX ning \"M\" bosqichi 18-bobdagi qaysi tushunchaga yaqin?",
            "Nega vaqt birinchi emas, oxirgi filtr bo'lishi kerak?",
        ]),
        PageBreak(),
    ]


def bolim5(u: dict) -> list:
    return [
        *bolim_ajratkich(u, "5-BO‘LIM", "ICT KONSEPSIYALARI"),
        *_bob19(u),
        *_bob20(u),
    ]
