# Natija #13 — ablation va walk-forward

**Sana:** 2026-09-03
**Yugurish:** GitHub Actions #16 (walk-forward) va #17 (ablation)
**Ma'lumot:** BTC, ETH, SOL, BNB, XRP · 730 kun · 4 soatlik · 427 kun isinish
**Xarajat:** har savdoda 0.3% (komissiya 0.1% × 2 + slippage 0.05% × 2)

Ikkita YANGI o'lchov turi qo'shildi. Ular gipoteza sinamaydi — ular
o'lchovning O'ZINI o'lchaydi:

    ablation      ball omillari haqiqatan hissa qo'shadimi
    walk-forward  sozlama tanlash keyingi davrda saqlanadimi

---

## 1. ABLATION — 60 ball hech narsa qilmayapti

Har bir omil ikki xil chiqarildi. Farqi muhim:

    "nol"          vazn 0, shkala 100 dan pasayadi.
                   Chegaradan o'tish qiyinlashadi, ya'ni SIGNAL SONI
                   ham o'zgaradi. Bu "omil yo'q bo'lsa" holati.

    "qayta taqsim" vazn 0, ulushi qolganlarga bo'linadi, shkala 100
                   qoladi. Chegara o'z ma'nosida turadi, ya'ni faqat
                   omilning MA'LUMOTI olib tashlanadi. Sof ablation.

### Sof ablation (shkala 100 qoladi)

| omil | signal | foydali | PF | o'rtacha | PF farqi |
|---|---|---|---|---|---|
| **TAYANCH** | 603 | 28.9% | **0.84** | −0.46% | — |
| S/R zonasi (25 ball) | 431 | 27.6% | 0.80 | −0.59% | **−0.04** |
| Risk/Reward (15 ball) | 574 | 27.7% | 0.77 | −0.67% | **−0.07** |
| MACD (10 ball) | 597 | 28.6% | 0.81 | −0.56% | −0.03 |
| RSI (15 ball) | 639 | 29.0% | 0.83 | −0.50% | −0.01 |
| Hajm (15 ball) | 600 | 29.5% | 0.83 | −0.50% | −0.01 |
| Trend (20 ball) | 611 | 29.5% | 0.83 | −0.47% | **−0.00** |

### Vazn olib tashlanganda (shkala pasayadi)

| omil | signal | foydali | PF | o'rtacha |
|---|---|---|---|---|
| TAYANCH | 603 | 28.9% | 0.84 | −0.46% |
| S/R zonasi → 75 shkala | **54** | 24.1% | 0.77 | −0.76% |
| Trend → 80 shkala | 451 | 26.2% | 0.71 | −0.87% |
| Risk/Reward → 85 shkala | 355 | 27.3% | 0.76 | −0.71% |
| RSI → 85 shkala | 518 | 28.8% | 0.83 | −0.50% |
| Hajm → 85 shkala | 450 | 27.8% | 0.82 | −0.51% |
| MACD → 90 shkala | 546 | 28.6% | 0.82 | −0.52% |

S/R chiqarilganda signal 603 dan **54** ga tushdi. Bu omilning
sifatini emas, CHEGARANI ko'rsatadi: 25 ball yo'qolganda ball 55
chegarasidan deyarli hech qachon o'ta olmaydi. Aynan shuning uchun
ikkinchi usul kerak edi — ansiz ablation omilni emas, chegarani
o'lchagan bo'lardi.

### Nima aniqlandi

**Faqat IKKI omil ma'lumot beradi: S/R zonasi (−0.04) va
Risk/Reward (−0.07).** Ikkalasining vazni jami 40 ball.

**Trend, RSI, Hajm va MACD — jami 60 ball — sof ablationda PF ni
0.00 dan 0.03 gacha o'zgartirdi.** Bu o'lchov shovqinidan farq
qilmaydi. Ya'ni ball tizimining uchdan ikki qismi nomzodlarni
tartiblashda deyarli hech narsa qilmayapti.

Diqqat: HECH BIR omil olib tashlanganda natija YAXSHILANMADI. Ya'ni
ular zarar ham keltirmayapti — shunchaki ta'sirsiz.

