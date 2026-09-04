# Zanjir natijasi #3 — TUZATILGAN ablatsiya bilan qayta o'lchov

Sana: 2026-09-04 (kechqurun)
Actions yugurishi: 33823240410 (`olchov: hammasi`)
Coinlar: 12 ta, 730 kun, xarajat 0.3%/savdo

Natija #2 dagi ablatsiya mexanizmi buzuq edi
(`BACKTEST_NATIJA_2026-09-04_zanjir2.md`, 2-bo'limdagi ⛔ blok).
Mexanizm tuzatilgach HAMMA o'lchov qaytadan yuritildi. Bu hujjat —
ishonchli raqamlar.

---

## 1. Zanjirning chuqurligi — ENG MUHIM JADVAL

| Variant | Savdo | Foydali | PF | O'rt. savdo | Jami | Pasayish |
|---|---|---|---|---|---|---|
| to'liq zanjir (4 blok) | 277 | 68.2% | 3.50 | +2.78% | +770% | **28.2%** |
| 11 bo'sh tekshiruvsiz | 194 | 61.3% | **2.80** | +2.49% | +483% | 28.2% |
| tasdiqlashsiz (3 blok) | 374 | 69.3% | **3.95** | +3.06% | +1143% | 35.2% |
| faqat fundamental+struktura | 374 | 69.3% | 3.95 | +3.06% | +1143% | 35.2% |
| zanjirsiz — faqat darajalar | 474 | 62.4% | 3.05 | +2.43% | +1153% | **54.8%** |

Bu besh qatorda uchta javob bor.

---

## 2. ⛔ PROMPTNING QOIDASI SHU YERDA ISHLAMADI

Prompt (8-qism, 3-band) aytadi: **|ΔPF| < 0.03 bo'lgan tekshiruv
olib tashlanadi.** Ablatsiya 11 ta shunday tekshiruvni topdi.

Ularni BIRGA o'chirib o'lchadik:

    to'liq zanjir       277 savdo   PF 3.50
    11 tasiz            194 savdo   PF 2.80    ← YOMONROQ

Ya'ni qoidani so'zma-so'z bajarish tizimni **yomonlashtiradi**.

### Nega bunday — sabab aniq

Blok `kuch >= 1` da o'tadi: 4 tadan bittasi yetadi. Bitta
tekshiruvni o'chirish blokni deyarli o'zgartirmaydi (qolganlari
o'tkazadi). Lekin 3 tasini birga o'chirish blokni **qattiqroq**
qiladi:

    Zona bloki, oldin:  fib YOKI OB YOKI FVG YOKI VP  → 4 dan 1 ta yetadi
    Zona bloki, keyin:  faqat fib                     → fib bo'lmasa blok YIQILADI

Voronka buni raqam bilan tasdiqlaydi: Struktura to'sig'i
**4074 → 5477** ga o'sdi.

**Xulosa: "bo'sh" tekshiruvlar bo'sh emas — ular BLOKNI OCHIQ
USHLAB TURADI.** Ular alohida qaror qilmaydi, lekin birgalikda
blokni yumshoq qiladi.

### Bu qoidani BUZISH degani emas

Prompt qoidasining maqsadi — murakkablikni ushlab qolmaslik. Bu
o'z kuchida. Lekin qoida "PF ni o'zgartirmagan narsa keraksiz"
degan taxminga asoslangan edi, va o'lchov bu taxminni RAD ETDI.

Shuning uchun 11 ta tekshiruv **O'CHIRILMADI** va qaror admin
bilan muhokamaga qo'yildi (prompt, 8-qism: "raqam yo'q joyda
qaror qabul qilinmaydi" — bu yerda raqam bor va u qoidaga qarshi).

---

## 3. 4-BLOK (Tasdiqlash) NATIJANI YOMONLASHTIRADI

| Variant | Savdo | PF | Pasayish |
|---|---|---|---|
| to'liq zanjir (4 blok) | 277 | 3.50 | 28.2% |
| **tasdiqlashsiz (3 blok)** | **374** | **3.95** | 35.2% |

Tasdiqlash bloki 2399 nomzodni to'sadi. Uni o'chirsak savdo soni
35% ga oshadi VA PF 3.50 dan 3.95 ga ko'tariladi.

Ya'ni 4-blok **o'rtacha yaxshi savdolarni to'syapti.** Bu — 16 ta
o'lchovlik eski tizimning saboqi qaytarilgani: "yana bitta
tekshiruv qo'shaylik" degan fikr ko'pincha natijani buzadi.

Lekin bitta narsa qarama-qarshi: pasayish 28.2% dan 35.2% ga
o'sadi. 4-blok **PF ni pasaytiradi, lekin yo'lni tekislaydi.**
Bu — qaror, o'lchov emas: qaysi biri muhimroq?

---

## 4. 3-BLOK (Zona Sifati) HECH NARSA QILMAYDI

    tasdiqlashsiz (3 blok)         374 savdo   PF 3.95
    faqat fundamental+struktura    374 savdo   PF 3.95

**Raqamma-raqam bir xil.** Zona Sifati bloki 6440 nomzoddan
atigi **15 tasini** to'sgan.

Sabab: Fibonacci deyarli har doim topiladi, va 1/4 qoidasi ostida
u yolg'iz blokni o'tkazadi. Ya'ni blok bor, lekin darvoza vazifasi
yo'q.

DIQQAT: bu "zona keraksiz" degani EMAS. Zona bloki **zonaning
o'zini** topadi va Entry/Stop/TP o'sha zonadan quriladi. U
darvoza sifatida ishlamaydi, lekin **o'lchagich** sifatida
zarur.

---

## 5. USTUNLIK QAYERDA — javob topildi

Natija #2 da gipoteza qo'yilgan edi: "ehtimol ustunlik zanjirda
emas, DARAJALARDA". O'lchandi:

| Variant | Savdo | PF | Pasayish |
|---|---|---|---|
| zanjirsiz — faqat darajalar | 474 | 3.05 | **54.8%** |
| to'liq zanjir | 277 | 3.50 | **28.2%** |

**Gipoteza QISMAN tasdiqlandi, qismon rad etildi.**

Darajalarning o'zi (zona ichida kirish, zona tagida stop,
strukturaviy TP) **PF 3.05** beradi — ya'ni ustunlikning katta
qismi haqiqatan shu yerda.

Lekin zanjir bekorga turgani yo'q: u pasayishni **54.8% dan
28.2% ga**, ya'ni deyarli ikki barobar kamaytiradi. Bu — eng
muhim raqam, chunki real hisobda 55% pasayish ko'p odamni
strategiyadan chiqarib yuboradi.

**Zanjir foydani emas, XAVFNI boshqaradi.** Bu — kutilmagan,
lekin foydali javob.

---

## 6. Ablatsiya — birma-bir (tuzatilgan mexanizm)

Tayanch: 277 savdo, PF 3.50

| # | Tekshiruv | O'chirilganda savdo | PF | ΔPF |
|---|---|---|---|---|
| 1.1 | bozor holati | 277 | 3.50 | +0.00 |
| 1.2 | pul oqimi | 277 | 3.50 | +0.00 |
| 1.3 | katalizator | 277 | 3.50 | +0.00 |
| 1.4 | kayfiyat | 277 | 3.50 | +0.00 |
| 2.1 | swing ketma-ketligi | 276 | 3.53 | +0.03 |
| 2.2 | BOS tasdiqlangan | 277 | 3.50 | +0.00 |
| 2.3 | qarshi CHOCH yo'q | 277 | 3.50 | +0.00 |
| 2.4 | **nisbiy kuch** | 239 | **4.15** | **+0.65** |
| 3.1 | **fibonacci** | 180 | **4.03** | **+0.53** |
| 3.2 | order block | 277 | 3.50 | +0.00 |
| 3.3 | FVG | 277 | 3.50 | +0.00 |
| 3.4 | volume profile | 277 | 3.50 | +0.00 |
| 4.1 | liquidity sweep | 275 | 3.52 | +0.03 |
| 4.2 | pastki TF | **74** | 3.56 | +0.06 |
| 4.3 | RSI/divergensiya | 266 | 3.59 | +0.09 |
| 4.4 | fundamental mos | 277 | 3.50 | +0.00 |

Hech bir tekshiruv PF ni OSHIRMAYDI. Bu xulosa natija #2 dagi
bilan bir xil — lekin endi u TUZATILGAN asbob bilan olingan,
ya'ni ishonchli.

DIQQAT: 4.2 (pastki TF) o'chirilganda savdo 277 dan **74** ga
tushadi. Ya'ni bu tekshiruv 200 dan ortiq savdoni YOLG'IZ ochib
turgan — u blokdagi yagona ijobiy tekshiruv bo'lgan holat ko'p.
Uni "hissa qo'shmaydi" deb o'chirish xato bo'lardi.

---

## 7. Chegara va walk-forward — o'zgarmadi

| Chegara | Savdo | PF |
|---|---|---|
| stop 0.5% | 523 | 3.63 |
| stop 1.0% | 372 | 3.43 |
| **stop 1.5% (hozirgi)** | **277** | **3.50** |
| stop 2.0% | 211 | 3.16 |
| stop 3.0% | 111 | 1.80 |
| nisbat 1.0 | 339 | 3.39 |
| nisbat 1.5 | 237 | 3.51 |
| nisbat 2.0 | 114 | 2.64 |

Walk-forward (3 kesishmaydigan oyna):

    121 / 87 / 96 savdo
    PF 3.48 → 4.10 → 2.90
    bitta savdoda +3.18% → +3.15% → +1.86%
    🟡 barcha oynada PF ≥ 1.0, ustunlik 17% toraygan

**To'xtash qoidasi ishga tushmadi.**

---

## 8. Sig'im — o'zgarmadi

    sig'imsiz   277 savdo   PF 3.50   pasayish 28.2%
    sig'im bilan 208 savdo  PF 3.54   pasayish 33.5%
    to'sgan: 144 × korrelyatsiya, 1 × max_open_signals

---

## 9. ADMIN QARORI KUTILMOQDA — uchta savol

Prompt aytadi: "natija noaniq yoki kutilmagan bo'lsa —
davom etishdan oldin admin bilan aniq raqamlar bilan muhokama
qil, taxmin qilib oldinga ketma."

Natija kutilmagan chiqdi. Uchta qaror MENIKI EMAS:

### Savol 1 — 11 ta "bo'sh" tekshiruv o'chirilsinmi?

    O'chirilsa:  194 savdo, PF 2.80   (YOMONROQ)
    Qolsa:       277 savdo, PF 3.50

Promptning qoidasi "o'chir" deydi, o'lchov "qoldir" deydi.
Mening tavsiyam: **QOLDIRILSIN**, va qoidaga izoh qo'shilsin —
"o'lchov qoidadan ustun".

### Savol 2 — 4-blok (Tasdiqlash) olib tashlansinmi?

    Bilan:  277 savdo, PF 3.50, pasayish 28.2%
    Bilansiz: 374 savdo, PF 3.95, pasayish 35.2%

Ko'proq foyda va ko'proq signal — LEKIN chuqurroq pasayish.
Bu — didga emas, MAQSADGA bog'liq qaror. Mening tavsiyam:
**hozircha QOLSIN**, chunki 28.2% pasayish obunachi uchun
35.2% dan yaxshiroq va farq (0.45 PF) uchta oynada takrorlanishi
tekshirilmagan.

### Savol 3 — blok qoidasi 1/4 dan 2/4 ga o'zgartirilsinmi?

Bu 🔴 O'LCHANMAGAN. Yangi qoida — yangi o'lchov kerak.
Mening tavsiyam: **oldin o'lchansin**, keyin qaror.

---

## 10. Hech narsa jonliga chiqmaydi

Yuqoridagi uchta savol hal bo'lmaguncha modul jonli signal
bermaydi. Bu — 2-promptning qoidasi va u buzilmaydi.
