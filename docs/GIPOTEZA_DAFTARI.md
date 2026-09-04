# Gipoteza daftari

Tizimda uch xil raqam yonma-yon yashaydi va ular **bir xil ko'rinadi**:

| Tur | Misol | Qanday o'zgaradi |
|---|---|---|
| **FAKT** | Binance komissiyasi 0.1% | birja e'lon qiladi |
| **QOIDA** | Stop 1–8% oralig'ida | loyiha egasi qaror qiladi |
| **GIPOTEZA** | Confluence vazni 40 ball | **faqat backtest hal qiladi** |

Uchalasi ham `config/default.yaml` da bir xil yotibdi. Shuning uchun
gipoteza jimgina "haqiqat"ga aylanib qoladi.

Bu daftar shuni to'xtatadi.

**Qoida:** yangi raqam qo'shilsa, u avval shu yerga **GIPOTEZA** deb
yoziladi. O'lchangandan keyingina holati o'zgaradi.
`tests/test_gipoteza_daftari.py` buni majburiy qiladi.

---

## Holatlar

| Belgi | Ma'nosi |
|---|---|
| 🔴 | o'lchanmagan — taxmin |
| 🟡 | o'lchandi, natija aniq emas |
| 🟢 | **gipoteza emas** — fakt yoki ataylab qabul qilingan qoida |
| ⚫ | o'lchandi, **rad etildi** |

---

## Hisob

    o'lchanmagan  (🔴)   124
    aniq emas     (🟡)     9
    gipoteza emas (🟢)     9
    rad etilgan   (⚫)     6
    -------------------------
    jami                 147

**130 ta raqam hech kim tomonidan tekshirilmagan.**

Bu ro'yxatning maqsadi ularni darhol o'lchash emas — bu bir necha
yillik ish. Maqsadi: **ular taxmin ekanini ko'rinib turishi**.

Dastlabki hisobda 26 ta deb yozgan edim. Ro'yxat mashinada tuzilgach
raqam besh baravar katta chiqdi — qo'lda sanashning o'zi ham taxmin
ekan.

---

## Rad etilganlar

Bular yopiq. Qayta ochish uchun YANGI dalil kerak.

| Gipoteza | Nima deb o'ylangan | Natija |
|---|---|---|
| ⚫ `correction_entry.enabled` | Past bandda tuzilmaviy kirish yordam beradi | 4 ta signal qo'shdi, natija yomonlashdi (−276.9% → −293.7%) |
| ⚫ `tp2_from_structure` | TP2 haqiqiy zonada bo'lsa unga yetish ehtimoli oshadi | Ehtimol **pasaydi**: 29.9% → 24.7% |
| ⚫ `require_htf_alignment` | Kunlik trend majburiy bo'lsa sifat oshadi | Win-rate 37.9% → 37.8% |
| ⚫ `require_confirmation` | Indikator tasdig'i soxta kirishlarni kamaytiradi | Win-rate 37.9% → 37.3% |
| ⚫ `adx_trend_threshold: 25` | Faqat kuchli trendda kirish sifatni oshiradi | Win-rate 37.9% → 37.5% |
| ⚫ `entry_max_range_pct: 40` | Chuqurroq Discount = yaxshiroq kirish | Win-rate 37.9% → 38.0% |

**Umumiy naqsh:** oltitasi ham **sozlama darajasida** edi. Hech biri
ishlamadi. Muammo sozlamada emas.

> **Raqamlar haqida eslatma.** Yuqoridagi win-rate lar run #7 da,
> ya'ni o'lchov hali buzuq bo'lgan paytda olingan. To'g'ri o'lchov
> — **run #9** (`BACKTEST_NATIJA_2026-09-02_6.md`): bazaviy
> win-rate **37.3%**, TP2 gacha **30.0%**, bitta savdo **−0.75%**.
> Filtrlar yangi o'lchovda ham qimirlamadi (36.9–39.1%), ya'ni
> **oltita rad etish kuchida qoladi**.

---

## Tarixdan: yozilmagan taxmin nima qiladi

