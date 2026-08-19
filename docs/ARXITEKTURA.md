# Arxitektura qarorlari

Bu hujjat — spetsifikatsiyadagi talablar kodda **qayerda** amalga
oshirilganini ko'rsatuvchi xarita, va yo'l davomida qabul qilingan
qarorlarning sababi.

---

## 1. Nima uchun `core/` da `aiogram` importi yo'q

0.1-band talabi. Amalda bu shuni anglatadi:

- `core/` dagi hech bir modul Telegram tipini bilmaydi
- `bot/database.py` — bu shunchaki `core/storage` ustidan qayta-eksport,
  chunki bir xil sxemani tahlil sikli, backtest va kelajakdagi REST API ham
  ishlatadi
- Strategiyalar `StrategyInput` dan o'qiydi, Risk Engine `RiskContext` dan —
  ikkalasi ham oddiy dataclass. Shu sababli **bir xil kod jonli rejimda ham,
  backtestda ham ishlaydi** (6.3-band talabi tabiiy bajariladi)

Tekshirish:
```bash
grep -rn "aiogram" core/ && echo "QOIDA BUZILDI" || echo "toza"
```

---

## 2. Fail-safe qanday ta'minlangan (0.3-band)

Har bir risk qoidasi ma'lumot yetishmaganda **rad etadi**, ruxsat bermaydi:

| Holat | Natija |
|---|---|
| Bozor Salomatligi hisoblanmagan | signal yo'q |
| ADX / ATR hisoblanmagan | signal yo'q |
| BTC holati noma'lum | signal yo'q |
| Narx oqimi eskirgan (>90s) | signal yo'q |
| Qoida ichida kutilmagan xato | signal yo'q, xato log qilinadi, **tizim to'xtamaydi** |

Oxirgi qator muhim: `RiskEngine.evaluate()` har bir qoidani `try/except` ichida
chaqiradi. Bitta modulning nosozligi butun tizimni to'xtatmaydi, lekin natija
"ruxsat" bo'lib qolmaydi.

---

## 3. Nima uchun barcha rad sabablari yig'iladi

`RiskEngine` birinchi rad etishda to'xtamaydi — barcha qoidalarni tekshirib,
sabablarni to'playdi. Sabab: admin dashboardi "signal nega berilmadi?"
savoliga **to'liq** javob berishi kerak, bitta sabab emas. Bu 3.8-banddagi
postmortem tahlili uchun ham zarur.

---

## 4. Juma filtri: nima uchun alohida ehtiyot

4.8-band. Server UTC'da, filtr esa mahalliy vaqtga bog'liq — bir soatlik xato
savdo noo'rin to'xtashiga olib keladi.

Qabul qilingan qarorlar:
- `datetime.now()` (naive) **hech qayerda ishlatilmaydi**
- Vaqt `Clock` abstraksiyasi orqali olinadi — testda "muzlatiladi"
- `is_within_daily_window` naive vaqtni **rad etadi**, jim qabul qilmaydi
- Hafta kuni **mahalliy** vaqt zonasi bo'yicha aniqlanadi (UTC'da payshanba
  20:00 = Toshkentda juma 01:00)
- Chegara: `start <= t < end` — 15:00 oynadan tashqarida

Filtr faqat **yangi signal generatsiyasiga** ta'sir qiladi. Mavjud faol
signallar kuzatuvi Risk Engine'dan o'tmaydi — u boshqa qatlamda, shuning uchun
to'xtamaydi.

---

## 5. Spot savdo cheklovi (spetsifikatsiyada ko'rsatilmagan, lekin zarur)

5.1-banddagi formula:
```
Tavsiya etilgan miqdor = Xavf qilinadigan pul ÷ Stop masofasi (%)
```

3.3-band Stop masofasini **1% gacha** cheklaydi. $500 balans, 3% kunlik xavf
va 0.8% Stop bilan formula **$637 pozitsiya** beradi — balansdan katta. Spot
savdoda leverage yo'q, bu imkonsiz.

Yechim (uch bosqichli cheklov `core/position_sizing/sizer.py` da):
1. Bitta pozitsiya balansdan oshmaydi
2. Barcha ochiq pozitsiyalar **yig'indisi** ham balansdan oshmaydi
3. **Kapital ham xavf byudjeti kabi taqsimlanadi** — aks holda birinchi signal
   butun balansni band qilib, keyingilariga joy qoldirmaydi

