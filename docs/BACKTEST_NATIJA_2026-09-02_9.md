# Backtest natijasi #9 — BOSHQA DAVRDA HAM TAKRORLANDI

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun tahlil + 427 kun isinish
**Oyna:** 2022-09-02 → **2024-09-02** (`--end-date 2024-09-02`)
**Kod:** `e0ad1ff` | GitHub Actions run #12

> Bu natija #8 bilan BIR XIL kod, BIR XIL variantlar, lekin
> **butunlay boshqa ma'lumot**. Ikki oyna kesishmaydi:
>
> ```
> oyna A (natija #8):  2024-09 ---------------- 2026-09
> oyna B (natija #9):  2022-09 -- 2024-09
> ```
>
> Har oynaning keshi alohida saqlanadi, ya'ni ikkinchi yugurish
> birinchisining shamlarini qayta ishlatmadi
> (`docs/ARXITEKTURA.md`, 84-bo'lim).

---

## Jadval — oyna B (2022-09 → 2024-09)

| variant | signal | win | TP2 gacha | **PF** | **o'rt.%** | jami% | pasayish |
|---|---|---|---|---|---|---|---|
| hozirgi holat | 1098 | 18.8% | 18.6% | 0.34 | −1.20 | −1287.7 | 1290.0% |
| **TP1 nisbat poli 1.5** | 601 | 34.6% | 34.3% | **0.93** | −0.17 | −98.9 | 239.7% |
| **TP1 nisbat poli 2.0** | 495 | 31.1% | 30.7% | **1.01** | **+0.03** | **+15.7** | 211.1% |
| bitta TP (nazorat) | 672 | 36.2% | 36.2% | 0.87 | −0.29 | −190.8 | 241.9% |
| foiz oraliqlari (nazorat) | 752 | 33.5% | 32.4% | 0.75 | −0.48 | −354.2 | 359.0% |
| oraliq + nisbat poli | 605 | 33.2% | 32.8% | 0.83 | −0.39 | −231.2 | 286.8% |

Tayanch: **+150.3%** (2022-yil tubidan 2024-yilgacha).

---

## 1. 🟢 TAKRORLANDI — oltita variantning TARTIBI ham saqlandi

| variant | PF, oyna A | PF, oyna B |
|---|---|---|
| hozirgi holat | 0.30 | 0.34 |
| foiz oraliqlari (nazorat) | 0.64 | 0.75 |
| bitta TP (nazorat) | 0.74 | 0.87 |
| oraliq + nisbat poli | 0.76 | 0.83 |
| TP1 nisbat poli 1.5 | 0.79 | 0.93 |
| TP1 nisbat poli 2.0 | 0.82 | 1.01 |

Ikkala oynada ham:

1. nisbat poli bazadan **ancha** yaxshi (0.30→0.82 va 0.34→1.01);
2. nisbat poli **foiz oraliqlaridan** yaxshi — ya'ni tashxis eski
   yo'lni takrorlamadi, yangi narsa qo'shdi;
3. nisbat poli **bitta TP** dan yaxshi — muammo qismli sotishning
   o'zida emas, TP1 ning JOYIDA edi;
4. **oraliq + poli** yolg'iz polidan YOMON — foizlar keraksiz,
   loyiha egasining qoidasi raqam bilan yana tasdiqlandi.

Tartibda bitta joy almashdi (oyna B da "bitta TP" 0.87 bilan
"oraliq + poli" 0.83 dan o'tib ketdi) — qo'shni ikki qiymat,
xulosaga ta'sir qilmaydi.

Bu tasodif bo'lishi qiyin: alohida yuklangan ma'lumot, boshqa
bozor rejimi (A — yon/tushuvchi, B — ko'tarilish), oltita
variant, va munosabatlarning hammasi bir xil yo'nalishda.

### Baza qanchalik buzuq edi — buni ham ikkala oyna aytdi

```
              oyna A    oyna B
win-rate      17.5%     18.8%
TP2 gacha     17.1%     18.6%
```

Ikkita mustaqil davrda deyarli bir xil raqam. Ya'ni bu bozor
xususiyati emas, MEXANIZM xatosi edi (natija #7 tashxisi).

---

## 2. BAYROQ YOQILDI

Qoida oldindan yozib qo'yilgan edi (`docs/GIPOTEZA_DAFTARI.md`):

> `enforce_tp1_ratio` bayrog'i faqat IKKALA oynada ham bir
> yo'nalishda natija bergandagina yoqiladi.

Shart bajarildi:

```yaml
enforce_tp1_ratio: true
tp1_min_risk_reward: 2.0
```

**Nega 1.5 emas, 2.0.** 2.0 ikkala oynada ham PF va jami natija
bo'yicha 1.5 dan yaxshi. Farq shundaki:

* oyna A da 2.0 ning ustunligi faqat SAVDO KAMAYGANIDAN edi —
  bitta savdodagi natija bir xil (ikkalasida −0.51%);
* oyna B da esa bitta savdodagi natija ham yaxshiroq
  (+0.03% va −0.17%).

Ya'ni 2.0 hech bir oynada hech bir o'lchov bo'yicha yomon
emas, bittasida esa haqiqatan yaxshiroq. Qiymat daftarda 🟡
bo'lib qoladi — uchinchi oynada qiymat supurgisi (1.5 / 2.0 /
2.5 / 3.0) o'lchanadi.

---

## 3. NIMA O'ZGARMADI — tizim hali ham tayanchdan yomon

```
oyna B, eng yaxshi variant:  +15.7%
o'sha davrda olib ushlash:  +150.3%
```

PF 1.01 — bu "nolga yaqin", "foydali" emas. Va bu OYNA B da,
ya'ni bozor tubdan ko'tarilgan davrda. Oyna A da eng yaxshi
variant hali ham 0.82.

Ikkala oyna bitta xulosaga olib keladi va u o'zgarmadi:

> **Signal berish mexanizmi hali ham hech narsa qilmaslikdan
> yomon ishlaydi.** TP1 poli katta teshikni yopdi, lekin
> kirishning O'ZI hali ham tanlay olmaydi.

Raqam buni ochiq ko'rsatadi: pol yoqilganda ham TP2 gacha
yetish 30-34%. Tasodifiy kirish uchun (Stop S, nishon 1.5S)
kutilgan qiymat ~40%. Ya'ni kirish tanlovi hali ham
TASODIFDAN YOMON.

---

## 4. YOQISHDA TOPILGAN NARSA — mexanizm o'ylanganidan boshqa edi

Bayroqni yoqib, testlarni yurgizganda kod boshqa narsa aytdi.
Tizimda ikkita nisbat bor va ular bir-biriga bog'liq:

```
trade_rules.tp1_min_risk_reward         2.0   TP1 uchun POL
strategies.classic_ta.min_risk_reward   1.5   YAKUNIY nishon
```

Pol yakuniy nishondan **yuqori**. Ya'ni polga bo'ysungan har
qanday TP1 avtomatik ravishda yakuniy nishondan ham uzoqda
bo'ladi — "ikkinchi nishon" degan narsa qolmaydi.

Kod buni JIMGINA hal qilardi:

```python
# eski kod, _build_tp2 ichida
if nishon <= tp1:
    nishon = tp1 * 1.001      # TP2 = TP1 + 0.1%
```

Kartochkada bu shunday ko'rinardi: **TP1 130.00, TP2 130.13**.
0.1% masofa kelib-ketish xarajatini (0.3%) ham qoplamaydi —
ya'ni ikkinchi nishon mavjud emas edi, faqat mavjuddek
ko'rinardi.

### Buning izi RAQAMLARDA ham bor edi

| | win-rate | TP2 gacha |
|---|---|---|
| natija #8, poli 1.5 | 31.6% | 30.9% |
| natija #9, poli 1.5 | 34.6% | 34.3% |

Ikkalasi deyarli teng. Sabab endi ma'lum: TP1 va TP2 amalda
bitta narx edi.

### XULOSA TUZATILADI

O'lchangan mexanizm "TP1 ni yaxshiroq joyga qo'yish" emas:

> **Yagona nishonni yetarlicha UZOQQA (Stop×2) va imkon
> bo'lsa haqiqiy zonaga qo'yish.**

Natija o'zgarmaydi — PF ikkala oynada ham ko'tarildi. Faqat
NIMA UCHUN degan javob boshqa.

### Kod endi buni OCHIQ qiladi

Yasama `tp1 * 1.001` olib tashlandi. TP1 allaqachon 1:N
nisbatidan uzoqda bo'lsa, signal **bitta TP** bilan quriladi
(butun pozitsiya o'sha yerda yopiladi). Bu loyiha egasining
qoidasiga mos — "2 TP majburiy emas, 1, 2 yoki 3 bo'lishi
mumkin — sharoitga qarab".

Lekin hozir bu TANLOV emas, MAJBURIYAT: classic_ta uchun boshqa
variant qolmagan. Shuning uchun keyingi to'plam shu haqda.

---

## 5. Keyingi o'lchov — yakuniy nishon nisbati

`strategies.classic_ta.min_risk_reward` polidan yuqoriga
ko'tarilsa, haqiqiy ikkita TP qaytadi. Savol: natija saqlanadimi?

| variant | nima o'lchaydi |
|---|---|
| hozirgi holat (1.5) | bugungi sozlama — amalda bitta TP |
| 2.2 | poldan sal yuqori: tor, lekin haqiqiy joy |
| 2.5 | o'rtacha joy |
| 3.0 | brief talab qiladigan 1:3 |
| 4.0 | ataylab uzoq — nishon yetib bo'lmaydigan bo'ladimi |

Nazorat — "hozirgi holat" ning o'zi. Yangi qiymatlar undan
yaxshi chiqmasa, bitta TP shundayligicha qoladi.

---

## 6. Keyingi 🔴 — ball shifti

Ikkala oynada, barcha variantlarda, 4412 qadam va 5 coin
bo'ylab rad etilgan nomzodlarning **eng yuqori bali aynan
55.0**:

```
Chegaraga yetmagan nomzodlar: 7985 ta
  eng yuqori ball: 55.0  |  o'rtacha: 42.8
```

55.0 — tasodifiy son emas: u `scoring.thresholds.
threshold_mid_health` ning aynan o'zi. Ball hech qachon undan
yuqoriga chiqmasa, "moslashuvchi chegara" amalda ikki
qiymatlidir va ball SIFAT haqida hech narsa demaydi.

Bu daftarda run #9 dan beri 🔴 turibdi va endi IKKINCHI
oynada ham aynan shu shift ko'rindi — ya'ni u davrga bog'liq
emas. Keyingi to'plam shu haqda.
