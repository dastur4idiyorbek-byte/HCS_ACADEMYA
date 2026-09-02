# Backtest natijasi #7 — to'rtta mexanizm o'zgarishi

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun tahlil + 427 kun isinish
**Qadam:** 4 412 tahlil qilindi
**Kod:** `47d3cb6` | GitHub Actions run #10

---

## Jadval

| variant | signal | savdo | win* | TP2 gacha | PF | **o'rt.%** | jami% |
|---|---|---|---|---|---|---|---|
| hozirgi holat (oraliqlar O'CHIQ) | 1297 | 1268 | 64.0% | 17.1% | 0.30 | **−1.31** | −1665.1 |
| sifat darvozasi (pol 35) | 446 | 446 | 69.3% | 17.0% | 0.29 | −1.43 | −640.0 |
| sifat darvozasi (pol 45) | 368 | 368 | 69.0% | 16.6% | 0.29 | −1.49 | −547.6 |
| faqat pol 35 (shartnomasiz) | 2054 | 2029 | 71.2% | 16.8% | 0.28 | −1.35 | −2731.1 |
| bitta TP (yakuniy nishon) | 855 | 833 | 34.5% | **32.4%** | **0.74** | **−0.60** | −499.9 |
| uchtagacha TP | 1297 | 1268 | 64.0% | 17.1% | 0.28 | −1.37 | −1737.8 |
| **foiz oraliqlari YOQILGAN** | 884 | 866 | 37.3% | 30.0% | 0.64 | **−0.75** | −649.8 |
| muddat 24 soat | 1536 | 1504 | 61.0% | 9.8% | 0.32 | −1.08 | −1619.0 |
| muddat 72 soat | 1365 | 1337 | 63.3% | 15.6% | 0.31 | −1.23 | −1640.7 |

Tayanch: **+31.5%**. To'qqiztasi ham tayanchdan yomon.

> **\* Bu win-rate yolg'on gapiradi.** Pastdagi "Nima uchun 64% va
> −1.31% yonma-yon turibdi" bo'limiga qarang. Tuzatildi, lekin
> yuqoridagi jadval eski ta'rif bilan bosilgan.

---

## 0. Avval o'lchovning O'ZI tekshirildi

`foiz oraliqlari yoqilgan` varianti run #9 ning bazasiga **aynan
teng** chiqdi:

```
run #9 baza:              884 signal, 37.3%, 30.0%, −0.75, −649.8
run #10 "oraliqlar yoq.": 884 signal, 37.3%, 30.0%, −0.75, −649.8
```

Ya'ni TP soni, `takes` ro'yxati, yangi darvoza va yangi holat —
hammasi qo'shildi, lekin bayroq yoqilganda tizim aynan eskicha
ishlaydi. Refaktor xatti-harakatni o'zgartirmagan.

---

## 1. ⚫ FOIZ ORALIQLARI: qaror natijani YOMONLASHTIRDI

Bu sizning qaroringiz edi ("TP STOP FOIZLARI MAJBURIY EMAS — RISK
1/3") va u tekshirildi. Ikki variant faqat shu bayroq bilan farq
qiladi:

| | oraliqlar YOQILGAN | oraliqlar O'CHIQ |
|---|---|---|
| Signal | 884 | 1297 |
| TP2 gacha | **30.0%** | **17.1%** |
| Profit factor | **0.64** | **0.30** |
| O'rtacha savdo | **−0.75%** | **−1.31%** |
| Jami | −649.8% | −1665.1% |

**MEXANIZM — nima uchun.** Oraliqlar o'chirilganda `min_tp_distance_pct`
ham o'chdi. U TP1 uchun YAGONA pol edi:

```
oraliq yoqilgan:  TP1 = kamida 3% (yoki stop×1.5)
oraliq o'chiq:    TP1 = ENG YAQIN qarshilik — u +0.5% bo'lishi mumkin
```

Natijada savdo shunday ko'rinish oldi:

```
TP1 +0.5% da  -> pozitsiyaning yarmi sotiladi  -> +0.25%
Stop breakeven -> qolgan yarmi nolda yopiladi  ->  0.00%
komissiya                                       -> −0.30%
                                                  --------
                                                   −0.05%
```

Ya'ni "g'alaba" deb yozilgan savdo AMALDA NOLGA yaqin. Stop esa
o'z-o'zicha keng qoladi (support qayerda bo'lsa, o'sha yerda —
11% ham bo'lishi mumkin). Natija: **kichkina yutuqlar, katta
zararlar**.

**MUHIM: sizning qoidangiz noto'g'ri emas.** Xato uni bajarishda.
"Nisbat 1:3" faqat YAKUNIY nishonga qo'llanildi, TP1 esa polsiz
qoldi. To'g'ri yechim foizni qaytarish emas — TP1 ga ham NISBAT
poli qo'yish:

```
tp1_min_risk_reward: 1.5   # allaqachon sozlamada bor
```

Bu qiymat hozir faqat "qarshilik topilmadi" tarmog'ida ishlaydi.
Tuzilmaviy TP1 ga u umuman qo'llanmaydi. Shu tuzatilsa, foiz
oraliqlarisiz ham TP1 mazmunli masofada qoladi.

---

## 2. ⚫ SIFAT DARVOZASI: signal 3 barobar kamaydi, sifat oshmadi

| | hozirgi holat | pol 35 | pol 45 |
|---|---|---|---|
| Signal | 1297 | **446** | **368** |
| TP2 gacha | 17.1% | 17.0% | 16.6% |
| Profit factor | 0.30 | 0.29 | 0.29 |
| O'rtacha savdo | −1.31% | **−1.43%** | **−1.49%** |

CryptoSpot3% shartnomasi 10 584 nomzodni rad etdi va voronkani
52% dan **7.5%** ga tushirdi. Lekin TP2 gacha yetish
QIMIRLAMADI (17.1% → 17.0%), bitta savdodagi natija esa
YOMONLASHDI.

**Xulosa:** shartnoma (yo'nalish + yalash + daraja turi) yaxshi
savdoni yomonidan ajrata olmaydi. U signal SONINI kamaytiradi,
sifatini emas. Bu — oldingi oltita gipoteza bilan bir xil taqdir,
lekin endi u sozlama emas, QAROR MEXANIZMI darajasida sinaldi.

**Nazorat varianti aynan shuning uchun kerak edi.** "Faqat pol 35
(shartnomasiz)" 2054 signal berdi va eng yomon natijani
(−2731.1%). Ya'ni darvozaning "yaxshi" ko'rinishi shartnomadan
emas, signal KAMAYGANIDAN — zarar keltiruvchi ishni kamroq
bajarish.

---

## 3. 🟡 TP SONI: bitta TP eng yaxshi natija berdi

| | 1 TP | 2 TP (baza) | 3 TP |
|---|---|---|---|
| TP2 gacha | **32.4%** | 17.1% | 17.1% |
| Profit factor | **0.74** | 0.30 | 0.28 |
| O'rtacha savdo | **−0.60%** | −1.31% | −1.37% |
| Jami | **−499.9%** | −1665.1% | −1737.8% |

**Bitta TP** barcha to'qqiz variant ichida eng yaxshisi. Sabab
1-bo'limdagi mexanizmning teskarisi: qismli sotish yo'q, ya'ni
arzimas TP1 da yarim pozitsiya sotilmaydi va breakeven stop
foydani nolga qaytarmaydi. Butun pozitsiya 1:3 nishonda turadi.

Bu **1-bo'limdagi tashxisni mustaqil ravishda tasdiqlaydi**:
muammo TP1 ning joyida.

**Uchta TP** — jadvalda bazadan farq qilmaydi (1297 signal, aynan
bir xil voronka). Ya'ni oraliq zona deyarli hech qachon
topilmaydi va uchinchi TP amalda qo'shilmaydi. Kod to'g'ri
ishlayapti (raqam o'ylab topilmaydi), lekin bu sozlama hozircha
ta'sirsiz. 🟡 — o'lchandi, natijasi "farq yo'q".

---

## 4. ⚫ MUDDAT: eng yomon natijalardan biri

| | baza | 24 soat | 72 soat |
|---|---|---|---|
| Signal | 1297 | 1536 | 1365 |
| TP2 gacha | 17.1% | **9.8%** | 15.6% |
| O'rtacha savdo | −1.31% | −1.08% | −1.23% |
| Jami | −1665.1% | −1619.0% | −1640.7% |
| Ushlash | 23.4 soat | 15.9 soat | 21.1 soat |

**TP2 gacha yetish 17.1% dan 9.8% ga tushdi.** Ya'ni muddat
foydasiz savdolarni emas, KUCHAYISHGA ULGURMAGAN savdolarni
kesyapti. Bu gipotezani rad etishning aynan o'zi — oldindan
yozib qo'yilgan shart shu edi.

Yon ta'sir ham ko'rindi: signal soni 1297 dan 1536 ga chiqdi,
chunki erta yopilgan pozitsiyalar ochiq signal limitini
bo'shatadi (`risk_engine` o'tish darajasi 43% → 50.6%). Ko'proq
savdo, har biri yomonroq.

---

## Nima uchun 64% va −1.31% yonma-yon turibdi

Bu ikkalasi ham to'g'ri hisoblangan, lekin "win-rate" so'zi
boshqa ma'noda ishlatilgan edi:

```python
is_win = outcome in {"tp2_hit", "tp1_then_stop"}   # ESKI
```

`tp1_then_stop` — TP1 olindi, keyin Stop kirish narxida ishladi.
1-bo'limdagi hisob bo'yicha bunday savdo komissiyadan keyin
MANFIY chiqadi. Turkum "g'alaba", pul esa kamaygan.

**Tuzatildi:**

```python
is_win = result_pct > 0   # YANGI — hisobda pul ko'paydimi
```

"Nishonga yetdimi" degan boshqa savol yo'qolmadi: unga `tp2_rate`
javob beradi va u hisobotda alohida qator.

**Diqqat:** yuqoridagi jadval ESKI ta'rif bilan bosilgan. Keyingi
yugurishda win-rate raqamlari ancha past chiqadi va ular shu
hisobot bilan solishtirilmaydi. Qolgan hamma ko'rsatkich
(TP2 gacha, profit factor, o'rtacha, jami) o'zgarmaydi — xulosalar
ularga tayanadi.

---

## Xulosa

To'rtta mexanizm o'zgarishidan **uchtasi rad etildi**, bittasi
ta'sirsiz. Lekin bu yugurish oldingilaridan farq qiladi: u
faqat "ishlamadi" demadi, **SABABNI ko'rsatdi**.

Uchta mustaqil dalil bitta joyga ishora qilyapti:

1. Foiz oraliqlari o'chirilganda natija yomonlashdi
2. Bitta TP (qismli sotishsiz) eng yaxshi natija berdi
3. Ikkalasining mexanizmi bir xil — **TP1 juda yaqin**

Ya'ni muammo endi "kirish sifati" ham, "TP2 qayerda" ham emas:

> **TP1 polsiz qoldi. Qismli sotish arzimas foydada bo'lyapti,
> breakeven stop esa qolganini nolga qaytaryapti.**

Bu O'LCHANGAN tashxis, taxmin emas — uni ikkita mustaqil variant
tasdiqlaydi.

**Keyingi qadam** (hali o'lchanmagan): `tp1_min_risk_reward`
tuzilmaviy TP1 ga ham qo'llanilsin. Bu sizning qoidangizga zid
emas — foiz emas, NISBAT poli.
