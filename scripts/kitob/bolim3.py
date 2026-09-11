"""3-BO'LIM: KLASSIK TEXNIK TAHLIL — 11-16 boblar.

Bu yerdan boshlab GRAFIK asosiy tilga aylanadi. Shuning uchun har
bir tushuncha `chizma.py` dagi sham grafigi bilan ko'rsatiladi —
7-promptning 2.1-bandi buni MAJBURIY deb belgilagan.

CHIZMALARDAGI SHAMLAR QO'LDA YOZILGAN. Tasodifiy son chiroyli
ko'rinishi mumkin, lekin u tushunchani buzishi ham mumkin: "bu
yerda swing bo'lishi kerak" degan joyda swing chiqmay qolsa,
chizma o'quvchini adashtiradi.
"""

from __future__ import annotations

from reportlab.lib.units import mm
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

# --------------------------------------------------------------------------- #
#  11-bob: sham anatomiyasi
# --------------------------------------------------------------------------- #


def _sxema_sham_anatomiyasi() -> sxema.Drawing:
    """Bitta shamning to'rt narxi — yorliqlar bilan."""
    d = sxema.yangi(boyi=62 * mm)
    sxema.matn(d, 80 * mm, 57 * mm, "Bitta sham — to'rtta narx", qalin=True, olcham=9)

    def bitta(x: float, osdi: bool, sarlavha: str) -> None:
        rang = ch.SHAM_OSDI if osdi else ch.SHAM_TUSHDI
        tepa, past = 46 * mm, 10 * mm
        tana_t, tana_p = (38 * mm, 20 * mm) if osdi else (38 * mm, 20 * mm)
        d.add(sxema.Line(x, past, x, tepa, strokeColor=rang, strokeWidth=1.2))
        d.add(sxema.Rect(x - 5 * mm, tana_p, 10 * mm, tana_t - tana_p,
                         fillColor=rang, strokeColor=rang))
        # Yorliqlar
        ochilish_y, yopilish_y = (tana_p, tana_t) if osdi else (tana_t, tana_p)
        sxema.matn(d, x, tepa + 3, "HIGH — eng yuqori", olcham=7,
                   rang=sxema.MATN_PAST)
        sxema.matn(d, x, past - 6, "LOW — eng past", olcham=7, rang=sxema.MATN_PAST)
        sxema.matn(d, x - 30 * mm, ochilish_y - 1, "OPEN — ochilish", olcham=7,
                   rang=sxema.MATN, markaz=False)
        sxema.oq(d, x - 11 * mm, ochilish_y + 1, x - 6 * mm, ochilish_y + 1,
                 rang=sxema.MATN_PAST)
        # 12 mm — strelka DUMIdan (x + 11 mm) keyin boshlanadi. Ilgari
        # 7 mm edi va strelka chizig'i "CLOSE" harflari ustidan o'tib,
        # so'zni chizib tashlagandek ko'rinardi.
        sxema.matn(d, x + 12 * mm, yopilish_y - 1, "CLOSE — yopilish", olcham=7,
                   rang=sxema.MATN, markaz=False)
        sxema.oq(d, x + 11 * mm, yopilish_y + 1, x + 6 * mm, yopilish_y + 1,
                 rang=sxema.MATN_PAST)
        sxema.matn(d, x, 2 * mm, sarlavha, olcham=8, qalin=True, rang=rang)

    bitta(45 * mm, True, "O'SUVCHI: Close > Open")
    bitta(120 * mm, False, "TUSHUVCHI: Close < Open")
    return d


def _grafik_soya() -> sxema.Drawing:
    """Uzun soya nima aytadi."""
    ketma = ch.shamlar([
        (100, 101, 99.4, 100.6), (100.6, 101.4, 100.1, 101.1),
        (101.1, 101.6, 97.6, 101.3),   # uzun pastki soya
        (101.3, 102.2, 101, 102),
        (102, 105.4, 101.8, 102.3),    # uzun tepa soya
        (102.3, 102.6, 101.4, 101.6), (101.6, 102, 101.1, 101.9),
        (101.9, 102.4, 101.5, 102.2),
    ])
    d, k = ch.sham_chizma(ketma, boyi=52 * mm)
    ch.izoh_matni(d, k.x(2), k.y(97.0), "uzun PASTKI soya:", markaz=True)
    ch.izoh_matni(d, k.x(2), k.y(96.3), "past narx RAD ETILDI", markaz=True,
                  rang=ch.SHAM_OSDI)
    ch.izoh_matni(d, k.x(4), k.y(105.9), "uzun TEPA soya:", markaz=True)
    ch.izoh_matni(d, k.x(4), k.y(105.2), "yuqori narx RAD ETILDI", markaz=True,
                  rang=ch.SHAM_TUSHDI)
    return d


# --------------------------------------------------------------------------- #
#  12-bob: Support / Resistance
# --------------------------------------------------------------------------- #