Kesish **jim bo'lmaydi**: foydalanuvchi nima uchun kamroq miqdor tavsiya
etilganini va haqiqiy xavfi qancha ekanini ko'radi.

Natijada spot rejimda **kapital** cheklovchi omil bo'ladi, kunlik xavf
byudjeti emas — haqiqiy xavf kunlik limitdan ancha past chiqadi. Bu xavfsiz
tomon, 0.3-bandga mos.

---

## 6. Nima uchun `haram_list` va `mashbooh_list` bitta jadvalda

Spetsifikatsiya ikkita ro'yxatni eslatadi, lekin mantiq **bir xil**: ikkalasi
ham savdodan chetlatadi. Farq faqat sababda. Shuning uchun `coin_rulings`
jadvali `status` ustuni bilan — ro'yxatlar ajratilgan bo'lsa, "shubhali ham
harom kabi chetlanadi" qoidasi ikki joyda takrorlanardi va bir joyda
unutilishi mumkin edi.

Kod darajasidagi kafolat: `HalalStatus.is_tradable` faqat `HALAL` uchun `True`.

---

## 7. Konfiguratsiya qatlamlari

```
dataclass standartlari  ←  config/default.yaml  ←  DB (risk_config)  ←  env
     (eng past)                                                   (eng yuqori)
```

Ishga tushishda konfiguratsiya **tekshiriladi** (`core/config/loader.py`):
vaznlar yig'indisi, pog'onalar tartibi, noma'lum kalitlar, Juma vaqt formati.
Noto'g'ri sozlama bilan tizim ishga tushmaydi — signal berish paytida
buzilgandan ko'ra yaxshiroq.

---

## 8. Strategiya plug-in arxitekturasi

`core/analysis/strategies/base.py` — barcha strategiyalar uchun bitta
shartnoma. Yangi strategiya qo'shish uchun shu papkaga fayl qo'shish kifoya:

```python
class YangiStrategiya(Strategy):
    name = "yangi"
    @property
    def enabled(self) -> bool: ...
    def required_timeframes(self) -> list[str]: ...
    def analyze(self, data: StrategyInput) -> SignalCandidate | None: ...
```

Risk Engine barcha strategiyalarni bir xil chaqiradi — u strategiya turini
bilmaydi, faqat `SignalCandidate` ni ko'radi.

`analyze()` ning `None` qaytarishi **xato emas** — "hozir signal berish
to'g'ri emas" degani (0.2-band).

---

## 9. Indikatorlar: `pandas-ta` o'rniga o'z hisobimiz

6.3-band `pandas-ta` yoki `TA-Lib` ni eslatadi. Rejalashtirilgan yondashuv —
indikatorlarni `numpy`/`pandas` ustida bevosita hisoblash:

- `TA-Lib` C kutubxonasini talab qiladi (Oracle Cloud ARM'da o'rnatish
  muammoli)
- `pandas-ta` o'rnatish nizolari bilan mashhur va oxirgi paytda sust
  qo'llab-quvvatlanadi
- Indikatorlar (EMA, RSI, MACD, ATR, ADX) — bir necha o'nlab qator kod, va
  ularni o'zimiz yozsak **testdan o'tkaza olamiz**, bu esa 6.4-band talabi

Interfeys saqlanadi, shuning uchun kelajakda kutubxonaga o'tish oson.

---

## 10. Timeframe to'plami (3.2-band, tuzatilgan)

Dastlabki to'plam `1h → 4h → 1d → 1w → 1M` edi. U haddan tashqari katta —
haftalik va oylik shamlar bir xil trendni ko'rsatishini kutish signal
chastotasini deyarli nolga tushirardi.

Amaldagi standart to'plam:

```
15m → 30m → 1h → 4h → 1d
     ↑                  ↑
  kirish TF        tasdiqlovchi TF'lar
 (S/R + indikator)  (trend zid bo'lmasligi kerak)
```

Qat'iy qoida o'zgarmadi: signal faqat **barcha** yuqori timeframelar bir xil
trendni ko'rsatganda **va** eng pastki timeframeda S/R + indikatorlar
tasdiqlanganda beriladi.

