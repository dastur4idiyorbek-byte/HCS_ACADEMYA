# ML/AI ishimiz — to'liq hisobot

**Kim uchun:** bu loyihaga YANGI kelgan odam yoki yangi Claude
sessiyasi uchun. Hech narsani oldindan bilish shart emas.

**Sana:** 2026-09-10
**Holat:** ish TUGADI, javob OLINDI, avtomatik signal TO'XTATILDI

---

## 0. Bir gapda

Sun'iy intellektdan (XGBoost) "bizning signallarimiz haqiqatan
ishlaydimi" deb so'radik. Javob: **yo'q**. Model 16 486 ta
savdodan o'rgandi va foyda beradigan birorta qoida topa olmadi.
Shundan keyin avtomatik signal to'xtatildi.

---

## 1. Muammo qayerdan boshlandi

Loyiha egasi ekran suratini yubordi: signallar ro'yxatida
**90% ga yaqin coin "Bekor qilingan"** va bir xil coinlar bir xil
foizlar bilan o'nlab marta takrorlanardi.

Ikkita haqiqiy xato topildi va tuzatildi:

1. **TP1 narxdan ORQADA** — tizim "sotib ol, 104 da sot" deb
   signal berardi, narx esa allaqachon 106 edi. Signal
   tug'ilishidayoq o'lik edi.
   (`core/position/entry_stop_tp.py` — `nishon_narxdan_yuqori`)

2. **Bir zona qayta-qayta signal berardi** — sikl 4 soatda bir
   marta yuradi, struktura esa o'shancha vaqtda o'zgarmaydi.
   Signal yopilishi bilan o'sha coin darrov yana "bo'sh" bo'lib
   qolardi va aynan o'sha signal qaytadan tug'ilardi.
   (`core/services/zanjir_sikl.py` — `_bir_xil_daraja`)

Bular tuzatildi. **Lekin ularni o'lchaganda ancha kattaroq
haqiqat ochildi.**

---

## 2. Uchta o'lchov — hammasi bir xil javob berdi

### 2.1 Ablatsiya

16 ta ichki tekshiruvni birma-bir olib tashlab ko'rdik.
**Birortasi ham natijani sezilarli yaxshilamadi va
yomonlashtirmadi.** Ya'ni tekshiruvlar ishlamayapti.

### 2.2 Zanjirsiz solishtiruv

| nima | savdo | PF |
|---|---|---|
| To'liq zanjir (4 blok) | 153 | 0.83 |
| Zanjir UMUMAN yo'q | 310 | **0.84** |

Zanjir — bizning butun tahlil modulimiz — **saralamayapti**.
Uni butunlay o'chirib qo'ysak, natija bir xil (hatto arzimas
darajada yaxshiroq).

> PF (Profit Factor) — yutgan pulning yutqazgan pulga nisbati.
> 1.0 dan past = zarar. 0.83 = har 1$ zararga 0.83$ foyda.

### 2.3 Chegara supurgisi

Nishonni (TP1) uzoqlashtirib ko'rdik:

| nisbat | g'alaba foizi | PF |
|---|---|---|
| 1.2 | 29.7% | 0.90 |
| 2.0 | 18.9% | 0.78 |
| 3.0 | 16.7% | 0.89 |

Nishon 1.67 barobar uzoqlashganda g'alaba foizi 1.57 barobar
tushdi — **deyarli aynan mutanosib**. PF esa 0.78–0.90 da qotib
qoldi.

**Bu tasodifiy kirishning imzosi.** Agar kirishimizda ustunlik
bo'lganida, uzoqroq nishon ko'proq foyda berardi. Bu yerda esa
faqat ehtimollik ishlaydi.

---

## 3. Nega XGBoost kerak bo'ldi

Yuqoridagi uchta o'lchov "qoidalarimiz ishlamayapti" dedi. Lekin
bir savol ochiq qoldi:

> Balki qoidalar noto'g'ri qo'yilgandir? Balki ma'lumotimizda
> ustunlik BOR, biz uni topa olmayapmizmi?

Bu savolga odam javob bera olmaydi — variantlar juda ko'p.
Mashina esa bera oladi.

### XGBoost nima (oddiy tilda)

Bu — "qora quti" emas. U minglab kichik **if-else** shartlar
daraxtini quradi:

    agar stop_pct < 3 VA nisbat > 1.5 VA fvg bor
        -> ehtimol yutadi

Va eng muhimi: u **qaysi omil qanchalik ishlatilgani**ni
ro'yxat qilib beradi (feature importance). Ya'ni bizning
"ablatsiya" ishimizni **avtomatik** bajaradi.

---

## 4. Nima qurildi

### 4.1 Dataset (`scripts/zanjir_dataset.py`)

Har bir nomzod — bitta qator. Uchta qat'iy qoida:

1. **Kelajakka qaramaslik.** Har bir qator faqat o'sha
   paytgacha mavjud shamlardan quriladi.
2. **Yakuni jonli tizim bilan bir xil hisoblanadi** —
   backtest motorining aynan o'sha funksiyasi ishlatiladi.
