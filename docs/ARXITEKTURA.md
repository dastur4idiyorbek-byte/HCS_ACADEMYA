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

## 12. Bosqichlar holati

| # | Bosqich | Holat |
|---|---|---|
| 1 | Arxitektura skeleti | ✅ |
| 2 | DB sxemasi (15 jadval) | ✅ |
| 3 | Bot "tana" qismi | skelet tayyor |
| 4 | Halol skrining (Top 30 Halal) | ✅ |
| 5 | Signal moduli + WebSocket | interfeys tayyor |
| 6 | Support/Resistance | — |
| 7 | Indikatorlar | — |
| 8 | Ball hisoblash + backtest | — |
| 9 | Risk Engine | ✅ (13 qoida) |
| 10 | Bozor Salomatligi Indeksi | modellar tayyor |
| 11 | Pozitsiya hajmi + agregat balans | ✅ |
| 12 | Opening range scalp | interfeys tayyor |
| 13 | Postmortem (Signal Xotirasi) | DB tayyor |
| 14 | Shaxsiy portfel | DB tayyor |
| 15 | Hammasini bog'lash | — |
| 16 | Backtest (1-2 yillik) | — |
| 17 | Test va sozlash | davomiy |