def _grafik_sr() -> sxema.Drawing:
    ketma = ch.shamlar([
        (100, 103, 99.6, 102.5), (102.5, 108.6, 102, 107.8),
        (107.8, 109.8, 106.5, 107),    # qarshilikka tegdi
        (107, 107.5, 103, 103.4),
        (103.4, 104, 100.2, 100.6),    # qo'llab-quvvatlashga tegdi
        (100.6, 104, 100.1, 103.8),
        (103.8, 109.9, 103.4, 106.5),  # yana qarshilik
        (106.5, 107, 102.5, 103),
        (103, 103.6, 100.3, 102.8),    # yana qo'llab-quvvatlash
        (102.8, 106, 102.4, 105.6),
        (105.6, 110.2, 105.2, 110),    # UZIB O'TDI
        (110, 113, 109.6, 112.6),
    ])
    d, k = ch.sham_chizma(ketma, boyi=60 * mm)
    ch.gorizontal(d, k, 109.8, "QARSHILIK (Resistance)", rang=ch.SHAM_TUSHDI)
    ch.gorizontal(d, k, 100.2, "QO'LLAB-QUVVATLASH (Support)", rang=ch.SHAM_OSDI)
    ch.strelka(d, k.x(10), k.y(114), k.x(10), k.y(111))
    ch.izoh_matni(d, k.x(10), k.y(115), "uzib o'tdi", markaz=True, rang=ch.APELSIN)
    return d


def _grafik_sr_almashuv() -> sxema.Drawing:
    """Uzilgan qarshilik — qo'llab-quvvatlashga aylanadi."""
    ketma = ch.shamlar([
        (100, 101.5, 99.6, 101), (101, 104.9, 100.8, 104.6),
        (104.6, 105, 103.6, 104),
        (104, 108.2, 103.8, 107.9),    # uzib o'tdi
        (107.9, 109, 107.4, 108.6),
        (108.6, 108.8, 105.1, 105.6),  # qaytib sinadi
        (105.6, 106.2, 104.9, 106),
        (106, 109, 105.7, 108.8), (108.8, 112, 108.4, 111.6),
    ])
    d, k = ch.sham_chizma(ketma, boyi=54 * mm)
    ch.gorizontal(d, k, 105.0, "bu daraja", rang=ch.KOK)
    ch.izoh_matni(d, k.x(1), k.y(103.4), "avval QARSHILIK", rang=ch.SHAM_TUSHDI)
    ch.izoh_matni(d, k.x(5.6), k.y(103.4), "endi QO'LLAB-QUVVATLASH",
                  rang=ch.SHAM_OSDI)
    ch.strelka(d, k.x(5), k.y(102.6), k.x(5), k.y(104.6))
    return d


# --------------------------------------------------------------------------- #
#  13-bob: bozor strukturasi
# --------------------------------------------------------------------------- #


def _grafik_swing() -> sxema.Drawing:
    """5 shamli fraktal — swing high va swing low."""
    ketma = ch.shamlar([
        (100, 101.2, 99.6, 101), (101, 103, 100.8, 102.8),
        (102.8, 106.4, 102.6, 106),   # SWING HIGH (o'rtada)
        (106, 106.2, 103.6, 104), (104, 104.4, 102.2, 102.6),
        (102.6, 103, 99.2, 99.6),     # SWING LOW (o'rtada)
        (99.6, 102, 99.4, 101.8), (101.8, 104, 101.4, 103.8),
    ])
    d, k = ch.sham_chizma(ketma, boyi=62 * mm, tepa_joy=12)
    ch.nuqta(d, k, 2, 106.4, "SWING HIGH", rang=ch.SHAM_TUSHDI)
    ch.nuqta(d, k, 5, 99.2, "SWING LOW", rang=ch.SHAM_OSDI, tepada=False)
    ch.izoh_tepada(d, k.x(2), "chapda 2 ta pastroq, o'ngda 2 ta pastroq")
    return d


def _grafik_trend() -> sxema.Drawing:
    """Uptrend (HH/HL) va downtrend (LH/LL)."""
    d = sxema.yangi(boyi=64 * mm)
    yuqori = ch.shamlar([
        (100, 103, 99.6, 102.6), (102.6, 103.2, 100.8, 101.2),
        (101.2, 106.4, 101, 106), (106, 106.4, 103.4, 103.8),
        (103.8, 109.6, 103.6, 109.2), (109.2, 109.6, 106.4, 106.8),
        (106.8, 112.6, 106.6, 112.2),
    ])
    kichik, k1 = ch.sham_chizma(yuqori, eni=74 * mm, boyi=56 * mm)
    ch.nuqta(kichik, k1, 2, 106.4, "HH", rang=ch.SHAM_OSDI)
    ch.nuqta(kichik, k1, 4, 109.6, "HH", rang=ch.SHAM_OSDI)
    ch.nuqta(kichik, k1, 3, 103.4, "HL", rang=ch.SHAM_OSDI, tepada=False)
    ch.nuqta(kichik, k1, 5, 106.4, "HL", rang=ch.SHAM_OSDI, tepada=False)
    ch.izoh_matni(kichik, k1.x(3), k1.y(113.6), "O'SISH TRENDI", markaz=True,
                  rang=ch.SHAM_OSDI)
    # Ikki kichik grafik bitta chizmaga joylashtiriladi. `Drawing` ning
    # o'zi `Group` — shuning uchun uni ota chizmaga qo'shib, surish mumkin.
    kichik.translate(4 * mm, 4 * mm)
    d.add(kichik)

    past = ch.shamlar([
        (112, 112.4, 108.6, 109), (109, 111.6, 108.8, 111.2),
        (111.2, 111.4, 105.6, 106), (106, 108.6, 105.8, 108.2),
        (108.2, 108.4, 102.6, 103), (103, 105.4, 102.8, 105),
        (105, 105.2, 99.8, 100.2),
    ])
    ikki, k2 = ch.sham_chizma(past, eni=74 * mm, boyi=56 * mm)
    ch.nuqta(ikki, k2, 1, 111.6, "LH", rang=ch.SHAM_TUSHDI)
    ch.nuqta(ikki, k2, 3, 108.6, "LH", rang=ch.SHAM_TUSHDI)
    ch.nuqta(ikki, k2, 2, 105.6, "LL", rang=ch.SHAM_TUSHDI, tepada=False)
    ch.nuqta(ikki, k2, 4, 102.6, "LL", rang=ch.SHAM_TUSHDI, tepada=False)
    ch.izoh_matni(ikki, k2.x(3), k2.y(113.6), "TUSHISH TRENDI", markaz=True,
                  rang=ch.SHAM_TUSHDI)
    ikki.translate(82 * mm, 4 * mm)
    d.add(ikki)
    return d


