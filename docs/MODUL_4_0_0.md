# MODUL 4.0.0 — "Portlash xavfi radari"

Yagona manba. Kod shu hujjatga qarab quriladi; qaror o'zgarsa, avval
shu fayl o'zgaradi.

Holat: **hamma qarorlar loyiha egasi tomonidan tasdiqlangan
(2026-10-14)**.

---

## 1. Modul nima

Binance Futures'dagi barcha USDT juftliklarini kuniga 12 marta
tekshiradigan **kuzatuvchi**. LSK kabi holatlarni (bir kunda 500%+
sakrash) oldindan sezishga yordam beradi.

**Signal bermaydi.** Entry / Stop / TP yo'q, "sotib ol" yoki "sot"
demaydi. Faqat: *"bu coinda g'ayrioddiy faollik bor, kuzatib boring."*

LSK darsi: kichik kapitalizatsiya + yupqa likvidlik + kutilmagan
yangilik + ko'p shortlar = portlash. Modul 3.0.0 bunday ma'lumotni
yig'maydi (u spot struktura bilan ishlaydi).

## 2. Qat'iy chegaralar

- Modul 3.0.0 ga (`core/watch_panel`, `kuzatuv`, `qidiruv`) **hech
  qanday o'zgartirish kiritilmaydi**.
- Alohida kod papkasi (`core/portlash_radari/`), alohida jadvallar
  (`radar_*`), alohida sahifa (`/modul-4`).
- Mavjud tizimdan **faqat o'qiladi**: halol reestr (`coin_rulings` va
  80 talik ro'yxat) va unlock kalendari (`UnlockManba`).
- Pullik signal oqimiga umuman aralashmaydi.
- **Telegram botga hech narsa qo'shilmaydi** (loyiha egasining qarori,
  2026-10-14: "botga shart emas, faqat veb uchun"). Bot kodiga
  tegilmaydi. Ma'lumotni serverda **alohida jarayon** yig'adi:
  `python -m core.portlash_radari` — `scripts/start.sh` uni bot va sayt
  yonida ishga tushiradi va yiqilsa o'zi qayta ko'taradi. Radar
  yiqilsa bot ham, sayt ham ishlayveradi.
- Natija faqat yangi sahifada va **faqat admin uchun**. Menyudagi
  "Modul 4.0.0" tugmasi ham faqat adminga ko'rinadi.
- Ma'lumot manbai: Binance Futures (bepul, kalitsiz). Kapitalizatsiya
  va ta'minot — CoinGecko (bepul). Futures ma'lumoti **faqat bozor
  haqida ma'lumot** sifatida o'qiladi — loyihada futures, short yoki
  leverage savdosi yo'q va bo'lmaydi.
- Kodda Entry/Stop/TP hisoblaydigan modul import qilinmaydi — test
  buni mexanik tekshiradi.

## 3. Nomlanish

- Modul raqami **4.0.0**. Qo'shimcha ish → 4.0.1, 4.0.2 ...; butunlay
  yangi modul → 5.0.0.
- Pastki navdagi **Modul** tabi ichida ikki bo'lim: Modul 3.0.0 va
  Modul 4.0.0.
- Logotip (S → T, "HCT") — alohida ish, kodni to'xtatmaydi. Hozircha
  mavjud ikonka ishlatiladi.

## 4. Universum va 0-darvoza

