# Backtest natijasi #6 — NOLINCHI NUQTA

**Ma'lumot:** BTC, ETH, SOL, BNB, XRP | 730 kun tahlil + 427 kun isinish
**Qadam:** 6 942 yuklandi, **4 412 tahlil qilindi**
**Kod:** `ab764e0` | GitHub Actions run #9

> Beshta backtest/jonli farqi tuzatilgandan keyingi BIRINCHI o'lchov.
> Bundan keyingi taqqoslashlar shu jadval bilan qilinadi. Run #7 va
> #8 bilan solishtirilmaydi — ular boshqa (buzuq) o'lchov ostida
> olingan.

---

## Jadval

| variant | signal | savdo | win | TP2 gacha | **o'rt.%** | jami% | pasayish |
|---|---|---|---|---|---|---|---|
| **hozirgi holat** | 884 | 866 | **37.3%** | **30.0%** | **−0.75** | −649.8 | 659.8% |
| kunlik trend majburiy | 610 | 582 | 37.3% | 29.4% | −0.68 | −397.8 | 400.6% |
| indikator tasdig'i majburiy | 841 | 823 | 36.9% | 30.4% | −0.71 | −584.1 | 593.6% |
| faqat kuchli trend (ADX 25) | 821 | 804 | 39.1% | 30.7% | −0.66 | −532.4 | 570.9% |
| faqat chuqur Discount (40%) | 838 | 816 | 37.0% | 28.6% | −0.81 | −661.3 | 670.9% |

```
Tayanch — olib ushlab turish: +31.5%
⚠️ Strategiya HECH NARSA QILMASLIKDAN yomon ishlagan.   (beshta variantda ham)
```

---

## 1. O'lchov TUZALDI — indeks tirildi

Isinish tuzatilgandan keyin indeks endi 26-32 bandida qotib
turmaydi: signal soni **389 dan 884 ga** ko'tarildi. Ya'ni tizim
endi haqiqatan ishlayapti va biz uning ishini ko'ryapmiz.

| | run #8 (o'lik indeks) | run #9 (tirik indeks) |
|---|---|---|
| Signal | 389 | **884** |
| Win-rate | 32.1% | **37.3%** |
| TP2 gacha | 26.1% | **30.0%** |
| O'rtacha savdo | −1.04% | **−0.75%** |

Har bir ko'rsatkich yaxshilandi. **Jami natija esa yomonlashdi:**
−394.5% dan −661.3% ga. Sabab oddiy — savdo soni ikki barobardan
ko'p oshdi.

Zarar keltiruvchi ishni yaxshiroq bajarish, ko'proq bajarilsa,
ko'proq zarar keltiradi.

---

## 2. Diqqat: ikkita xato bir-birini QOPLAB turgan

Run #7 raqamlari (noto'g'ri ADX, o'lik indeks) run #9 raqamlariga
juda yaqin:

| | run #7 (ikkita xato) | run #9 (xatosiz) |
|---|---|---|
| Signal | 667 | 884 |
| Win-rate | 37.9% | 37.3% |
| TP2 gacha | 29.9% | 30.0% |
| O'rtacha savdo | −0.73% | −0.75% |

Bu tasodif emasga o'xshaydi: noto'g'ri ADX 4 soatlik qatordan
o'qilardi va u haftalikdan YUQORI chiqadi, ya'ni indeksni
ko'tarardi — o'lik kenglik omili tushirgan ballni qisman qaytarib
berardi.

**Buni biz o'lchamaganmiz.** Yuqoridagi izoh — taxmin, dalil emas.
Lekin u bitta narsani aniq ko'rsatadi: ikkita mustaqil xato bir-
birini qoplab, natijani "to'g'ri"ga o'xshatib qo'yishi mumkin. Shu
sababli "raqam ishonchli ko'rinyapti" hech qachon tekshiruv o'rnini
bosmaydi.

---

## 3. Asosiy xulosa O'ZGARMADI — endi u to'g'ri o'lchov ustida turibdi

### Tizim tasodifdan yomon

Tasodifiy kirish, stop S va nishon 1.5S bo'lsa:

```
S / (S + 1.5S) = 40%
```