Bu 58-bo'limdagi qaror bilan mos: EMA olib tashlanganda ham hech
narsa yomonlashmagan edi. Endi raqam bor: kechikuvchi indikatorlar
(RSI, MACD, hajm) va trend o'lchovi bu strategiyada tartiblash uchun
ishlatilmayapti.

---

## 2. WALK-FORWARD — tanlov keyingi davrda saqlanmaydi

Tarix uch teng bo'lakka bo'lindi. Har bo'lakda 12 ta sozlama
sinalib PF bo'yicha eng yaxshisi tanlandi, so'ng o'sha tanlov
KEYINGI bo'lakda o'zgartirilmasdan qo'llandi. Yonma-yon TAYANCH —
hozirgi `config/default.yaml` — ham yuritildi.

| bo'lak | sana | sozlama | signal | foydali | PF | o'rtacha |
|---|---|---|---|---|---|---|
| 1 — o'rgatish | 2024-08-28 .. 2025-04-30 | diapazon 45% | 194 | 33.5% | **1.00** | +0.01% |
| 2 — tekshiruv | 2025-04-30 .. 2025-12-31 | o'sha 45% | 175 | 29.7% | **0.84** | −0.46% |
| 2 — tayanch | 2025-04-30 .. 2025-12-31 | hozirgi 55% | 188 | 29.3% | 0.83 | −0.48% |
| 3 — tekshiruv | 2025-12-31 .. 2026-09-02 | o'sha 45% | 199 | 27.6% | **0.69** | −0.76% |
| 3 — tayanch | 2025-12-31 .. 2026-09-02 | hozirgi 55% | 200 | 26.5% | 0.69 | −0.77% |

Ikkala bo'lakda ham tanlangan sozlama `entry_max_range_pct` 45%
bo'ldi (hozirgi 55% o'rniga), qolgan ikki parametr esa hozirgidek
qoldi.

### Nima aniqlandi

**Sozlama qidirish foyda bermaydi.** 12 nomzoddan eng yaxshisi
keyingi davrda tayanchdan +0.01 va −0.00 punkt farq qildi. Ya'ni
backtestda "eng yaxshi" deb topilgan sozlama keyingi davrda hech
narsani yaxshilamaydi.

**Hozirgi sozlama moslashib qolmagan.** Bu ijobiy xabar: tayanch
qidiruv g'olibi bilan amalda teng, ya'ni oldingi qarorlar tarixga
moslab tanlanmagan.

**Natija vaqt bo'yicha yomonlashyapti:**

    1-davr (2024-08 → 2025-04)   PF 1.00   foydali 33.5%
    2-davr (2025-04 → 2025-12)   PF 0.84   foydali 29.7%
    3-davr (2025-12 → 2026-09)   PF 0.69   foydali 27.6%

Uch davrda ham pastga. Bitta davrni tasodif deyish mumkin edi,
uchtasi ketma-ket esa yo'nalish. Bu YANGI 🔴: strategiya bozor
xarakteri o'zgarganda ergashmayaptimi, yoki 2024-yilgi ko'tarilish
faqat qulay sharoit bo'lganmi.

`docs/BACKTEST_NATIJA_2026-09-02_9.md` dagi "oyna B (2022-09 →
2024-09) PF 1.01" ham shu chiziqqa tushadi: eski davrlarda
yaxshiroq, yangi davrlarda yomonroq.

---

## 3. Ikkalasi birga nima deydi

Oldingi o'n ikki o'lchov "qaysi qoida yaxshiroq" deb so'ragan edi.
Bu ikkitasi boshqa savolga javob berdi va javob bir xil chiqdi:
**tanlash qatlamining o'zi ishlamayapti.**

    ablation      ballning 60 punkti tartiblashga hissa qo'shmaydi
    walk-forward  sozlama tanlash keyingi davrga o'tmaydi

Ikkalasi ham bitta narsani aytadi: nomzodlar orasidan "eng yaxshisi"
ni tanlash mexanizmi haqiqiy ustunlik bermayapti. Bu natija #12
bilan ham mos — u yerda ikkita butunlay boshqa KIRISH mexanizmi
bir xil natija bergan edi.

