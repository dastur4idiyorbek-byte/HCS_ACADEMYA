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

## 24. Signal Xotirasi: naqsh va statistika farqi

3.8-band "statistika emas, **naqsh izlash**" deydi. Farq:

| | Misol |
|---|---|
| Statistika | "35% signal Stop yedi" |
| **Naqsh** | "Salomatlik 60dan past bo'lganda 79% Stop yeydi" |

Ikkinchisi **sababga** ishora qiladi va aniq harakat taklif qiladi.

### 24.1. Halollik chegarasi

Naqsh faqat namuna yetarli bo'lganda e'lon qilinadi. 5 ta signal asosida
"70% Stop yeydi" deyish statistika emas, shovqin. Har bir naqsh ikki
shartdan o'tishi kerak:

- `min_sample_size` — **har ikkala** guruhda alohida
- `min_effect_pct` — natijalar farqi shu foiz punktidan katta bo'lishi

Ma'lumoti yo'q signal (masalan salomatlik qayd etilmagan) **ikkala guruhga
ham kirmaydi** — noma'lum ma'lumot naqshni buzmasligi kerak.

### 24.2. "Naqsh topilmadi" ≠ "ma'lumot yetarli emas"

Hisobot bu ikkisini **ajratadi**. Kichik namunada:

> ℹ️ Namuna kichik (3 ta savdo, kamida 12 kerak) — naqsh izlanmadi.
> Bu "muammo yo'q" degani EMAS, shunchaki ma'lumot yetarli emas.

Aralashtirish xavfli bo'lardi: admin "hammasi joyida" deb o'ylab qolardi.

### 24.3. Nima uchun avtomatik o'zgartirish yo'q

Spetsifikatsiya buni aniq talab qiladi, va sabab jiddiy: tizim o'z
sozlamalarini o'zi o'zgartirsa, **xato naqsh butun strategiyani buzishi va
buni hech kim sezmasdan qolishi mumkin**. Har bir hisobot oxirida bu ochiq
yoziladi:

> ⚠️ Bu tavsiyalar AVTOMATIK qo'llanilmaydi. Sozlamani o'zgartirish qarori —
> sizniki.

### 24.4. "TP1 oldi, keyin Stop" alohida natija

`Outcome.TP1_THEN_STOP` — bu foyda hisoblanadi (pozitsiyaning bir qismi TP1
da yopilgan), lekin `Outcome.STOP` dan ajratiladi. Aralashtirilsa, naqsh
tahlili "Stop yedi" deb noto'g'ri xulosa chiqarardi.

Xuddi shunday, **bekor qilingan signal statistikaga kirmaydi** — u savdo
bo'lmagan va win-rate ni sun'iy buzardi.

---

## 25. Portfel: nima uchun qismli yopish kerak

5.4-band foydalanuvchining **real** foyda/zararini hisoblashni talab qiladi.
Muammo shundaki, signal TP1 ni olib, keyin narx Stop'ga qaytishi mumkin.

Agar pozitsiya butunlay yakuniy narxda yopilgan deb hisoblansa:

| Holat | Qismli yopishsiz | Qismli yopish bilan (50%) |
|---|---|---|
| TP1 (+3%) → Stop (−1%) | **−1.00%** | **+1.00%** |
| TP1 (+3%) → TP2 (+5%) | +5.00% | +4.00% |

Birinchi qator hal qiluvchi: foydalanuvchi TP1 da pozitsiyasining yarmini
yopgan bo'lsa, uning natijasi **foyda**. Tizim uni zarar deb ko'rsatsa,
foydalanuvchi raqamlarga ishonmay qolardi — va haqli ravishda.

Ulush `portfolio.tp1_close_pct` da sozlanadi (standart 50%), va natija
xabarida ochiq aytiladi: *"TP1 da pozitsiyaning 50% yopilgan edi."*

Bu 3.8-banddagi `Outcome.TP1_THEN_STOP` ajratmasi bilan ham mos keladi —
u yerda ham bu holat foyda deb hisoblanadi.

### 25.1. Shaxsiy ma'lumot umumiy statistikada oshkor qilinmaydi

Umumiy hisobot faqat agregat ko'rsatadi: nechta ishtirokchi, jami hajm.
Kim qancha kiritgani hech qayerda ko'rinmaydi.

### 25.2. Aylanma bog'liqlik va uning yechimi

Portfel modellari dastlab `core/services/portfolio.py` da edi, lekin
repository'lar ham ularni ishlatadi:

```
repository -> services -> repository   ❌ aylanma
```

Yechim: sof ma'lumot tiplari `core/domain/portfolio.py` ga ko'chirildi,
hisob mantig'i esa `services` da qoldi. Bu — qatlamlar qoidasining tabiiy
natijasi: **domain hech kimga bog'liq emas**, xizmatlar va repository'lar
esa unga bog'lanadi.

---

## 26. Avtomatik sikl: nima uchun ikki qatlam

15-bosqich butun mexanizmni bog'ladi, lekin ATAYLAB ikki qatlamda:

```
core/pipeline/cycle.py     SOF: CycleInput -> CycleResult
                           tarmoq yo'q, baza yo'q, Telegram yo'q
        ↑
bot/services/runner.py     Jonli ma'lumotni YIG'ADI va natijani TARQATADI
```

Sabab: 16-bosqichdagi backtest `runner.py` o'rniga tarixiy ma'lumot
yig'uvchini qo'yadi va **sikl kodi o'zgarmaydi**. Agar sikl bazaga
murojaat qilganda, backtest uchun uni qayta yozishga to'g'ri kelardi — va
ikki xil kod ikki xil natija berardi, ya'ni backtest ma'nosini yo'qotardi.

### 26.1. Past salomatlikda coinlar umuman tahlil qilinmaydi

4.9-band "indeks 40dan past bo'lsa yangi signal to'xtaydi" deydi. Sikl
buni **birinchi** tekshiradi va tahlilni umuman boshlamaydi:

```
Yomon bozor (salomatlik 30):
  Sikl: 0 coin tahlil qilindi, 0 signal chiqdi (chegara yopiq)
```

30 coinni tahlil qilib, keyin hammasini rad etish resurs isrofi bo'lardi.

### 26.2. Yangi signal darhol "ochiq" hisoblanadi

Bir siklda bir nechta nomzod chiqishi mumkin. Yangi chiqarilgan signal
keyingi nomzodlar uchun darhol "ochiq signal" ro'yxatiga qo'shiladi —
ansiz korrelyatsiya (4.3) va limit (4.2) qoidalari bir siklda buzilardi:

```
Yaxshi bozor: BTC ✅ chiqdi
              ETH ⏭ 'btc_major' guruhida allaqachon ochiq signal bor
```

### 26.3. Sikl oralig'i timeframega bog'langan

`cycle_interval()` kirish timeframeidan hisoblanadi (15m -> 15 daqiqa).
Tez-tez ishga tushirish foyda bermaydi: sham yopilmaguncha tahlil natijasi
o'zgarmaydi, faqat tarmoq va CPU sarflanadi.

### 26.4. Rotatsiyada faqat BITTA tavsiya

4.2-band "faqat eng zaif faol signalni almashtirish" deydi. Bir vaqtda bir
nechta almashtirish taklifi foydalanuvchini chalg'itardi — u qaysi birini
bajarishni bilmasdi.

Whipsaw himoyasi ikki qatlamli: minimal ball farqi (30) **va** sovutish
davri (120 daqiqa). Ansiz tizim har sham yopilganda "u yaxshiroq, yo'q bu
yaxshiroq" deb foydalanuvchini charchatardi.

---

## 27. Backtest 1-topilma: 3.1 va 3.2 bandlar bir xil qoidani baham ko'ra olmaydi

**Muammo.** 16-bosqichda backtest ishga tushirilganda **birorta signal
chiqmadi**. Sabab qidirilganda ikki to'siq navbatma-navbat almashib
turgani ko'rindi:

| qadam | holat | to'siq |
|---|---|---|
| 22000 | barcha timeframelar UP | narx tsikl cho'qqisida -> **Premium** -> zona to'sig'i |
| 23500 | narx qaytmoqda -> **Discount** | 30m/1h endi DOWN -> timeframe to'sig'i |

Ya'ni ikki shart bir vaqtda hech qachon bajarilmasdi.

**Birinchi gipoteza rad etildi.** "Tasdiqlovchi timeframelar ro'yxati juda
keng" deb o'ylandi. O'lchandi — ro'yxatni toraytirish **hech narsani
o'zgartirmadi**:

| `htf_confirmation` | signal | asosiy to'siq |
|---|---|---|
| `30m, 1h, 4h, 1d` | 0 | `classic_ta:timeframes` (614) |
| `1h, 4h, 1d` | 0 | `classic_ta:timeframes` (614) |
| `4h, 1d` | 0 | `classic_ta:timeframes` (614) |
| `1d` | 0 | `classic_ta:timeframes` (614) |

To'rttala variantda bir xil raqam — demak, muammo ro'yxatda emas.

**Haqiqiy sabab.** Har bir timeframe uchun trend yo'nalishi chop etildi
(chapda `trend_requires_price_above_fast=True`, o'ngda `False`):

| qadam | 30m | 1h | 4h | 1d |
|---|---|---|---|---|
| 19210 | down/down | down/down | flat/flat | **flat/up** |
| 19930 | up/up | flat/down | down/down | **flat/up** |
| 20290 | flat/up | up/up | flat/down | **flat/up** |

Kunlik timeframe **har bir qadamda** qat'iy qoida bilan `FLAT`, yumshoq
qoida bilan `UP`. Sabab oddiy: qat'iy qoida "narx EMA50 dan yuqori" ni
talab qiladi, lekin **sog'lom ko'tarilish trendi ham muntazam EMA50 ga
qaytadi** — aynan shu qaytish support zonasini va Discount holatini
yaratadi. Qat'iy qoida bilan kunlik trend hech qachon `UP` bo'lmaydi.

**Qaror.** 3.1-band va 3.2-band **har xil savolga** javob beradi:

- **3.1-band** — *kirish* qarori: "hozir sotib olish to'g'rimi". Bu yerda
  "narx EMA'lardan yuqori" mazmunli.
- **3.2-band** — yuqori timeframelarning *trend yo'nalishi*: "katta rasm
  ko'tarilishdami". Bu yerda tuzilma muhim (EMA50 > EMA200 va narx >
  EMA200), narxning EMA50 ga nisbatan hozirgi holati emas.

Shuning uchun ikkinchi sozlama ajratildi:

```yaml
analysis:
  indicators:
    trend_requires_price_above_fast: true       # 3.1 — kirish qarori (qat'iy qoladi)
    htf_trend_requires_price_above_fast: false  # 3.2 — trend tasnifi (tuzilma bo'yicha)
```

Ikkalasi ham sozlanadi. Spetsifikatsiyaning 3.1-bandi **o'zgarmadi** —
faqat u qo'llaniladigan joy aniqlashtirildi.

---

## 28. Backtest 2-topilma: trend balli 20 dan 1 ball ola olmasdi

Birinchi tuzatishdan keyin zanjir to'liq ishladi — 463 ta nomzod
shakllandi va ballandi. Lekin **eng yuqori ball 66.8**, chegara esa 70.
Hech biri o'tmadi. Nomzodlar tarkibi ko'rildi:

| omil | o'rtacha | maksimal | vazn |
|---|---|---|---|
| support_resistance | 20.62 | 24.98 | 25 |
| **trend** | **0.71** | **10.21** | **20** |
| rsi | 6.69 | 7.50 | 15 |
| volume | 3.06 | 15.00 | 15 |
| macd | 4.16 | 10.00 | 10 |
| risk_reward | 15.00 | 15.00 | 15 |

Trend omili 20 balldan o'rtacha **0.71** olardi. Kodda sabab topildi:

```python
ajralish = abs(ema_fast - ema_slow) / price
kuch = min(1.0, ajralish / 0.05)      # <- 5% qat'iy raqam
```

To'liq ball uchun EMA50 va EMA200 orasidagi masofa **narxning 5%** i
bo'lishi kerak edi. Haqiqiy ajralish o'lchandi:

| timeframe | mediana | p90 | maksimal |
|---|---|---|---|
| 15m (kirish TF) | 0.19% | 0.42% | 0.61% |
| 1h | 0.73% | 1.32% | 1.80% |
| 4h | 3.00% | 3.80% | 4.10% |
| 1d | 15.00% | 15.00% | 15.00% |

5% chegarasi **kunlik grafik uchun** to'g'ri, kirish timeframe uchun esa
10-25 baravar katta. Shu sababli bu omil 15 daqiqalik grafikda deyarli
har doim nolga yaqin bo'lardi — 100 ballik shkalaning 20 bali amalda
mavjud emasdi.

