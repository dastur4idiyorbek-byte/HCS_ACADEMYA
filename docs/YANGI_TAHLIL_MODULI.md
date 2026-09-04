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

## Ikkinchi o'lchov BAJARILDI (2026-09-04) — 12 coin

To'liq natija: `docs/BACKTEST_NATIJA_2026-09-04_zanjir2.md`

```
277 savdo, PF 3.50, 68.2% foydali
walk-forward:  PF 3.48 → 4.10 → 2.91   (121 / 87 / 96 savdo)
```

Ablatsiya "hech bir tekshiruv hissa qo'shmaydi" degan javob
berdi — va o'sha kuni ma'lum bo'ldiki, **javob emas, ASBOB
noto'g'ri edi**. Ablatsiya zanjir tugagandan keyin qo'llanardi,
ya'ni tekshiruvni o'chirish nomzodni oldinga o'tkaza olmasdi.

Xatoni "zanjirsiz — faqat darajalar" varianti ochdi: barcha 16
tekshiruv o'chirilganda natija "tasdiqlashsiz" varianti bilan
raqamma-raqam bir xil chiqdi (374 savdo). Hammasini o'chirib
ham hech narsa o'zgarmasa — o'zgartiradigan mexanizm
ishlamayapti.

Mexanizm tuzatildi (`ZanjirKirish.ochirilgan` — ablatsiya har
bir blok qurilgandan keyin darhol qo'llanadi) va ablatsiya
qayta yuritilmoqda. Tayanch, chegara va walk-forward raqamlari
o'z kuchida: ular ablatsiyasiz yurgan.

## Keyingi qadam — tartib bilan

1. **11 ta bo'sh tekshiruvni BIRGA o'chirib o'lchash.** Birma-bir
   va birga o'chirish — boshqa narsa. `zanjir_backtest.py` dagi
   "11 bo'sh tekshiruvsiz" varianti aynan shu.

2. **Zanjirsiz o'lchash.** Agar hech bir tekshiruv hissa
   qo'shmasa, PF 3.50 ni nima keltiryapti? Eng kuchli gumon —
   **darajalar**: zona ichida kirish, zona tagida stop,
   strukturaviy TP. "zanjirsiz — faqat darajalar" varianti buni
   tekshiradi. Agar natija yaqin chiqsa, modulning haqiqiy
   qiymati zanjirda emas.

3. **Sig'im bilan o'lchash** (`olchov: sigim`). Jonli tizimda
   `max_open_signals = 5` va guruhdan bitta signal — 12 coinning
   hammasiga bir vaqtda kirib bo'lmaydi.

4. **Faqat shundan keyin** — admin bilan jonliga chiqarish rejasi,
   KICHIK pozitsiya bilan (2-prompt, 8-qism, 7-band).

Avtomatik "yana bitta narsa qo'shaylik" bo'lmaydi. 2-3 bandlarning
natijasi "zanjirni soddalashtirish kerak" degan xulosaga olib
kelishi mumkin — bu ham QO'SHISH emas, OLIB TASHLASH bo'ladi.