## 4. Keyingi savollar (o'lchanmagan)

1. To'rt ta'sirsiz omil (trend, RSI, hajm, MACD) BIR VAQTDA olib
   tashlansa nima bo'ladi — ball faqat S/R va R/R dan iborat
   bo'lsa? Alohida-alohida ta'sirsiz bo'lish birga ham ta'sirsiz
   degani emas.
2. Natijaning uch davrda pasayishi bozorning o'zgarishimi yoki
   strategiyaning eskirishimi?
3. `entry_max_range_pct` 45% ikkala o'rgatish bo'lagida ham
   tanlandi, lekin ustunlik 0.01 punkt. Bu sozlamani o'zgartirish
   uchun asos EMAS.

---

## 5. Audit 2-bosqichidan keyingi o'lchov (Actions #16)

Ulanmagan bayroqlar ulangach o'lchov takrorlandi. Tayanch — o'sha
oyna, o'sha coinlar, o'sha 4 412 tahlil qadami.

| | signal | foydali | PF | o'rtacha | jami | pasayish |
|---|---|---|---|---|---|---|
| oldin (natija #12) | 603 | 28.9% | 0.84 | −0.46% | −277.7 | 451.3% |
| **keyin (2-bosqich)** | **593** | **28.8%** | **0.84** | **−0.45%** | **−269.5** | **445.1%** |

**Farq deyarli yo'q.** 10 ta signal kamaydi, qolgan hamma raqam
o'z joyida. Ya'ni beshta ulanmagan bayroq natijaga ta'sir
qilmaydigan joylarda yotgan ekan.

Bu YOMON XABAR EMAS: bayroqlar endi haqiqatan ishlaydi va voronka
haqiqatni ko'rsatadi. Lekin ular tizimni foydali qilmadi.

### Voronka birinchi marta to'liq ko'rinmoqda

    Bosqich          Kirdi     Rad   O'tdi   O'tish
    market_health    21240     205   21035    99.0%
    zone_position    21035   10439   10596    50.4%
    threshold        10596    5928    4668    44.1%
    risk_engine       4668    4075     593    12.7%
    -> SIGNAL                          593

Ilgari bu jadval faqat to'rtta kalitni bilardi va `market_health`
qatori umuman ko'rinmasdi.

**Eng katta yo'qotish `risk_engine` da: 4 668 nomzoddan 593 tasi
o'tdi (12.7%).** Sababi esa strategiya emas — sig'im:

    3540 x risk_engine:max_open_signals
     317 x risk_engine:correlation

Ya'ni nomzodlarning ko'pi "yomon" bo'lgani uchun emas, **o'rin
qolmagani uchun** rad etilyapti (bir vaqtda 5 ta ochiq signal).

### YANGI 🔴 — `ZoneIntegrityRule` backtestda deyarli ishlamaydi

Qoida ulandi, lekin u eng ko'p rad etish sabablari ro'yxatiga
umuman kirmadi. Sababi tuzilmada:

    build_levels():  entry = zone_map.price   (JORIY narx)
    ZoneIntegrityRule: narx entry dan pastdami?

Kirish narxi signal qurilgan paytdagi JORIY narxga teng qilib
qo'yiladi, ya'ni masofa har doim nol. Qoida hech qachon ishlamaydi.

Bu yakka topilma emas — o'sha ildizdan yana bittasi chiqadi:

    entry_order.market_threshold_pct = 0.15%
    masofa har doim ~0  ->  har doim MARKET

Ya'ni LIMIT buyurtma tarmog'i ham amalda hech qachon
tanlanmaydi. "Narx zonaga qaytganda avtomatik bajariladi" degan
xatti-harakat mavjud emas.

| Holat | Savol |
|---|---|
| 🔴 | Kirish narxi joriy narx bo'lishi kerakmi yoki ZONANING o'zi bo'lishi kerakmi |

Bu 3-bosqichning 3.1 va 3.3 bandlariga bevosita tegishli: agar
kirish zona narxiga qo'yilsa, TP1 masofasi ham, Stop masofasi ham,
qoidalarning ishlashi ham o'zgaradi.
