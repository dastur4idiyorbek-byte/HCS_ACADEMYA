# Zanjir natijasi #1 — yangi tahlil moduli birinchi marta o'lchandi

**Sana:** 2026-09-03
**Ma'lumot:** BTC, ETH, SOL, BNB, XRP · 730 kun · kunlik + 15 daqiqalik
**Xarajat:** har savdoda 0.3% (komissiya 0.1% × 2 + sirg'anish 0.05% × 2)
**Yugurishlar:** Actions #3 (backtest+ablatsiya+WF), #5 (chegara),
#6 va #7 (walk-forward, nomzod chegaralar bilan)

> Bu — YANGI arxitekturaning birinchi o'lchovi. Eski tizimning 16
> to'plami bilan SOLISHTIRILMAYDI: ular boshqa modulga tegishli
> (`OLCHOVLAR_XULOSASI.md`). Yagona umumiy raqam — tayanch.

---

## 1. Birinchi yugurish: zanjir ishlaydi, lekin deyarli jim

| Konfiguratsiya | Signal | Foydali | PF | O'rt.% | Jami% |
|---|---|---|---|---|---|
| to'liq zanjir (4 blok) | 35 | 48.6% | 1.83 | +2.10 | +73.5 |
| tasdiqlashsiz (3 blok) | 48 | — | 3.01 | — | — |
| faqat fundamental+struktura | 48 | — | — | — | — |

730 kunda 35 savdo — oyiga bittadan kam. To'xtash qoidasi 100 talab
qiladi, ya'ni PF 1.83 **hech narsani isbotlamaydi**.

Ablatsiya ham shu sababdan ma'nosiz chiqdi: 16 tadan 14 tasi PF ni
0.00 o'zgartirdi. 35 savdoda bitta savdo PF ni 0.1 dan ko'p
qimirlatadi — ya'ni "hissa qo'shmaydi" degan gap tasodifdan farq
qilmaydi. Skript endi bunday holatda xulosa chiqarmaydi.

---

## 2. Voronka sababni ANIQ ko'rsatdi

```
Zanjir qayerda uzildi:
    1563 × Struktura
    1232 × Tasdiqlash
       4 × Zona Sifati

Zanjir TO'LIQ, lekin daraja rad etildi:
     868 × stop juda yaqin              <- ENG KATTA to'siq
     420 × narx zonadan pastga tushgan
     182 × TP1/Stop nisbati past
```

`stop_eng_kam_pct = 3.0` — men qo'ygan **taxminiy** raqam. U
zanjir to'liq bog'langan holatlarning yarmidan ko'pini tashlab
yuborardi. Bu 2-promptning 3-tamoyilining buzilishi edi: "har
qanday raqamli chegara backtest orqali TOPILADI".

---

## 3. Chegara o'lchandi — 3.0 noto'g'ri raqam edi

| Chegara | Signal | Foydali | PF | O'rt.% | Jami% | Pasayish |
|---|---|---|---|---|---|---|
| **0.5%** | **195** | 65.1% | **3.26** | +1.74 | +340.1 | 20.4% |
| 1.0% | 124 | 62.9% | 2.89 | +1.96 | +243.3 | 23.3% |
| **1.5%** | 82 | 67.1% | **3.17** | **+2.68** | +219.5 | 21.8% |
| 2.0% | 59 | 64.4% | 2.47 | +2.38 | +140.2 | 33.8% |
| 3.0% (eski) | 35 | 48.6% | 1.83 | +2.10 | +73.5 | 30.7% |

TP1/Stop nisbati alohida sinaldi va u yerda hozirgi 1.2 eng yaxshi
qoldi (1.0 → PF 1.86, 1.5 → 2.11 lekin 31 savdo, 2.0 → 9 savdo).

Uch tomon ham bir yo'nalishda: chegara pasayganda savdo KO'PAYDI,
PF O'SDI, pasayish KAMAYDI.

---

## 4. Walk-forward — hal qiluvchi tekshiruv

Parametr izlash natijasini o'sha oynada maqtash — o'zini aldash.
Eski loyihaning eng achchiq saboqi aynan shu edi.

### stop = 0.5%

| Oyna | Signal | Foydali | PF | O'rt.% | Pasayish |
|---|---|---|---|---|---|
| 2024-02 → 2024-12 | 79 | 62.0% | 3.18 | +2.14 | 20.4% |
| 2024-12 → 2025-10 | 62 | 64.5% | 3.07 | +1.81 | 22.4% |
| 2025-10 → 2026-09 | 79 | 67.1% | 2.78 | +1.05 | 7.8% |

### stop = 1.5%

| Oyna | Signal | Foydali | PF | O'rt.% | Pasayish |
|---|---|---|---|---|---|
| 2024-02 → 2024-12 | 42 | 66.7% | 3.37 | +3.25 | 21.8% |
| 2024-12 → 2025-10 | 34 | 67.6% | 2.90 | +2.49 | 21.4% |
| 2025-10 → 2026-09 | 28 | 71.4% | 2.44 | +1.29 | 6.5% |

**Ikkalasida ham uchala kesishmaydigan oynada PF ≥ 2.44.**

Eski tizim bilan farq shu yerda ko'rinadi:

```
ESKI:   1.00 → 0.84 → 0.69     ustunlik YO'QOLADI
YANGI:  3.37 → 2.90 → 2.44     ustunlik BOR, lekin torayadi
```

---

## 5. ⚠️ Ustunlik torayyapti — bu yashirilmaydi

Bitta savdodagi natija PF dan TEZROQ pasayadi:

```
stop 0.5%:   +2.14% → +1.81% → +1.05%    (51% pasayish)
stop 1.5%:   +3.25% → +2.49% → +1.29%    (60% pasayish)
```

Ikkala qatorda ham yo'nalish bitta tomonga. Bu "moslashgan"
degani EMAS — uchala oyna ham foydali. Lekin jonli kuzatuvda
BIRINCHI NAVBATDA shu qator tekshiriladi.

---

## 6. QAROR: chegara 3.0 → 1.5

`config/default.yaml` da `stop_eng_kam_pct` **1.5** qilindi.

**1.5 tanlandi, 0.5 emas — va bu O'LCHOV emas, MUHANDISLIK qarori.**

0.5% chegarasida:

    xavf     0.5%
    xarajat  0.3%      <- xavfning 60% i
    qolgani  0.2%

Backtest sirg'anishni QAT'IY 0.3% deb modellaydi. Jonli bozorda
tez harakatda stop ancha yomon narxda bajariladi va o'sha
ustunlikning katta qismi modelning ICHIDA qolib ketadi — bozorda
emas. 1.5% da xavf xarajatdan besh barobar katta, ya'ni natija
modelning eng zaif taxminiga kamroq bog'liq.

Qaror QAYTARILADIGAN: `config/default.yaml` dagi bitta qatorni
almashtirish yetarli.

---

## 7. Nimaga hali ISHONMASLIK kerak

Raqamlar chiroyli, va aynan shuning uchun ularga shubha bilan
qarash kerak. To'rtta aniq zaiflik:

1. **`jami%` — portfel daromadi EMAS.** U 195 ta savdo natijasining
   YIG'INDISI, qat'iy pozitsiya hajmi bilan. "+340%" hisob uch
   barobar oshdi degani emas.

2. **Sig'im va korrelyatsiya o'lchovda YO'Q.** `risk_engine`
   ataylab chetda qoldirilgan (zanjirning O'Z sifatini o'lchash
   uchun). Jonli tizimda `max_open_signals = 5` bu 195 savdoning
   bir qismini kesadi.

3. **1-blok deyarli o'lchanmagan.** Fundamental manbalarning
   yarmida tarix yo'q (`FUNDAMENTAL_MALUMOT_MANBALARI.md`), ya'ni
   bu aslida 3 BLOKLI natija.

4. **Ablatsiya hali qilinmagan.** 35 savdoli yugurishda u ma'nosiz
   edi. Yangi chegarada (82-195 savdo) uni QAYTA yuritish kerak —
   va aynan u qaysi tekshiruvlar bo'sh ekanini aytadi.

---

## 8. Keyingi qadamlar — tartib bilan

1. **Ablatsiyani yangi chegarada qayta yuritish** (82+ savdo bilan
   endi ma'noli). Hissa qo'shmaydigan tekshiruvlar olib tashlanadi.
2. **`risk_engine` bilan birga o'lchash** — sig'im nechta signalni
   kesishini ko'rish.
3. Faqat shundan keyin — admin bilan jonliga chiqarish rejasi,
   **kichik pozitsiya bilan** (2-prompt, 8-qism, 7-band).

To'xtash qoidasi ISHGA TUSHMADI: PF ≥ 1.0 uchala oynada, 100+
savdo bilan (0.5% da 195, walk-forwardda har oynada 28-79).
