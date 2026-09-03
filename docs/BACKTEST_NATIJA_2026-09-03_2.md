# Backtest natijasi #12 — KITOBNING YADROSI O'LCHANDI

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun tahlil + 427 kun isinish
**Kod:** `656a4b3` | GitHub Actions run #15
**Manba:** `docs/NARX_HARAKATI_STRATEGIYALARI.md`

---

## Jadval

| variant | signal | win | **PF** | **o'rt.%** | jami% | pasayish |
|---|---|---|---|---|---|---|
| hozirgi holat (classic_ta) | 603 | **28.9%** | **0.84** | −0.46 | −277.7 | 451.3% |
| **narx harakati (yolg'iz)** | 300 | 21.3% | 0.74 | −0.46 | −138.7 | **185.3%** |
| ikkalasi birga | 611 | 28.5% | 0.84 | −0.45 | −274.6 | 459.1% |
| kitob, tasdiqsiz | 668 | 28.1% | 0.85 | **−0.39** | −261.2 | 475.3% |
| kitob, qayta sinov 5 | 611 | 28.5% | 0.84 | −0.45 | −274.6 | 459.1% |

Tayanch: **+31.5%**.

---

## 1. ⚫ KITOB USULI YAXSHILAMADI

```
                         win     PF    o'rtacha savdo
classic_ta              28.9%   0.84      −0.46%
narx harakati (kitob)   21.3%   0.74      −0.46%
```

**Bitta savdodagi natija AYNAN BIR XIL: −0.46%.**

Ikkita butunlay boshqa kirish mexanizmi — biri arzon zonada
kiradi, ikkinchisi yorilish va qayta sinovni kutadi — va
o'rtacha natija bir xil chiqdi. Bu tasodif bo'lishi qiyin.

Win-rate esa PASAYDI: 28.9% dan 21.3% ga.

### "Jami natija yaxshiroq" degan gap aldamasin

−138.7% vs −277.7% — chiroyli ko'rinadi, lekin savdo soni ikki
barobar kam (300 va 603). Bitta savdodagi natija o'zgarmagan.

Bu naqsh loyihada OLTINCHI marta uchramoqda (74-bo'lim):
**zarar keltiruvchi ishni kamroq bajarish tuzatish emas.**

---

## 2. ⚫ KITOBNING ENG KO'P TAKRORLANGAN QOIDASI HAM YORDAM BERMADI

Kitob bir necha marta ta'kidlaydi: qayta sinovdan keyin
**buqasimon sham** kutish shart.

```
                    signal    PF    o'rtacha
tasdiq shami SHART    611    0.84    −0.45%
tasdiq shami YO'Q     668    0.85    −0.39%
```

Tasdiqni TALAB QILMAGAN variant biroz YAXSHIROQ chiqdi.

Ya'ni yashil shamni kutish signalni yaxshilamadi — faqat
kechiktirdi.

### Qayta sinov oynasi ham ta'sirsiz

12 shamlik oyna va 5 shamlik oyna — natija bir xilda
(0.84, −0.45%, 611 signal). "Tez qaytgan naqsh kuchliroq"
degan taxmin tasdiqlanmadi.

---

## 3. NIMA ANIQLANDI

Bu **sakkizinchi** to'plam va kirish tomonidagi **beshinchi**
rad etish. Endi ikkita mustaqil dalil bor:

1. `classic_ta` (arzon zonadan kirish) → o'rtacha −0.46%
2. `narx_harakati` (yorilish + qayta sinov + tasdiq) → −0.46%

Ikkalasi ham bir xil. Bundan chiqadigan xulosa qattiqroq:

> **Muammo qaysi naqshni tanlashda emas.** 4 soatlik shamlardan
> hisoblanadigan hech bir naqsh keyingi harakatni oldindan
> aytmayapti. Qaysi qoidani qo'ymaylik, o'rtacha natija bir xil
> chiqmoqda.

Kitobning o'zi ham buni aytadi:

> "Bu xolatda biz 10 tadan 3 martagina to'g'ri bo'lishimiz
> mumkin."

Bizda ham shu: 21-29%. Ya'ni kitob ham, biz ham bir xil
raqamdamiz. Farq shundaki, 30% to'g'ri chiqishda foydali
bo'lish uchun nisbat 1:3 dan yuqori bo'lishi kerak — bizda esa
kelib-ketish xarajati (0.3%) va o'rtacha 1:2 nisbat buni yeb
qo'ymoqda.

---

## 4. BITTA FOYDALI FARQ BOR

```
                        pasayish
classic_ta                451.3%
narx harakati (kitob)     185.3%
```

Kitob usuli **ancha tinch**: savdo ikki barobar kam, pasayish
ikki yarim barobar sayoz. Foyda bermaydi, lekin kapitalni
kamroq silkitadi.

Bu — qaror uchun ma'lumot, tavsiya emas.

---

## 5. BAYROQ O'CHIQ QOLADI

`narx_harakati.enabled: false`. O'lchov uni tasdiqlamadi.

Kod registrda qoladi va o'chirilmaydi: qaror o'lchovga
tayanadi, o'lchov esa boshqa davrda qaytarilishi mumkin.