| | TP2 gacha yetish |
|---|---|
| Tasodifiy kirish | **40%** |
| Tizim (to'g'ri o'lchov) | **30.0%** |

Tizim nomzodni tanlaydi, tahlil qiladi, ball qo'yadi, 13 qoidadan
o'tkazadi — va tanga tashlashdan yomonroq natija beradi.

### Filtrlar HALI HAM qimirlamaydi

| variant | win-rate |
|---|---|
| hozirgi holat | 37.3% |
| kunlik trend majburiy | 37.3% |
| indikator tasdig'i majburiy | 36.9% |
| faqat kuchli trend (ADX 25) | 39.1% |
| faqat chuqur Discount (40%) | 37.0% |

To'rtta mustaqil filtr, signal soni 610 dan 884 gacha, win-rate
**36.9–39.1%**. Eng katta farq 2.2 punkt.

Uchinchi gipoteza (kirish filtrlari) **rad etilgan holicha
qoladi** — endi to'g'ri o'lchov bilan tasdiqlangan.

### "Kunlik trend majburiy" yana aldamchi

U jami natija bo'yicha eng yaxshi ko'rinadi (−397.8%), lekin sabab
yana o'sha: **kamroq savdo** (610 vs 884). Bitta savdodagi farq
0.07 punkt, win-rate esa aynan bir xil — 37.3%.

---

## 4. Yangi ma'lumot: BALL SHIFTI

Voronkada ko'rinadigan raqam:

```
Chegaraga yetmagan nomzodlar: 7 584 ta
  eng yuqori ball: 55.0  |  o'rtacha: 44.3
```

Ikki yil, 22 mingdan ortiq nomzod — va **eng yuqori ball aynan
55.0**, ya'ni chegaraning o'zi. Yuqoriroq ball umuman chiqmagan.

Bu `test_chegara_erishiladi` topgan muammoning davomi: ball
funksiyasi 100 ballik shkalada o'lchanadi, lekin amalda 55 dan
yuqoriga chiqmaydi, chunki omillarning bir qismi bu strategiyada
bir vaqtda to'liq bo'la olmaydi.

Oqibati: "moslashuvchi chegara" amalda moslashmaydi. Yashil rejim
(55) va sariq rejim (50) orasidagi farq — nomzodlar taqsimotining
eng tepasidagi tor tasma.

Ya'ni ball SIFATNI emas, faqat TARTIBNI beradi. Retseptdagi
3-qadam ("Ball faqat tartiblaydi") aynan shu haqida edi, va endi
buning o'lchovi ham bor.

---

## 5. Nima o'lchandi, nima o'lchanmadi

**O'lchandi va yopildi:**

| gipoteza | natija |
|---|---|
| Correction Entry past bandda yordam beradi | ⚫ rad etildi |
| TP2 tuzilmadan olinsa yaxshiroq | ⚫ rad etildi |
| Kunlik trend majburiyligi sifatni oshiradi | ⚫ rad etildi |
| Indikator tasdig'i soxta kirishni kamaytiradi | ⚫ rad etildi |
| ADX 25 chegarasi sifatni oshiradi | ⚫ rad etildi |
| Chuqurroq Discount yaxshiroq kirish beradi | ⚫ rad etildi |

**Hali o'lchanmagan (🔴):**

- Bozor Salomatligi indeksi kalibrlanganmi — omil vaznlari,
  band chegaralari, ADX chegaralari. Indeks endi tirik, lekin
  u to'g'ri raqam beryaptimi degan savolga javob yo'q.
- Ball funksiyasining shifti (55) — u shunday bo'lishi kerakmi
  yoki omillar noto'g'ri vaznlanganmi.
- Nomzodga MUDDAT yo'qligi. O'rtacha ushlash 45.2 soat, bozor
  esa ikki yilda +31.5% o'sgan. Chiqish qoidasi faqat TP va
  Stop — vaqt bo'yicha chiqish umuman yo'q.

---

## 6. Xulosa

O'lchov endi to'g'ri. Xulosa esa o'sha-o'sha, faqat qattiqroq:

> Tizim tasodifiy kirishdan yomon ishlaydi va ko'tarilayotgan
> bozorda hech narsa qilmaslikdan ko'p zarar keltiradi.

Sozlama darajasida oltita urinish qilindi — oltitasi ham
ishlamadi. Muammo sozlamada emas, **mexanizmda**: sifat dalillari
faqat tartiblaydi, qaror qilish esa portfel holatiga qolgan.

Keyingi qadam sozlamani emas, mexanizmni o'zgartirishi kerak.
