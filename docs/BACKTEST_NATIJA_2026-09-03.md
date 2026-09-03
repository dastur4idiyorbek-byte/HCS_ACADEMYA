# Backtest natijasi #11 — YANGI TUZILMA O'LCHANDI

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun tahlil + 427 kun isinish
**Kod:** `06c5e86` | GitHub Actions run #14

---

## Jadval

| variant | signal | win | **PF** | **o'rt.%** | jami% | pasayish |
|---|---|---|---|---|---|---|
| hozirgi holat (skalpsiz) | 603 | 28.9% | **0.84** | **−0.46** | −277.7 | 451.3% |
| skalp yoqilgan (nazorat) | 653 | 28.0% | 0.83 | −0.47 | −300.2 | 464.8% |
| rejim yoqilgan | 410 | 27.4% | 0.75 | −0.75 | −306.4 | 453.9% |
| rejim + diapazon 25% | 389 | 27.1% | 0.75 | −0.76 | −295.8 | 418.8% |
| zona oynasi 200 | 551 | 28.5% | **0.84** | **−0.45** | −245.8 | 450.4% |
| rejim + zona oynasi 200 | 394 | 27.5% | 0.77 | −0.69 | −269.7 | 374.2% |

Tayanch: **+31.5%**.

---

## 1. 🟢 Skalpni o'chirish TO'G'RI qaror edi

Nazorat varianti buni tasdiqladi:

```
skalpsiz:      PF 0.84,  o'rtacha −0.46%,  jami −277.7%
skalp bilan:   PF 0.83,  o'rtacha −0.47%,  jami −300.2%
```

Farq kichik, lekin bir yo'nalishda: skalp qo'shgan 50 ta signal
o'rtachadan yomonroq edi. Bayroq o'chiq qoladi.

---

## 2. ⚫ REJIM RAD ETILDI — va sabab muhim

```
                signal    win     PF    o'rtacha
hozirgi holat     603    28.9%   0.84    −0.46%
rejim yoqilgan    410    27.4%   0.75    −0.75%
```

Rejim 193 ta signalni (32%) kesdi va **qolganlari YOMONROQ**
chiqdi. Ya'ni u o'rtachadan yaxshi savdolarni olib tashlagan.

Bu naqsh loyihada uchinchi marta takrorlanmoqda (74-bo'lim):
zarar keltiruvchi ishni kamroq bajarish tuzatish emas, va bu
yerda hatto shunday ham bo'lmadi — kamroq bajarib, yomonroq
natija olindi.

"Diapazon 25%" ham yordam bermadi (PF 0.75 — aynan bir xil).

**TASHXIS NOTO'G'RI EDI.** "Har timeframe bitta ish qilsin"
degan g'oya mantiqan to'g'ri ko'rinardi, lekin ma'lumot uni
tasdiqlamadi.

---

## 3. 🟡 Zona oynasi — deyarli ta'sirsiz

```
500 sham (83 kun):   PF 0.84,  o'rtacha −0.46%,  603 signal
200 sham (33 kun):   PF 0.84,  o'rtacha −0.45%,  551 signal
```

Bitta savdodagi farq 0.01 punkt — o'lchov xatosidan farq
qilmaydi. Jami natija yaxshiroq ko'rinadi (−245.8 vs −277.7),
lekin bu savdolar yaxshilanganidan emas, **kamayganidan**.

Eskirgan chiziqlar haqidagi kuzatuv mantiqan to'g'ri, lekin
natijaga sezilarli ta'sir qilmaydi.

---

## 4. 🔴 YANGI SAVOL — haftalik struktura juda tez-tez "pasayish"

Rejim varianti 21 000 nomzoddan **10 463 tasini** (deyarli
yarmini) "haftalik yoki kunlik struktura pasayishda" deb rad
etdi.

Ayni davrda bozor **+31.5% ko'tarilgan**.

Ikki ehtimol bor va ular tafovutli:

1. bozor rostdan vaqtining yarmida tuzatishda bo'lgan
   (ko'tarilish uzluksiz bo'lmaydi);
2. struktura aniqlovchisi haftalik qatorda pasayishni
   ORTIQCHA ko'radi.

`tests/core/test_poydevor_tekshiruvi.py` aniqlovchini QO'LDA
qurilgan toza zinapoyada tekshirdi va u to'g'ri ishladi. Lekin
haqiqiy haftalik qator toza zinapoya emas. Bu tekshirilmagan.

---

## 5. ENG MUHIM RAQAM — u yana qimirlamadi

```
hozirgi holat            28.9%
skalp yoqilgan           28.0%
rejim yoqilgan           27.4%
rejim + diapazon 25%     27.1%
zona oynasi 200          28.5%
rejim + zona oynasi 200  27.5%
```

Oltita variant, butunlay boshqa voronkalar (signal soni 389
dan 653 gacha), win-rate esa **27-29%** da qotib qoldi.

Bu — yettinchi to'plam va yettinchi marta shu raqam
o'zgarmadi. Ilgari o'zgargani faqat TP1 nisbat poli edi
(natija #8, #9), va u ham chiqish tomonida.

Xulosa o'zgarmadi va endi u ancha kuchliroq asosga ega:

> **Kirish tanlovi tasodifdan yaxshi emas, va uni filtrlash
> bilan tuzatib bo'lmaydi.** Etti xil filtr sinaldi. Hech biri
> "yaxshi" savdoni "yomon"idan ajrata olmadi.
