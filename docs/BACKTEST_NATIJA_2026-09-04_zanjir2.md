# Zanjir natijasi #2 — 12 coin, ablatsiya va kengaytirilgan walk-forward

Sana: 2026-09-04
Actions yugurishi: 33819901519 (12 coin, 730 kun, `data-api.binance.vision`)
Coinlar: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOT, ATOM, LTC, NEAR
Xarajat: har savdoda 0.3% (komissiya + slippage, borish-kelish)

Natija #1 (5 coin) ni davom ettiradi. Coin soni 5 dan 12 ga
ko'tarildi — sabab: 5 coinda savdo soni juda kam edi va ablatsiya
xulosasi ishonchsiz chiqardi.

---

## 1. Tayanch o'lchov — 12 coin

| Ko'rsatkich | Qiymat |
|---|---|
| Savdo soni | **277** |
| Foydali | 68.2% |
| Profit Factor | **3.50** |
| O'rtacha savdo | +2.78% |
| Jami | +770.0% |
| Eng katta pasayish | 28.2% |

Savdo soni 100 dan oshdi — ya'ni ablatsiya xulosasi endi
`ISHONCHLI_SAVDO = 100` chegarasidan yuqori va o'qilishi mumkin.

---

## 2. Ablatsiya — 16 ta ichki tekshiruv birma-bir o'chirildi

Prompt qoidasi: **|ΔPF| < 0.03 bo'lgan tekshiruv olib tashlanadi.**

### 2.1. Hech bir tekshiruv PF ni OSHIRMADI

Bu — kutilmagan natija va yashirilmaydi. "Hissa qo'shadi" ro'yxati
**bo'sh** chiqdi. Ya'ni: har bir tekshiruvni o'chirganda PF yo
o'zgarmadi, yo **yaxshilandi**.

### 2.2. PF ni umuman o'zgartirmagan 11 ta tekshiruv (ΔPF = +0.00)

| # | Tekshiruv | Blok |
|---|---|---|
| 1.1 | bozor_holati | Fundamental |
| 1.2 | pul_oqimi | Fundamental |
| 1.3 | katalizator | Fundamental |
| 1.4 | kayfiyat | Fundamental |
| 2.2 | bos_tasdiqlangan | Struktura |
| 2.3 | qarshi_choch_yoq | Struktura |
| 3.2 | order_block | Zona Sifati |
| 3.3 | fvg | Zona Sifati |
| 3.4 | volume_profile | Zona Sifati |
| 4.1 | liquidity_sweep | Tasdiqlash |
| 4.4 | fundamental_mos | Tasdiqlash |

### 2.3. O'chirilganda PF OSHGAN 5 ta tekshiruv

| # | Tekshiruv | O'chirilganda PF | ΔPF |
|---|---|---|---|
| 2.4 | nisbiy kuch | 4.15 | **+0.65** |
| 3.1 | fibonacci | 4.03 | **+0.53** |
| 4.3 | RSI | 3.60 | +0.10 |
| 4.2 | pastki TF | 3.56 | +0.06 |
| 2.1 | swing | 3.53 | +0.03 |

---

## 3. Nima uchun bunday chiqdi — sabab TUZILMAVIY

Sabab tekshiruvlarning "yomonligi" emas. Sabab — **blok qoidasi**.

Blok `kuch >= 1` da o'tadi, ya'ni 4 tadan **bittasi** yetadi.
Bu blok ichida tekshiruvlarni **VA** emas, **YOKI** qilib qo'yadi:

    Blok o'tdi = t1 YOKI t2 YOKI t3 YOKI t4

Bir tekshiruvni YOKI zanjiridan olib tashlash natijani deyarli
o'zgartirmaydi — qolgan uchtasi baribir blokni o'tkazadi. Shuning
uchun 11 ta tekshiruv **+0.00** bergani "ular ishlamaydi" degani
emas; "ular hozirgi qoida ostida hech qachon HAL QILUVCHI emas"
degani.

O'chirilganda PF oshgan 5 tasi esa boshqa narsani ko'rsatadi:
ular ba'zan **yolg'iz** blokni o'tkazgan — ya'ni qolgan uchtasi
YO'Q bo'lgan holatda ham savdo ochilgan, va o'sha savdolar
o'rtacha yomon chiqqan.

**Bu — o'lchangan fakt, taxmin emas.** Lekin undan "qoidani
2/4 qilaylik" degan xulosa CHIQARILMAYDI: bu yangi qoida bo'ladi
va uni ham o'lchash kerak. Prompt qoidasi: taxmin qilinmaydi.

---

## 4. Chegara qayta o'lchandi — 12 coinda

### 4.1. `stop_eng_kam_pct`

| Chegara | Savdo | PF |
|---|---|---|
| 0.5 | 523 | **3.63** |
| 1.0 | 372 | 3.43 |
| **1.5 (hozirgi)** | **277** | **3.50** |
| 2.0 | 211 | 3.17 |
| 3.0 | 111 | 1.80 |

