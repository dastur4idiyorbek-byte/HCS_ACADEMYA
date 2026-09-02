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

    o'lchanmagan  (🔴)   130
    aniq emas     (🟡)     2
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
> ya'ni ADX noto'g'ri qatordan o'qilayotgan paytda o'lchangan.
> `07c2147` dan keyingi run #8 da bazaviy win-rate 37.9% emas,
> **32.1%** chiqdi (`BACKTEST_NATIJA_2026-09-02_5.md`). Filtrlar
> yangi o'lchovda ham qimirlamadi (30.8–33.5%), ya'ni **xulosa
> o'zgarmadi** — faqat mutlaq qiymatlar pastroq.

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
| 🔴 | `weights.support_resistance` | 25 |  |
| 🔴 | `weights.trend` | 20 |  |
| 🔴 | `weights.rsi` | 15 |  |
| 🔴 | `weights.volume` | 15 |  |
| 🔴 | `weights.macd` | 10 |  |
| 🔴 | `weights.risk_reward` | 15 |  |
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

> **YANGILANDI — sabab topildi, gipoteza EMAS.** Uchinchi ma'no
> bor ekan: backtest isinish davri salomatlik timeframeini
> hisobga olmasdi, ya'ni sinovning 54% ida haftalik struktura
> umuman hisoblanmasdi va indeksning 60 balli qismi nolda qolardi
> (`docs/ARXITEKTURA.md`, 80-bo'lim). Bu o'lchov xatosi edi, bozor
> haqidagi xulosa emas.
>
> Tuzatildi. Indeks kalibrlanganmi degan savol **hali ochiq** —
> lekin unga javob berish uchun avval o'lchov to'g'ri bo'lishi
> kerak edi.

Indeksga kiruvchi HAMMA raqam bu daftarda 🔴: omil vaznlari, ADX
chegaralari, kenglik foizlari, band chegaralari
(`low`/`normal`/`high`). Ya'ni markaziy puls to'liq o'lchanmagan
taxminlar ustida turibdi.

Bu gipotezaning oldingilardan farqi: u "signal sifati" haqida emas,
**"tizim umuman qachon savdo qiladi"** haqida.
