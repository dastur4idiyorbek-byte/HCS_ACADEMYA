# Backtest natijasi #8 — TP1 nisbat poli ISHLADI

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun tahlil + 427 kun isinish
**Kod:** `6f877fd` | GitHub Actions run #11

> **Win-rate ta'rifi o'zgardi** (`result_pct > 0`). Shu sababli
> win-rate ustuni natija #7 bilan solishtirilmaydi. PF, TP2 gacha
> va o'rtacha solishtiriladi — xulosalar ularga tayanadi.

---

## Jadval

| variant | signal | win | TP2 gacha | **PF** | **o'rt.%** | jami% | pasayish |
|---|---|---|---|---|---|---|---|
| hozirgi holat | 1297 | 17.5% | 17.1% | 0.30 | −1.31 | −1665.1 | 1672.2% |
| **TP1 nisbat poli 1.5** | 807 | 31.6% | **30.9%** | **0.79** | **−0.51** | −408.9 | 479.1% |
| **TP1 nisbat poli 2.0** | 643 | 28.2% | 27.3% | **0.82** | **−0.51** | −322.3 | 489.3% |
| bitta TP (nazorat) | 855 | 32.9% | 32.4% | 0.74 | −0.60 | −499.9 | 528.1% |
| foiz oraliqlari (nazorat) | 884 | 31.4% | 30.0% | 0.64 | −0.75 | −649.8 | 659.8% |
| oraliq + nisbat poli | 795 | 31.3% | 30.5% | 0.76 | −0.56 | −441.9 | 475.7% |

Tayanch: **+31.5%**. Oltitasi ham hali tayanchdan yomon.

---

## 1. 🟢 TASHXIS TASDIQLANDI

Natija #7 da tashxis shunday yozilgan edi:

> TP1 polsiz qoldi. Qismli sotish arzimas foydada bo'lyapti,
> breakeven stop esa qolganini nolga qaytaryapti.

Yechim taklif qilingan edi: **foiz emas, nisbat poli**. O'lchov:

| | baza | nisbat poli 1.5 |
|---|---|---|
| Profit factor | 0.30 | **0.79** |
| O'rtacha savdo | −1.31% | **−0.51%** |
| TP2 gacha | 17.1% | **30.9%** |
| Maks. pasayish | 1672% | **479%** |

Bitta savdodagi natija **2.6 barobar** yaxshilandi. TP2 gacha
yetish 17.1% dan 30.9% ga chiqdi — ya'ni TP1 mazmunli joyga
surilgach yakuniy nishon ham erishiladigan bo'ldi.

**Bu sakkiz urinishdan BIRINCHISI bo'lib ishladi.**

---

## 2. Nazorat variantlari — nima uchun ular zarur edi

### Nazorat 1: foiz oraliqlari (eski yo'l)

```
foiz oraliqlari yoqilgan:  PF 0.64,  o'rtacha −0.75%
TP1 nisbat poli 1.5:       PF 0.79,  o'rtacha −0.51%
```

Bu — **hal qiluvchi tekshiruv**. Nisbat poli eski yo'ldan
yaxshiroq chiqmasa, tashxis yangi narsa qo'shmagan bo'lardi:
"foizni qaytargan ma'qul" degan xulosa chiqardi.

Chiqdi. Ya'ni **loyiha egasining qoidasi to'g'ri** — foizlar
kerak emas, lekin NISBAT poli kerak edi.

### Nazorat 2: bitta TP (qismli sotishsiz)

```
bitta TP:            PF 0.74
TP1 nisbat poli 1.5: PF 0.79
```

Natija #7 da bitta TP eng yaxshi variant edi va savol tug'ilgan
edi: qismli sotishning O'ZI muammomi?

**Yo'q.** Qismli sotish TP1 mazmunli joyda bo'lsa foydali.
Muammo qismli sotishda emas, uning QAYERDA bo'lishida edi.

### Nazorat 3: oraliq + nisbat poli birga

```
faqat nisbat poli:   PF 0.79
oraliq + nisbat poli: PF 0.76
```

Ikkalasi birga bo'lganda natija **bir oz yomonroq**. Ya'ni foiz
oralig'i nisbat poli ustiga hech narsa qo'shmaydi — u faqat
ba'zi mazmunli signallarni ortiqcha kesadi.

Bu loyiha egasining qarorini yana bir marta tasdiqlaydi:
**foizlar keraksiz.**

---

## 3. Pol qiymati: 1.5 va 2.0

| | 1.5 | 2.0 |
|---|---|---|
| Signal | 807 | 643 |
| Profit factor | 0.79 | **0.82** |
| O'rtacha savdo | −0.51% | −0.51% |
| Jami | −408.9% | **−322.3%** |
| Maks. pasayish | 479.1% | 489.3% |
| O'rtacha ushlash | 57.8 soat | **75.8 soat** |

2.0 jami natija bo'yicha yaxshiroq, lekin **bitta savdodagi
natija bir xil** (−0.51%). Ya'ni farq savdolar yaxshilanganidan
emas, KAMAYGANIDAN — bu naqsh oldin ham uchragan
(`BACKTEST_NATIJA_2026-09-02_3.md`, "kunlik trend majburiy").

Pasayish ham chuqurroq (489% vs 479%), ushlash ham uzunroq
(75.8 soat vs 57.8). Shuning uchun **1.5 ma'qulroq** — u bir
xil sifatni ko'proq savdoda beradi.

---

## 4. Nima O'ZGARMADI — ochiq aytish kerak

**Tizim hali ham zarar keltiradi.**

```
Profit factor:  0.82  (foydali bo'lish uchun >1.0 kerak)
O'rtacha savdo: −0.51%
Tayanch:        +31.5%,  strategiya: −322.3%
```

Ya'ni tashxis to'g'ri edi va yechim ishladi, lekin u
**yetarli emas**. Yaxshilanish katta (PF 0.30 → 0.82), lekin
pul topish chizig'igacha yetmadi.

### Bitta o'lchov yetarli emas

Loyihaning o'z intizomi (`scripts/backtest.py`):

> Yaxshi natija BOSHQA DAVRDA qayta tekshirilishi shart.

Bu natija BITTA davr (730 kun), BITTA coin to'plami (5 ta) va
BITTA yugurishdan olingan. Oltita variantdan eng yaxshisini
tanlab "tasdiqlandi" deyish — bu backtestning eng keng
tarqalgan xatosi.

**Shuning uchun `enforce_tp1_ratio` hali ham O'CHIQ.** Uni
standart holatga o'tkazish uchun boshqa davrda takroriy o'lchov
kerak.

---

## Xulosa

| gipoteza | holat |
|---|---|
| TP1 ga nisbat poli | 🟢 **ishladi** — PF 0.30 → 0.79 |
| Foizlar keraksiz | 🟢 tasdiqlandi — oraliq qo'shilsa yomonroq |
| Qismli sotish muammo | ⚫ rad etildi — TP1 joyi muammo edi |
| Pol qiymati 2.0 > 1.5 | 🟡 jami yaxshiroq, lekin faqat savdo kamayganidan |

**Sakkizta urinishdan birinchisi ishladi**, va u tasodifan
emas — natija #7 dagi o'lchangan tashxisdan chiqarilgan.

Lekin tizim hali foydali emas. Keyingi ikki savol:

1. **Takroriy o'lchov** — boshqa davrda ham shundaymi?
2. PF 0.82 dan 1.0 gacha qolgan masofani nima yopadi?