- Binance Futures `exchangeInfo`: `contractType = PERPETUAL`,
  `quoteAsset = USDT`, `status = TRADING`, `underlyingType = COIN`
  (bo'lsa). Stablecoinlar (`halal_screening.stablecoin_symbols`)
  chiqariladi.
- 80 talik ro'yxatdagi coinlar ham kiradi.
- `1000PEPE`, `1000000MOG`, `1MBABYDOGE` kabi ko'paytirgichli nomlar
  reestr va CoinGecko uchun asl belgiga keltiriladi (`PEPE`, `MOG`,
  `BABYDOGE`). Foiz hisobiga ko'paytirgich ta'sir qilmaydi.
- **Hajm darvozasi:** 24 soatlik hajm ≥ **$500 ming** (ticker'dan,
  so'rovsiz).
- **Kapitalizatsiya darvozasi:** ≥ **$10 mln** — **elakdan keyin**
  qo'llanadi, chunki ma'lumot faqat 20-30 coin uchun so'raladi.
  Kapitalizatsiya noma'lum bo'lsa coin chetlatilmaydi (bilmaslik
  coinni tozalab ham, chetlatib ham qo'ymaydi) — kartochkada
  "kapitalizatsiya noma'lum" deb yoziladi.

## 5. Tekshiruv mantig'i — ball emas, sanoq

- Har tekshiruv: ✅ tasdiqlandi / ❌ tasdiqlanmadi / ⚪ ma'lumot yo'q.
- Natija — nechtasi ✅. Og'irlik, formula yo'q.
- Har tekshiruv yonida qiymat, chegara va manba ko'rsatiladi.
- **Ikki guruh** (sanoq hali ham ball emas, faqat bo'lib ko'rsatiladi):
  - **Harakat** — "bo'lyapti": 1, 2, 6
  - **Yoqilg'i** — "bo'lishi uchun sharoit bor": 3, 4, 5, 7
  - Ko'rinishi: `5/7 · Harakat 3/3 · Yoqilg'i 2/4`

## 6. Bosqichlar

### 1-bosqich — elak

- Hajm (24s) / 30 kunlik o'rtacha ≥ **3 barobar**.
- **Yangi listing** (Binance'da 30 kundan kam yoki tarix 7 kundan kam)
  ham elakdan o'tadi — ularda o'rtacha yo'q.
- 30 kunlik o'rtacha **kuniga bir marta** (00:05 UTC) hisoblanib,
  `radar_hajm` jadvalida saqlanadi. Sessiyada faqat solishtiriladi —
  elak bitta so'rovga tushadi.
- Tasdiqlash (B) sessiyasida pool = elakdan o'tganlar **+ shu shamning
  kashfiyot (A) sessiyasidagi nomzodlar** (B ularni qayta tekshiradi).

### 2-bosqich — 7 ta tekshiruv

| № | Kod | Nomi | Guruh | ✅ sharti | ⚪ qachon |
|---|---|---|---|---|---|
| 1 | `hajm` | Hajm anomaliyasi | harakat | hajm / 30k o'rtacha ≥ **5x** | tarix yo'q (yangi listing) |
| 2 | `narx` | Narx harakati | harakat | \|24s o'zgarish\| ≥ **20%** | ticker yo'q |
| 3 | `funding` | Funding ekstremali | yoqilg'i | \|funding (8 soatga keltirilgan)\| ≥ **0.1%** | funding yo'q |
| 4 | `oi` | Open Interest o'sishi | yoqilg'i | **8 soatda** OI (kontrakt soni) ≥ **+30%** | OI tarixi yo'q |
| 5 | `long_short` | Long/Short og'ishi | yoqilg'i | nisbat ≥ **2.5:1** istalgan tomonga | ma'lumot yo'q |
| 6 | `btc` | BTC'dan mustaqillik | harakat | \|coin − BTC (24s)\| ≥ **15 punkt** | BTC yoki coin yo'q |
| 7 | `taminot` | Ta'minot tarkibi | yoqilg'i | aylanma/maksimal < **60%** yoki **7 kunda** ≥ **5%** unlock | ikkalasi ham noma'lum |

Izohlar:

- **Funding normallashtiriladi.** Binance'da funding oralig'i coinga
  qarab 8, 4 yoki 1 soat (`/fapi/v1/fundingInfo`; ro'yxatda yo'q coin
  — 8 soat). Qiymat `stavka × 8 / oraliq` bilan 8 soatlik ekvivalentga
  keltiriladi.
- **OI kontrakt sonida** (`sumOpenInterest`) o'lchanadi, dollarda
  emas: dollar qiymati narx bilan o'sadi va pozitsiya o'sishini narx
  harakatidan ajratib bo'lmay qoladi.
- **Ta'minot:** aylanma = aylanmadagi / maksimal (maksimal yo'q bo'lsa
  — umumiy). "Kamida 90% aylanmada" degan qattiq filtr **yo'q**: LSK da
  aylanma ~70.6% edi va qulfdagi qismning bo'shatilishi portlash
  sabablaridan biri bo'lgan.
- Aniq raqamlar (5x, 20%, 0.1%, 30%, 2.5:1, 15, 60%, 7 kun, 5%) — sinovdan
  o'tmagan taklif. Ular **admin sahifasida o'zgartiriladi** (13-bo'lim).

### Halol reestr — sanoqqa kirmaydi

Faqat yonida ko'rsatiladi:

| Holat | Qachon |
|---|---|
| ✅ halol | `coin_rulings` da `halal`, yoki 80 talik ro'yxatda (ishchi taxmin) |
| ❌ harom | `coin_rulings` da `haram` |
| ⚠️ shubhali | `coin_rulings` da `mashbooh`, yoki stablecoin |
| ❔ hali baholanmagan | hech qayerda yozilmagan |

**Nega `verdict_for()` emas:** u reestrda yo'q coinga `HALAL` qaytaradi
(`core/halal_screening/rulings.py`). Yuzlab futures coinida bu yolg'on
"✅ halol" bo'lib chiqardi. Modul reestrni o'zi o'qiydi va
"yozilmagan"ni "halol"dan ajratadi. Halol moduliga tegilmaydi.

### 3-bosqich — sanoq, holat, o'rin

- **NOMZOD:** 7 tadan kamida **4 tasi ✅**.
- **TASDIQLANGAN:** A da nomzod va B da ham nomzod.
- **VAQTINCHALIK EDI:** A da nomzod, B da pasaygan — asosiy ro'yxatdan
  tushadi, "O'tkinchi holatlar" bo'limida ko'rinadi.
- A sessiyasi o'tkazib yuborilgan bo'lsa (bot o'chiq edi), B nomzodi
  oddiy "nomzod" bo'lib qoladi — tasdiqni bilib bo'lmaydi.
- **O'rin** — har sessiyada pooldagi hamma coin (yashirilganlardan
  tashqari) tartiblanadi:
  1. ✅ soni (ko'pi yuqorida)
  2. TASDIQLANGAN oldin
  3. Yoqilg'i ✅ soni (ko'pi yuqorida)
  4. Hajm nisbati (kattasi yuqorida; noma'lum — oxirida)
  5. Symbol (alifbo — natija har doim bir xil chiqsin)
- "Ketma-ket" hisoblagichi tartibga ta'sir qilmaydi.

## 7. Kartochka ko'rinishi

```
LSKUSDT — 5/7 · Harakat 3/3 · Yoqilg'i 2/4      🆕   Halol reestr: ❔

✅ Hajm anomaliyasi     — o'rtachadan 8.2 barobar        (Binance, 30k o'rtacha)
✅ Narx harakati        — 24 soatda +287%                (Binance ticker)
✅ Funding ekstremali   — −0.34% (8 soatga keltirilgan)  (Binance premiumIndex)
✅ OI o'sishi           — 8 soatda +41%                  (Binance openInterestHist)
❌ Long/Short og'ishi   — 1.8:1 (chegara 2.5:1)          (Binance globalLongShort)
✅ BTC'dan mustaqillik  — farq 287.7 punkt               (Binance ticker)
❌ Ta'minot tarkibi     — aylanma 70.6%, yaqin unlock yo'q (CoinGecko, DefiLlama)

XULOSA: G'ayrioddiy faollik: ... KUZATIB BORING — bu signal emas.
```

- 🆕 — bu safar yangi chiqdi; 🔁 N — oldingi sessiyadan davom etyapti
  (N-marta ketma-ket). Faqat ma'lumot uchun.

## 8. Vaqt jadvali — kuniga 12 marta

Binance 4 soatlik shamlari (UTC): 00, 04, 08, 12, 16, 20.

| Bosqich | Qachon | UTC | Qirg'iziston (UTC+6) |
|---|---|---|---|
| **A — Kashfiyot** | shamdan **1 soat** oldin | 23:00, 03:00, 07:00, 11:00, 15:00, 19:00 | 05:00, 09:00, 13:00, 17:00, 21:00, 01:00 |
| **B — Tasdiqlash** | shamdan **15 daqiqa** oldin | 23:45, 03:45, 07:45, 11:45, 15:45, 19:45 | **05:45, 09:45, 13:45, 17:45, 21:45, 01:45** |

- **Rasmiy sessiya — B.** Grafik, jadval va calibration faqat B
  natijalaridan quriladi (kuniga 6 nuqta). A faqat nomzod qidiradi va
  B dagi "tasdiqlangan" belgisini beradi.
- Vaqt UTC da hisoblanadi, ekranda **Asia/Bishkek** vaqti.
- Kechikish chegarasi: A — 40 daqiqa, B — 14 daqiqa. Bot shu vaqtdan
  keyin ko'tarilsa, o'sha sessiya o'tkazib yuboriladi (ekranda
  "o'tkazib yuborildi" bo'lib turadi) — sun'iy to'ldirilmaydi.
- Admin istalgan paytda **qo'lda tekshiruv** boshlay oladi. U rasmiy
  zanjirga, grafikka va calibration'ga kirmaydi.

### Kun

- **1 kun = 6 ta rasmiy (B) sessiya.** Kun 05:45 da boshlanadi va
  01:45 (keyingi kalendar kunining tungi soati) sessiyasi bilan
  yopiladi.
- Texnik ta'rif: kun = B sessiyasi oldidan turgan 4 soatlik shamning
  UTC sanasi. 23:45 UTC sessiyasi keyingi kunning 00:00 shamiga
  tegishli, demak keyingi kunning 1-sessiyasi.

## 9. "Eski holat yopishmasin"

- Har sessiya hisobi noldan boshlanadi.
- "Ketma-ket" hisoblagichi faqat ma'lumot uchun, qarorga ta'sir
  qilmaydi. Sessiyada nomzod bo'lmasa — 0, coin joriy ro'yxatdan
  chiqadi. Kechirim yo'q.
- Qayta paydo bo'lsa — yangi voqea (hisoblagich 1 dan).
- Joriy ro'yxat faqat oxirgi sessiyani ko'rsatadi — tarixiy "shuhrat"
  yo'q. (Calibration jadvali bundan mustasno: u natijani o'lchaydi.)

## 10. Grafik va sessiya jadvali

### Grafik — o'rin oqimi (bump chart)

- Tepada: `[1 kun] [3 kun] [1 oy]` va kunlar qatori
  (`Bugun · Kecha · 12-okt · ...`, 30 kungacha).
- **1 kun:** tanlangan kunning 6 ta rasmiy sessiyasi. Bugungi varaq
  sessiya o'tgan sari o'ngga o'sadi; kun tugagach tarixga o'tadi va
  yangi kun 1-sessiyadan boshlanadi.
- **3 kun:** uch kunning sessiyalari ketma-ket (18 nuqtagacha).
- **1 oy:** har kun bitta nuqta — kunlik umumiy o'rin (B-variant):
  kun davomida Top-10 da eng ko'p turgan 10 ta coin, teng bo'lsa
  o'rtacha o'rin bo'yicha. Bitta g'alati sessiya kunni buzmaydi.
- Har coin — bitta chiziq. Y o'qi: 1..10 o'rin; tagida **"Top-10 dan
  tashqari"** zonasi (coin o'z raqami bilan, masalan #13) va **"chiqdi"**
  zonasi (elakdan ham tushgan).
- Grafikka shu oynada kamida bir marta Top-10 ga kirgan coinlar
  chiziladi. O'tkazib yuborilgan sessiya ustuni bo'sh qoladi.
- 30 kundan eski kunlar ko'rsatilmaydi.

### Sessiya jadvali

```
Bugun — 14-oktabr

Coin | 1-sessiya 05:45 | 2-sessiya 09:45 | 3-sessiya 13:45 | ...
LSK  | #1    —         | #13   +38%      | #4    −6%       |
ABC  | #2    —         | #6    −4%       | chiqdi +2%      |
XYZ  | —               | #3    —         | #1    +11%      |
```

- **O'rin:** shu sessiyada tekshiruvdan keyin bergan o'rni.
- **Foiz:** oldingi rasmiy sessiyadagi narxdan shu sessiyagacha
  o'zgarish. Coin oldingi sessiyada o'rin olgan bo'lsagina hisoblanadi.
- **"chiqdi":** oldingi sessiyada o'rin olgan, endi elakdan ham
  tushgan coin. Uning narxi baribir yoziladi va foizi ko'rinadi.
- **"—":** oldingi sessiyada ro'yxatda yo'q edi.
- Kunning 1-sessiyasi foizi kechagi oxirgi (01:45) sessiyadan
  hisoblanadi — kunlar narx orqali bog'lanadi, varaq esa yangi.
- Jadvalga oynada Top-10 ga kirgan coinlar + oynadan oldingi
  sessiyada Top-10 da bo'lganlar kiradi.
- Narx nomi: **"o'sha sessiyadagi narx"**. "Kirish narxi" so'zi
  ishlatilmaydi — modul signal bermaydi.

## 11. Calibration — o'zini-o'zi tekshirish

- Har rasmiy sessiyada pooldagi **hamma** coin yoziladi (faqat
  nomzodlar emas) — aks holda nomzod bo'lmay portlaganlarni hech qachon
  ko'rmaymiz.
- **Nazorat guruhi (namuna):** har sessiyada hajm darvozasidan o'tgan,
  lekin elakdan o'tmagan **10 ta** coin (har sessiya uchun bir xil
  takrorlanadigan tanlov) ham to'liq tekshiriladi va yoziladi. Ular
  o'ringa kirmaydi. Agar namuna coinlari tez-tez portlasa — elak
  yaxshi coinlarni o'tkazib yuboryapti degani.
- Har yozuv uchun **24 soat** va **7 kun** keyin: oxirgi narx, eng
  yuqori o'sish, eng chuqur tushish (1 soatlik / 4 soatlik shamlardan).
- **"Portlash"** (statistika uchun): 24 soatda eng yuqori o'sish ≥ 20%,
  7 kunda ≥ 50% (sozlanadi).
- Sahifada: nomzodlar / nomzod bo'lmaganlar / namuna bo'yicha portlash
  ulushi; har tekshiruv uchun ✅ va ❌ bo'lganda portlash ulushi;
  ✅ soni (0..7) bo'yicha ulush. Kam ma'lumotda ogohlantirish chiqadi.
- Yashirilgan coin ham calibration'ga yoziladi — statistika buzilmasin.

## 12. Ma'lumot manbalari

| Manba | Endpoint | Qachon |
|---|---|---|
| Binance | `/fapi/v1/exchangeInfo` | har sessiya, 1 so'rov |
| Binance | `/fapi/v1/ticker/24hr` | har sessiya, 1 so'rov (hamma symbol) |
| Binance | `/fapi/v1/premiumIndex` | har sessiya, 1 so'rov (hamma symbol) |
| Binance | `/fapi/v1/fundingInfo` | har sessiya, 1 so'rov |
| Binance | `/futures/data/openInterestHist` | pooldagi har coin, 1h, 9 nuqta |
| Binance | `/futures/data/globalLongShortAccountRatio` | pooldagi har coin, 1h, 1 nuqta |
| Binance | `/fapi/v1/klines` 1d | kuniga 1 marta, hamma symbol (30k o'rtacha) |
| Binance | `/fapi/v1/klines` 1h / 4h | calibration, 24s va 7k keyin |
| CoinGecko | `/coins/markets?symbols=...` | elakdan o'tganlar, 1 so'rov |
| DefiLlama | `/emissions` (`UnlockManba`) | har sessiya, 1 so'rov |

- Har manbaning holati (ok / xato kodi) sessiyaga yoziladi va
  sahifada ko'rinadi. **451** — server mintaqasi Binance tomonidan
  cheklangan degani; sahifa buni ochiq yozadi.
- CoinGecko narxi Binance narxidan 25% dan ko'p farq qilsa, topilgan
  coin boshqa loyiha deb hisoblanadi va ishlatilmaydi.

## 13. Sozlamalar va yashirish

- Standart qiymatlar: `config/default.yaml` → `radar:` bo'limi.
- Admin sahifada istalgan chegarani o'zgartira oladi (kodga tegmasdan)
  — `radar_sozlamalar` jadvaliga yoziladi va keyingi sessiyadan
  ishlaydi. "Standartga qaytarish" ham bor.
- Har sessiya o'zi ishlatgan chegaralarni (`sozlama_json`) saqlaydi —
  keyin "qaysi raqam bilan hisoblangan" degan savolga javob bor.
- **Coinni yashirish:** admin shovqinli coinni vaqtincha (sanagacha)
  yoki doimiy yashira oladi. Yashirilgan coin o'ringa kirmaydi, lekin
  tekshiriladi va calibration'ga yoziladi.

## 14. Keyingi versiyalar

- **4.0.1:** Order book likvidligi — 8-tekshiruv (±1% dagi pul).
- **Keyinroq:** sektor birga harakatlanmoqda bayrog'i (toifa manbai
  80 talikdan keng bo'lishi kerak), logotip.
- Calibration natijasiga qarab: elakka "yoki OI keskin o'sgan" sharti,
  chegaralarni to'g'rilash.

---

## 15. Texnik shartnoma

### Kod joylashuvi

```
core/portlash_radari/        modul (core qavati 5, watch_panel bilan teng)
  belgi.py                   symbol -> asl belgi, stablecoin
  vaqt.py                    sessiya jadvali, kun, tartib (sof)
  tekshiruvlar.py            7 tekshiruv, sanoq (sof)
  tartib.py                  elak, o'rin, holat, ketma-ket (sof)
  halol.py                   reestr holati (sof + o'qish)
  manba.py                   Binance Futures + CoinGecko mijozlari
  repository.py              radar_* jadvallari
  sessiya.py                 bitta sessiya: manba -> tekshiruv -> baza
  baholash.py                calibration (24s / 7k keyin)
  ishchi.py                  asyncio sikli
  __main__.py                alohida jarayon: python -m core.portlash_radari
web/src/lib/radar.ts         tiplar va sof yordamchilar
web/src/lib/radar-baza.ts    radar_* jadvallaridan o'qish/yozish
web/src/app/(ichki)/modul-4/ sahifa va server amallari
web/src/components/radar/    kartochka, grafik, jadval, calibration
```

### Jadvallar

**`radar_sessiyalar`** — har bir yugurish.

| Ustun | Tur | Ma'nosi |
|---|---|---|
| id | int PK | |
| turi | str(16) | `kashfiyot` \| `tasdiq` \| `qolda` |
| sham_vaqti | UTC vaqt | sessiya oldidan turgan 4h sham ochilishi |
| kun | str(10), indeks | `YYYY-MM-DD` = `sham_vaqti` ning UTC sanasi |
| tartib | int | 1..6 = `sham_vaqti.hour // 4 + 1` |
| boshlandi, tugadi | UTC vaqt | |
| holat | str(16) | `yurmoqda` \| `tugadi` \| `xato` |
| universum, darvozadan, elakdan, nomzod | int | sanoqlar |
| btc_ozgarish | float? | BTC 24s % |
| manbalar_json | text | `{"ticker": {"holat": "ok"\|"xato", "kod": 200, "izoh": ""}, ...}` |
| sozlama_json | text | ishlatilgan chegaralar |
| izoh | text | xato matni |

**`radar_natijalar`** — sessiyadagi har coin. Unikal: (sessiya_id, symbol).

| Ustun | Tur | Ma'nosi |
|---|---|---|
| sessiya_id | FK, cascade | |
| symbol | str(32) | `LSKUSDT` |
| belgi | str(32) | `LSK` |
| turi | str(16) | `elak` (pool) \| `namuna` (nazorat) \| `chiqdi` (faqat narx) |
| narx | float? | o'sha sessiyadagi narx (ticker `lastPrice`) |
| hajm_24s, hajm_nisbati, ozgarish_24s, market_cap | float? | |
| tekshiruvlar_json | text | quyidagi shakl |
| tasdiq_soni, harakat_soni, yoqilgi_soni, malumot_yoq_soni | int | |
| nomzod | bool | |
| holat | str(16) | `tasdiqlangan` \| `vaqtinchalik` \| `nomzod` \| `oddiy` |
| orin | int? | faqat `elak` va yashirilmagan |
| ketma_ket | int | ma'lumot uchun |
| yashirin, yangi_listing | bool | |
| halol | str(16) | `halol` \| `harom` \| `shubhali` \| `baholanmagan` |
| kel_24s_oxiri, kel_24s_max, kel_24s_min | float? | % (narxga nisbatan) |
| kel_24s_vaqt | UTC vaqt? | baholangan payt |
| kel_7k_oxiri, kel_7k_max, kel_7k_min, kel_7k_vaqt | | xuddi shunday, 7 kun |

`tekshiruvlar_json` elementi:

```json
{"kod": "hajm", "guruh": "harakat", "holat": "ha",
 "qiymat": 8.2, "chegara": 5.0, "manba": "binance_hajm",
 "qoshimcha": {}}
```

- `holat`: `ha` | `yoq` | `malumot_yoq`
- `qiymat`: hajm — barobar; narx — 24s % (ishorali); funding — 8 soatga
  keltirilgan % (ishorali); oi — % (ishorali); long_short — long/short
  nisbati; btc — coin − BTC punkt (ishorali); taminot — aylanma %.
- `qoshimcha`: funding → `{"oraliq_soat", "xom_pct"}`; oi → `{"soat"}`;
  taminot → `{"aylanma_pct", "unlock_kun", "unlock_pct"}`;
  hajm → `{"kunlar"}`.

**`radar_hajm`** — 30 kunlik o'rtacha kesh: symbol (unikal),
ortacha_30k, kunlar, yangilangan.

**`radar_sozlamalar`** — admin o'zgartirgan chegaralar: kalit (unikal),
qiymat, ozgartirdi (Telegram ID).

**`radar_yashirin`** — yashirilgan coinlar: symbol (unikal), sabab,
gacha (bo'sh — doimiy), qoshdi.

**`radar_holati`** — bitta qator (id=1): sorov (qo'lda tekshiruv
so'raldi), ishchi_tirik (yurak urishi), hajm_yangilandi,
baholash_oxirgi, oxirgi_xato.

### Sozlanadigan kalitlar (`radar:` va `radar_sozlamalar`)

| Kalit | Standart | Oraliq |
|---|---|---|
| min_kapitalizatsiya_usd | 10 000 000 | 0 .. 10¹¹ |
| min_hajm_24s_usd | 500 000 | 0 .. 10¹¹ |
| elak_hajm_x | 3 | 1 .. 100 |
| yangi_listing_kun | 30 | 0 .. 365 |
| hajm_x | 5 | 1 .. 100 |
| narx_ozgarish_pct | 20 | 1 .. 1000 |
| funding_8s_pct | 0.1 | 0.001 .. 10 |
| oi_osish_pct | 30 | 1 .. 1000 |
| long_short_nisbat | 2.5 | 1 .. 100 |
| btc_farq_pp | 15 | 1 .. 1000 |
| aylanma_max_pct | 60 | 1 .. 100 |
| unlock_kun | 7 | 1 .. 180 |
| unlock_min_pct | 5 | 0.01 .. 100 |
| nomzod_min | 4 | 1 .. 7 |
| top_n | 10 | 3 .. 30 |
| namuna_soni | 10 | 0 .. 50 |
| portlash_24s_pct | 20 | 1 .. 1000 |
| portlash_7k_pct | 50 | 1 .. 1000 |
