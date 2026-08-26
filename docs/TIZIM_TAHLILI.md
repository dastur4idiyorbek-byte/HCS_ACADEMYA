# HALOL CRYPTO SAVDO — tizim tahlili

**Maqsad:** bir hafta uzluksiz ishlagan bot bironta signal bermadi. Bu hujjat
nima qurilgani, nima ishlayotgani, nima uchun signal chiqmayotgani va qanday
muqobil yo'llar borligini raqamlar bilan bayon qiladi.

**Kim uchun:** tizimni birinchi marta ko'radigan mutaxassis uchun. Kodga kirish
shart emas — barcha kerakli raqamlar shu yerda.

> Bu hujjatdagi barcha raqamlar **o'lchangan**: jonli botning admin
> dashboardidan va kod ustida yurgizilgan kalibrlash skriptidan olingan.
> Taxmin qilingan joylar alohida belgilangan.

---

## 1. Bir sahifalik xulosa

| | |
|---|---|
| Kod hajmi | 16 139 satr (`core/` 11 610 + `bot/` 4 529) |
| Testlar | 658 ta test funksiyasi, 46 faylda — hammasi yashil |
| Ishlash muddati | ~1 hafta uzluksiz (Railway) |
| Tahlil qilingan coin | ~74 ta (150 mo'ljallangan, likvidlik filtri qisqartirgan) |
| Kuniga baholash | ~2 500–5 500 marta |
| **Chiqarilgan signal** | **0** |

**Asosiy xulosa:** muammo bitta sozlamada emas. Tizim **ketma-ket 4 ta
mustaqil filtrdan** iborat va ularning ko'paytmasi amalda nolga teng. Har bir
filtr alohida mantiqiy, lekin birgalikda ular "hech qachon" degan javob
beradi.

Qo'shimcha: bir hafta davomida ikkita **to'sar xato** ham bor edi (quyida
2.3-bo'lim) — ular tuzatildi, lekin ular tuzatilgandan keyin ham asosiy
savol qoladi: **filtrlar ko'paytmasi juda tor**.

---

## 2. Tizim nima

### 2.1 Arxitektura

Ikki qatlam, qat'iy ajratilgan:

```
core/   — "miya": tahlil, qaror, baza. Telegramni BILMAYDI (0 ta aiogram importi)
bot/    — "tana": Telegram interfeysi, fon vazifalari
```

Bu ajratish tekshirilgan va haqiqiy: `core/` ni veb-saytga yoki mobil ilovaga
o'zgarishsiz ulash mumkin.

### 2.2 Modullar

| Modul | Satr | Vazifasi | Holati |
|---|---|---|---|
| `core/analysis` | 3 846 | S/R zonalar, indikatorlar, ball, strategiyalar | ishlaydi, sinalmagan |
| `core/storage` | 1 687 | 15 jadval, migratsiyalar | ishlaydi |
| `core/config` | 846 | Qatlamli sozlama (dataclass ← YAML ← baza ← env) | ishlaydi |
| `core/domain` | 830 | Sof modellar, enumlar | ishlaydi |
| `core/backtest` | 805 | Tarixiy sinov mexanizmi | **hech qachon haqiqiy ma'lumotda ishlatilmagan** |
| `core/market_data` | 759 | Binance OHLCV + WebSocket, CoinGecko/CMC reyting | ishlaydi |
| `core/risk_engine` | 714 | 13 ta majburiy qoida | ishlaydi (juda qattiq) |
| `core/pipeline` | 571 | Sikl: skrining → strategiya → ball → risk | ishlaydi |
| `core/position_sizing` | 482 | Pozitsiya hajmi, agregat sig'im | **hech qachon ishlatilmagan** |
| `core/signals` | 346 | Holat mashinasi (kutilmoqda→faol→TP/Stop) | **hech qachon ishlatilmagan** |
| `core/halal_screening` | 264 | Halol coin filtri | ishlaydi, **diniy tekshiruvdan o'tmagan** |
| `bot/handlers` | 2 105 | Telegram ekranlari | ishlaydi |
| `bot/services` | 1 176 | Sikl yurituvchi, narx kuzatuvchi, jadval | ishlaydi |

### 2.3 Savdo mantiqi (asosiy strategiya `classic_ta`)

Falsafa: **"arzon paytda ol"** — narx qo'llab-quvvatlash zonasiga qaytganda
xarid qilish.

```
1. Halol coinlar ro'yxati (kapitalizatsiya + likvidlik + diniy filtr)
2. 1 soatlik shamlarda Support/Resistance zonalari topiladi
3. Narx support zonasiga YAQIN (<=1 ATR) va diapazonning pastki qismida (<=55%)
4. Stop support ostiga qo'yiladi; Stop 1-5%, TP 3-20%, nisbat >= 1:3 bo'lishi SHART
5. Ball hisoblanadi (S/R 25 + trend 20 + RSI 15 + hajm 15 + MACD 10 + R/R 15)
6. Ball chegaradan o'tsa -> Risk Engine (13 qoida) -> signal
```

Ikkinchi strategiya `opening_range_scalp`: kunlik ochilish shamining
diapazoni buzilishida kirish.

---

## 3. Signal yo'li — o'lchangan voronka

Oxirgi 24 soatdagi haqiqiy raqamlar (`classic_ta` strategiyasi):

| Bosqich | Kirdi | Rad etildi | O'tdi | O'tish |
|---|---|---|---|---|
| Zona joylashuvi | 1345 | 605 | 740 | 55.0% |
| Darajalar (Stop/TP/nisbat) | 740 | 146 | 594 | 80.3% |
| Ball chegarasi | 594 | 488 | 106 | 17.8% |
| **Risk Engine** | **106** | **106** | **0** | **0.0%** |

**Risk Engine'gacha yetish ehtimoli: 7.9%. Undan o'tish: 0%.**

### Muhim ogohlantirish raqamlar haqida

Dashboard **baholashni** sanaydi, **imkoniyatni** emas. Sikl har soatda
ishlaydi (kuniga 24 marta), ya'ni support zonasida 6 soat turgan coin
6 marta sanaladi.

Haqiqiy tasvir: **kuniga ~4.4 ta alohida coin** Risk Engine'gacha yetadi.
Ya'ni tanlov doirasi ko'ringanidan ancha tor.

---

## 4. Nima uchun signal yo'q — uch daraja

### 4.1 Birinchi daraja: to'sar xatolar (tuzatildi)

**A. Deadlock — tizim o'z-o'zini bloklagan.**

```
Ochiq signal yo'q
  → narx oqimi (WebSocket) faqat OCHIQ SIGNALLAR coinlariga obuna bo'ladi
  → obuna bo'sh → narx keshi bo'sh → narx yoshi noma'lum
  → Risk Engine "narx holati noma'lum" deb bloklaydi
  → yangi signal yo'q → ochiq signal yo'q
```

Aylana yopiq edi. Tizim bir marta 0 ta ochiq signalga tushsa **abadiy shu
yerda qolardi** — ya'ni birinchi signalini hech qachon chiqara olmasdi.
Nechta nomzod topishidan qat'i nazar.

Sabab: signal qarori **shamdan** olingan narxga tayanadi, tekshirilayotgani
esa **tik oqimi** edi. Ya'ni ishlatilmaydigan ma'lumotning holati so'ralardi.

**B. Ball chegarasi erishib bo'lmas edi.**

Chegara 70/80 qo'yilgan edi. Kalibrlash skripti 27 ta turli sifatdagi
sozlamada o'lchadi:

```
Erishish mumkin bo'lgan ENG YUQORI ball : 59.7
Chegara                                  : 80
Chegaradan o'tganlar                     : 0 / 12
```

Ball funksiyasi 100 ga chiqmaydi, chunki omillarning bir qismi bu
strategiyada **bir vaqtda to'liq bo'la olmaydi**: support'da xarid qilinganda
MACD hali kesmagan bo'ladi (0/10), RSI o'rta zonada bo'ladi (7.5/15), R/R
aynan eng kam talabda bo'ladi (7.5/15). Chegara 50/55 ga tushirildi.

### 4.2 Ikkinchi daraja: filtrlar ko'paytmasi

Bu **hali hal qilinmagan** va asosiy savol shu.

Har bir filtr alohida mantiqiy:

| Filtr | Talab | Alohida mantiqiy? |
|---|---|---|
| Halol | diniy + likvidlik ($50M/kun) | ha |
| Zona | narx support'ga <=1 ATR **va** diapazonning <=55% ida | ha |
| Stop | 1%–5% oralig'ida | ha |
| TP | 3%–20% oralig'ida | ha |
| Nisbat | **kamida 1:3** | ha |
| Ball | >= 55/100 | ha |
| Risk Engine | 13 ta qoidaning **hammasi** ruxsat bersin | ha |

Lekin bular **"VA"** mantig'i bilan bog'langan. 7 ta shartning ko'paytmasi.
Kuniga ~4 ta coin oxirgi qatlamgacha yetadi, keyin 13 ta qoida ularni ham
to'xtatadi.

**Eng qattiq talab — 1:3 nisbat.** Bu Stop 2% bo'lsa TP2 kamida 6% bo'lishini
talab qiladi. 1 soatlik grafikda bunday harakat kam uchraydi.

### 4.3 Uchinchi daraja: dizayn falsafasi

Tizim **0.2-band** ("signal bermaslik xato emas") va **0.3-band**
(fail-safe: noaniqlikda signal berma) tamoyillari ustiga qurilgan.

Bu tamoyillar to'g'ri, lekin ular **bir tomonga og'gan**: har bir noaniqlik,
har bir yetishmagan ma'lumot, har bir chegaradagi holat — hammasi "yo'q"
tomonga hal qilinadi. 15+ joyda shunday qaror bor.

Natijada tizim **hech qachon xato signal bermaydi** — lekin **hech qanday
signal ham bermaydi**. Ikkinchisi ham xato, faqat u ko'rinmaydi.

---

## 5. Takrorlangan xato naqshi — 7 marta

Loyihada bir xil turdagi xato **yetti marta** topildi:

> **Bir shkala uchun to'g'ri bo'lgan qiymat boshqa shkalaga qo'llangan.**

| # | Qayerda | Xato |
|---|---|---|
| 1 | EMA ajralishi | bitta coin uchun 5% chegarasi 15m ga qo'llangan |
| 2 | ADX | bitta coin uchun 40 chegarasi 30 coin o'rtachasiga qo'llangan |
| 3 | Narx > EMA50 | kirish qoidasi rejim tasnifiga qo'llangan |
| 4 | Narx > EMA50 | xuddi shu, bozor kengligi hisobida |
| 5 | Sokinlik dashboardi | sikl darajasi va coin darajasi bitta maxrajga qo'shilgan |
| 6 | Ball chegarasi | 0–100 shkalasi uchun raqam 0–60 shkalasiga qo'llangan |
| 7 | **Stop chegarasi** | **1% qat'iy foiz barcha coinlarga** |

7-si hali tuzatilmagan va jonli dashboardda ko'rinadi:

```
ETH: Support zonasi juda yaqin: Stop 0.42% da qolardi, ruxsat 1.0-5.0%
```

`min_stop_distance_pct: 1.0` — **qat'iy foiz**. Lekin uning maqsadi
"bozor shovqini Stop'ni yeb qo'ymasin". Shovqin esa **ATR** bilan
o'lchanadi, foiz bilan emas:

- BTC (ATR ~0.8%/soat): 1% stop = 1.2 ATR → mantiqiy
- Volatil altcoin (ATR ~3%/soat): 1% stop = 0.33 ATR → **juda tor**, shovqin yeydi
- Barqaror coin (ATR ~0.3%/soat): 1% stop = 3.3 ATR → **keraksiz keng**, yaxshi
  setuplarni rad etadi

Nima uchun bu naqsh takrorlanadi: **chegara qiymatlari kod yozilgan paytda
"mantiqiy eshitilgan" raqamlardan olingan, o'lchovdan emas.** "Stop 1% dan
yaqin bo'lmasin" tabiiy eshitiladi — lekin qaysi coinda, qaysi timeframeda?

---

## 6. Nima ISHLAYAPTI (haqqoniy baho)

Bu qismlar jonli sinovda o'zini ko'rsatdi:

- **Ma'lumot yig'ish.** 74 coin × 4 timeframe, chegaralangan parallellik,
  birjadan ban yo'q.
- **Halol skrining.** Ro'yxat quriladi, admin tahrirlashi mumkin.
- **S/R zonalar.** Zonalar topiladi, tafsilotlar mantiqiy
  ("narx diapazonning 69% ida").
- **Bozor Salomatligi Indeksi.** 5 omil, barqaror qiymat (70-73), tarix bilan.
- **Sokinlik dashboardi.** Bu — tizimning eng qimmatli qismi. Aynan u
  bosqichma-bosqich sabab ko'rsatib, yuqoridagi barcha topilmalarni
  ko'rsatdi.
- **Telegram interfeysi.** Obuna, to'lov, admin panel, signal kartochkasi.
- **Testlar.** 658 ta test. Ular xatolarni topdi (masalan i18n kalitlari,
  chegara erishilishi, HTML xavfsizligi).

## 7. Nima ISBOTLANMAGAN

Bu qismlar **bir marta ham haqiqiy ishlamagan**:

- **Signal chiqarish** — 0 marta
- **Signal kuzatuvi** (TP/Stop aniqlash) — 0 marta
- **Pozitsiya hajmi hisobi** — 0 marta
- **Portfel va statistika** — bo'sh
- **Postmortem hisoboti** — ma'lumot yo'q
- **Backtest** — mexanizm yozilgan, **haqiqiy tarixiy ma'lumotda hech qachon
  yurgizilmagan** (sinov muhitida tashqi tarmoq yopiq edi)
- **Halol ro'yxat** — bilimli kishi ko'rib chiqmagan

**Eng muhimi:** strategiyaning **foydali ekani hech narsa bilan
tasdiqlanmagan**. Biz uni hech qachon o'tgan ma'lumotda sinamaganmiz.

---

## 8. Muqobil yo'llar

### Variant A — Filtrlarni yumshatish (mavjud tizim ichida)

Nima o'zgaradi: 1:3 nisbat → 1:2; Stop chegarasi ATR birligiga; zona
kengligi 55% → 65%; Risk Engine qoidalarining bir qismi "to'siq" dan
"ball" ga o'tadi.

- ✅ Tez, kod tayyor
- ❌ **Taxminga tayangan** — qaysi filtr foydali ekanini bilmaymiz
- ❌ Signal keladi, lekin sifati noma'lum

### Variant B — Avval backtest, keyin qaror

Nima o'zgaradi: hech narsa. Avval 1-2 yillik tarixiy ma'lumotda mavjud
strategiya yurgiziladi.

- ✅ **Yagona yo'l**, unda qaror o'lchovga tayanadi
- ✅ Kod allaqachon yozilgan
- ✅ Har bir filtrni alohida yoqib/o'chirib solishtirish mumkin
- ❌ Natija "strategiya foydasiz" bo'lishi mumkin — lekin buni **hozir**
  bilish yaxshiroq

### Variant C — Strategiyani almashtirish

Hozirgi strategiya — **mean reversion** ("arzon paytda ol"). Muqobil:

| Strategiya | Mantiq | Signal chastotasi |
|---|---|---|
| Trend following | trend yo'nalishida kirish, kechikadi | o'rta |
| Breakout | diapazon buzilganda kirish | yuqori |
| Momentum reyting | eng kuchli N ta coin, davriy qayta balanslash | past, lekin muntazam |
| DCA / to'plash | belgilangan vaqtda xarid | juda yuqori |

Diqqat: **halol spot savdo** cheklovi kuchli — faqat xarid (long), shortsiz,
leverajsiz. Bu mean reversion va trend following uchun mos, lekin ko'p
klassik strategiyalarni chiqarib tashlaydi.

### Variant D — Ikki rejimli tizim

"Signal" tushunchasini ikkiga bo'lish:

- **Kuchli signal** (hozirgi qattiq filtrlar) — kam, ishonchli
- **Kuzatuv ro'yxati** (yumshoqroq filtrlar) — "shu coinlarga qarab turing"

Foydalanuvchi bo'sh ekran ko'rmaydi, lekin tizim ham yolg'on va'da bermaydi.

### Variant E — Vaqt oynasini kengaytirish

Hozir kirish timeframei 1 soat. 4 soatlik yoki kunlik grafikda:
- harakatlar kattaroq → 1:3 nisbat osonroq bajariladi
- signal kamroq, lekin **haqiqatan** bajariladigan bo'ladi
- savdo turi "kunlik" dan "pozitsion" ga o'zgaradi

---

## 9. Maslahat uchun aniq savollar

Bularga javob topilsa, keyingi qadam aniq bo'ladi:

1. **1:3 nisbat talabi 1 soatlik kripto grafigida realistikmi?**
   Agar yo'q bo'lsa — nisbatni pasaytirish kerakmi yoki timeframeni oshirish?

2. **7 ta ketma-ket "VA" filtri — bu normal dizaynmi?**
   Professional signal tizimlari nechta qattiq filtr ishlatadi? Qaysilari
   to'siq, qaysilari ball bo'lishi kerak?

3. **Stop masofasi qanday o'lchanishi kerak** — foizdami, ATR birligidami,
   yoki tuzilmaga (support ostiga) qarabmi?

4. **"Arzon paytda ol" (mean reversion) strategiyasi spot kripto uchun
   to'g'ri tanlovmi?** Yoki trend/breakout mosroqmi?

5. **Halol spot cheklovi (faqat long, leverajsiz) qaysi strategiyalarni
   real qiladi?**

6. **Backtestsiz jonli ishga tushirish qanchalik xavfli?** Biz hozir aynan
   shu holatdamiz.

7. **Kuniga nechta signal maqsad qilinishi kerak?** Bu raqamsiz "juda kam"
   yoki "yetarli" deb baho berib bo'lmaydi. Hozir maqsad belgilanmagan.

---

## 10. Tavsiya

Mening baholashimcha tartib shunday bo'lishi kerak:

1. **Avval o'lchash** (Variant B). Backtest kodi tayyor, faqat serverda
   yurgizish kerak:
   ```
   python -m scripts.backtest --compare --days 730
   ```
   Bu bir necha soatlik ish, lekin u **barcha qolgan savollarga javob
   beradi**: qaysi filtr foydali, qaysi biri shunchaki signal o'ldiradi.

2. **Keyin 7-xatoni tuzatish** (Stop chegarasi ATR birligiga) — bu
   o'lchovdan mustaqil, aniq xato.

3. **Keyin qaror**: mavjud strategiyani sozlash yoki almashtirish.

Filtrlarni o'lchovsiz yumshatish — bir hafta oldin qilingan xatoni
takrorlash bo'ladi: raqamlar "mantiqiy eshitilgani uchun" tanlanadi va
biz yana shu yerda o'tiramiz.

---

## Ilova: joriy sozlamalar

```
Halol ro'yxat     : 150 ta maqsad, $50M/kun likvidlik chegarasi (amalda ~74 coin)
Timeframe         : kirish 1h, tasdiq 4h, salomatlik 1d
S/R yaqinlik      : 1.0 ATR
Kirish zonasi     : diapazonning <= 55% i (0% = support, 100% = resistance)
Zona ishonchi     : kamida 2 marta teginish
Stop              : 1.0% .. 5.0%
TP                : 3.0% .. 20.0%
Nisbat            : TP2/Stop >= 1:3.0 ; TP1/Stop >= 1:1.5
Ball chegarasi    : 50 (bozor kuchli) / 55 (o'rtacha) / signal yo'q (zaif)
Ochiq signal      : 5 / 3 / 0 (salomatlikka qarab)
Skalping          : oyna kun bo'yi, hajm 2.0x, diapazon 0.15-1.2%

Risk Engine (13 qoida, hammasi "VA"):
  kill_switch, friday_prayer, market_health, consecutive_loss,
  daily_loss_limit, max_open_signals, correlation, btc_market,
  market_regime, volatility, fresh_data, halal, trade_rules
```

## Ilova: ball tizimi

```
S/R zonasi sifati   25 ball   (yaqinlik 35% + chuqurlik 35% + ishonch 30%)
Trend               20 ball   (EMA 30% + ADX 30% + yuqori TF 40%)
RSI                 15 ball
Hajm                15 ball   (o'rtachadan 2x = to'liq ball)
MACD                10 ball
Risk/Reward         15 ball
                   ---------
                   100 ball (nazariy)
                    ~60 ball (amalda erishilgan eng yuqori — o'lchangan)
```
