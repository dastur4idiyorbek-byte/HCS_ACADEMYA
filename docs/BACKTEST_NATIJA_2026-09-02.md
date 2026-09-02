# Backtest natijasi — 2026-09-02

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun | 4 380 qadam
**Manba:** Binance (data-api.binance.vision), GitHub Actions run #4
**Kod:** `afc2da9`

Bu hujjat NATIJANI o'zgartirmasdan yozib qo'yadi. Raqamlar yoqmasa ham
qoladi — 6.3-bandning butun ma'nosi shunda.

---

## Taqqoslash jadvali

```
konfiguratsiya              signal  savdo     win   o'rt.%    jami%  pasayish
-----------------------------------------------------------------------------
eski: past bandda to'xtash     667    649     38%    -0.43   -276.9    362.2%
yangi: Correction Entry        671    653     38%    -0.45   -293.7    379.0%
CE: confluence 3               667    649     38%    -0.43   -276.9    362.2%
CE: R/R 1.5                    671    653     38%    -0.45   -293.7    379.0%
CE: R/R 2.5                    671    653     38%    -0.45   -293.7    379.0%
```

---

## 1. Asosiy xulosa: Correction Entry YOQILMAYDI

Brief so'ragan savolga javob: **yo'q**.

- Qo'shgan signali: 667 -> 671, ya'ni **4 ta** (0.6%)
- O'sha 4 ta savdo natijani yaxshilamadi, **yomonlashtirdi**:
  -276.9% -> -293.7%
- Pasayish ham chuqurlashdi: 362% -> 379%

`config/default.yaml` da `correction_entry.enabled` **`false` bo'lib
qoladi**.

**Nima uchun deyarli ishlamadi.** Eng ko'p rad etish sababi —
`correction_entry:trend` (13 462 marta). Bu qat'iy darvoza: kunlik
trend ko'tarilishda bo'lishi SHART. Bozor Salomatligi past bo'lgan
paytda esa kunlik trend odatda pastga qaragan bo'ladi. Ya'ni
strategiya o'zi mo'ljallangan lahzada deyarli hech qachon ochilmaydi.

Darvoza noto'g'ri emas — u aynan "tushayotgan bozorda arzon degan
narsa yo'q" qoidasini himoya qiladi. Lekin shu bilan strategiyaning
o'zi deyarli ma'nosiz bo'lib qoladi.

---

## 2. Bundan MUHIMROQ topilma: asosiy tizim zarar ko'rsatyapti

Correction Entry savoli kichik bo'lib qoldi. Jadvaldagi haqiqiy
xabar boshqa:

| Ko'rsatkich | Qiymat |
|---|---|
| Win-rate | **37.9%** |
| Profit factor | **0.77** (1 dan past = zarar) |
| O'rtacha natija | **-0.43%** har savdoda |
| TP2 gacha yetgan | 29.9% |
| Yopilgan savdo | 649 ta |
| Ketma-ket zarar | 23 ta |

Bu — Correction Entry'siz, ya'ni **hozir jonli ishlayotgan tizim**.

Ikki yillik ma'lumotda 649 ta savdo — namuna kichik emas. Ya'ni
"tasodif" deb yozib bo'lmaydi.

**Raqamlar qanday o'qiladi.** "jami%" va "pasayish" — foizlarning
YIG'INDISI, murakkab foiz emas. Ya'ni -276.9% "hisob nolga tushdi"
degani emas; u "har savdoga bir xil ulush qo'yilganda o'rtacha
-0.43% dan 649 marta" degani. Baribir manfiy.

**Muhim cheklov: komissiya va slippage HISOBGA OLINMAGAN.** Kodda
ular umuman modellashtirilmagan. Demak haqiqiy natija bu
raqamlardan YOMONROQ bo'ladi, yaxshiroq emas.

---

## 3. Nima noto'g'ri ketyapti — dastlabki o'qish

Win-rate 38% o'z-o'zidan yomon emas: R/R 1:3 bo'lsa, 38% ham
foydali chiqadi. Lekin **"haqiqatda olingan o'rtacha R/R" = -0.45**.

Ya'ni: darajalar 1:3 nisbat bilan QURILADI, lekin narx TP2 gacha
faqat 30% holatda yetadi. Stop esa to'liq ishlaydi. Demak:

> TP2 stopga nisbatan JUDA UZOQ qo'yilyapti.

**Sabab kodda ochiq turibdi.** `core/analysis/scoring/levels.py`:

- **TP1 — TUZILMADAN**: eng yaqin resistance zonasi (`_build_tp1`)
- **TP2 — FORMULADAN**: `entry x (1 + stop_masofa x min_risk_reward)`
  (`_build_tp2`)

Ya'ni TP2 bozorda nima borligiga umuman qaramaydi. U faqat stopdan
hisoblanadi. Stop keng bo'lsa — TP2 uzoqqa uchib ketadi, u yerda
qarshilik bormi yoki yo'qmi, ahamiyati yo'q.

TP1 esa haqiqiy zonada. Shuning uchun narx TP1 gacha yetadi,
TP2 gacha esa 70% holatda yetmaydi.

### Tuzatish (2026-09-02, keyingi tahrir)

Dastlabki hisobotda "ball chegarasi deyarli hamma narsani to'sadi"
deb yozilgan edi. **Bu noto'g'ri.** Voronkada chegara bosqichi 29%
o'tkazadi (7 335 dan 2 130 ta). "Eng yuqori ball 55" faqat RAD
ETILGANLAR orasidagi eng yuqorisi — rad etilgan har bir nomzod
ta'rifiga ko'ra 60 dan past, ya'ni bu raqam hech narsani isbotlamaydi.

Xato o'z vaqtida tuzatildi, chunki u noto'g'ri qarorga olib borardi:
zarar ko'rsatayotgan tizimda chegarani PASAYTIRISH zararni
ko'paytirardi.

---

## 4. Nima qilinmasin

- **Jonli pulga qo'yilmasin.** 6.3-band shartini bu natija
  bajarmaydi.
- **Raqamlarni "yaxshilash" uchun sozlama tanlanmasin.** Beshta
  variantdan eng yaxshisini olish — tarixga moslashib qolish
  (overfitting). Muammo sozlamada emas, TP/Stop mantiqida.
- **`R/R 1.5` va `R/R 2.5` variantlari hech narsa o'lchamadi** —
  ikkalasi bir xil natija berdi. Sabab: Correction Entry'da TP2
  impuls cho'qqisiga qo'yiladi va nisbat baribir 2.5 dan yuqori
  chiqadi, ya'ni chegara hech qachon ishlamaydi. Bu variantlar
  keyingi safar boshqacha qurilishi kerak.

---

## 5. Keyingi qadam (taklif, qaror loyiha egasiniki)

1. TP2 masofasini tuzilmadan olish — hozir u `min_risk_reward`
   orqali STOPDAN hisoblanadi, ya'ni bozor emas, formula belgilaydi
2. Komissiya va slippage backtestga qo'shilsin — hozir natija
   haqiqiydan yaxshiroq ko'rinadi
3. Shundan keyin backtest qaytadan — eski va yangi TP2 yonma-yon

Ball chegarasiga (60) TEGILMAYDI: voronka uni muammo deb
ko'rsatmayapti va zarar ko'rsatayotgan tizimda chegarani
pasaytirish zararni ko'paytiradi.