Yuqori timeframelar (`1w`, `1M`) `analysis.positional_timeframes` da zaxirada
qoldirildi. Kelajakda pozitsion strategiya qo'shilsa, u ularni
`Strategy.required_timeframes()` orqali **o'zi e'lon qiladi** — plug-in
arxitekturasi buni allaqachon qo'llab-quvvatlaydi, konfiguratsiya
o'zgartirilmaydi.

---

## 11. Kirish buyurtmasi turi (5.1.0-band)

`core/analysis/entry_order.py` narx va Entry orasidagi masofaga qarab
avtomatik tanlaydi:

| Masofa | Buyurtma | Nima uchun |
|---|---|---|
| Narx Entry'dan yuqorida (> 0.15%) | **LIMIT** | narx zonaga kelganda avtomatik bajariladi |
| Narx zonada (±0.15%) | **MARKET** | kutish shart emas, signal shu daqiqada shakllanmoqda |
| Narx Entry'dan pastda (0.15–0.30%) | **LIMIT** | zona hali buzilmagan, buyurtma Entry'da qoladi |
| Narx Entry'dan pastda (> 0.30%) | **signal berilmaydi** | support zonasi ushlab tura olmadi |

Oxirgi qator spetsifikatsiyada ko'rsatilmagan, lekin amalda uchraydi: narx
kirish zonasini pastga kesib o'tgan bo'lsa, kirish asosi yo'qolgan. 0.3-band
(fail-safe) bo'yicha bunday holatda signal berilmaydi — `EntryPlan.is_valid`
`False` bo'ladi.

Chiqish har doim **OCO** (TP + Stop birgalikda) — u yerda tanlov yo'q.

Chegaralar `analysis.entry_order` da sozlanadi. Taqqoslashda `1e-9` epsilon
ishlatiladi: usiz `100.15` narxi `0.15%` chegarasiga tushmay qolardi (suzuvchi
nuqta `0.15000000000000568` beradi).

---

## 12. Vaqt saqlash: `UtcDateTime` (3-bosqichda chiqqan muammo)

SQLite vaqt zonasini **saqlamaydi**. `DateTime(timezone=True)` bo'lsa ham,
o'qishda naive `datetime` qaytadi. Oqibatlari:

1. Naive va aware vaqtni taqqoslash `TypeError` beradi (bu hali yaxshi —
   darhol ko'rinadi)
2. Bundan yomoni: mahalliy vaqt zonasiga bog'liq mantiq (4.8-band Juma
   filtri) jimgina noto'g'ri ishlashi mumkin

Yechim — `core/storage/base.py` dagi `UtcDateTime` `TypeDecorator`:

- **yozishda:** naive vaqt **rad etiladi**, aware vaqt UTC'ga keltiriladi
- **o'qishda:** naive vaqtga UTC belgisi qo'yiladi

Barcha vaqt ustunlari shu turdan foydalanadi. PostgreSQL'ga o'tilganda
xatti-harakat o'zgarmaydi.

---

## 13. Nima uchun repository'lar `core/` da

3-bosqichda handlerlar yozilganda tabiiy vasvasa — SQL so'rovlarni
handlerlarga yozish. Bunday qilinsa, mobil ilovaga o'tishda hammasi qayta
yozilardi.

Shuning uchun:

```
bot/handlers/     — faqat "ko'rsatish" (yupqa)
core/services/    — "nima qilinishi kerak" (biznes qaror)
core/storage/     — "qanday saqlanadi" (repository)
```

Masalan `SubscriptionService.approve_payment()` obunani faollashtiradi va
to'lovni belgilaydi — handler faqat natijani foydalanuvchiga yetkazadi.
Shu sababli obuna mantig'i Telegram'siz to'liq test qilinadi
(`tests/core/test_repositories.py`).

---

## 14. Narx sakrashi (gap) qanday talqin qilinadi

Narx bir nuqtadan ikkinchisiga sakrab o'tishi mumkin — masalan Entry'dan
to'g'ridan-to'g'ri Stop'dan pastga. Ikki talqin bor:

1. "Buyurtma bajarilmadi, biz kirmadik" — foydani oshirib ko'rsatadi
2. "Buyurtma Entry'da bajarilib, keyin Stop yedi" — ehtiyotkor

