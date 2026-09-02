# Backtest natijasi #3 — kirish sifati filtrlari

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun | 4 380 qadam
**Kod:** `a990f72` | GitHub Actions run #6

---

## Jadval

| variant | signal | savdo | win | TP2 gacha | **o'rt.%** | jami% | pasayish |
|---|---|---|---|---|---|---|---|
| hozirgi holat | 667 | 649 | 37.9% | 29.9% | **-0.73** | -471.6 | 547.6% |
| kunlik trend majburiy | 454 | 431 | 37.8% | 28.1% | **-0.65** | -280.2 | 335.3% |
| indikator tasdig'i majburiy | 635 | 616 | 37.3% | 30.0% | **-0.72** | -446.6 | 523.3% |
| faqat kuchli trend (ADX 25) | 540 | 525 | 37.5% | 29.1% | **-0.74** | -386.1 | 464.4% |
| faqat chuqur Discount (40%) | 633 | 610 | 38.0% | 28.9% | **-0.73** | -443.6 | 527.0% |

---

## 1. "Yaxshilanish" — bu yaxshilanish emas

Birinchi qarashda `kunlik trend majburiy` g'olib: jami natija
-471.6% dan -280.2% ga ko'tarildi, pasayish 547% dan 335% ga
tushdi.

**Lekin bu savdolar yaxshilanganidan emas.** Ular KAMAYGANIDAN:

    649 savdo x -0.73%  =  -474%
    431 savdo x -0.65%  =  -280%

Bitta savdodagi natija -0.73% dan -0.65% ga o'zgardi — atigi 0.08
punkt. Qolgan butun "yutuq" shunchaki zarar keltiruvchi ishni
KAMROQ qilishdan chiqdi.

Zarar keltiruvchi strategiyani kamroq bajarish — tuzatish emas.
Uni umuman bajarmaslik ham "yaxshilaydi": 0 savdo = 0% zarar.

## 2. Asosiy topilma: filtrlar yaxshi va yomon savdoni AJRATMAYDI

Eng muhim ustun — **win-rate**:

    hozirgi holat                37.9%
    kunlik trend majburiy        37.8%
    indikator tasdig'i majburiy  37.3%
    faqat kuchli trend (ADX 25)  37.5%
    faqat chuqur Discount        38.0%

To'rtta mustaqil filtr qo'llandi. Signal soni 454 dan 667 gacha
o'zgardi. **Win-rate esa qimirlamadi.**

TP2 gacha yetish ham xuddi shunday: 28.1% – 30.0%.

Bu shuni anglatadi:

> Filtrlar signallarni KAMAYTIRADI, lekin yaxshisini yomonidan
> ajrata olmaydi. Ular tasodifiy ravishda kesib tashlaydi.

Agar filtr haqiqatan sifatni oshirsa, o'chirilgan savdolar
o'rtachadan YOMONROQ bo'lishi va win-rate ko'tarilishi kerak edi.
Bo'lmadi.

## 3. Nima kerakligi hisoblab chiqildi

Hozirgi natijalar bilan:

    TP2 (1.5R) yetadi:        29.9%
    TP1 keyin breakeven:       8.0%
    to'g'ri stop:             62.1%

    kutilma = 0.299 x 1.5 + 0.080 x 0.375 - 0.621 = -0.14R

Nolga chiqish uchun TP2 gacha yetish **~35.6%** bo'lishi kerak.
Hozir 29.9%. Farq — 6 punkt.

To'rtta filtrning eng yaxshisi 30.0% berdi. Ya'ni **hech biri bu
farqni yopishga yaqin ham kelmadi.**

## 4. Uchta gipoteza rad etildi

| # | Gipoteza | Natija |
|---|---|---|
| 1 | Correction Entry past bandda yordam beradi | ❌ 4 ta signal, natija yomonlashdi |
| 2 | Tuzilmaviy TP2 ehtimolni oshiradi | ❌ 29.9% -> 24.7%, teskari |
| 3 | Kirish filtrlari sifatni oshiradi | ❌ win-rate qimirlamadi |

Uchalasi ham sozlama darajasidagi tuzatish edi. Uchalasi ham
ishlamadi.

## 5. Javob berilmagan ASOSIY savol

Hali biror narsa yetishmayapti: **taqqoslash uchun tayanch yo'q.**

-0.73% har savdoda — bu yomonmi? Nimaga nisbatan?

- Agar shu davrda coinlar o'sgan bo'lsa va oddiy "olib ushlab
  turish" foyda bergan bo'lsa — strategiya zarar keltiribgina
  qolmay, hech narsa qilmaslikdan ham yomon
- Agar coinlar tushgan bo'lsa — raqam boshqacha o'qiladi

Bu tayanchsiz "yomon" degan so'zning o'lchovi yo'q. Keyingi qadam
— hisobotga **"olib ushlab turish" (buy & hold)** taqqoslamasi
qo'shish.

Bu birinchi navbatdagi ish, chunki u savolni o'zgartirishi mumkin:
"strategiyani qanday tuzatamiz" emas, "bu strategiya umuman
kerakmi".