**Qaror.** O'lchov birligi foizdan **ATR**ga o'zgartirildi va chegara
konfiguratsiyaga chiqarildi (6.4-band: kodda sehrli raqam bo'lmasin):

```python
ajralish_atr = abs(ema_fast - ema_slow) / atr
kuch = min(1.0, ajralish_atr / config.ema_separation_full_atr)
```

Nima uchun ATR: u volatillikni o'zi hisobga oladi, shuning uchun o'lchov
timeframedan mustaqil bo'ladi. ATR birligida o'lchangan ajralish trend
kuchini haqiqatan ajratadi:

| trend | 15m mediana | 15m maksimal |
|---|---|---|
| kuchli (0.25%/kun) | 0.53 ATR | 2.10 ATR |
| o'rtacha (0.15%/kun) | 0.39 ATR | 1.70 ATR |
| zaif (0.05%/kun) | 0.35 ATR | 1.41 ATR |

Standart qiymat `ema_separation_full_atr: 1.5` — kuchli trend to'liq
ballga yaqinlashadi, zaif trend past ball oladi.

ATR hisoblanmagan bo'lsa kuch **0** bo'ladi (0.3-band: noaniqlikda
kamroq), lekin yo'nalish tasdig'i saqlanadi.

**RSI omili ham yarim ballda to'yingan** (maksimal 7.50 / 15). Bu esa
**ataylab shunday**: 3.1-band "RSI 30 dan QAYTISH" ni kuchli tasdiq deb
belgilaydi, o'rta zona (30-55) esa zaif tasdiq. Ko'tarilish trendidagi
qaytishda RSI odatda 50-55 atrofida bo'ladi — undan chuqurroq tushish
trendning buzilganini bildiradi. Bu chegara o'zgartirilmadi.

---

## 29. Backtest 3-topilma: chiqish narxi sham chekkasida yozilardi

Uchidan uchiga sinov qo'shilganda (signal chiqishi -> kuzatuv -> yopilish)
birinchi natija shubha uyg'otdi: stop masofasi **1% dan oshmasligi
kafolatlangan** bo'lsa ham, savdolar bunday natija berardi:

```
  stop  natija -1.561%   entry 120.9592  chiqish 119.0712
  stop  natija -1.231%   entry 120.9896  chiqish 119.5008
  stop  natija -1.658%   entry 121.0401  chiqish 119.0339
  stop  natija -1.050%   entry 120.9713  chiqish 119.7008
```

**Sabab.** Kuzatuvchiga sham ichidagi harakat `low -> high -> close`
tartibida beriladi (eng yomon talqin). Hodisa qaytarganda esa **o'sha
narx** — ya'ni shamning eng past nuqtasi — chiqish narxi sifatida
yozilardi. Natijada zarar shamning kattaligiga bog'lanib qolardi: keng
sham "yomonroq stop" bergandek ko'rinardi, garchi buyurtma o'sha 1%
darajada bajarilgan bo'lsa ham.

**Qaror.** Chiqish buyurtmasi — **OCO** (5.1.0-band). U Stop yoki TP
darajaga TEGILGANDA bajariladi. Sham ichida narx daraja orqali uzluksiz
o'tadi, shuning uchun to'g'ri to'ldirish narxi — **darajaning o'zi**:

```python
if event.new_status is SignalStatus.TP2_HIT:
    return darajalar.tp2      # narx TP2 orqali YUQORIGA o'tdi
if event.new_status is SignalStatus.STOPPED:
    return darajalar.stop     # narx Stop orqali PASTGA o'tdi
```

Tuzatishdan keyin barcha stoplar chegara ichida:

```
  stop  natija -0.983%    stop  natija -0.914%
  stop  natija -0.984%    stop  natija -0.977%
```

Bu — `tests/core/test_backtest.py::test_stop_zarari_universal_chegaradan_oshmaydi`
regressiya testi bilan qulflangan.

**Ochiq qolgan cheklov.** Haqiqiy uzilish (gap) modellashtirilmaydi: sham
ochilishi darajadan nariga sakrasa, jonli savdoda to'ldirish yomonroq
bo'ladi. Kuzatuvchiga faqat low/high/close beriladi, shuning uchun bu farq
ko'rinmaydi. 15 daqiqalik spot grafikda uzilish kam uchraydi, lekin
natijalarni o'qiganda esda tutilsin.

---

## 30. Backtest sintetik ma'lumotda: nima isbotlandi, nima isbotlanmadi

**Isbotlandi:**

0. Zanjir haqiqatan signal chiqaradi, kuzatadi va yopadi — sozlama
   qisqartirilgan holda 4 ta signal chiqdi va 4 tasi yopildi
   (`test_zanjir_signal_chiqarib_savdoni_yopadi`).
1. Zanjir uchidan uchiga ishlaydi: skrining -> S/R -> Discount ->
   timeframe -> indikator -> daraja -> ball -> Risk Engine -> kuzatuv.
2. Har bir to'siq o'z sababini qaytaradi va sabablar sanaladi
   (`rejections`), shuning uchun "nol signal" holati **tekshiriladigan**
   bo'ldi — bu 16-bosqichning asosiy qiymati.
3. Lookahead himoyasi ishlaydi (`Dataset.up_to` vaqt kesimi bilan).
4. Isinish (warm-up) eng yuqori timeframega qarab hisoblanadi — kunlik
   EMA200 uchun 200 kunlik ma'lumot kerak, kirish timeframeda bu
   200 x 96 = 19 200 qadam.

**Isbotlanmadi — va isbotlab ham bo'lmaydi:**

Win-rate, o'rtacha natija, maksimal pasayish kabi **birorta raqam**
sintetik ma'lumotdan chiqarilmaydi. Sintetik qator generatorning
parametrlariga bo'ysunadi, bozorga emas. Shu sababli bu yerda hech qanday
"strategiya X% beradi" degan xulosa yozilmagan.

**Muhit cheklovi.** Ushbu ishlab chiqish muhitida barcha tashqi bozor
ma'lumot manbalari yopiq (`api.binance.com`, `api.bybit.com`,
`api.coingecko.com`, `data-api.binance.vision` — 403/000). Haqiqiy
1-2 yillik backtest **serverda yoki shaxsiy kompyuterda** ishga
tushirilishi kerak:

```bash
python -m scripts.backtest --compare --days 730
```

Bu — 6.3-bandning majburiy sharti: **haqiqiy pul ishlatilishidan oldin**
backtest natijasi ko'rilishi shart.

**Hisobotdagi yangi qator.** Nol savdo chiqqanda "nomzod umuman
yo'q edi"mi yoki "nomzod bor edi, lekin ball yetmadi"mi — bu farq
chegarani sozlash uchun hal qiluvchi. Shuning uchun hisobot endi
chegaraga yetmagan ballarni ko'rsatadi:

```
   Chegaraga yetmagan nomzodlar: 463 ta
     eng yuqori ball: 66.8  |  o'rtacha: 50.2
```

Aynan shu qator 28-bo'limdagi xatoni topishga olib keldi.

---

## 31. 17-bosqichda topilgan yetishmovchiliklar

Yakuniy tekshiruvda uchta "e'lon qilingan, lekin qurilmagan" narsa topildi.
Ularning har biri bir xil turdagi xato: bog'liqlik yoki jadval mavjud,
lekin uni ishlatadigan kod yo'q.

### 31.1 `python-dotenv` chaqirilmasdi

`requirements.txt` da bor edi, README `cp .env.example .env` deydi — lekin
fayl hech qachon o'qilmasdi. Bu **birinchi ishga tushirishni to'sardi**.

Yuklash `load_settings()` ICHIGA qo'yilmadi: u sof muhit o'quvchisi bo'lib
qolishi kerak, aks holda testlar `.env` fayliga bog'lanardi. Shuning uchun
`load_env_file()` alohida funksiya va `run()` boshida chaqiriladi.

### 31.2 `alembic` sozlanmagan edi

Bog'liqlikda bor edi, lekin `alembic.ini` ham, migratsiyalar ham yo'q edi.
Sxema faqat `create_all` bilan yaratilardi — ya'ni **model o'zgarsa,
ishlab turgan serverni yangilab bo'lmasdi** (to'lovlar va obunalar bazada).

Uch qaror qayd etilsin:

1. **Migratsiyalar ilova kodini import qilmaydi.** `autogenerate` odatda
   `core.storage.base.UtcDateTime` deb yozadi va migratsiya ilova kodiga
   bog'lanib qoladi — o'sha klass ko'chirilsa eski migratsiyalar
   ishlamaydi. `env.py` dagi `_render_item` uni `sa.DateTime(timezone=True)`
   deb yozadi: bazada u aynan shu.

2. **`create_all` endi `alembic_version` ni belgilaydi.** Tuzoq: yangi baza
   `create_all` bilan yaratilsa, `alembic_version` bo'sh qolardi va
   keyingi `alembic upgrade head` noldan boshlab "jadval allaqachon
   mavjud" xatosini berardi. Faqat BO'SH versiya to'ldiriladi — mavjudi
   hech qachon o'zgartirilmaydi.

3. **URL `alembic.ini` da saqlanmaydi.** U `DATABASE_URL` dan olinadi,
   chunki PostgreSQL paroli git ga tushmasligi kerak.

Uchta test buni qulflaydi: migratsiya `create_all` bilan bir xil sxema
beradimi, mavjud bazani yangilab bo'ladimi, migratsiyalar `core.*` ni
import qilmaydimi.

### 31.3 `risk_blocks` jadvaliga hech narsa yozilmasdi

Jadval 2-bosqichda "tizim nega sokin?" uchun qurilgan, `RejectedCandidate`
ning izohida "admin dashboardi uchun (3.7-band)" deb yozilgan — lekin na
yozuvchi, na ko'rsatuvchi kod bor edi. Sabablar faqat jurnalga tushardi,
jurnal esa aylanadi va Telegram'dan ochib bo'lmaydi.

Endi sikl har bir rad etishni yozadi va `/panel` → 🔇 ularni guruhlab
ko'rsatadi. Yozib bo'lmasa sikl to'xtamaydi (0.3-band).

Yozuvlar 7 kun saqlanadi: har siklda o'nlab qator yoziladi, cheklanmasa
bepul serverning diski to'lardi.

### 31.4 `numpy` va `pandas` ishlatilmasdi

O'lchandi: `core/`, `bot/`, `scripts/`, `tests/` da **nol** import.
Indikatorlar ataylab sof Python'da yozilgan (9-bo'lim). Ikkalasi ~100 MB
egallardi — Oracle Cloud bepul ARM serverida bu sezilarli. Olib tashlandi.

---

## 32. Volatillik omili o'z shkalasiga chiqa olmasdi

**Belgi.** Jonli botda avtomatik sikl signal bermasdi:
`Sikl to'xtatildi: Bozor Salomatligi past (39/100)`.

**Tekshiruv.** Indeks eng IDEAL kirish bilan hisoblandi — 30 ta coinning
hammasi ko'tarilishda, dominance barqaror, ochiq signal yo'q:

| omil | ball | vazn | ulush |
|---|---|---|---|
| btc_dominance_stability | 1.00 | 20 | 20.0 |
| halal_trend_breadth | 1.00 | 25 | 25.0 |
| **volatility_regime** | **0.50** | 20 | **10.0** |
| aggregate_user_capacity | 1.00 | 20 | 20.0 |
| signal_saturation | 1.00 | 15 | 15.0 |
| | | | **90.0 / 100** |

Ya'ni indeks o'zining eng yaxshi holatida ham 100 ga chiqa olmasdi, chunki
volatillik omili to'liq ball bermasdi.

**Sabab.** Kodda to'liq ball chegarasi qat'iy `40.0` edi:

```python
elif ortacha >= 40.0:
    ball = 1.0
```

Bu — 27 va 28-bo'limlardagi bilan BIR XIL turdagi xato: bitta o'lchov
uchun to'g'ri chegara boshqa o'lchovga qo'llanilgan.

ADX 40 — **bitta coin** uchun kuchli trend. Lekin bu yerda o'lchanadigan
narsa **30 ta coinning o'rtachasi**. Coinlar har xil vaqtda trendga
kiradi, o'rtacha esa hammasini silliqlaydi — shuning uchun o'rtacha 40 ga
amalda chiqmaydi.

**Qaror.** Chegara konfiguratsiyaga chiqarildi (6.4-band) va o'rtacha
uchun mo'ljallangan qiymat qo'yildi:

```yaml
market_health:
  strong_trend_adx: 30
```

Tuzatishdan keyin indeks o'z shkalasini to'liq ishlatadi:

| bozor holati | oldin | keyin |
|---|---|---|
| ideal (30/30 UP, ADX 30) | 90.0 | **100.0** |
| yaxshi (20/30 UP, ADX 25) | 76.7 | **81.7** |
| o'rtacha (15/30 UP, ADX 20) | 63.5 | 63.5 |
| zaif (10/30 UP, ADX 15) | 50.0 | 50.0 |

Tekis bozor (ADX chegaradan past) hali ham **nol** ball oladi — bu
o'zgarmadi. Tuzatish faqat "trend bor" tomonini to'g'riladi.

**Bu signal berishni MAJBURLAMAYDI.** Ball chegarasi (3.5-band) o'z
o'rnida qoladi: indeks yuqori bo'lsa 70, o'rta bo'lsa 80. Tuzatilgani —
indeksning o'zi sun'iy ravishda past turishi edi.

**Ochiq qolgan savol.** `strong_trend_adx: 30` qiymati o'lchov bilan emas,
tahlil bilan tanlandi: bu muhitda haqiqiy bozor ma'lumoti yo'q. Jonli
ishlashda `/panel` -> 💓 orqali kuzatilishi va kerak bo'lsa
tuzatilishi kerak.

---

## 33. Jonli indeks nima uchun 38/100 turardi

32-bo'limdagi tuzatishdan keyin ham jonli bot signal bermadi. Bu safar
taxmin qilishning hojati yo'q edi: `/panel` -> 💓 beshta omilni ochib
berdi.

```
🔴 Bozor Salomatligi: 38/100
• BTC Dominance ma'lumoti yo'q
• Halol coinlarning 4%i ko'tarilish trendida (27 tadan)
• Bozor rejimi: trend shakllanmoqda (ADX 24)
• 1/1 foydalanuvchida hali kunlik xavf sig'imi bor
• Faol signallar: 2/5 (60% joy bo'sh)
```

Hisob qayta qurildi va **aynan 38.0** chiqdi — ya'ni model jonli tizimga
mos:

| omil | ball | vazn | ulush |
|---|---|---|---|
| btc_dominance_stability | **0.00** | 20 | **0.0** |
| halal_trend_breadth | **0.04** | 25 | **1.0** |
| volatility_regime | 0.40 | 20 | 8.0 |
| aggregate_user_capacity | 1.00 | 20 | 20.0 |
| signal_saturation | 0.60 | 15 | 9.0 |
| | | | **38.0** |

Ikkita omil deyarli nol edi va ikkalasi ham xato sababli.

### 33.1 BTC Dominance manbai umuman ulanmagan edi

