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

`classic_ta:zone_position` adminga hech narsa aytmaydi. Endi
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
xato. Bir o'lchov surilsa band yana yopiladi. Zaxira qoldirish kerak.

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

### Birinchi deploy: "Application failed to respond"

Domen ochilgach sayt javob bermadi. Uchta sabab topildi va ularning
eng yomon tomoni shu edi: **uchalasi ham aynan bir xil xatoni
ko'rsatardi**, ya'ni ularni bir-biridan ajratib bo'lmasdi.

**1. Port.** `start.sh` da `${PORT:-3000}` turgan edi. Railway domen
yaratganda maqsad porti sifatida **8080** ni taklif qiladi. `PORT`
o'zgaruvchisi qo'yilmasa, sayt 3000 da tinglardi, Railway esa 8080 ga
yo'naltirardi — ikkala tomon ham "men ishlayapman" deb turardi.
Standart qiymat 8080 ga o'zgartirildi.

**2. Bot va sayt bir-biriga bog'lab qo'yilgan edi.** Dastlab shunday
qilingandi: biri to'xtasa, ikkinchisi ham to'xtardi. Mantiq mudofaaviy
edi — "signal dvigateli o'lgan holda sayt eski ma'lumotni jonli qilib
ko'rsatgani yomonroq".

Amalda esa bu diagnostikani butunlay o'ldirdi. Bot bir soniya qoqilsa,
tashqaridan aynan o'sha "Application failed to respond" chiqardi va bu
xato **bot haqidami, sayt haqidami, qurilish haqidami** — bilib
bo'lmasdi. Ya'ni himoya vositasi ko'rlik manbaiga aylandi.

Endi mas'uliyat bo'lingan:

| Nima bo'ldi | Natija |
|---|---|
| Bot yiqildi | Sayt ishlab turaveradi; bot 5s, 10s, 20s... kutib qayta ko'tariladi |
| Bot 5 marta ko'tarilmadi | Konteyner chiqadi, Railway noldan qayta ko'taradi |
| Sayt yiqildi | Konteyner darhol chiqadi |

**3. Sog'liq tekshiruvi sahifaga qaratilgan edi** (`/kirish`). Sahifa
cookie o'qiydi va nazariy jihatdan 500 qaytarishi mumkin — o'shanda
Railway butun deploy'ni muvaffaqiyatsiz deb belgilab, ESKI versiyani
saqlab qolardi. Eski versiyada esa umuman HTTP server yo'q edi (bot
worker sifatida ishlardi), ya'ni xato yana o'sha xato bo'lib qaytardi.

Endi `/api/health` — hech narsaga bog'liq bo'lmagan manzil. U bitta
savolga javob beradi: "HTTP server ko'tarildimi?". Sog'liq tekshiruvi
ilovaning ISHLASHINI emas, TIRIKLIGINI o'lchashi kerak.

Uchalasi ham mahalliy tekshirildi: `PORT` o'zgaruvchisisiz sayt 8080 da
290ms da ko'tarildi; soxta token bilan bot uch marta yiqildi va sayt shu
davomida `/api/health` va `/kirish` uchun 200 qaytarib turdi.

### 502: mahalliy modul jarayonni o'ldirardi

Tarmoq loglari masalani hal qildi:

    GET /kirish             200
    GET /                   307
    GET /api/auth/telegram  502   <- faqat shu
    GET /favicon.ico        502   <- keyingi so'rov ham

**502, 500 emas** — bu hal qiluvchi farq. 500 bo'lsa ilova xato
qaytargan bo'lardi. 502 esa ilova UMUMAN javob bermaganini bildiradi:
jarayon o'ldi. Keyingi `/favicon.ico` ham 502 bo'lgani buni tasdiqlaydi
— favicon statik fayl, u bizning kodimizga umuman tegmaydi.

Farqi bitta edi: `/kirish` bazaga tegmaydi (kirmagan foydalanuvchida
`kirim()` erta qaytadi), `/api/auth/telegram` esa so'rovdagi BIRINCHI
baza murojaatini qiladi.

Tashxis manzili (`/api/health?tekshir=baza`) qo'yildi — u bazani
dinamik import va try/catch ichida ochardi. **U ham 502 qaytardi.**
Ya'ni xato JavaScript darajasida emas: `try/catch` uni tuta olmaydi,
chunki jarayon butunlay o'lmoqda.

Yagona nomzod — `better-sqlite3`, mahalliy (native) modul: ichida
`.node` ikkilik fayli bor. Serverda u bilan bog'liq har qanday
nomuvofiqlik (bundler ikkilik faylni ko'chirmasligi, Node ABI farqi,
kutubxona versiyasi) toza xato bermaydi, jarayonni o'ldiradi.

### Yechim: bog'liqlikni butunlay olib tashlash

`serverExternalPackages` qo'shish yetarli bo'lmadi. Shuning uchun
`better-sqlite3` **umuman olib tashlandi** va o'rniga `node:sqlite`
ishlatiladi — u Node'ning O'ZIGA kirgan (22.5 dan beri). Ikkilik fayl
yo'q, qurish bosqichi yo'q, ABI mosligi masalasi yo'q. Ya'ni muammoning
BUTUN SINFI yo'qoladi, bitta ko'rinishi emas.

Ko'chirishda ikkita farq bor edi:

| `better-sqlite3` | `node:sqlite` |
|---|---|
| `db.transaction(fn)` | yo'q — `BEGIN`/`COMMIT`/`ROLLBACK` qo'lda |
| `fileMustExist: true` | yo'q — fayl mavjudligi `existsSync` bilan tekshiriladi |

Ikkinchisi muhim: `node:sqlite` mavjud bo'lmagan faylni JIMGINA
YARATADI. Tekshirmasak, noto'g'ri `DATABASE_URL` da sayt bo'sh baza
ochib, "jadval yo'q" deb yiqilardi va asl sabab — yo'l noto'g'riligi —
ko'rinmay qolardi.

`lastInsertRowid` BigInt qaytishi mumkin, shuning uchun bitta joyda
(`songaAylantir`) oddiy songa aylantiriladi.

### Qurish: Node 22.10 va `node:sqlite` bayrog'i

`better-sqlite3` dan `node:sqlite` ga o'tgach qurish yiqildi. Uch urinish
ketdi va faqat oxirgisi to'g'ri chiqdi — chunki faqat oxirgisi
O'LCHOVGA tayandi.

1. **Taxmin:** "nixpacks eski Node berayotgandir" -> `nodejs_24`.
   Natija: `error: undefined variable 'nodejs_24'`. Railway ishlatadigan
   nixpkgs surati 2025-yil apreliga tegishli, Node 24 esa o'shanda hali
   chiqmagan edi.
2. **`nodejs_22` ga qaytarildi** va qurish buyrug'ining birinchi qatoriga
   `node --version` qo'yildi.
3. **O'lchov:** log `v22.10.0` deb yozdi va aniq xatoni ko'rsatdi:

       ERR_UNKNOWN_BUILTIN_MODULE: No such built-in module: node:sqlite
         at module evaluation (src/lib/db.ts:2:1)

`node:sqlite` Node **22.5** da qo'shilgan, lekin **22.13** gacha BAYROQ
ostida turgan. Mahalliy mashinada 22.22 bo'lgani uchun hammasi bayroqsiz
ishlardi — ya'ni bu xatoni bu yerda hech qachon ko'rib bo'lmasdi.

Yechim — `NODE_OPTIONS=--experimental-sqlite`:

| Qayerda | Nima uchun |
|---|---|
| `nixpacks.toml` `[variables]` | `next build` sahifalarni tahlil qilayotib modullarni ISHGA TUSHIRADI, ya'ni modul qurish paytida ham kerak |
| `scripts/start.sh` | ishlash payti; mavjud qiymat saqlanadi, bosib o'tilmaydi |

### Nima uchun importni kechiktirib bo'lmadi

Avval boshqa yo'l sinaldi: `node:sqlite` ni faqat ishlash paytida
yuklash, shunda qurish muhitidagi Node versiyasi ahamiyatsiz bo'lardi.
Ikki usul ham rad etildi:

    createRequire(import.meta.url)("node:sqlite")   -> Turbopack rad etadi
    require("node:sqlite")                          -> Turbopack rad etadi
    "Unsupported external type Url for commonjs reference"

Ya'ni Turbopack bilan `node:sqlite` ni faqat statik `import` shaklida
ishlatib bo'ladi. Bu `db.ts` da izoh bilan qayd etilgan, aks holda
keyingi safar yana o'sha yo'ldan urinilardi.

### Veb-panelda signal berish: jarayonlararo bo'shliq

Admin panelga signal berish qo'shildi. Bu oddiy forma emas edi —
oradan bitta jimgina xato chiqib turardi.

Kuzatuvchi yangi signalni faqat `watcher.add_signal()` orqali biladi, u
esa **jarayon ichidagi** chaqiruv. Sayt boshqa jarayonda ishlaydi, ya'ni
u yozgan signal bazada "ochiq" bo'lib turardi-yu, narxi kuzatilmasdi:
na TP, na Stop aniqlanardi. Tashqaridan hammasi joyida ko'rinardi.

Tarqatishda ham shunday: kartochka HAR BIR obunachi uchun alohida
yasaladi (miqdor uning balansidan hisoblanadi) va `protect_content=True`
bilan yuboriladi. Buni TypeScriptda takrorlash — kartochka mantig'ining
ikkinchi nusxasi demak edi.

**Yechim — mas'uliyatni bo'lish:**

| Kim | Nima qiladi |
|---|---|
| Sayt | Signalni bazaga yozadi, `broadcast_at` ni BO'SH qoldiradi |
| Bot (`web-signals` fon vazifasi, 1 daqiqada bir) | Kuzatuvga oladi, keyin tarqatadi va `broadcast_at` ni belgilaydi |

Ikki qadam ataylab shu tartibda: teskarisi bo'lsa, tarqatish yiqilganda
signal kuzatuvsiz qolardi.

`broadcast_at` — yangi ustun. Mavjud `broadcast_message_ids` ishlatilmadi:
uning nomi "xabar id lari" degani, "tarqatildimi" degani emas. Bitta
ustunni ikki ma'noda ishlatish bu loyihada allaqachon uchragan.

### Uchta nusxa o'rniga bitta

