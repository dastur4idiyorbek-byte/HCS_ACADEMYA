# Yangi modulni ishga tushirish — QADAMMA-QADAM

Sana: 2026-09-04

Bu hujjat bitta savolga javob beradi: **Railway'da nima qilishim
kerak?**

---

## 0. ENG MUHIM JAVOB: yangi API KERAK EMAS

Savol: "botga, market'ga API ulagandik — bularga ham ulanadimi?"

**Javob: YO'Q. Yangi modul uchun bironta ham yangi kalit kerak emas.**

Sabab: modul faqat **sham (candle) ma'lumoti** bilan ishlaydi va
Binance uni **kalitsiz, bepul** beradi. Kod tekshirildi —
`core/market_data/binance.py` da `api_key` degan narsa umuman yo'q.

| Nima | Kerakmi | Izoh |
|---|---|---|
| `BOT_TOKEN` | ✅ ALLAQACHON BOR | o'zgarmaydi |
| `ADMIN_IDS` | ✅ ALLAQACHON BOR | o'zgarmaydi |
| `DATABASE_URL` | ✅ ALLAQACHON BOR | o'zgarmaydi |
| Binance kaliti | ❌ KERAK EMAS | ochiq API |
| CoinMarketCap (`CMC_API_KEY`) | ❌ ENDI KERAK EMAS | pastga qarang |

### CoinMarketCap haqida

U eski modulda **reyting** (Top-N coin) va **BTC dominance** uchun
ishlatilardi. Ikkalasi ham eski modul bilan birga ketdi.

Yangi modul coinlarni reytingdan olmaydi — ular `config` dagi
**aniq 12 talik ro'yxat**. Shuning uchun CMC kaliti endi hech
narsaga ta'sir qilmaydi.

O'chirsangiz ham bo'ladi, qoldirsangiz ham — hech nima
o'zgarmaydi. Menimcha **qoldiring**: kelajakda kerak bo'lishi
mumkin va u pul turmaydi.

---

## 1-QADAM: Nusxa oling (backup)

O'chirish QAYTARILMAYDI.

- **Postgres bo'lsa:** Railway panel → Postgres xizmati → `Data`
  → `Backups` → nusxa oling.
- **SQLite + volume bo'lsa:** volume'dagi `hcs.db` faylini
  yuklab oling.

Bu qadamni o'tkazib yubormang.

---

## 2-QADAM: Yangi kodni Railway'ga chiqaring

`claude/assalomu-alaykum-hncsjy` shoxidagi kod Railway'ga
tushishi kerak (odatda `main` ga birlashtirish orqali).

Deploy tugagach bot qayta ko'tariladi.

---

## 3-QADAM: "Modul yoqildi" xabarini KUTING

Bot ko'tarilgandan ~3 daqiqa keyin Telegramda **sizga** xabar
keladi:

    🤖 Zanjir moduli ishga tushdi
    Har 4 soatda tekshiradi
    Kuzatilayotgan coinlar: 12 ta
    BTC, ETH, SOL, ADA, AVAX, LINK, DOT, ATOM, LTC, NEAR, ETC, FIL

**Bu xabar kelmasa — modul ishlamayapti.** Loglarda qidiring:

    "Zanjir sikli O'CHIQ"   -> sham provayderi ulanmagan

---

## 4-QADAM: Eski ma'lumotni o'chiring — BOTDAN

Railway'da CLI, SSH yoki start-buyruqni o'zgartirish **kerak
emas**. Bot allaqachon o'sha bazaga ulangan.

Telegramda, admin hisobingizdan:

**a) Avval KO'RING (hech narsa o'chmaydi):**

    /eski_tozalash

Javob shunday bo'ladi:

    Eski modul qoldirgan ma'lumot:
    signals                 5 — ESKI MODUL BERGAN SIGNALLAR
    risk_blocks          1693 — Risk Engine rad etishlari
    ...
    JAMI: 1711 qator
    ⚠️ Hech narsa o'chirilmadi.

**b) Ro'yxatni tekshiring.** Raqamlar mantiqiymi? Kutilmagan
katta son yo'qmi?

**c) Rozi bo'lsangiz — o'chiring:**

    /eski_tozalash tasdiqla

### Nima o'chadi va nima QOLADI

| O'chadi | Qoladi |
|---|---|
| eski signallar | foydalanuvchilar |
| signal hodisalari | obunalar |
| foydalanuvchi pozitsiyalari | to'lovlar va cheklar |
| Risk Engine rad etishlari | halol/harom hukmlar |
| kunlik statistika | kontent, darsliklar |
| Bozor Salomatligi jurnali | narxlar, sozlamalar |
| audit hisobotlari | sayt bozor ko'rinishi |

Bu ro'yxat test bilan qulflangan: foydalanuvchi yoki to'lov
jadvali o'chirish ro'yxatiga tushsa, testlar yiqiladi.

---

## 5-QADAM: Tekshiring

O'chirgandan keyin sayt va botdagi statistika **bo'sh** ko'rsatadi.
Bu — TO'G'RI holat: yangi modul hali jonli signal bermagan.

---

## 6-QADAM: Endi kuting

Birinchi signalgacha vaqt ketishi mumkin. Backtestda modul 12
coinda **oyiga ~10 signal** bergan. Ya'ni bir necha kun jim
turishi butunlay normal.

Signal kelganda ikkita narsa bo'ladi:

1. Sizga xabar: `🤖 Zanjir moduli 1 ta signal topdi — SOL`
2. Signal kartochkasining oxirida yorliq:

       🤖 Zanjir moduli (avtomatik)

**Yorliqqa qarang:**

| Yorliq | Ma'nosi |
|---|---|
| 🤖 Zanjir moduli | yangi modul — o'lchangan |
| ✍️ Qo'lda kiritilgan | siz yozgansiz |
| 🕰 Eski modul | eski ma'lumot — ishonmang |
| yorliq yo'q | eski kod bilan yuborilgan |

---

## Nima HALI YO'Q — bilib turing

| Yo'q | Oqibati |
|---|---|
| Avtomatik TP/Stop kuzatuvi | signal yopilishini QO'LDA belgilaysiz |
| Fundamental blok manbalari | blok "o'lchanmadi" holatida, zanjirni uzmaydi |
| Pul taqsimoti tuzatilishi | hisob simulyatsiyasi −68% bergan (alohida ish) |

Oxirgisi eng muhimi: **signal sifati yaxshi, pul taqsimoti
buzuq** (`BACKTEST_NATIJA_2026-09-04_hisob.md`). Shuning uchun
signal kartochkasidagi "Miqdor" raqamiga hozircha
tayanmang — u alohida hal qilinadi.
