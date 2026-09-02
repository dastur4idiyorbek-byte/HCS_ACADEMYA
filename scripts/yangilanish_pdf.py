"""Yangilanish hisoboti PDF: "Nima qo'shildi, nima olib tashlandi".

`scripts/qollanma_pdf.py` — tizim QANDAY ISHLASHI haqida. Bu hujjat
esa undan KEYIN qilingan ishlarni yig'adi: yangi modul, olib
tashlangan qismlar va topilgan xatolar.

Nima uchun ikkita hujjat: qo'llanma yangi odamga tizimni tushuntiradi
va u barqaror bo'lishi kerak. Yangilanish esa vaqtga bog'liq — uni
qo'llanma ichiga aralashtirsak, ikkalasi ham o'qilmaydigan bo'lardi.

CHIZISH USULLARI QAYTA YOZILMAYDI: sarlavha, jadval, eslatma —
hammasi `qollanma_pdf` dan olinadi. Ikki nusxa bo'lsa, dizayn bir
kuni ikkiga bo'linib ketardi.

RAQAMLAR KONFIGURATSIYADAN o'qiladi (`config/default.yaml`), qo'lda
yozilmaydi: sozlama o'zgargach hujjat eskirib qolmasin.

Ishga tushirish:
    python -m scripts.yangilanish_pdf

Chiqish: `docs/HALOL_CRYPTO_SAVDO_yangilanish.pdf`
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

from core.config import load_config
from scripts.qollanma_pdf import (
    APELSIN,
    BALAND,
    EN,
    KOK_TOQ,
    LOGO,
    MATN_PAST,
    ODDIY,
    QALIN,
    QIZIL,
    SARIQ,
    TURKUAZ,
    Sahifa,
    eslatma,
    jadval,
    qadam,
    shriftlar,
)

ILDIZ = Path(__file__).resolve().parent.parent
CHIQISH = ILDIZ / "docs" / "HALOL_CRYPTO_SAVDO_yangilanish.pdf"

BOLIMLAR = [
    "1.  Bir qarashda",
    "2.  Nima olib tashlandi",
    "3.  Nima qo'shildi",
    "4.  Signal chiqqandan keyin",
    "5.  Sinov davri va topilgan xatolar",
]


# --------------------------------------------------------------------------- #
#  Muqova
# --------------------------------------------------------------------------- #


def muqova(c: pdfcanvas.Canvas) -> None:
    c.setFillColor(KOK_TOQ)
    c.rect(0, 0, EN, BALAND, stroke=0, fill=1)

    c.setFillColor(TURKUAZ)
    c.roundRect(EN - 96, BALAND - 96, 150, 150, 34, stroke=0, fill=1)
    c.setFillColor(APELSIN)
    c.roundRect(-54, -54, 150, 150, 34, stroke=0, fill=1)

    olcham = 120
    ramka = olcham + 22
    c.setFillColor(HexColor("#ffffff"))
    c.roundRect((EN - ramka) / 2, BALAND - 300, ramka, ramka, 26, stroke=0, fill=1)
    c.drawImage(
        ImageReader(str(LOGO)),
        (EN - olcham) / 2,
        BALAND - 289,
        width=olcham,
        height=olcham,
        mask="auto",
    )

    c.setFont(QALIN, 26)
    c.setFillColor(HexColor("#ffffff"))
    c.drawCentredString(EN / 2, BALAND - 352, "HALOL CRYPTO SAVDO")

    c.setStrokeColor(APELSIN)
    c.setLineWidth(2.6)
    c.line(EN / 2 - 46, BALAND - 372, EN / 2 + 46, BALAND - 372)

    c.setFont(ODDIY, 16)
    c.setFillColor(TURKUAZ)
    c.drawCentredString(EN / 2, BALAND - 404, "Yangilanish hisoboti")

    c.setFont(ODDIY, 11)
    c.setFillColor(HexColor("#9ab0d2"))
    for i, qator in enumerate(
        [
            "Nima qo'shildi, nima olib tashlandi va nima uchun.",
            "Qo'llanmadan keyin qilingan barcha o'zgarishlar.",
        ]
    ):
        c.drawCentredString(EN / 2, BALAND - 434 - i * 18, qator)

    c.setFont(ODDIY, 10)
    for i, qator in enumerate(BOLIMLAR):
        y = BALAND - 520 - i * 22
        c.setFillColor(APELSIN)
        c.circle(EN / 2 - 106, y + 3.5, 3, stroke=0, fill=1)
        c.setFillColor(HexColor("#c7d4ea"))
        c.drawString(EN / 2 - 92, y, qator)

    c.setFont(ODDIY, 9)
    c.setFillColor(HexColor("#6b83a8"))
    c.drawCentredString(
        EN / 2, 84, datetime.now(UTC).strftime("%d.%m.%Y") + " · ichki hujjat"
    )
    c.drawCentredString(EN / 2, 68, "Spot savdo · leverage yo'q · qarz yo'q")


# --------------------------------------------------------------------------- #
#  Sahifalar
# --------------------------------------------------------------------------- #


def sahifa_qisqacha(s: Sahifa) -> None:
    s.yangi("1. Bir qarashda")
    s.matn(
        "Uch yo'nalishda ish qilindi: tahlilga yangi qatlam qo'shildi, "
        "takrorlanayotgan qismlar olib tashlandi va signal chiqqandan "
        "keyingi qoidalar aniqlashtirildi. Har birining sababi keyingi "
        "sahifalarda.",
        rang=MATN_PAST,
    )
    s.bosh(6)

    jadval(
        s,
        ["Yo'nalish", "Nima o'zgardi"],
        [
            ["Qo'shildi", "CryptoSpot3% qatlami: struktura, daraja turi, yalash, sessiya, davr"],
            ["Qo'shildi", "Jonli Oshxona - admin uchun real vaqtli tahlil monitori"],
            ["Qo'shildi", "TP1 dan keyin Stop kirish narxiga ko'tariladi"],
            ["Qo'shildi", "Kech kirish ogohlantirishi va \"faol emas\" yorlig'i"],
            ["Olib tashlandi", "EMA indikatori - strukturani takrorlardi"],
            ["Olib tashlandi", "Trend kengligi omili - struktura kengligi bilan bir xil savol"],
            ["Vaqtincha", "Foydalanuvchi sig'imi omili va uch tormoz - sinov davrida"],
            ["Tuzatildi", "Natija hisobi, ball darvozasi, daraja turi, monitor zanjiri"],
        ],
        [104, 343],
        ranglar=[TURKUAZ, TURKUAZ, TURKUAZ, TURKUAZ, QIZIL, QIZIL, SARIQ, APELSIN],
    )

    eslatma(
        s,
        "Asosiy tamoyil o'zgarmadi: yangi omillar QAT'IY FILTR sifatida "
        "qo'shilmadi. Har biri ball ichiga kiradi, qarorni esa bitta "
        "umumiy ball chegarasi qabul qiladi. Sabab oddiy: har bir yangi "
        '"shart ham bajarilsin" talabi signal sonini nolga yaqinlashtiradi.',
    )


def sahifa_olib_tashlandi(s: Sahifa) -> None:
    s.yangi("2. Nima olib tashlandi")
    s.matn(
        "Olib tashlash - qo'shishdan qiyinroq qaror. Mezon bitta bo'ldi: "
        "qism BOSHQASI BILAN BIR XIL savolga javob berayaptimi. Bir xil "
        "savolga ikki javob tizimni kuchaytirmaydi - u shunchaki bitta "
        "fikrni ikki marta sanaydi.",
        rang=MATN_PAST,
    )
    s.bosh(4)

    qadam(
        s,
        1,
        "EMA INDIKATORI",
        "EMA \"narx o'rtachadan balandmi\" degan savolga javob berardi. "
        "SMC strukturasi esa aynan shu savolga to'g'ridan-to'g'ri javob "
        "beradi: cho'qqilar va chuqurliklar ko'tarilyaptimi. Struktura "
        "kechikmaydi, EMA esa kechikadi - ya'ni ikkinchisi birinchisining "
        "sekinroq nusxasi edi.",
        QIZIL,
    )
    qadam(
        s,
        2,
        "TREND KENGLIGI OMILI",
        "Bozor Salomatligida ikkita kenglik omili bor edi: biri EMA "
        "bo'yicha, ikkinchisi struktura bo'yicha. Ikkalasi ham \"ro'yxatda "
        "nechta coin ko'tarilishda\" degan bitta savolni o'lchardi. "
        "Bittasi qoldi va uning vazni oshirildi.",
        QIZIL,
    )
    qadam(
        s,
        3,
        "200 SHAMLIK TALAB",
        "Tahlil uchun kamida 200 ta sham talab qilinardi - bu EMA200 "
        "uchun kerak edi. EMA ketgach talab ham ma'nosini yo'qotdi: "
        "haftalik grafikda 200 sham ~4 yil tarix degani va ko'p coin "
        "jimgina chetlab o'tilardi.",
        QIZIL,
    )

    s.sarlavhacha("Vaqtincha chetga chiqarilganlar")
    s.matn(
        "Bular O'CHIRILMADI - sinov davriga (100 kun) qo'yildi va muddat "
        "tugagach o'zi qaytadi. Ularning umumiy jihati: bozorni emas, "
        "BIZNING holatimizni o'lchaydi.",
        rang=MATN_PAST,
    )
    jadval(
        s,
        ["Nima", "Nimani o'lchaydi", "Nega sinovda kerak emas"],
        [
            ["Foydalanuvchi sig'imi", "Obunachilar balansi", "Sinovda obunachi kam"],
            ["Kunlik zarar chegarasi", "Bugungi zararimiz", "Namunani yarim qoldiradi"],
            ["Ochiq signal limiti", "Nechta signalimiz bor", "Signal sonini cheklaydi"],
            ["Ketma-ket zarar pauzasi", "Ketma-ket Stoplar", "Tizimni o'chirib qo'yadi"],
        ],
        [126, 132, 189],
    )


def sahifa_qoshildi(s: Sahifa, konfig) -> None:  # noqa: ANN001
    s.yangi("3. Nima qo'shildi")
    s.matn(
        "Yangi qatlam - CryptoSpot3% metodikasi. U eski modulni "
        "almashtirmadi: ikkalasi ARALASHIB ishlaydi. Yangi dalillar "
        "eski omillarning ICHIGA qo'shiladi, ya'ni ball chegarasi bitta "
        "raqamni o'qiydi va u raqamda ikkala modul ham bor.",
        rang=MATN_PAST,
    )
    s.bosh(4)

    jadval(
        s,
        ["Qatlam", "Nima qiladi"],
        [
            ["Struktura (SMC)", "Cho'qqi/chuqurlik ketma-ketligi: ko'tarilishmi yoki pasayish"],
            ["Daraja turi", "Zona shunchaki chiziqmi yoki kuchli daraja (RBS, SBR, OB)"],
            ["Yalash (LIT)", "Narx darajani yalab o'tib qaytdimi - kuchli kirish belgisi"],
            ["Sessiya (ICT)", "London/Nyu-York kesishuvi - harakat eng faol payt"],
            ["Davr (QT/AMDX)", "Sutkaning qaysi davri: yig'ish, manipulyatsiya, harakat"],
        ],
        [116, 331],
    )

    v = konfig.market_health.weights
    s.sarlavhacha("Bozor Salomatligining yangi vaznlari")
    jadval(
        s,
        ["Omil", "Vazn", "Izoh"],
        [
            [
                "Struktura kengligi",
                f"{v.halal_structure_breadth:.0f}",
                "ASOSIY: nechta coin HH/HL da",
            ],
            ["Volatillik rejimi", f"{v.volatility_regime:.0f}", "Bozorda trend bormi (ADX)"],
            [
                "Foydalanuvchi sig'imi",
                f"{v.aggregate_user_capacity:.0f}",
                "Sinov davrida hisobga olinmaydi",
            ],
            ["Signal to'yinganligi", f"{v.signal_saturation:.0f}", "Ochiq signallar soni"],
            ["BTC dominatsiyasi", f"{v.btc_dominance_stability:.0f}", "Faqat qo'shimcha kontekst"],
            ["QT davri", f"{v.quarterly_phase:.0f}", "Boshlang'ich vazn"],
        ],
        [140, 44, 263],
    )

    eslatma(
        s,
        f"BTC dominatsiyasi 20 dan {v.btc_dominance_stability:.0f} ga tushirildi. "
        "Sabab: u foydali kontekst beradi, lekin qaror mezoni emas. Uning "
        f"o'rniga asosiy omil - halol ro'yxatning struktura holati "
        f"({v.halal_structure_breadth:.0f} vazn), ya'ni real narx harakati.",
        rang=TURKUAZ,
    )


def sahifa_signal_keyin(s: Sahifa, konfig) -> None:  # noqa: ANN001
    s.yangi("4. Signal chiqqandan keyin")
    s.matn(
        "Ilgari signal chiqqach tizim faqat kuzatardi. Endi ikkita "
        "qoida qo'shildi - ular signalga ALLAQACHON KIRGAN va HALI "
        "KIRMAGAN foydalanuvchini ajratadi.",
        rang=MATN_PAST,
    )
    s.bosh(4)

    ulush = konfig.portfolio.tp1_close_pct
    qadam(
        s,
        1,
        "TP1 OLINDI - STOP KIRISH NARXIGA",
        f"TP1 da pozitsiyaning {ulush:.0f}% i sotiladi va foyda qo'lda "
        "qoladi. Qolgan qismni eski Stopda ushlab turish o'sha foydani "
        "qaytarib berish xavfini saqlaydi. Endi Stop kirish narxiga "
        "ko'tariladi: eng yomon holat - nolga chiqish. Signal TP1 da "
        "yopilmaydi, to'liq TP gacha davom etadi.",
        TURKUAZ,
    )
    qadam(
        s,
        2,
        f"NARX {konfig.trade_rules.late_entry_warn_pct}% YURSA - OGOHLANTIRISH",
        "Signal berilgan paytdagi Stop va TP nisbati - signalning butun "
        "asosi. Narx kirish nuqtasidan uzoqlashgach o'sha nisbat "
        "buziladi. Shuning uchun hali kirmagan foydalanuvchiga xavf "
        "kattalashgani aytiladi va kirish tavsiya etilmaydi. Ikkala "
        "tomonga ham: yuqoriga ketsa TP gacha masofa qisqargan, pastga "
        "ketsa Stop yaqinlashgan.",
        SARIQ,
    )

    s.sarlavhacha("Kalkulyator ham shunga moslandi")
    s.matn(
        "Olingan TP kalkulyatordan O'CHIRILMAYDI - u bashorat emas, "
        "amalga oshgan savdo. O'chirilsa, kalkulyator o'sha pulni "
        "yo'qotib \"hech narsa yo'q\" degan yolg'on manzara ko'rsatardi. "
        "Uning o'rniga TP olingan deb belgilanadi va uchta yangi qator "
        "chiqadi.",
        rang=MATN_PAST,
    )
    jadval(
        s,
        ["Qator", "Nimani ko'rsatadi"],
        [
            ["Qo'lda", "Olingan TP dan qo'lga kirgan foyda - FAKT"],
            ["Kutilmoqda", "Qolgan TP lardan kutilayotgan foyda"],
            ["Eng yomon holat", "Qo'lda minus qolgan qismning zarari"],
        ],
        [120, 327],
    )
    eslatma(
        s,
        "Stop endi FAQAT qolgan qismga hisoblanadi. Ilgari pozitsiyaning "
        "yarmi sotilgan bo'lsa ham \"Stop bo'lsa\" qatori to'liq summadan "
        "hisoblanardi - ya'ni mavjud bo'lmagan zarar ko'rsatilardi.",
        rang=QIZIL,
    )


def sahifa_sinov(s: Sahifa, konfig) -> None:  # noqa: ANN001
    sinov = konfig.sinov
    s.yangi("5. Sinov davri va topilgan xatolar")
    s.matn(
        f"{sinov.days} kun davomida tizim FAQAT BOZORGA qarab qaror "
        "qiladi. Bizning holatimiz - nechta obunachimiz bor, bugun "
        "qancha zarar ko'rdik, nechta signalimiz ochiq - natijaga "
        "aralashmaydi. Sabab halollik talabi: ommaga ko'rsatiladigan "
        "natijaga bizning ichki holatimiz qo'shilmasin.",
        rang=MATN_PAST,
    )

    s.sarlavhacha("Sinovda ham to'xtatilmaydi")
    s.matn(
        "Sinov \"hamma narsani o'chirish\" emas. Bozor filtrlari (Bozor "
        "Salomatligi, BTC filtri, volatillik, narx yangiligi), diniy "
        "qoidalar (halol ro'yxat, juma namozi), favqulodda to'xtash va "
        "har bir signalning o'z Stop/TP qoidalari - hammasi o'z kuchida. "
        "Signal SIFATI o'zgarmaydi.",
        rang=MATN_PAST,
    )

    s.sarlavhacha("Yo'l-yo'lakay topilgan xatolar")
    jadval(
        s,
        ["Xato", "Ta'siri"],
        [
            ["Natija TP1 ni sanamasdi", "Foydali savdo \"0%\" deb yozilardi"],
            ["Ball darvozasi bonus bilan", "Chegaradan 80% nomzod o'tib ketardi"],
            ["Barcha zona bir turda", "Daraja turi hech narsani ajratmasdi"],
            ["Monitor zanjiri noto'g'ri", "Bajarilmagan bosqich \"o'tdi\" ko'rinardi"],
            ["Sahifa TP1 dan keyin yopiq", "Kirgan odam signalini ko'ra olmasdi"],
            ["Stop butun pozitsiyaga", "Mavjud bo'lmagan zarar ko'rsatilardi"],
        ],
        [176, 271],
    )

    eslatma(
        s,
        "Bu xatolarning ko'pi YANGI qism qo'shilayotganda topildi: yangi "
        "o'lchov eskisining ustiga tushganda, mos kelmagan raqam darhol "
        "ko'zga tashlandi. Har biri uchun test yozildi - shuning uchun "
        "ular qaytib kelmaydi.",
        rang=TURKUAZ,
    )

    s.bosh(4)
    eslatma(
        s,
        "Tizim hech qachon \"shuncha oling\" demaydi. Barcha raqamlar - "
        "hisob-kitob va tavsiya. Qaror foydalanuvchiniki, mas'uliyat ham "
        "foydalanuvchiniki. Bu moliyaviy maslahat emas.",
        rang=QIZIL,
    )


def main() -> None:
    konfig = load_config()
    shriftlar()
    CHIQISH.parent.mkdir(parents=True, exist_ok=True)
    c = pdfcanvas.Canvas(str(CHIQISH), pagesize=A4)
    c.setTitle("HALOL CRYPTO SAVDO - Yangilanish hisoboti")
    c.setAuthor("HALOL CRYPTO SAVDO")

    muqova(c)
    c.showPage()
    s = Sahifa(c, quyi_sarlavha="Yangilanish hisoboti")
    sahifa_qisqacha(s)
    sahifa_olib_tashlandi(s)
    sahifa_qoshildi(s, konfig)
    sahifa_signal_keyin(s, konfig)
    sahifa_sinov(s, konfig)

    c.showPage()
    c.save()
    print(f"Tayyor: {CHIQISH}")


if __name__ == "__main__":
    main()