3. **Zanjir filtri YO'Q.** Zanjirdan o'tmagan nomzodlar ham
   olinadi, zanjirning o'z xulosasi esa **ustun** bo'ladi,
   filtr emas. Ansiz model faqat 66 ta qator ko'rardi va
   shovqinni yodlab olardi.

Natija: **16 486 qator, 56 ustun, 24 halol coin, 4 yil.**

| yakun | soni | ulush |
|---|---|---|
| bekor (limit bajarilmadi) | 10 883 | 66.0% |
| stop | 4 482 | 27.2% |
| tp | 1 014 | 6.2% |
| muddat | 107 | 0.6% |

### 4.2 Model (`scripts/zanjir_model.py`)

**Walk-forward** — tasodifiy bo'lish EMAS:

    1-oyna:  [o'rgatish........][imtihon]
    2-oyna:  [o'rgatish.............][imtihon]
    3-oyna:  [o'rgatish..................][imtihon]

Imtihon oynasi DOIM o'rgatishdan KEYIN keladi. Vaqt qatorida
tasodifiy bo'lish — eng keng tarqalgan va eng qimmat xato:
model kelasi haftani o'tgan haftadan o'rganib qo'yadi va
imtihonda "a'lo" chiqadi.

Baholash **sof pul** bilan, "aniqlik foizi" bilan emas: 66%
qator `bekor` bo'lgani uchun "hech narsa qilma" degan model
ham 66% aniqlik olardi.

### 4.3 Kutubxona masalasi

`numpy`/`pandas`/`xgboost` ~100 MB va serverda kerak emas.
Shuning uchun ular `requirements-ml.txt` da — **faqat GitHub
Actions da** o'rnatiladi. Server bularsiz ishlaydi.

---

## 5. MENING IKKITA XATOM

Bu bo'lim ataylab yozildi. Ikkalasi ham **o'lchovni yolg'on
qilib ko'rsatgan** xatolar edi.

### 5.1 Noto'g'ri savol (1-yugurish)

Modelga bergan yorlig'im: `yutdi = natija_pct > 0`, ya'ni
**"musbat tugadimi?"**.

Model bunga 68% aniqlik bilan javob berdi — lekin pul yo'qotdi
(PF 0.59). Sabab:

    +0.2% lik mayda g'alaba × 10 ta  =  +2%
    −4.0% lik to'liq stop   ×  3 ta  = −12%

"Musbat" va "foydali" bir xil emas. Model **to'g'ri narsani**
o'rgandi, men **noto'g'ri narsani** so'radim.

Tuzatish: ikkinchi model qo'shildi — u to'g'ridan-to'g'ri
kutilayotgan **foizni** bashorat qiladi (`reg:squarederror`).

### 5.2 Imtihondan keyin chegara tanlash (2-yugurish)

Skript "🟢 Model 4/4 oynada tayanchdan yaxshi, jonli sinovga
tayyorlash" deb chiqardi.

**Bu yolg'on edi.** Xulosa kodi har bir oynaning ENG YAXSHI
chegarasini tanlardi — **imtihon natijasini ko'rgandan keyin**:

| oyna | tanlangan chegara | natija |
|---|---|---|
| 1 | foyda ≥ 1.5% | +8.1% |
| 2 | foyda ≥ 0.0% | +102.4% |
| 3 | foyda ≥ 0.0% | −22.0% |
| 4 | foyda ≥ 2.0% | −46.7% |

Har oynada **boshqa** chegara. Jonli savdoda chegara
**oldindan** qo'yiladi — ya'ni bu natijaga erishib bo'lmasdi.

Bundan tashqari shart ham noto'g'ri edi: "tayanchdan yaxshi"
deb baholanardi, "foydali" deb emas.

Ikkalasi ham tuzatildi va regressiya testi yozildi
(`tests/core/test_zanjir_model.py`).

**Sabog'i:** o'lchov kodining o'zi ham xato qilishi mumkin, va
uning xatosi eng xavflisi — chunki u sizga **yashil chiroq**
ko'rsatadi.

---

## 6. HAQIQIY NATIJA

Bir xil chegara barcha oynalarda:

```
konfiguratsiya                savdo     jami%   musbat oyna
-----------------------------------------------------------
TAYANCH (hozirgi qoidalar)      162    -169.1        0/4
yutadimi >= 0.35               1832    -795.7        1/4
yutadimi >= 0.45               1269    -550.7        1/4
yutadimi >= 0.55                861    -523.8        0/4
yutadimi >= 0.65                504    -337.7        0/4
kutilgan foyda >= 0.0%         1215    -428.7        1/4
kutilgan foyda >= 0.5%          392    -296.4        1/4
kutilgan foyda >= 1.0%          206    -193.7        1/4
kutilgan foyda >= 1.5%          132     -94.8        2/4
kutilgan foyda >= 2.0%           90    -122.0        1/4
```

**Bitta ham konfiguratsiya foyda bermadi.**

Musbat natijalarning deyarli hammasi 2-oynada to'plangan —
bitta qulay bozor davri. Bu ustunlik emas, bu **ob-havo**.

### Ustunlar muhimligi

| ustun | ulush |
|---|---|
| `t_fvg` | 7.75% |
| `blok3_maxraj` | 5.80% |
| `nisbat` | 5.76% |
| `t_pastki_tf` | 4.09% |
| `tp_soni` | 4.01% |

Eng muhim ustun ham atigi **7.75%**. Kuchli signal bo'lganda
bitta-ikkita ustun 20–40% oladi. Bu yerda 51 ustun deyarli teng
bo'lingan — **model tayanadigan narsa topmadi**.

**Deyarli ishlatilmaganlar (18 ta):** `t_liquidity_sweep`,
butun `blok1_*` to'plami, `t_fundamental_mos`, `t_fibonacci`,
`t_bozor_holati`, `t_pul_oqimi`, `t_katalizator`, `t_kayfiyat`.

Ya'ni **Bozor Salomatligi Indeksi**, **LIT moduli** va butun
**1-blok** — modelga foydasiz chiqdi.

---

## 7. XULOSA

To'rtta **mustaqil** usul bir xil javob berdi:

| # | usul | javob |
|---|---|---|
| 1 | Ablatsiya | tekshiruvlar ta'sir qilmaydi |
| 2 | Zanjirsiz backtest | 0.84 va 0.83 — bir xil |
| 3 | Chegara supurgisi | kirish tasodifiy |
| 4 | XGBoost | foydali qoida yo'q |

**Ma'lumotimizda kelajak haqida ma'lumot yo'q.** Model buni
o'rgana olmadi — chunki o'rganadigan narsa yo'q.

Buning sababi ochiq ko'rinadi: **51 ustunning HAMMASI narxdan
olingan.** Narx grafigi o'zining kelajagini bilmaydi.

---

## 8. QANDAY QAROR QABUL QILINDI

2026-09-10 da loyiha egasi **avtomatik signalni to'xtatdi**.

**Nima to'xtadi:** faqat signal yozish
(`zanjir.avtomatik_signal = False`).

**Nima davom etadi:**
- sikl 4 soatda yugurishda davom etadi va har bir coin
  holatini `zanjir_holatlari` ga yozadi. To'xtatish davri ham
  ma'lumot beradi;
- mavjud ochiq signallar kuzatiladi (TP/Stop);
- admin panelidan qo'lda signal yozish ishlaydi.

Sayt va bot buni **ochiq ko'rsatadi** — zanjir oxirida
«TO'XTATILGAN» yorlig'i, voronkada alohida hisoblagich, adminga
xabar. Jim to'xtatish ekranni buzuq ko'rsatardi.

Uchta test bu qarorni qulflaydi
(`tests/core/test_zanjir_sikl.py`).

---

## 9. KEYINGI QADAM UCHUN UCHTA YO'L

Hech biri tanlanmagan — bu loyiha egasining qarori.

### 9.1 Yangi ma'lumot manbai

Hozirgi ustunlarning hammasi narxdan. Narx bilmagan narsa kerak:
- on-chain oqimlar (birjaga kirayotgan/chiqayotgan coin);
- birja zaxiralari;
- yangilik va kayfiyat.

Bu — eng ehtimolli yo'l, chunki muammoning **ildiziga** tegadi.

### 9.2 Boshqa savol

"Qaysi coin o'sadi" — juda qiyin savol. "Bozor qachon xavfli" —
osonroq va foydasi aniqroq. Ya'ni signal berish emas,
**kirmaslik** signali.

### 9.3 Signalsiz mahsulot

Loyihada signaldan tashqari qismlar bor: akademiya, halol
skrining, portfel hisobi, bozor ko'rinishi. Ular signalga
bog'liq emas va ishlashda davom etadi.

---

## 10. Fayllar

| fayl | nima |
|---|---|
| `scripts/zanjir_dataset.py` | dataset yig'adi (CSV) |
| `scripts/zanjir_model.py` | o'rgatish + walk-forward |
| `requirements-ml.txt` | ML kutubxonalari (faqat Actions) |
| `.github/workflows/zanjir.yml` | `olchov: dataset` va `olchov: model` |
| `tests/core/test_zanjir_dataset.py` | dataset qoidalari |
| `tests/core/test_zanjir_model.py` | tayanch + xulosa qorovuli |
| `docs/XGBOOST_REJA.md` | dastlabki reja |
| `docs/BACKTEST_NATIJA_2026-09-10_model.md` | 1-yugurish (noto'g'ri savol) |
| `docs/BACKTEST_NATIJA_2026-09-10_model2.md` | 2-yugurish (haqiqiy natija) |
| `docs/BACKTEST_NATIJA_2026-09-10_chegara.md` | chegara supurgisi |
| `docs/GIPOTEZA_DAFTARI.md` | o'lchanmagan raqamlar ro'yxati |

### Qayta yugurtirish

GitHub -> Actions -> "Zanjir o'lchovi" -> Run workflow:

    olchov:   model
    days:     1460
    symbols:  BTC,ETH,SOL,ADA,AVAX,LINK,DOT,ATOM,LTC,NEAR,ETC,FIL,
              ALGO,VET,XLM,HBAR,EOS,ICP,XTZ,IOTA,THETA,EGLD,GRT,BCH