Kodda ochiq qoldirilgan:

```python
btc_dominance=None,  # TODO(17): dominance manbai ulanadi
```

Ya'ni indeksning **20 bali o'lik** edi. Bu 17-bosqichda bajarilishi kerak
edi, lekin o'tkazib yuborilgan.

**Qaror.** `core/market_data/dominance.py` qo'shildi — CoinMarketCap
`/global-metrics/quotes/latest`. Kalit allaqachon reyting uchun
ishlatilyapti, yangi kalit kerak emas.

Ikki ehtiyot chorasi:

1. **Sutkalik o'zgarish maydoni ixtiyoriy.** CMC uni har doim ham
   qaytarmaydi va nomini o'zgartirgan. Ikkita nom sinab ko'riladi,
   topilmasa `None` — omil buni hisobga oladi.
2. **Hech qanday istisno tashqariga chiqmaydi.** Tarmoq xatosi, buzuq
   javob, yaroqsiz kalit — hammasi `None` beradi va sikl davom etadi
   (0.3-band).

Kalit yo'q bo'lsa ishga tushishda ogohlantirish yoziladi: *"BTC Dominance
omili nol ball oladi (indeksning 20 bali ishlatilmaydi)"*.

### 33.2 Bozor kengligi qat'iy qoida bilan o'lchanardi

27 coindan atigi **1 tasi** (4%) "ko'tarilishda" deb hisoblangan. Sabab —
27-bo'limdagi xatoning aynan o'zi, faqat boshqa joyda:

```python
trendlar[symbol] = timeframe_trend(..., indicators.trend_requires_price_above_fast)
```

Bozor **kengligi** — "katta rasm ko'tarilishdami" degan REJIM savoli,
kirish qarori emas. 27-bo'limda buning uchun
`htf_trend_requires_price_above_fast` ajratilgandi, lekin bu joy
o'tkazib yuborilgan: kenglik hali ham qat'iy qoidani ishlatardi va
support zonasiga qaytgan har bir coin "trendsiz" ko'rinardi.

Endi kenglik ham tuzilma qoidasini ishlatadi (EMA50 > EMA200). Backtest
dvigateli ham bir xil qilindi.

### 33.3 Nima o'zgarmadi

Ball chegarasi (70/80) va salomatlik chegarasi (40) **tegilmadi**. Uchala
tuzatish ham indeksning sun'iy ravishda past turishiga qaratilgan, signal
berishni majburlashga emas. 0.2-band kuchda: bozor mos bo'lmasa bot jim
turadi.

**Ochiq savol.** Dominance so'rovi bu muhitda sinab ko'rilmagan — tarmoq
yopiq. Javob TAHLILI to'liq sinalgan (bo'sh, buzuq, maydonsiz javoblar),
lekin haqiqiy chaqiruv jonli ishlashda tekshirilishi kerak: `/panel` ->
💓 da "BTC Dominance ma'lumoti yo'q" qatori yo'qolishi lozim.

---

## 34. Jonli sinovda topilgan beshta xato

Bot haqiqiy foydalanuvchilarga ko'rsatilganda beshta xato aniqlandi.
Hammasi mavjud mantiqdagi xato — yangi funksiya emas.

### 34.1 Sarlavha va holat bir-biriga zid edi

Bitta xabarda: *"⚡ Hozir oling — narx allaqachon kerakli joyda"* va
pastida *"⏳ Kutilmoqda — narx kirish nuqtasiga yetmadi"*.

**Sabab.** Buyurtma turini tanlashda joriy narx o'rniga KIRISH narxining
o'zi uzatilardi:

```python
reja = decide_entry_plan(levels.entry, levels, ...)   # noto'g'ri
```

Ya'ni "joriy narx = kirish narxi" — masofa har doim nol, tur har doim
**Market**. Kuzatuvchi esa haqiqiy narxni ko'rib **Kutilmoqda** derdi.

**Tuzatish.** Ikkala yo'l ham bozordagi haqiqiy narxni oladi: avtomatik
sikl — oxirgi shamning yopilish narxini, qo'lda yuborish — birjadan
so'rov orqali. Narx olinmasa eski xatti-harakat qoladi (0.3-band).

### 34.2 Futures terminologiyasi

Bu SPOT savdo. "Pozitsiya ochish/yopish", "long/short" atamalari
foydalanuvchi matnlaridan olib tashlandi:

| eski | yangi |
|---|---|
| ✋ Men kirdim | 🖐 Men sotib oldim |
| Qancha miqdorda kirdingiz? | Qancha miqdorga sotib oldingiz? |
| Ochiq pozitsiyalar | Ochiq xaridlar |
| Faol — pozitsiya ochiq | Faol — sotib olingan |

Ichki kod o'zgaruvchilari o'zgarmadi — faqat ko'rinadigan matn.

### 34.3 OCO mantig'i noto'g'ri tushuntirilgan edi

Kartochka "TP1, TP2, Stop — uchalasi birga OCO" derdi. Bu **texnik
jihatdan noto'g'ri**: birjada bitta OCO faqat bitta sotish narxi + bitta
stopdan iborat, ikkita TP ni bitta OCO ichiga qo'yib bo'lmaydi.

To'g'ri mantiq — miqdor ikkiga bo'linadi:

```
SOTISH — 2 ta OCO buyurtma
1-OCO (50%)  🎯 123 500  +4.44%
            🛑 116 500  -1.48%
2-OCO (50%)  🎯 124 000  +4.86%
            🛑 116 500  -1.48%
```

Ulush `portfolio.tp1_close_pct` dan olinadi — ya'ni kartochka va
5.4-banddagi qismli yopish hisobi BITTA manbadan ishlaydi.

### 34.4 Ortiqcha izohlar

"Uchalasi birga qo'yiladi...", "Har 1 birlik zararga N birlik foyda
imkoniyati" kabi qatorlar olib tashlandi. Kartochka endi faqat raqam va
harakatdan iborat; tushuntirish «Nega bu signal?» tugmasi ostida qoladi.

### 34.5 Risk qoidasi noto'g'ri cheklangan edi (ENG MUHIM)

**Eski qoida:** Stop masofasi narxning 1% idan oshmasin.

Bu signal sonini keskin kamaytirardi — aynan 1% masofada mos S/R zonasi
kam uchraydi. Jonli botda `classic_ta:levels` sababi aynan shundan
chiqardi.

**Yangi qoida:** Stop **1%..5%** oralig'ida ERKIN joylashadi. Qat'iy
shart — **NISBAT**:

| Stop | TP2 kamida |
|---|---|
| −1% | +3% |
| −2% | +6% |
| −5% | +15% |

Nisbat 1:3 dan past bo'lsa signal berilmaydi — Stop foizi kichik yoki
katta bo'lishidan qat'i nazar.

**Xavf oshmaydi.** Pozitsiya hajmi formulasi (5.1-band) o'zgarmadi:

```
miqdor = xavf qilinadigan pul / Stop masofasi (%)
```

Stop kattalashsa miqdor avtomatik kichrayadi. Bu formula allaqachon
to'g'ri edi — endi Stop erkin bo'lgani uchun u to'liq ishlaydi.

**Uchta qo'shimcha tuzatish shundan kelib chiqdi:**

1. **Stop pastki chegarasi** qo'shildi (1%): juda yaqin Stop'ni bozor
   shovqini bekorga yeb qo'yadi.
2. **Skalping alohida chegara oladi.** Universal 1% minimal Stop
   skalpingni imkonsiz qilardi — kunlik diapazonning narigi chekkasi
   odatda 1% dan yaqin. `scalp_trade_rules()` endi Stop chegarasini ham
   qaytaradi.
3. **Volatillik qoidasi qayta bog'landi.** U `max_stop_distance_pct` ga
   bog'langandi; u 1% dan 5% ga o'zgarganda qoida ATR dan 5% talab qilib,
   deyarli har bir signalni to'sardi. Endi `min_stop_distance_pct` ga
   bog'langan.

**TP1 ham Stop bilan bog'landi** (`tp1_min_risk_reward: 1.5`). Sabab:
TP1 da xaridning yarmi sotiladi — agar u 1:1 dan past bo'lsa, o'sha yarim
savdo o'rtacha zarar keltirardi. Stop 4% bo'lsa TP1 kamida 6% da turadi.

---

## 35. Yuborilgan signalni bekor qilish

### Muammo

Signal yuborilgach uni to'xtatishning **hech qanday yo'li yo'q edi**.
`signal:cancel` degan tugma bor edi, lekin u faqat *yozish jarayonini*
bekor qilardi — signal hali yuborilmagan payt. Yuborilgandan keyin
signal ikki holatdan birida tugashi mumkin edi:

1. narx TP2 yoki Stop'ga yetadi;
2. 24 soat kutadi va `check_expiry()` uni eskirgan deb bekor qiladi.

Ya'ni noto'g'ri kiritilgan yoki sinov uchun berilgan signal obunachilarda
bir kunga qadar "faol" bo'lib turardi.

### Nima uchun o'chirish emas, bekor qilish

Yozuvni bazadan o'chirish eng oson yo'l edi, lekin u ikki narsani buzardi:

- **Postmortem tarixi** (3.8-band) — signal nima uchun berilgani va nima
  bilan tugagani yozuvda qoladi. O'chirilgan signal haqida keyin hech
  narsa aytib bo'lmaydi.
- **Ochiq pozitsiyalar** — "Men sotib oldim" degan foydalanuvchining
  pozitsiyasi `signal_id` ga bog'langan. Signal o'chirilsa, pozitsiya
  hech qachon yopilmaydigan yetim yozuvga aylanardi.

`CANCELLED` holati esa allaqachon **natija statistikasidan chiqarilgan** —
ya'ni sinov signali g'alaba foizini ham buzmaydi. Shuning uchun tanlov:
signal `CANCELLED` deb belgilanadi, yozuv joyida qoladi.

### Nima uchun bitta yo'l

Bekor qilish to'rt joyni birga yangilashi kerak:

| Joy | Yangilanmasa nima bo'ladi |
|---|---|
| `SignalTracker` | narx TP'ga yetsa signal qayta "ochiladi" |
| baza | qayta ishga tushirilganda signal yana kuzatuvga tiklanadi |
| ochiq pozitsiyalar | foydalanuvchi natijasini kutib qolaveradi |
| `PriceStream` obunasi | kerak bo'lmagan coin oqimda qolib ketadi |

Shuning uchun handler bu ishni o'zi qilmaydi — hammasi
`SignalWatcher.cancel_signal()` ichida, bitta joyda. Handler faqat
tasdiq so'raydi va natijani ko'rsatadi.

Kuzatuvchi ishlamayotgan bo'lsa (`watcher is None`) handler bazani
to'g'ridan-to'g'ri yopadi: bunday holatda kuzatuvda yangilanadigan narsa
ham yo'q.

### Yo'l-yo'lakay topilgan xato: TP1 dan keyingi Stop

`_close_positions()` qismli sotishni hisobga olish uchun signal TP1 ga
yetgan-yetmaganini so'rardi:

```python
return signal.status in {SignalStatus.TP1_HIT, SignalStatus.TP2_HIT}
```

Lekin bu tekshiruv signal **yopilgandan keyin** bajariladi. TP1 dan keyin
narx Stop'ga tushsa, `status` allaqachon `STOPPED` bo'lib qolgan — ya'ni
"TP1 olingan edi" fakti yo'qolgan. Natijada aynan shu holat, ya'ni
funksiya izohida yozilgan holat, sof zarar bo'lib hisoblanardi.

Sabab tanish: **bir maydondan ikki xil ma'no so'ralgan** — `status`
"hozir qayerda" degan savolga javob beradi, "qayerdan o'tgan" degan
savolga emas. Yechim: `Signal.tp1_reached` bayrog'i. U bir marta
ko'tariladi va keyin o'chmaydi; qayta ishga tushirilganda holatdan
tiklanadi.

Bu xato bekor qilish yo'lida ham takrorlanardi (`CANCELLED` ham `status`
ni almashtiradi), shuning uchun shu yerda tuzatildi.

---

## 36. Signallar ro'yxati: nima uchun kech qolganlar ochilmaydi

### Avvalgi ko'rinish

`menu:signallar` bosilganda har bir ochiq signal ALOHIDA xabar bo'lib
kelardi. Uchta signal — uchta uzun kartochka, ular orasida hech qanday
tartib yo'q, suhbat to'lib ketardi. Va eng muhimi: TP1 allaqachon
olingan signal ham xuddi yangi signaldek to'liq narxlari bilan
ko'rsatilardi.

### Yangi ko'rinish

Bitta ekran, ikkita guruh:

```
📡 Signallar

✅ Hozir qo'shilish mumkin — 2 ta
   [⏳ BTC · kutilmoqda]
   [🟢 ETH · faol]

⏸ Kech qolindi — 1 ta
   [🎯 SOL · TP1 olindi]
```

Birinchi guruhdagi tugma kartochkani ochadi. Ikkinchi guruhdagi tugma
faqat sababni tushuntiradi — narxlar ko'rsatilmaydi.

### Nima uchun narxlar umuman berilmaydi

Bu qaror **yangi foydalanuvchi** uchun. Tajribali savdogar kech
kirishning zararini o'zi ko'radi, yangi odam esa ko'rmaydi — u faqat
"signal bor ekan" deb o'ylaydi.

Narx TP1 ga yetgach vaziyat quyidagicha o'zgaradi:

| | Signal berilganda | TP1 dan keyin |
|---|---|---|
| Stop'gacha masofa | 3% | 6% (narx uzoqlashdi) |
| TP2 gacha masofa | 10% | 6% |
| Nisbat (R/R) | 1:3.3 | 1:1 |

Stop **o'sha joyda qoladi** — u narx bilan birga ko'tarilmaydi. Ya'ni
kech kiruvchi bir xil xavfni oladi, lekin foydaning yarmidan
ko'prog'ini boy bergan. 3.3-bandda butun tizim uchun eng kam nisbat
1:3 deb belgilangan; kech kirish aynan shu qoidani chetlab o'tadi.

