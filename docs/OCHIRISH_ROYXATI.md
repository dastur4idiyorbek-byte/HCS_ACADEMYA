# Eski tahlil moduli — o'chirish ro'yxati (BAJARILDI 2026-09-03)

Bu hujjat 1-prompt bo'yicha tuzildi va **to'liq bajarildi**. Loyiha egasi
G-bo'limdagi to'rttasini ham o'chirishga qaror qildi.

Yakuniy holat: Python 505 test o'tadi, ruff toza, sayt `next build` o'tadi,
saytda 163 test o'tadi. Bot va sayt ishga tushadi.

---

## A. O'CHIRILADI — kod

| Yo'l | Qator | Nima |
|---|---|---|
| `core/analysis/scoring/` | 1525 | 100 balllik tizim, `scorer.py`, `factors.py`, `levels.py`, `bonuses.py`, `setup_route.py` |
| `core/analysis/strategies/` | 1583 | `classic_ta`, `correction_entry`, `narx_harakati_strategiya`, `opening_range_scalp`, `registry`, `base` |
| `core/analysis/support_resistance/` | 849 | `detector`, `pivots`, `fibonacci`, `liquidity`, `range_position` (Discount/Premium shu yerda) |
| `core/analysis/market_health/` | 755 | eski formula: `calculator`, `factors`, `breadth`, `quarterly`, `inputs` |
| `core/analysis/smc/` | 383 | `zones.py` — eski ball uchun OB/FVG |
| `core/analysis/market_structure.py` | ~380 | HH/HL/LH/LL, BOS/CHOCH |
| `core/analysis/regime.py` | ~150 | rejim (o'lchandi, RAD ETILDI — #11) |
| `core/analysis/narx_harakati.py` | ~330 | kitob usuli (RAD ETILDI — #12) |
| `core/analysis/entry_order.py`, `level_types.py` | ~250 | eski kirish/daraja turi |
| `core/pipeline/` | 941 | `cycle.py` — eski ikki qatlamli sikl, `context`, `monitor`, `events` |
| **JAMI** | **~7 100** | |

### Qisman o'chiriladi

| Yo'l | Nima ketadi | Nima qoladi |
|---|---|---|
| `core/risk_engine/` (966) | `MarketHealthRule`, `TradeRulesRule` (eski R/R + stop%), `ZoneIntegrityRule`, `VolatilityRule`, `BtcMarketRule`, `btc_filter.py` | `KillSwitchRule`, `FridayPrayerRule`, `DailyLossLimitRule`, `MaxOpenSignalsRule`, `CorrelationRule`, `ConsecutiveLossRule`, `FreshDataRule`, `HalalRule` — sof xavfsizlik |
| `core/position_sizing/` (482) | eski R/R formulasiga bog'liq joy (`sizer.py` ichida) | `budget.py`, `aggregate.py` — balans/risk byudjeti |
| `core/backtest/` (1278) | eski strategiya konfiguratsiyalari (`scripts/backtest.py` variantlari) | freymvork: `dataset`, `warmup`, `report`, `engine` skeleti |

---

## B. O'CHIRILADI — admin panel

**Bot (`bot/handlers/admin.py`, 917 qator):**
- `smc_settings` (855-qator) + `_smc_matni` — SMC/LIT sozlamalari
- `market_health_dashboard` (581) + `_render_health` — eski formula ko'rsatkichi
- ball chegarasi va eski Risk Engine parametrlarini sozlash bo'limlari

**Sayt (`web/src/app/(ichki)/admin/`):**
- `admin/page.tsx` — eski salomatlik/ball bo'limlari
- `admin/jonli/page.tsx` + `JonliOshxona.tsx` + `lib/oshxona.ts` — bosqich nomlari uziladi (UI qoladi)
- `admin/hisobot/page.tsx` — eski voronka hisoboti

---

## C. UZILADI — mijoz ko'radigan joy (UI qoladi, ma'lumot manbai uziladi)

| Joy | Holat |
|---|---|
| `web/src/lib/bosqichlar.ts` — eski 28 bosqich nomi | o'chiriladi |
| `salomatlik/page.tsx` — voronka | "tez orada yangilanadi" |
| `signallar/` sahifalari | "hozircha mavjud emas" |
| `sokinlik/page.tsx` ("Nega signal yo'q?") | "yangilanmoqda" |
| Bot: "Nega bu signal?" eski 25-20-15-15-10-15 matni | o'chiriladi |
| `bot/services/runner.py`, `scheduler.py` — avtomatik sikl | to'xtatiladi |

---

## D. KONFIGURATSIYA

`config/default.yaml` dan o'chiriladi (~290 qator):
`analysis:`, `scoring:`, `trade_rules:`, `strategies:`, `market_health:`
va `risk_engine:` ning tahlilga bog'liq bandlari.

---

## E. TESTLAR

Hozir **1 562 test** o'tadi. Eski modulga bog'liq **~45 fayl** o'chiriladi
(`tests/core/` dagi 61 fayldan). Qoladigan testlar: to'lov, obuna,
halol skrining, storage, market_data, position_sizing byudjeti.

---

## F. SAQLANADI (tegilmaydi)

✅ Trading kalkulyator · TradingView widget · halol skrining (uch manbali)
✅ Bot infratuzilmasi (obuna, to'lov, rollar, Telegram Login, sessiya)
✅ Sayt tuzilmasi, menyu, dizayn, Bosh sahifa
✅ `core/market_data/`, `core/storage/`, `core/domain/`, `core/config/`
✅ Backtest freymvorki · Signal Xotirasi infratuzilmasi
✅ `docs/OLCHOVLAR_XULOSASI.md`, `GIPOTEZA_DAFTARI.md`, `BACKTEST_NATIJA_*.md`

---

## G. PROMPTDA AYTILMAGAN — QAROR: TO'RTTASI HAM O'CHIRILDI

Men to'rttasini saqlashni tavsiya qilgan edim; loyiha egasi hammasini
o'chirishni tanladi. Sabab tushunarli: `core/analysis` butunlay bo'shab,
yangi modul toza joyda quriladi.

Faqat IKKI narsa ko'chirildi (o'chirilmadi), chunki ular signalni QO'LDA
kiritishga kerak va u qoladigan xususiyat:

| Nima | Qayerdan | Qayerga |
|---|---|---|
| `decide_entry_plan()` | `core/analysis/entry_order.py` | `core/services/kirish_rejasi.py` |
| sham yuklash + kesh | `scripts/backtest.py` | `core/backtest/yuklash.py` |

Ikkalasi ham ball tizimiga hech qachon bog'liq bo'lmagan: birinchisi
ikkita narxni solishtiradi, ikkinchisi Binance'dan sham yuklaydi.

### Quyidagilar o'chirildi (avvalgi tavsiyam)

1. **`core/analysis/bozor_korinishi.py` (236 qator)** — saytdagi haftalik/
   kunlik bozor ko'rinishi (BTC.D, USDT.D, TOTAL2...). 4 soatlik signal
   siklidan MUSTAQIL, o'lchovda qatnashmagan. **Tavsiyam: QOLSIN.**

2. **`core/analysis/postmortem/` (434 qator)** — Signal Xotirasi mantig'i.
   Prompt "infratuzilma qoladi" deydi, lekin u `core/analysis` ichida.
   **Tavsiyam: QOLSIN** (`core/postmortem/` ga ko'chiriladi).

3. **`core/analysis/indicators/` (684 qator)** — EMA/RSI/MACD/ATR sof
   matematikasi. Ball bilan bog'lanish `scoring/` da, bu yerda emas.
   **Tavsiyam: QOLSIN** — yangi modul ham shu formulalardan foydalanadi,
   qayta yozish yangi xato keltiradi.

4. **`core/signals/tracker.py` (533 qator)** — TP/Stop kuzatuvi. Ballga
   bog'liq yagona joy: "ball pasaydi -> zaiflashmoqda" xabari.
   **Tavsiyam: QOLSIN**, o'sha bitta tarmoq olib tashlanadi.

---

## H. YAKUNIY HOLAT — nima ishlaydi, nima yo'q

### Ishlaydi

- Bot ishga tushadi: obuna, to'lov, admin/foydalanuvchi rollari, kontent
- Signal QO'LDA kiritiladi va obunachilarga tarqatiladi (kirish rejasi bilan)
- Veb-panelda yaratilgan signal botga chiqadi (`web-signals` vazifasi)
- Halol skrining, Telegram Login, sessiya, portfel, kalkulyator, TradingView
- Sayt to'liq quriladi va ishlaydi

### Vaqtincha yo'q ("yangilanmoqda" holatida)

| Joy | Sabab |
|---|---|
| Avtomatik signal sikli | `core/pipeline` o'chirildi |
| TP/Stop avtomatik kuzatuvi | `core/signals/tracker.py` o'chirildi |
| Bozor Salomatligi sahifasi | eski indeks formulasi o'chirildi |
| "Nega signal yo'q" voronkasi | eski bosqich nomlari o'chirildi |
| Bozor ko'rinishi sahifasi | postni quruvchi xizmat o'chirildi |
| Haftalik postmortem hisoboti | `core/analysis/postmortem` o'chirildi |
| Bot `/panel` da 4 ta bo'lim | yuqoridagi to'rttasiga bog'liq edi |
| Jonli Oshxona monitori | UI qoldi, `pipeline_events` ga yozuvchi yo'q |

### Risk Engine — 13 dan 8 ta qoida qoldi

    QOLDI   kill_switch, friday_prayer, consecutive_loss, daily_loss_limit,
            max_open_signals, correlation, fresh_data, halal
    KETDI   market_health, trade_rules, zone_integrity, volatility, btc_market

Ketganlarining hammasi eski tahlil natijasiga (ball, indeks, zona,
ATR) tayanardi. Qolganlari signal QANDAY tug'ilganidan qat'i nazar
ishlaydi — shuning uchun yangi modul kelganda ular o'zgarmaydi.

### Raqamlar

    Kod           −8 700 qator (core/analysis 7 538 + pipeline 941 + signals 533,
                  minus ko'chirilgan ~300)
    Konfiguratsiya  −693 qator (883 -> 201), 18 blokdan 11 tasi qoldi
    Test          1 562 -> 505 (Python), 165 -> 163 (sayt)

Test soni keskin kamaydi, chunki testlarning uchdan ikkisi aynan
o'chirilgan modulni tekshirardi. Qolganlari — to'lov, obuna, halol
skrining, storage, pozitsiya hajmi — hammasi o'tadi.
