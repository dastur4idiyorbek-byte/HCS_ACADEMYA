# XGBoost 1-yugurish — model o'rgandi, lekin MEN noto'g'ri savol berdim

Sana: 2026-09-10 | Actions: 93360313675
16 486 qator, 51 ustun, 24 coin, 4 yil, 4 ta walk-forward oynasi

---

## 1. Natija

| Oyna | Tayanch | Eng yaxshi model |
|---|---|---|
| 1 | −2.0% (27 savdo) | −118.3% |
| 2 | −8.0% (23 savdo) | **+50.5%** |
| 3 | −52.2% (32 savdo) | −132.8% |
| 4 | −106.9% (80 savdo) | −178.6% |

🟡 Model 1/4 oynada yaxshi — **barqaror emas**.

---

## 2. LEKIN raqamlarda G'ALATILIK bor

Chegara ko'tarilganda **g'alaba foizi o'sadi, PF esa tushadi**:

| chegara | g'alaba | PF |
|---|---|---|
| 0.35 | 57.6% | 0.68 |
| 0.50 | 66.3% | 0.76 |
| 0.60 | **68.1%** | **0.59** |

68% g'alaba bilan PF 0.59 — bu qarama-qarshilik emas, **tashxis**.

### Sabab: MEN NOTO'G'RI SAVOL BERDIM

Modelga berilgan yorliq: `yutdi = natija_pct > 0`, ya'ni
**"musbat tugadimi?"**.

Model bu savolga **yaxshi javob berdi** — 68% aniqlik. Lekin
"musbat" va "foydali" bir xil emas:

    +0.2% lik mayda g'alaba  ×  10 ta   =  +2%
    −4.0% lik to'liq stop    ×   3 ta   =  −12%

Model mayda g'alabalarni to'plashni o'rgandi va katta zararni
qoplay olmadi. Ya'ni u o'rgangan narsa TO'G'RI, so'ralgan narsa
NOTO'G'RI edi.

Bu — modelning emas, **o'lchov qurgan odamning** xatosi.

### Tuzatildi

Endi IKKINCHI model qo'shildi: u to'g'ridan-to'g'ri **kutilayotgan
foiz**ni bashorat qiladi (`reg:squarederror`), ya'ni mayda
g'alaba katta zararni qoplamasligini o'zi hisobga oladi.

Ikkalasi bir yugurishda, yonma-yon o'lchanadi.

---

## 3. USTUNLAR MUHIMLIGI — bu qism ALLAQACHON qimmatli

| Ustun | Muhimlik |
|---|---|
| **narx_entry_farq_pct** | **19.3%** |
| t_alternativ_qosh_tub | 8.4% |
| stop_pct | 7.9% |
| t_alternativ_oldingi_swing | 5.2% |
| blok4_maxraj | 4.7% |

### Ikkita muhim xulosa

**1. Eng foydali ustun — hozirgi qoidalarda YO'Q.**

`narx_entry_farq_pct` = "narx entry'dan qancha yuqorida". Model
uni hammasidan ko'p ishlatdi (19.3%).

Bu maydonni men dataset uchun qo'shgandim va u hozirgi signal
qoidalarida **umuman ishlatilmaydi**. Aynan u limit
bajarilish ehtimolini bildiradi — ya'ni 66% "bekor" muammosining
o'zagi.

**2. `zanjir_toliq` — DEYARLI ISHLATILMAGAN.**

Zanjirning O'Z hukmi ("to'rtala blok o'tdimi") "ishlatilmaganlar"
ro'yxatida turibdi. Ular bilan birga:

    t_fundamental_mos, t_fibonacci, t_bozor_holati,
    t_katalizator, t_pul_oqimi, t_kayfiyat, t_qarshi_choch_yoq

Bu — **uchinchi mustaqil tasdiq**. Avval ablatsiya aytdi, keyin
"zanjirsiz 0.84 / to'liq zanjir 0.83" aytdi, endi model ham
o'sha ustunni umuman ochmadi.

**Alternativ yo'llar esa ISHLATILDI** (8.4% va 5.2%) — ular
haqiqatan ma'lumot tashiyapti.

---

## 4. Keyingi yugurish nima aytadi

Endi ikkita model yonma-yon:

* **"yutadimi"** — eski, noto'g'ri savol (solishtirish uchun qoladi)
* **"kutilgan foyda"** — to'g'ri savol

Agar ikkinchisi ham 4 oynadan hech qaysisida tayanchdan yaxshi
bo'lmasa — **ustunlarimizda kelajak haqida ma'lumot yo'q** degan
xulosa mustahkamlanadi va yangi ma'lumot manbai kerak bo'ladi.