`SignalTracker` **ikkinchisini** tanlaydi (0.3-band). Statistika haqiqatdan
yomonroq ko'rinishi mumkin, lekin yaxshiroq ko'rinishidan afzal — 3.6-band
shaffoflik talabi ham shuni taqozo qiladi.

Shu sababli Stop tekshiruvi TP'dan **oldin** bajariladi.

---

## 15. Nima uchun kuzatuv qayta ishga tushirishda tiklanadi

`SignalWatcher.restore_from_database()` bot har ishga tushganda ochiq
signallarni bazadan o'qib, kuzatuvga qaytaradi. Ansiz server qayta
yuklangach barcha faol signallar "yo'qolardi" — foydalanuvchi TP yoki Stop
haqida xabar olmasdan qolardi.

Xuddi shu sababli `SignalWatcher` yangi signal qo'shilganda darhol
xabardor qilinadi (`add_signal`), keyingi qayta ishga tushirishni kutmaydi.

---

## 16. Kuzatuvchi nima uchun bunchalik "yupqa"

`bot/services/watcher.py` faqat ulab turadi:

```
narx oqimi -> SignalTracker -> hodisalar -> baza + Telegram
```

Barcha qaror `core/signals/tracker.py` da — u sof, tarmoqqa va Telegram'ga
bog'liq emas. Natijada:

- holat mashinasi 21 ta test bilan to'liq qamrab olingan
- kuzatuvchining o'zi soxta oqim va soxta bot bilan sinaladi
  (`tests/bot/test_watcher.py`) — haqiqiy tarmoq kerak emas
- backtest (16-bosqich) xuddi shu `SignalTracker` ni ishlatadi

---

## 17. S/R zonalarida qabul qilingan qarorlar

**Zona — nuqta emas, oraliq.** Bozor aniq bir narxda emas, tor oraliqda
buriladi. Bitta pivotdan iborat zona ham ATR asosida kengaytiriladi.

**Tekis cho'qqida faqat birinchi sham pivot deb olinadi.** Aks holda bir xil
balandlikdagi ketma-ket shamlar bir nechta bir xil pivot berardi va zona
sun'iy ravishda "ko'p test qilingan" ko'rinardi.

**Oxirgi `lookback` ta sham pivot bo'la olmaydi.** Ular hali o'ng tomondan
tasdiqlanmagan. Bu ataylab: tasdiqlanmagan cho'qqiga tayanish "kelajakka
qarash" (lookahead) xatosi bo'lardi va backtest natijalarini
soxtalashtirardi — 16-bosqichda bu xato butun sozlashni buzardi.

**Ketma-ket shamlar zonada turgani bitta test hisoblanadi.** Narx zonada 5
sham turgani "5 marta sinaldi" degani emas.

**ATR — o'lchov birligi, tasdiqlovchi indikator emas.** Zona kengligi va
narxgacha masofa ATR bilan o'lchanadi, shuning uchun coin $0.0004 yoki
$67 000 bo'lishidan qat'i nazar "yaqin" bir xil ma'no beradi. Tasdiqlovchi
indikatorlar (EMA, RSI, MACD, hajm) 7-bosqichda alohida qo'shiladi.

**Fibonacci zonalari alohida belgilanadi** (`from_fibonacci=True`). Yolg'iz
Fibonacci darajasi — hech qanday pivot tasdiqlamagan — zaif dalil, shuning
uchun ball hisoblashda (8-bosqich) pastroq baholanadi.

---

## 18. Discount / Premium zonalari (3.1-band davomi)

S/R diapazoni ikkiga bo'linadi va narxning nisbiy joylashuvi foizda
hisoblanadi:

```
Resistance  ───────────────  100%
                                    PREMIUM — narx QIMMAT
O'rta chiziq ─ ─ ─ ─ ─ ─ ─    50%
                                    DISCOUNT — narx ARZON
Support     ───────────────    0%
```

Qat'iy qoida: **kirish faqat "Support zonasida VA Discount zonada"** bo'lganda
ko'rib chiqiladi.

