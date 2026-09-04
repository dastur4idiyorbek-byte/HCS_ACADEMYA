# Yangi tahlil moduli — to'rt blokli zanjir

2026-09-03 da noldan qurildi. Eski 100 balllik tizim 16 o'lchov
to'plamida foyda bermagani isbotlangach o'chirildi
(`OLCHOVLAR_XULOSASI.md`, `OCHIRISH_ROYXATI.md`).

---

## Asosiy g'oya

```
BLOK 1 Fundamental → BLOK 2 Struktura → BLOK 3 Zona → BLOK 4 Tasdiq
```

Har bir blok — 4 ta ichki tekshiruv. Qoida:

    0/4    → blok BUTUNLAY BO'SH → zanjir UZILADI, keyingi bloklar
             UMUMAN hisoblanmaydi
    1-4/4  → blok o'tadi, kuch darajasi bilan

Signal faqat to'rtala blok ham o'tganda chiqadi.

**Eski tizimdan farqi.** U 6 omilni QO'SHIB, yig'indini chegara bilan
solishtirardi — ya'ni bitta kuchli omil qolgan beshtasining yo'qligini
yopib ketardi. Zanjirda bunday almashtirish mumkin emas.

---

## Uchinchi holat: `MALUMOT_YOQ`

Modulning eng muhim qarori. Har bir tekshiruv **uchta** javob beradi:

    HA           ✅ hisoblanadi
    YOQ          ❌ hisoblanadi
    MALUMOT_YOQ  maxrajga UMUMAN kirmaydi

Nima uchun kerak: fundamental manbalarning yarmida 2 yillik tarix
yo'q (`FUNDAMENTAL_MALUMOT_MANBALARI.md`). Agar "ma'lumot yo'q" ni
"yo'q" deb hisoblasak, backtestda 1-blok doim 0/4 chiqib zanjir
**hech qachon** ulanmasdi — ya'ni biz strategiyani emas, ma'lumot
yetishmasligini o'lchagan bo'lardik.

Natijada blok "2/4" o'rniga halol "1/2" yozadi.

---

## Fayl xaritasi

```
core/analysis/
  turlar.py                 Blok, Tekshiruv, Zanjir, Holat
  fundamental/              BLOK 1
    market_regime.py          1.1 Funding + OI + DXY
    capital_flow.py           1.2 Netflow + Stablecoin
    catalyst_watch.py         1.3 Unlock/Delisting (QATTIQ TO'SIQ)
    sentiment_sector.py       1.4 F&G + Sektor + Yangiliklar
    fundamental_block.py      + ziddiyat belgisi
  structure/                BLOK 2
    swing_detector.py         2.1 5 shamli fraktal, HH/HL
    bos_choch.py              2.2/2.3 BOS va CHOCH
    relative_strength.py      2.4 coin/BTC
    new_coin_pattern.py       yangi coinlar uchun soddalashtirilgan
    structure_block.py
  zone_quality/             BLOK 3
    fibonacci.py              3.1
    order_block.py            3.2 (ikki ta'rif, ikkalasi sinaladi)
    fvg.py                    3.3
    volume_profile.py         3.4 POC
    zone_block.py             DARAJALI birlashtirish
  confirmation/             BLOK 4
    liquidity_sweep.py        4.1
    lower_tf_confirm.py       4.2 (YANGI KOD YO'Q — qayta chaqiradi)
    rsi_divergence.py         4.3
    fundamental_recheck.py    4.4
    confirmation_block.py
  chain/
    block_chain_engine.py     uzilish/o'tish qoidasi
    state_tracker.py          bosqichma-bosqich yangilash

core/position/
  entry_stop_tp.py            Entry/Stop/TP STRUKTURADAN
  scaling_out.py              50/30/20, breakeven, muddat

core/market_data/
  bitget.py                   ikkinchi manba
  price_reconciliation.py     wick solishtirish

core/backtest/
  zanjir_engine.py            zanjirni tarixda qayta o'ynatadi
  yuklash.py                  sham yuklash + oynaga bog'langan kesh
```

---

## Besh o'lchov skripti

```bash
# 1. Bosqichma-bosqich: 2 blok -> 3 blok -> to'liq zanjir
python -m scripts.zanjir_backtest --days 730

# 2. ABLATSIYA: 16 ta ichki tekshiruv birma-bir o'chiriladi
python -m scripts.zanjir_ablatsiya --days 730 --offline

# 3. WALK-FORWARD: kesishmaydigan oynalarda takrorlanadimi
python -m scripts.zanjir_walk_forward --days 730 --bolaklar 3 --offline

# 4. CHEGARA: stop va TP1 nisbati chegaralari BITTALAB surib ko'riladi
python -m scripts.zanjir_chegara --days 730 --offline

# 5. SIG'IM: portfel chegarasi (max_open_signals, korrelyatsiya)
#    zanjirdan nechtasini kesadi
python -m scripts.zanjir_sigim --days 730 --offline
```

