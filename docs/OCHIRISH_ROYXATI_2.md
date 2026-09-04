# Eski tahlil moduli — IKKINCHI VA YAKUNIY O'CHIRISH

Sana: 2026-09-04

## Nima uchun ikkinchi marta

2026-09-03 da eski modulning **kodi** o'chirilgan edi (156 fayl,
−31 579 qator). Lekin uning **izlari** qoldirilgan edi va bu xato
edi. Admin buni to'g'ri ko'rsatdi.

Qolgan izlar quyidagilar edi va ular endi ham ketdi.

## O'CHIRILDI

### Kod

| Nima | Nega qolgan edi |
|---|---|
| `core/risk_engine/` | bot uni yaratardi, lekin HECH QAYERDAN chaqirmasdi |
| `core/market_data/ranking.py` | CMC reyting — eski modulning "Top-N coin"i |
| `core/market_data/dominance.py` | BTC dominance — eski Salomatlik indeksiga kirardi |
| `core/halal_screening/screener.py` | `build_universe()` — hech kim chaqirmasdi |
| `MarketRankEntry`, `RankingProvider` | faqat reyting uchun edi |

### Signal turlari

Eski modulning to'rt strategiyasi `SignalSource` dan chiqarildi:
`CLASSIC_TA`, `OPENING_RANGE_SCALP`, `CORRECTION_ENTRY`,
`NARX_HARAKATI`.

Qoldi: **`MANUAL`** va **`ZANJIR`** — boshqa hech narsa.

### Jadvallar

`pipeline_events`, `risk_blocks`, `daily_stats`,
`market_health_log`, `audit_reports`.

Model, repozitoriy, migratsiya — hammasi. Va eng muhimi:
**server bazasidan ham o'zi olib tashlanadi** (pastga qarang).

### Sayt

| Sahifa | Nima edi |
|---|---|
| `/salomatlik` | Bozor Salomatligi shkalasi |
| `/sokinlik` | eski "nega signal yo'q" ekrani |
| `/admin/jonli` | Jonli Oshxona monitori |
| `/admin/hisobot` | haftalik audit hisobotlari |
| `/api/jonli` | o'sha monitorning API'si |

Komponentlar: `Salomatlik.tsx`, `JonliOshxona.tsx`, `oshxona.ts`.
`queries.ts` dan olti funksiya: `salomatlikOxirgi`,
`salomatlikTarixi`, `voronka`, `ballStatistikasi`, `hisobotlar`,
`jonliHolat`.

Bosh sahifadagi Salomatlik kartochkasi, menyudagi bandi, signal
sahifasidagi "Bozor Salomatligi" ko'rsatkichi — hammasi ketdi.

### Botdagi ekranlar

**Statistika** ekrani eski modulning `daily_stats` jadvalidan
o'qirdi. Endi u ochiq aytadi: hozircha ma'lumot yo'q. Eski
raqamlarni yangi modul natijasi sifatida ko'rsatish
foydalanuvchini aldash bo'lardi.

### Yorliq

"🕰 Eski modul" yorlig'i ham o'chirildi. Uning ma'nosi yo'q:
belgilanadigan eski signal qolmadi.

## Server bazasi — QO'SHIMCHA BUYRUQ YO'Q

Avval `/eski_tozalash` buyrug'i qurilgan edi. **U ham
o'chirildi** — chunki admin qo'lidan qo'shimcha ish talab qilardi.

Endi jadvallar ishga tushishda **o'zi** olib tashlanadi
(`core/storage/database.py`, `ESKI_MODUL_JADVALLARI`). Ya'ni:

    deploy qilinadi -> bot ko'tariladi -> jadvallar ketadi

Loglarda ko'rinadi:

    Eski tahlil moduli jadvallari bazadan chiqarildi: ...

Ikkinchi marta ishga tushirilganda hech narsa qilmaydi.

## QOLGAN — va nega

| Nima | Nega qoladi |
|---|---|
| `config.risk_engine` bo'limi | SOZLAMA, modul emas. Korrelyatsiya guruhlarini YANGI modul ishlatadi |
| `core/halal_screening/rulings.py` | halol/harom hukmlari — eski modulga tegishli emas |
| `coin_rulings`, `halal_universe_snapshots` | o'sha hukmlarning bazasi |
| `signals`, `signal_events`, `user_positions` | YANGI modul ham shu jadvallarga yozadi |
| `bozor_kesimlari`, `bozor_korinishlari` | sayt uchun bozor ko'rinishi — tahlilga bog'liq emas |
| O'lchov hujjatlari | tarix. Hech qachon o'chirilmaydi |

`signals` jadvalidagi eski QATORLAR ketadi — lekin jadvalning
o'zi qoladi, chunki yangi modul unga yozadi.

## Natija

    53 fayl o'zgardi, 3972 qator o'chirildi
    699 Python testi + 151 veb testi o'tdi

Eski tahlil modulidan **kod ham, jadval ham, sahifa ham, yorliq
ham** qolmadi.