# --------------------------------------------------------------------------- #
#  14-bob: patternlar
# --------------------------------------------------------------------------- #


def _grafik_bosh_yelka() -> sxema.Drawing:
    ketma = ch.shamlar([
        (100, 102.6, 99.8, 102.4), (102.4, 105.6, 102.2, 105.2),  # chap yelka
        (105.2, 105.6, 102, 102.4), (102.4, 103, 100.6, 101),
        (101, 104, 100.8, 103.8), (103.8, 110.2, 103.6, 109.8),   # bosh
        (109.8, 110, 105.4, 105.8), (105.8, 106, 100.8, 101.2),
        (101.2, 103.4, 101, 103.2), (103.2, 105.8, 103, 105.4),   # o'ng yelka
        (105.4, 105.6, 101.4, 101.8), (101.8, 102, 97.6, 98),     # bo'yin uzildi
    ])
    d, k = ch.sham_chizma(ketma, boyi=58 * mm)
    ch.gorizontal(d, k, 100.7, "BO'YIN CHIZIG'I", rang=ch.KOK, yorliq_chapda=True)
    ch.izoh_matni(d, k.x(1), k.y(106.6), "chap yelka", markaz=True)
    ch.izoh_matni(d, k.x(5), k.y(111), "BOSH", markaz=True, rang=ch.APELSIN)
    ch.izoh_matni(d, k.x(9), k.y(106.6), "o'ng yelka", markaz=True)
    ch.strelka(d, k.x(11), k.y(100), k.x(11), k.y(97.6))
    return d


def _grafik_uchburchak() -> sxema.Drawing:
    ketma = ch.shamlar([
        (100, 108.4, 99.8, 107.8), (107.8, 108, 100.4, 101),
        (101, 107, 100.8, 106.6), (106.6, 106.8, 101.8, 102.2),
        (102.2, 105.6, 102, 105.2), (105.2, 105.4, 102.8, 103.2),
        (103.2, 104.6, 103, 104.2), (104.2, 104.4, 103.4, 103.6),
        (103.6, 109.2, 103.4, 108.8),
    ])
    d, k = ch.sham_chizma(ketma, boyi=54 * mm)
    ch.chiziq(d, [(k.x(0), k.y(108.4)), (k.x(7), k.y(104.4))], rang=ch.SHAM_TUSHDI)
    ch.chiziq(d, [(k.x(1), k.y(100.4)), (k.x(7), k.y(103.4))], rang=ch.SHAM_OSDI)
    ch.izoh_matni(d, k.x(3), k.y(110), "narx siqilmoqda — kuch to'planmoqda",
                  markaz=True)
    ch.strelka(d, k.x(8), k.y(106.5), k.x(8), k.y(109.2), rang=ch.APELSIN)
    ch.izoh_matni(d, k.x(8), k.y(110.4), "chiqish", markaz=True, rang=ch.APELSIN)
    return d


# --------------------------------------------------------------------------- #
#  15-bob: Fibonacci
# --------------------------------------------------------------------------- #


def _grafik_fib() -> sxema.Drawing:
    ketma = ch.shamlar([
        (100, 101, 99.6, 100.8), (100.8, 106, 100.6, 105.6),
        (105.6, 110.4, 105.4, 110),     # tepa
        (110, 110.2, 107, 107.4), (107.4, 107.8, 104.6, 105),
        (105, 105.4, 103.4, 103.8),     # 61.8% ga yaqin
        (103.8, 106.6, 103.6, 106.2), (106.2, 109, 106, 108.6),
        (108.6, 111.4, 108.4, 111),
    ])
    d, k = ch.sham_chizma(ketma, boyi=60 * mm)
    past, baland = 100.0, 110.4
    for daraja, nom in ((0.382, "38.2%"), (0.5, "50%"), (0.618, "61.8%")):
        narx = baland - (baland - past) * daraja
        ch.gorizontal(d, k, narx, nom, rang=ch.KOK, yorliq_chapda=True)
    ch.gorizontal(d, k, baland, "100% — tepa", rang=ch.MATN_PAST)
    ch.gorizontal(d, k, past, "0% — tub", rang=ch.MATN_PAST)
    ch.izoh_matni(d, k.x(5.8), k.y(102.4), "narx qaytdi va davom etdi",
                  markaz=True, rang=ch.APELSIN)
    return d


# --------------------------------------------------------------------------- #
#  16-bob: trendliniya, hajm, indikatorlar
# --------------------------------------------------------------------------- #