Nima uchun ikkala shart ham kerak — spetsifikatsiyadagi holat: oraliq juda
tor bo'lsa, narx Support zonasi **ichida** turgani holda ham diapazonning
yuqori yarmida (Premium'da) bo'lishi mumkin. Bunday kirish qimmat va
Resistance'gacha joy kam.

| narx | foiz | zona | Support ichida | kirish |
|---|---|---|---|---|
| 96 | 0% | Discount | ha | ✅ |
| 100 | 22% | Discount | yo'q | ❌ |
| 106 | 56% | Premium | ha | ❌ |
| 92 | −22% | — | ha | ❌ (zona buzilgan) |

**Tayanch nuqtalar — zona MARKAZLARI**, chekkalar emas. Chekkalarni olish
diapazonni zona kengligiga bog'liq qilib qo'yardi: keng zona diapazonni
sun'iy toraytirib, foizni buzardi.

**Diapazondan chiqish yashirilmaydi.** `percent < 0` — qo'llab-quvvatlash
buzilgan, `> 100` — qarshilik yorib o'tilgan. Ikkalasi ham muhim ma'lumot,
`0..100` ga siqib qo'yilmaydi.

`depth` (0..1) qiymati 3.5-banddagi "S/R zonasi sifati" ballida ishlatiladi:
chuqurroq Discount — yuqoriroq ball.

---

## 19. Indikatorlar: nima uchun ular hech qachon o'zicha signal bermaydi

`confirm()` funksiyasi `zone_ready` ni **kiruvchi shart** sifatida oladi:

```python
hukm = confirm(snapshot, config, zone_ready=zone_map.entry_allowed())
```

Agar `zone_ready=False` bo'lsa, indikatorlar qanchalik yaxshi bo'lmasin,
`is_confirmed` `False` qaytadi. Bu ataylab shunday tuzilgan: 3.1-band
"yolg'iz RSI 30dan past chiqdi kabi indikator-asosli signal YO'Q" deb aniq
belgilaydi, va bu qoida kod tuzilishining o'zida mustahkamlangan — uni
tasodifan chetlab o'tib bo'lmaydi.

---

## 20. Aniqlangan ziddiyat: qat'iy EMA talabi va "arzon joydan kirish"

3.1-band ikkita talabni birga qo'yadi:

1. **Trend:** narx **ikkala** EMA'dan yuqori bo'lishi shart
2. **Kirish:** narx Support zonasida va Discount zonada bo'lishi shart

Amalda bular bir-biriga qarshi ishlaydi. Support zonasiga qaytish
(pullback) deyarli har doim narxni EMA50 dan pastga tushiradi — aks holda
u support'ga yetib bormaydi.

Sinov (sun'iy ma'lumot, ko'tarilish trendi + support'ga qaytish, 12 ta
takrorlash):

| Talab | Trend tasdig'i |
|---|---|
| Qat'iy (`narx > EMA50` shart) | 0/12 |
| Yumshoq (`EMA50 > EMA200` va `narx > EMA200`) | 12/12 |

*Eslatma: sun'iy ma'lumot har doim pullback bilan tugaydi, shuning uchun
farq haqiqiy bozordagidan kattaroq ko'rinadi. Lekin tuzilmaviy ziddiyat
real.*

**Qabul qilingan yechim:** sozlanadigan bayroq
`analysis.indicators.trend_requires_price_above_fast`, standart qiymati
`true` — ya'ni **spetsifikatsiya bo'yicha qat'iy variant**. Uni o'zgartirish
loyiha egasining qarori, va 16-bosqichdagi backtest ikkala variantni real
ma'lumotda taqqoslab, javobni raqam bilan beradi.

---

## 21. 8-bosqichda aniqlangan uchta tuzilmaviy ziddiyat

Ball tizimini qurish jarayonida strategiyani sun'iy ma'lumotda uchdan-uchgacha
sinaganda uchta ziddiyat chiqdi. Uchalasi ham bir manbadan: **support'da sotib
olish barcha "trend davom etmoqda" ko'rsatkichlariga qarshi turadi.**

### 21.1. Toza trendda ustda qarshilik yo'q

3.1-band "TP1 — eng yaqin resistance" deydi. Lekin ko'tarilish trendi degani
aynan **yangi cho'qqilar** demakdir — ustda qarshilik zonasi yo'q.

Natijada tizim aynan trend filtri talab qiladigan sharoitda TP1 ni qura
olmasdi. Yechim: `trade_rules.allow_measured_tp` (standart `true`) —
qarshilik topilmasa TP1 o'lchangan masofa bo'yicha qo'yiladi va bu
`tp_from_structure=False` bilan ochiq belgilanadi.

### 21.2. Discount/Premium diapazoni ham ikkala zonani talab qilardi

Xuddi shu sabab bir qatlam yuqorida takrorlandi: diapazon qurilmasa,
Discount filtri umuman ishlamaydi.

Yechim: bir tomonda zona bo'lmasa, **oxirgi muhim swing darajasi** tayanch
sifatida ishlatiladi (`ZoneMap.swing_low` / `swing_high`). Treyderlar ham
trendda "joriy oyoq"ning (leg) diapazoniga qarab arzon/qimmatni baholaydi.

### 21.3. MACD tasdig'i va Discount oynasi kesishmaydi

Eng jiddiy topilma. O'lchov (sun'iy ma'lumot, turli chuqurlik va burilish
kombinatsiyalari):