Tarqatish kodi ikki joyda edi (qo'lda signal va avtomatik sikl), veb
uchun uchinchisi kerak bo'lardi. Shuning uchun u `bot/services/broadcast.py`
ga chiqarildi — `broadcast_signal()` va `obunachilar()`. Aks holda
`protect_content` bir joyda unutilsa, o'sha yo'ldan ketgan signal
himoyasiz tarqalardi va buni hech kim sezmasdi.

### Video darslik: veb nimani QILA OLMAYDI

Darslik nomi, tarifi, tartibi va chop etish holati saytdan boshqariladi.
Lekin **video faylning o'zi botga yuklanadi**: Telegram fayl raqami
(`file_id`) faqat o'sha yerda paydo bo'ladi — bu Telegram cheklovi,
bizning tanlovimiz emas. Saytda dars yaratib, videoni keyin botdan
biriktirish mumkin; videosi yo'q darslar ro'yxatda alohida belgilanadi.

Tahrirlashda bo'sh `file_id` mavjud videoni O'CHIRMAYDI (`coalesce`) —
aks holda sarlavhani tuzatgan admin darsni ham buzib qo'yardi. Buni
`tests/signal.test.ts` tekshiradi.

## 51. Veb: bosh sahifa, Bozor Salomatligi sahifasi va kalkulyator

Uchta mustaqil o'zgarish, lekin har biri bitta xatoga qarshi qurilgan.

### 51.1. Diniy iqtibos YOZILMADI — placeholder qo'yildi

Bosh sahifada savdo ahkomlarini bilish zarurligi haqidagi diniy asos
turishi kerak. Uning aniq lafzi **yozilmadi**: manba tekshirilmagan.
Uning o'rnida `[TASDIQLASH KUTILMOQDA]` belgisi va nima kutilayotganini
aytadigan matn turadi.

Nega bu shunchalik muhim: bu — loyihaning 1.4-bandidagi halollik
tekshiruvi tamoyilining o'ziga tegishli. Tekshirilmagan diniy da'voni
"vaqtincha" qo'yib, keyin unutish — halol savdo haqidagi loyihada eng
yomon xato bo'lardi. Belgi ko'zga tashlanadigan qilib qo'yilgan
(`Badge tone="ortacha"`), ya'ni uni tasodifan e'tibordan qoldirib
bo'lmaydi. Matnni muftiy/olim tasdiqlagach almashtiriladi.

### 51.2. Ijtimoiy tarmoqlar — kod emas, baza

Havolalar `social_links` jadvalida, admin panelidan boshqariladi.
Sabab oddiy: yangi tarmoq qo'shish uchun deploy kutish kerak
bo'lmasin. Ikonka turi ham tanlovdan — ya'ni ro'yxat kengaysa, sayt
kodi o'zgarmaydi.

### 51.3. "Nega signal yo'q?" alohida bo'lib qololmasdi

Bozor Salomatligi shkalasi bosh sahifadan `/salomatlik` ga ko'chdi va
voronka ("Nega bugun signal kam?") **shu sahifaga qo'shildi**, alohida
menyu bandi olib tashlandi.

Bu — dizayn emas, mazmun masalasi. Ikkalasi bitta savolga javob
beradi: "bugun nega jim?". Ular ikki bandda turganda foydalanuvchi
shkalani ko'rib "bozor 66/100, yaxshi-ku" deb ketardi va voronkadagi
haqiqiy sababni (masalan ball chegarasidan hech kim o'tmagani) umuman
ko'rmasdi. 37-bo'limdagi sokinlik dashboardining o'zi ham aynan shu
uchun qurilgan edi.

Eski `/sokinlik` manzili o'chirilmadi — `/salomatlik` ga yo'naltiradi.
Foydalanuvchida saqlangan havola sinmasin.

### 51.4. Kalkulyator — sof funksiya, keyin ekran

Hisob-kitob `web/src/lib/kalkulyator.ts` da: React'siz, DOM'siz sof
funksiya, test bilan qoplangan (11 ta). Komponent faqat maydonlarni
ko'rsatadi va natijani chizadi.

Nega bunday bo'lindi: bu yerda foydalanuvchi O'Z PULINI hisoblaydi.
Hisobdagi xato — ekrandagi xato emas, u odamning qaroriga ta'sir
qiladi. Testlar orasida topshiriqdagi aniq misol ham bor ($1000,
kirish 100, stop 97, TP 103/106/109 — 50/30/20%), ya'ni raqamlar
kutilgani bilan solishtiriladi, "ishlayotganga o'xshaydi" bilan emas.

TP soni **qattiq yozilmagan**: komponent massiv qabul qiladi. Signalda
uchinchi TP paydo bo'lsa, kalkulyatorda hech narsa o'zgarmaydi.
Ulushlar yig'indisi 100% bo'lmasa ogohlantirish chiqadi, lekin hisob
to'xtatilmaydi — foydalanuvchi qismini sotmoqchi bo'lishi ham mumkin.

### 51.5. Grafik himoyadan TASHQARIDA, kalkulyator ICHIDA

| Element | Joyi | Sabab |
|---|---|---|
| TradingView grafigi | `Himoya` dan tashqarida | ochiq bozor ma'lumoti, bizniki emas |
| Kalkulyator | `Himoya` ichida | maydonlarida kirish, Stop va TP narxlari turadi — ya'ni signalning O'ZI |

Agar kalkulyator tashqarida qolsa, suv belgisi va xiralashtirish
qatlamlari aylanib o'tilardi: narxlar himoyalangan kartochkada
yashirin, lekin kalkulyator maydonida ochiq turardi.

### 51.6. Uchinchi tomon skripti tushib qolishi HISOBGA olingan

TradingView widget'i tashqi domendan skript tortadi. Reklama
bloklovchi (uBlock va shunga o'xshash) uni bemalol to'sadi. Zaxirasiz
foydalanuvchi 420px bo'sh quti ko'rardi va saytni buzilgan deb
o'ylardi.

Shuning uchun ikkita tekshiruv bor: skriptning `onerror` hodisasi VA
6 soniyadan keyin natijaning o'zi (`iframe` paydo bo'lganmi). Ikkinchisi
kerak, chunki bloklovchi so'rovni jimgina bekor qilsa `onerror`
kelmaydi. Ikkalasidan biri ishlasa — tushuntirish matni chiqadi va
signal narxlari grafikka bog'liq emasligi aytiladi.

## 52. Video darsliklar saytda: Telegramning 20 MB devori

Video Telegramda `file_id` sifatida yotardi va saytda ko'rsatib
bo'lmasdi. Sabab texnik va qat'iy: Bot API `getFile` orqali bot
**faqat 20 MB gacha** faylni yuklab olishi mumkin. Video darslik esa
odatda bundan katta — ya'ni "Telegramdan olib ko'rsatamiz" yo'li
darslarning ko'pchiligi uchun UMUMAN ishlamasdi.

Uch yo'ldan biri tanlanishi kerak edi va bu — texnik emas, egalik
qarori: Telegramdan oqim (tekin, lekin 20 MB), YouTube/Vimeo (tekin va
cheklovsiz, lekin havola tarqalsa obunasiz odam ham ko'radi), yoki
faylni o'zimizning diskimizda saqlash (disk pullik, lekin kirish
nazorati bizda qoladi). Tanlangan yo'l — uchinchisi.

### 52.1. Jild qoidasi ikki tilda yozilgan — va shu narsa xavf

Fayllar baza fayli YONIDAGI `video/` jildida turadi. Bu qoida ikki
joyda amalga oshirilgan: `web/src/lib/media.ts` (`videoJildi()`) va
`bot/hosting.py` (`video_dir()`). Ikkalasi bir xil jildni ko'rsatishi
SHART — ayrilib ketsa, sayt yozgan faylni bot topa olmaydi va dars
botda jimgina ko'rinmay qoladi.

Shuning uchun ikkala tomonda ham aynan bir xil qiymatni tekshiradigan
test bor (`web/tests/media.test.ts` va `tests/bot/test_video_dir.py`):
`sqlite+aiosqlite:////data/hcs.db` -> `/data/video`.

Alohida muhit o'zgaruvchisi ATAYLAB qo'yilmadi: u ikki xizmatda
boshqa-boshqa qo'yilishi mumkin edi va xato faqat "video ochilmayapti"
bo'lib ko'rinardi. Bazadan hisoblansa, doimiy disk ko'chganda ikkalasi
birga ko'chadi.

### 52.2. Fayl xotiraga YIG'ILMAYDI

Yuklashda `multipart/form-data` ishlatilmadi: uni ajratish uchun butun
fayl xotiraga tushardi — yuz megabaytlik dars uchun yuz megabayt
operativ xotira, bepul serverda esa bu jarayonning o'limi.

O'rniga so'rov tanasining O'ZI fayl (`?nom=` da faqat kengaytma uchun
asl nom). Tana to'g'ridan-to'g'ri diskka oqiziladi, xotirada bir vaqtda
faqat kichik bo'lak turadi.

Hajm ikki joyda tekshiriladi: `content-length` sarlavhasi VA haqiqatda
oqib kelgan baytlar. Birinchisi yolg'on bo'lishi mumkin, ikkinchisi —
bo'lmaydi. Chegaradan oshsa yarim yozilgan fayl O'CHIRILADI: u diskda
joy egallaydi va hech qachon o'ynatilmaydi.

### 52.3. `Range` — bu bezak emas

Berish marshrutida `Accept-Ranges` va 206 javobi bor. Usiz brauzer
videoni faqat boshidan ketma-ket yuklaydi va O'RTAGA SAKRASH ishlamaydi
— uzun darsda bu darrov seziladi.

Range tahlilidagi eng adashtiradigan joy alohida testga olingan:
`bytes=-500` — bu "0 dan 500 gacha" EMAS, bu OXIRGI 500 bayt.

### 52.4. Fayl statik emas — har so'rov tekshiriladi

Video oddiy statik fayl bo'lsa, manzilini bilgan har kim ko'rardi va
obuna tekshiruvi chetlab o'tilardi. Shuning uchun har bir so'rov
`/api/video/[id]` dan o'tadi: sessiya, tarif va darsning chop etilgani
tekshiriladi.

Yo'l xavfsizligi ikki qavat: avval fayl nomining o'zi (`/`, `\`, `..`
rad etiladi), keyin natija jild ichida ekani ALOHIDA tasdiqlanadi.
Birinchisi o'tkazib yuborsa, ikkinchisi tutadi.

### 52.5. Bot ham shu darsni ko'rishi kerak — yana bir "pickup"

Saytga yuklangan dars botda ko'rinmay qolsa, bitta ro'yxat ikki joyda
ikki xil bo'lardi — foydalanuvchi uchun eng chalkash holat, va aynan
shu 49-bo'limdagi signal muammosining takrori.

Yechim ham o'sha naqsh bo'yicha: `web-videos` fon vazifasi (5 daqiqada
bir) `video_path` bor-u `file_id` yo'q darslarni topadi, faylni
adminning chatiga yuboradi va javobdagi `file_id` ni saqlaydi. Shundan
keyin bot uni avvalgidek `file_id` orqali tarqatadi.

Fayl adminning chatiga yuboriladi, chunki `file_id` faqat fayl BIR
MARTA Telegramga yuborilganda paydo bo'ladi — bu Telegram cheklovi,
bizning tanlovimiz emas.

### 52.6. Videoda xiralashtirish YO'Q — ataylab

Signal narxlarida fokus yo'qolganda ekran xiralashadi (50-bo'lim).
Videoda bu qatlam ATAYLAB yoqilmadi: darsni tinglab turib boshqa
oynaga o'tish odatiy hol, har safar ekranni yopish himoya emas,
xalaqit. Suv belgisi (foydalanuvchi IDsi) esa qoladi — u yozib olingan
nusxa kimdan chiqqanini ko'rsatadi.

### 52.7. WAL: test bazani eskisicha ko'rgan edi

Yangi ustun qo'shilgach testlar "no such column: video_path" berdi —
holbuki migratsiya muvaffaqiyatli o'tgan va ustun bazada bor edi.

Sabab: baza WAL rejimida. Yangi yozuvlar avval `hcs.db-wal` fayliga
tushadi, asosiy faylga esa keyinroq ko'chadi. Test esa faqat `hcs.db`
ni nusxalar edi — ya'ni migratsiyani KO'RMASDI.

Bu jimgina adashtiradi: baza to'g'ri, kod to'g'ri, xato esa kodda
izlanadi. Endi nusxalash bitta joyda (`web/tests/nusxa.ts`) va u
`-wal` bilan `-shm` ni ham oladi.

## 53. "Sayt eski kodni ko'rsatyapti" — ikkita mustaqil sabab

Yangi kod GitHub'da bor edi, saytda esa yo'q. Bu ikki soatdan ko'proq
vaqt oldi va sabab BITTA emas, IKKITA edi — ular bir-birini yashirib
turdi. Har biri alohida ham topilishi qiyin, birga esa deyarli
imkonsiz.

### 53.1. Ikkita Railway loyihasi

Bitta GitHub reposiga IKKITA loyiha ulangan edi:

| Loyiha | Domen | Doimiy disk |
|---|---|---|
| `amiable-light` | yo'q ("Unexposed service") | yo'q |
| `selfless-benevolence` | `hcsacademya-production...` | bor |

Deploy loglari birinchisida kuzatilardi, sayt esa ikkinchisidan
kelardi. Ikkalasi ham "HCS_ACADEMYA" deb atalgan, ikkalasi ham
"Deployment successful" deb turardi.

Yon ta'siri bundan ham yomonroq edi: `scripts/start.sh` ikkala
loyihada ham botni ishga tushiradi, Telegram esa bitta botga bitta
`getUpdates` ulanishiga ruxsat beradi. Natijada bot 3,5 soat davomida
o'zi bilan urishdi (`TelegramConflictError`, 2498 urinish) va HECH
QANDAY xabarni qabul qilmadi. Logda faqat konflikt ko'rinardi,
"nega signal tarqatilmayapti" degan savolga esa javob yo'q edi.

**Belgi:** xizmat sozlamalarida "Public Networking" bo'sh, lekin sayt
baribir ochiladi. Demak uni BOSHQA xizmat berayapti.

### 53.2. `[variables]` dagi NODE_OPTIONS bosib o'tilgan

Ikkinchi sabab birinchisi ostida yashirin turdi: qurish YIQILARDI.

  Failed to collect configuration for /api/auth/telegram
  [cause]: ERR_UNKNOWN_BUILTIN_MODULE: No such built-in module: node:sqlite
    at module evaluation (src/lib/db.ts:2:1)
  node v22.10.0

`node:sqlite` 22.10 da bayroq ostida (bayroqsiz faqat 22.13 dan) va
bayroq `nixpacks.toml` ning `[variables]` bo'limida allaqachon
qo'yilgan edi. Lekin unga TAYANIB BO'LMAYDI: Railway xizmatining o'z
o'zgaruvchilari uni bosib o'tishi mumkin. Aynan shu sodir bo'ldi —
bitta loyihada qurish o'tdi, ikkinchisida o'sha commit shu xato bilan
yiqildi. Ikki loyiha bo'lmaganda bu farq umuman ko'rinmasdi.

Endi qiymat `npm run build` buyrug'ining O'ZIDA. Buni hech qanday
muhit o'zgaruvchisi bosib o'tolmaydi.

Qo'shimcha: qurishdan oldin bitta qator `node:sqlite` ochilishini
tekshiradi. Usiz xato `next build` ning o'rtasida, "Collecting page
data" bosqichida chiqadi va 40 qator ichida ko'milib ketadi.

### 53.3. Xulosa: "deploy o'tdi" — javob emas

Ikkala sababda ham platformaning xabari ("Deployment successful")
to'g'ri edi, lekin SAVOLGA javob bermasdi. Kerakli savol boshqa:
"ochiq domenda HOZIR qaysi commit ishlayapti?".

Shuning uchun `/api/health` ga ikkita tashxis qo'shildi:

  `?tekshir=versiya` — repo, shox, commit, deploy raqami VA menyu
  bandlari ro'yxati. Oxirgisi kodning O'ZIDAN olinadi: platforma
  o'zgaruvchilari yo'q bo'lsa yoki boshqa narsani ko'rsatsa ham,
  `salomatlik` bandi bo'lsa — yangi kod, `sokinlik` bo'lsa — eskisi.

  `?tekshir=baza` — bazaning YO'LI. `/data` bilan boshlanmasa, bu
  xizmat doimiy diskka ulanmagan va uning bazasi har yangilanishda
  o'chadi. Ikki loyihali holatda aynan shu ikkalasini ajratib berdi.

Qoida: joylashtirish haqidagi har qanday da'vo ISHLAYOTGAN TIZIMNING
O'ZIDAN tasdiqlanishi kerak. Bu — 48-bo'limdagi "ulanmagan filtr"
xatosining boshqa qiyofasi: hamma narsa to'g'ri ko'rinadi, chunki
hech kim natijaning o'zini so'ramagan.

## 54. TradingView skrinshoti: TEKSHIRILDI, IMKONSIZ — va rasm olib tashlandi

Talab: signal bilan birga TradingView'dan "uzun pozitsiya" asbobi
qo'yilgan grafik skrinshoti ketsin.

### 54.1. Tekshiruv natijasi — bepul yo'l YO'Q

Bu xulosa SAQLANADI, chunki savol yana ko'tarilishi mumkin:

  - TradingView'da grafik rasmini beradigan OCHIQ API yo'q. "Snapshot"
    tugmasi — sayt interfeysining bir qismi, xizmat emas.
  - Brauzer bilan avtomatlashtirish TradingView shartlariga zid,
    konteynerga ~400 MB Chromium qo'shadi va interfeys o'zgargan kuni
    sinadi.
  - ENG MUHIMI: bepul embed widget'da CHIZISH API si umuman yo'q.
    "Long Position" asbobini dastur orqali qo'yib bo'lmaydi — u faqat
    litsenziyalangan Charting Library da. Ya'ni brauzer yo'li
    ishlaganda ham kerakli rasmni BERMASDI.
  - `chart-img` kabi uchinchi tomon xizmatlari buni qiladi, lekin
    pullik (oyiga ~$15 dan) va ular yiqilsa rasm ham yo'qoladi.

### 54.2. O'zimiz chizgan variant QURILDI va KEYIN OLIB TASHLANDI

Alternativa sifatida grafik o'zimizning ma'lumotimizdan chizildi:
Binance shamlari + signal darajalari, Pillow bilan (~3 MB, matplotlib
emas — u numpy'ni tortadi va `requirements.txt` dagi qoidani buzardi).
Ishladi: kirish chizig'i, Stop'gacha qizil zona, TP2 gacha yashil zona,
yorliqlar ustma-ust tushmasligi uchun alohida joylashtirish hisobi.

Egasi ko'rib chiqib, rasm KERAK EMAS degan qarorga keldi — signal
kartochkasining o'zi yetarli. Shuning uchun `bot/chart.py`, Pillow
bog'liqligi va tarqatishdagi rasm yo'li butunlay olib tashlandi.

Nima uchun bu yerda yozib qo'yilgan: tekshiruvning O'ZI qimmatli
natija. Rasm yana kerak bo'lsa, TradingView tomonini qaytadan
tekshirish shart emas — javob 54.1 da. Qurilgan variantni esa
`3c1c050` commitidan tiklash mumkin.

### 54.3. Yo'l-yo'lakay topilgan xavf

Grafik moduli `bot/services/broadcast.py` da modul boshida import
qilingan edi. Serverda `pip install` yiqilsa, import xatosi butun
zanjirni (broadcast -> runner -> bot) o'ldirardi — ya'ni QO'SHIMCHA
QULAYLIK butun botni ishga tushirmay qo'yardi.

Bu naqsh boshqa joyda ham takrorlanishi mumkin: ixtiyoriy imkoniyat
majburiy import bilan ulansa, u ixtiyoriy bo'lmay qoladi.

## 55. Balans -> taklif -> "men sotib oldim": bitta zanjir

Uch joyda uch xil raqam bor edi va ular bir-biriga ulanmagan:
kalkulyator har doim "1000" dan boshlanardi, signal kartochkasidagi
"Miqdor" balansdan hisoblanardi, "Men sotib oldim" esa bo'sh turardi.
Foydalanuvchi qaysi raqamga ishonishni bilmasdi.

### 55.1. Tartib — mantiqiy, dizayn emas

    balans -> tizim taklifi -> kalkulyator -> "men sotib oldim"

Balans BIRINCHI, chunki usiz tizim hech narsa taklif qila olmaydi.
Avval kartochka "balansingizni kiriting" derdi-yu, QAYERDAN kiritishni
ko'rsatmasdi — botda ham, saytda ham. Endi balanssiz foydalanuvchiga
signal sahifasining tepasida so'rov chiqadi, botda esa kartochkaning
eng tepasida balans tugmasi turadi.

### 55.2. Biz TAKLIF qilamiz, foydalanuvchi HAQIQATNI aytadi

Taklif — kunlik xavf byudjeti va Stop masofasidan hisoblangan raqam.
U kalkulyatorning boshlang'ich summasiga ham, "Men sotib oldim"
maydoniga ham tushadi, ya'ni bir sahifada ikki xil son yo'q.

Lekin maydon QULFLANMAYDI: foydalanuvchi haqiqatda boshqacha olishi
mumkin va portfeldagi foyda/zarar aynan HAQIQIY miqdordan hisoblanishi
kerak. Taklifni majburiy qilsak, statistika xayoliy bo'lardi.

KIRISH NARXI esa aksincha — ko'rsatiladi, lekin tahrirlanmaydi. U
signal yozuvidan olinadi. Tahrirlansa, foydalanuvchi o'ziga qulay narx
yozib, statistikada mavjud bo'lmagan foyda ko'rsatardi.

### 55.3. Pul hisobi IKKI TILDA — ochiq boshqariladi

Taklif asli Pythonda (`core/position_sizing/`), sayt esa TypeScriptda
(`web/src/lib/hajm.ts`). Ikki nusxa — xavf, shuning uchun:

  1. barcha parametrlar bitta YAML dan o'qiladi;
  2. `tests/hajm_fixtures.json` — Python chiqargan ETALON. Python
     testi ham, sayt testi ham SHU faylga solishtiradi.

Biror tomon o'zgarsa testlardan biri darhol yiqiladi. Faqat
KO'RSATISH yo'li ko'chirilgan: kunlik byudjetdan xavf AJRATISH
Pythonda qoladi.

### 55.4. i18n kalitlari endi test bilan qoplangan

`tarjima()` kalit topilmasa xato bermaydi — kalitning O'ZINI
qaytaradi. Bu ataylab (bitta yetishmagan matn sahifani yiqitmasin),
lekin narxi bor: ekranda `portfel.balans_kerak` degan xom matn chiqadi
va buni faqat tasodifan ko'rib qolamiz.

UCH MARTA sodir bo'ldi: `admin.izoh` mavjud tarjimani bosib ketgan;
`balans_kerak` noto'g'ri bo'limga tushgan; `umumiy.saqlash` umuman
yo'q edi. Endi kodda ishlatilgan har bir qattiq yozilgan kalit ikkala
tilda ham tekshiriladi — test yozilgan zahoti uchinchisini topdi.

## 56. Jonli narx: signal kirishdan qancha yurgan

Ro'yxatda signal "Faol" deb turardi-yu, u foydaga ketayotganini yoki
Stop tomon yurayotganini KO'RSATMASDI. Yangi foydalanuvchi uchun esa
birinchi savol aynan shu. Endi har bir kartochkada bo'sh joyda foiz
turadi: yuqorida bo'lsa yashil `+`, pastda bo'lsa qizil `−`.

**Narxni SERVER oladi, brauzer emas.** Ikki sabab: foydalanuvchining
tarmog'i Binance'ni to'sishi mumkin (TradingView bilan aynan shunday
bo'ldi), va uchta kartochka uchta to'g'ridan-to'g'ri so'rov yuborsa
birja chegarasiga tez yetamiz. Server `/api/v3/ticker/price?symbols=[…]`
ga BITTA so'rov yuboradi va javobni 15 soniya keshda saqlaydi;
brauzer esa 20 soniyada bir marta `/api/narx` ga murojaat qiladi.

`/api/narx` SESSIYA BILAN yopiq va juftliklar `^[A-Z0-9]{4,24}$` ga
tekshiriladi (ko'pi bilan 30 ta). Narxning o'zi maxfiy emas, lekin
manzilimiz birov uchun bepul narx manbai bo'lib qolmasin.

**Narx noma'lum bo'lsa HECH NARSA ko'rsatilmaydi.** `0.00%` yozish
yolg'on bo'lardi — u "narx o'zgarmadi" degan ma'noni beradi, aslida
esa narx umuman kelmagan. Tarmoq uzilsa oxirgi ma'lum foiz qoladi.

### Modul chegarasi: `jonli.ts` va `jonli-server.ts`

Avval hammasi bitta faylda edi va qurish yiqildi:

    the chunking context does not support external modules
    (request: node:fs)

Sabab: brauzerdagi komponent `ozgarishFoizi()` ni import qilardi, u
turgan fayl esa `config.ts` ni tortardi, u esa YAML uchun `node:fs`
ni. Fayl ikkiga bo'lindi:

  - `lib/jonli.ts` — sof hisob, klientga ham tushadi;
  - `lib/jonli-server.ts` — Binance so'rovi, FAQAT serverda.

Bu 1-naqshning qarindoshi: "bitta fayl ikki xil muhitga xizmat
qilyapti" ham xuddi "bitta son ikki xil ma'noda" kabi jimgina buzadi.

### Yon ta'sir: yorliqlar to'qnashuvi topildi

Tekshiruv paytida ma'lum bo'ldiki, BITTA signal ikki joyda ikki xil
ko'rinardi — ro'yxatda "Kirish narxi", o'z sahifasida "Kirish".
Sabab: `kalkulyatorMatnlari` ichidagi `kirish` kaliti
`kartochkaMatnlari` dagi shu nomli kalitni bosib ketardi. Kalkulyator
kalitlari `kalk_` prefiksiga o'tkazildi, `tests/i18n.test.ts` ga esa
"kartochka matnlari bosib ketilmaydi" testi qo'shildi.

## 57. CryptoSpot3% (ISC 1.0) metodikasi qo'shildi

Admin o'zining mualliflik kursidan besh qismli metodikani strategiyaga
kiritishni so'radi: **MSNR -> SMC -> LIT -> ICT -> QT+SMT**.

### Qaerga joylashdi

| Qism | Modul | Qanday ta'sir qiladi |
|---|---|---|
| SMC (HH/HL, BOS/CHOCH) | `core/analysis/market_structure.py` | TREND omilini ko'taradi + Salomatlik indeksining ASOSIY omili |
| MSNR (RBS/SBR/OCL/Qm/OB) | `core/analysis/level_types.py` | S/R omilini ko'taradi |
| LIT (Liquidity Sweep) | `support_resistance/liquidity.py` | S/R omilini ko'taradi |
| ICT (Kill Zone) | `scoring/bonuses.py` | ball bonusi (+5) |
| QT (AMDX) | `market_health/quarterly.py` | Salomatlik omili (kichik vazn) + saytda kontekst |
| SMT (divergensiya) | — | V2 ga qoldirildi (metodika hujjatining o'z tavsiyasi) |

### Eng muhim qaror: DALIL OMIL ICHIDA, YONIDA EMAS

Birinchi yozuvda metodika omillari BONUS edi — mavjud omillar yonida
turardi va bazaviy 100 ball ustiga qo'shilardi. Admin buni to'g'ri
tanqid qildi:

> "Eski modul 10 kunda 3 ta signal berdi. Demak yangi modul o'sha
> uchtasini qayta tartiblab chiqadi, xolos — u aslida signal
> tanlashda ham ishlatilishi kerak."

Tanqid o'rinli edi. Bonus chegaraga kirmagani uchun yangi modul signal
SONIGA umuman ta'sir qila olmasdi. Undan ham chuqurroq muammo bor edi:
**bitta narsa ikki joyda o'lchanardi.** "Yalab o'tib qaytilgan
Quasimodo zonasi" — bu boshqa bir omil emas, bu shunchaki SIFATLIROQ
S/R zonasi. HH/HL ketma-ketligi ham alohida narsa emas — bu trendning
o'zi, faqat EMA dan oldinroq ko'rinadigan ko'rinishi.

Shuning uchun dalillar MAVJUD OMILLAR ICHIGA ko'chirildi:

| Dalil | Qaysi omilga | Nima uchun aynan u |
|---|---|---|
| MSNR daraja turi + LIT sweep | S/R zonasi (25) | ikkalasi ham AYNAN SHU ZONA haqidagi ma'lumot |
| SMC strukturasi (HH/HL, BOS) | Trend (20) | struktura — trendning kechikmaydigan ko'rinishi |
| ICT Kill Zone | bonus (5) | kirish VAQTI haqida, tuzilma haqida emas |

Qo'shish shakli:

    yangi = eski + (1 - eski) * dalil * ulush

Ikki xossa kafolatlanadi: dalil bo'lmasa qiymat o'zgarmaydi, dalil
to'liq bo'lsa ham omil o'z vaznidan oshmaydi. Ya'ni yangi bilim
ballni faqat KO'TARADI — hech kimni yo'ldan qaytarmaydi.

Natijada ikki modul ORALASHIB ishlaydi: dalil chegara o'qiydigan
BAZAVIY ball ichida, ya'ni u ham QAYSI signal chiqishiga, ham QANCHA
signal chiqishiga ta'sir qiladi. Parallel ikkinchi darvoza
QILINMADI — u ikkita alohida qoidalar to'plami, ikki barobar sozlash
va "qaysi biri ishladi" degan doimiy savol degani bo'lardi.

### Mustaqil dalillar QO'SHILADI, o'rtachalanmaydi

Daraja turi va sweep bir vaqtda topilganda ular `noisy-OR` bilan
birlashtiriladi:  `1 - (1-a)(1-b)`.

Sabab: ikkalasi ham AYNAN BIR narsani tasdiqlaydi ("bu zona
ishonchli"), lekin MUSTAQIL manbalardan — biri tarixiy tuzilmadan,
ikkinchisi hozirgi narx harakatidan. O'rtacha olinganda ikkinchi
tasdiq birinchisini SUSAYTIRARDI (agar sal zaifroq bo'lsa) va
metodikaning asosiy da'vosi — naqshlar BIRGA kuchli — modelda aks
etmasdi.

### O'lchov: dalil signal soniga ta'sir qiladimi

`python -m scripts.cryptospot3_olchov` (tarmoq talab qilmaydi):

```
Nomzodlar soni:        15 -> 15
Bazaviy ball:  dalilsiz 19.5..63.8 (o'rt. 50.4)
               dalilli  32.5..67.2 (o'rt. 56.3)

Chegara bo'ylab o'tganlar soni:
   chegara  dalilsiz   dalilli
        45        12        13
        50         9        12
        52         8        11
        55         8         8   <-- joriy
        58         7         8
        60         4         8
        62         1         7
        65         0         3
```

**Sinalgan 8 chegaradan 7 tasida dalil signal sonini OSHIRDI.**
Joriy chegarada (55) son o'zgarmadi — bu TASODIF: 15 ta sun'iy
nomzoddan hech biri aynan shu chiziqni kesib o'tmadi. 60 da esa
4 -> 8, ya'ni ikki barobar. Mexanizm ishlaydi, bitta chegaradagi
natija esa namunaga bog'liq.

Chegarani shu jadvalga qarab o'zgartirmang: 15 ta sun'iy nomzod —
mexanizmni tekshirish uchun, chegarani tanlash uchun emas.

### Yo'l-yo'lakay: MSNR tasnifi hech narsani ajratmasdi

O'lchov qilinganda kalibrlash to'plamidagi **27 zonaning HAMMASI**
"RBS" deb tasniflangani ma'lum bo'ldi. Sabab: `_is_flipped()` faqat
"narx qachondir bu zonani kesib o'tganmi" degan savolni tekshirardi —
ko'tarilayotgan narx esa har qanday support zonasini kesib o'tgan
bo'ladi.

Ya'ni "dalil" aslida hammaga bir xil qo'shiladigan doimiy songa
aylanib qolgan edi — bu chegarani jimgina pasaytirish bilan barobar.

Tuzatildi: RBS uchun endi zona ROSTDAN qarshilik bo'lganini
ko'rsatuvchi burilish nuqtasi (zona ichidagi pivot high) talab
qilinadi. Taqsimot 27/27 RBS dan 15 RBS + 12 oddiy ga o'zgardi —
tasnif haqiqiy ajratish kuchiga ega bo'ldi.

### BTC Dominance asosiy omil bo'lishdan chiqarildi

Tajribali treyderlar bilan maslahat: dominance foydali, lekin
ko'pchilik uchun qaror mezoni emas. Vaznlar qayta taqsimlandi:

| Omil | Eski | Yangi |
|---|---|---|
| Halol ro'yxat STRUKTURA kengligi (SMC) | — | **30** |
| Halol ro'yxat trend kengligi (EMA) | 25 | 15 |
| Volatillik rejimi | 20 | 15 |
| Agregat foydalanuvchi sig'imi | 20 | 20 |
| Signal to'yinganligi | 15 | 10 |
| BTC Dominance | **20** | **5** |
| QT davri (AMDX) | — | 5 |

Kunlik oldindan tahlil ham dominance'dan strukturaga o'tdi: endi u
"nechta coin HH/HL qadam tashlayapti" degan savolga tayanadi.

### QT haqida ochiq ogohlantirish

QT davri SOAT bo'yicha aniqlanadi, ya'ni u bozor holatidan qat'i nazar
har kuni bir xil ritmda o'zgaradi. Bu — o'lchanmagan taxmin. Shuning
uchun vazni ataylab kichik (5) va davr -> ball moslashuvi
(`QuarterPhase.score`) BOSHLANG'ICH qiymat.

Yon ta'siri qayd etildi va test bilan qulflandi: QT omili indeks
shiftini soatga bog'liq qiladi (95..100). "Erishib bo'lmas shift" bu
loyihada uch marta muammo bo'lgan (32, 46, 47-bo'limlar), shuning
uchun `test_qt_omili_shiftni_soatga_bogliq_qiladi` shiftning 95 dan
pastga tushmasligini tekshiradi.

### Struktura darvozasi — bor, lekin O'CHIRIQ

`analysis.require_structure_alignment: false`. Yoqilsa, pasayish
strukturasidagi (LH/LL) coin butunlay rad etiladi va voronkada
`classic_ta:structure` qatori paydo bo'ladi. Bu `require_htf_alignment`
va `require_confirmation` bilan bir xil naqsh: imkoniyat bor, lekin
standart holatda yopiq — backtest tasdiqlamaguncha yoqilmaydi.

### Yo'l-yo'lakay topilgan ikkita eski xato

**1. `breakdown_to_text()` hech qayerda chaqirilmagan edi** (2-naqsh:
"e'lon qilingan, lekin ulanmagan"). Bot "Nega bu signal?" tugmasida
bazadagi XOM JSON ni ko'rsatib turardi — foydalanuvchi ekranida
`{"symbol": "DOT", "components": [...]}` chiqardi. `breakdown_from_json()`
qo'shildi va handler ulandi.

**2. Salomatlik omillari shkalasi mos kelmasdi** (1-naqsh). Bot
`HealthFactor.score` ni 0..1 oralig'ida yozadi, sayt esa uni
to'g'ridan-to'g'ri foiz deb chizardi: haqiqiy ma'lumotda har bir omil
"0" yoki "1" ko'rinardi. Xato bir necha oy sezilmadi, chunki demo
ma'lumot 0-100 shkalada yozilgan edi va ekranni to'g'ri ko'rsatardi.
Sahifa ham, demo skript ham tuzatildi, `web/tests/i18n.test.ts` ikkala
tomonni qulfladi.

### Admin panel

Bot `/panel` da ham, veb admin panelida ham "SMC / LIT sozlamalari"
bo'limi bor — FAQAT KO'RSATISH. Bu loyihada strategiya parametrlari
`config/default.yaml` da yashaydi; ishga tushgan tizimda ularni
saqlaydigan mexanizm yo'q. Tahrirlash tugmasini qo'yib, aslida hech
narsa yozmaslik eng yomon variant bo'lardi: admin o'zgartirdim deb
o'ylaydi, tizim esa eski qiymat bilan ishlashda davom etadi.

## 58. EMA olib tashlandi va takroriy tahlil tozalandi

Admin ikkita ish so'radi: **EMA indikatorini olib tashlash** va **eski
hamda yangi modulni tahlil qilib, bir ishni ikki marta qiladigan yoki
umumiy tahlilga ta'sir qilmaydigan qismlarni chiqarib tashlash**.

### Nima uchun EMA ni olib tashlash MUMKIN bo'ldi

EMA ning ikkita ishi bor edi:

  1. trend YO'NALISHINI aniqlash (EMA50 > EMA200);
  2. uni tasdiqlash (`confirm()` dagi "trend" omili).

Ikkalasini ham endi SMC strukturasi bajaradi — u narxning O'Z
qadamlarini (HH/HL/LH/LL) o'qiydi. Ya'ni EMA olib tashlangach
bo'shliq qolmadi; aksincha, ikkita takror o'lchov bittaga tushdi.

EMA ning zarari o'lchangan edi:

  * **kechikish** — EMA200 200 shamlik o'rtacha. U tasdiqlaguncha narx
    Discount zonasidan chiqib ketardi, ya'ni "arzon paytda ol"
    strategiyasining o'z maqsadiga zid ishlardi (27- va 28-bo'limlar);
  * **tarix talabi** — haftalik timeframeda 200 sham ~3.8 yil degani.
    Ko'p altcoinlarda bunday tarix yo'q va ular jimgina "ko'tarilishda
    emas" deb sanalardi; bozor kengligi sun'iy tushib, indeks signalni
    butunlay to'xtatardi (33-bo'lim).

Tahlil uchun minimal sham chegarasi 200 dan **60** ga tushdi
(`indicators.min_candles`) — u faqat EMA200 uchun kerak edi.

### EMA o'rniga nima keldi

Trend omili (20 ball) ichidagi ulushlar:

| Qism | Eski | Yangi |
|---|---|---|
| EMA ajralishi | 0.30 | **yo'q** |
| SMC strukturasi | — | **0.35** |
| ADX (trend KUCHI) | 0.30 | 0.25 |
| Yuqori timeframe | 0.40 | 0.40 |

ADX qoldi, chunki u boshqa savolga javob beradi: struktura
YO'NALISHNI aytadi, ADX esa KUCHNI. Ular takror emas.

Yuqori timeframe tasnifi ham EMA dan strukturaga o'tdi
(`_timeframe_view`), ya'ni `htf_trend_requires_price_above_fast`
bayrog'i bilan birga 27-bo'limdagi muammoning o'zi ham yo'qoldi.

### EMA olib tashlangach chiqqan BO'SHLIQ va uning yopilishi

Sinov paytida ma'lum bo'ldi: **silliq, to'xtovsiz ko'tarilishda
burilish nuqtalari umuman bo'lmaydi**, ya'ni HH/HL ketma-ketligi ham
yo'q va struktura "aniq emas" deydi — holbuki bu eng kuchli trendning
o'zi. EMA bu holatni ushlab turardi.

Bo'shliq zaxira o'lchov bilan yopildi: swing yetarli bo'lmaganda
oynadagi SOF NARX O'ZGARISHI qaraladi
(`market_structure.fallback_min_pct`, standart 1%). Bu EMA emas —
o'rtacha ham, uzoq tarix ham talab qilinmaydi, faqat "narx oynaning
boshidan balandmi" degan to'g'ridan-to'g'ri savol.

### Takroriy va o'lik qismlar olib tashlandi

| Nima | Nima uchun |
|---|---|
| `ema`, `ema_series`, `trend_direction`, `timeframe_trend` | struktura bilan takror |
| `confirm()` dagi "trend" omili | o'sha EMA, ikkinchi joyda |
| `halal_trend_breadth` (Salomatlik omili, 15) | `halal_structure_breadth` bilan AYNAN bir savol; vazni unga qo'shildi (30 -> **45**) |
| `market_structure.uptrend_ratio()` | `HealthInputs.structure_uptrend_ratio` bilan takror |
| `is_trending()` | e'lon qilingan, hech qayerda chaqirilmagan |
| `volume_confirms()` | o'sha holat |
| `MarketStructure.last_high/last_low` | ishlatilmagan aksessorlar |
| `SignalLevels.risk_reward_tp1` | ishlatilmagan |
| `ScoreUplift.trend` | struktura endi "ko'tarish" emas, omilning to'liq qismi |

`ema_series` MACD ichiga ko'chdi va yopiq qilindi (`_ema_series`): u
MACD ta'rifining bir qismi (ikki eksponensial o'rtachaning ayirmasi),
olib tashlangan EMA TREND FILTRI emas.

### O'lchov

`python -m scripts.cryptospot3_olchov`, EMA olib tashlangandan keyin:

```
Chegaradan o'tganlar:  2 -> 3     (dalilsiz -> dalil bilan)
Bazaviy ball:  dalilsiz 32.4..66.7 (o'rt. 49.0)
               dalilli  38.4..68.2 (o'rt. 51.3)

Chegaradan o'tgan uchala nomzodda ham CryptoSpot3% shartnomasi TO'LIQ.
```

Ikki narsa muhim:

1. **Joriy chegarada signal soni o'zgardi (2 -> 3)** — ya'ni yangi
   modul endi haqiqatan "qancha signal chiqadi" degan savolga ham
   javob beradi.
2. **O'tganlarning hammasi to'liq shartnomali** — tasodif emas,
   tanlov endi tuzilma sifatiga qarab ishlayapti.

### Kalibrlash QAYTA ISHGA TUSHIRILDI — chegaralar o'zgartirilmadi

EMA olib tashlangach ballar taqsimoti o'zgardi, shuning uchun
`python -m scripts.kalibrlash` qayta ishga tushirildi:

```
Sinalgan sozlamalar : 27      Nomzod chiqdi : 15
Eng yuqori ball     : 68.2    Eng past : 38.4
O'rtacha            : 51.3    Mediana  : 51.9

  chegara  60:   2 / 15 ( 13%)
  chegara  55:   3 / 15 ( 20%)   <- joriy (o'rta salomatlik)
  chegara  50:  10 / 15 ( 67%)   <- joriy (yuqori salomatlik)
  chegara  45:  11 / 15 ( 73%)
```

Loyihaning e'lon qilingan mo'ljali (config izohida) shunday edi:
`55 -> eng yaxshi 33%`, `50 -> eng yaxshi 67%`.

**Natija: 50 aynan mo'ljalda (67%), 55 esa biroz qattiqroq (20%,
mo'ljal 33%).**

CHEGARALAR O'ZGARTIRILMADI, sabab uchta:

  1. **Ikkalasi ham ERISHILADI.** Asosiy xavf — "erishib bo'lmas
     chegara" (40- va 46-bo'limlar) — takrorlanmadi: yuqori bandda
     10 ta, o'rta bandda 3 ta nomzod o'tadi.
  2. **55 ni 54 ga tushirish 15 ta sun'iy namunaga moslash bo'lardi.**
     Taqsimot g'adir-budur: 54.4 da ikkita nomzod turibdi, ya'ni bir
     ballik siljish natijani ikki barobar o'zgartiradi. Bu shovqinni
     sozlash demakdir.
  3. **O'rta salomatlikda qattiqroq bo'lish — mo'ljalga zid emas.**
     Bandning butun ma'nosi shu: bozor kuchsizlanganda talab oshadi.
     Ikki band orasidagi masofa endi kengroq, ya'ni moslashuvchi
     chegara ilgarigidan KO'PROQ ish qiladi.

Yakuniy qaror haqiqiy bozor ma'lumotida:
`python -m scripts.backtest --compare --days 730`.

### Uchidan-uchiga sinov

Butun zanjir tarmoqsiz ishga tushirildi va ishladi: 27 sozlamadan
15 nomzod, Salomatlik 72 -> chegara 50, 10 nomzod o'tdi, eng
yuqorisi 68.2 ball. Signal kartochkasi va "Nega bu signal?" ekrani
to'g'ri chiqdi — dalillar S/R va trend omillari ICHIDA ko'rinadi:

```
▰▰▰▰▰ 23/25 — S/R: ... RBS — buzilgan qarshilik endi qo'llab-quvvatlash;
              🧲 Liquidity Sweep [tuzilma dalili: +1.5 ball]
▰▰▰▰▱ 15/20 — Trend: 🔵 Ko'tarilish trendi (HH/HL), so'nggi BOS ...
```

## 59. Jonli Oshxona — admin monitori (`pipeline_events`)

Restoran metaforasi: oshxona — `core/pipeline`, taom — signal,
qaytarilgan buyurtma — rad etilgan nomzod VA SABABI. Admin
`/admin/jonli` sahifasida tizim orqa fonda nima qilayotganini ko'zi
bilan ko'radi.

**Nima uchun kerak.** "Signal yo'q" degan holat normal (0.2-band),
lekin uni "bot to'xtab qolgan" dan ajratib bo'lmasdi. Endi ajratiladi:
ekranda har bir coin qaysi bosqichgacha yetgani turadi.

**Tahlil kodiga TEGILMADI.** Bosqichlar qat'iy tartibda bajariladi,
demak coin qaysi bosqichda to'xtaganini bilsak, undan oldingilarni
o'tgani ham aniq. `core/pipeline/events.py` shu mantiq bilan
`CycleResult` dan butun ketma-ketlikni QAYTA TIKLAYDI — strategiya
ichiga birorta "hodisa yozish" chaqiruvi qo'shilmadi, ya'ni tahlil
yo'li ham, tezligi ham o'zgarmadi.

**Rostgo'ylik qoidasi.** Ko'rsatilgan har bir ✅ haqiqatan bajarilgan
bo'lishi kerak. Shuning uchun:

* har strategiyaning O'Z zanjiri bor (`CLASSIC_TA_STAGES`,
  `SCALP_STAGES`) — skalpingda `zones` ham, `confirmation` ham yo'q,
  klassik zanjir unga qo'llansa monitor mavjud bo'lmagan bosqichlarni
  "o'tdi" derdi;
* notanish strategiya uchun zanjir to'qib chiqarilmaydi — faqat
  to'xtagan bosqich yoziladi;
* `classic_ta:levels:stop_too_close` kabi aniqroq kod ham `levels`
  bosqichi deb tanib olinadi (aks holda undan keyingi bosqich ham
  "o'tgan" bo'lib chizilardi);
* zanjir tartibi test bilan qulflangan: `test_pipeline_events.py`
  `analyze()` MANBASIDAN haqiqiy tartibni o'qib solishtiradi
  (1-naqsh: "bitta qiymat ikki joyda yozilgan").

**Vaqt darvozalari pastga suriladi.** Skalping oynasi kuniga atigi 45
daqiqa ochiq, ya'ni "oyna yopiq" yozuvi har siklda, har coin uchun
keladi va zanjirda chuqurroq turadi. U klassik tahlilning haqiqiy
sababini bosib ketmasligi uchun `ROUTINE_STAGES` yozuvlari faqat
boshqa sabab bo'lmaganda ko'rsatiladi (voronkadagi qaror bilan bir xil).

**Saqlash — jonli, arxiv emas.** `pipeline_events` jadvali
(migratsiya `c7d2f5a91e40`) har siklda to'ldiriladi va
`monitoring.pipeline_events.retention_hours` (standart 6 soat) dan
eskirgani o'chiriladi. Doimiy statistika allaqachon voronkada va
Signal Xotirasida. Yozish `bot/services/runner.py` da `try/except`
ichida: monitor hech qachon siklni to'xtatmasligi kerak.

**Ekranda.** `jonliHolat()` faqat `max(cycle_at)` ni o'qiydi — ikki
siklni aralashtirsak, bir coin ikki marta va ikki xil natija bilan
chiqardi. Signal chiqqan kartochka yashil (`urgu`) va tepada.
Yangilanish — har 5 soniyada `/api/jonli` (admin-only) ga polling;
WebSocket emas, chunki yangilanish tezligi baribir sikl tezligi bilan
cheklangan, WebSocket esa faqat ulanishni tiklash muammosini qo'shardi.
Uzilish YASHIRILMAYDI: "⚠️ yangilanish uzildi" yoziladi, aks holda
eskirgan ma'lumot jonli deb ko'rinardi.

**Bosqich nomlari — voronkanikidan BOSHQA.** Python'dagi
`STAGE_LABELS` — rad etish sabablari ("Halol ro'yxatda emas"). Ular
voronkada to'g'ri, monitorda esa "✅ Halol ro'yxatda emas" degan
bema'nilik chiqardi. Shuning uchun monitor neytral nomlarni
(`oshxona.b_*`, uz va ru) ishlatadi; kod -> kalit aylantirish
`web/src/lib/oshxona.ts` da, testi bilan.

**Tepadagi xulosa qatori.** Kartochkalarni sanab chiqmaslik uchun:
nechta coin tahlil qilindi, nechtasi signal berdi, eng ko'p qaysi
bosqichda to'xtashdi va o'rtacha/eng yuqori ball. SERVERDA hisoblanadi
(`xulosaHisobla()`) — mijoz tomonda hisoblansa, bir savolga ikki joyda
javob bo'lardi.

**Botda yo'q.** Bunday tezlikdagi yangilanish o'nlab Telegram xabariga
aylanardi — bu funksiya faqat saytning admin panelida.

## 60. Sinov davri — tizim faqat BOZORGA qarab qaror qiladi (100 kun)

Bozor Salomatligi Indeksining bir omili — `aggregate_user_capacity`
(vazni 20) — bozorni emas, BIZNING holatimizni o'lchaydi:
obunachilarning balansi va kunlik xavf sig'imi. Sinov paytida obunachi
yo'q, ya'ni bu omil bozor haqida hech narsa aytmaydi. U yo tekin 20
ball beradi (indeks bor holidan sog'lomroq ko'rinadi), yo bitta test
foydalanuvchisi limitiga yaqinlashsa indeksni tushiradi — bozor esa
o'zgarmagan bo'ladi. Ikkala holat ham sinov natijasini buzadi.

Halollik talabi ham shuni aytadi: ommaga "tizim shu natijani berdi"
deb ko'rsatilganda, o'sha natijaga bizning obunachilar soni
aralashmagan bo'lishi kerak.

**Qanday ishlaydi** (`config/default.yaml` -> `market_health.sinov`):

```yaml
sinov:
  enabled: true
  start_date: "2026-08-29"
  days: 100
  exclude_factors: ["aggregate_user_capacity"]
```

`MarketHealthCalculator._sinov_bilan()` shu davrda:

* chiqarilgan omilning vaznini 0 ga tushiradi va sababini yozadi —
  omil ro'yxatdan O'CHIRILMAYDI (jimgina yo'qolgan omil keyin "nega
  indeks boshqacha?" degan javobsiz savol qoldirardi);
* uning vaznini qolgan omillarga ULUSHIGA QARAB bo'ladi, ya'ni
  vaznlar yig'indisi 100 bo'lib qoladi.

Ikkinchi qadam majburiy: omil shunchaki olib tashlansa, indeksning
yuqori chegarasi 100 dan 80 ga tushardi va 55/70 chegaralari jimgina
boshqa ma'no olardi — bu loyihaning 1-naqshi ("shkala mos
kelmasligi"). Testlar ikkalasini ham qulflaydi.

Muddat tugagach omil O'ZI qaytadi — hech kim hech narsani yoqishi
shart emas. Sayt ham shu YAML dan o'qiydi (`sinovHolati()`), shuning
uchun bot bilan sayt bir kunda bir xil qarorga keladi.

### 60.1 Tormozlar ham ushlab turilmaydi

Maqsad — 100 kun ichida strategiyaning O'ZINI to'liq ko'rish. Signal
berishni BIZNING holatimizga qarab to'xtatuvchi qoidalar bunga
xalaqit beradi: yomon ertalakdan keyin tizim o'zini o'chiradi va
kunning qolgan qismini umuman ko'rmaymiz — namuna qiyshayadi.

Shuning uchun `sinov.suspend_risk_rules` ro'yxatidagi qoidalar shu
davrda tekshirilmaydi:

| Qoida | Nimani o'lchaydi |
|---|---|
| 4.1 `daily_loss_limit` | bugungi/haftalik zararimiz |
| 4.2 `max_open_signals` | nechta signalimiz ochiq |
| 4.3 `correlation` | shu guruhda allaqachon signalimiz bor |
| 4.10 `consecutive_loss` | ketma-ket nechta Stop yedik |

**TO'XTATILMAYDI** — va bu chegara muhim, chunki sinov "hamma narsani
o'chirish" emas: Bozor Salomatligi, BTC filtri, volatillik, narx
yangiligi, halol ro'yxat, juma namozi, favqulodda to'xtash va har bir
signalning O'Z risk qoidalari (Stop/TP/RR, pozitsiya hajmi). Ya'ni
signal SIFATI o'zgarmaydi — faqat "bugunga yetadi" degan tormozlar
ushlab turilmaydi.

Qoida jimgina o'chirilmaydi: har siklda `logger.warning` bilan qaysi
qoidalar to'xtatilgani va necha kun qolgani yoziladi
(`_sinovni_ogohlantir()`), saytda esa Bozor Salomatligi sahifasida
ro'yxati bilan ko'rsatiladi.

**XAVF OCHIQ AYTILADI:** kunlik zarar tormozi yo'q ekan, ketma-ket
zararli kunda tizim o'zini to'xtatmaydi. Sinov davrida obunachi kam
bo'lgani uchun bu ataylab qabul qilingan narx; muddat tugagach tormoz
o'zi qaytadi, yoki YAML dagi bitta qatorni o'chirish bilan darhol
qaytariladi.

### 60.2 Ekranda

Bozor Salomatligi sahifasida o'sha qator "Sinov davri — indeksga
qo'shilmadi" deb ko'rsatiladi, ostida sababi, necha kun qolgani va
to'xtatilgan tormozlar ro'yxati yoziladi.

## 61. TP1 dan keyin: Stop kirish narxiga, kirish esa yopiladi

Ikki qoida, ikki xil odam uchun: signalga ALLAQACHON KIRGAN va HALI
KIRMAGAN foydalanuvchi.

### 61.1 Stop kirish narxiga ko'tariladi (breakeven)

TP1 da pozitsiyaning bir qismi sotiladi (`portfolio.tp1_close_pct`,
standart 50%) va foyda qo'lda qoladi. Qolgan qismni eski Stopda ushlab
turish o'sha foydani qaytarib berish xavfini saqlaydi.

Shuning uchun `Signal.effective_stop` TP1 dan keyin `entry` ga teng
bo'ladi va kuzatuvchi AYNAN SHU darajani kuzatadi. Eng yomon holat —
nolga chiqish. Spot uchun bu ayniqsa to'g'ri: leverage yo'q, ya'ni
"nolda yopish" haqiqatan zararsiz chiqish.

Signal TP1 da YOPILMAYDI — to'liq TP gacha yoki narx kirish narxiga
qaytguncha davom etadi. Botda TP1 xabari bilan birga ko'rsatma
yuboriladi: "🛡 Stopni kirish narxiga ko'taring". Foydalanuvchi buni
O'ZI qiladi — bot uning birja hisobiga ulanmaydi.

### 61.2 Natija endi QISMLI YOPISHNI hisobga oladi

`result_pct` ilgari bitta ayirmadan hisoblanardi:
`(chiqish − kirish) / kirish`. Bu ikki tomonga ham yolg'on edi:

| Holat | Eski (noto'g'ri) | Yangi (to'g'ri) |
|---|---|---|
| TP1 (103) keyin breakeven (100) | 0.0% | +1.5% |
| TP1 (103) keyin TP2 (105) | +5.0% | +4.0% |

Ya'ni breakeven chiqish foydani YO'QOTARDI, TP2 esa haqiqiydan
YUQORI ko'rinardi. Endi ikkalasi ham `blended_result_pct()` orqali
hisoblanadi — bu funksiya `core/domain/portfolio.py` da, chunki u
IKKI joyda kerak: foydalanuvchining pozitsiyasi va signalning o'z
natijasi uchun.

`signals.tp1_reached` ustuni ham shu uchun qo'shildi (migratsiya
`e91b4c7a2d55`): TP1 fakti `status` da SAQLANMAYDI — narx qaytsa
status STOPPED, zaiflashuv belgisi esa WEAKENING qilib qo'yadi.

### 61.3 "Faol emas" — yangi kirish yopiladi, sahifa esa ochiladi

Bu ikkisi ADASHTIRILGAN edi. Sayt TP1 olgan signalni ochishga umuman
yo'l qo'ymasdi (`/signallar` ga qaytarardi), ya'ni signalga KIRGAN
odam ham o'z signalini ko'ra olmasdi — holbuki unga aynan o'sha
paytda breakeven ko'rsatmasi, yangilangan grafik va kalkulyator
kerak edi.

Endi:

* sahifa YOPILMAGAN signal uchun ochiladi (`davomEtmoqda`);
* kartochka, grafik va kalkulyator AMALDAGI Stop bilan ishlaydi
  (`amaldagiStop()` — botdagi `effective_stop` ning aynan aksi);
* kirmagan odamga "⛔ Faol emas — yangi kirish tavsiya etilmaydi"
  yoziladi va "Men sotib oldim" formasi ko'rsatilmaydi;
* botda ham `sig:enter:` shu holatda yangi pozitsiyani qayd etmaydi —
  aks holda botda ruxsat etilgan narsa saytda taqiqlangan bo'lardi.

### 61.4 Kech kirish ogohlantirishi (1.2%)

Narx kirish nuqtasidan `trade_rules.late_entry_warn_pct` (1.2%) dan
ko'p uzoqlashgan bo'lsa, HALI KIRMAGAN foydalanuvchiga xavf
kattalashgani aytiladi va kirish tavsiya etilmaydi.

IKKALA TOMONGA ham: yuqoriga ketgan bo'lsa TPgacha masofa qisqargan
va Stopgacha uzoqlashgan; pastga ketgan bo'lsa Stop yaqinlashgan.
Ikkalasida ham nisbat signal berilgan paytdagi nisbat emas.

Bu TO'SIQ EMAS — ogohlantirish; qaror foydalanuvchiniki. Narx
noma'lum bo'lsa ogohlantirish CHIQMAYDI: yolg'on xotirjamlik ham,
yolg'on vahima ham bermaymiz.

### 61.5 Kalkulyator olingan TP ni FAKT deb sanaydi

Savol: TP1 olingandan keyin uni kalkulyatordan o'chirish kerakmi?
Javob — YO'Q. Olingan TP bashorat emas, allaqachon amalga oshgan
savdo: o'chirilsa, kalkulyator o'sha pulni yo'qotib "hech narsa yo'q"
degan yolg'on manzara ko'rsatardi.

Uning o'rniga TP olingan deb BELGILANADI va hisob shunga moslanadi:

* olingan TP qatori "✅ TP1 olindi" bo'ladi, narxi va ulushi
  QULFLANADI — ular tarixiy fakt (kirish narxi ham shu sababdan);
* **Stop endi faqat QOLGAN qismga** qo'llanadi. Bu jiddiy xato edi:
  pozitsiyaning yarmi sotilgan bo'lsa ham "Stop bo'lsa" qatori to'liq
  summadan hisoblanardi va mavjud bo'lmagan zararni ko'rsatardi;
* uchta yangi qator chiqadi — **Qo'lda** (olingan foyda), **Kutilmoqda**
  (qolgan TP lardan) va **Eng yomon holat** = qo'lda − qolgan qismning
  zarari.

Oxirgisi eng muhimi: "Stop bo'lsa nima bo'ladi?" degan savolga javob
endi manfiy son emas. $1000, kirish 100, TP1 103 (50% olindi), Stop
kirish narxida:

```
✅ TP1 olindi (50% — 5 DOT)     +$15.00 (+3.00%)
🎯 TP2        (50% — 5 DOT)     +$25.00 (+5.00%)
🛑 Agar Stop'ga borsa (50% — qolgan qismga)   $0.00

✅ Qo'lda (olingan foyda)        +$15.00
🎯 Kutilmoqda (qolgan TP)        +$25.00
🛡 Eng yomon holat (Stop bo'lsa) +$15.00
```

## 62. Signal Xotirasi: har bir yopilgan signal jadvali

Haftalik hisobot NAQSH izlaydi va u faqat namuna yetarli bo'lganda
(`postmortem.min_sample_size`, hozir 12) gapiradi. To'g'ri qoida —
lekin sinovning birinchi haftalarida signal bundan kam bo'ladi va
admin qo'lida hech qanday raqam qolmaydi.

Shuning uchun hisobot sahifasiga BIRINCHI signaldan boshlab
ishlaydigan jadval qo'shildi. Har bir savdoda uchta narsa yonma-yon
turadi:

| Ustun | Nima |
|---|---|
| Ball, Bozor Salomatligi | signal berilgan paytdagi SHART |
| Stop, R/R | signalning VA'DASI |
| Vaqt, Natija | YAKUN |

Yakun belgisi TP1 dan keyingi Stopni alohida ko'rsatadi (🎯🛑): u
zarar emas — TP1 dagi foyda qo'lda qolgan.

**Kerakli win-rate** — eng muhim katak. "20% yomonmi?" degan savolga
javob NISBATNI bilmasdan berilmaydi: 1:1.5 nisbatda zarar qilmaslik
uchun 40% kerak, 1:3 da esa 25% yetadi. Shuning uchun haqiqiy
win-rate yonida o'sha davrning o'rtacha nisbatidan hisoblangan
KERAKLI qiymat turadi va rang shu taqqoslashdan chiqadi.

Bekor qilingan signallar (Entry'ga yetmagan) win-rate maxrajiga
kirmaydi: ular savdoga aylanmagan, ya'ni na yutuq, na yutqazish.

Hisob `web/src/lib/signal-tahlil.ts` da — sof funksiya, testi bilan.
Sahifada hisoblansa, strategiya haqidagi xulosaga asos bo'lgan
raqamlarni tekshirib bo'lmasdi.

## 63. Bozor Salomatligi ON/OFF kalit emas — REJIM tanlovchi

**Tashxis.** Indeks past bo'lganda tizim butunlay to'xtardi:
`SignalCycle` coinlarni umuman tahlil qilmasdi va `RiskEngine.score_threshold()`
past bandda `None` qaytarardi — "chegara yo'q, chunki savdo yo'q".

Bu strategiyaning O'Z falsafasiga zid edi. Past indeks — narxlar
ARZONLASHGAN payt, ya'ni "arzon ol, qimmat sot" uchun eng qulay lahza.
Tizim esa aynan shunda ko'zini yumardi va indeks qayta ko'tarilgach —
narx allaqachon o'sib bo'lgach — signal berardi. Ya'ni **doim KECH
kirardi**.

**Yechim.** Indeks endi "ishlaymi yoki yo'q" degan kalit emas, "QANDAY
ishlayman" degan tanlov:

| Indeks | Rejim | Kim ishlaydi | Chegara |
|---|---|---|---|
| yuqori | `NORMAL` | `classic_ta`, `opening_range_scalp` | `threshold_high_health` |
| o'rta | `NORMAL` | hammasi | `threshold_mid_health` |
| past | `CORRECTION` | **faqat** `correction_entry` | `threshold_low_health` (60 — eng qattiqi) |

Kod:

- `RiskEngine.market_regime()` — indeksdan rejimni aytadi
- `RiskEngine.score_threshold()` past bandda endi `None` emas, `60` qaytaradi
- `SignalCycle._for_regime()` — rejimga mos strategiyalarni tanlaydi

Sikl faqat BITTA holatda butunlay to'xtaydi: indeks umuman
hisoblanmaganda (`market_health is None`). "Ma'lumot yo'q" va "bozor
yomon" — ikki boshqa narsa, va ular endi bir xil ko'rinmaydi.

**Nima uchun past bandda chegara QATTIQROQ.** Pasayishda kirish ko'proq
dalil talab qiladi. Chegarani pasaytirish "bozor yomon, shuning uchun
sifatsiz signalga rozimiz" degani bo'lardi — bu aynan teskari mantiq.

---

## 64. Correction Entry — tuzilmaviy kirish (OB / FVG / Fibonacci)

63-bo'limdagi bo'shliqni to'ldiradigan strategiya. U pasayishda ham
qaraydi, lekin **faqat tuzilma ruxsat bergan joyda**.

**Darvozalar, tartibi bilan** (`core/analysis/strategies/correction_entry.py`):

1. `halal` — coin halol ro'yxatidami
2. `data` — yetarli sham bormi
3. `trend` — **kunlik timeframe KO'TARILISHDA bo'lishi SHART**
4. `impulse` — oldin haqiqiy ko'tarilish impulsi bo'lganmi
5. `retracement` — narx Fibonacci "oltin zona"siga (0.382–0.618) tushganmi
6. `confluence` — kamida **2 TURLI manba** bir joyga tushganmi
7. `zone_position` — narx zona ichidami
8. `confirm` — pastki timeframeda (15m) mini OB/FVG tasdiqlanganmi
9. `levels` — Stop juda yaqin/juda uzoq emasmi, R/R yetarlimi

**3-darvoza murosasiz.** Tushayotgan bozorda "arzon" degan narsa yo'q —
narx yana ham arzonlashaveradi. Spot xaridida bu eng qimmat xato.

**Confluence — KESISHMA, birlashma emas.** `find_confluences()` zonalar
bir-birining ustiga tushgan joyni oladi va `strength` sifatida TURLI
manbalar sonini sanaydi. Beshta usuldan "eng mosini" tanlash har doim
qandaydir usul topiladi degani — bu tarixga moslashib qolish
(overfitting). Ikki mustaqil manbaning bir joyda uchrashuvi esa tasodif
bo'lish ehtimoli ancha past.

**ENTRY va STOP bitta manbadan.** Ikkalasi ham topilgan zonadan
chiqadi: Entry — zona ichida, Stop — zonaning pastki chekkasidan
`stop_buffer_pct` past. Ilgari Entry tuzilmadan, Stop esa ATR dan
kelardi — ikki xil mantiq bir signalda.

**Qurish paytida topilgan xato.** Sinovda tuzilmaviy Stop 0.55% chiqdi
va R/R 1:36 bo'lib ketdi — chiroyli raqam, lekin ma'nosiz: bunday tor
Stop oddiy shovqindan ham ishlab ketadi. Stop KENGAYTIRILMADI (bu
tuzilmani buzardi) — o'rniga `levels:stop_too_close` va
`levels:stop_too_far` rad etish sabablari qo'shildi. Tuzilma mos
kelmasa — signal bo'lmaydi.

**Ball tarkibi:** confluence 40, retracement 25, risk_reward 20, RSI 15.

**Coin bo'yicha farq.** Har bir coin uchun Entry/Stop usuli boshqa
bo'lishi mumkin: birida OB, boshqasida FVG, uchinchisida Fibonacci —
qaysi biri o'sha coinning tuzilmasida uchrashsa. Bu qasddan: bitta
qolipni hamma coinga majburlash o'lchanmagan taxmin bo'lardi.

---

## 65. QT davri soatga emas, SHAM STRUKTURASIGA bog'landi

**Eski holat.** Sutka UTC bo'yicha to'rt olti soatlik chorakka
bo'linardi va davr bozor holatidan QAT'I NAZAR har kuni bir xil ritmda
o'zgarardi. Soat 13:00 bo'lgani "hozir asosiy harakat davri" degani
emas — bu o'lchanmagan taxmin edi.

**Yangi holat** (`core/analysis/market_health/quarterly.py`):

| Davr | Sharti |
|---|---|
| A (Accumulation) | tor diapazon, sokinlik — hech narsa buzilmagan |
| M (Manipulation) | likvidlik yig'ib olindi (sweep) — yolg'on harakat |
| D (Distribution) | struktura yaqinda buzildi (BOS) |
| X (Continuation) | buzilishdan keyin narx ushlab turibdi |

Aniqlab bo'lmasa `None` qaytadi va omil **NEYTRAL** bo'ladi. Davr
soatdan "o'ylab topilmaydi" — bu loyihadagi asosiy qoida: bilmaslikni
raqam bilan yashirmaslik.

**Vazn baribir kichik (5).** Bashorat kuchi o'lchanmagan ko'rsatkichga
katta vazn berish bu loyihada allaqachon zarar keltirgan (BTC
Dominance, 33- va 57-bo'limlar). Struktura asosidagi davr ham backtest
bilan tasdiqlanmaguncha shu vaznda qoladi.

Davr `market_health_log.quarterly_phase` ustuniga yozib boriladi —
keyinchalik "qaysi davrda chiqqan signal qanday tugagan" degan savolga
javob berish uchun.

---

## 66. Backtest taqqoslashi: eski tizim vs Correction Entry

**Yangi qoida sinovsiz yoqilmaydi.** `correction_entry` konfiguratsiyada
`enabled: false` holatida turibdi. Kod tayyor, testlar bilan qoplangan,
lekin haqiqiy bozorda o'lchanmagan — shuning uchun jonli ishlamaydi.

**Taqqoslash nimani o'lchaydi** (`scripts/backtest.py --compare`):

| Variant | Ma'nosi |
|---|---|
| `eski: past bandda to'xtash` | `correction_entry.enabled=False` |
| `yangi: Correction Entry` | `enabled=True` |
| `CE: confluence 3` | 2 ta manba yetarlimi yoki 3 kerakmi |
| `CE: R/R 1.5` / `CE: R/R 2.5` | metodikadagi "taxminan 1:2" to'g'rimi |

Eski tizim **taqlid qilinmaydi**: `enabled=False` da past bandda
`_for_regime()` bo'sh ro'yxat qaytaradi va sikl o'sha yerda to'xtaydi —
ya'ni bu aynan eski xatti-harakatning o'zi.

**Topilgan va tuzatilgan xato.** Eski `_variantlar()` EMA davridan
qolgan `trend_requires_price_above_fast` sozlamasini o'zgartirmoqchi
bo'lardi. U sozlama 58-bo'limda olib tashlangan, ya'ni `--compare`
birinchi qadamda `TypeError` bilan tushardi — va buni faqat tarmoqli
mashinada, ma'lumot yuklab bo'lingandan keyin ko'rish mumkin edi.
Endi `tests/core/test_backtest_taqqoslash.py` butun zanjirni sun'iy
qatorda ishga tushirib tekshiradi (raqamlarni emas — MEXANIZMNI).

**O'chirilgan strategiyaning ma'lumoti ham yuklanadi.** `_yukla()` endi
`build_strategies(config, enabled_only=False)` ga tayanadi. Aks holda
`correction_entry` o'chirilgan bo'lgani uchun uning 4h/15m/1d shamlari
umuman yuklanmasdi, taqqoslashda yangi variant nol savdo qaytarardi va
biz buni "strategiya yomon" deb o'qib qo'yardik.

**`--offline` bayrog'i.** Ishlab chiqish muhitida barcha bozor
manbalari yopiq (403). Offline rejim tarmoqqa umuman chiqmaydi va
yetishmagan kesh fayllarini **nomma-nom** aytadi:

```
Offline rejim: quyidagi kesh fayllari yo'q —
  data/candles/BTC_4h.json
  data/candles/ETH_4h.json
```

**Yoqish tartibi** (loyiha egasi bajaradi, serverda):

1. `python -m scripts.backtest --compare --days 365`
2. "yangi" qatori "eski" qatoridan yaxshi bo'lsa → `enabled: true`
3. dastlab kuzatuv ostida, kichik hajm bilan

30 tadan kam savdo bo'lsa hisobot "namuna kichik" ogohlantirishini
chiqaradi — bunday natijadan xulosa chiqarilmaydi.

**`--days 730` JIMGINA ~166 kunga aylanardi.** Ma'lumot yuklovchida
`min(1000, ...)` turardi va Binance provayderi ham so'rovni 1000 ta
sham bilan qirqardi. Kirish timeframei 4 soatlik: 1000 sham — atigi
166 kun. Ya'ni "1-2 yillik backtest" degan MAJBURIY shart
bajarilgandek ko'rinib, aslida bajarilmasdi va bu hech qayerda
aytilmasdi.

`BinanceCandleProvider.fetch_candles()` endi 1000 dan ortig'ini
sahifalab yuklaydi: har safar oldingi sahifaning eng eski shamidan
bir millisekund oldingi vaqt `endTime` ga beriladi. Tarix tugasa
to'xtaydi. 1000 gacha so'rovlar — ya'ni jonli botning yo'li — bir
xil qoladi, `endTime` ham qo'shilmaydi.

Sahifalashning nozik joyi: javobning oxirgi shami yopilmagan
bo'lishi mumkin, lekin bu FAQAT eng yangi sahifaga tegishli. Eski
sahifalarga ham qo'llanilsa, backtest tarix bo'ylab har 1000
shamda bitta soxta "yopilmagan" shamni ko'rardi.

---

## 67. Correction Entry ning R/R si ULANMAGAN edi

Taqqoslashni qurayotib topilgan xato — 66-bo'limdagi ish paytida.

`CorrectionEntryConfig.min_risk_reward` 2.0 deb turardi va strategiya
darajalarni AYNAN shu nisbat bo'yicha qurardi. Lekin `TradeRulesRule`
ning `overrides` ro'yxatida bu manba yo'q edi — demak unga GLOBAL
qiymat (1:3) qo'llanardi. Natijada 1:2 va 1:3 orasidagi har bir
nomzod strategiyadan o'tib, keyingi qadamda jimgina yo'q qilinardi.
Sozlamadagi 2.0 raqami MAVJUD, lekin hech qachon amalda ishlamasdi.

Bu loyihada takrorlanuvchi xato turi: **e'lon qilingan, lekin
ulanmagan**. Avval BTC Dominance bilan (33-bo'lim), keyin Kill Zone
bonusi bilan bo'lgan edi.

Yechim `classic_ta_rules()` bilan bir xil naqsh:
`correction_entry_trade_rules(config)` — YAGONA manba, ikkala tomon
ham shundan o'qiydi.

**TP quyi chegarasi ham boshqacha.** Global 3% `classic_ta` uchun
(3.3-band TP ni 3–5% deb belgilaydi). Bu yerda TP tuzilmadan keladi:
TP2 — impuls cho'qqisi, TP1 — yo'lning yarmi. Shuning uchun chegara
o'ylab topilmaydi, CHIQARIB olinadi:

    eng kichik TP1 = eng kichik Stop x min_risk_reward / 2

Sozlama o'zgarsa chegara o'zi ergashadi.

**TP yuqori chegarasi strategiyaning O'ZIDA tekshiriladi.** Yangi
`levels:tp_too_far` rad etish sababi qo'shildi. Ilgari bunday nomzod
strategiyadan o'tib, Risk Engine'da umumiy "risk qoidalari buzildi"
xabari bilan tugardi — Jonli Oshxonada haqiqiy sabab ko'rinmasdi.
Qoida oddiy: **strategiya Risk Engine rad etadigan narsani
chiqarmasligi kerak.**

**Testdagi "ijobiy yo'l" ham noto'g'ri edi.** Fixture 100 dan 150
gacha impuls berardi, TP2 esa kirishdan 21.16% uzoqda chiqardi —
ya'ni global 20% chegarasidan tashqarida. Test "signal chiqdi" deb
o'tardi, lekin bu signal foydalanuvchiga hech qachon yetib
bormasdi. Cho'qqi 145 ga tushirildi.

---

## 68. Backtest jonli tizim bilan bir xil narsani o'lchamas edi

Terminalsiz ishga tushirish yo'lini qurayotib topildi.

**Bozor Salomatligi noto'g'ri timeframedan o'lchanardi.** Jonli tizim
(`bot/services/runner.py`) struktura kengligini `market_health_timeframe`
(haftalik) qatordan hisoblaydi. Backtest esa uni KIRISH timeframeidan
(4 soatlik) hisoblardi. Ya'ni:

| | Jonli | Backtest (eski) |
|---|---|---|
| Kenglik qatori | haftalik | 4 soatlik |
| QT davri | haftalikdan o'qiladi | **umuman berilmasdi** |

63-bo'limdan keyin indeks butun REJIMNI tanlaydi. Demak backtest
boshqa indeks bo'yicha boshqa rejimda ishlardi va uning javobi jonli
xatti-harakat haqida hech narsa aytmasdi. Bu — 66-bo'limdagi
taqqoslashning ma'nosini yo'q qiladigan xato edi.

Endi `_build_input()` kenglikni salomatlik timeframeidan o'qiydi
(ma'lumot bo'lmasa — jonli tizimdagidek kirish timeframeiga qaytadi)
va `reference_candles` ni ham beradi, ya'ni QT omili sinovda ham
ishlaydi.

Ma'lumot yuklovchi ham tuzatildi: `_kerakli_timeframelar()` endi
strategiyalar so'ragan qatorlarga salomatlik timeframeini QO'SHADI.
U hech bir strategiyaning ro'yxatida yo'q — indeks strategiyadan
tashqarida hisoblanadi — shuning uchun jimgina yuklanmay qolardi.

**Terminalsiz ishga tushirish.** Loyiha egasi buyruq qatori bilan
ishlamasligi mumkin, backtest esa MAJBURIY qadam. Ikki yo'l qo'shildi:

- `BACKTEST.bat` — Windows'da ikki marta bosiladi. Muhitni o'zi
  quradi va `natija.txt` yozadi. PowerShell'ning ijro siyosati
  muammosi chetlab o'tilgan: `activate` umuman ishlatilmaydi.
- `.github/workflows/backtest.yml` — GitHub Actions, brauzerda
  ishlaydi va natijani fayl sifatida beradi. Manba
  `data-api.binance.vision`, chunki GitHub serverlari AQShda va
  `api.binance.com` u yerga 451 qaytaradi.

Skriptga ikkita bayroq qo'shildi: `--output` (hisobotni faylga ham
yozadi — oyna yopilsa yo'qolmasin) va `--base-url` (manbani
almashtirish).

---

## 69. Backtest butun tarixni berardi — jonli tizim esa 500 sham

68-bo'limdagi tuzatishdan keyin GitHub Actions'da ishga tushirilgan
ikki yillik backtest 13 daqiqada ham tugamadi. Sabab qidirilganda
undan kattaroq narsa chiqdi.

**Jonli tizim birjadan `analysis.candles_lookback` (500) tadan ortiq
sham SO'RAMAYDI** (`bot/services/runner.py`). Ya'ni ADX ham, S/R
zonalari ham, struktura ham ana shu 500 shamlik oynada hisoblanadi.

Backtest esa `Dataset.window()` orqali O'SHA PAYTGACHA MAVJUD BUTUN
tarixni berardi. Ikki yillik sinovda bu 4 soatlik qatorda 4380 sham
degani — indikatorlar boshqa oynada, boshqa qiymat bilan chiqardi.
Ya'ni sinov jonli qarorni emas, BOSHQA qarorni o'lchardi.

Bu 68-bo'limdagi xato bilan bir xil turkumdan: backtest bilan jonli
tizim orasidagi jimgina farq. Bunday farq eng yomon xato turi,
chunki natija ishonchli KO'RINADI.

Ikkinchi oqibati — tezlik. Indikatorlar butun ro'yxat bo'ylab
yuradi, ya'ni har qadamda ish hajmi o'sib borardi: O(n²).

`up_to()` va `window()` endi `limit` qabul qiladi, `Backtester` esa
unga `candles_lookback` ni beradi. O'lchov: to'liq taqqoslash
(730 kun, 5 coin, 5 variant) ~6 daqiqa.

---

## 70. Birinchi haqiqiy backtest: tizim ZARAR ko'rsatdi

2026-09-02, 730 kun, 5 coin, 4 380 qadam. To'liq hisobot —
`docs/BACKTEST_NATIJA_2026-09-02.md`.

| konfiguratsiya | signal | savdo | win | o'rt.% | jami% |
|---|---|---|---|---|---|
| eski: past bandda to'xtash | 667 | 649 | 38% | -0.43 | -276.9 |
| yangi: Correction Entry | 671 | 653 | 38% | -0.45 | -293.7 |

**Correction Entry yoqilmadi.** U atigi 4 ta signal qo'shdi va
natijani yomonlashtirdi. Sabab voronkada: `correction_entry:trend`
13 462 marta rad etgan. Kunlik trend ko'tarilishda bo'lishi shart,
Bozor Salomatligi past bo'lganda esa u odatda pastga qaragan —
strategiya o'zi mo'ljallangan lahzada deyarli ochilmaydi.

**Bundan muhimroq: asosiy tizim ham zarar ko'rsatyapti.** 649 ta
savdo — tasodif deb yozib bo'lmaydigan namuna.

Hisob oddiy va shafqatsiz:

    0.299 x 1.5S - 0.621 x S ~ -0.17S,  S ~ 2.5%  ->  -0.43%

Ya'ni 1:1.5 nisbatda foydali bo'lish uchun TP2 gacha 40% yetish
kerak edi, amalda 29.9% yetadi.

### Sabab kodda ochiq turgan ekan

`core/analysis/scoring/levels.py`:

- **TP1 — TUZILMADAN**: eng yaqin resistance zonasi
- **TP2 — FORMULADAN**: `entry x (1 + stop_masofa x nisbat)`

TP2 bozorda nima borligiga umuman qaramaydi. Stop keng bo'lsa u
uzoqqa uchib ketadi, o'sha yerda qarshilik bormi — ahamiyatsiz.
TP1 esa haqiqiy zonada. Shuning uchun narx TP1 gacha yetadi, TP2
gacha 70% holatda yetmaydi.

### Nima QILINMADI

Beshta variantdan eng yaxshisi tanlanmadi. Muammo sozlamada emas,
TP mantiqida — sozlama tanlash tarixga moslashib qolish bo'lardi.

Ball chegarasiga (60) tegilmadi. Dastlabki tahlilda "chegara deyarli
hamma narsani to'sadi" degan xato xulosa bor edi; voronka aslida 29%
o'tkazadi. Xato o'z vaqtida tuzatildi — zarar ko'rsatayotgan tizimda
chegarani pasaytirish zararni ko'paytirardi.

---

## 71. Backtest endi BEPUL emas: komissiya va sirg'anish

70-bo'limdagi raqamlar ham hali OPTIMISTIK edi: savdo xarajatlari
umuman modellashtirilmagan edi.

`BacktestConfig`: `fee_pct` 0.1 (Binance spot taker),
`slippage_pct` 0.05. Pozitsiya ikki marta to'laydi — kirishda va
chiqishda — ya'ni savdo boshiga 0.3%.

649 ta savdoda bu **~195%**. Ya'ni xulosani o'zgartira oladigan
hajm, "kichik tuzatish" emas.

Qiymatlar EHTIYOTKOR tomonga og'dirilgan: kirish ko'pincha LIMIT
buyurtma (5.1.0-band), ya'ni arzonroq. Natijani yaxshiroq
ko'rsatgandan ko'ra yomonroq ko'rsatish afzal.

---

## 72. TP2 tuzilmadan — bayroq ostida, o'lchash uchun

70-bo'lim topgan sababga javob. `trade_rules.tp2_from_structure`
yoqilganda TP2 formuladan emas, **TP1 dan keyingi haqiqiy
resistance zonasidan** olinadi. Zona topilmasa — signal berilmaydi
(`levels:tp2_no_structure`), formula bilan "to'ldirilmaydi".

**Nisbat pasayadi, ehtimol oshadi.** Qaysi tomon og'irroq — bu
taxmin emas, o'lchov savoli. Shuning uchun bayroq standart holatda
`false`.

Risk Engine ham shu manbadan o'qiydi: `classic_ta_rules()` bayroq
yoqilganda `tp2_structural_min_rr` ni qaytaradi. Ansiz darajalar
quriladi-yu, tekshiruv ularni darhol yo'q qilardi — e'lon
qilingan, lekin ULANMAGAN sozlama (67-bo'limdagi xatoning aynan
o'zi).

**Test skanerining o'zida ham teshik topildi.** `test_stage_labels`
bosqich nomlarini `[a-z_]` ifodasi bilan qidirardi, ya'ni ichida
RAQAM bo'lgan nom (`levels:tp2_no_structure`) unga ko'rinmasdi.
Nomsiz qolsa ham test jim o'tardi. Ifodalar tuzatildi.

---

## 73. Tuzilmaviy TP2 — GIPOTEZA RAD ETILDI

To'liq hisobot — `docs/BACKTEST_NATIJA_2026-09-02_2.md`.

```
konfiguratsiya              signal  savdo   win   o'rt.%    jami%  TP2 gacha
eski: formulaviy TP2           667    649   38%    -0.73   -471.6      29.9%
yangi: tuzilmaviy TP2          660    649   38%    -0.98   -634.8      24.7%
tuzilmaviy, nisbat >= 1.5      613    601   38%    -0.91   -544.2      23.0%
tuzilmaviy, nisbat >= 2.0      571    555   38%    -1.01   -560.2      19.5%
```

**Kutilgan:** TP2 haqiqiy zonaga qo'yilsa, unga yetish ehtimoli
oshadi (nisbat pasayishi evaziga).

**Bo'lgan:** ehtimol OSHMADI, pasaydi — 29.9% dan 24.7% ga.

Sabab oldindan ko'rilmagan edi: TP1 dan keyingi haqiqiy resistance
zonasi formuladagi nishondan ko'pincha **UZOQROQ** turar ekan,
yaqinroq emas. "TP2 juda uzoq" degan tashxis to'g'ri edi, taklif
qilingan yechim esa TP2 ni yana ham uzoqlashtirdi.

`tp2_from_structure` **`false` bo'lib qoldi.**

### Xarajat modeli tekshirildi

| | xarajatsiz (#1) | xarajatli (#2) | farq |
|---|---|---|---|
| eski yo'l, jami% | -276.9 | -471.6 | **-194.7** |

Kutilgan: 649 x 0.3% = 194.7%. Aynan mos keldi — ya'ni xarajat
to'g'ri ulangan.

### Ma'lumot yangi joyni ko'rsatdi

Beshta variantda TP2 turli joyga qo'yildi, signal soni 571 dan 671
gacha o'zgardi. **Win-rate esa hamma joyda 37.5–38.4%.**

Bu barqarorlik bitta narsani aytadi: kirishlarning ~62% i TP ga
umuman yaqinlashmay stopga boradi, va TP ni qayerga qo'yish bunga
ta'sir qilmaydi.

Ikki gipoteza (Correction Entry, tuzilmaviy TP2) rad etildi va
ikkalasi ham TP/kirish YO'LI haqida edi. Uchinchi to'plam KIRISHNING
O'ZI haqida: kunlik trend majburiyligi, indikator tasdig'i, ADX
chegarasi, Discount chuqurligi.

**INTIZOM oldindan yozib qo'yildi.** To'rtta gipotezadan eng
yaxshisini tanlab "tasdiqlandi" deyish mumkin emas — bittasi
tasodifan ham yaxshi chiqadi. Yaxshi natija boshqa davrda qayta
tekshirilishi shart.

---

## 74. Kirish filtrlari ham ishlamadi — va nima uchun

To'liq hisobot — `docs/BACKTEST_NATIJA_2026-09-02_3.md`.

| variant | signal | savdo | win | **o'rt.%** | jami% |
|---|---|---|---|---|---|
| hozirgi holat | 667 | 649 | 37.9% | **-0.73** | -471.6 |
| kunlik trend majburiy | 454 | 431 | 37.8% | **-0.65** | -280.2 |
| indikator tasdig'i majburiy | 635 | 616 | 37.3% | **-0.72** | -446.6 |
| faqat kuchli trend (ADX 25) | 540 | 525 | 37.5% | **-0.74** | -386.1 |
| faqat chuqur Discount (40%) | 633 | 610 | 38.0% | **-0.73** | -443.6 |

Birinchi qarashda `kunlik trend majburiy` g'olib: -471.6% dan
-280.2% ga. **Lekin bu savdolar yaxshilanganidan emas, KAMAYGANIDAN:**

    649 x -0.73% = -474%
    431 x -0.65% = -280%

Bitta savdodagi natija atigi 0.08 punktga o'zgardi. Zarar
keltiruvchi ishni kamroq bajarish — tuzatish emas: 0 savdo ham
"yaxshilaydi".

**ASOSIY TOPILMA — win-rate qimirlamadi.** To'rtta mustaqil filtr,
signal soni 454 dan 667 gacha, win-rate esa 37.3–38.0%. TP2 gacha
yetish 28.1–30.0%.

Filtr haqiqatan sifatni oshirsa, o'chirilgan savdolar o'rtachadan
yomonroq bo'lishi va win-rate KO'TARILISHI kerak edi. Bo'lmadi.
Ya'ni filtrlar signallarni kamaytiradi, lekin yaxshisini yomonidan
ajrata olmaydi.

### Nolga chiqish uchun nima kerak

    TP2 (1.5R):  29.9%   TP1+breakeven: 8.0%   stop: 62.1%
    kutilma = 0.299 x 1.5 + 0.080 x 0.375 - 0.621 = -0.14R

Nol uchun TP2 gacha yetish ~35.6% kerak. Eng yaxshi filtr 30.0%
berdi — farqni yopishga yaqin ham kelmadi.

### Uch gipoteza, uch rad

| # | Gipoteza | Natija |
|---|---|---|
| 1 | Correction Entry past bandda yordam beradi | ❌ |
| 2 | Tuzilmaviy TP2 ehtimolni oshiradi | ❌ teskari chiqdi |
| 3 | Kirish filtrlari sifatni oshiradi | ❌ win-rate qimirlamadi |

Uchalasi ham sozlama darajasidagi tuzatish edi.

---

## 75. Tayanch qo'shildi: "olib ushlab turish"

74-bo'lim bir narsani ochdi: **taqqoslash uchun tayanch yo'q edi.**

"O'rtacha -0.73% har savdoda" — bu yomonmi? NIMAGA nisbatan? Agar
sinov davrida coinlar o'sgan bo'lsa, strategiya nafaqat zarar
keltirgan, balki hech narsa qilmaslikdan ham yomon ishlagan
bo'ladi. Agar tushgan bo'lsa — raqam boshqacha o'qiladi.

`BacktestResult.buy_and_hold_pct`: har bir coinga teng ulush,
birinchi qadamda olinadi, oxirgi qadamda sotiladi. Strategiyaning
o'z hisobi (har savdoga teng miqdor) bilan bir xil shkalada.

Hisobot strategiya tayanchdan yomon ishlaganda buni OCHIQ yozadi:
"Strategiya HECH NARSA QILMASLIKDAN yomon ishlagan."

Bu — 3.6-banddagi halollik talabining davomi. O'lchovsiz raqam
ko'rsatish, aslida, raqamni yashirish bilan barobar.

---

## 76. Teskari g'ishtlar to'g'rilandi — va qoida testga aylandi

Qurilish xaritasi ikkita teskari bog'liqlikni ko'rsatdi. Ikkalasi ham
yopildi.

### 1. `storage` -> `analysis`, `pipeline`

Baza qatlami tahlil qatlamidan TUR o'qirdi: `ClosedSignal`,
`SelfAuditReport`, `PipelineEvent`. Poydevor tomga suyanardi.

`core/domain` ga ko'chirildi:

| Tip | Sabab |
|---|---|
| `Outcome`, `EventStatus` | ikkala qatlam ham o'qiydi |
| `ClosedSignal`, `PipelineEvent` | sof ma'lumot, mantiq yo'q |
| `PeriodStats` | sof sonlar |
| `outcome_from_status()` | sof o'tkazish: holat -> natija |

`SelfAuditReport` tahlilda QOLDI — uning ichida `Pattern` ro'yxati
bor va u tahlilning tushunchasi. `AuditReportRepository.save()` endi
butun hisobotni emas, kerakli sonlarni oladi.

### 2. `analysis` -> `position_sizing`

`HealthInputs.capacity` maydonida `AggregateCapacity` obyekti turardi
— ya'ni bozor tahlili foydalanuvchining puliga qarardi.

Endi ikkita son: `capacity_headroom` (0..1) va `capacity_note`.
Salomatlik indeksiga butun obyekt kerak emas — unga faqat "qancha joy
qoldi" degan ulush va bir qatorli izoh yetadi. Omilning o'zi
o'chirilmadi: sinov davri tugagach u qaytadi (60-bo'lim).

### Qoida endi testda

`tests/test_arxitektura.py` har bir `core/` moduliga qavat raqamini
beradi va **bog'liqlik faqat pastga qarashini** tekshiradi. Yangi
modul qo'shilsa, uning qavati aytilmaguncha test yiqiladi — ya'ni
qoida hujjatda emas, kodda yashaydi.

    utils, domain            0
    config, storage          1
    market_data, halal       2
    analysis                 3
    position_sizing, risk    4
    pipeline, services       5
    backtest                 6

---

## 77. Fakt qatlami: struktura endi BIR MARTA hisoblanadi

`analyze_structure()` **yettita joyda** chaqirilardi: runner,
backtest, `classic_ta` (kirish TF + har bir HTF), `correction_entry`,
kenglik, QT davri. Har biri sozlamani o'zi uzatardi — ya'ni bitta
fakt haqida yettita javob bo'lishi mumkin edi.

Bu mavhum xavf emas. Aynan shu turkumdagi uch farq bugun topildi va
ular backtest bilan jonli tizimni ajratib yubordi (68 va 69-bo'limlar).

### Ikki manba qoldi, uchinchisi mustaqil

**1. `StrategyInput.structure(timeframe)`** — strategiyalar uchun.

Kirish endi BITTA COIN uchun bir marta quriladi (`cycle.py`), sozlama
ham unda turadi. Ikkinchi so'rovda kesh qaytadi:

    classic_ta      -> data.structure(entry_tf), data.structure(htf)
    correction_entry -> data.structure(trend_tf)

Ikki strategiya bir xil sham qatori haqida boshqa-boshqa javob bera
olmaydi — bu endi tuzilma darajasida imkonsiz.

**2. `market_health/breadth.py -> universe_facts()`** — kenglik uchun.

Jonli tizim ham, backtest ham shu bitta funksiyani chaqiradi. Ilgari
ikkalasi hisobni o'zida takrorlardi va ular ajralib ketgan edi.

**3. `quarterly.py`** — QT davri o'z oynasida ishlaydi (`lookback=40`)
va sozlamasi boshqacha. U alohida qoladi.

### Qoida testda

- `tests/core/test_fakt_qatlami.py` — kesh ishlaydimi, ikki
  strategiya bitta javobni ko'radimi, va strategiya faylida
  `analyze_structure` qolmaganmi
- `test_mean_reversion_tuzatish.py` — kenglik hisobi ikki joyda
  takrorlanmayotganini tekshiradi

Manba matnini qidirish o'rniga XATTI-HARAKAT tekshiriladi: qisqa
tarixli coin haqiqatan kenglikdan chiqarilyaptimi.

### Refaktorning o'zi TO'RTINCHI farqni topdi

Ikki hisobni bitta funksiyaga birlashtirganda ular bir-biriga mos
kelmadi:

| | ADX qaysi qatordan | |
|---|---|---|
| Jonli tizim | `market_health_timeframe` (haftalik) | |
| Backtest | `entry_timeframe` (4 soatlik) | **farq** |

ADX bozorning volatillik rejimini belgilaydi — ya'ni indeksning
uchdan bir omili. Jonli tizim haftalik ADX ni, backtest esa 4
soatlik ADX ni o'qiyotgan ekan.

Bu 68 va 69-bo'limlardagi uchtasidan keyingi TO'RTINCHISI. Uchtasi
qo'lda qidirib topilgan edi; bu esa **o'zi chiqdi** — ikkita
takrorlangan hisobni bitta joyga qo'yish uchun ular teng bo'lishi
kerak edi, teng emasligi shunda ko'rindi.

Bu — "bitta fakt, bitta manba" qoidasining eng aniq dalili: takror
bo'lgan joyda farq ham bo'ladi, va u faqat qo'shilganda ko'rinadi.

**OQIBATI: backtest raqamlari o'zgaradi.** Bu sof refaktor emas —
u yana bitta bo'shliqni yopdi. Yangi natija eskisi bilan
solishtirilmaydi: eskisi noto'g'ri ADX bilan hisoblangan edi.

---

## 78. Gipoteza daftari: o'lchanmagan raqam ochiq belgilanadi

Config'da uch xil raqam yonma-yon yotibdi va bir xil ko'rinadi:

| tur | misol | savol |
|---|---|---|
| FAKT | `fee_pct: 0.1` | birja shunday oladi — tekshirilmaydi |
| QOIDA | `min_stop_distance_pct: 1` | loyiha egasining qarori |
| GIPOTEZA | `adx_trend_threshold: 20` | **kim o'lchagan?** |

Farq hech qayerda yozilmagani uchun gipoteza vaqt o'tishi bilan
jimgina "haqiqat"ga aylanadi. 67, 73 va 74-bo'limlardagi uchta rad
etilgan gipoteza, va undan oldingi BTC Dominance vazni, Kill Zone
bonusi — hammasi shu sababdan tug'ilgan.

`docs/GIPOTEZA_DAFTARI.md` har bir sozlamani to'rt holatdan biriga
qo'yadi:

```
🔴 o'lchanmagan   130
🟡 qisman           2
🟢 o'lchangan       9
⚫ rad etilgan      6
                 ----
                  147
```

**130/147.** Bu raqamning o'zi tashxis: tizim to'qqiz o'lchangan
raqam va bir yuz o'ttiz taxmin ustida turibdi.

`tests/test_gipoteza_daftari.py` daftarni majburiy qiladi — config'ga
yangi raqam qo'shilib daftarda paydo bo'lmasa, test yiqiladi. Nom,
manzil, timeframe tanlovi va ro'yxatlar `DAFTARSIZ` ro'yxatida:
ular haqida "to'g'rimi" degan savol qo'yilmaydi.

Test noqulay va shundayligicha qoladi. Yozilmagan taxminni bir oydan
keyin tuzatish ancha qimmatga tushadi.

---

## 79. ADX to'g'rilanishi natijani YOMONLASHTIRDI

`07c2147` dan keyingi birinchi yugurish (run #8, `natija_5`):

| | run #7 (noto'g'ri ADX) | run #8 (to'g'ri ADX) |
|---|---|---|
| Signal | 667 | 389 |
| Win-rate | 37.9% | **32.1%** |
| TP2 gacha | 29.9% | **26.1%** |
| O'rtacha savdo | -0.73% | **-1.04%** |

Xato topilganda odatda "endi yaxshilanadi" deb kutiladi. Bu safar
teskarisi: 73 va 74-bo'limlardagi "37-38% win-rate" raqami tizimning
haqiqiy ko'rsatkichi emas ekan. Haqiqiy raqam pastroq.

Tasodifiy kirish 1:1.5 nisbatda 40% beradi. Tizim 26.1% beradi —
ya'ni tasodifdan **1.5 barobar yomonroq**.

**Yangi ma'lumot.** To'g'ri (haftalik) ADX bilan Bozor Salomatligi
indeksi butun ikki yil davomida 26-32 bandida qotdi va sikllarni
to'xtatib turdi. Ayni davrda tayanch **+33.0%**, ya'ni bozor
ko'tarilgan. Indeks ko'tarilgan bozorni "kasal" deb o'qiyapti.

Ya'ni markaziy puls noto'g'ri kalibrlangan. Bu keyingi o'lchanadigan
gipoteza va u oldingi uchtasidan boshqa turkumdan: oldingilar
"signal sifati" haqida edi, bu esa "tizim umuman qachon ishlaydi"
haqida.

---

## 80. Beshinchi farq: indeks sinovning yarmida O'LIK edi

79-bo'limda savol shunday qo'yilgan edi: nega Bozor Salomatligi
indeksi ikki yil davomida 26-32 bandida qotib qoldi, ayni davrda
bozor esa +33.0% ko'tarilgan?

Javob kalibrlashda emas, ma'lumotda chiqdi.

**MEXANIZM.** Isinish davri (`_warmup_steps()`) faqat
`htf_confirmation` ro'yxatiga qarardi. Bozor Salomatligi
timeframei (`1w`) unda yo'q — indeks strategiyadan tashqarida
hisoblanadi. Natijada:

```
isinish (eski)  =  min_candles(60) × (1d / 4h = 6) + 10  =   370 qadam
haftalik uchun  =  min_candles(60) × (1w / 4h = 42) + 10 = 2 530 qadam
```

Tahlil 370-qadamda boshlanardi. 2 530-qadamgacha haftalik qatorda
60 sham yo'q edi, ya'ni `universe_facts()` BO'SH qaytardi:

| omil | vazn | ball |
|---|---|---|
| `halal_structure_breadth` | 45 | **0.0** |
| `volatility_regime` | 15 | **0.0** |

Indeksning **60 balli qismi** 4 010 tahlil qadamining 2 160 tasida
(54%) erishib bo'lmaydigan edi. Qolgan 40 balldan ham indeks 26-32
chiqardi — aynan jurnalda ko'ringan raqam.

Ya'ni sinovning yarmida tizim "bozor kasal" degan qarorni
ma'lumotdan emas, ma'lumot YO'QLIGIDAN o'qirdi.

**TUZATISH.**

1. `core/backtest/warmup.py` — bitta manba. Isinish uzunligi eng
   yuqori timeframedan hisoblanadi va salomatlik timeframei ham
   unga kiradi.
2. Skript sinov oynasidan tashqari **427 kun** isinish tarixini
   yuklaydi. `--days 730` endi "730 kun TAHLIL QILINADI" degani —
   ilgari u jimgina qisqarardi.
3. Kesh uzunligi tekshiriladi: kalta kesh qayta yuklanadi. Ansiz
   eski fayllar jimgina ishlatilib, isinish yana yo'qolardi.

**NIMA UCHUN TEST TUTMADI.** Test bor edi va o'zi ham teshik edi:
u `htf_confirmation` ni tekshirardi, ya'ni hisobning aynan o'sha
qismini. Endi u nomlangan ro'yxatga emas TALABGA qaraydi —
"isinish tugagach har bir timeframeda `min_candles` sham bo'lsin".

Test o'lchayotgan narsani kod bilan bir joydan olsa, u kodni emas,
o'z aksini tekshiradi.

**HISOB.** Bu 68, 69 va 79-bo'limlardan keyingi BESHINCHI
backtest/jonli farqi. Beshtasining ham shakli bir xil: jonli tizim
bir narsani ko'radi, backtest boshqasini, va farq raqamda emas —
natija ishonchli ko'rinishida yashiringan.

**OGOHLANTIRISH.** Run #8 raqamlari (79-bo'lim) shu sababdan
noto'liq: ularning yarmi o'lik indeks ostida olingan.

**TASDIQ (run #9).** Tuzatishdan keyin indeks tirildi — signal
soni 389 dan **884** ga chiqdi, ya'ni 60 balli qism haqiqatan
o'lik bo'lgan ekan. Raqamlar 81-bo'limda.

---

## 81. Nolinchi nuqta: to'g'ri o'lchov bilan birinchi natija

Beshta backtest/jonli farqi tuzatilgandan keyingi birinchi
o'lchov (run #9, `natija_6`). Bundan keyingi taqqoslashlar shu
jadval bilan qilinadi.

| variant | signal | win | TP2 gacha | o'rt.% | jami% |
|---|---|---|---|---|---|
| **hozirgi holat** | 884 | **37.3%** | **30.0%** | **−0.75** | −649.8 |
| kunlik trend majburiy | 610 | 37.3% | 29.4% | −0.68 | −397.8 |
| indikator tasdig'i majburiy | 841 | 36.9% | 30.4% | −0.71 | −584.1 |
| faqat kuchli trend (ADX 25) | 821 | 39.1% | 30.7% | −0.66 | −532.4 |
| faqat chuqur Discount (40%) | 838 | 37.0% | 28.6% | −0.81 | −661.3 |

Tayanch: **+31.5%**. Beshtasi ham tayanchdan yomon.

**INDEKS TIRILDI.** Har bir ko'rsatkich run #8 dan yaxshi:
win-rate 32.1% -> 37.3%, TP2 gacha 26.1% -> 30.0%, bitta savdo
−1.04% -> −0.75%. Jami natija esa yomonlashdi, chunki savdo soni
ikki barobardan ko'p oshdi. Zarar keltiruvchi ishni yaxshiroq
bajarish, ko'proq bajarilsa, ko'proq zarar keltiradi.

**IKKITA XATO BIR-BIRINI QOPLAB TURGAN.** Run #7 (noto'g'ri ADX
+ o'lik indeks) raqamlari run #9 ga juda yaqin: 37.9% / 29.9% /
−0.73% qarshi 37.3% / 30.0% / −0.75%. Noto'g'ri ADX 4 soatlik
qatordan o'qilardi va u haftalikdan yuqori chiqadi, ya'ni o'lik
kenglik omili tushirgan ballni qisman qaytarib berardi. Bu izoh
O'LCHANMAGAN — taxmin. Lekin u bitta narsani aniq ko'rsatadi:
ikkita mustaqil xato natijani "to'g'ri"ga o'xshatib qo'yishi
mumkin, ya'ni "raqam ishonchli ko'rinyapti" tekshiruv o'rnini
bosmaydi.

**XULOSA O'ZGARMADI.** Tasodifiy kirish 1:1.5 nisbatda 40% beradi,
tizim 30.0%. To'rtta filtr win-rate ni 36.9-39.1% oralig'ida
qoldirdi — eng katta farq 2.2 punkt. Oltita gipoteza sozlama
darajasida sinalgan va oltitasi ham rad etilgan.

**YANGI MA'LUMOT: BALL SHIFTI.** Ikki yil, 22 mingdan ortiq
nomzod — eng yuqori ball **aynan 55.0**, ya'ni chegaraning o'zi.
O'rtacha 44.3. Ya'ni "moslashuvchi chegara" amalda moslashmaydi:
yashil (55) va sariq (50) rejim orasidagi farq taqsimotning eng
tepasidagi tor tasma. Ball SIFATNI emas, faqat TARTIBNI beradi —
retseptdagi 3-qadam aynan shu haqida edi, endi uning o'lchovi ham
bor.

---

## 82. Mexanizm o'zgarishi: qaror, TP soni va MUDDAT

81-bo'lim o'lchov ishini yakunladi: sozlama darajasidagi oltita
gipoteza rad etildi, tizim tasodifiy kirishdan yomon ishlaydi.
Bu bo'lim SOZLAMANI emas, MEXANIZMNI o'zgartiradi. Uchalasi ham
bayroq ostida va alohida o'lchanadi.

### 1. Ball faqat TARTIBLAYDI (`scoring.quality_gate`)

Yagona darvoza — ball chegarasi edi. Ball esa nomzodlarni
bir-biriga NISBATAN o'lchaydi: u "eng yaxshisi qaysi" deydi, "shu
yetarlimi" demaydi. Shuning uchun tizim uyumning eng yuqorisini
oladi — uyumning o'zi yomon bo'lsa ham. 74 va 81-bo'limlardagi
natija aynan shunga o'xshaydi: to'rtta filtr uyumga kim kirishini
o'zgartirdi, uyum baribir tartiblanib eng yuqorisi olinaverdi.

O'LIK SIM ULANDI. CryptoSpot3% shartnomasi (yo'nalish + yalash +
daraja turi) allaqachon hisoblanardi va `setup_qualified` da
yotardi — lekin u faqat YORLIQ edi. Ya'ni yangi mantiq yozilmadi,
mavjud dalilga OVOZ berildi.

    eski:  bazaviy ball >= chegara
    yangi: shartnoma bajarildi VA ball xavfsizlik polidan yuqori

`passed_threshold: bool` o'rniga `rejection: str | None`. Ilgari
uchala sabab ham "threshold" deb yozilardi va dashboard "ball
past" deb NOTO'G'RI sabab ko'rsatardi.

NAZORAT VARIANTI zarur: darvoza ikki narsani bir vaqtda qiladi —
shartnomani talab qiladi VA chegarani polga almashtiradi. "Faqat
pol (shartnomasiz)" ikkinchisini alohida o'lchaydi.

### 2. TP soni QAT'IY EMAS (`trade_rules.max_take_profits`)

`SignalLevels` da `tp1` va `tp2` maydonlari turardi, ya'ni "har
doim aynan ikkita" degan qoida MODELGA yozib qo'yilgan edi.
Bozorda esa toza ko'tarilishda ustda bitta ham qarshilik
bo'lmasligi, keng diapazonda esa uchtasi bo'lishi mumkin.

    SignalLevels.takes: tuple[TakeProfit, ...]   # 1..3

`max_take_profits` — YUQORI CHEGARA, majburiy son emas. Uchinchi
TP faqat TP1 bilan yakuniy nishon orasida HAQIQIY zona bo'lganda
qo'shiladi; bo'lmasa ikkitasi qoladi. Raqam o'ylab topilmaydi.

NOM ANIQLASHTIRILDI. `tp2` "ikkinchi" ham, "oxirgi" ham degani
edi — uchta TP bilan bu ikki ma'no ajraladi:

    tp1       BIRINCHI nuqta -> breakeven shundan keyin
    final_tp  YAKUNIY nishon -> signal yopiladi, R/R shundan

Ulush endi darajalarning O'ZIDA (`TakeProfit.close_pct`). Ilgari
bot ham, sayt ham "TP2 = 100 dan qolgani" deb alohida hisoblardi —
"har doim ikkita" taxminining yana ikkita nusxasi.

### 3. FOIZ ORALIQLARI MAJBURIY EMAS (`enforce_distance_bands`)

Loyiha egasining qarori: "TP STOP FOIZLARI MAJBURIY EMAS — RISK
1/3". Bog'lovchi shart bitta — `min_risk_reward`.

Foizlar MASOFA haqida, nisbat haqida emas. Haqiqiy support 5% dan
uzoqroqda, haqiqiy resistance 3% dan yaqinroqda bo'lishi butunlay
normal; ularni majburiy qilish tuzilmani e'tiborsiz qoldirish
demakdir.

`build_levels` ham, Risk Engine ham AYNAN shu bayroqqa qaraydi.
Aks holda darajalar bir qoida bo'yicha qurilib, ikkinchisi
bo'yicha rad etilardi — 67-bo'limdagi xatoning o'zi.

NIMA YO'QOLDI: `min_stop_distance_pct` himoya vazifasini ham
bajarardi (juda tor Stop shovqinda bekorga ishlaydi). Bu himoya
endi `stop_atr_mult` ga qoladi — shovqin ATR birligida
o'lchanadi. To'g'riroq, lekin O'LCHANMAGAN.

### 4. Nomzodga MUDDAT (`trade_rules.max_holding_hours`)

Chiqish qoidasi faqat ikkita edi: TP yoki Stop. Ya'ni tizim
jimgina shunday deb turardi: "bozor qachon bo'lmasin, bir kun
bularning biriga boradi". Uchinchi yo'l — narx o'rtada osilib
qolishi — hisobga olinmagan.

Sanoat naqshida (QuantConnect LEAN) Alpha `Insight` chiqaradi:
yo'nalish, ishonch va MUDDAT. Bizda uchinchisi yo'q edi.

O'lchov: o'rtacha ushlash **45.2 soat**, bozor esa ikki yilda
**+31.5%** o'sgan. Kapital foydasiz pozitsiyalarda band turadi va
o'sha vaqtda ochiq signal limiti to'lgan bo'ladi.

YANGI HOLAT: `SignalStatus.TIMED_OUT` (⏱). U `CANCELLED` dan
farq qiladi va farq muhim:

    CANCELLED   narx Entry'ga yetmadi -> pozitsiya OCHILMAGAN,
                natija yo'q, statistikaga kirmaydi
    TIMED_OUT   pozitsiya ochilgan, bozor narxida yopildi ->
                natija BOR, foyda ham, zarar ham bo'lishi mumkin

Ikkalasini bir turkumga qo'yish raqamlarni buzardi.

To'rtinchi yopuvchi holat qo'shilganda hech bir ro'yxatni qo'lda
yangilash kerak bo'lmadi — u `is_closed` dan o'zi chiqdi
(76-bo'limdagi qoida ishladi).

### Hammasi O'CHIQ holatda keladi

To'rttasi ham gipoteza, fakt emas. Backtest yettita variant
oladi va har biri BITTA o'qni o'zgartiradi (`OLCHOV_OQI`).

### NATIJA (run #10, `natija_7`)

| variant | signal | TP2 gacha | PF | o'rt.% |
|---|---|---|---|---|
| hozirgi holat (oraliqlar o'chiq) | 1297 | 17.1% | 0.30 | −1.31 |
| sifat darvozasi (pol 35) | 446 | 17.0% | 0.29 | −1.43 |
| faqat pol 35 (nazorat) | 2054 | 16.8% | 0.28 | −1.35 |
| **bitta TP** | 855 | **32.4%** | **0.74** | **−0.60** |
| uchtagacha TP | 1297 | 17.1% | 0.28 | −1.37 |
| **foiz oraliqlari yoqilgan** | 884 | 30.0% | 0.64 | **−0.75** |
| muddat 24 soat | 1536 | 9.8% | 0.32 | −1.08 |

**O'LCHOV O'ZINI TEKSHIRDI.** `foiz oraliqlari yoqilgan` varianti
run #9 bazasiga AYNAN teng chiqdi (884 / 37.3% / 30.0% / −0.75 /
−649.8). Ya'ni butun refaktor — `takes` ro'yxati, yangi darvoza,
yangi holat — bayroq yoqilganda xatti-harakatni o'zgartirmagan.

**UCHTASI RAD ETILDI, BITTASI TA'SIRSIZ.** Lekin bu yugurish
oldingilaridan farq qiladi: u faqat "ishlamadi" demadi, SABABNI
ko'rsatdi.

Uchta mustaqil dalil bitta joyga ishora qiladi:

1. Foiz oraliqlari o'chirilganda profit factor 0.64 dan 0.30 ga
   tushdi
2. Bitta TP (qismli sotishsiz) eng yaxshi natija berdi
3. Ikkalasining mexanizmi BIR XIL

Mexanizm:

```
TP1 +0.5% da   -> yarmi sotiladi   -> +0.25%
Stop breakeven -> qolgani nolda    ->  0.00%
komissiya                          -> −0.30%
                                      --------
                                       −0.05%
```

`min_tp_distance_pct` TP1 uchun YAGONA pol edi. U o'chirilganda
TP1 eng yaqin qarshilikka tushdi, Stop esa keng qoldi — kichkina
yutuqlar, katta zararlar.

> **TASHXIS:** muammo "kirish sifati" ham, "TP2 qayerda" ham emas.
> TP1 POLSIZ QOLDI.

Loyiha egasining qoidasi ("foizlar majburiy emas, risk 1/3")
noto'g'ri emas — uni bajarishda xato bo'lgan: nisbat faqat
YAKUNIY nishonga qo'llanilgan. Keyingi o'lchanadigan qadam —
`tp1_min_risk_reward` ni tuzilmaviy TP1 ga ham qo'llash. Bu foiz
emas, NISBAT poli.

### Yo'l-yo'lakay: `win_rate` yolg'on gapirardi

Hisobotda "win-rate 64%" va "o'rtacha −1.31%" yonma-yon turdi.
Ikkalasi ham to'g'ri hisoblangan edi, lekin "g'alaba" so'zi
TURKUMNI bildirardi:

```
eski:  is_win = outcome in {"tp2_hit", "tp1_then_stop"}
yangi: is_win = result_pct > 0
```

`tp1_then_stop` yuqoridagi hisob bo'yicha manfiy chiqadi —
turkum "g'alaba", pul esa kamaygan. "Nishonga yetdimi" degan
boshqa savol `tp2_rate` da qoldi.

O'lchov o'zini o'zi tekshirmasa, u o'lchov emas, bezak.

---

## 83. TP1 nisbat poli — sakkizta urinishdan birinchisi ishladi

82-bo'lim tashxis bilan tugagan edi: **TP1 polsiz qoldi**.
Yechim taklif qilingan edi — foiz emas, NISBAT poli
(`enforce_tp1_ratio`). Run #11 uni o'lchadi.

| | baza | nisbat poli 1.5 | nisbat poli 2.0 |
|---|---|---|---|
| Signal | 1297 | 807 | 643 |
| TP2 gacha | 17.1% | **30.9%** | 27.3% |
| Profit factor | 0.30 | **0.79** | **0.82** |
| O'rtacha savdo | −1.31% | **−0.51%** | −0.51% |
| Maks. pasayish | 1672% | **479%** | 489% |

Bitta savdodagi natija **2.6 barobar** yaxshilandi.

### MEXANIZM

`min_tp_distance_pct` (3%) TP1 uchun YAGONA pol edi. Foiz
oraliqlari o'chirilgach TP1 eng yaqin qarshilikka tushdi:

```
TP1 +0.5% da   -> yarmi sotiladi   -> +0.25%
Stop breakeven -> qolgani nolda    ->  0.00%
komissiya                          -> -0.30%
                                      -------
                                       -0.05%
```

Nisbat poli TP1 ni Stop masofasiga bog'laydi: pol qanoatlantirmagan
zona o'tkazib yuboriladi va KEYINGISI qidiriladi. Signal
yo'qolmaydi — mos zona topilmasa o'lchangan TP ga qaytiladi.

### UCHTA NAZORAT VARIANTI — nima uchun ular zarur edi

Bitta variantni "eng yaxshi" deb tanlash yetarli emas: u
tasodifan ham chiqishi mumkin. Har bir nazorat aniq savolga
javob beradi.

| nazorat | PF | nima aytadi |
|---|---|---|
| foiz oraliqlari yoqilgan | 0.64 | nisbat poli ESKI YO'LDAN yaxshiroq — tashxis yangi narsa qo'shdi |
| bitta TP (qismli sotishsiz) | 0.74 | qismli sotish muammo emas, uning JOYI muammo edi |
| oraliq + nisbat poli | 0.76 | foiz oralig'i nisbat poli ustiga hech narsa qo'shmaydi |

Birinchisi HAL QILUVCHI edi: nisbat poli 0.64 dan past chiqsa,
"foizni qaytargan ma'qul" degan xulosa chiqardi va tashxis
bekor bo'lardi.

Uchinchisi loyiha egasining qarorini raqam bilan tasdiqlaydi:
**foizlar keraksiz, nisbat yetarli.** Oraliq qo'shilganda natija
bir oz YOMONLASHDI — u faqat mazmunli signallarni ortiqcha
kesadi.

### POL QIYMATI: 1.5 tanlandi

2.0 jami natija bo'yicha yaxshiroq (−322.3% vs −408.9%), lekin
**bitta savdodagi natija bir xil** (−0.51%). Ya'ni farq
savdolar yaxshilanganidan emas, KAMAYGANIDAN — bu naqsh
74-bo'limda ham uchragan. Pasayish chuqurroq, ushlash uzunroq.

### NIMA O'ZGARMADI

```
Profit factor:  0.82   (foydali bo'lish uchun >1.0 kerak)
Tayanch:        +31.5%,  strategiya: -322.3%
```

Tashxis to'g'ri edi va yechim ishladi, lekin YETARLI EMAS.

### BAYROQ HALI HAM O'CHIQ

Loyihaning o'z intizomi: "Yaxshi natija BOSHQA DAVRDA qayta
tekshirilishi shart". Bu natija bitta davr, bitta coin
to'plami va bitta yugurishdan olingan. Oltita variantdan eng
yaxshisini tanlab "tasdiqlandi" deyish — backtestning eng keng
tarqalgan xatosi, va biz uni o'z hujjatimizda ogohlantirish
sifatida yozib qo'yganmiz.

Daftarda 🟢 belgisi "o'lchandi va yo'nalish to'g'ri" degani,
"yoqilsin" degani emas.

---

## 84. Sinov OYNASI: takroriy o'lchov endi mumkin

83-bo'lim "bayroq o'chiq" bilan tugadi va sabab bitta edi:
natijani boshqa davrda tekshirishning YO'LI yo'q edi. Backtest
har doim "oxirgi N kun" ni olardi. Ya'ni hujjatlarimizda
qayta-qayta yozilgan talab —

> "Yaxshi natija BOSHQA DAVRDA qayta tekshirilishi shart"

— texnik jihatdan bajarib bo'lmaydigan talab bo'lib turardi.
Bu 78-bo'limdagi naqshning yana bir ko'rinishi: qoida yozilgan,
lekin uni bajaradigan mexanizm qurilmagan.

### O'ZGARISH

`BinanceCandleProvider.fetch_candles(..., until=None)` va
`scripts/backtest.py --end-date YYYY-MM-DD`.

Uchta nozik joy bor edi:

**1. Birinchi sahifa endi "eng yangi" emas.** Provayder javobning
oxirgi shamini yopilmagan deb belgilaydi (66-bo'lim). Oyna oxiri
o'tmishda bo'lsa bu noto'g'ri — u sham allaqachon yopilgan.
`oyna_belgilangan` bayrog'i shu farqni ushlaydi.

**2. Oyna KESH NOMIGA kiradi.** `BTC_4h_2025-09-02.json`. Ansiz
2025-yilgi oyna uchun yuklangan shamlar 2026-yilgi yugurishda
jimgina qayta ishlatilardi va ikkita "mustaqil" o'lchov aslida
BIR XIL ma'lumotda bajarilardi. Bu xatoning eng yomon tomoni —
u xato ko'rinmaydi: ikkinchi yugurish muvaffaqiyatli tugaydi va
"tasdiqlandi" degan xulosa beradi.

**3. Isinish oynadan OLDIN.** `--days 365 --end-date 2025-09-02`
degani "2024-09 dan 2025-09 gacha tahlil qilinadi", va uning
ustiga 427 kunlik isinish yuklanadi (80-bo'lim). Tahlil oynasi
va isinish aralashmaydi.

### QO'RIQCHI

`tests/core/test_sinov_oynasi.py` beshta narsani ushlaydi, eng
muhimi — ikkita oyna bitta kesh faylini bo'lishmasligi.

### BUNDAN KEYIN

Endi 🔴 savolga javob berish mumkin: TP1 nisbat poli boshqa
davrda ham ishlaydimi. Ikkita kesishmaydigan yil o'lchanadi.
Bitta oynada ishlab, ikkinchisida ishlamasa — bu gipoteza rad
etilgan demak, va daftarga shunday yoziladi.

---

## 85. Takroriy o'lchov tasdiqladi — va mexanizmni tuzatdi

84-bo'lim sinov oynasini qurdi. Birinchi ishlatilishi
83-bo'limdagi ochiq savolga javob berdi.

### NATIJA TAKRORLANDI

Oyna B (2022-09 → 2024-09) — oyna A bilan umuman
kesishmaydi, alohida yuklangan. Oltita variantning TARTIBI
ikkalasida ham bir xil:

```
                          PF, A    PF, B
hozirgi holat              0.30     0.34
foiz oraliqlari (nazorat)  0.64     0.75
bitta TP (nazorat)         0.74     0.87
oraliq + nisbat poli       0.76     0.83
TP1 nisbat poli 1.5        0.79     0.93
TP1 nisbat poli 2.0        0.82     1.01
```

Oldindan yozilgan qoida bajarildi, shuning uchun bayroq
yoqildi: `enforce_tp1_ratio: true`, `tp1_min_risk_reward: 2.0`.

### YOQISHDA YASHIRIN BOG'LIQLIK OCHILDI

Testlar darhol yiqildi va sabab qiziq bo'lib chiqdi. Tizimda
ikkita nisbat bor:

```
trade_rules.tp1_min_risk_reward         2.0   TP1 uchun POL
strategies.classic_ta.min_risk_reward   1.5   YAKUNIY nishon
```

Pol yakuniy nishondan yuqori. Ya'ni polga bo'ysungan har
qanday TP1 avtomatik ravishda yakuniy nishondan ham uzoqda —
"ikkinchi nishon" degan narsa qolmaydi.

Kod buni jimgina hal qilardi:

```python
if nishon <= tp1:
    nishon = tp1 * 1.001      # TP2 = TP1 + 0.1%
```

Kartochkada: **TP1 130.00, TP2 130.13**. 0.1% masofa hatto
kelib-ketish xarajatini (0.3%) ham qoplamaydi.

Bu — 67 va 77-bo'limlardagi naqshning yana bir ko'rinishi:
raqam quriladi, keyin boshqa qoida uni jimgina yo'q qiladi va
hech qayerda xato ko'rinmaydi.

### XULOSA TUZATILDI, NATIJA EMAS

O'lchangan mexanizm "TP1 ni yaxshiroq joyga qo'yish" emas
ekan:

> yagona nishonni yetarlicha UZOQQA (Stop×2) va imkon bo'lsa
> haqiqiy zonaga qo'yish.

Buning izi raqamlarda ham bor edi va ilgari e'tibor
berilmagan: win-rate va "TP2 gacha" deyarli teng (34.6% va
34.3%) — chunki TP1 va TP2 amalda bitta narx edi.

### KOD ENDI BUNI OCHIQ QILADI

Yasama `tp1 * 1.001` olib tashlandi. TP1 allaqachon 1:N
nisbatidan uzoqda bo'lsa, signal BITTA TP bilan quriladi va
butun pozitsiya o'sha yerda yopiladi.

Loyiha egasining qoidasiga mos ("2 TP majburiy emas — 1, 2
yoki 3 bo'lishi mumkin, sharoitga qarab"), lekin hozir bu
TANLOV emas, MAJBURIYAT. Shuning uchun oltinchi to'plam aynan
shu haqda: yakuniy nishon nisbati polidan yuqoriga
ko'tarilsa, haqiqiy ikkita TP qaytadi — natija saqlanadimi?

`tests/core/test_tp_soni_moslashuvchan.py` da bu oqibat
alohida test bilan yozib qo'yilgan, unutilmasin uchun.

---

## 86. Tuzilma o'zgardi: har timeframe BITTA ish qiladi

Oltita gipoteza to'plami sinaldi va hammasi CHIQISH yoki BALL
haqida edi. Kirish tanlovining o'zi hech qachon o'zgarmadi —
aynan u zaif: o'nta signaldan uchtasi nishonga yetadi, kerakli
miqdor to'rt-beshta.

Loyiha egasining tashxisi (2026-09-03) boshqa joyni ko'rsatdi.

### TOPILGAN TO'RTTA KAMCHILIK

**1. Bitta dalil bir necha marta sanaladi.** Bir nechta
timeframe bitta ballga qo'shiladi, lekin ular mustaqil emas:
kunlik ko'tarilish va 4 soatlik ko'tarilish ko'pincha AYNAN bir
xil narsa.

**2. Hech kim "YO'Q" deya olmaydi.** Haftalik tushayotgan
bo'lsa ham, boshqa beshta omil yaxshi bo'lsa ball yetadi va
signal chiqadi. Ballda faqat "kamroq ball" bor, "to'xta" yo'q.

**3. Mayda timeframe xarajatdan kichik.** 15 daqiqalik shamda
narx chorak foiz yuradi, kelib-ketish xarajati 0.3%.

**4. Zona qidiruvi juda uzun.** 500 sham ≈ 83 kun, va kod uch
oy oldingi darajani bugungisi bilan TENG hisoblaydi.

### YANGI TUZILMA

```
haftalik   ->  yo'nalish   (bu hafta nima kutamiz)
kunlik     ->  rejim       (bugun qay holatda)
4 soatlik  ->  kirish      (tahlil shu yerda)
```

Haftalik va kunlik SIGNAL BERMAYDI — ular rejimni aytadi
(`core/analysis/regime.py`):

| rejim | qoida |
|---|---|
| ko'tarilish | tuzatish kutiladi (odatiy Discount) |
| diapazon | faqat TUB (chuqurroq talab) |
| pasayish | umuman olinmaydi |

Rejim ball emas, SHART. U `analyze()` da ZONALARDAN OLDIN
turadi va bu tasodif emas: pasayayotgan bozorda zona qidirishning
ma'nosi yo'q.

### POYDEVOR TEKSHIRILDI — birinchi marta

`tests/core/test_poydevor_tekshiruvi.py`. Shamlar QO'LDA
quriladi, ya'ni to'g'ri javob oldindan ma'lum. Bozor ma'lumoti
ishlatilmaydi — u yerda "to'g'ri javob" degan narsa yo'q.

Tekshirildi va ta'rifga mos ishlaydi: S/R zonalari, tegishlar
soni, HH/HL va LH/LL, FVG bo'shlig'i, order block tanasi,
impuls yo'nalishi.

**BITTA KAMCHILIK TOPILDI VA HUJJATLASHTIRILDI.** Klassik
ta'rifda order block impulsi tuzilmani BUZISHI kerak (oldingi
cho'qqi olinadi). Bizning aniqlovchi buni talab qilmaydi: har
qanday tushuvchi shamdan keyin ~1% ko'tarilish bo'lsa, u "order
block" deb belgilanadi — pasayish trendi ichida ham. Ya'ni
"order block yaqinida" degan ball ko'pincha oddiy qizil shamga
beriladi.

Ball noto'g'ri emas — u shunchaki o'zi o'ylagan narsani
o'lchamaydi.

### SKALP O'CHIRILDI

`opening_range_scalp` — o'lchov asos bo'ldi: oxirgi yugurishda
eng ko'p rad etish o'sha strategiyadan chiqdi (16 473 marta hajm
sharti), signal esa deyarli bermasdi. Kod registrda qoladi,
faqat bayroq o'chdi — qaror o'lchovga tayangan va o'lchov
qaytarilishi mumkin.

Shu bilan 15 daqiqalik qator umuman yuklanmaydi.

### HAMMASI BAYROQ OSTIDA

`regime_rules.enabled` va `zone_lookback` standart holatda
o'chiq. Yettinchi to'plam ularni o'lchaydi, va "skalp yoqilgan"
NAZORAT varianti o'chirish to'g'ri qaror edimi degan savolga
javob beradi.

Ogohlantirish daftarga ham yozildi: shunga o'xshash narsa bir
marta sinalgan — "kunlik trend majburiy" filtri (natija #3), va
u ishlamagan. Farqi shundaki, u FILTR edi va faqat kesardi; bu
yerda har rejim uchun BOSHQA qoida bor.

### O'LCHANDI: REJIM RAD ETILDI (natija #11)

Ogohlantirish o'rinli chiqdi.

```
                signal    win     PF    o'rtacha
hozirgi holat     603    28.9%   0.84    −0.46%
rejim yoqilgan    410    27.4%   0.75    −0.75%
```

Rejim 193 ta signalni (32%) kesdi va qolganlari YOMONROQ
chiqdi — ya'ni u o'rtachadan yaxshi savdolarni olib tashladi.
Bayroq o'chiq qoladi.

Skalp qarori esa nazorat bilan TASDIQLANDI (PF 0.84 vs 0.83),
zona oynasi ta'sirsiz (bitta savdoda 0.01 punkt).

Yettita to'plamdan keyin win-rate hali ham 27-29% da qotib
turibdi. Kod tozalandi, tuzilma tushunarli bo'ldi — lekin
kirish tanlovi tasodifdan yaxshi emasligi o'zgarmadi.

Yangi 🔴: rejim 21 000 nomzoddan 10 463 tasini "haftalik yoki
kunlik pasayishda" deb rad etdi, ayni davrda bozor +31.5%
ko'tarilgan. Struktura aniqlovchisi haftalik qatorda pasayishni
ortiqcha ko'rayotgan bo'lishi mumkin — bu tekshirilmagan.

---

## 87. Kitobning yadrosi o'lchandi — va rad etildi

Loyiha egasi manba berdi: "PRICE ACTION STRATEGIES — TOP 15"
(`docs/NARX_HARAKATI_STRATEGIYALARI.md`). To'qqizta XARID
strategiyasidan oltitasi aynan bir xil uch qadamni takrorlaydi:

    1. daraja YORIB o'tiladi
    2. narx unga QAYTA SINOVGA keladi
    3. o'sha yerda BUQASIMON sham  ->  kirish

Bizda bu yo'q edi — `classic_ta` qaytishni kutmaydi va tasdiq
so'ramaydi. Kitob esa aynan shu xatoni ogohlantiradi.

`core/analysis/narx_harakati.py` + alohida strategiya qurildi.
Faqat XARID: kitobdagi sotish naqshlari umuman qurilmagan
(loyiha egasining sharti va kitobning o'z qoidasi).

### NATIJA

```
                         signal    win     PF    o'rtacha
classic_ta                  603   28.9%   0.84    −0.46%
narx harakati (kitob)       300   21.3%   0.74    −0.46%
```

**Bitta savdodagi natija AYNAN BIR XIL.** Ikkita butunlay
boshqa kirish mexanizmi, bir xil o'rtacha. Win-rate esa
pasaydi.

Kitobning eng ko'p takrorlangan qoidasi — buqasimon shamni
kutish — ham yordam bermadi: tasdiqsiz variant biroz
yaxshiroq chiqdi (PF 0.85 vs 0.84).

### XULOSA QATTIQLASHDI

Sakkizta to'plam, kirish tomonida beshta rad etish. Endi
ikkita mustaqil dalil bitta narsani aytadi:

> 4 soatlik shamlardan hisoblanadigan hech bir naqsh keyingi
> harakatni oldindan aytmayapti.

### BITTA FOYDALI FARQ

Kitob usuli tinch: pasayish 451% dan 185% ga tushdi, savdo
soni ikki barobar kam. Foyda bermaydi, lekin kapitalni kamroq
silkitadi.

---

## 88. Sayt uchun bozor ko'rinishi — signaldan AJRATILGAN

Loyiha egasining sharti:

> "Haftalik va kunlik shunchaki qarash. Asosiy tahlil 4
>  soatlik. Bu umumiy ta'sir qilmaydi, faqat veb sayt uchun
>  post. San uni 4 soatlikka bog'lama."

Bu shart 86-bo'limdagi rejim tajribasidan keyin keldi va u
bilan bir xil javob beradi: rejim (haftalik/kunlik 4 soatlik
kirishni to'sadigan qilib) O'LCHANDI VA RAD ETILDI —
PF 0.84 → 0.75.

Ya'ni qaror ham, o'lchov ham bir tomonda.

### QURILDI

    core/analysis/bozor_korinishi.py    postni quradi (sof)
    core/market_data/global_metrics.py  TOTAL va ustunliklar
    bot/services/bozor_korinishi.py     yozadi va saqlaydi
    web .../bozor/page.tsx              ko'rsatadi

Ko'rsatiladigan ro'yxat loyiha egasi bergani: BTC, ETH, BTC.D,
USDT.D, TOTAL, TOTAL2, TOTAL3, OTHERS.

### NIMA UCHUN QIYMATLAR SAQLANADI

BTC.D, TOTAL va hosilalari birjadan SHAM sifatida kelmaydi —
manba faqat hozirgi holatni beradi. Yo'nalish esa tarixsiz
aniqlanmaydi, shuning uchun har kuni o'zimiz yozib boramiz
(`bozor_kesimlari` jadvali).

### AJRALISH KOD BILAN QULFLANGAN

`tests/core/test_bozor_korinishi.py` strategiya va quvur
fayllarini skanerlaydi. Ularda `bozor_korinishi` so'zi paydo
bo'lsa test yiqiladi. Izoh yozib qo'yish yetarli emas —
loyihada izoh bir necha marta koddan ajralib ketgan.

### TAXMIN YOZILMAYDI

Post FAKT beradi: qiymat, o'zgarish, yo'nalish. "Kutilma"
qatori esa an'anaviy o'qishdan iborat va har safar "Kafolat
emas" deb belgilanadi — test buni ham tekshiradi.

---

## 90. Ablation va walk-forward — o'lchovning o'zini o'lchash

Ikkita yangi skript qo'shildi. Ikkalasi ham FAQAT o'lchaydi: ball
mantig'iga, vaznlarga, chegaralarga va strategiya kodiga tegmaydi va
`config/default.yaml` ga hech narsa yozmaydi.

    python -m scripts.ablation_test --days 730
    python -m scripts.walk_forward --days 730 --bolaklar 3

Tarmoq yopiq mashinada `--offline`, brauzerda esa
`.github/workflows/tekshiruv.yml` (Actions -> "Tekshiruv"). Natija
`reports/` ga CSV va matn bo'lib tushadi; papka `.gitignore` da —
xulosa qilingan natija `docs/` ga QO'LDA ko'chiriladi.

### Ablation — omilning haqiqiy hissasi

Vaznlar (25/20/15/15/10/15) o'ylab qo'yilgan, o'lchab emas. Skript har
bir omilni navbat bilan chiqarib to'liq backtestni qaytadan yuritadi.
IKKI xil chiqarish bor va ular boshqa-boshqa savolga javob beradi:

    nol            vazn 0, qolganlari o'zgarmaydi. Shkala 100 dan
                   pasayadi, ya'ni chegaradan o'tish qiyinlashadi —
                   bu "omil YO'Q bo'lsa" holati.

    qayta taqsim   vazn 0, uning ulushi qolganlarga NISBATIGA qarab
                   bo'linadi. Shkala 100 bo'lib qoladi, chegara
                   ham o'sha — bu "omil MA'LUMOTI yo'q bo'lsa"
                   holati, ya'ni sof ablation.

Ikkinchisisiz ablation omilni emas, chegarani o'lchagan bo'lardi.

### Walk-forward — tanlov keyingi davrda saqlanadimi

Tarix teng bo'laklarga bo'linadi. Har bo'lakda parametr to'ri
sinaladi va PF bo'yicha eng yaxshisi tanlanadi; o'sha tanlov KEYINGI
bo'lakda hech narsa o'zgartirmasdan qo'llanadi. Yonma-yon TAYANCH
ham yuritiladi — hozirgi sozlama aynan shu tekshiruv bo'lagida.

Uchinchi qator eng muhimi: tanlangan sozlama tayanchdan yomon chiqsa,
qidiruv foyda emas, ZARAR keltirgan degani.

Qidiriladigan uchta parametr allaqachon mavjud
(`tp1_min_risk_reward`, `classic_ta.min_risk_reward`,
`entry_max_range_pct`) — walk-forward yangi g'oya sinash uchun emas,
tanlovning barqarorligini tekshirish uchun.

ISINISH. Har bo'lak o'zidan oldingi tarixni isinish sifatida oladi,
lekin savdolarini QO'SHMAYDI. Kesim chegarasi shunday tanlanadiki,
dvigatel o'zining `warmup_steps` qadamini o'tkazib bo'lgach aynan
bo'lak boshida turadi — buni `tests/test_olchov_skriptlari.py`
qulflaydi. Kam bo'lsa bo'lakning boshi yeb ketilardi, ko'p bo'lsa
oldingi bo'lakning savdolari shu bo'lakka qo'shilib, "out-of-sample"
degan so'z ma'nosini yo'qotardi.

## 91. Ablation va walk-forward natijasi — tanlash qatlami ishlamayapti

To'liq raqamlar: `docs/BACKTEST_NATIJA_2026-09-03_3.md`.

Birinchi marta ball VAZNLARI o'lchandi. Sof ablationda (shkala 100
bo'lib qoladi, faqat omilning ma'lumoti olinadi):

    S/R zonasi   25 ball   PF 0.84 -> 0.80    ma'lumot beradi
    Risk/Reward  15 ball   PF 0.84 -> 0.77    eng katta hissa
    MACD         10 ball   PF 0.84 -> 0.81
    RSI          15 ball   PF 0.84 -> 0.83    ta'sirsiz
    Hajm         15 ball   PF 0.84 -> 0.83    ta'sirsiz
    Trend        20 ball   PF 0.84 -> 0.83    ta'sirsiz

Ballning 60 punkti nomzodlarni tartiblashga deyarli hech narsa
qo'shmayapti. Hech biri zarar ham keltirmayapti — birortasi olib
tashlanganda natija yaxshilanmadi.

VAZNLAR O'ZGARTIRILMADI. Alohida-alohida ta'sirsiz bo'lish birga
ham ta'sirsiz degani emas: to'rttasi bir vaqtda olib tashlanganda
nima bo'lishi hali o'lchanmagan (daftarda 🔴).

Walk-forwardda uch bo'lakning har birida 12 sozlama sinaldi va
g'olib keyingi bo'lakda qo'llandi. Tanlov tayanchdan +0.01 va
−0.00 punkt farq qildi — ya'ni backtestda "eng yaxshi" deb
topilgan sozlama keyingi davrda hech narsani yaxshilamaydi. Ijobiy
tomoni: hozirgi sozlama tarixga moslashib qolmagan.

Yangi 🔴 — natija uch davrda ketma-ket pasaydi:

    2024-08 -> 2025-04   PF 1.00   foydali 33.5%
    2025-04 -> 2025-12   PF 0.84   foydali 29.7%
    2025-12 -> 2026-09   PF 0.69   foydali 27.6%

Bitta davr tasodif bo'lishi mumkin, uchtasi ketma-ket esa
yo'nalish. 85-bo'limdagi oyna B (2022-09 -> 2024-09, PF 1.01) ham
shu chiziqqa tushadi.

XULOSA. Natija #12 ikkita boshqa KIRISH mexanizmi bir xil natija
berganini ko'rsatgan edi. Bu ikki o'lchov esa TANLASH qatlami
haqida bir xil narsani aytdi: nomzodlar orasidan "eng yaxshisi" ni
tanlash mexanizmi haqiqiy ustunlik bermayapti.

## 89. Bosqichlar holati

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

---

## 92. YANGI TAHLIL MODULI — to'rt blokli zanjir (2026-09-03)

Eski modul butunlay o'chirildi (`OCHIRISH_ROYXATI.md`) va o'rniga
boshqa arxitektura qurildi. To'liq tavsif:
`docs/YANGI_TAHLIL_MODULI.md`.

### Nima o'zgardi — bitta jumlada

```
ESKI:  6 omil QO'SHILADI    -> yig'indi chegara bilan solishtiriladi
YANGI: 4 blok KETMA-KET     -> biri bo'sh bo'lsa zanjir UZILADI
```

Yig'indida bitta kuchli omil qolgan beshtasining yo'qligini yopib
ketardi. Zanjirda bunday almashtirish mumkin emas — har bir blok
o'z halqasi.

### Uchinchi holat: `MALUMOT_YOQ`

Bu — modulning eng muhim qarori va u loyihaning eng qimmat
saboqidan kelib chiqadi.

Har bir tekshiruv UCHTA javob beradi: `HA`, `YOQ`, `MALUMOT_YOQ`.
Uchinchisi blok MAXRAJIGA kirmaydi.

Nima uchun: fundamental manbalarning yarmida 2 yillik tarix yo'q
(`FUNDAMENTAL_MALUMOT_MANBALARI.md`). "Ma'lumot yo'q" ni "yo'q" deb
hisoblasak, backtestda 1-blok doim 0/4 chiqib zanjir HECH QACHON
ulanmasdi — ya'ni biz strategiyani emas, ma'lumot yetishmasligini
o'lchagan bo'lardik.

Blok "2/4" o'rniga halol "1/2" yozadi.

### Zona bloki boshqalaridan farq qiladi

Blok 1, 2 va 4 da har bir ichki tekshiruv MUSTAQIL ovoz. Blok 3 da
esa Fib/OB/FVG — bir-birini ICHIGA OLGAN qatlamlar:

```
faqat Fib         ZAIF
Fib + OB          O'RTA
Fib + OB + FVG    KUCHLI
```

OB va FVG faqat Fib zonasi bilan KESISHSA hisoblanadi. Aks holda
grafikning boshqa-boshqa joyidagi uchta zona "3/4 kuchli" deb
o'qilardi — aslida ular uchta alohida daraja, konfluensiya emas.

Zona natijasi Entry va Stop uchun ham ishlatiladi: qatlamlarning
KESISHMASI olinadi (birlashma emas — u Stopni uzoqlashtirib R/R ni
buzardi).

### Eski xatolar qaytarilmadi — ro'yxat

| Eski xato | Yangi tizimda |
|---|---|
| `entry = joriy narx` (LIMIT tarmog'i o'lik edi) | Entry zona ichida yoki zona chetida |
| Qat'iy foizli Stop/TP | Zona chetidan va struktura nuqtalaridan |
| Ko'p qat'iy "VA" filtri, voronka nolga | Blok 1/4 bilan ham o'tadi |
| Ma'lumotsiz omil ball berardi | `MALUMOT_YOQ` maxrajdan chiqadi |
| Pastki TF uchun ALOHIDA kod | O'sha funksiyalar qayta chaqiriladi |
| Trailing Stop TP1 dan oldin | Faqat TP2 dan keyin, standart holatda O'CHIQ |

### Yassi grafik tuzatildi (qurish paytida topilgan)

Birinchi versiyada `qarshi_choch_yoq` yo'nalish umuman aniqlanmagan
holatda ham `True` qaytardi. Oqibati: YASSI, o'lik grafik ham
"qarshi CHOCH yo'q ✅" olardi va struktura bloki 1/3 bilan o'tardi
— ya'ni hech narsa bo'lmagani "yaxshi xabar" deb o'qilardi.

Endi na BOS, na CHOCH bo'lsa `None` qaytadi va tekshiruv
o'lchanmagan deb belgilanadi. Bu — eski tizimni o'ldirgan naqshning
aynan o'zi edi (hissa qo'shmaydigan omil ball berardi).

### Bosqichma-bosqich holat (6-qism)

`state_tracker.py` zanjirni har sham yopilganda to'liq qayta
hisoblamaydi. Tartib QAT'IY:

1. Eski "to'liq" bloklar TEZ tekshiriladi (qattiq to'siq / qarshi
   CHOCH / narx zonadan chiqdimi)
2. Buzilgan bo'lsa — o'sha blokdan KEYINGI hammasi bekor qilinadi
3. Faqat shundan keyin — hali to'lmagan blok yangilanadi

Teskarisi bo'lsa: 4-blok tasdiqlanadi, signal chiqadi, va faqat
keyin 2-blokning buzilgani ma'lum bo'lardi — signal ALLAQACHON
yuborilgan bo'lardi.

---

## 93. Sig'im o'lchovi — portfel chegarasi alohida o'lchanadi (2026-09-04)

`ZanjirBacktest` sukut bo'yicha portfel chegaralarini
QO'LLAMAYDI. Bu — ataylab qilingan tanlov va 92-bo'limda
yozilgan: zanjirning O'Z sifati o'lchanayotganda `max_open_signals`
aralashmasligi kerak.

Lekin "aralashmasin" degani "unutilsin" degani emas. Eski
tizimning eng katta yo'qotishi aynan shu yerda edi:
`risk_engine` 4 668 nomzoddan 593 tasini o'tkazgan va sababning
87% i `max_open_signals` bo'lgan. Ya'ni bir necha hafta davomida
strategiya emas, portfel chegarasi o'lchangan.

Shuning uchun `sigim=True` bayrog'i qo'shildi va u ALOHIDA
skriptda (`scripts/zanjir_sigim.py`) ikkita bir xil yugurishni
solishtiradi. Bayroqsiz hech narsa o'zgarmaydi — test bilan
qulflangan.

### O'rin cheklanganda kim kiradi

Sig'im yoqilganda savol tug'iladi: beshta o'rin bor, sakkizta
nomzod bor — kim kiradi?

Javob: **ishonchi eng yuqori nomzod**. Nomzodlar shu qadam ichida
yig'iladi va `ishonch()` bo'yicha tartiblangandan keyin
joylashtiriladi.

Ansiz o'rinni har doim `symbols` ro'yxatida oldinroq turgan coin
egallardi. Natijada o'lchov coinlar ro'yxatining TARTIBIGA
bog'lanib qolardi — ya'ni o'lchov o'zi haqida yolg'on gapirardi.
Bu qatorlarni tekshiradigan test:
`test_sigimda_kuchli_nomzod_orinni_oladi`.

### Nima o'lchanmaydi

Kunlik/haftalik zarar chegaralari, kill switch, juma filtri —
BULAR QO'SHILMADI. Ular vaqtga bog'liq va tarixiy simulyatsiyada
qanday qo'llanishini ALOHIDA hal qilish kerak. Taxmin qilib
qo'shilsa, natija "o'lchandi" deb ko'rinardi-yu, aslida taxmin
bo'lardi.

---

## 94. PORTFEL VA XAVF BOSHQARUVI MODULI (2026-09-04)

Tahlil moduli **qayerga kirishni** aytadi. Bu modul **qancha pul
bilan kirishni va qachon chiqishni** aytadi. Ikkalasi bir-biriga
bog'lanmaydi.

Nima uchun ajratilgan: 2026-09-04 dagi $1000 hisob simulyatsiyasi
(`docs/BACKTEST_NATIJA_2026-09-04_hisob.md`) shuni ko'rsatdi —
tahlil moduli PF 3.49 bergan bo'lsa ham, pul taqsimoti sababli
hisob **−68.1%** ga tushdi. Ya'ni signal to'g'ri, taqsimot noto'g'ri
edi. Bitta modul ichida bu ikkisi aralashib turganda sabab ko'rinmasdi.

### To'rt qism

| Fayl | Vazifa |
|---|---|
| `capital_allocator.py` | balansni N ta teng bo'lakka bo'lish, signalga bo'lak topish |
| `exit_manager.py` | N ta TP ga moslashuvchan chiqish, Stop ko'chishi |
| `pnl_calculator.py` | realized / unrealized, davrlar bo'yicha |
| `pnl_dashboard.py` | bot va sayt uchun bitta manzara |

### Mustaqillik — izoh emas, test

`core/portfolio/` **hech qanday `core.*` paketga bog'lanmaydi**.
Buni ikki test ushlab turadi:

* `tests/test_arxitektura.py` — portfel 0-qavatda;
* `tests/core/test_portfel_mustaqil.py` — AST orqali har bir
  importni tekshiradi va soxta signalni to'liq yo'ldan o'tkazadi.

Kimdir kelib unga `core.analysis` importini qo'shsa, test darrov
yiqiladi. 3-promptning asosiy sharti shu edi.

### Kapital bo'laklari

Balans N ta teng bo'lakka bo'linadi (boshlang'ich N = 3). Har bir
bo'lak **o'zining** ichki zarar chegarasiga ega — umumiy balansdan
emas, bo'lakning o'zidan hisoblanadi:

    Stop% <= chegara  ->  bo'lakning to'lig'i
    Stop% >  chegara  ->  ulush = chegara / Stop%

Ikkinchi holatda pozitsiya kichrayadi, lekin **xavf baribir
chegarada qoladi**: (hajm × chegara/stop) × stop = hajm × chegara.

Barcha bo'laklar band bo'lsa — signal **kutadi**, rad etilmaydi.

### Kafolat qayerda ishlamaydi

3-prompt aytadi: "hamma bo'lak band bo'lib, hammasi Stop ursa —
umumiy zarar ~10%". Bu **bo'lakda bitta pozitsiya** bo'lgandagina
to'g'ri.

O'sha promptning o'zi ishlatilmagan qismni keyingi signalga berishga
ruxsat beradi. Bo'lakda ikkita pozitsiya bo'lsa, o'sha bo'lakning
xavfi chegaradan oshadi — o'lchangani: **20%**
(`test_bolakda_IKKITA_pozitsiya_bolsa_xavf_chegaradan_OSHADI`).

Shuning uchun raqam taxmin qilinmaydi: `umumiy_xavf_pct()` uni har
safar o'lchaydi va ekranda ochiq ko'rsatiladi.

### N ta TP — yashirin shartsiz

    TP[k] ga yetganda:  1/N sotiladi, Stop -> TP[k-1]
    k = 1 bo'lsa:       Stop -> Entry (breakeven)
    oxirgi TP da:       qolgan hammasi

Kodda birorta `if tp_soni == 2` yo'q. Testlar N = 1, 2, 3, 5, 8 ni
parametr sifatida yuradi — yashirin shart paydo bo'lsa, N = 5 da
darrov yiqiladi.

Eski `core/position/scaling_out.py` da ulushlar qo'lda yozilgan
jadval edi (50/50, 40/30/30) va u faqat 1–3 TP ni bilardi.

### Raqam TAXMIN qilinmaydi

Bu modulda birorta ham "kutilayotgan oylik foyda" turidagi doimiy
yo'q. Har bir raqam kiruvchi yozuvlardan chiqadi; yozuv bo'lmasa —
nol qaytadi va ekran **rostini aytadi** ("hozircha yopilgan savdo
yo'q"), taxminiy raqam emas.

Shu sababdan **`pnl_records` jadvali ataylab yaratilmadi**. Yig'ilgan
raqamni alohida saqlash ikkinchi haqiqat manbaini yaratardi va vaqt
o'tib ikkalasi farq qila boshlardi. Kunlik/haftalik/oylik natija
`position_exits` yozuvlaridan har safar qayta hisoblanadi.

### "Narx olinmadi" ≠ "savdo nolda"

Ochiq pozitsiyaning joriy narxi olinmasa, `joriy_narx = None` bo'ladi:
u unrealized hisobiga kirmaydi va ekranda alohida aytiladi
("❓ N ta ochiq savdoning joriy narxi olinmadi").

Ilgari bunday holatda kirish narxi qo'yilardi va ekranda "+$0.00"
chiqardi — ya'ni **ma'lumot** ko'rinishida. Aslida bu "biz
bilmaymiz" edi.

### Bitta manba, ikki ekran

Bot ham, sayt ham `dashboard_qur()` dan o'qiydi. Sayt TypeScriptda
ishlagani uchun u yerda ikkinchi nusxa bor (`web/src/lib/portfel.ts`),
lekin nusxa **etalon fayl bilan bog'langan**:

    scripts/portfel_fixtures.py -> tests/portfel_fixtures.json
        tests/test_portfel_fixtures.py   (Python tomon)
        web/tests/portfel.test.ts        (sayt tomoni)

Biror tomon o'zgarsa testlardan biri yiqiladi. Bu naqsh loyihada
allaqachon bor edi (`hajm_fixtures`), shuning uchun takrorlandi.

### Baza

| Jadval | Nima uchun |
|---|---|
| `capital_blocks` | bot qayta ishga tushganda "bu bo'lak band" bilimi yo'qolmasin — aks holda o'sha bo'lakka ikkinchi pozitsiya ochilib xavf ikki barobar bo'lardi |
| `position_exits` | TP1 dushanba, TP2 payshanba bo'lishi mumkin; "bugungi natija" faqat QISM darajasidagi yozuvdan to'g'ri chiqadi |

### O'lchanmagan qolgani

`bolak_soni` (3) va `bolak_chegara_pct` (10) — ikkalasi ham gipoteza
daftarida 🔴. 3-promptning o'zi ularni "boshlang'ich qiymat" deydi.
Ular backtestda hali sinalmagan; sinalgunicha raqam taxmin bo'lib
qoladi va daftarda shunday ko'rinib turadi.