Shuning uchun tanlov: narxni ko'rsatib "ehtiyot bo'ling" deb yozish
emas, umuman ko'rsatmaslik.

Signal ro'yxatdan OLIB TASHLANMAYDI: foydalanuvchi qanday signallar
borligini va ular qanday ketayotganini bilishi kerak — bu tizimga
ishonch beradi. Ochilmaydigani faqat narxlar.

### `is_open` va `is_enterable` farqi

`SignalStatus.is_open` — "signal hali kuzatuvda", `is_enterable` — "bunga
hozir qo'shilish mumkin". TP1 olingan va zaiflashayotgan signal
birinchisiga kiradi, ikkinchisiga kirmaydi.

Ikkalasini bitta xususiyat qilib qo'yish oson edi, lekin ular ikki xil
savolga javob beradi: birinchisi kuzatuv tizimi uchun (narxni
tekshirishda davom etamizmi), ikkinchisi interfeys uchun (tugmani
ochamizmi). Bir xil deb hisoblash — 33 va 34-bo'limlarda to'rt marta
takrorlangan xatoning aynan o'zi.

Holat ro'yxat tuzilgandan keyin ham o'zgarishi mumkin (narx TP1 ga
yetadi), shuning uchun `sig:open:` handleri tekshiruvni QAYTA bajaradi
— eski tugma orqali kech qolgan signalga kirib bo'lmaydi.

### Kartochkadagi narx

Kartochka ochilganda joriy narx bozordan qayta olinadi. Avval
`price_at_signal` ishlatilardi — ya'ni signal yaratilgan paytdagi narx
"hozirgi narx" deb yozilardi. Ro'yxat signal kelganidan bir necha soat
keyin ochilishi mumkin, shuning uchun bu raqam yolg'on bo'lib chiqardi.

---

## 37. Sokinlik dashboardi: bitta ustunda uch xil o'lchov

Jonli ekran shunday ko'rinardi:

```
• opening_range_scalp:window — 945 marta (49%)
• classic_ta:zone_position   — 624 marta (32%)
• classic_ta:timeframes      — 312 marta (16%)
• market_health              —  53 marta (3%)
• threshold                  —   5 marta (0%)
• classic_ta:levels          —   3 marta (0%)
• classic_ta:confirmation    —   1 marta (0%)
```

Bu ro'yxatda uchta alohida xato bor edi.

### 1. "5 marta (0%)"

`{:.0f}%` yaxlitlashi 0.26% ni "0%" ga aylantiradi. Natijada bitta
qatorda ikkita qarama-qarshi gap turardi: "5 marta bo'ldi" va
"hech qachon bo'lmadi".

Yechim: nolga yaxlitlanadigan qiymat `<1%` deb yoziladi. Chegara
qo'lda tanlanmaydi — matn yasab ko'riladi va `"0%"` chiqsa
almashtiriladi. Python yarim sonlarni juft tomonga yaxlitlaydi
(`f"{0.5:.0f}"` → `"0"`), shuning uchun 0.5 ni chegara qilib qo'yish
noto'g'ri bo'lardi.

### 2. Vaqt sharti tashxis o'rnida turibdi

`opening_range_scalp:window` — skalping oynasi yopiq degani. Oyna
kuniga atigi **45 daqiqa** ochiq (12-bosqich), ya'ni vaqtning 96.9%
ida bu yozuv HAR SIKLDA, HAR COIN uchun yoziladi.

Shuning uchun u har doim birinchi o'rinda turadi va har doim ~50%
bo'ladi — bozor qanday bo'lishidan qat'i nazar. Bu tashxis emas, soat
ko'rsatkichi. Yomoni: u maxrajni ikki barobar shishirib, qolgan barcha
sabablarning foizini ikki barobar kichraytiradi.

Yozuvlar o'chirilmaydi (kutuv ishlayotganini ko'rsatadi), lekin
`ROUTINE_STAGES` ro'yxati orqali alohida bo'limga chiqariladi va foiz
hisobiga kirmaydi.

### 3. Ikki xil o'lchov bitta ustunda