5 coinda 0.5 va 1.5 orasidagi farq katta ko'rinardi; 12 coinda
farq **0.13 PF** — ya'ni shovqin darajasida. Lekin savdo soni
523 va 277 — deyarli ikki barobar.

**Qaror: 1.5 QOLADI.** Sabab muhandislik, o'lchov emas va shundayligicha
yoziladi: 0.5% stop bilan real bozorda spread va slippage stopni
tasodifan uradi, backtest esa buni to'liq modellay olmaydi.

### 4.2. `tp1_eng_kam_nisbat`

| Nisbat | Savdo | PF |
|---|---|---|
| 1.0 | 339 | 3.39 |
| **1.5 (hozirgi)** | **237** | **3.51** |
| 2.0 | 114 | 2.65 |

1.5 eng yuqori. O'zgartirilmaydi.

---

## 5. Walk-forward — 12 coin, uchta kesishmaydigan oyna

| Oyna | Savdo | PF | O'rtacha savdo |
|---|---|---|---|
| 1 | 121 | 3.48 | +3.18% |
| 2 | 87 | **4.10** | +3.15% |
| 3 | 96 | **2.91** | +1.87% |

Uchala oynada ham PF ≥ 1.0 — **to'xtash qoidasi ishga tushmadi.**

Lekin skript ogohlantirdi: 🟡 **ustunlik 16% toraygan.**
Uchinchi oynada o'rtacha savdo +3.18% dan +1.87% ga tushgan —
ya'ni PF hali baland bo'lsa ham, har bir savdodan olinadigan
foyda kamaygan. Bu — kuzatiladi, e'tiborsiz qoldirilmaydi.

---

## 6. Voronka — nima to'sib turibdi

| To'siq | Soni |
|---|---|
| Struktura bloki | 4074 |
| Tasdiqlash bloki | 2399 |
| Zona Sifati bloki | 15 |

Daraja bosqichidagi rad etishlar:

| Sabab | Soni |
|---|---|
| zona buzilgan | 1113 |
| TP1/Stop nisbati past | 1003 |
| stop juda yaqin | 990 |

Zona Sifati bloki deyarli hech kimni to'smaydi (15 ta) — chunki
u ham 1/4 qoidasi ostida ishlaydi va Fibonacci deyarli har doim
topiladi. Bu 3-bo'limdagi tuzilmaviy sabab bilan bir xil.

---

## 7. Nimaga hali ISHONMASLIK kerak

1. **PF 3.50 juda baland.** Bunday raqam odatda o'lchov xatosini
   bildiradi, ustunlikni emas. Ikkita oyna 2.91 va 4.10 — tarqoqlik
   katta.
2. **277 savdo — 12 coin va 2 yil uchun kam.** Statistik ishonch
   uchun yetarli, lekin bozor rejimlari bo'yicha emas: ikki yilda
   bitta chuqur ayiq bozori bor edi.
3. **Ablatsiya "hech narsa hissa qo'shmaydi" deyapti.** Agar
   16 ta tekshiruvning birortasi ham natijani yaxshilamasa,
   savol tug'iladi: natijani nima keltirib chiqaryapti? Ehtimoliy
   javob — **darajalar** (zona ichida kirish, zona tagida stop,
   strukturaviy TP), tekshiruvlar emas. Buni alohida o'lchash kerak.
4. **`risk_engine` ulanmagan.** Sig'im va korrelyatsiya
   cheklovlari hisobga olinmagan — real hisobda 12 coinning
   hammasiga bir vaqtda kirib bo'lmaydi.
5. **Fundamental blok qisman soxta.** Funding Rate va Fear & Greed
   tarixi bor; OI, Netflow, sektor, yangiliklar tarixi yo'q va
   backtestda `MALUMOT_YOQ` sifatida o'tadi
   (`docs/FUNDAMENTAL_MALUMOT_MANBALARI.md`).

---

## 8. Keyingi qadamlar — tartib bilan

1. **11 ta bo'sh tekshiruvni BIRGA o'chirib o'lchash.** Birma-bir
   o'chirish va birga o'chirish — boshqa narsa: birinchisida blok
   qolgan tekshiruvlar bilan o'tadi, ikkinchisida blok butunlay
   bo'shab qolishi mumkin. Taxmin qilinmaydi, o'lchanadi.
2. **Darajalarni alohida o'lchash:** zanjirsiz, faqat zona +
   stop + TP qoidasi. Agar PF o'xshash chiqsa — ustunlik
   darajalarda, tekshiruvlarda emas.
3. **`risk_engine` bilan o'lchash.**
4. Faqat shundan keyin — jonli tizimga ulash haqida gap.

Hech biri bajarilmaguncha modul **jonli signal bermaydi.**