def _grafik_trendliniya() -> sxema.Drawing:
    ketma = ch.shamlar([
        (100, 102.6, 99.6, 102.2), (102.2, 102.6, 100.4, 100.8),
        (100.8, 105.4, 100.6, 105), (105, 105.4, 102.4, 102.8),
        (102.8, 108, 102.6, 107.6), (107.6, 108, 104.6, 105),
        (105, 110.4, 104.8, 110), (110, 110.4, 106.8, 107.2),
        (107.2, 108, 104.2, 104.6),   # trendliniya uzildi
    ])
    d, k = ch.sham_chizma(ketma, boyi=56 * mm)
    ch.chiziq(d, [(k.x(1), k.y(100.4)), (k.x(7), k.y(106.8))], rang=ch.TURKUAZ)
    ch.izoh_matni(d, k.x(3), k.y(99.6), "har yangi tub OLDINGISIDAN baland",
                  markaz=True)
    ch.strelka(d, k.x(8), k.y(107.4), k.x(8), k.y(104.8), rang=ch.SHAM_TUSHDI)
    ch.izoh_matni(d, k.x(8), k.y(108.6), "uzildi", markaz=True, rang=ch.SHAM_TUSHDI)
    return d


def _diagramma_indikator() -> sxema.Drawing:
    """EMA, RSI va hajm — uchalasi bitta sahifada."""
    d = sxema.yangi(boyi=60 * mm)
    sxema.matn(d, 80 * mm, 55 * mm, "Uch xil indikator — uch xil savol",
               qalin=True, olcham=8.5)
    sxema.chiziqli(
        d, 14 * mm, 30 * mm, 40 * mm, 18 * mm,
        [100, 101, 103, 102, 105, 107, 106, 109],
        rang=sxema.KOK, yorliq="EMA — o'rtacha yo'nalish",
    )
    sxema.matn(d, 34 * mm, 25 * mm, "«Umumiy yo'nalish qayoqqa?»",
               olcham=7, rang=sxema.MATN_PAST)
    sxema.chiziqli(
        d, 59 * mm, 30 * mm, 42 * mm, 18 * mm,
        [45, 52, 63, 71, 78, 74, 62, 55],
        rang=sxema.APELSIN, yorliq="RSI — kuch",
    )
    sxema.matn(d, 80 * mm, 25 * mm, "«Harakat haddan oshdimi?»",
               olcham=7, rang=sxema.MATN_PAST)
    sxema.ustunli(
        d, 106 * mm, 30 * mm, 40 * mm, 18 * mm,
        [20, 35, 28, 62, 80, 30, 22, 18],
        sarlavha="Hajm — ishtirok",
        musbat=sxema.KOK_TOQ,
    )
    sxema.matn(d, 126 * mm, 25 * mm, "«Harakat ortida odam bormi?»",
               olcham=7, rang=sxema.MATN_PAST)
    # Uzun qator IKKIGA bo'linadi: markazlangan bitta qator chizma
    # kengligidan oshib ketardi.
    sxema.matn(d, 80 * mm, 16 * mm, "INDIKATOR NARXDAN KEYIN YURADI.",
               olcham=7.5, rang=sxema.APELSIN, qalin=True)
    sxema.matn(
        d, 80 * mm, 11 * mm,
        "U narxni bashorat qilmaydi — bo'lgan harakatni boshqa shaklda "
        "ko'rsatadi.",
        olcham=7.5, rang=sxema.APELSIN,
    )
    sxema.matn(
        d, 80 * mm, 5 * mm,
        "Shuning uchun indikator TASDIQ uchun ishlatiladi, qaror uchun emas.",
        olcham=7, rang=sxema.MATN_PAST,
    )
    return d


# --------------------------------------------------------------------------- #
#  Boblar
# --------------------------------------------------------------------------- #


def _bob11(u: dict) -> list:
    return [
        *bob_sarlavha(u, "11-BOB", "Sham (Candle) nima — OHLC"),
        *savol_bilan_boshla(
            u,
            "Grafikni birinchi marta ochganingizda yashil va qizil "
            "to'rtburchaklarni ko'rasiz. Ularning har biri aslida "
            "nima deyapti?",
        ),
        p(u, "Har bir to'rtburchak — bitta " + a("sham") + ". U <b>bitta vaqt "
             "oralig'ida</b> nima bo'lganini to'rtta raqam bilan aytadi. "
             "Bu to'rtlik " + a("OHLC") + " deb ataladi."),
        *royxat(u, [
            a("Open") + " — oraliq boshlanganda narx qayerda edi.",
            a("High") + " — oraliqdagi eng yuqori narx.",
            a("Low") + " — oraliqdagi eng past narx.",
            a("Close") + " — oraliq tugaganda narx qayerda edi.",
        ]),
        chizma_bilan(
            _sxema_sham_anatomiyasi(),
            "11.1-chizma. Yo'g'on qism — <b>tana</b> (ochilish va yopilish "
            "orasi). Ingichka chiziq — <b>soya</b> (eng yuqori va eng past).",
            u,
        ),
        h2(u, "O'suvchi va tushuvchi sham"),
        p(u, "Agar yopilish ochilishdan yuqori bo'lsa — sham <b>o'suvchi</b> "
             "(odatda yashil). Aksincha bo'lsa — <b>tushuvchi</b> (qizil). "
             "Rang shartli: uni istagancha o'zgartirsa bo'ladi, ma'no "
             "o'zgarmaydi."),
        h2(u, "Vaqt oralig'i — timeframe"),
        p(u, a("Timeframe") + " — bitta sham qancha vaqtni qamrashi. "
             "1 daqiqalik shamda 60 ta sham bir soatni beradi, kunlik "
             "shamda esa bitta sham butun kunni."),
        p(u, "Muhim: <b>bir xil bozor, turli timeframe — turli manzara.</b> "
             "Kunlik grafikda o'sish ko'rinayotgan paytda 15 daqiqalik "
             "grafikda tushish bo'lishi mumkin. Ikkalasi ham to'g'ri."),
        h2(u, "Soya nima aytadi"),
        p(u, "Uzun soya — <b>rad etilgan narx</b>. Narx o'sha yergacha bordi, "
             "lekin u yerda qololmadi va qaytib keldi."),
        chizma_bilan(
            _grafik_soya(),
            "11.2-chizma. Uzun pastki soya — pastga tushish rad etildi. "
            "Uzun tepa soya — yuqoriga chiqish rad etildi.",
            u,
        ),
        p(u, "Bu kuzatuv keyingi boblarda juda ko'p ishlatiladi: "
             "qo'llab-quvvatlash va qarshilik aynan shunday izlardan "
             "topiladi."),
        real_misol(
            u,
            "BTC/USDT kunlik grafik: uzun pastki soyali sham va undan "
            "keyingi harakat.",
        ),
        xulosa(u, [
            "Sham bitta vaqt oralig'ini to'rtta raqam bilan tasvirlaydi: "
            "Open, High, Low, Close.",
            "Tana — ochilish va yopilish orasi; soya — eng yuqori va eng past.",
            "Rang shartli; ma'noni Close va Open nisbati beradi.",
            "Uzun soya — narxning o'sha darajada <b>rad etilgani</b>.",
            "Bir xil bozor turli timeframe da turlicha ko'rinadi — ikkalasi "
            "ham to'g'ri.",
        ]),
        tekshiring(u, [
            "Sham tanasi qaysi ikki narxdan hosil bo'ladi?",
            "Uzun tepa soya nimani anglatadi?",
            "Kunlik grafikda o'sish, soatlikda tushish — bu qarama-qarshilikmi?",
        ]),
        PageBreak(),
    ]


