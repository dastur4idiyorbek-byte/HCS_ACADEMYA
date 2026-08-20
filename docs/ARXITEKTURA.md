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

## 31. Bosqichlar holati

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
| 17 | Test va sozlash | davomiy |