`market_health` — SIKL darajasidagi yozuv (`symbol` yo'q). U chiqqanda
sikl to'xtaydi va **birorta coin umuman ko'rilmaydi**. Qolgan sabablar
esa COIN darajasida: bitta coin, bitta sikl.

Ya'ni "53 marta market_health" ≈ 53 × 30 = 1590 ta coin imkoniyati
yo'qolgan, "624 marta zone_position" esa 624 ta coin imkoniyati. Ularni
qo'shib foizlash — 30 ta coinni to'xtatgan sababni bittasini to'xtatgani
bilan teng deb hisoblash.

Ekranda market_health "3%" bo'lib ko'rinardi, aslida u eng katta
to'siqlardan biri edi.

Yechim: `summary_since()` endi `symbol IS NULL` bo'yicha ham guruhlaydi
va uchinchi element sifatida "sikl darajasidami" degan javobni
qaytaradi. Dashboard uchta bo'limga ajratadi, foiz faqat coin
darajasidagi yozuvlar ichida hisoblanadi.

### Yana bir marta: bir xil xatoning to'rtinchi ko'rinishi

32, 33 va 34-bo'limlarda **bir shkala uchun to'g'ri bo'lgan qiymat
boshqa shkalaga qo'llangani** to'rt marta topilgan edi (EMA ajralishi,
ADX, narx-EMA qoidasi ikki marta). Bu — o'shaning beshinchisi, faqat
chegara emas, **sanoq** darajasida: bir xil o'lchovda emas raqamlar
bitta maxrajga qo'shilgan.

### Kod nomlari o'rniga odam o'qiydigan nomlar

`classic_ta:zone_position` adminга hech narsa aytmaydi. Endi
`STAGE_LABELS` dan "Narx support zonasidan uzoq" deb chiqadi.

Nomlar `core/pipeline/context.py` da, bosqich kodlari esa boshqa
fayllarda yaratiladi — ikkisi ajralib ketishi mumkin. `i18n` uchun
allaqachon ishlatilgan usul takrorlandi: `tests/core/test_stage_labels.py`
kodni skanerlab, nomsiz qolgan yoki ortiqcha qolgan bosqichni topadi.
Nom topilmasa dashboard yiqilmaydi — kodning o'zi ko'rsatiladi
(0.3-band).

### Natija

```
📊 Coin tahlili — 945 ta tekshiruv
• Narx support zonasidan uzoq — 624 marta (66%)
• Timeframelar bir-biriga zid — 312 marta (33%)
• Ball chegaradan past — 5 marta (1%)
• Darajalar risk qoidasiga sig'madi — 3 marta (<1%)
• Indikatorlar tasdiqlamadi — 1 marta (<1%)

⏸ Butun sikl to'xtagan
• Bozor Salomatligi past — 53 marta

⏱ Vaqt shartlari — foiz hisobiga kirmaydi
• Skalping oynasi yopiq — 945 marta
```

Endi ro'yxatning boshida turgan raqam haqiqatan ham eng katta to'siqni
ko'rsatadi.

---

## 38. `<1%` butun ekranni o'chirib qo'ydi

37-bo'limdagi tuzatish joylashtirilgach, 🔇 tugmasi **umuman javob
bermay qoldi**. Qolgan tugmalar ishlardi.

### Sabab

Bot xabarlari `parse_mode=HTML` bilan yuboriladi. Bunda matndagi ochiq
`<` teg boshlanishi deb o'qiladi. `<1%` esa hech qanday tegga
o'xshamaydi, shuning uchun Telegram BUTUN xabarni rad etadi:

```
Bad Request: can't parse entities
```

Handler xato bilan tugaydi, `callback.answer()` ga yetib bormaydi —
foydalanuvchi uchun bu "tugma bosildi, hech narsa bo'lmadi" ko'rinadi.
Ekranda hech qanday xato yo'q, jurnalda esa bor. Aynan shu sababli
uni faqat jonli sinovda sezish mumkin edi.

Ya'ni "0%" ni tuzatish uchun qo'yilgan `<1%` ekranni butunlay
ochilmas qilib qo'ydi.

### Ikkinchi manba

Xuddi shu xato ikkinchi joyda ham kutib turgan edi:

```python
detail=f"Ball {element.score:.0f} < chegara {chegara:.0f}",
```

Bu matn "Oxirgi tafsilotlar" bo'limida ko'rsatiladi. Ya'ni `threshold`
rad etishi oxirgi uchtalikka tushgan har safar ekran ochilmasdi. Bu
mening o'zgarishimdan oldin ham mavjud edi, faqat kamdan-kam
uchraganidan ko'rinmagan.

### Yechim

Bazadan yoki tahlildan kelgan har bir qiymat `_xavfsiz()` dan o'tadi.

Muhim tafsilot: `html.escape` sukut bo'yicha apostrofni ham qochiradi.
O'zbek matnida u har qadamda uchraydi va `sig&#x27;madi` bo'lib
chiqadi. Matn tanasida apostrofni qochirish SHART EMAS — faqat
`< > &` maxsus ma'noga ega — shuning uchun `quote=False`.

### Nima uchun test funksiyani emas, XABARNI tekshiradi

`_ulush()` ni alohida sinash bu xatoni topmagan bo'lardi: u to'g'ri
qiymat qaytaradi. Xato qismlar birlashganda, ya'ni tayyor xabarda
tug'iladi.

`tests/bot/test_message_html.py` tayyor matnni oladi, Telegram
qabul qiladigan teglarni olib tashlaydi va qolgan `<` ni qidiradi.
Tuzatishdan oldingi kodda bu test 5 ta xato topadi.

### Naqsh

Bu — 34-bo'limdagi "sarlavha va holat ikki manbadan" xatosining
qarindoshi: **ma'lumot va belgilash bir-biridan ajratilmagan**. U
yerda ikkita manba bitta gapni ikki xil aytardi; bu yerda ma'lumot
matni belgilash sifatida o'qildi. Ikkalasida ham chegara qo'yilmagan
edi.

---

## 39. Tahlil doirasi 30 tadan 150 taga kengaytirildi

### Nima uchun

37-bo'limdagi sokinlik dashboardi aniq javob berdi: rad etishlarning
**66% i "narx support zonasidan uzoq"**. Ya'ni to'siq strategiyada
emas — strategiya to'g'ri ishlayapti, faqat qaraydigan coini kam edi.

30 ta coinning bir vaqtda support zonasiga yaqin turishi kam
uchraydi. 150 tada esa xuddi shu ulush besh barobar ko'p imkoniyat
beradi. Strategiya, chegara, Risk Engine — hech biri o'zgarmaydi.

Signal soni toshib ketmaydi: bir vaqtda nechta signal ochiq
turishini `target_count` emas, Risk Engine belgilaydi (4.2-band:
salomatlikka qarab 0/3/5 ta).

### Bu bitta raqam o'zgarishi emas edi

`target_count: 30 -> 150` deb yozib qo'yish tizimni **ishlamas holga**
keltirardi. Ikkita to'siq bor edi va ikkalasi ham jimgina buzilardi.

#### 1. Chegarasiz parallellik

`_load_candles()` barcha coin × barcha timeframe so'rovini bir zumda
yuborardi:

| Coinlar | Bir vaqtdagi so'rov | Binance javobi |
|---|---|---|
| 30 | 90 | chidaydi |
| 150 | 450 | 429, keyin 418 (IP ban) |

Ya'ni ro'yxat kengaygani sari tizim ko'proq emas, **kamroq** ma'lumot
olardi. `max_concurrent_candle_requests` (standart 8) qo'shildi.

Test buni o'lchaydi: chegarasiz kodda 60 ta coinda 300 ta so'rov
ochiladi, chegara bilan 8 ta.

#### 2. CoinGecko faqat birinchi sahifani so'rardi

```python
"per_page": str(min(limit, 250)),
"page": "1",
```

500 ta so'ralsa ham 250 tasi kelardi — **xatosiz, jimgina**. Log ham
"250 ta coin olindi" deb yozardi, ya'ni skanerlash chuqurligini
oshirish hech qanday ta'sir bermasdi va buni sezish qiyin edi. Endi
sahifalab yuklanadi.

### Likvidlik filtri ATAYLAB pasaytirilmadi

`min_daily_volume_usd` $50M da qoldi. Reytingda pastroq turgan
coinlarda kunlik hajm kichik bo'ladi va $500 lik buyurtma ham narxni
surib yuboradi. Pozitsiya hajmi mexanizmi (5.1-band) haqiqiy pul
bilan ishlaydi — bu yerda "ko'proq coin" degan foyda slippage zarariga
arzimaydi.

Shuning uchun ro'yxat 150 taga to'lmasligi mumkin. **Bu nosozlik
emas** — aynan shu filtr ishlagani. Haqiqiy son `/panel` -> 💓 ekranida
ko'rinadi: "Halol coinlarning 45%i ko'tarilish trendida (87 tadan)".

Bu raqamni bir necha kun kuzatib, keyin qaror qilish kerak: agar u
90 atrofida tursa, filtrni pasaytirish emas, shunday qoldirish
to'g'riroq.

### O'lchov shkalasi tekshirildi

32-34 bo'limlardagi takrorlangan xato — bir shkala uchun to'g'ri
qiymatni boshqasiga qo'llash — shu yerda ham bo'lishi mumkin edi.
Bozor Salomatligi omillari tekshirildi: `uptrend_ratio`,
`headroom_ratio`, `saturation_ratio` — hammasi NISBAT, sanoq emas.
Shuning uchun coinlar soni ortishi ularni buzmaydi, aksincha bozor
kengligi baholashini aniqlashtiradi (30 ta emas, 150 ta namuna).

### Halol ro'yxat haqida ogohlantirish

Reytingda 30 dan 150 gacha tushish — ilgari umuman ko'rilmagan
coinlarni ro'yxatga kiritish demakdir. Avtomatik skrining toifa
bo'yicha ishlaydi va u to'liq kafolat emas.

Ro'yxatni bilimli kishi bilan ko'rib chiqish talabi shu o'zgarishdan
keyin **kuchayadi**, kamaymaydi.

---

## 40. Bot 48 soat jim turdi: chegara erishib bo'lmas edi

### Belgi

Ro'yxat 150 taga kengaytirilgach ham signal chiqmadi. Dashboard:

```
📊 Coin tahlili — 4737 ta tekshiruv
• Narx support zonasidan uzoq — 2996 (63%)
• Timeframelar bir-biriga zid  — 1506 (32%)
• Ochilish diapazoni mos emas  —  135 (3%)
• Ball chegaradan past         —   47 (1%)
...
```

47 ta nomzod butun zanjirni o'tib, oxirgi darvozagacha yetgan. Va
**47 tasidan bittasi ham o'tmagan**. Oxirgi darvozada 100% rad etish —
bu tasodif emas.

### O'lchov

`scripts/kalibrlash.py` yozildi: 27 ta turli sifatdagi sozlama
quriladi (chuqur/o'rta/sayoz qaytish × past/yaxshi/kuchli hajm ×
sust/o'rta/kuchli trend) va har biriga ball hisoblanadi.

```
Nomzod chiqdi   : 12
Eng yuqori ball : 59.7
O'rtacha        : 50.9

  chegara 80: 0/12 (0%)   <- joriy (o'rta salomatlik)
  chegara 70: 0/12 (0%)   <- joriy (yuqori salomatlik)
  chegara 60: 0/12 (0%)
  chegara 55: 4/12 (33%)
  chegara 50: 8/12 (67%)
```

**Erishish mumkin bo'lgan eng yuqori ball — 59.7. Chegara — 80.**
Ya'ni bot signal chiqara olmasdi. Umuman. Hech qanday bozorda.

### Nima uchun 100 ball chiqmaydi

Ball funksiyasi darajali, va omillarning bir qismi bu strategiyada
**bir vaqtda to'liq bo'la olmaydi**. "Ideal" sozlamaning tafsiloti:

| Omil | Ball | Sabab |
|---|---|---|
| S/R | 18.7/25 | zonaga 0.02 ATR, 18 marta sinalgan — deyarli mukammal |
| Hajm | 15/15 | o'rtachadan 2.4× |
| RSI | 7.5/15 | RSI 51 — o'rta zona |
| R/R | 7.5/15 | 1:3.0 — aynan eng kam talab |
| Trend | 6.4/20 | ADX 13 |
| MACD | **0/10** | signal chizig'idan pastda |

Oxirgi ikki qator muhim. **Support'da xarid qilish MACD kesishidan
OLDIN sodir bo'ladi** — kesish keyinroq keladi. Ya'ni "support'da ol"
va "MACD tasdiqlasin" bir-biriga zid talab. Xuddi shunday, R/R aynan
3.0 bo'lsa (qoida talab qilgan eng kam qiymat) faqat yarim ball
beriladi.

100 ball — nazariy cho'qqi, amaliy emas.

### Xatoning turi: yana o'sha

32-34 va 37-bo'limlarda bir xil xato besh marta topilgan edi: **bir
shkala uchun to'g'ri qiymat boshqasiga qo'llangan**. Bu — oltinchisi
va eng qimmati. "Signal uchun 80 ball kerak" degan gap 0-100 shkalada
tabiiy eshitiladi; ball funksiyasining HAQIQIY shkalasi esa 0-60.

### Nima uchun hech qanday test tutmadi

Barcha testlar ballni tashqaridan berardi (`{"BTC": 95.0}`) yoki
chegarani raqam bilan yozardi (`assert threshold == 80`). Ya'ni
"chegara qo'yilgani" sinalgan, "chegaraga yetish mumkinmi" hech qachon
sinalmagan. Ikkisi orasidagi bo'shliqda bot 48 soat jim turdi.

`tests/core/test_chegara_erishiladi.py` aynan shu bo'shliqni yopadi:
u strategiyani haqiqiy sham ma'lumotida ishga tushirib, chiqqan
ballni chegara bilan solishtiradi. Eski konfiguratsiyada bu test
yiqiladi va sababini aytadi:

```
chegara 80.0, lekin eng yuqori ball 59.7 — birorta signal chiqmaydi
```

Teskari xavf ham qo'riqlanadi: nomzodlarning 60% dan ko'pi o'tsa,
chegara ma'nosini yo'qotgan deb hisoblanadi.

### Yangi qiymatlar

| | Eski | Yangi | Taqsimotdagi o'rni |
|---|---|---|---|
| Yuqori salomatlik | 70 | **50** | eng yaxshi 67% |
| O'rta salomatlik | 80 | **55** | eng yaxshi 33% |

3.5-banddagi mantiq saqlandi: bozor zaiflashsa talab OSHADI. Chegaradan
keyin Risk Engine'ning 13 qoidasi ham turibdi.

### Ko'rlik tuzatildi

`RejectedCandidate.score` allaqachon mavjud edi, lekin `record_many()`
uni yozishda tashlab ketardi — "e'lon qilingan, lekin ulanmagan"
naqshining navbatdagi ko'rinishi (31-bo'lim). Shu sababli dashboard
"Ball chegaradan past" deb yozardi-yu, QANCHALIK past ekanini
ko'rsatolmasdi.

78 ball olib 80 dan qaytish va 44 ball olib 80 dan qaytish — butunlay
boshqa muammo, lekin ekranda bir xil ko'rinardi. Endi:

```
• Ball chegaradan past — 47 marta (1%)
   ↳ eng yuqori ball 58, o'rtacha 44
```

Chegarani keyingi safar o'zgartirish kerak bo'lsa, qaror shu qatordan
olinadi — taxmindan emas.

---

## 41. Indikatorlar to'siq bo'lishdan to'xtadi

### Talab

"Indikatorlar doim kech qolib yuradi, bu bizning ishimizga teskari.
Indikator faqat ball uchun bo'lsin — qaysi coinni olish mumkin, qaysini
mumkin emas degan qarorga aloqasi bo'lmasin. U shunchaki ko'p
kriptovalyuta ichidan tanlash uchun bo'lsin."

### Talab to'g'ri, va buni kod o'zi tan olgan edi

`confirmation.py` dagi izoh allaqachon shunday yozilgan:

> MACD kechikuvchi indikator — u faqat narx ko'tarilgandan keyin
> tasdiqlaydi, o'sha paytda narx Discount zonasidan chiqib ketgan
> bo'ladi.

Bu kuzatuvdan chiqarilgan xulosa esa yarim edi: 4/4 talab 2/4 ga
tushirilgan, lekin to'siqning O'ZI qolgan. Bir xil mantiq qolgan
indikatorlarga ham tegishli.

Ziddiyat quyidagicha ko'rinadi:

| Strategiya nima qiladi | Indikator nima talab qiladi |
|---|---|
| narx arzon zonaga tushganda oladi | narx ko'tarila boshlaganini kutadi |
| ya'ni pasayish oxirida | ya'ni ko'tarilish boshida |

"Indikator tasdiqlasin" talabi amalda "arzon paytda olma,
qimmatlashgach ol" degani — strategiyaning o'z maqsadiga zid.

Kunlik EMA200 bunda eng yomoni: u 200 kunlik o'rtacha, ya'ni mavjud
o'lchovlarning eng sekini. Jonli ma'lumotda rad etishlarning **32% i**
aynan shu to'siqda edi.

### Kim nimaga javob beradi

```
QAROR (to'siq)              REYTING (ball)
─────────────────────      ──────────────────
S/R zonasi + Discount      EMA / ADX / yuqori TF
Risk qoidasi (3.3)         RSI
Halol ro'yxat              Hajm
Risk Engine (4-bo'lim)     MACD
                           R/R sifati
```

Chap ustun **kechikmaydi**: narxning hozirgi joylashuvi va nisbatlar
haqida gapiradi. O'ng ustun kechikadi — shuning uchun u faqat "ko'p
nomzod ichidan qaysi biri" degan savolga javob beradi.

### To'siq olib tashlandi, ma'lumot emas

Muhim farq. To'siqni olib tashlab o'rniga hech narsa qo'ymaslik yuqori
timeframe ma'lumotini butunlay yo'qotardi — u holda kunlik tushishda
ham signal berilaverardi.

`MultiTimeframeView.alignment_ratio()` qo'shildi: `all_aligned()`
"hammasi yoki hech biri" deb javob beradi (to'siq uchun mos edi),
`alignment_ratio()` esa daraja qaytaradi — 4 tadan 3 tasi ko'tarilishda
bo'lishi 0 tasi bilan bir xil emas (3.5-band: darajali baho).

### `score_trend` qayta yozildi

Ilgari:

```python
if omil is None or not omil.confirmed:
    return ScoreComponent("trend", 0.0, ...)   # DARHOL nol
xom = ema_kuchi * 0.5 + adx_kuchi * 0.5
```

Bu kechikish muammosini **ballga ham** olib kirardi: narx support
zonasiga qaytganda kirish timeframedagi trend deyarli har doim pastga
qaragan bo'ladi — aynan shuning uchun narx pastga tushgan. Ya'ni "yaxshi
qaytish" holati 20 balldan 0 olardi.

Endi uch qism qo'shiladi: EMA 0.30, ADX 0.30, **yuqori TF 0.40**. Katta
rasm eng katta ulushni oladi, chunki u vaqtinchalik pasayishga
aldanmaydi. Yuqori TF hisoblanmasa uning ulushi qolgan ikkitasiga
taqsimlanadi — hisoblab bo'lmagan narsa jarimaga aylanmasligi kerak
(0.3-band).

### Qayta kalibrlash

Ball taqsimoti o'zgardi, shuning uchun chegara QAYTA o'lchandi
(40-bo'limdagi xato takrorlanmasligi uchun):

| | Avval | Keyin |
|---|---|---|
| Nomzod chiqdi | 12/27 | **15/27** |
| Eng yuqori ball | 59.7 | **63.7** |
| Mediana | 53.0 | 58.1 |

Chegaralar (50 / 55) **o'zgarmadi**: taqsimot 51 va 58 orasida tekis,
ya'ni bu oraliqdagi har qanday qiymat bir xil natija beradi. Sun'iy
ma'lumotdagi 15 ta nuqtaga moslab raqamni surish — o'sha ma'lumotga
moslashib qolish bo'lardi. Haqiqiy taqsimot `/panel` -> 🔇 dagi "eng
yuqori ball" qatorida ko'rinadi.

### Ortga qaytarish

Ikkala to'siq ham konfiguratsiyada qoldi va yoqilishi mumkin:

```yaml
analysis:
  require_htf_alignment: false
  indicators:
    require_confirmation: false
```

Kod o'chirilmadi, chunki qaror o'lchovga tayanadi va o'lchov
o'zgarishi mumkin.

---

## 42. Timeframe, support jari va skalping oynasi

Jonli o'lchov (5524 ta tekshiruv, 24 soat) uchta alohida narsani
ko'rsatdi.

### 1. Ball chegarasi endi ishlayapti, lekin nomzodlar 55 da qotgan

```
• Ball chegaradan past — 482 marta (9%)
   ↳ eng yuqori ball 55, o'rtacha 45
• Risk Engine to'xtatdi — 44 marta (1%)
```

40 va 41-bo'limlardan keyin nomzodlar soni **47 dan 482 ga** chiqdi va
44 tasi chegarani o'tib Risk Engine'gacha yetdi. Ya'ni zanjir oxirigacha
ishlayapti.

Lekin eng yuqori ball **aynan 55** — chegaraning o'zi. Nomzodlar
chegaraga tegib turibdi, o'tolmayapti.

### 2. Support jari: 60% rad etish bir foizlik farq ustida

Eng katta to'siq — `zone_position`, 3338 marta (60%). Tafsilotlar:

```
• BTC: Narx Premium zonada (51%) — kirish uchun qimmat
• ETH: Narx Premium zonada (63%) — kirish uchun qimmat
```

BTC **51%** da rad etilgan. Chegara — muvozanat chizig'i, ya'ni 50%.
Bir foiz.

Bu JAR: 49.9% — ruxsat, 50.1% — butunlay rad. Holbuki ball allaqachon
chuqurlikni **darajali** baholaydi (`depth`: 50% da 0 ball, Support'da
to'liq ball). Ya'ni chuqurroq qaytish baribir yuqoriroq o'ringa
chiqadi — qat'iy jar shunchaki chetdagi nomzodni yo'q qilardi.

`entry_max_range_pct: 55.0` qo'shildi. Yumshatish, ochib yuborish emas:
diapazonning yuqori qismi baribir yopiq, support va diapazondan chiqish
shartlari kuchida qoladi.

### 3. Timeframe: 15m da tuzilma va risk qoidasi turli shkalada edi

Bu — 32-34, 37 va 40-bo'limlardagi naqshning yana bir ko'rinishi.

| | 15m | 1h |
|---|---|---|
| ATR (narxga nisbatan) | ~0.5% | ~1-2% |
| Support zonasigacha masofa (1 ATR) | ~0.5% | ~1-2% |
| Talab qilingan Stop (3.3-band) | **kamida 1%** | kamida 1% |

15m da support zonasi narxga shunchalik yaqin ediki, undan qurilgan
Stop 1% lik eng kam talabga **yetmasdi**. Ya'ni tuzilma bir shkalada,
risk qoidasi boshqa shkalada ishlardi. Jonli ma'lumotda "Darajalar risk
qoidasiga sig'madi" 112 marta chiqdi.

1h da ikkalasi bir shkalaga tushadi. Qo'shimcha foyda: 1h zonalari
kamroq shovqinli.

Yangi to'plam:

```yaml
entry_timeframe: "1h"
htf_confirmation: ["4h"]        # to'siq emas, ballga qo'shiladi (41-bo'lim)
market_health_timeframe: "1d"   # ALOHIDA
```

**Nima uchun `market_health_timeframe` alohida.** `compute_health()`
kunlik seriyani `htf_confirmation` orqali olardi. Tasdiq timeframelari
qisqarganda u kirish timeframeiga tushib ketardi va bozor kengligi
soatlik o'lchovga aylanardi — indeks kun bo'yi tebranib, ma'nosini
yo'qotardi. Kenglik "katta rasm" savoli, tasdiq esa "kirish" savoli:
bir manbadan ikki xil savolga javob so'ralmasligi kerak (34-bo'lim
naqshi).

Sikl oralig'i ham avtomatik 15 daqiqadan 1 soatga o'tdi — sham
yopilmaguncha tahlil natijasi o'zgarmaydi.

### 4. Skalping oynasi 45 daqiqadan bir kunga

```
• Skalping oynasi yopiq — 5114 marta
```

Oyna kuniga 45 daqiqa, ya'ni kunning **3%** i. Qolgan 97% da strategiya
umuman ishlamasdi va bu yozuv dashboardda hamma narsadan ko'p chiqardi.

`signal_window_minutes: 45 -> 1440`.

**Almashuv ONGLI.** Kech kirish yomonroq kirish: diapazon kun boshida
qurilgani uchun kunning oxiridagi buzilish "eskirgan" diapazonga
nisbatan o'lchanadi. Buzilish kuchi, hajm va risk qoidasi baribir talab
qilinadi, lekin kech kirishning zarari endi ball orqali emas, umuman
qoplanmaydi. Postmortem (3.8-band) shu strategiyaning natijasini
alohida ko'rsatadi — bir-ikki haftadan keyin shu raqamga qarab qaror
qilish kerak.

### Testlar konfiguratsiyaga bog'landi

Timeframe o'zgarishi 11 ta testni sindirdi va **hammasi bir sababdan**:
qiymat testga yozib qo'yilgan edi (`== "15m"`, `19_200`,
`build_dataset(..., ["15m", "1h", "4h", "1d"])`).

Bularning ba'zilari jimgina sinardi: backtest dataseti kerakli
timeframeni saqlamay, `steps=0` qaytarardi — xato emas, shunchaki bo'sh
natija. Hammasi endi konfiguratsiyadan hisoblanadi.

---

## 43. "Skalping nega yana yopiq?" — ekran sozlamadan orqada qolgan edi

### Savol

Oyna 45 daqiqadan bir kunga uzaytirilgandan keyin ham ekranda shu
turardi:

```
⏱ Vaqt shartlari
Skalping oynasi kuniga atigi 45 daqiqa ochiq...
• Skalping oynasi yopiq — 2247 marta
```

### Javob: o'zgarish ishlagan, MATN o'zgarmagan

Izoh matni `bot/i18n/uz.json` da **qotib** yozilgan edi: "kuniga atigi
45 daqiqa". Sozlama 1440 ga o'tdi, matn esa 45 da qoldi. Ya'ni ekran
eski dunyoni tasvirlab turardi.

O'zgarish ishlaganini raqamlar isbotlaydi — `window` dan KEYINGI barcha
bosqichlar keskin o'sdi:

| Bosqich | Oldin | Keyin |
|---|---|---|
| `range` (diapazon mos emas) | 135 | **913** |
| `volume` (hajm yetarli emas) | 30 | **210** |
| `breakout` (buzilmagan) | 3 | **36** |

Bu sonlar faqat `window` dan o'tilganda o'sishi mumkin.

Qolgan 2247 ta yozuv esa — joylashtirishdan OLDINGI davrga tegishli
(hisobot 24 soatni qamraydi). `_find_session_open()` faqat BUGUNGI
ochilish shamini qaytaradi, ya'ni `opened_at + 1440` doim ertangi
kunga tushadi va shart hech qachon bajarilmaydi.

Endi matn sozlamadan quriladi: `kun bo'yi`, `4 soat`, `45 daqiqa`.

### Ikkinchi topilma: "eng yuqori ball" chalg'itardi

```
• Ball chegaradan past — 955 marta
   ↳ eng yuqori ball 55, o'rtacha 44
```

Chegara ham 55. Ya'ni "ball aynan chegarada to'xtab qolgan" degan
xulosa chiqadi — va aynan shu xulosa noto'g'ri tuzatishga olib borishi
mumkin edi (yana chegarani pasaytirish).

Sabab oddiy: bu ustun **faqat RAD ETILGANLARNI** sanaydi
(`reason == "threshold"`). Rad etilganlarning bali ta'rifiga ko'ra
chegaradan past. Ya'ni ko'rsatilgan qiymat hech qachon chegaradan
oshmaydi — u "shift" emas, **shipning o'zi**.

Haqiqiy holat qo'shni qatorda edi: `Risk Engine to'xtatdi — 103 marta`.
Ya'ni 103 ta nomzod chegarani O'TGAN va keyingi qatlamda to'xtagan.

Matn tuzatildi: "chegaraga eng yaqini". Raqam o'sha, ma'nosi to'g'ri.

### Naqsh

Ikkalasi ham bir xil xatoning ko'rinishi: **o'lchov va uning izohi
turli manbadan**. 34-bo'limda sarlavha va holat ikki manbadan kelib
bir-biriga zid chiqqan edi; bu yerda raqam sozlamadan, izoh esa qo'lda
yozilgan matndan kelgan. Raqam to'g'ri, izoh yolg'on.

---

## 44. DEADLOCK: tizim birinchi signalini chiqara olmasdi

72 soat, birorta signal yo'q. Dashboard oxirgi to'siqni ko'rsatdi:

```
• Risk Engine to'xtatdi — 103 marta (2%)
```

103 ta nomzod butun zanjirni o'tib, oxirgi qatlamda to'xtagan. Qaysi
qoida to'xtatgani esa ko'rinmasdi.

### Zanjir

```
Ochiq signal yo'q
      ↓
SignalWatcher._sync_subscription() -> stream.subscribe(ochiq signallar coinlari)
      ↓
obuna BO'SH  ->  WebSocket hech narsa yubormaydi
      ↓
PriceCache bo'sh  ->  age_seconds("BTC") = None
      ↓
_build_input():  yosh None -> price_ages ga coin UMUMAN qo'shilmaydi
      ↓
FreshDataRule:  "Narx oqimi holati noma'lum" -> BLOKLAYDI
      ↓
Yangi signal yo'q  ->  Ochiq signal yo'q
```

Aylana yopiq. Tizim bir marta 0 ta ochiq signalga tushsa, **abadiy
shu yerda qoladi**. Ya'ni u birinchi signalini hech qachon chiqara
olmasdi — 47 ta nomzod ham, 482 ta ham, 955 ta ham farq qilmasdi.

### Nima uchun bu 0.3-bandning to'g'ri qo'llanishiga o'xshab turardi

`FreshDataRule` fail-safe qoida: "narx holati noma'lum bo'lsa signal
berma". Mantiq to'g'ri. Xato — **qaysi ma'lumot tekshirilayotganida**.

| Qatlam | Qaror uchun nima ishlatiladi | Nima tekshirilardi |
|---|---|---|
| Sikl (signal berish) | **sham** (`_joriy_narx()` oxirgi sham yopilishi) | tik oqimi |
| Kuzatuvchi (TP/Stop) | tik oqimi | tik oqimi ✓ |

Kuzatuvchida tekshiruv to'g'ri va ishlaydi — u yerda signal ochiq
bo'lgani uchun obuna ham bor. Siklda esa **ishlatilmaydigan
ma'lumotning holati** so'ralardi.

### Yechim

Har qatlam O'ZI ISHLATADIGAN ma'lumotni tekshiradi. Sikl uchun narx
yoshi shamdan hisoblanadi (tik bor bo'lsa u afzal — aniqroq).

Chegara ham to'g'rilandi. `stale_price_seconds: 90` tik uchun
mo'ljallangan; 1 soatlik sham esa **tabiatan** 1 soatgacha "eski"
bo'ladi. 90 soniyalik chegarani unga qo'llash — har doim "eskirgan"
degani. Endi chegara timeframedan hisoblanadi:
`entry_timeframe × stale_candle_multiplier` (1h × 2 = 2 soat).

### Ko'rinmagan to'siqni tuzatib bo'lmaydi

Dashboard 13 ta qoidani bitta "Risk Engine to'xtatdi" qatoriga
yig'ardi. Endi bosqich nomiga sabab qo'shiladi:

```
• Korrelyatsiya: shu guruhda signal bor (4.3) — 61 marta
• Bozor tekis — trend yo'q (4.4) — 28 marta
• Narx ma'lumoti eskirgan (0.3) — 14 marta
```

`test_stage_labels.py` skaneri `BlockReason` ni ham qamrab oladi:
yangi qoida qo'shilib nomi unutilsa, test darhol aytadi.

### "Bugungi ochilish shami hali yo'q" — bu xato EMAS

`_find_session_open()` faqat BUGUNGI 00:00 shamini qaytaradi. UTC
yarim tunidan keyingi birinchi siklda o'sha sham hali yo'q — 49 ta
yozuv aynan shu bitta siklga to'g'ri keladi (24 sikl × ~74 coin
ichidan bittasi). Kun davomida strategiya normal ishlaydi.

### Naqsh

Yana bir marta: **bir manba ikki xil savolga javob berishga
majburlangan**. 34-bo'limda sarlavha va holat, 42-bo'limda kenglik va
tasdiq, bu yerda esa tik oqimi ham kuzatuv, ham signal qarori uchun
ishlatilgan. Har safar yechim bir xil: savolni to'g'ri manbadan so'rash.

---

## 45. Mean reversion o'z qiymatlariga qaytarildi

Bir hafta jonli ishlagan bot 0 ta signal berdi. Tashqi maslahatdan keyin
sabab aniqlandi va u sozlamada emas, **strategiya turi bilan qoidalar
turi o'rtasidagi nomuvofiqlikda** edi.

`classic_ta` — **mean reversion** ("arzon zonaga qaytganda ol"). Unga
qo'yilgan qoidalar esa **trend/breakout** strategiyalariga xos edi:

| Qoida | Qiymat | Kimga xos |
|---|---|---|
| Kirish timeframei | 1 soat | skalping/intraday |
| Stop | qat'iy 1–5% | universal, coinga bog'liq emas |
| Nisbat | majburiy 1:3 | trend following |

### Uchta tuzatish

**1. Timeframe: 1h → 4h (tasdiq 4h → 1d, salomatlik 1d → 1w).**
1 soatlik grafik mean reversion uchun shovqinli. `opening_range_scalp`
tegilmadi — u o'zining kunlik ochilish mantig'i bilan 15m da ishlaydi.

**2. Stop: qat'iy foiz → ATR ko'paytmasi.**
Stopning maqsadi bozor shovqinidan himoya, shovqin esa ATR bilan
o'lchanadi. 1% stop BTC uchun ~1.2 ATR (mantiqiy), volatil altcoin
uchun ~0.3 ATR (shovqin yeydi), barqaror coin uchun ~3 ATR (keraksiz
keng, yaxshi setuplarni rad etadi).

Endi `stop_atr_mult: 1.75`. Foiz oralig'i (1–5%) **yo'qolmadi** —
ikkinchi darajali xavfsizlik cheklovi sifatida qoladi.

Tuzilmaviy himoya ham saqlandi: Stop ATR masofasi va support
zonasidan pastdagi nuqta — **ikkalasidan uzoqrog'i**. Zona ichida
qolgan Stop narx support'ga tegib qaytganda ham ishlardi, ya'ni
strategiyaning o'z asosini buzardi.

**3. Nisbat: global 1:3 → strategiya darajasida 1:1.5.**
Mean reversion tabiiy ravishda diapazon o'rtasiga qaytganda yopiladi —
bu 1:1..1:1.5 beradi. 1:3 talab qilish bu strategiya uchun deyarli hech
qachon bajarilmaydigan shart edi. Qiymat endi `ClassicTaConfig` da:
boshqa turdagi strategiya qo'shilsa, u o'zinikini saqlaydi.

### Yo'l-yo'lakay topilgan ikkita tuzoq

Ikkalasi ham tuzatishlarni **jimgina bekor qilardi**.

**A. Ball hisobi eski nisbatni ko'rardi.**

`Scorer` global `trade_rules` ni olardi. Ya'ni darajalar 1:1.5 bo'yicha
quriladi, ball esa 1:3 bo'yicha hisoblanadi:

```
haqiqiy R/R 1:1.50
  global qoidalar    -> 0.0/15 ball  "R/R 1:1.5 — minimal 1:3 dan past"
  classic_ta qoidalari -> 7.5/15 ball
```

15 balldan ayrilish chegaradan (55) o'tishni imkonsiz qiladi. Endi
qurish, ball va tekshiruv — **uchalasi bir manbadan** (`classic_ta_rules()`).

**B. Haftalik salomatlik indeksi bozor kengligini o'ldirardi.**

`timeframe_trend()` sham soni EMA davridan kam bo'lsa `FLAT` qaytaradi —
ya'ni "aniqlab bo'lmadi" va "ko'tarilishda emas" bir xil javob beradi.

Haftalik timeframeda EMA200 uchun **200 hafta (~3.8 yil)** kerak. Ko'p
altcoinlarda bunday tarix yo'q — ular jimgina "ko'tarilishda emas" deb
sanalardi, bozor kengligi sun'iy ravishda tushardi va indeks 40 dan
pastga o'tib **signalni butunlay to'xtatardi**. Ya'ni bir hafta
sukunatdan keyin yana sukunat, faqat boshqa eshikdan.

0.3-band: noaniqlik dalil emas. Aniqlab bo'lmagan coin hisobga umuman
kirmaydi.

### Backtest hisoboti to'ldirildi

Tuzatishlarni tekshirish uchun so'ralgan jadval endi backtest chiqishida
bor: **voronka** (bosqich / kirdi / rad / o'tdi / o'tish %), **profit
factor** va **haqiqatda olingan o'rtacha R/R**.

Win-rate o'zi yetarli emas: 80% g'alaba, lekin har zarar g'alabadan uch
barobar katta bo'lsa strategiya zarar keltiradi.

### Nima o'lchanmadi

**Backtest bu muhitda yurgizilmadi** — tashqi bozor ma'lumoti bloklangan
(`403 Forbidden`). Ya'ni prompt talab qilgan bosqichma-bosqich
tekshiruv (0→1→2→3 qadam) **serverda bajarilishi kerak**.

Mavjud dalil: 1038 ta test yashil va kalibrlash skripti chegaralar
erishiladigan ekanini tasdiqlaydi (eng yuqori ball 63.8, chegara 55).
Bu **strategiya foydali** degani emas — faqat "zanjir yopiq emas"
degani.

---

## 46. Salomatlik BANDI ham erishib bo'lmas edi

Admin savol berdi: "77 ball bo'lganda ham signal bermayapti". Savol
ikkita narsani ochdi.

### 1. Panelda ikkita 0–100 raqam bor va ular chalkashadi

| Raqam | Nima qiladi |
|---|---|
| **Bozor Salomatligi: 77/100** | qaysi CHEGARA ishlashini tanlaydi |
| **Nomzod bali: 0..~64** | ana o'sha chegara bilan TAQQOSLANADI |

"77/100 — signal beriladi, lekin ehtiyotkorroq" degani "ball 77" emas.
Ikkalasi ham `/100` ko'rinishida yozilgani uchun farqni ko'rish qiyin.

### 2. Asosiy topilma: YUQORI band hech qachon ochilmagan

Jonli botda indeks: `70 → 70 → 71 → 71 → 71 → 71 → 73 → 77`.
YUQORI band esa **80** talab qilardi.

Ya'ni `threshold_high_health: 50` sozlamasi **bir marta ham
qo'llanilmadi**, "moslashuvchi chegara" amalda doim **55** bo'lib
qoldi.

### Nima uchun indeks 80 ga chiqmaydi — arifmetika

Kenglik omili **25 ball** turadi. Jonli holatda kenglik **5%** edi:

```
kenglik omili       :  1.2 / 25   ->  23.8 ball YO'QOTILDI
qolgan 4 omil       : 75.8 / 75   ->  deyarli MUKAMMAL
                      ─────────
                        77 = SHIFT
```

Indeks o'z matematik shiftida turgan — qolgan omillar to'liq ishlagan,
ko'proq chiqarib bo'lmasdi.

| Bozor kengligi | Erishish mumkin bo'lgan max |
|---|---|
| 0% | 75.0 |
| 5% (jonli holat) | 76.2 |
| 20% | 80.0 |
| 50% | 87.5 |

**YUQORI band uchun 74 ta coinning kamida 20% i ko'tarilishda bo'lishi
kerak.** Hozir — 5%, ya'ni ~4 tasi.

### Naqsh: bitta omil butun bandni qulflaydi

Bu — 40-bo'limdagi "erishib bo'lmas chegara" xatosining ikkinchi
ko'rinishi, bir daraja yuqorida:

- 40-bo'lim: ball chegarasi (80) ball funksiyasining shiftidan (64) baland
- bu yer: salomatlik bandi (80) indeksning shiftidan (76) baland

Ikkalasida ham sabab bir xil: **chegara o'lchovdan emas, "mantiqiy
eshitilgani uchun" tanlangan.**

`health_high_min: 80 → 70`. 70 — kuzatilgan sakkizta o'lchovning
hammasini qamraydi.

### Test bu xatoni uchinchi marta takrorlanishiga yo'l qo'ymaydi

`test_chegara_erishiladi.py` ga ikkita invariant qo'shildi:

1. **Kengliksiz ham erishiladi.** Bitta omil (25 ball) butun bandni
   qulflab qo'ymasligi kerak: kenglik nolga yaqin bo'lganda ham indeks
   75 ga chiqadi, ya'ni band chegarasi shundan past bo'lishi shart.
2. **Kuzatilgan oraliq bandga tushadi.** Jonli botdan olingan haqiqiy
   qiymatlar (70..77) YUQORI bandga tushishi kerak.

Eski qiymat (80) bilan ikkala test ham yiqiladi.

### Ochiq qolgan savol

Kenglik 5% — bu **haqiqatan zaif bozor**: 74 coindan atigi 4 tasi
ko'tarilish trendida. Va aynan bunday bozorda "arzon paytda ol"
strategiyasi eng xavfli: har bir support zonasi buzilishi mumkin.

Ya'ni signal chiqmasligining bir qismi nosozlik emas, **tizim to'g'ri
ehtiyot bo'lgani**. Chegarani pasaytirish signal beradi, lekin
tushayotgan bozorda xarid qilish xavfini ham oshiradi. Buni faqat
backtest hal qila oladi.

---

## 47. ATR tuzatishi o'z shiftiga urildi

Yangi sozlamalar bilan birinchi kun. Ikkita yangi to'siq va bitta
chalkashlik.

### 1. "Darajalar risk qoidasiga sig'madi" 146 dan 299 ga chiqdi

ATR asosli Stop joriy qilindi (`stop_atr_mult: 1.75`), lekin foiz
oralig'i (1–5%) o'zgarmadi. Arifmetika shafqatsiz:

```
Stop = ATR × 1.75
5% shift  ->  ATR 2.86% dan oshsa Stop AVTOMATIK rad etiladi
```

4 soatlik grafikda altcoin ATR'i 2.86% dan tez-tez oshadi. Ya'ni
"ikkinchi darajali xavfsizlik cheklovi" **asosiy filtrga aylanib, ATR
tuzatishining o'zini bekor qilardi**.

`max_stop_distance_pct: 5.0 → 8.0`. Endi ATR 4.57% gacha ruxsat.

Xavf oshmaydi: pozitsiya hajmi `xavf puli / Stop%` formulasi bilan
avtomatik kichrayadi (5.1-band). Keng Stop — kichik pozitsiya.

### 2. Salomatlik bandi yana bir ball bilan yopiq qoldi

46-bo'limda band 80 dan 70 ga tushirilgan edi. Haftalik timeframega
o'tgach indeks **69** ga tushdi:

```
76 → 76 → 76 → 76 → 76 → 77 → 69 → 69
                                  ↑ band 70, ya'ni YOPIQ
```

Sabab: haftalik o'lchovda namuna o'zgardi — 74 coindan atigi **21 tasi**
200 haftalik tarixga ega. Boshqa namuna, boshqa qiymat.

`health_high_min: 70 → 65`. Kuzatilgan oraliq 69..77, ya'ni pastki
chetdan zaxira bor.

**Naqsh:** chegarani kuzatilgan oraliqning aynan chetiga qo'yish —
xato. Bir o'lchov surилsa band yana yopiladi. Zaxira qoldirish kerak.

### 3. Diagnostika: qaysi tomonga sig'madi?

"Darajalar risk qoidasiga sig'madi" — Stop juda **yaqin** bo'lgani
uchunmi yoki juda **uzoq** bo'lgani uchunmi? Ikkalasi qarama-qarshi
tuzatish talab qiladi, dashboard esa ikkalasini bitta qatorga
yig'ardi.

Endi bosqich ajratilgan:

```
• Stop juda YAQIN — support zonasi yaqin
• Stop juda UZOQ — ATR keng, shift 8% da
```

Bu safar men shiftni arifmetika bilan hisoblab tuzatdim. Keyingi safar
raqam dashboardda turadi — taxmin qilish shart bo'lmaydi.

### 4. Skalping matni chalkash edi

Admin savol berdi: "skalping kunlik sham ochilishiga bog'liq deyapti,
biz uni olib tashlagan edik-ku". Bu tushunmovchilik, xato emas — lekin
matn aybdor.

Biz **oynani** kengaytirdik (45 daqiqa → kun bo'yi). Strategiyaning
o'zi esa kunlik ochilish shamiga tayanadi — u shu shamdan diapazon
quradi, bu uning ta'rifi. "Bugungi ochilish shami hali yo'q" yozuvi
faqat UTC yarim tunidan keyingi birinchi siklda chiqadi.

Matn aniqlashtirildi: endi bu qator qachon chiqishi ochiq yozilgan.

---

## 48. BTC filtri hech qachon ulanmagan edi — bir haftalik sukunatning sababi

Per-qoida nomlari qo'shilgach dashboard nihoyat oxirgi to'siqni
ko'rsatdi:

```
• BTC tushmoqda (4.5) — 119 marta (4%)
```

Voronka to'liq:

| Bosqich | Kirdi | Rad | O'tdi | O'tish |
|---|---|---|---|---|
| Zona joylashuvi | 1428 | 603 | 825 | 57.8% |
| Darajalar | 825 | 299 | 526 | 63.8% |
| Ball chegarasi | 526 | 407 | 119 | 22.6% |
| **BTC filtri (4.5)** | **119** | **119** | **0** | **0.0%** |

**Chegaradan o'tgan 119 ta nomzodning hammasi bitta qoida bilan
to'xtatilgan.**

### Sabab: e'lon qilingan, lekin ulanmagan

`BtcMarketRule` bor. `BtcFilterConfig` bor.
`CycleInput.btc_change_24h_pct` maydoni ham bor. Lekin uni
**hech kim to'ldirmasdi** — runner `CycleInput` ni yig'ayotganda bu
maydonni umuman uzatmasdi.

Qiymat doim `None` bo'lib qolardi va qoida fail-safe tarmog'iga
tushardi:

> "BTC holati noma'lum — umumiy bozor filtri tekshirilmadi."

Fail-safe to'g'ri yozilgan (0.3-band: noaniqlikda signal berma). Lekin
noaniqlik **doimiy** edi, ya'ni qoida hech qachon o'z ishini
qilmasdi — u shunchaki hamma narsani bloklardi.

### Nima uchun bir hafta ko'rinmadi

Uchta qatlam uni yashirdi:

1. **Ball chegarasi erishib bo'lmas edi** (40-bo'lim) — nomzodlar bu
   yergacha yetmasdi.
2. **Deadlock** (44-bo'lim) — `FreshDataRule` birinchi bo'lib
   bloklardi.
3. **Dashboard 13 ta qoidani bitta qatorga yig'ardi** — "Risk Engine
   to'xtatdi" deb yozardi, qaysi biri ekanini aytmasdi.

Har uch to'siq olib tashlangandan keyingina asl sabab ko'rindi.

### Naqsh: sakkizinchi marta

"E'lon qilingan, lekin ulanmagan" naqshi bu loyihada sakkizinchi marta
uchradi: `python-dotenv`, `alembic`, `numpy/pandas`, `risk_blocks`
jadvali, `suggestion=` parametri, BTC dominance, `RejectedCandidate.score`,
va endi `btc_change_24h_pct`.

Har safar bir xil: tip bor, konfiguratsiya bor, ishlatuvchi kod bor —
faqat qiymatni **hisoblab beruvchi** qism yo'q. Va har safar natija
jimgina: xato yo'q, log toza, tizim shunchaki ishlamaydi.

### Tuzatish

24 soatlik o'zgarish shamlardan hisoblanadi. Timeframe
konfiguratsiyadan olinadi, lekin u yuklanmagan bo'lsa kirish
timeframeiga tushiriladi — aks holda sozlama o'zgarganda filtr yana
jimgina "noma'lum" holatiga qaytardi (bu allaqachon sodir bo'lgan edi:
`btc_filter.timeframe: "1h"`, kirish timeframei esa 4h ga o'tgan).

BTC shamlari **kafolatlangan**: u halol ro'yxatda bo'lmasa ham alohida
yuklanadi. Aks holda likvidlik filtri yoki admin qarori filtrni
jimgina o'chirib qo'yishi mumkin edi.

Test tuzatishsiz yiqiladi: `CycleInput.btc_change_24h_pct` `None`
bo'lsa, "4.5-band filtri hamma signalni bloklaydi" deb aytadi.

---

## 49. Tizimli sweep: yana ikkita "ulanmagan" topildi

BTC filtri sakkizinchi marta bo'lgach, tasodifiy qidirish o'rniga
**tizimli tekshiruv** yozildi: `CycleInput` va `RiskContext` ning har
bir maydoni uchun "uni kim to'ldiradi?" degan savol.

### Natija

| Maydon | Standart | To'ldiriladimi | Oqibat |
|---|---|---|---|
| `btc_change_24h_pct` | `None` | ❌ (48-bo'lim) | HAMMA signalni bloklardi |
| `daily_loss_pct` | `0.0` | ❌ | himoya o'lik |
| `weekly_loss_pct` | `0.0` | ❌ | himoya o'lik |
| `consecutive_stop_until` | `None` | ❌ | qo'shimcha pauza ishlamaydi |
| qolgan 10 ta | — | ✅ | — |

`RiskContext` to'liq ulangan — bo'shliq faqat runner chegarasida edi.

### Teskari muammo: fail-open

BTC filtri **fail-safe** edi (noaniqlik → blokla). Kunlik zarar
chegarasi esa **fail-open**: standart `0.0` "bugun zarar yo'q" degani,
ya'ni qoida hech qachon ishlamaydi.

Bu signal to'smaydi — shuning uchun uni sezish ham qiyin. Lekin
oqibati jiddiyroq: `daily_loss_limit_pct: 3.0` sozlamasi bor, admin
uni ko'radi va himoya bor deb o'ylaydi. Amalda **strategiya qancha
zarar keltirsa ham signal berishda davom etardi**.

Endi yopilgan signallarning SOF natijasidan hisoblanadi. Sof, faqat
zararlar emas: kun +5% va −4% bilan o'tgan bo'lsa, kun yomon o'tmagan
— gross hisob foydali kunni ham to'xtatib qo'yardi.

`consecutive_stop_until` ataylab qoldirildi: asosiy himoya
(`consecutive_stops`) ishlaydi, bu esa qo'shimcha vaqtli pauza. Uni
ulash uchun holat saqlanishi kerak — alohida ish.

### Ikkinchi sinf: sozlama yuklanmaydigan timeframega ishora qiladi

`btc_filter.timeframe: "1h"` qolib ketgan edi. Kirish 4h ga o'tgach bu
seriya umuman yuklanmay qoldi va filtr jimgina fail-safe holatiga
tushdi. Men 48-bo'limda zaxira yo'l qo'ygandim (kirish timeframeiga
tushish), lekin sozlamaning o'zi hamon **yolg'on** gapirardi.

`test_timeframe_izchilligi.py` bu sinfni qulflaydi: sozlamadagi har
bir timeframe yuklanadigan to'plamda bo'lishi shart. Eski qiymat
bilan test yiqiladi.

Bu — o'sha "bir manba, ikki haqiqat" naqshi: sozlama bir narsani
aytadi, yuklovchi boshqasini qiladi.

### Nima uchun bu sweep muhim

Sakkizta "ulanmagan" holatning har biri **jimgina** buzilardi: xato
yo'q, log toza, testlar yashil. Faqat tizim ishlamaydi.

Endi ikkita test bu sinfni doimiy qo'riqlaydi:
- `test_btc_ozgarishi_siklga_uzatiladi` va `test_kunlik_zarar_siklga_uzatiladi`
  — qiymat haqiqatda to'ldirilyaptimi
- `test_sozlamadagi_timeframe_yuklanadi` — sozlama mavjud ma'lumotga
  ishora qilyaptimi

---

## 50. Veb-sayt qatlami: ranglar TAXMIN qilinmadi

`web/` — Next.js sayti, botning **qo'shimcha interfeysi**. `core/` (miya)
unga umuman tegmaydi: sayt bazani o'qiydi, hisoblash logikasi joyida qoladi.

Dizayn tizimida bitta qoida qat'iy bajarildi: **birorta rang "ko'zga
chiroyli" deb tanlanmadi**. Hammasi `web/public/logo.jpg` faylidan aniq
koordinatalar bo'yicha o'lchandi — `web/scripts/logo_ranglari.py` shuni
qayta ishlab beradi (9x9 kvadrat MEDIANASI: JPEG siqilishi bitta pikselni
buzishi mumkin, mediana esa chidamli).

Logotipda yo'q bo'lgan uchta rang alohida belgilandi — sahifa foni
(qoraytirilgan), uzun matn toni va qizil. Ular "hisoblangan" deb
yozilgani muhim: keyinchalik kimdir "bu ham logotipdan-ku" deb
o'ylamasligi kerak.

### 4-naqsh yana urinib ko'rdi

`docs/ARXITEKTURA.md` da qayd etilgan to'rtinchi naqsh — "testdagi qattiq
yozilgan qiymat jimgina eskiradi" — bu yerda ham paydo bo'ldi. Men
kontrast nisbatlarini hujjatga QO'LDA yozdim va to'rttasi ham noto'g'ri
chiqdi: hisoblashda `#123772` ni ishlatgan edim, CSS da esa `#133C7C`
turardi.

Shuning uchun `web/scripts/kontrast.py` yozildi — u raqamlarni
`globals.css` NING O'ZIDAN o'qiydi (`var(...)` zanjirini ham yechadi) va
WCAG bo'yicha tekshiradi. Birinchi ishga tushirishdayoq u haqiqiy
kamchilikni tutdi:

    XATO  past holat yorlig'i    2.55 : 1  (kerak 3.0)

Ya'ni "🔴 Past" yorlig'i **ko'rinardi-yu, o'qib bo'lmasdi**. Bu ekranga
qarab sezilmaydigan xato — chunki rang "qizil" ekani ko'rinib turadi,
matn esa to'q ko'k fonda yo'qoladi. Natijada qizil ikkiga ajratildi:

| O'zgaruvchi | Vazifasi |
|---|---|
| `--rang-past-toq` | Bozor Salomatligi shkalasi — katta grafik, to'yingan bo'lishi kerak |
| `--rang-past` | Matn va yorliq — ochroq, chunki o'qilishi kerak |

Bu — 3-naqshning ("bitta manba, ikki xil ma'no") rang darajasidagi
ko'rinishi: bitta qizil ikkita boshqa savolga javob berayotgan edi.

### Sayt bazani QANDAY o'qiydi

Sayt bot bilan bir xil SQLite faylini ochadi va shu sababli bot bilan
**bitta Railway xizmatida** ishlaydi (`scripts/start.sh`). Sabab oddiy:
Railway'da doimiy disk faqat bitta xizmatga ulanadi. Saytni alohida
xizmatga yoki Vercel'ga qo'ysak, u faylni umuman ko'rmaydi.

Shu qaror ikkita o'zgarishni talab qildi:

- `core/storage/database.py` ga `PRAGMA busy_timeout=5000` qo'shildi.
  Endi bazaga IKKINCHI jarayon ham yozadi (admin paneli), busiz SQLite
  qulf band bo'lsa darhol "database is locked" beradi.
- `scripts/start.sh` baza manzilini BIR MARTA hisoblab, ikkala jarayonga
  eksport qiladi. `bot/hosting.py` uni Python jarayoni ICHIDA
  o'rnatardi — Node jarayoni buni ko'rmasdi.

### Yana uchta "ikki joyda bir xil qiymat" xavfi

Saytda bir nechta qiymat botdan takrorlanishi mumkin edi. Har birida
nusxa o'rniga MANBAGA murojaat qilindi:

| Qiymat | Manba | Nima uchun nusxa emas |
|---|---|---|
| Obuna muddati (1 / 30 kun) | `config/default.yaml` | Sayt eski qiymat bilan obuna ochsa, bir xil to'lov ikki xil muddat berardi |
| Bosqich nomlari (40+ ta) | `core/pipeline/context.py` | Yangi strategiya qo'shilsa saytda xom kod (`classic_ta:zones`) ko'rinardi |
| Salomatlik bandlari | `config/default.yaml` | Shkaladagi belgilar botning haqiqiy chegarasidan siljib ketardi |

Bosqich nomlari uchun Python fayli ish paytida o'qiladi va tahlil
qilinadi. Bu "g'alati" ko'rinadi, lekin muqobili — 40 qatorlik ro'yxatni
ikkinchi marta yozib qo'yish, ya'ni 1-naqshning o'zi.

### Testlar yana ikkita xatoni tutdi

**1. Baza yo'li — xato TEST TUFAYLI YASHIRINGAN edi.**

`sqliteYoli()` da shunday yozilgan edi:

```ts
const [, , yol] = xom.split(":///");   // massivda atigi 2 element bor!
```

Uchinchi element yo'q, ya'ni natija DOIM `undefined` edi va zaxira yo'lga
tushardi. Zaxira yo'l esa MUTLAQ manzillar uchun tasodifan to'g'ri
ishlardi — testda aynan mutlaq manzil (`/tmp/...`) ishlatilgani uchun
test yashil bo'lib turdi. Xato faqat brauzerda ochganda ko'rindi:

    TypeError: Cannot open database because the directory does not exist

SQLAlchemy'da `:///` nisbiy, `:////` mutlaq yo'lni bildiradi. Endi
`tests/env.test.ts` ikkala shaklni ham tekshiradi.

**2. Voronka tartibi teskari edi.**

`STAGE_LABELS` Python'da o'qish qulayligi uchun guruhlab yozilgan: avval
sikl darajasidagi bosqichlar (`threshold`, `risk_engine:*`), keyin
strategiyalar. Voronkani shu tartibda chizganda ekranda "Ball chegaradan
past" BIRINCHI o'rinda turdi — holbuki nomzod unga eng oxirida yetib
boradi.

Tuzatish ro'yxatni ko'chirib olish emas, QOIDA yozish bo'ldi
(`voronkaTartibi`): guruh bosqich kodining prefiksidan aniqlanadi
(strategiya -> ball -> risk engine). Yangi strategiya qo'shilsa, u
avtomatik to'g'ri joyga tushadi.

**3. `HCS_CONFIG_FILE` nisbiy yo'li.**

Bot ildizdan, sayt esa `web/` dan ishga tushadi. Bir xil
`config/default.yaml` qiymati ikkalasi uchun boshqa-boshqa faylni
bildirardi va sayt jimgina zaxira qiymatlarga o'tib ketardi. Endi nisbiy
yo'l doim loyiha ildiziga nisbatan hisoblanadi.

### Signal himoyasi: nima MUMKIN va nima MUMKIN EMAS

Telegramda `protect_content=True` bor — signalni nusxalash va boshqa
chatga yuborish to'silgan. Vebda bunday narsa **yo'q**: bu brauzer
imkoniyati emas, operatsion tizim darajasidagi cheklov. Yonidagi
ikkinchi telefon bilan ekranni suratga olishni esa hech qanday
texnologiya to'xtata olmaydi.

Shuning uchun `components/Himoya.tsx` da uchta QATLAM bor, har biri
boshqa ishni bajaradi:

| Qatlam | Nimani tutadi | Nimani tutmaydi |
|---|---|---|
| Fokus yo'qolganda xiralashtirish | `Win+Shift+S`, `Cmd+Shift+4`, telefonda boshqa ilovaga o'tish — hammasi sahifadan fokusni oladi | `PrintScreen` tugmasi (fokusni olmaydi) |
| Suv belgisi (Telegram ID) | Tarqalgan skrinshotda kimning IDsi turgani ko'rinadi | Nusxalashning o'zini to'xtatmaydi |
| Nusxalash / chop etishni bloklash | `Ctrl+C`, `Ctrl+P`, uzun bosish menyusi | Skrinshotni |

Eng kuchli to'siq — uchinchisi emas, **ikkinchisi**: pullik signal
xizmatlarida tarqatgan odamni aniqlash imkoniyati texnik to'siqdan ko'ra
ko'proq ish beradi. Shuning uchun izoh ham foydalanuvchiga ochiq
yoziladi: "narxlar ustida sizning IDingiz turadi".

Suv belgisi dastlab CSS `content` bilan qilingan edi va **umuman
ko'rinmadi**: kafel o'lchami (300x120) kartochka balandligidan katta
bo'lib, bitta qator ham sig'magan. Endi u SVG kafel — o'lchami matn
burchagiga moslangan va `tests/himoya.test.ts` uni tekshiradi.

### Admin panel: `/panel` bilan tenglashtirish

Boshlang'ich versiyada saytda faqat to'lov tasdiqlash va Bozor
Salomatligi bor edi. Endi uchta bo'lim qo'shildi va shu bilan
`/panel`ning ishlaydigan qismlari to'liq qamrab olindi:

| Bo'lim | Nima uchun aynan bu |
|---|---|
| Signal Xotirasi (3.8) | Hisobot faqat Telegramga yuborilardi — o'qilmay qolsa butunlay yo'qolardi |
| Narxlar (1.2) | Tarif narxini o'zgartirish uchun har safar botga kirish shart emas |
| Halol ro'yxat (1.4 / 3.4) | Universum 150 taga kengaydi; 150 ta coinni bot tugmalari orqali ko'rib chiqish amalda mumkin emas |

Risk sozlamalari ATAYLAB qo'shilmadi: u botda ham hali tayyor emas
("9-bosqich ustiga qo'shiladi" deb ochiq yozilgan). Saytda uni qilib
qo'yish ikki interfeys o'rtasida farq tug'dirardi.

### Hisobot endi SAQLANADI

`audit_reports` jadvali qo'shildi (`da6c8ea490c9` migratsiyasi). Nima
uchun kerak edi: `build_report()` har safar qaytadan hisoblanardi va
natija faqat Telegram xabari bo'lib qolardi. Ya'ni "o'tgan oy tizim
qanday ishlagan" degan savolga javob bermasdi.

Ikkita qaror muhim:

- **Bir kunda bitta qayd** (`report_date` + `period_days` bo'yicha
  upsert). Admin panelda tugmani o'n marta bossa, o'n xil qator paydo
  bo'lardi. Endi eng so'nggi holat yoziladi.
- **To'liq matn ham saqlanadi** (`rendered`), faqat raqamlar emas.
  Naqshlar tuzilmasi kelajakda o'zgarishi mumkin; matn esa o'sha paytda
  admin AYNAN NIMANI ko'rgani — bu audit izi.

Hisobotni saytda QAYTA HISOBLASH ataylab qilinmadi. Naqsh tahlili
`core/analysis/postmortem/` da yashaydi; uni TypeScriptda qayta yozish
ikki joyda ikki xil natija berishi mumkin edi — bu 1-naqshning eng
xavfli ko'rinishi bo'lardi, chunki farqni faqat kimdir ikkalasini
solishtirib ko'rgandagina sezardi.

### Yozuv amallarida adminlik IKKI MARTA tekshiriladi

Sahifa layout'ida bitta tekshiruv bor, lekin u yetarli emas: server
amali (server action) alohida HTTP so'rov bo'lib keladi va uni
to'g'ridan-to'g'ri chaqirish mumkin. Shuning uchun `amallar.ts` dagi har
bir funksiya `adminTekshir()` bilan boshlanadi.

Xuddi shu sabab bilan kiritilgan ma'lumot ham SERVERDA tekshiriladi:
`required` atributi brauzerda bir buyruq bilan olib tashlanadi. Buni
brauzerda sinab ko'rildi — `required` olib tashlangandan keyin ham
sababsiz qaror rad etildi.

## 51. Bosqichlar holati

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
| 13 | Postmortem (Signal Xotirasi) | ✅ |
| 14 | Shaxsiy portfel va statistika | ✅ |
| 15 | Hammasini bog'lash | ✅ |
| 16 | Backtest mexanizmi | ✅ (haqiqiy ma'lumot serverda kerak) |
| 17 | Yakuniy test, migratsiya, joylashtirish | ✅ |