def _bob12(u: dict) -> list:
    return [
        *bob_sarlavha(u, "12-BOB", "Support va Resistance"),
        *savol_bilan_boshla(
            u,
            "Grafikda narx bir necha marta bir xil darajaga tegib qaytadi. "
            "U yerda devor bormi? Nega aynan o'sha joy?",
        ),
        p(u, a("Qo'llab-quvvatlash") + " (Support) — narx pastga tushganda "
             "bir necha marta to'xtagan daraja. " + a("Qarshilik") +
             " (Resistance) — yuqoriga chiqqanda to'xtagan daraja."),
        chizma_bilan(
            _grafik_sr(),
            "12.1-chizma. Narx bir xil darajalarda qayta-qayta to'xtaydi — "
            "toki ulardan birini uzib o'tguncha.",
            u,
        ),
        h2(u, "Nega bu darajalar ishlaydi"),
        p(u, "Sehr yo'q. Sabab oddiy: <b>ko'pchilik o'sha darajaga qaraydi.</b>"),
        *royxat(u, [
            "O'tgan safar u yerdan sotib olganlar — endi ham sotib oladi.",
            "O'sha yerda zarar ko'rganlar — narx qaytganda \"tenglashib\" "
            "chiqmoqchi bo'ladi.",
            "Ko'p savdogar Stop buyrug'ini aynan o'sha darajalar ortiga qo'yadi.",
        ]),
        p(u, "Ya'ni daraja o'zi kuchli emas — <b>odamlarning unga munosabati</b> "
             "kuchli. Bu muhim tafovut: daraja abadiy emas va u albatta bir "
             "kun uziladi."),
        h2(u, "Uzilgandan keyin — rollar almashadi"),
        p(u, "Qarshilik uzib o'tilsa, u ko'pincha <b>qo'llab-quvvatlashga</b> "
             "aylanadi. Va aksincha."),
        chizma_bilan(
            _grafik_sr_almashuv(),
            "12.2-chizma. Bitta daraja: uzilgunga qadar qarshilik, undan "
            "keyin qo'llab-quvvatlash.",
            u,
        ),
        h3(u, "Daraja emas — ZONA"),
        p(u, "Amalda narx hech qachon aynan bir tiyingacha to'xtamaydi. "
             "Shuning uchun tajribali savdogarlar chiziq emas, "
             "<b>zona</b> chizadi — bir necha foizli oraliq. Chiziq "
             "chizsangiz, narx uni har safar \"biroz\" buzib o'tadi va siz "
             "chalkashasiz."),
        real_misol(
            u,
            "ETH/USDT 4 soatlik grafik: bir necha marta sinalgan qarshilik "
            "zonasi, uzilishi va qayta sinov.",
        ),
        xulosa(u, [
            "Support — pastda to'xtagan daraja, Resistance — yuqorida.",
            "Ular ishlaydi, chunki <b>ko'pchilik o'sha joyga qaraydi</b> — "
            "sehr emas, xotira.",
            "Uzilgandan keyin rollar ko'pincha almashadi.",
            "Chiziq emas, <b>zona</b> chizing: narx aniq nuqtada to'xtamaydi.",
        ]),
        tekshiring(u, [
            "Nega narx bir xil darajada qayta-qayta to'xtaydi?",
            "Uzilgan qarshilik nimaga aylanishi mumkin?",
            "Nega chiziq emas, zona chizish tavsiya etiladi?",
        ]),
        PageBreak(),
    ]


