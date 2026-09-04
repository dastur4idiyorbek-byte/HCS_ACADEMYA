# TP oralig'i o'lchovi — yaqin darajalar birlashtirilgandan keyin

**Sana:** 2026-09-04
**Sabab:** jonli signalda TP2 = 54.70, TP3 = 54.78 chiqdi — orasi 0.16%.
**O'zgarish:** `darajalar.tp_eng_kam_oraliq_pct = 1.0`

Actions: [run #20](https://github.com/dastur4idiyorbek-byte/HCS_ACADEMYA/actions/runs/33890762496)
4 yil (1460 kun), 12 halol coin, offline kesh.

---

## Solishtirish

| | savdo | foydali | **PF** | o'rt.% | jami% | pasayish |
|---|---|---|---|---|---|---|
| **Oldin** (birlashtirishsiz) | 498 | 68% | **3.49** | — | — | — |
| **Keyin** (1.0% oraliq) | 486 | 67.9% | **3.56** | 3.04 | 1479.0 | 36.5% |

**PF pasaymadi: 3.49 → 3.56.**

Farq kichik va shovqin doirasida. Muhimi shu: o'zgarish natijani
BUZMADI. Uning asosiy foydasi backtestda emas — u yerda 0.16% masofadagi
ikki TP deyarli bir vaqtda uriladi, ya'ni farq ko'rinmaydi.

## Nima uchun baribir kerak

Foyda JONLI savdoda:

1. **Xarajat.** Ikkinchi TP ikkinchi sotuv degani: 0.1% komissiya +
   0.05% sirg'anish. 0.16% lik farqda bu — foydaning katta qismi.
   Backtest buni o'lchaydi, lekin ta'siri kichik bo'lgani uchun
   umumiy raqamda ko'rinmaydi.

2. **Ekranning rostligi.** Foydalanuvchi TP2 = 54.70 va TP3 = 54.78
   ni ko'rib "nega ikkita?" deb so'raydi. Javob yo'q edi, chunki
   javob "bu aslida bitta daraja".

## Boshqa konfiguratsiyalar (o'sha yugurishdan)

| konfiguratsiya | savdo | foydali | PF | jami% |
|---|---|---|---|---|
| to'liq zanjir (4 blok) | 486 | 67.9% | 3.56 | 1479.0 |
| 11 bo'sh tekshiruvsiz | 361 | 62.3% | 2.90 | 993.8 |
| tasdiqlashsiz (3 blok) | 703 | 70.7% | 4.80 | 2753.2 |
| faqat fundamental+struktura | 703 | 70.7% | 4.80 | 2753.2 |
| zanjirsiz — faqat darajalar | 903 | 62.6% | 3.35 | 2650.4 |

⚠️ "Tasdiqlashsiz" qatoridagi PF 4.80 — bu ABLATSIYA natijasi, tavsiya
emas. Uning pasayishi ham kattaroq (42.6% vs 36.5%) va u ALOHIDA
walk-forward talab qiladi. Bu yerda faqat TP oralig'i o'lchandi.

## Holat

`tp_eng_kam_oraliq_pct` gipoteza daftarida 🟡 — **o'lchandi, lekin
1.0 aynan to'g'ri qiymat ekani isbotlanmagan.** 0.5 va 2.0 sinalmadi.
Hozircha 1.0 qoladi: u xarajatdan (0.15%) sezilarli katta va
ekrandagi takrorlanishni yo'q qiladi.
