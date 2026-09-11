"""4-BO'LIM: SMART MONEY CONCEPTS — 17-18 boblar.

3-bo'limda grafikni o'qishni o'rgandik. Bu bo'lim bitta savol
qo'shadi: grafikdagi harakat ortida KIM turadi.

OGOHLANTIRISH KITOB ICHIDA HAM BOR: SMC — ommalashgan yondashuv,
lekin uning atamalari ko'pincha haddan tashqari ishonch bilan
ishlatiladi. Bu yerda ular tushuncha sifatida beriladi, kafolat
sifatida emas.
"""

from __future__ import annotations

from reportlab.platypus import PageBreak

from scripts.kitob import chizma as ch
from scripts.kitob import sxema
from scripts.kitob.bloklar import (
    a,
    chizma_bilan,
    h2,
    h3,
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


def _sxema_kim() -> sxema.Drawing:
    """Katta va kichik ishtirokchi — buyruq hajmi farqi."""
    d = sxema.yangi(boyi=46 * sxema.mm)
    sxema.matn(d, 80 * sxema.mm, 41 * sxema.mm,
               "Katta buyruqni bir zarbada bajarib bo'lmaydi",
               qalin=True, olcham=8.5)
    mm = sxema.mm
    sxema.quti(d, 10 * mm, 24 * mm, 46 * mm, 13 * mm,
               ["KICHIK ISHTIROKCHI", "$1 000 — bir bosishda"],
               ramka=sxema.TURKUAZ, ichi=sxema.colors.HexColor("#eef9fb"))
    sxema.quti(d, 94 * mm, 24 * mm, 46 * mm, 13 * mm,
               ["YIRIK ISHTIROKCHI", "$50 mln — bir bosishda EMAS"],
               ramka=sxema.APELSIN, ichi=sxema.colors.HexColor("#fff4e8"),
               sarlavha_rang=sxema.APELSIN)
    sxema.oq(d, 33 * mm, 22 * mm, 33 * mm, 15 * mm, rang=sxema.MATN_PAST)
    sxema.matn(d, 33 * mm, 11 * mm, "narxga ta'siri yo'q", olcham=7,
               rang=sxema.MATN_PAST)
    sxema.oq(d, 117 * mm, 22 * mm, 117 * mm, 15 * mm, rang=sxema.APELSIN)
    sxema.matn(d, 117 * mm, 11 * mm, "narxni O'ZI surib yuboradi", olcham=7,
               rang=sxema.APELSIN)
    sxema.matn(
        d, 80 * mm, 4 * mm,
        "Shuning uchun yirik buyruq bo'lib-bo'lib bajariladi — va bu "
        "grafikda IZ qoldiradi.",
        olcham=7.5, rang=sxema.MATN,
    )
    return d


def _grafik_bos_choch() -> sxema.Drawing:
    """BOS — trend davomi; CHOCH — xarakter o'zgarishi."""
    ketma = ch.shamlar([
        (100, 102.6, 99.6, 102.2), (102.2, 102.6, 100.6, 101),
        (101, 106.2, 100.8, 105.8),   # BOS: oldingi cho'qqidan oshdi
        (105.8, 106, 103.2, 103.6),
        (103.6, 109.4, 103.4, 109),   # yana BOS
        (109, 109.4, 105.8, 106.2),
        (106.2, 107, 102.8, 103.2),   # CHOCH: oxirgi HL buzildi
        (103.2, 104, 100.2, 100.6),
        (100.6, 102, 100.2, 101.6),
    ])
    d, k = ch.sham_chizma(ketma, boyi=60 * sxema.mm)
    ch.gorizontal(d, k, 102.6, "oldingi cho'qqi", rang=ch.MATN_PAST,
                  yorliq_chapda=True)
    ch.gorizontal(d, k, 103.2, "oxirgi HL", rang=ch.KOK)
    ch.nuqta(d, k, 2, 106.2, "BOS", rang=ch.SHAM_OSDI)
    ch.nuqta(d, k, 6, 102.8, "CHOCH", rang=ch.SHAM_TUSHDI, tepada=False)
    ch.izoh_matni(d, k.x(4), k.y(110.6), "trend DAVOM etmoqda", markaz=True,
                  rang=ch.SHAM_OSDI)
    ch.izoh_matni(d, k.x(7.2), k.y(110.6), "xarakter O'ZGARDI", markaz=True,
                  rang=ch.SHAM_TUSHDI)
    return d


def _grafik_ob() -> sxema.Drawing:
    """Order Block — keskin harakatdan OLDINGI qarama-qarshi sham."""
    ketma = ch.shamlar([
        (100, 101, 99.6, 100.8), (100.8, 101.2, 100.2, 100.6),
        (100.6, 100.8, 99.8, 99.9),   # OB: keskin o'sishdan oldingi tushuvchi
        (99.9, 106.4, 99.8, 106),     # keskin harakat
        (106, 108.2, 105.8, 107.8),
        (107.8, 108, 104.6, 105),
        (105, 105.4, 100.4, 100.8),   # OB ga qaytdi
        (100.8, 104, 100.5, 103.6),
        (103.6, 107, 103.4, 106.8),
    ])
    d, k = ch.sham_chizma(ketma, boyi=62 * sxema.mm, tepa_joy=12)
    ch.zona(d, k, 2, 8, 99.8, 100.8, "ORDER BLOCK", rang=ch.APELSIN)
    ch.izoh_pastda(d, k.x(3.4), "keskin harakat SHU YERDAN boshlandi")
    ch.strelka(d, k.x(6), k.y(108.2), k.x(6), k.y(102.4), rang=ch.KOK)
    ch.izoh_tepada(d, k.x(6), "narx qaytib keldi", rang=ch.KOK)
    return d


def _grafik_fvg() -> sxema.Drawing:
    """FVG — uch shamda qolgan bo'shliq."""
    ketma = ch.shamlar([
        (100, 101.4, 99.6, 101.2),    # 1-sham: high = 101.4
        (101.2, 106.6, 101, 106.2),   # 2-sham: katta
        (106.2, 107, 102.8, 106.6),   # 3-sham: low = 102.8 > 101.4 -> bo'shliq
        (106.6, 107.4, 105.8, 106.2),
        (106.2, 106.4, 102.4, 102.8),  # bo'shliqni to'ldirdi
        (102.8, 105.6, 102.6, 105.2),
        (105.2, 108.4, 105, 108),
    ])
    d, k = ch.sham_chizma(ketma, boyi=58 * sxema.mm)
    ch.zona(d, k, 0, 6, 101.4, 102.8, "FVG — bo'shliq", rang=ch.KOK,
            shaffoflik=0.22)
    ch.izoh_matni(d, k.x(1), k.y(99.4),
                  "1-sham tepasi va 3-sham tubi TEGISHMADI", markaz=True)
    ch.strelka(d, k.x(4), k.y(100.2), k.x(4), k.y(102.2), rang=ch.APELSIN)
    ch.izoh_matni(d, k.x(4.4), k.y(99.2), "narx bo'shliqni to'ldirdi",
                  markaz=True, rang=ch.APELSIN)
    return d


def _grafik_likvidlik() -> sxema.Drawing:
    """Likvidlik va sweep — Stop larning to'planishi va yig'ib olinishi."""
    ketma = ch.shamlar([
        (100, 104.2, 99.8, 103.8), (103.8, 104.4, 101.2, 101.6),
        (101.6, 104.3, 101.4, 104), (104, 104.2, 100.8, 101.2),
        (101.2, 101.6, 98.2, 101.4),   # SWEEP: tubni yalab o'tdi va qaytdi
        (101.4, 105, 101.2, 104.8), (104.8, 108.6, 104.6, 108.2),
    ])
    d, k = ch.sham_chizma(ketma, boyi=58 * sxema.mm)
    ch.gorizontal(d, k, 100.9, "tublar bir xil — Stop lar SHU YERDA",
                  rang=ch.SHAM_TUSHDI, yorliq_chapda=True)
    ch.zona(d, k, 4, 4, 98.2, 100.9, "sweep", rang=ch.APELSIN, shaffoflik=0.25)
    ch.strelka(d, k.x(5), k.y(99.4), k.x(5), k.y(104.4), rang=ch.SHAM_OSDI)
    ch.izoh_matni(d, k.x(5.6), k.y(98.6), "yig'ib oldi va QAYTDI",
                  markaz=True, rang=ch.SHAM_OSDI)
    return d


def _grafik_discount() -> sxema.Drawing:
    """Discount va Premium — oraliqning yarmiga nisbatan."""
    ketma = ch.shamlar([
        (100, 101, 99.6, 100.8), (100.8, 106, 100.6, 105.6),
        (105.6, 110.4, 105.4, 110), (110, 110.2, 106.6, 107),
        (107, 107.4, 103.4, 103.8), (103.8, 104.2, 101.6, 102),
        (102, 105, 101.8, 104.6), (104.6, 108, 104.4, 107.6),
    ])
    d, k = ch.sham_chizma(ketma, boyi=58 * sxema.mm)
    orta = (100.0 + 110.4) / 2
    ch.zona(d, k, 0, 7, orta, 110.4, "PREMIUM — sotish uchun qulayroq",
            rang=ch.SHAM_TUSHDI, shaffoflik=0.10)
    ch.zona(d, k, 0, 7, 100.0, orta, "DISCOUNT — sotib olish uchun qulayroq",
            rang=ch.SHAM_OSDI, shaffoflik=0.10)
    ch.gorizontal(d, k, orta, "50%", rang=ch.KOK)
    return d


# --------------------------------------------------------------------------- #
#  Boblar
# --------------------------------------------------------------------------- #


def _bob17(u: dict) -> list:
    return [
        *bob_sarlavha(u, "17-BOB", "Smart Money Concepts — asosiy g'oya"),
        *savol_bilan_boshla(
            u,
            "Grafikda narx qayerga borishini o'rgandik. Endi boshqa savol: "
            "narxni SURAYOTGAN kim? Va uning izini ko'rish mumkinmi?",
        ),
        p(u, a("Smart Money") + " — \"aqlli pul\" deb tarjima qilinadi. "
             "Bu atama yirik ishtirokchilarni bildiradi: fondlar, "
             "marketmeykerlar, katta kapitalga ega savdogarlar."),
        h2(u, "Nega ular alohida o'rganiladi"),
        p(u, "Sabab \"aqlliroq\" bo'lgani emas. Sabab <b>hajm</b>."),
        p(u, "Sizning $1 000 lik buyrug'ingiz bozorga umuman ta'sir "
             "qilmaydi. $50 millionlik buyruq esa narxni o'zi surib "
             "yuboradi — ya'ni uni bir zarbada bajarib bo'lmaydi."),
        chizma_bilan(
            _sxema_kim(),
            "17.1-chizma. Yirik buyruq bo'lib-bo'lib bajarilishi shart. "
            "Aynan shu majburiyat grafikda iz qoldiradi.",
            u,
        ),
        p(u, "SMC ning butun mantiqi shunda: <b>katta pul yashirinolmaydi.</b> "
             "U harakat qilish uchun qarshi tomonni topishi kerak, va bu "
             "izlanish grafikda ko'rinadi."),
        h2(u, "Klassik tahlildan farqi"),
        p(u, "Klassik tahlil <b>shakl</b>ga qaraydi: daraja, pattern, "
             "indikator. SMC esa <b>sabab</b>ga qaraydi: bu yerda kim, "
             "nima uchun, qanday buyruq qoldirdi."),
        p(u, "Amalda ikkalasi bir-birini inkor qilmaydi. SMC ning ko'p "
             "atamasi — 3-bo'limdagi tushunchalarning boshqa nomi. "
             "Masalan Order Block ko'pincha oddiy qo'llab-quvvatlash "
             "zonasining o'zi bo'lib chiqadi."),
        h3(u, "Halol ogohlantirish"),
        p(u, "SMC juda ommalashgan, va u bilan birga ko'p <b>haddan tashqari "
             "ishonch</b> ham keldi. \"Bu Order Block, demak narx shu "
             "yerdan qaytadi\" degan gap — kafolat emas."),
        p(u, "Bu kitob SMC ni <b>tushuncha</b> sifatida beradi: nimaga "
             "e'tibor berish mumkinligini ko'rsatadi. Undan qanday "
             "foydalanish va u qanchalik ishonchli ekani — sizning "
             "o'lchovingiz va javobgarligingiz."),
        real_misol(
            u,
            "Yirik harakat oldidan hosil bo'lgan to'planish zonasi — "
            "keskin o'sishdan oldingi tinch davr ko'rinsin.",
        ),
        xulosa(u, [
            "Smart Money — yirik ishtirokchilar; ular \"aqlliroq\" emas, "
            "<b>kattaroq</b>.",
            "Katta buyruqni bir zarbada bajarib bo'lmaydi — u iz qoldiradi.",
            "Klassik tahlil shaklga, SMC sababga qaraydi.",
            "SMC atamalarining ko'pi klassik tushunchalarning boshqa nomi.",
            "\"Order Block bor, demak qaytadi\" — bu kafolat emas.",
        ]),
        tekshiring(u, [
            "Nega yirik buyruq grafikda iz qoldiradi?",
            "SMC va klassik tahlil qaysi jihatdan farq qiladi?",
            "\"Bu FVG, demak narx shu yerga qaytadi\" — bu gapda qanday "
            "muammo bor?",
        ]),
        PageBreak(),
    ]


def _bob18(u: dict) -> list:
    return [
        *bob_sarlavha(u, "18-BOB", "SMC instrumentlari va qoidalari"),
        *savol_bilan_boshla(
            u,
            "Katta pul iz qoldiradi. Xo'sh, o'sha iz grafikda aynan "
            "qanday ko'rinadi?",
        ),
        p(u, "Quyida beshta asosiy tushuncha. Har biri 13-bobdagi "
             "strukturaga tayanadi — shuning uchun u bobni eslamasangiz, "
             "qaytib o'qing."),
        h2(u, "BOS va CHOCH"),
        p(u, a("BOS") + " (Break of Structure) — narx oldingi cho'qqidan "
             "(yoki tubdan) o'tib ketishi. Bu <b>trend davom etmoqda</b> "
             "degani."),
        p(u, a("CHOCH") + " (Change of Character) — trendga QARSHI "
             "tomondagi struktura buzilishi. O'sish trendida oxirgi HL "
             "buzilsa — bu CHOCH."),
        chizma_bilan(
            _grafik_bos_choch(),
            "18.1-chizma. BOS — davom; CHOCH — birinchi jiddiy "
            "ogohlantirish. CHOCH hali trend o'zgardi degani emas.",
            u,
        ),
        h2(u, "Order Block"),
        p(u, a("Order Block") + " (OB) — keskin harakatdan <b>oldingi</b> "
             "qarama-qarshi rangdagi sham. Mantiq: yirik xaridor o'sha "
             "yerda buyruq qoldirgan va hammasini bajara olmagan."),
        chizma_bilan(
            _grafik_ob(),
            "18.2-chizma. OB — keskin o'sishdan oldingi oxirgi tushuvchi "
            "sham. Narx qaytib kelganda u ko'pincha qo'llab-quvvatlash "
            "vazifasini bajaradi.",
            u,
        ),
        p(u, "Har qanday sham OB emas. Ikki shart bor: (1) undan keyin "
             "<b>keskin</b> harakat bo'lishi, (2) o'sha harakat strukturani "
             "buzishi (BOS)."),
        h2(u, "FVG — Fair Value Gap"),
        p(u, a("FVG") + " — uchta ketma-ket shamda qoladigan bo'shliq: "
             "birinchi shamning tepasi va uchinchi shamning tubi "
             "<b>tegishmaydi</b>."),
        chizma_bilan(
            _grafik_fvg(),
            "18.3-chizma. Bo'shliq — narx u yerdan juda tez o'tgani belgisi. "
            "Bozor ko'pincha keyin qaytib, o'sha oraliqni \"to'ldiradi\".",
            u,
        ),
        h2(u, "Likvidlik va Liquidity Sweep"),
        p(u, a("Likvidlik") + " — bu yerda \"bajarilishga tayyor buyruqlar "
             "to'plami\" ma'nosida. Ular qayerda to'planadi? Ko'pchilik "
             "Stop qo'yadigan joyda: bir xil darajadagi tublar yoki "
             "cho'qqilar ortida."),
        p(u, a("Liquidity Sweep") + " — narxning o'sha darajani qisqa vaqt "
             "yalab o'tib, darhol qaytishi."),
        chizma_bilan(
            _grafik_likvidlik(),
            "18.4-chizma. Uzun soya — Stop lar yig'ib olingani belgisi. "
            "Narx u yerda qolmadi, ya'ni maqsad boshqa edi.",
            u,
        ),
        p(u, "Buni \"kimdir sizni ovlayapti\" deb tushunish shart emas. "
             "Oddiyroq izoh ham bor: yirik xaridorga qarshi tomon kerak, "
             "va Stop larning ishga tushishi aynan shuni beradi."),
        h2(u, "Discount va Premium"),
        p(u, "Oraliqning yarmidan <b>pastki</b> qismi — " + a("Discount") +
             ", yuqorigi qismi — " + a("Premium") + "."),
        chizma_bilan(
            _grafik_discount(),
            "18.5-chizma. Sodda qoida: sotib olish Discount da, sotish "
            "Premium da qulayroq. Bu qoida emas — mo'ljal.",
            u,
        ),
        h3(u, "Bularni qanday birga ishlatiladi"),
        *royxat(u, [
            "Avval <b>struktura</b>: trend qayoqqa (HH/HL yoki LH/LL)?",
            "Keyin <b>CHOCH yoki BOS</b>: xarakter o'zgardimi?",
            "So'ng <b>zona</b>: OB yoki FVG qayerda?",
            "Oxirida <b>joylashuv</b>: bu zona Discount dami yoki Premium da?",
        ]),
        p(u, "Bir nechta dalil bir joyga to'planishi — SMC da eng ko'p "
             "qidiriladigan holat. Bitta dalil o'zi kam narsa aytadi."),
        real_misol(
            u,
            "4 soatlik grafik: CHOCH, undan keyingi Order Block va narxning "
            "o'sha zonaga qaytishi — uchalasi bitta ekranda belgilangan.",
        ),
        xulosa(u, [
            "BOS — trend davomi; CHOCH — qarshi tomondagi struktura "
            "buzilishi.",
            "Order Block — keskin harakatdan oldingi qarama-qarshi sham; "
            "u BOS bilan tasdiqlanishi kerak.",
            "FVG — uch shamda qolgan bo'shliq; bozor uni ko'pincha "
            "to'ldiradi.",
            "Likvidlik Stop lar to'plangan joyda; sweep — uni yig'ib olish.",
            "Discount/Premium — oraliqning yarmiga nisbatan joylashuv.",
            "Bitta dalil kam; SMC da dalillar <b>to'planishi</b> qidiriladi.",
        ]),
        tekshiring(u, [
            "BOS va CHOCH farqini bir jumlada ayting.",
            "Order Block bo'lishi uchun qanday ikki shart kerak?",
            "Liquidity Sweep dan keyin narx odatda qayerga qaytadi va nega?",
            "Nima uchun bitta OB o'zi yetarli dalil emas?",
        ]),
        PageBreak(),
    ]


def bolim4(u: dict) -> list:
    return [
        *bolim_ajratkich(u, "4-BO‘LIM", "SMART MONEY CONCEPTS"),
        *_bob17(u),
        *_bob18(u),
    ]