def _bob13(u: dict) -> list:
    return [
        *bob_sarlavha(u, "13-BOB", "Bozor strukturasi"),
        *savol_bilan_boshla(
            u,
            "\"Trend do'stingiz\" degan gapni eshitgansiz. Lekin trend "
            "hozir qayoqqa qarab ketayotganini QANDAY aniqlaysiz? "
            "Ko'z bilanmi?",
        ),
        p(u, "Ko'z aldaydi. Struktura esa aniq qoidaga tayanadi, va u "
             "qoida ikkita tushunchadan boshlanadi."),
        h2(u, "Swing High va Swing Low"),
        p(u, a("Swing High") + " — chap va o'ng tomonidagi shamlardan "
             "baland bo'lgan cho'qqi. " + a("Swing Low") + " — chap va "
             "o'ngidagilardan past bo'lgan tub."),
        p(u, "Eng keng tarqalgan qoida — <b>5 shamli fraktal</b>: o'rtadagi "
             "shamning cho'qqisi chapdagi ikkitasidan ham, o'ngdagi "
             "ikkitasidan ham baland bo'lishi kerak."),
        chizma_bilan(
            _grafik_swing(),
            "13.1-chizma. Swing nuqtasi faqat o'ngdagi ikki sham yopilgandan "
            "KEYIN tasdiqlanadi — ya'ni u har doim biroz kechikadi.",
            u,
        ),
        p(u, "Oxirgi jumla muhim: swing nuqtasini <b>real vaqtda</b> "
             "bilib bo'lmaydi. Siz uni faqat keyin ko'rasiz. Buni unutgan "
             "odam grafikni orqaga qarab o'qib, o'zini aldaydi."),
        h2(u, "Trend — swing nuqtalarning ketma-ketligi"),
        p(u, "Endi trendni aniq ta'riflash mumkin:"),
        *royxat(u, [
            a("O'sish trendi") + " (Uptrend) — har yangi cho'qqi oldingisidan "
            "baland (" + a("HH") + ", Higher High) va har yangi tub "
            "oldingisidan baland (" + a("HL") + ", Higher Low).",
            a("Tushish trendi") + " (Downtrend) — har yangi cho'qqi pastroq "
            "(" + a("LH") + ", Lower High) va har yangi tub pastroq "
            "(" + a("LL") + ", Lower Low).",
        ]),
        chizma_bilan(
            _grafik_trend(),
            "13.2-chizma. Trend — fikr emas, ketma-ketlik. Chapda HH va HL, "
            "o'ngda LH va LL.",
            u,
        ),
        p(u, "Ketma-ketlik buzilsa — masalan o'sish trendida yangi tub "
             "oldingisidan past bo'lsa — bu <b>ogohlantirish</b>. Trend "
             "hali o'zgarmagan bo'lishi mumkin, lekin u zaiflashdi."),
        h3(u, "Yon harakat"),
        p(u, "Uchinchi holat ham bor va u eng ko'p uchraydi: " + a("yon "
             "harakat") + " (range). Bunda cho'qqilar ham, tublar ham "
             "taxminan bir xil darajada qoladi. Trend yo'q — bozor "
             "\"nafas olyapti\"."),
        real_misol(
            u,
            "Istalgan coinning kunlik grafigi: HH/HL ketma-ketligi "
            "belgilangan o'sish trendi va uning buzilish nuqtasi.",
        ),
        xulosa(u, [
            "Swing High/Low — 5 shamli fraktal bilan aniqlanadigan cho'qqi "
            "va tub.",
            "Swing nuqta faqat keyin tasdiqlanadi — real vaqtda bilib "
            "bo'lmaydi.",
            "O'sish trendi = HH + HL; tushish trendi = LH + LL.",
            "Ketma-ketlik buzilishi — trend o'zgargani emas, zaiflashgani.",
            "Uchinchi holat — yon harakat, va u eng ko'p uchraydi.",
        ]),
        tekshiring(u, [
            "5 shamli fraktal qoidasini o'z so'zingiz bilan ayting.",
            "O'sish trendi qaysi ikki shart bilan ta'riflanadi?",
            "Nega swing nuqtani real vaqtda aniqlab bo'lmaydi?",
        ]),
        PageBreak(),
    ]