| Burilish shamlari | Holat |
|---|---|
| 0–3 | Narx Discount'da ✅, lekin MACD tasdiqlamaydi ❌ |
| ≥4 | MACD tasdiqlaydi ✅, lekin narx Premium'ga o'tgan ❌ |

Sabab tuzilmaviy: MACD **kechikuvchi** indikator, u faqat narx allaqachon
ko'tarilgandan keyin tasdiqlaydi — o'sha paytda narx kirish zonasidan chiqib
ketgan bo'ladi.

**Yechim va uning asosi:** 3.5-band ball tizimini AYNAN shu uchun yaratgan —
indikatorlar ballga hissa qo'shadi, qarorni esa **umumiy ball chegarasi**
qabul qiladi. "4/4 indikator majburiy" talabi ball chegarasining ustiga
qo'yilgan ikkinchi to'siq edi.

Endi: `analysis.indicators.min_confirmations` (standart 2, 4 = qat'iy
variant). Zona sharti (S/R + Discount) MAJBURIY bo'lib qoladi, shuning uchun
"yolg'iz indikator-asosli signal yo'q" qoidasi buzilmaydi.

Bu qaror o'zini oqladi: sinovda MACD tasdiqlamagan nomzod **61.5/100** ball
oldi — bu eng past chegaradan (70) ham past, ya'ni signal baribir
yuborilmaydi. Ball tizimi zaif kirishni o'zi filtrlaydi, qattiq to'siqsiz.

---

## 22. Bozor Salomatligi Indeksi — nima uchun bitta raqam

3.7-band muammoni aniq qo'yadi: har omil alohida tekshirilsa, ular orasida
nomuvofiqlik chiqadi — bitta modul "bozor yaxshi" desa, boshqasi "balans
yo'q" deydi.

Yechim — besh omilni bitta 0-100 raqamga jamlash. Indeks uchta narsani
boshqaradi:

| Indeks | Rejim | Ball chegarasi (3.5) | Ochiq signal limiti (4.2) |
|---|---|---|---|
| 96 | 🟢 | 70 | 5 |
| 63 | 🟡 | 80 | 3 |
| 56 | 🟡 | 80 | 3 |
| 35 | 🔴 | yopiq | 0 |

**Ma'lumot yo'q bo'lganda har bir omil alohida qaror qiladi** — "ma'lumot
yo'q" har doim ham "yomon" degani emas:

| Omil | Ma'lumot yo'q | Sabab |
|---|---|---|
| BTC dominance | 0.0 | bozor holati noma'lum — ehtiyotkorlik |
| Trend kengligi | 0.0 | halol ro'yxat tahlil qilinmagan |
| Volatillik | 0.0 | tekis bozorni ajratib bo'lmaydi |
| **Sig'im** | **1.0** | foydalanuvchi yo'q — tizim o'zini cheklamasin |
| To'yinganlik | hisoblanadi | ochiq signal soni doim ma'lum |

Birinchi uchtasi nol bo'lgani uchun ma'lumotsiz indeks 40 dan past chiqadi
va signal berilmaydi — bu ataylab (0.3-band).

**Kunlik oldindan tahlilda boshqa omillar 0.5 (neytral)**, nol emas. Nol
qo'yilsa kun boshida tizim har doim "qizil" bo'lardi va hech qachon ishga
tushmasdi.

Eng ko'rgazmali holat — 5.2-banddagi "inson omili": bozor yaxshi (dominance
barqaror, 80% coin ko'tarilishda, ADX 38), lekin foydalanuvchilarning
10 tadan 9 tasi band. Indeks 63 ga tushadi va chegara qattiqlashadi —
tajribali treyderning *"odamlar allaqachon band, yana signal keraksiz"*
degan fikri avtomatlashtirildi.

