# Eski tahlil moduli — o'chirish ro'yxati (TASDIQLASH KUTILMOQDA)

Bu hujjat 1-prompt bo'yicha tuzildi. **Hech narsa hali o'chirilmadi.**
Tasdiqlangandan keyin bajariladi.

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

## G. PROMPTDA AYTILMAGAN — QAROR KERAK

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