def _bob14(u: dict) -> list:
    return [
        *bob_sarlavha(u, "14-BOB", "Pattern (naqsh)lar"),
        *savol_bilan_boshla(
            u,
            "Grafikda \"bosh va yelkalar\", \"uchburchak\" kabi shakllar "
            "haqida eshitgansiz. Ular haqiqatan ishlaydimi — yoki bulutda "
            "hayvon ko'rgandek gapmi?",
        ),
        p(u, "Halol javob: <b>ikkalasi ham to'g'ri.</b> Pattern — bozor "
             "strukturasining takrorlanadigan ko'rinishi, lekin uni "
             "istagan joyda \"ko'rib\" olish ham oson."),
        p(u, "Shuning uchun bu bobda ikkita eng keng tarqalgan naqsh "
             "ko'rsatiladi va ularning <b>ma'nosi</b> tushuntiriladi — "
             "shakli emas."),
        h2(u, "Bosh va yelkalar"),
        p(u, a("Bosh va yelkalar") + " (Head and Shoulders) — o'rtadagi "
             "cho'qqi ikki yonidagidan baland bo'lgan uchta cho'qqi."),
        chizma_bilan(
            _grafik_bosh_yelka(),
            "14.1-chizma. Ma'nosi: o'sish kuchi tugadi. O'ng yelka boshdan "
            "past — ya'ni xaridorlar oldingi cho'qqini takrorlay olmadi.",
            u,
        ),
        p(u, "Diqqat qiling: bu shakl 13-bobdagi struktura tilida "
             "<b>LH</b> hosil bo'lganini bildiradi. Ya'ni pattern yangi "
             "narsa emas — u strukturaning ko'rinishi."),
        h2(u, "Uchburchak"),
        p(u, a("Uchburchak") + " — cho'qqilar pasayib, tublar ko'tarilib, "
             "narx torayib boradigan holat."),
        chizma_bilan(
            _grafik_uchburchak(),
            "14.2-chizma. Ma'nosi: ikki tomon ham qat'iy emas, harakat "
            "siqilmoqda. Siqilish uzoq davom etmaydi.",
            u,
        ),
        p(u, "Uchburchak <b>yo'nalish aytmaydi</b>. U faqat \"tez orada "
             "keskin harakat bo'lishi mumkin\" deydi. Qaysi tomonga — "
             "chiqishdan oldin bilib bo'lmaydi."),
        h2(u, "Pattern bilan ishlash qoidalari"),
        *royxat(u, [
            "<b>Avval struktura, keyin shakl.</b> Agar pattern strukturaga "
            "zid bo'lsa, strukturaga ishoning.",
            "<b>Tasdiqni kuting.</b> Bosh va yelkalar bo'yin chizig'i "
            "uzilgunga qadar — bu shunchaki uchta cho'qqi.",
            "<b>Har joyda pattern qidirmang.</b> Izlagan odam topadi — "
            "bo'lmasa ham.",
        ]),
        real_misol(
            u,
            "Haqiqiy grafikdan bosh va yelkalar namunasi: uchta cho'qqi, "
            "bo'yin chizig'i va uzilish shami belgilangan.",
        ),
        xulosa(u, [
            "Pattern — strukturaning takrorlanadigan ko'rinishi, alohida "
            "sehr emas.",
            "Bosh va yelkalar o'sish kuchining tugaganini ko'rsatadi (LH).",
            "Uchburchak yo'nalish aytmaydi — faqat siqilishni ko'rsatadi.",
            "Tasdiqsiz pattern — hali pattern emas.",
        ]),
        tekshiring(u, [
            "Bosh va yelkalar struktura tilida nimani bildiradi?",
            "Uchburchak qaysi tomonga chiqishini oldindan aytadimi?",
            "Pattern strukturaga zid bo'lsa, qaysi biriga ishonasiz?",
        ]),
        PageBreak(),
    ]


def _bob15(u: dict) -> list:
    return [
        *bob_sarlavha(u, "15-BOB", "Fibonacci"),
        *savol_bilan_boshla(
            u,
            "Narx ko'tarildi, keyin biroz qaytdi. Qayerga qadar qaytishi "
            "mumkin — buni oldindan taxmin qilsa bo'ladimi?",
        ),
        p(u, "Fibonacci darajalarining butun maqsadi shu savolga taxminiy "
             "javob berish."),
        h2(u, "Ketma-ketlik qayerdan kelgan"),
        p(u, "XIII asrda italiyalik matematik Leonardo Fibonacci shunday "
             "ketma-ketlikni tasvirlagan: <b>1, 1, 2, 3, 5, 8, 13, 21…</b> "
             "— har son oldingi ikkitasining yig'indisi."),
        p(u, "Qiziq xossasi: qo'shni sonlar nisbati taxminan "
             "<b>0.618</b> ga intiladi. Aynan shu raqam savdoda "
             "ishlatiladigan 61.8% darajasini beradi."),
        h2(u, "Retracement darajalari"),
        p(u, a("Retracement") + " — o'sishdan keyingi qaytish. Fibonacci "
             "asosiy uchta darajani beradi:"),
        jadval(
            u,
            ["Daraja", "Ma'nosi", "Qanday o'qiladi"],
            [
                ["38.2%", "Sayoz qaytish",
                 "Trend kuchli — qaytish qisqa bo'ldi"],
                ["50%", "O'rta qaytish",
                 "Fibonacci soni emas, lekin an'anaviy ravishda qaraladi"],
                ["61.8%", "Chuqur qaytish",
                 "Oxirgi chegara — undan pastga tushsa, trend shubha ostida"],
            ],
            [22 * mm, 46 * mm, 80 * mm],
        ),
        Spacer(1, 4 * mm),
        chizma_bilan(
            _grafik_fib(),
            "15.1-chizma. Darajalar tub (0%) va cho'qqi (100%) orasiga "
            "tortiladi. Narx ulardan birida to'xtab, harakatni davom "
            "ettirishi mumkin.",
            u,
        ),
        h2(u, "Eng ko'p qilinadigan xato"),
        p(u, "Fibonacci <b>o'zi bilan</b> ishlamaydi. U faqat \"e'tibor "
             "berish mumkin bo'lgan joy\" ko'rsatadi."),
        p(u, "Kuchli signal — Fibonacci darajasi <b>boshqa narsa bilan mos "
             "tushganda</b> paydo bo'ladi: masalan 61.8% aynan oldingi "
             "qo'llab-quvvatlash zonasiga to'g'ri kelsa."),
        p(u, "Yana bir xato — darajalarni qayerdan tortishni har safar "
             "o'zgartirish. Agar siz uch marta qayta tortsangiz, "
             "to'rtinchisida albatta \"ishlaydigan\" daraja topasiz. "
             "Bu — tahlil emas, o'zini aldash."),
        real_misol(
            u,
            "Kunlik grafikda Fibonacci retracement: 61.8% darajasi eski "
            "support zonasi bilan ustma-ust tushgan holat.",
        ),
        xulosa(u, [
            "Fibonacci ketma-ketligidagi nisbat 0.618 ga intiladi — 61.8% "
            "shundan.",
            "Asosiy retracement darajalari: 38.2%, 50%, 61.8%.",
            "Darajalar tub va cho'qqi orasiga tortiladi.",
            "Fibonacci yolg'iz ishlamaydi — u boshqa dalil bilan mos "
            "tushgandagina kuchli.",
            "Darajani qayta-qayta tortish — tahlil emas, o'zini aldash.",
        ]),
        tekshiring(u, [
            "61.8% raqami qayerdan kelib chiqqan?",
            "50% Fibonacci sonimi?",
            "Fibonacci darajasi qachon kuchli signal beradi?",
        ]),
        PageBreak(),
    ]