---

## 23. Plug-in arxitekturasi sinovdan o'tdi (12-bosqich)

6.1-band "yangi strategiya qo'shish uchun bitta fayl kifoya" deb va'da
bergan edi. Skalping qo'shilganda bu tekshirildi. Natija:

| O'zgardi | O'zgarmadi |
|---|---|
| `opening_range_scalp.py` (yangi) | Risk Engine mantig'i |
| `registry.py` ga bitta qator | Signal kuzatuvchisi |
| Konfiguratsiya bo'limi | Ball chegarasi mexanizmi |
| | Bozor Salomatligi Indeksi |

Risk Engine strategiya turini **umuman bilmaydi** — u faqat
`SignalCandidate` ni ko'radi. Bitta istisno hujjatlashtirilgan (pastda).

### 23.1. Skalping ballari asosiy strategiyanikidan boshqa

S/R zonasi skalpingda yo'q, shuning uchun uning omillari ham boshqa:

| Omil | Vazn |
|---|---|
| Hajm sakrashi | 35 |
| Diapazon sifati | 25 |
| Yo'nalish aniqligi | 25 |
| Risk/Reward | 15 |

Yig'indi baribir 100 — shu sababli **bir xil ball chegarasi** ikkala
strategiyaga ham qo'llaniladi va ular halol taqqoslanadi.

### 23.2. Aniqlangan ziddiyat: universal TP oralig'i skalpingga to'g'ri kelmaydi

3.3-band TP ni **3–5%** deb belgilaydi. 3.9-band esa skalping **1–2%**
harakat kutishini aytadi. Bir xil chegara bilan tekshirilsa, skalping
signallari **har doim** rad etilardi — ya'ni spetsifikatsiyada talab
qilingan strategiya hech qachon ishlamasdi.

Yechim: `TradeRulesRule` strategiyaga qarab moslashadi
(`overrides[SignalSource]`). Muhim tafsilot — **Stop chegarasi (1%) barcha
strategiyalar uchun bir xil qoladi**: u kapital himoyasi, strategiya
xususiyati emas.

### 23.3. Alohida byudjet, lekin umumiy limit ichida

3.9-band ikkita talabni birga qo'yadi: "alohida risk byudjeti" va
"ikkalasi birga umumiy kunlik limitdan oshmasligi kerak".

`StrategyBudget` ikkalasini ham ta'minlaydi — u **mustaqil hisob
yuritmaydi**, asosiy byudjetdan ajratadi:

```
Umumiy byudjet $30  |  skalp ulushi $9
asosiy strategiya $28 oldi  ->  skalpda $2 qoldi (o'z ulushi $9 bo'lsa ham)
```

### 23.4. Stop nima uchun diapazon o'rtasida

Yorib o'tish muvaffaqiyatsiz bo'lsa narx odatda ochilish diapazoni ichiga
qaytadi. O'rtaga qaytish — "yorib o'tish yolg'on edi" degan aniq belgi, va
bu diapazon pastini kutishdan ko'ra **tezroq va arzonroq** chiqish.

---

## 24. Bosqichlar holati

| # | Bosqich | Holat |
|---|---|---|
| 1 | Arxitektura skeleti | ✅ |
| 2 | DB sxemasi (15 jadval) | ✅ |
| 3 | Bot "tana" qismi | ✅ |
| 4 | Halol skrining (Top 30 Halal) | ✅ |
| 5 | Signal moduli + WebSocket | ✅ |
| 6 | Support/Resistance | ✅ |
| 7 | Indikatorlar | ✅ |
| 8 | Ball hisoblash + reytinglash | ✅ |
| 9 | Risk Engine | ✅ (13 qoida) |
| 10 | Bozor Salomatligi Indeksi | ✅ |
| 11 | Pozitsiya hajmi + agregat balans | ✅ |
| 12 | Opening range scalp | ✅ |
| 13 | Postmortem (Signal Xotirasi) | DB tayyor |
| 14 | Shaxsiy portfel | DB tayyor |
| 15 | Hammasini bog'lash | — |
| 16 | Backtest (1-2 yillik) | — |
| 17 | Test va sozlash | davomiy |