| Raqam | Nima bo'lgan |
|---|---|
| BTC Dominance vazni | Katta vazn berilgan, o'lchanmagan. Indeksni buzgan (33-bo'lim) |
| Kill Zone bonusi | E'lon qilingan, **ulanmagan** — ballga umuman qo'shilmasdi |
| Correction Entry R/R | Sozlamada 2.0, Risk Engine'da 3.0. Signal jimgina o'lardi (67-bo'lim) |
| EMA200 talabi | 200 sham = haftalikda 3.8 yil. Ko'p altcoin chetlab o'tilardi (58-bo'lim) |
| ADX qaysi qatordan | Jonli haftalik, backtest 4 soatlik — to'rt oy ko'rinmagan (77-bo'lim) |

Beshtasi ham **mulohaza bilan** qabul qilingan, **o'lchov bilan**
emas.

---

## To'liq ro'yxat

Bo'limlar `config/default.yaml` tartibida. Izohsiz qator — hech kim
tekshirmagan degani.

### Tahlil — zona, indikator, struktura — `analysis`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `candles_lookback` | 500 |  |
| ⚫ | `require_htf_alignment` | yo'q | win-rate qimirlamadi (natija #3) |
| 🔴 | `entry_order.market_threshold_pct` | 0.15 |  |
| 🔴 | `entry_order.zone_broken_threshold_pct` | 0.3 |  |
| 🔴 | `support_resistance.swing_lookback` | 5 |  |
| 🔴 | `support_resistance.zone_merge_atr_mult` | 0.5 |  |
| 🔴 | `support_resistance.min_touches` | 2 |  |
| 🔴 | `support_resistance.proximity_atr_mult` | 1 |  |
| ⚫ | `support_resistance.entry_max_range_pct` | 55 | win-rate qimirlamadi (natija #3) |
| 🟢 | `indicators.min_candles` | 60 | QOIDA — MACD uchun eng kam tarix |
| 🔴 | `indicators.rsi_period` | 14 |  |
| 🔴 | `indicators.rsi_oversold` | 30 |  |
| 🔴 | `indicators.rsi_overbought` | 70 |  |
| 🔴 | `indicators.macd_fast` | 12 |  |
| 🔴 | `indicators.macd_slow` | 26 |  |
| 🔴 | `indicators.macd_signal` | 9 |  |
| 🔴 | `indicators.volume_ma_period` | 20 |  |
| 🔴 | `indicators.atr_period` | 14 |  |
| 🔴 | `indicators.adx_period` | 14 |  |
| ⚫ | `indicators.adx_trend_threshold` | 20 | win-rate qimirlamadi (natija #3) |
| 🔴 | `indicators.min_confirmations` | 2 |  |
| ⚫ | `indicators.require_confirmation` | yo'q | win-rate qimirlamadi (natija #3) |
| 🔴 | `require_structure_alignment` | yo'q |  |
| 🔴 | `market_structure.swing_lookback` | 5 |  |
| 🔴 | `market_structure.min_swings` | 4 |  |
| 🔴 | `market_structure.fallback_min_pct` | 1 |  |
| 🔴 | `liquidity_sweep.enabled` | ha |  |
| 🔴 | `liquidity_sweep.lookback_bars` | 30 |  |
| 🔴 | `liquidity_sweep.min_sweep_pct` | 0.3 |  |
| 🔴 | `liquidity_sweep.max_reclaim_bars` | 3 |  |
| 🔴 | `session_overlap.enabled` | ha |  |
| 🔴 | `session_overlap.start_hour_utc` | 13 |  |
| 🔴 | `session_overlap.end_hour_utc` | 16 |  |

### Backtest xarajatlari — `backtest`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟢 | `fee_pct` | 0.1 | FAKT — Binance spot taker tarifi |
| 🔴 | `slippage_pct` | 0.05 |  |

### Halol skrining — `halal_screening`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟢 | `target_count` | 150 | QOIDA — tanlov doirasi |
| 🔴 | `max_scan_depth` | 500 |  |
| 🟢 | `min_daily_volume_usd` | 5e+07 | QOIDA — likvidlik chegarasi |
| 🔴 | `exclude_stablecoins` | ha |  |
| 🔴 | `refresh_interval_hours` | 12 |  |

### Loglar — `logging`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `rotate_mb` | 20 |  |
| 🔴 | `backups` | 5 |  |

### Bozor ma'lumoti — `market_data`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `stale_price_seconds` | 90 |  |
| 🔴 | `max_concurrent_candle_requests` | 8 |  |
| 🔴 | `candle_page_pause_seconds` | 0.25 |  |

### Bozor Salomatligi Indeksi — `market_health`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `strong_trend_adx` | 30 |  |
| 🔴 | `weights.halal_structure_breadth` | 45 |  |
| 🔴 | `weights.volatility_regime` | 15 |  |
| 🔴 | `weights.aggregate_user_capacity` | 20 |  |
| 🔴 | `weights.signal_saturation` | 10 |  |
| 🔴 | `weights.btc_dominance_stability` | 5 |  |
| 🔴 | `weights.quarterly_phase` | 5 |  |
| 🔴 | `recompute_on_candle_close` | ha |  |
| 🔴 | `daily_preview_utc_hour` | 0 |  |
| 🔴 | `btc_dominance.stable_change_pct` | 0.5 |  |
| 🔴 | `btc_dominance.sharp_change_pct` | 2 |  |

### Kuzatuv — `monitoring`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `pipeline_events.enabled` | ha |  |
| 🔴 | `pipeline_events.retention_hours` | 6 |  |

### Shaxsiy portfel — `portfolio`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `tp1_close_pct` | 50 |  |
| 🔴 | `min_position_usd` | 1 |  |

### Pozitsiya hajmi — `position_sizing`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `sequential_decay_fraction` | 0.34 |  |
| 🔴 | `equal_split_expected_slots` | 3 |  |
| 🔴 | `min_allocation_usd` | 1 |  |
| 🔴 | `max_position_pct_of_balance` | 100 |  |
| 🔴 | `aggregate.capacity_used_threshold` | 0.8 |  |
| 🔴 | `aggregate.active_user_days` | 7 |  |

### Signal Xotirasi — `postmortem`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟢 | `min_sample_size` | 12 | QOIDA — kichik namunadan xulosa yo'q |
| 🔴 | `min_effect_pct` | 15 |  |
| 🔴 | `lookback_days` | 30 |  |
| 🔴 | `report_weekday` | 0 |  |
| 🔴 | `report_hour_utc` | 6 |  |
| 🔴 | `false_signal_window_minutes` | 60 |  |

### Risk Engine — `risk_engine`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `daily_loss_limit_pct` | 3 |  |
| 🔴 | `weekly_loss_limit_pct` | 8 |  |
| 🔴 | `max_open_signals` | 5 |  |
| 🔴 | `max_open_signals_by_health.high` | 5 |  |
| 🔴 | `max_open_signals_by_health.mid` | 3 |  |
| 🔴 | `max_open_signals_by_health.low` | 0 |  |
| 🔴 | `max_signals_per_correlation_group` | 1 |  |
| 🔴 | `btc_filter.max_drop_pct_24h` | -5 |  |
| 🔴 | `kill_switch.price_spike_pct` | 5 |  |
| 🔴 | `kill_switch.price_spike_window_seconds` | 60 |  |
| 🔴 | `kill_switch.requires_manual_reset` | ha |  |
| 🔴 | `consecutive_loss.max_consecutive_stops` | 5 |  |
| 🔴 | `consecutive_loss.cooldown_hours` | 24 |  |
| 🔴 | `friday_filter.enabled` | ha |  |
| 🔴 | `friday_filter.weekday` | 4 |  |
| 🔴 | `rotation.min_score_gap` | 30 |  |
| 🔴 | `rotation.cooldown_minutes` | 120 |  |
| 🔴 | `weakening.score_drop_points` | 25 |  |

### Ball tizimi — `scoring`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟡 | `weights.support_resistance` | 25 | ablation: olib tashlansa PF 0.84 → 0.80 |
| 🟡 | `weights.trend` | 20 | ablation: PF 0.84 → 0.83 — ta'sirsiz, lekin o'zgartirilmadi |
| 🟡 | `weights.rsi` | 15 | ablation: PF 0.84 → 0.83 — ta'sirsiz, lekin o'zgartirilmadi |
| 🟡 | `weights.volume` | 15 | ablation: PF 0.84 → 0.83 — ta'sirsiz, lekin o'zgartirilmadi |
| 🟡 | `weights.macd` | 10 | ablation: PF 0.84 → 0.81 — deyarli ta'sirsiz |
| 🟡 | `weights.risk_reward` | 15 | ablation: olib tashlansa PF 0.84 → 0.77 — eng katta hissa |
| 🔴 | `thresholds.health_high_min` | 65 |  |
| 🔴 | `thresholds.health_mid_min` | 40 |  |
| 🟡 | `thresholds.threshold_high_health` | 50 | kalibrlash taqsimotidan olingan |
| 🟡 | `thresholds.threshold_mid_health` | 55 | kalibrlash taqsimotidan olingan |
| 🔴 | `thresholds.threshold_low_health` | 60 |  |
| 🔴 | `bonuses.session_overlap` | 5 |  |
| 🔴 | `uplift.support_resistance` | 0.5 |  |
| 🔴 | `setup_route.enabled` | ha |  |
| 🔴 | `setup_route.max_sweep_age_bars` | 5 |  |
| 🔴 | `setup_route.require_bos` | ha |  |
| 🔴 | `setup_route.min_level_confidence` | 0.6 |  |

### Sinov davri — `sinov`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `enabled` | ha |  |
| 🔴 | `days` | 100 |  |

### Strategiyalar — `strategies`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `classic_ta.enabled` | ha |  |
| 🔴 | `classic_ta.min_risk_reward` | 1.5 |  |
| ⚫ | `correction_entry.enabled` | yo'q | past bandda yordam bermadi (natija #1) |
| 🔴 | `correction_entry.impulse_lookback` | 60 |  |
| 🔴 | `correction_entry.ob_min_move_pct` | 1 |  |
| 🔴 | `correction_entry.fvg_min_gap_pct` | 0.1 |  |
| 🔴 | `correction_entry.min_confluence` | 2 |  |
| 🔴 | `correction_entry.confirm_lookback` | 20 |  |
| 🔴 | `correction_entry.stop_buffer_pct` | 0.15 |  |
| 🔴 | `correction_entry.min_risk_reward` | 2 |  |
| 🔴 | `correction_entry.rsi_reversal_max` | 45 |  |
| 🔴 | `opening_range_scalp.enabled` | ha |  |
| 🔴 | `opening_range_scalp.range_minutes` | 15 |  |
| 🔴 | `opening_range_scalp.volume_surge_mult` | 2 |  |
| 🔴 | `opening_range_scalp.volume_ma_period` | 20 |  |
| 🔴 | `opening_range_scalp.min_move_pct` | 1 |  |
| 🔴 | `opening_range_scalp.max_move_pct` | 2 |  |
| 🔴 | `opening_range_scalp.signal_window_minutes` | 1440 |  |
| 🔴 | `opening_range_scalp.min_range_pct` | 0.15 |  |
| 🔴 | `opening_range_scalp.max_range_pct` | 1.2 |  |
| 🔴 | `opening_range_scalp.daily_risk_share_pct` | 30 |  |
| 🔴 | `opening_range_scalp.weights.volume_surge` | 35 |  |
| 🔴 | `opening_range_scalp.weights.range_quality` | 25 |  |
| 🔴 | `opening_range_scalp.weights.direction_clarity` | 25 |  |
| 🔴 | `opening_range_scalp.weights.risk_reward` | 15 |  |

### Obuna — `subscriptions`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `periods.daily` | 1 |  |
| 🔴 | `periods.monthly` | 30 |  |

### Savdo qoidalari — `trade_rules`

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `stop_atr_mult` | 1.75 |  |
| 🟢 | `min_stop_distance_pct` | 1 | QOIDA — kapital himoyasi |
| 🟢 | `max_stop_distance_pct` | 8 | QOIDA — pozitsiya kichrayib ketmasin |
| 🟢 | `min_tp_distance_pct` | 3 | QOIDA — 3.3-band |
| 🟢 | `max_tp_distance_pct` | 20 | QOIDA — 3.3-band |
| 🔴 | `min_risk_reward` | 3 |  |
| 🔴 | `tp1_min_risk_reward` | 1.5 |  |
| 🔴 | `late_entry_warn_pct` | 1.2 |  |
| 🔴 | `allow_measured_tp` | ha |  |
| ⚫ | `tp2_from_structure` | yo'q | TP2 gacha yetish pasaydi (natija #2) |
| 🔴 | `tp2_structural_min_rr` | 1 |  |

---

## Keyingi o'lchanadigan gipoteza

Oltita rad etish sozlama darajasida edi. Run #8 boshqa turkumdagi
savolni ochdi.

**🔴 Bozor Salomatligi indeksi kalibrlanganmi?**

To'g'ri (haftalik) ADX bilan indeks ikki yil davomida **26–32**
bandida qotdi va sikllarni to'xtatib turdi. Ayni davrda tayanch
**+33.0%** — ya'ni bozor ko'tarilgan.

Ikki mumkin bo'lgan ma'no bor:

1. bozor haqiqatan ikki yil "kasal" bo'lgan — bu tayanch raqamiga zid;
2. indeks ko'tarilgan bozorni "past" deb o'qiydi.

> **YOPILDI — bu gipoteza emas, o'lchov xatosi edi.** Backtest
> isinish davri salomatlik timeframeini hisobga olmasdi, ya'ni
> sinovning 54% ida haftalik struktura umuman hisoblanmasdi va
> indeksning 60 balli qismi nolda qolardi
> (`docs/ARXITEKTURA.md`, 80-bo'lim).
>
> Tuzatilgach indeks TIRILDI: signal soni 389 dan 884 ga chiqdi
> (run #9). Ya'ni indeks ko'tarilgan bozorni "kasal" deb
> o'qimasdi — u umuman hisoblanmasdi.
>
> Indeks KALIBRLANGANMI degan savol hali ochiq va u 🔴 bo'lib
> qoladi. Lekin unga javob berish uchun avval o'lchov to'g'ri
> bo'lishi kerak edi.

Indeksga kiruvchi HAMMA raqam bu daftarda 🔴: omil vaznlari, ADX
chegaralari, kenglik foizlari, band chegaralari
(`low`/`normal`/`high`). Ya'ni markaziy puls to'liq o'lchanmagan
taxminlar ustida turibdi.

Bu gipotezaning oldingilardan farqi: u "signal sifati" haqida emas,
**"tizim umuman qachon savdo qiladi"** haqida.

---

## Ball shifti — yangi 🔴

Run #9 voronkasi ikki yillik taqsimotni ko'rsatdi:

```
Chegaraga yetmagan nomzodlar: 7 584 ta
  eng yuqori ball: 55.0  |  o'rtacha: 44.3
```

22 mingdan ortiq nomzod ichida **eng yuqori ball aynan 55.0** —
chegaraning o'zi. Undan yuqorisi umuman chiqmagan.

Ya'ni `scoring.thresholds` "moslashuvchi" deb atalgan, lekin
yashil (55) va sariq (50) rejim orasidagi farq taqsimotning eng
tepasidagi tor tasma. Ball SIFAT haqida gapirmaydi, faqat
TARTIB beradi.

Bu ikki savolni ochadi va ikkalasi ham o'lchanmagan:

| 🔴 | savol |
|---|---|
| `scoring.weights.*` | omillar shunday vaznlanishi kerakmi — yoki shift shundan |
| `scoring.thresholds.*` | 55/50 taqsimotdan olingan, lekin NATIJA bilan bog'lab tekshirilmagan |

---

## Sifat darvozasi — yangi 🔴 (2026-09-02)

`scoring.quality_gate` — retseptning 3-qadami, "ball faqat
tartiblaydi".

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `quality_gate.enabled` | yo'q | GIPOTEZA — hali o'lchanmagan |
| 🔴 | `quality_gate.require_setup_contract` | ha | shartnoma majburiymi |
| 🔴 | `quality_gate.min_base_score` | 35 | XAVFSIZLIK poli, sifat chegarasi emas |

**Gipoteza:** ball nomzodlarni bir-biriga NISBATAN o'lchaydi — u
"eng yaxshisi qaysi" deydi, "shu yetarlimi" demaydi. Shuning uchun
tizim uyumning eng yuqorisini oladi, uyumning o'zi yomon bo'lsa
ham. Kirishga DALIL (CryptoSpot3% shartnomasi) ruxsat bersa,
win-rate ko'tarilishi kerak.

**Kutilayotgan narx:** signal soni keskin kamayadi. Shartnoma
uchta shartni birgalikda talab qiladi (yo'nalish + yalash +
daraja turi), va har biri alohida ham kam uchraydi.

**Nima rad etardi:** signal kamayadi-yu, win-rate qimirlamaydi.
U holda shartnoma ham yaxshi savdoni yomonidan ajrata olmaydi —
ya'ni oldingi oltita gipoteza bilan bir taqdirni bo'lishadi.

**Diqqat — bu oldingi rad etishlar bilan bir xil emas.** Ular
sozlamani o'zgartirardi (chegara, filtr, TP joyi). Bu esa QAROR
KIMDA ekanini o'zgartiradi.

---

## TP soni va foiz oraliqlari (2026-09-02)

Loyiha egasining ikkita qarori. Bular GIPOTEZA emas — QOIDA, ya'ni
o'lchov emas, tanlov. Lekin ularning oqibati o'lchanadi.

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟢 | `enforce_distance_bands` | yo'q | QOIDA — "TP STOP FOIZLARI MAJBURIY EMAS, RISK 1/3" |
| 🔴 | `max_take_profits` | 2 | nechtagacha TP — YUQORI chegara, majburiy son emas |
| 🟢 | `tp_close_shares` | jadval | QOIDA — TP soniga qarab ulush |

**Foiz oraliqlari.** `min/max_stop_distance_pct` va
`min/max_tp_distance_pct` endi to'smaydi. Bog'lovchi shart bitta —
`min_risk_reward` (1:3). Oraliqlar sozlamada qoladi va
`enforce_distance_bands` bilan qayta yoqilishi mumkin.

**Nima yo'qoladi.** `min_stop_distance_pct` himoya vazifasini ham
bajarardi: juda tor Stop bozor shovqinida bekorga ishlaydi. Bu
himoya endi `stop_atr_mult` ga qoladi — Stop ATR ning ko'paytmasi
bilan qo'yiladi, ya'ni shovqin o'z birligida o'lchanadi. Bu qat'iy
foizdan to'g'riroq, lekin **o'lchanmagan**.

**TP soni.** `max_take_profits` — yuqori chegara. Bozorda nechta
haqiqiy nishon bo'lsa, shuncha TP quriladi:

- 1 ta — toza ko'tarilish, ustda qarshilik yo'q
- 2 ta — odatiy holat (standart)
- 3 ta — TP1 va yakuniy nishon orasida yana bir zona bo'lsa

Uchinchi TP **o'ylab topilmaydi**: oraliqda haqiqiy zona bo'lmasa,
ikkitasi qoladi.

---

## Nomzodga MUDDAT — yangi 🔴 (2026-09-02)

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `max_holding_hours` | 0 | GIPOTEZA — 0 degani muddat yo'q |

**Muammo.** Chiqish qoidasi faqat ikkita: TP yoki Stop. Ya'ni
tizim jimgina shunday deb turibdi: *"bozor qachon bo'lmasin, bir
kun bularning biriga boradi"*. Uchinchi yo'l — narx o'rtada
osilib qolishi — hisobga olinmagan.

Sanoat naqshida (QuantConnect LEAN) Alpha `Insight` chiqaradi:
yo'nalish, ishonch va **muddat**. Bizda uchinchisi yo'q.

**O'lchov.** O'rtacha ushlash **45.2 soat**, bozor esa ikki yilda
**+31.5%** o'sgan (natija #6). Kapital foydasiz pozitsiyalarda
band turadi va o'sha vaqtda tizim boshqa hech narsa qila olmaydi —
ochiq signal limiti to'lgan bo'ladi.

**Nima rad etardi:** muddat yoqilganda o'rtacha natija
yomonlashsa. U holda muddat foydasiz savdolarni emas, kuchayishga
ULGURMAGAN yaxshi savdolarni kesayotgan bo'ladi.

Ikkita qiymat sinaladi — 24 va 72 soat. Bitta raqam "qisqa
yaxshimi yoki uzun" degan savolga javob bermaydi.

**Yangi holat:** `SignalStatus.TIMED_OUT` (⏱). U `CANCELLED` dan
farq qiladi va bu farq muhim: bekor qilingan signal umuman
ochilmagan, muddati tugagani esa OCHILGAN va natijasi bor —
foyda ham, zarar ham bo'lishi mumkin. Ikkalasini bir turkumga
qo'yish statistikani buzardi.

---

## Run #10 dan keyin: holatlar yangilandi

| Holat | Sozlama | Natija (natija #7) |
|---|---|---|
| ⚫ | `quality_gate.enabled` | Signal 3 barobar kamaydi, TP2 gacha qimirlamadi |
| ⚫ | `quality_gate.min_base_score` | Pol 35 va 45 — ikkalasi ham bazadan yomon |
| ⚫ | `enforce_distance_bands: false` | Natijani yomonlashtirdi, sabab aniqlandi |
| 🟡 | `max_take_profits: 3` | Ta'sirsiz — oraliq zona deyarli topilmaydi |
| 🟢 | `max_take_profits: 1` | Eng yaxshi variant (PF 0.74 vs 0.30) |
| ⚫ | `max_holding_hours: 24/72` | TP2 gacha 17.1% → 9.8% |

### Bu rad etishlar oldingilaridan FARQ QILADI

Oldingi oltitasi "ishlamadi" bilan tugagan edi. Bu safar uchta
mustaqil dalil bitta sababga ishora qildi:

1. Foiz oraliqlari o'chirilganda natija yomonlashdi
2. Bitta TP (qismli sotishsiz) eng yaxshi natija berdi
3. Ikkalasining mexanizmi bir xil

> **TP1 polsiz qoldi.** Qismli sotish arzimas foydada bo'lyapti,
> breakeven stop esa qolganini nolga qaytaryapti.

### Yangi 🔴 — keyingi o'lchanadigan gipoteza

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟢 | `enforce_tp1_ratio` | yo'q | O'LCHANDI VA ISHLADI: PF 0.30 → 0.79 (natija #8) |
| 🟡 | `tp1_min_risk_reward` | 1.5 | 2.0 jami bo'yicha yaxshiroq, lekin faqat savdo kamayganidan |

> **DIQQAT — bayroq hali ham O'CHIQ.** Loyihaning o'z intizomi:
> "Yaxshi natija BOSHQA DAVRDA qayta tekshirilishi shart". Bu
> natija bitta davr, bitta coin to'plami va bitta yugurishdan
> olingan. Oltita variantdan eng yaxshisini tanlab "tasdiqlandi"
> deyish — backtestning eng keng tarqalgan xatosi.
>
> 🟢 belgisi "o'lchandi va yo'nalish to'g'ri" degani, "yoqilsin"
> degani emas.

Ilgari `tp1_min_risk_reward` faqat "qarshilik topilmadi"
tarmog'ida ishlardi. Tuzilmaviy TP1 (eng yaqin qarshilik zonasi)
unga umuman bo'ysunmasdi. Loyiha egasining qoidasiga zid emas:
bu FOIZ emas, NISBAT poli.

**Qurildi** (`enforce_tp1_ratio`): nisbat poliga yetmagan zona
o'tkazib yuboriladi va KEYINGISI qidiriladi. Hech biri yetmasa
o'lchangan TP ga qaytiladi — u allaqachon shu nisbatga
bo'ysunadi. Ya'ni pol signal SONINI kesmaydi, TP1 ni mazmunli
joyga suradi.

**Nima rad etardi:** profit factor 0.30 dan sezilarli
ko'tarilmasa. U holda tashxis noto'g'ri — muammo TP1 joyida
emas, boshqa joyda.

**Nazorat:** "foiz oraliqlari yoqilgan" varianti PF 0.64 beradi.
Nisbat poli undan YAXSHIROQ chiqishi kerak — aks holda foizni
qaytargan ma'qul edi, ya'ni tashxis yangi narsa qo'shmagan.

### Yo'l-yo'lakay: `win_rate` ta'rifi tuzatildi

Run #10 hisobotida "win-rate 64%" va "o'rtacha −1.31%" yonma-yon
turdi. Ikkalasi ham to'g'ri hisoblangan edi, lekin "g'alaba"
so'zi turkumni bildirardi:

```
eski:  is_win = outcome in {"tp2_hit", "tp1_then_stop"}
yangi: is_win = result_pct > 0
```

O'lchov o'zini o'zi tekshirmasa, u o'lchov emas, bezak.

---

## Natija #8 — SAKKIZTA URINISHDAN BIRINCHISI ISHLADI

`enforce_tp1_ratio` (natija #7 dagi tashxisdan chiqarilgan):

| | baza | nisbat poli 1.5 |
|---|---|---|
| Profit factor | 0.30 | **0.79** |
| O'rtacha savdo | −1.31% | **−0.51%** |
| TP2 gacha | 17.1% | **30.9%** |
| Maks. pasayish | 1672% | **479%** |

### Uchta nazorat varianti — nima uchun ular zarur edi

| nazorat | natija | nima aytadi |
|---|---|---|
| foiz oraliqlari yoqilgan | PF 0.64 | nisbat poli eski yo'ldan YAXSHIROQ — tashxis yangi narsa qo'shdi |
| bitta TP (qismli sotishsiz) | PF 0.74 | qismli sotish muammo emas, uning JOYI muammo edi |
| oraliq + nisbat poli | PF 0.76 | foiz oralig'i nisbat poli ustiga hech narsa qo'shmaydi |

Uchinchisi loyiha egasining qarorini raqam bilan tasdiqlaydi:
**foizlar keraksiz, nisbat yetarli.**

### Nima O'ZGARMADI

```
Profit factor:  0.82  (foydali bo'lish uchun >1.0 kerak)
Tayanch:        +31.5%,  strategiya: −322.3%
```

Tashxis to'g'ri edi va yechim ishladi, lekin **yetarli emas**.

### Yangi 🔴 — keyingi savol

| Holat | Savol |
|---|---|
| 🔴 | Bu natija BOSHQA DAVRDA ham takrorlanadimi |
| 🔴 | PF 0.82 dan 1.0 gacha qolgan masofani nima yopadi |

Birinchisiga javob berish uchun backtestga sinov OYNASINI
tanlash kerak edi — hozir u qurildi.

---

## Sinov oynasi qurildi (`--end-date`)

`docs/ARXITEKTURA.md`, 84-bo'lim. Endi ikkita KESISHMAYDIGAN
davrni alohida o'lchash mumkin:

```bash
python -m scripts.backtest --compare --days 365 --end-date 2025-09-02
python -m scripts.backtest --compare --days 365
```

Har oynaning keshi alohida (`BTC_4h_2025-09-02.json`) — aks
holda ikkinchi yugurish birinchisining shamlarini jimgina qayta
ishlatardi va "ikkita mustaqil o'lchov" aslida bitta bo'lardi.

**Qoida:** `enforce_tp1_ratio` bayrog'i faqat IKKALA oynada ham
bir yo'nalishda natija bergandagina yoqiladi. Bitta oynada
ishlab ikkinchisida ishlamasa — gipoteza rad etiladi va shu
yerga ⚫ bilan yoziladi.

---

## Natija #9 — SHART BAJARILDI, BAYROQ YOQILDI

Oyna B (2022-09 → 2024-09) o'lchandi. Oltita variantning
TARTIBI ikkala oynada ham saqlandi:

| variant | PF, oyna A | PF, oyna B |
|---|---|---|
| hozirgi holat | 0.30 | 0.34 |
| foiz oraliqlari (nazorat) | 0.64 | 0.75 |
| bitta TP (nazorat) | 0.74 | 0.87 |
| oraliq + nisbat poli | 0.76 | 0.83 |
| TP1 nisbat poli 1.5 | 0.79 | 0.93 |
| TP1 nisbat poli 2.0 | 0.82 | 1.01 |

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟢 | `enforce_tp1_ratio` | **true** | ikki oynada tasdiqlandi — YOQILDI |
| 🟡 | `tp1_min_risk_reward` | **2.0** | ikkala oynada 1.5 dan yaxshi, lekin oyna A da faqat savdo kamayganidan |

**Tizim shunda ham tayanchdan yomon** (oyna B: +15.7% vs
+150.3%). Bayroq bitta teshikni yopdi, tizimni foydali
qilmadi.

---

## Yoqishda topilgan YASHIRIN BOG'LIQLIK — yangi 🔴

Ikkita nisbat bir-biriga bog'liq ekan:

```
trade_rules.tp1_min_risk_reward         2.0   TP1 uchun POL
strategies.classic_ta.min_risk_reward   1.5   YAKUNIY nishon
```

Pol yakuniy nishondan yuqori, ya'ni polga bo'ysungan TP1 doim
yakuniy nishondan ham uzoqda. Kod buni jimgina
`tp2 = tp1 * 1.001` bilan "hal qilardi" — kartochkada TP1
130.00 va TP2 130.13.

Ya'ni **o'lchangan mexanizm aslida "yagona nishonni uzoqqa
qo'yish" edi**, "TP1 ni yaxshilash" emas. Buning izi
raqamlarda ham bor: win-rate va "TP2 gacha" deyarli teng
(34.6% va 34.3%).

Yasama nishon olib tashlandi — endi bunday holatda signal
BITTA TP bilan quriladi.

| Holat | Savol |
|---|---|
| 🔴 | Yakuniy nishon nisbati polidan yuqori bo'lsa (2.2 / 2.5 / 3.0 / 4.0) natija saqlanadimi |

---

## Natija #10 — yakuniy nishon nisbati RAD ETILDI

Nishon qanchalik uzoq bo'lsa, natija shunchalik yomon. Chiziq
to'ppa-to'g'ri pastga ketdi:

| yakuniy nishon | signal | win | PF | o'rt.% |
|---|---|---|---|---|
| **1.5 (hozirgi)** | 653 | **28.0%** | **0.83** | **−0.47** |
| 2.2 | 630 | 26.4% | 0.78 | −0.58 |
| 2.5 | 592 | 25.5% | 0.69 | −0.85 |
| 3.0 | 517 | 25.0% | 0.70 | −0.81 |
| 4.0 | 440 | 25.5% | 0.64 | −1.02 |

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| ⚫ | `classic_ta.min_risk_reward` | 1.5 | 2.2-4.0 sinaldi, hammasi yomonroq |

**Bu loyiha egasining "RISK 1/3" qoidasiga tegishli.** 3.0
varianti — aynan o'sha talab. U hozirgi holatdan yomonroq
chiqdi. Qoida o'zgartirilmadi: qaror loyiha egasiniki, bu yerda
faqat o'lchov yozilgan.

### Nima uchun uzoq nishon yordam bermaydi

Har nisbat uchun kerakli "nishonga yetish" foizi:

| nisbat | kerak | bizda |
|---|---|---|
| 1:1.5 | 40% | 28% |
| 1:3 | 25% | 19% |
| 1:4 | 20% | 15% |

Nisbat o'zgarganda kerakli foiz ham, bizning foizimiz ham
BIRGA pasayadi — farq yopilmaydi. Ya'ni muammo nisbatda emas,
**kirish tanlovida**.

---

## Yangi tuzilma (2026-09-03) — 7-to'plam

Oltita to'plam chiqish va ball haqida edi. Kirish tanlovining
o'zi hech qachon o'zgarmadi va aynan u zaif.

Loyiha egasining tashxisi tuzilmani ko'rsatdi. Uchta yangi
sozlama, uchalasi ham 🔴:

| Holat | Sozlama | Qiymat | Savol |
|---|---|---|---|
| 🔴 | `regime_rules` (`enabled`) | false | Har timeframe bitta ish qilsa natija yaxshilanadimi |
| 🔴 | `kotarilish_max_range_pct` | 55.0 | Ko'tarilishda chegara shu bo'lsinmi |
| 🔴 | `diapazon_max_range_pct` | 35.0 | Diapazonda qanchalik qattiq bo'lsin |
| 🔴 | `zone_lookback` | 0 | Zona qidiruvi 200 shamga qisqarsa yaxshilanadimi |
| 🔴 | `regime_timeframe` | "1d" | Rejim kunlikdan o'qilsinmi |

### Rejim nima qiladi

```
haftalik   ->  yo'nalish   (bu hafta nima kutamiz)
kunlik     ->  rejim       (bugun qay holatda)
4 soatlik  ->  kirish      (tahlil shu yerda)
```

Rejim BALL emas, **SHART**:

| rejim | qoida |
|---|---|
| ko'tarilish | tuzatish kutiladi (odatiy Discount) |
| diapazon | faqat TUB (chuqurroq talab) |
| pasayish | umuman olinmaydi |

**Nima uchun bu ballda mumkin emas edi.** Ballda hech kim "yo'q"
deya olmaydi: haftalik tushayotgan bo'lsa ham, boshqa beshta
omil yaxshi bo'lsa ball yetadi va signal chiqadi.

**OGOHLANTIRISH.** Shunga o'xshash narsa bir marta sinalgan —
"kunlik trend majburiy" filtri (natija #3), va u ishlamagan.
Farqi: u FILTR edi, faqat kesardi. Bu yerda har rejim uchun
BOSHQA qoida bor. Agar bu ham ishlamasa, tashxis noto'g'ri
degani va shu yerga ⚫ yoziladi.

### Skalp o'chirildi — nazorat varianti bilan

`opening_range_scalp.enabled: false`. O'lchov asos bo'ldi:
oxirgi yugurishda eng ko'p rad etish o'sha strategiyadan chiqdi
(16 473 marta hajm sharti), signal esa deyarli bermasdi.

15 daqiqalik shamda narx chorak foiz yuradi, kelib-ketish
xarajati 0.3% — harakatning o'zi xarajatdan kichik.

Backtestda "skalp yoqilgan" NAZORAT varianti bor: o'chirish
to'g'ri qaror edimi degan savolga o'sha javob beradi.

---

## NARX HARAKATI strategiyasi — 8-to'plam (2026-09-03)

Manba: loyiha egasi bergan kitob, `docs/NARX_HARAKATI_STRATEGIYALARI.md`.
To'qqizta XARID strategiyasidan oltitasi aynan bir xil uch
qadamni takrorlaydi: **daraja yoriladi → qayta sinov →
buqasimon sham**.

Bizda bu YO'Q edi. `classic_ta` narx arzon zonada bo'lsa kiradi
— qaytishni kutmaydi, tasdiq so'ramaydi.

| Holat | Sozlama | Qiymat | Savol |
|---|---|---|---|
| 🔴 | `narx_harakati` (`enabled`) | false | Tasdiqni kutish win-rate ni ko'taradimi |
| 🔴 | `qayta_sinov_oynasi` | 12 | Qaytish shuncha sham ichida bo'lsinmi |
| 🔴 | `yorish_oynasi` | 12 | Yorish shuncha sham oldin bo'lishi mumkinmi |
| 🔴 | `qayta_sinov_tolerans_atr` | 0.5 | "Darajaga tegdi" shu masofadami |
| 🔴 | `figura_oynasi` | 60 | Ikkita pastlik shu oynada qidirilsinmi |
| 🔴 | `tub_tolerans_atr` | 1.0 | Ikki tub shu masofada "bir xil daraja"mi |
| ⚪ | `tasdiq_shami_shart` | true | Bayroq — kitobning sharti |

**NIMA UCHUN FILTR EMAS, ALOHIDA STRATEGIYA.** Yettita to'plam
`classic_ta` ga filtr qo'shdi va win-rate 27-29% da qoldi. Bu
esa BOSHQA kirish mexanizmi — ikkalasi yonma-yon o'lchanadi.

**Nima rad etardi:** win-rate yana 27-29% da qolsa. U holda
tasdiqni kutish ham yordam bermaydi va muammo boshqa joyda.

---

## Natija #12 — KITOB USULI RAD ETILDI

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| ⚫ | `narx_harakati.enabled` | false | win 28.9% → 21.3%, PF 0.84 → 0.74 |
| ⚫ | `tasdiq_shami_shart` | true | tasdiqsiz variant BIROZ YAXSHIROQ (0.85 vs 0.84) |
| ⚫ | `qayta_sinov_oynasi` | 12 | 5 bilan natija AYNAN bir xil — ta'sirsiz |

### Eng muhim raqam

```
                         o'rtacha savdo
classic_ta                   −0.46%
narx harakati (kitob)        −0.46%
```

Ikkita BUTUNLAY BOSHQA kirish mexanizmi — biri arzon zonada
kiradi, ikkinchisi yorilish va qayta sinovni kutadi — va bitta
savdodagi natija AYNAN teng.

"Jami natija yaxshiroq" (−138.7 vs −277.7) aldamasin: savdo soni
ikki barobar kam. Bu naqsh loyihada oltinchi marta uchradi.

### Yangi xulosa — oldingisidan qattiqroq

Sakkizta to'plam, kirish tomonida beshta rad etish. Endi ikkita
mustaqil dalil bitta narsani aytadi:

> 4 soatlik shamlardan hisoblanadigan hech bir naqsh keyingi
> harakatni oldindan aytmayapti. Qaysi qoidani qo'ymaylik,
> o'rtacha natija bir xil chiqmoqda.

### Bitta foydali farq

Kitob usuli ancha TINCH: pasayish 451% dan 185% ga tushdi.
Foyda bermaydi, lekin kapitalni kamroq silkitadi. Bu — qaror
uchun ma'lumot, tavsiya emas.

---

## Bozor ko'rinishi (sayt) — GIPOTEZA EMAS

`bozor_korinishi` sozlamalari daftarga kirmaydi: ular bozor
haqida emas, POST VAQTI haqida. Modul signalga umuman
bog'lanmaydi va `tests/core/test_bozor_korinishi.py` buni kod
bilan qulflaydi.

---

## Natija #11 — REJIM RAD ETILDI, skalp qarori TASDIQLANDI

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟢 | `opening_range_scalp.enabled` | false | nazorat tasdiqladi: skalpsiz PF 0.84 vs 0.83 |
| ⚫ | `regime_rules.enabled` | false | PF 0.84 → 0.75, o'rtacha −0.46% → −0.75% |
| ⚫ | `diapazon_max_range_pct` | 35.0 | 25% ham yordam bermadi (PF bir xil 0.75) |
| 🟡 | `zone_lookback` | 0 | 200 sham: bitta savdoda farq 0.01 punkt — ta'sirsiz |

**Rejim 193 ta signalni (32%) kesdi va qolganlari YOMONROQ
chiqdi** — ya'ni u o'rtachadan yaxshi savdolarni olib tashladi.
Tashxis mantiqan to'g'ri ko'rinardi, ma'lumot tasdiqlamadi.

### Yangi 🔴 — haftalik struktura juda tez-tez "pasayish"

Rejim 21 000 nomzoddan **10 463 tasini** (yarmini) "haftalik
yoki kunlik pasayishda" deb rad etdi. Ayni davrda bozor **+31.5%
ko'tarilgan**.

| Holat | Savol |
|---|---|
| 🔴 | Struktura aniqlovchisi haftalik qatorda pasayishni ORTIQCHA ko'radimi |

Poydevor testi uni QO'LDA qurilgan toza zinapoyada tekshirdi va
u to'g'ri ishladi. Haqiqiy haftalik qator toza zinapoya emas —
bu tekshirilmagan.

### Win-rate yettinchi marta qimirlamadi

Oltita variant, signal soni 389 dan 653 gacha, win-rate esa
**27-29%**. Etti xil filtr sinaldi, hech biri "yaxshi" savdoni
"yomon"idan ajrata olmadi. Faqat TP1 nisbat poli natijani
o'zgartirdi, va u ham CHIQISH tomonida.
| 🔴 | Ball shifti 55.0 — ikkinchi oynada ham aynan shu ko'rindi |
| 🔴 | PF 1.0 dan yuqoriga nima ko'taradi |

---

## 2026-09-03 — ablation va walk-forward (natija #13)

`docs/BACKTEST_NATIJA_2026-09-03_3.md`

Birinchi marta ball VAZNLARI o'lchandi. Ular loyiha boshidan
"o'ylab qo'yilgan" edi va daftarda 🔴 turardi.

Sof ablation (shkala 100 qoladi, faqat omil ma'lumoti olinadi):

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟡 | `weights.support_resistance` | 25 | olib tashlansa PF 0.84 → 0.80 — ma'lumot beradi |
| 🟡 | `weights.risk_reward` | 15 | olib tashlansa PF 0.84 → 0.77 — eng katta hissa |
| 🟡 | `weights.trend` | 20 | olib tashlansa PF 0.84 → 0.83 — ta'sirsiz |
| 🟡 | `weights.rsi` | 15 | olib tashlansa PF 0.84 → 0.83 — ta'sirsiz |
| 🟡 | `weights.volume` | 15 | olib tashlansa PF 0.84 → 0.83 — ta'sirsiz |
| 🟡 | `weights.macd` | 10 | olib tashlansa PF 0.84 → 0.81 — deyarli ta'sirsiz |

**Ballning 60 punkti (trend + RSI + hajm + MACD) tartiblashga
hissa qo'shmayapti.** Ular zarar ham keltirmayapti — birortasi
olib tashlanganda natija yaxshilanmadi.

Vaznlar O'ZGARTIRILMADI: alohida-alohida ta'sirsiz bo'lish
birga ham ta'sirsiz degani emas, va bu hali o'lchanmagan.

Walk-forward (uch bo'lak, 12 nomzod, tanlov keyingi bo'lakda):

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| ⚫ | parametr qidiruvi | — | tanlov tayanchdan +0.01 va −0.00 punkt farq qildi |
| 🟡 | `entry_max_range_pct` | 55.0 | ikkala o'rgatish bo'lagida 45% tanlandi, ustunlik 0.01 punkt — o'zgartirish uchun asos emas |

### Yangi 🔴 — natija vaqt bo'yicha pasaymoqda

    1-davr (2024-08 → 2025-04)   PF 1.00   foydali 33.5%
    2-davr (2025-04 → 2025-12)   PF 0.84   foydali 29.7%
    3-davr (2025-12 → 2026-09)   PF 0.69   foydali 27.6%

| Holat | Savol |
|---|---|
| 🔴 | Uch davrdagi pasayish bozor o'zgarishimi yoki strategiya eskirishimi |
| 🔴 | To'rt ta'sirsiz omil BIR VAQTDA olib tashlansa nima bo'ladi |

---

## 2026-09-03 — audit 3-bosqichi: uchta yarim holat

Uchtasi ham gipoteza sifatida emas, NOMUVOFIQLIK sifatida topilgan:
kod bir narsa qiladi, izoh boshqasini aytadi. Har biri bayroq ostida,
standart holatda hozirgi xatti-harakat.

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🟢 | `tp1_ratio_tuzilmaviy_zonaga` | true | O'LCHANDI: o'chirilsa PF 0.84 -> 0.32. "Doim bitta TP" nuqson emas, HIMOYA |
| ⚫ | `chuqurlik_darvozadan` | false | O'LCHANDI: PF 0.84 -> 0.83, signal +1. 96 nomzod chegaradan o'tdi, lekin sig'im to'sdi |
| 🟡 | `zona_yagona_manba` | false | O'LCHANDI: farq YO'Q (bit-ma-bit bir xil). Ikki manba 21 240 baholashda hech qachon ajralmadi |

**3.1 AUDIT XULOSASINI AGDARDI.** Audit "TP doim bitta" ni nuqson
deb belgilagan edi. O'lchov teskarisini aytdi: polni tuzilmaviy
zonadan olib tashlash signalni ikki barobar ko'paytiradi (593 ->
1092) va natijani uch barobar yomonlashtiradi (−0.45% -> −1.36%).
To'liq: `docs/BACKTEST_NATIJA_2026-09-03_3.md`, 6-bo'lim.

### Yangi 🔴 — kirish narxi joriy narxga teng

`build_levels()` da `entry = zone_map.price`. Oqibatlari ikkita va
ikkalasi ham o'lik tarmoq qoldiradi:

    ZoneIntegrityRule       masofa har doim 0  ->  hech qachon ishlamaydi
    market_threshold_pct    masofa har doim 0  ->  buyurtma HAR DOIM MARKET

Ya'ni "narx zonaga qaytganda LIMIT bajariladi" degan xatti-harakat
mavjud emas.

| Holat | Savol |
|---|---|
| 🔴 | Kirish narxi joriy narxmi yoki ZONANING o'zi bo'lishi kerakmi |
| 🔴 | Past bandda `classic_ta` 60 chegarasi bilan ishlashi kerakmi |

### Voronkadan chiqqan 🔴 — yo'qotish sig'imda

`risk_engine` 4 668 nomzoddan 593 tasini o'tkazdi (12.7%), sababi
strategiya emas:

    3540 x max_open_signals
     317 x correlation

| Holat | Savol |
|---|---|
| 🔴 | `max_open_signals` (5) chegarasi eng yaxshi nomzodni tanlaydimi yoki BIRINCHI kelganini |

---

## 2026-09-03 — 9-to'plam: CHIQISH TOMONI (oxirgi yo'nalish)

### Nima uchun aynan shu

O'n besh o'lchov davomida natijani FAQAT bitta narsa qimirlatdi:
TP1 nisbat poli (PF 0.30 -> 0.84). U chiqish tomonida edi.

Kirish tomonida sakkizta g'oya sinaldi va hammasi rad etildi. Eng
aniq dalil: ikkita BUTUNLAY BOSHQA kirish mexanizmi aynan bir xil
natija berdi (−0.46%). Ya'ni "o'ntadan uchtasi to'g'ri chiqadi" ni
o'zgartirib bo'lmadi.

Uchta richag qoldi va uchalasi ham chiqish/xarajat tomonida:

| Holat | Sozlama | Qiymat | Izoh |
|---|---|---|---|
| 🔴 | `trailing_stop.enabled` | false | g'olib savdoni uzoqroq ushlash — yagona sinalmagan richag |
| 🔴 | `trailing_stop.activate_at_r` | 1.0 | surish shu foydadan keyin boshlanadi; erta surish shovqinni Stopga aylantiradi |
| 🔴 | `trailing_stop.trail_r` | 1.0 | Stop cho'qqidan shuncha R pastda ergashadi |

Ikkinchi va uchinchi richag yangi sozlama talab qilmaydi — ular
mavjud qiymatlar bilan o'lchanadi:

    kamroq savdo   scoring.thresholds  +3 punkt
    sig'im         risk_engine.max_open_signals  5 -> 3

### TO'XTASH QOIDASI — OLDINDAN YOZILADI

Bu qoida natija chiqishidan OLDIN yozildi. Sabab oddiy: natija
ko'ringach "yana bittasini sinab ko'ray" deyish oson bo'ladi va biz
buni allaqachon o'n besh marta qildik.

> **Variant PF 1.0 dan yuqori chiqsa** — u IKKINCHI, kesishmaydigan
> oynada takrorlanadi. Ikkalasida ham o'tsa, yoqiladi.
>
> **Hech bir variant PF 1.0 ga yetmasa** — foyda ortidan quvish
> TO'XTAYDI. Signal moduli bor holicha qoladi, mahsulot esa halol
> skrining, risk boshqaruvi, ochiq statistika va ta'lim yo'nalishiga
> buriladi. Ular PF 1.0 ni talab qilmaydi.

Qo'shimcha shart: PF 1.0 dan o'tgan variant kamida 100 ta savdo
bilan o'tsin. Kam savdoda PF tasodifdan farq qilmaydi.

---

## 2026-09-03 — 9-TO'PLAM NATIJASI: TO'XTASH QOIDASI ISHGA TUSHDI

Manba: Actions run 33757139027, commit `0973f86`, BTC/ETH/SOL/BNB/XRP,
730 kun (+427 kun isinish), 4,412 tahlil qadami, xarajat 0.3%/savdo.

| Variant | Signal | Win | PF | O'rt.% | Jami% | Pasayish |
|---|---|---|---|---|---|---|
| hozirgi holat | 593 | 28.8% | **0.84** | −0.45 | −269.5 | 445.1% |
| surilgan Stop 1R/1R | 926 | 15.2% | 0.36 | −2.13 | −1968.2 | 1976.2% |
| surilgan Stop 1R/0.5R | 1064 | 7.0% | 0.15 | −3.06 | −3259.0 | 3259.0% |
| surilgan Stop 2R/1R | 639 | 25.7% | 0.72 | −0.83 | −531.8 | 663.6% |
| kamroq savdo (+3) | 577 | 27.4% | 0.79 | −0.62 | −360.0 | 487.7% |
| surilgan + kamroq | 848 | 14.7% | 0.35 | −2.19 | −1860.6 | 1860.6% |
| surilgan + kamroq + sig'im 3 | 818 | 14.8% | 0.35 | −2.17 | −1775.9 | 1775.9% |

**Hech bir variant PF 1.0 ga yetmadi. Eng yaxshisi — hech narsa
o'zgartirmagan hozirgi holat (0.84).**

### Surilgan Stop nima uchun ZARAR keltirdi

Kutish: g'olib savdolar uzoqroq ushlanadi. Haqiqat: surilgan Stop
g'olib savdolarni emas, hali shakllanmagan savdolarni o'ldirdi.

Dalil — ushlash vaqti va savdo soni:

    hozirgi holat        79.7 soat ushlash, 593 savdo, 28.8% g'alaba
    surilgan 1R/1R       48.2 soat ushlash, 926 savdo, 15.2% g'alaba
    surilgan 1R/0.5R     40.5 soat ushlash, 1064 savdo,  7.0% g'alaba

Savdo qanchalik tez yopilsa, g'alaba shunchalik kam. Surish qattiqroq
bo'lsa (0.5R), natija yomonroq — bu tasodif emas, bir yo'nalishli
bog'liqlik. 4 soatlik shamda narx 1R ko'tarilib keyin 1R qaytishi
oddiy shovqin; surilgan Stop uni "chiqish signali" deb o'qidi va
savdoni TP ga yetmasdan yopdi. Ketma-ket zarar 21 tadan 88 taga
chiqdi.

Xulosa: bu strategiyada qattiq Stop — o'z-o'zini zararlash. Aynan
shu sabab TP1 poli (2-bosqichda tekshirilgan) foydali edi: u savdoga
NAFAS berardi, surilgan Stop esa nafasni bo'g'adi.

### Kamroq savdo va sig'im — sezilarli emas

`kamroq savdo (+3)`: PF 0.84 -> 0.79, savdo 593 -> 577. 16 ta savdo
kam, PF pasaydi. Chegarani ko'tarish sifatni oshirmaydi — bu
9-o'lchovda oltinchi marta tasdiqlandi.

`sig'im 3`: surilgan Stop bilan birga o'lchandi, shuning uchun toza
o'lchov emas — lekin 848 -> 818 savdoda PF 0.35 -> 0.35, ya'ni ta'sir
nolga yaqin. Sig'imni kamaytirish "yaxshiroq savdoni tanlash" degani
emas; u shunchaki birinchi kelganini kamroq oladi.

### QAROR

To'xtash qoidasi shartsiz ishga tushdi:

> Hech bir variant PF 1.0 ga yetmadi -> **foyda ortidan quvish
> TO'XTAYDI.**

Ikkinchi oynada takrorlash O'TKAZILMAYDI — qoida bo'yicha u faqat
PF > 1.0 chiqqan variant uchun edi. Yangi variant ham sinalmaydi.

Nima qoladi:
- Signal moduli bor holicha qoladi (o'chirilmaydi, "yaxshilanmaydi").
- `trailing_stop.enabled` **false** bo'lib qoladi — kod bor, lekin
  o'lchov uni yoqishga ruxsat bermadi.
- Mahsulot yo'nalishi: halol skrining, risk boshqaruvi, ochiq
  statistika, ta'lim.

### Yopilgan 🔴 lar

| Sozlama | Yangi holat | Sabab |
|---|---|---|
| `trailing_stop.enabled` | 🔒 false — qayta ochilmaydi | PF 0.84 -> 0.36 |
| `trailing_stop.activate_at_r` | 🔒 1.0 (ishlatilmaydi) | 2R ham yordam bermadi (0.72) |
| `trailing_stop.trail_r` | 🔒 1.0 (ishlatilmaydi) | 0.5R yomonroq (0.15) |

Bu uchtasi endi gipoteza emas — yopiq savol. Qayta ochish uchun
yangi dalil kerak, "bir marta yana sinab ko'ramiz" emas.


---

## 2026-09-03 — YANGI MODUL: to'rt blokli zanjir

Eski modul o'chirildi va o'rniga butunlay boshqa arxitektura
qurildi. Daftarning bu qismi NOLDAN boshlanadi: eski gipotezalar
yuqorida, tarix sifatida qoladi, lekin yangi modulga tegishli emas.

### Nima o'zgardi — bitta jumlada

    ESKI:  6 omil QO'SHILADI -> yig'indi chegara bilan solishtiriladi
    YANGI: 4 blok KETMA-KET -> biri bo'sh bo'lsa zanjir uziladi

Farqi: yig'indida bitta kuchli omil qolgan beshtasining yo'qligini
yopib ketardi. Zanjirda bunday almashtirish mumkin emas.

### 🔴 O'LCHANMAGAN — hammasi

2-promptning 3-tamoyili: "hech bir vazn taxmin qilinmaydi". Quyidagi
raqamlar KODDA bor, lekin ularning HECH BIRI o'lchanmagan. Ular —
boshlang'ich nuqta, javob emas.

| Holat | Sozlama | Qiymat | Savol |
|---|---|---|---|
| 🔴 | `zanjir.eng_kam_ishonch` | 0.0 | Qaysi ishonchdan yuqorisi signal beradi |
| 🔴 | `bloklar.funding_sovugan` | −0.0001 | Funding qachon "sovuq" |
| 🔴 | `bloklar.fng_yuqori_chegara` | 55 | F&G qaysi qiymatdan past bo'lsa xaridga qulay |
| 🔴 | `bloklar.unlock_yaqin_kun` | 7 | Unlock qachon "yaqin" |
| 🔴 | `bloklar.unlock_katta_pct` | 5.0 | Unlock qachon "katta" |
| 🔴 | `bloklar.fraktal_qanot` | 2 | 5 shamli fraktal to'g'rimi (3 yoki 7 emas) |
| 🔴 | `bloklar.nisbiy_kuch_oyna` | 20 | Coin/BTC nisbati qancha oynada o'lchansin |
| 🔴 | `bloklar.fib_yuqori/past` | 0.382/0.618 | Zona chegaralari shu bo'lsinmi |
| 🔴 | `bloklar.ob_tarifi` | last_opposite | `sweep_candle` yaxshiroqmi |
| 🔴 | `bloklar.poc_savatlar` | 50 | Volume profile aniqligi |
| 🔴 | `bloklar.poc_yaqinlik_pct` | 2.0 | Zona POC ga qanchalik yaqin bo'lsin |
| 🔴 | `bloklar.sweep_eng_kam_pct` | 0.1 | Yalash chuqurligi |
| 🔴 | `bloklar.sweep_qaytish_sham` | 3 | Necha sham ichida qaytsin |
| 🔴 | `bloklar.rsi_past_zona` | 35.0 | RSI "sotilgan" chegarasi |
| 🔴 | `bloklar.wick_farq_chegara_pct` | 1.0 | Ikki birja wicki qancha ajralsa shubhali |
| 🟢 | `darajalar.stop_eng_kam_pct` | **1.5** | O'LCHANDI: 3.0 savdolarning 6 dan 5 ini to'sardi. 0.5→PF 3.26/195 savdo, 1.5→3.17/82, 3.0→1.83/35 |
| 🔴 | `darajalar.stop_eng_kop_pct` | 15.0 | Stop qanchalik uzoq bo'lishi mumkin |
| ⚫ | `darajalar.tp1_eng_kam_nisbat` | 1.2 | O'LCHANDI: 1.0→PF 1.86, **1.2→1.83**, 1.5→2.11 (31 savdo), 2.0→1.51 (9 savdo). 1.2 qoladi — yuqorisida savdo qolmaydi |
| 🔴 | `chiqish.qoldiq_muddat_kun` | 14 | Qoldiq qancha kutsin |
| 🔴 | `chiqish.umumiy_muddat_kun` | 28 | Umumiy muddat |
| 🔴 | `nomzod.eng_kam_hajm_usd` | 50M | Likvidlik chegarasi |

### ⚫ ESKI O'LCHOVDAN KO'CHIRILGAN QARORLAR

Bular yangi tizimda QAYTA o'lchanmaydi — eski o'lchov ular haqida
aniq javob bergan va sabab yangi tizimda ham amal qiladi.

| Holat | Sozlama | Qiymat | Dalil |
|---|---|---|---|
| ⚫ | `chiqish.trailing_yoqilgan` | false | PF 0.84 → 0.36 (9-to'plam) |
| 🟢 | TP1/Stop poli mavjudligi | bor | PF 0.30 → 0.84 (natija #8, #9) |
| ⚫ | Correction Entry | qaytarilmaydi | RAD ETILGAN (natija #1) |

**Trailing haqida aniqlik.** Eski o'lchov "trailing yomon" demaydi —
u "TP1 dan OLDIN trailing yomon" deydi. Yangi tizimda u faqat TP2
dan keyingi 20% qoldiqqa tegadi va kunlik timeframeda ishlaydi.
Shuning uchun bayroq bor, lekin O'CHIQ: backtest ruxsat bermaguncha
yoqilmaydi.

### 🔴 MA'LUMOT MUAMMOSI — 1-blokning yarmi o'lchanmaydi

To'liq jadval: `docs/FUNDAMENTAL_MALUMOT_MANBALARI.md`.

    o'lchanadi     Funding Rate, Fear & Greed
    o'lchanmaydi   Open Interest (30 kun), Netflow (pullik),
                   Sektor (tarix yo'q), Yangiliklar (tarix yo'q)
    jonli-only     Token Unlock / Delisting qattiq to'sig'i

Kod bu holatni YASHIRMAYDI: manba yo'q bo'lsa tekshiruv
`MALUMOT_YOQ` qaytaradi va blok MAXRAJIDAN chiqadi. Ya'ni "2/4"
o'rniga halol "1/2" yoziladi.

### TO'XTASH QOIDASI — o'zgarmasdan saqlanadi

> Agar hech bir konfiguratsiya PF ≥ 1.0 bermasa, foyda ortidan
> quvish TO'XTAYDI, natija admin bilan muhokama qilinadi, keyingi
> qadam BIRGA hal qilinadi.

Qo'shimcha shart (eski daftardan): PF 1.0 dan o'tgan variant
kamida 100 ta savdo bilan o'tsin va IKKINCHI, kesishmaydigan
oynada takrorlansin.


---

## 2026-09-03 — ZANJIR BIRINCHI MARTA O'LCHANDI

To'liq natija: `docs/BACKTEST_NATIJA_2026-09-03_zanjir.md`.

### Nima o'lchandi

| Holat | Sozlama | Eski | Yangi | Dalil |
|---|---|---|---|---|
| 🟢 | `stop_eng_kam_pct` | 3.0 | **1.5** | 35 savdo/PF 1.83 → 82 savdo/PF 3.17 |
| ⚫ | `tp1_eng_kam_nisbat` | 1.2 | 1.2 | 1.5 va 2.0 sinaldi — savdo qolmaydi |

### 🟢 ZANJIR USTUNLIK BERDI — uchala oynada

```
stop 0.5%:   PF 3.18 → 3.07 → 2.78    (79 / 62 / 79 savdo)
stop 1.5%:   PF 3.37 → 2.90 → 2.44    (42 / 34 / 28 savdo)
```

Eski tizim bilan farq:

```
ESKI:   1.00 → 0.84 → 0.69    ustunlik YO'QOLADI
YANGI:  3.37 → 2.90 → 2.44    ustunlik BOR, torayadi
```

**TO'XTASH QOIDASI ISHGA TUSHMADI.** PF ≥ 1.0 uchala kesishmaydigan
oynada, 100+ savdo bilan.

### 🟡 YANGI KUZATUV — ustunlik torayyapti

Bitta savdodagi natija PF dan TEZROQ pasayadi:

    stop 0.5%:   +2.14% → +1.81% → +1.05%
    stop 1.5%:   +3.25% → +2.49% → +1.29%

Bu "moslashgan" degani emas (uchala oyna ham foydali), lekin
yo'nalish bitta tomonga. Jonli kuzatuvda BIRINCHI shu qator
tekshiriladi.

### 🔴 HALI O'LCHANMAGAN — ro'yxat qisqarmadi

Yuqoridagi jadvaldagi 19 ta raqam hamon 🔴. Ablatsiya BIRINCHI
yugurishda ma'nosiz chiqdi (35 savdo), va u YANGI chegarada
QAYTA yuritilishi kerak. Aynan u qaysi tekshiruvlar bo'sh
ekanini aytadi.

Shuningacha: zanjirning 16 ta ichki tekshiruvidan **qaysi biri
ishlayotgani noma'lum**. PF 3.17 — zanjirning UMUMIY natijasi,
uning qismlariniki emas.

---

## 2026-09-04 — ABLATSIYA JAVOB BERDI (12 coin, 277 savdo)

Yuqoridagi savol — "16 ta tekshiruvdan qaysi biri ishlayapti?" —
o'lchandi. To'liq natija:
`docs/BACKTEST_NATIJA_2026-09-04_zanjir2.md`.

### Javob: BIRORTASI HAM emas

    Hissa qo'shadi (PF ni oshiradi):     0 ta
    Ta'sirsiz (ΔPF = +0.00):            11 ta
    O'chirilganda PF OSHADI:             5 ta

Bu — gipoteza RAD ETILDI degani. Modul qurilganda taxmin
shunday edi: "har bir tekshiruv nomzodni yaxshilaydi". O'lchov
buni tasdiqlamadi.

### Sabab TOPILDI va u tuzilmaviy

Blok `kuch >= 1` da o'tadi — 4 tadan bittasi yetadi. Ya'ni blok
ichida tekshiruvlar VA emas, **YOKI**:

    Blok = t1 YOKI t2 YOKI t3 YOKI t4

YOKI zanjiridan bitta halqani olib tashlash natijani
o'zgartirmaydi. Shuning uchun 11 ta "+0.00" — bu tekshiruvlar
yomon degani emas, ular hozirgi qoida ostida hech qachon HAL
QILUVCHI emas degani.

5 tasi (nisbiy kuch, fibonacci, RSI, pastki TF, swing)
o'chirilganda PF oshgani boshqa narsani aytadi: ular ba'zan
YOLG'IZ blokni o'tkazgan, va o'sha savdolar o'rtacha yomon.

### 🔴 Bu yerdan CHIQARILMAYDIGAN xulosalar

Quyidagilar MANTIQAN kelib chiqadi, lekin O'LCHANMAGAN — shuning
uchun ular gipoteza, qaror emas:

| 🔴 | Gipoteza | Nega hozir qabul qilinmaydi |
|---|---|---|
| 🔴 | Blok qoidasi 2/4 bo'lsin | Bu YANGI qoida — o'lchanishi shart |
| 🔴 | 11 ta bo'sh tekshiruv olib tashlansin | Birma-bir ≠ birga; alohida o'lchanadi |
| 🔴 | 5 ta "zararli" tekshiruv olib tashlansin | Ular boshqa qoida ostida foydali bo'lishi mumkin |
| 🔴 | Ustunlik DARAJALARDA (zona/stop/TP) | Eng kuchli gumon — alohida o'lchanadi |

Oxirgi qator eng muhimi. Agar 16 ta tekshiruvning birortasi ham
natijani yaxshilamasa, PF 3.50 ni nima keltiryapti? Eng ehtimoliy
javob — zanjir emas, **darajalar**: zona ichida kirish, zona
tagida stop, strukturaviy TP. Buni tekshirishning yagona yo'li —
zanjirni butunlay o'chirib, faqat darajalar bilan o'lchash.

### Chegaralar 12 coinda qayta o'lchandi

| Raqam | 5 coin xulosasi | 12 coin natijasi | Qaror |
|---|---|---|---|
| `stop_eng_kam_pct` | 1.5 (muhandislik) | 0.5→3.63, 1.5→3.50 (farq 0.13) | 1.5 QOLADI |
| `tp1_eng_kam_nisbat` | 1.5 | 1.0→3.39, 1.5→3.51, 2.0→2.65 | 1.5 QOLADI |

`stop_eng_kam_pct` farqi shovqin darajasida chiqdi — ya'ni bu
raqam O'LCHOV bilan emas, muhandislik mulohazasi bilan tanlangani
o'z kuchida qoladi va shundayligicha yozilgan.
