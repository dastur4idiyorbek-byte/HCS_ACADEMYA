"""KIRISH — kitobdan oldingi qism.

Bu yerda o'quvchiga uchta narsa aytiladi: kitob nima haqida, uni
qanday o'qish kerak va nima VA'DA QILINMAYDI. Uchinchisi eng
muhimi — ta'lim materiali moliyaviy maslahat bilan aralashib
ketmasligi kerak.
"""

from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Spacer

from scripts.kitob.bloklar import a, h2, p, royxat
from scripts.kitob.qolip import bob_sarlavha


def kirish(u: dict) -> list:
    return [
        *bob_sarlavha(u, "KIRISH", "Bu kitob haqida"),
        h2(u, "HCS Academy nima"),
        p(u, a("HCS Academy") + " — HALOL CRYPTO SAVDO loyihasining ta'lim "
             "bo'limi. Uning vazifasi bitta: kripto bozorini <b>tushunadigan</b> "
             "odam tayyorlash. Signal berish emas, tushuntirish."),
        p(u, "Bu kitob — akademiyaning asosiy materiali. U kripto haqida hech "
             "narsa bilmaydigan odamdan boshlanadi va texnik tahlil, "
             "fundamental tahlil hamda risk boshqaruvigacha olib boradi."),
        h2(u, "Kitobni qanday o'qish kerak"),
        p(u, "Bu — ma'lumotnoma emas, <b>bosqichma-bosqich qo'llanma</b>. Har "
             "bob avvalgisiga tayanadi: 13-bobdagi \"struktura\" so'zi "
             "11-bobdagi \"sham\" tushunchasisiz ma'nosiz bo'lib qoladi."),
        *royxat(u, [
            "<b>Tartib bilan o'qing.</b> O'rtadan boshlash — vaqtni tejash "
            "emas, adashish.",
            "<b>Shoshilmang.</b> Bir bobni tushunmasdan keyingisiga o'tmang. "
            "Har bob oxirida xulosa bor — agar u tanish tuyulmasa, bobni "
            "qayta o'qing.",
            "<b>Chizmalarga qarang.</b> Kitobdagi har bir sxema matnni "
            "takrorlamaydi, u matnni ko'rsatadi.",
            "<b>Savollarga javob bering.</b> \"O'zingizni tekshiring\" "
            "savollarining javobi ataylab berilmagan — o'ylash o'qishdan "
            "ko'ra ko'proq o'rgatadi.",
        ]),
        h2(u, "Bu kitob nima VA'DA QILMAYDI"),
        p(u, "Buni boshidayoq aytib qo'yamiz, chunki kripto haqidagi "
             "materiallarning ko'pi buni aytmaydi."),
        *royxat(u, [
            "Bu kitob <b>moliyaviy maslahat emas</b>. Unda birorta coin "
            "tavsiya qilinmaydi va \"nima sotib olish kerak\" degan savolga "
            "javob berilmaydi.",
            "Bu kitob <b>foyda kafolatlamaydi</b>. Tushunish — kafolat emas. "
            "Bozorda hech qanday kafolat yo'q.",
            "Bu kitob <b>tayyor tizim bermaydi</b>. U tushunchalarni beradi; "
            "ulardan qanday foydalanish — sizning qaroringiz va sizning "
            "javobgarligingiz.",
        ]),
        p(u, "Agar shu uch gap sizni to'xtatmasa — davom etamiz."),
        h2(u, "Kitob tuzilmasi"),
        p(u, "Kitob olti bo'limdan iborat. Har bo'lim o'z savoliga javob beradi:"),
        *royxat(u, [
            "<b>1-bo'lim — Asoslar.</b> Kripto o'zi nima va u qanday ishlaydi?",
            "<b>2-bo'lim — Fundamental tahlil.</b> Narxni nima harakatlantiradi?",
            "<b>3-bo'lim — Klassik texnik tahlil.</b> Grafikni qanday o'qiladi?",
            "<b>4-bo'lim — Smart Money Concepts.</b> Yirik ishtirokchilar "
            "qanday iz qoldiradi?",
            "<b>5-bo'lim — ICT konsepsiyalari.</b> Vaqt va sessiyalar nima "
            "beradi?",
            "<b>6-bo'lim — Risk menejment.</b> Eng muhim bo'lim: qanday qilib "
            "hamma narsani yo'qotmaslik kerak?",
        ]),
        Spacer(1, 4 * mm),
        p(u, "Oxirgi bo'limni oxirida o'qiysiz, lekin uning ahamiyati birinchi "
             "beshtasidan kam emas. To'g'ri tahlil qilib, noto'g'ri risk bilan "
             "savdo qilgan odam baribir yo'qotadi."),
        PageBreak(),
    ]
