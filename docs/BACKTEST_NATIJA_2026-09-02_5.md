# Backtest natijasi #5 — ADX to'g'rilangandan keyin

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun | 4 380 qadam
**Kod:** `07c2147` | GitHub Actions run #8

> **Bu natija #3 va #4 bilan SOLISHTIRILMAYDI.** `07c2147` da backtest
> ADX ni noto'g'ri timeframe'dan o'qiyotgani tuzatildi (4 soatlik
> o'rniga haftalik). Ya'ni oldingi yugurishlar boshqa indeks bilan,
> boshqa rejimda ishlagan. Quyidagi jadval nolinchi nuqta — bundan
> keyingi taqqoslashlar shu bilan qilinadi.

---

## Jadval

| variant | signal | savdo | win | TP2 gacha | **o'rt.%** | jami% | pasayish |
|---|---|---|---|---|---|---|---|
| hozirgi holat | 389 | 380 | 32.1% | 26.1% | **-1.04** | -394.5 | 406.8% |
| kunlik trend majburiy | 261 | 247 | 30.8% | 24.3% | **-0.95** | -235.4 | 238.2% |
| indikator tasdig'i majburiy | 371 | 361 | 32.4% | 26.3% | **-0.99** | -357.4 | 369.7% |
| faqat kuchli trend (ADX 25) | 354 | 346 | 33.5% | 26.3% | **-0.95** | -330.3 | 335.8% |
| faqat chuqur Discount (40%) | 370 | 357 | 32.2% | 24.9% | **-1.05** | -376.4 | 388.7% |

```
Tayanch — olib ushlab turish: +33.0%
⚠️ Strategiya HECH NARSA QILMASLIKDAN yomon ishlagan.   (beshta variantda ham)
```

---

## To'g'rilash natijani YOMONLASHTIRDI

Bu kutilmagan yo'nalish, shuning uchun alohida yoziladi.

| | run #7 (noto'g'ri ADX) | run #8 (to'g'ri ADX) |
|---|---|---|
| Signal (hozirgi holat) | 667 | **389** |
| Win-rate | 37.9% | **32.1%** |
| TP2 gacha | 29.9% | **26.1%** |
| O'rtacha savdo | -0.73% | **-1.04%** |

Ya'ni run #3 va #4 dagi "37-38% win-rate" raqami tizimning haqiqiy
ko'rsatkichi emas edi — u xato hisoblangan indeks ostida olingan.
Haqiqiy raqam pastroq.

**Nima uchun bu MUHIM:** xato topilganda odatda "endi yaxshilanadi"
deb kutiladi. Bu safar teskarisi bo'ldi. Agar tuzatish qilinmaganda,
tizim o'zi haqida yaxshiroq fikrda qolgan bo'lardi va qarorlar
o'sha yolg'on raqam ustiga qurilgan bo'lardi.

---

## Ikki barrer testi — endi yanada aniqroq

Tasodifiy kirish, stop S va nishon 1.5S bo'lsa, nishonga yetish
ehtimoli:

```
S / (S + 1.5S) = 40%
```

| | qiymat |
|---|---|
| Tasodifiy kirish beradi | 40% |
| Tizim beradi (run #7) | 29.9% |
| Tizim beradi (run #8) | **26.1%** |

Tizim tasodifiy kirishdan **1.5 barobar yomonroq**. Bu "biroz
sozlash kerak" degan farq emas.

---

## Yangi ma'lumot: indeks doim PAST

Jurnal butun sinov davomida bir xil ikki satrni takrorlaydi:

```
Bozor Salomatligi: 26.5/100 (low)
Sikl to'xtatildi: Bozor Salomatligi past (27/100), lekin
                  korreksiya strategiyasi o'chirilgan
```

To'g'ri (haftalik) ADX bilan indeks 26-32 bandida qotib qoldi.
Rad etish sabablari ro'yxatida `market_health` 1 922 marta.

Bu ikkita mumkin bo'lgan ma'noning biri:

1. Bozor haqiqatan ikki yil davomida "kasal" bo'lgan — lekin
   tayanch **+33.0%** deydi, ya'ni bozor ko'tarilgan. Bu ma'no
   ma'lumotga zid.
2. **Indeks kalibrlanmagan.** Vaznlar, chegaralar va omillar
   birortasi o'lchanmagan (`GIPOTEZA_DAFTARI.md`: 🔴 barchasi).
   Indeks ko'tarilgan bozorni "past" deb o'qiydi.

Ikkinchisi ancha ehtimolliroq. Ya'ni tizimning **markaziy puls**i
noto'g'ri joyda turibdi: u savdoni ko'tarilish davrida to'xtatadi.

Bu — keyingi o'lchanadigan gipoteza. Uni oldingi uchtasidan farqi
bor: oldingilar "signal sifatini oshiramiz" haqida edi, bu esa
"tizim umuman qachon ishlaydi" haqida.

---

## Xulosa o'zgarmadi, faqat qattiqroq bo'ldi

Uchta gipoteza (Correction Entry, tuzilmaviy TP2, kirish filtrlari)
rad etilgan edi. To'rtinchi ma'lumot ularni tasdiqlaydi:

- filtrlar win-rate ni 30.8-33.5% oralig'ida qoldiradi — hech biri
  kirish sifatini ajrata olmaydi;
- "kunlik trend majburiy" yana eng yaxshi ko'rinadi, sababi yana
  o'sha: **kamroq savdo**, bitta savdodagi farq atigi 0.09 punkt;
- beshta variantda ham tayanchdan yomon.

Tuzatiladigan narsa kirish filtrida emas. Kirishning O'ZIDA.