GitHub Actions: `.github/workflows/zanjir.yml` (`olchov: hammasi`
beshalasini birga yuritadi va `reports/` ni artifact qilib
saqlaydi).

**Bu muhitdan Binance'ga chiqish yopiq** — shuning uchun birinchi
yugurish Actions'da bo'lishi kerak (`--offline` siz), keyin kesh
qoladi.

---

## Nima uchun ablatsiya eng muhim skript

Eski tizimda aynan shu o'lchov 100 balldan 60 tasi hech nima
qilmayotganini ko'rsatgan edi. Agar biz uni bir oy oldinroq
qilganimizda, oyning yarmi tejalardi.

Qoida (2-prompt, 8-qism, 3-band): ichki tekshiruv PF ni 0.03 dan
kam o'zgartirsa — **olib tashlanadi**, murakkablik saqlanmaydi.

---

## Birinchi o'lchov BAJARILDI (2026-09-03)

To'liq natija: `docs/BACKTEST_NATIJA_2026-09-03_zanjir.md`

```
stop 1.5%, walk-forward:   PF 3.37 → 2.90 → 2.44
                           42 / 34 / 28 savdo, uchala oyna foydali
```

To'xtash qoidasi ISHGA TUSHMADI — PF ≥ 1.0 uchala kesishmaydigan
oynada.

Qurish paytida topilgan eng katta xato o'zimniki edi:
`stop_eng_kam_pct = 3.0` savdolarning oltidan beshini to'sib
turardi. O'lchandi, 1.5 ga tushirildi.

## O'LCHOVLAR TUGADI (2026-09-04) — 12 coin

To'liq natijalar:
- `docs/BACKTEST_NATIJA_2026-09-04_zanjir2.md` (birinchi urinish,
  ablatsiya qismi bekor)
- `docs/BACKTEST_NATIJA_2026-09-04_zanjir3.md` (**ishonchli**)

```
to'liq zanjir (4 blok)         277 savdo   PF 3.50   pasayish 28.2%
11 bo'sh tekshiruvsiz          194 savdo   PF 2.80   pasayish 28.2%
tasdiqlashsiz (3 blok)         374 savdo   PF 3.95   pasayish 35.2%
faqat fundamental+struktura    374 savdo   PF 3.95   pasayish 35.2%
zanjirsiz — faqat darajalar    474 savdo   PF 3.05   pasayish 54.8%

walk-forward:  PF 3.48 → 4.10 → 2.90   (121 / 87 / 96 savdo)
sig'im bilan:  208 savdo   PF 3.54
```

**To'xtash qoidasi ishga tushmadi.**

### Uchta kutilmagan natija

1. **Promptning "bo'sh tekshiruvni o'chir" qoidasi bu yerda
   ishlamadi.** 11 tasini birga o'chirish PF ni 3.50 dan 2.80 ga
   tushirdi. Sabab: blokning 1/4 qoidasi ostida ular blokni
   OCHIQ ushlab turadi.

2. **4-blok (Tasdiqlash) PF ni pasaytiradi**, lekin pasayishni
   ham kamaytiradi.

3. **Zanjir foydani emas, XAVFNI boshqaradi.** Darajalarning
   o'zi PF 3.05 beradi, lekin 54.8% pasayish bilan. Zanjir uni
   28.2% ga tushiradi.

### Qurish paytida topilgan ikkita xato

- `stop_eng_kam_pct = 3.0` savdolarning oltidan beshini to'sardi
  (o'lchandi, 1.5 ga tushirildi).
- Ablatsiya zanjir tugagandan KEYIN qo'llanardi — o'lchov asbobi
  buzuq edi. Tuzatildi va hamma o'lchov qayta yuritildi.

## Keyingi qadam — ADMIN QARORI

Uch savol hal bo'lmaguncha modul jonli signal BERMAYDI:

1. 11 ta "bo'sh" tekshiruv o'chirilsinmi? (o'lchov: yo'q)
2. 4-blok olib tashlansinmi? (PF +0.45, pasayish +7%)
3. Blok qoidasi 2/4 bo'lsinmi? (o'lchanmagan)

Savollar raqamlari bilan `BACKTEST_NATIJA_2026-09-04_zanjir3.md`
9-bo'limida.

Avtomatik "yana bitta narsa qo'shaylik" bo'lmaydi.