def _bob16(u: dict) -> list:
    return [
        *bob_sarlavha(u, "16-BOB", "Trendliniya, hajm va indikatorlar"),
        *savol_bilan_boshla(
            u,
            "TradingView da yuzlab indikator bor. Qaysi birini yoqish "
            "kerak? Va nega tajribali savdogarlarning grafigi ko'pincha "
            "deyarli bo'sh bo'ladi?",
        ),
        p(u, "Javob bobning oxirida. Avval uchta asosiy vositani ko'ramiz."),
        h2(u, "Trendliniya"),
        p(u, a("Trendliniya") + " — ketma-ket tublarni (yoki cho'qqilarni) "
             "bog'laydigan chiziq. U 13-bobdagi strukturani <b>ko'rinadigan</b> "
             "qiladi."),
        chizma_bilan(
            _grafik_trendliniya(),
            "16.1-chizma. Chiziq kamida ikkita nuqtadan tortiladi; "
            "uchinchi nuqta uni tasdiqlaydi.",
            u,
        ),
        p(u, "Qoida: chiziqni <b>narxga moslashtirmang</b>. Agar chiziq "
             "faqat bitta usulda tortilganda ishlasa, u ishlamaydi."),
        h2(u, "Hajm (Volume)"),
        p(u, a("Hajm") + " — o'sha oraliqda qancha savdo bo'lgani. U "
             "yo'nalish aytmaydi, lekin bitta muhim savolga javob beradi: "
             "<b>harakat ortida odam bormi?</b>"),
        *royxat(u, [
            "Katta hajmli o'sish — ko'pchilik ishtirok etdi, harakat "
            "ishonchliroq.",
            "Kichik hajmli o'sish — bir nechta buyruq narxni surdi, "
            "u tez qaytishi mumkin.",
            "Uzilish (breakout) paytidagi hajm — eng muhim tasdiqlardan biri.",
        ]),
        h2(u, "RSI, MACD, EMA"),
        p(u, a("EMA") + " (eksponensial siljuvchi o'rtacha) — oxirgi "
             "shamlarga ko'proq vazn beruvchi o'rtacha narx. U shovqinni "
             "tozalaydi va umumiy yo'nalishni ko'rsatadi."),
        p(u, a("RSI") + " — 0 dan 100 gacha bo'lgan kuch o'lchovi. 70 dan "
             "yuqori \"haddan oshgan o'sish\", 30 dan past \"haddan oshgan "
             "tushish\" deb o'qiladi."),
        p(u, a("MACD") + " — ikki EMA orasidagi farq. U yo'nalish "
             "o'zgarishini boshqa shaklda ko'rsatadi."),
        chizma_bilan(
            _diagramma_indikator(),
            "16.2-chizma. Uchala indikator ham NARXDAN hisoblanadi — "
            "ular yangi ma'lumot emas, o'sha ma'lumotning boshqa ko'rinishi.",
            u,
        ),
        h3(u, "Nega tajribali grafik bo'sh bo'ladi"),
        p(u, "Chunki indikator narxdan keyin yuradi. Beshta indikator "
             "yoqsangiz, beshtasi ham bir narsani — <b>allaqachon bo'lgan "
             "harakatni</b> — besh xil shaklda ko'rsatadi."),
        p(u, "RSI 70 dan oshdi degani \"soting\" degani emas: kuchli "
             "trendda RSI haftalab 70 dan yuqori turishi mumkin. Indikator "
             "<b>tasdiq</b> uchun, qaror uchun emas."),
        real_misol(
            u,
            "Kuchli trend davrida RSI uzoq vaqt 70 dan yuqori turgan "
            "grafik — \"haddan oshgan\" degan xulosaning xatosi ko'rinsin.",
        ),
        xulosa(u, [
            "Trendliniya strukturani ko'rinadigan qiladi; uni narxga "
            "moslashtirmang.",
            "Hajm yo'nalish aytmaydi — <b>ishtirok</b>ni aytadi.",
            "EMA yo'nalish, RSI kuch, MACD o'zgarish haqida gapiradi.",
            "Indikatorlar narxdan hisoblanadi — ular narxdan oldin "
            "yurmaydi.",
            "RSI 70 \"soting\" degani emas; indikator tasdiq uchun ishlatiladi.",
        ]),
        tekshiring(u, [
            "Hajm qaysi savolga javob beradi?",
            "Nega beshta indikator bittasidan yaxshi emas?",
            "RSI 75 ni ko'rsatdi. Qanday qo'shimcha ma'lumot kerak?",
        ]),
        PageBreak(),
    ]


def bolim3(u: dict) -> list:
    return [
        *bolim_ajratkich(u, "3-BO‘LIM", "KLASSIK TEXNIK TAHLIL"),
        *_bob11(u),
        *_bob12(u),
        *_bob13(u),
        *_bob14(u),
        *_bob15(u),
        *_bob16(u),
    ]
