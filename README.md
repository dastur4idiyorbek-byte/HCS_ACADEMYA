# HALOL CRYPTO SAVDO

Halol kripto **spot** savdo signallari va avtomatlashtirilgan tahlil mexanizmi.

Bu — oddiy signal-bot emas. Bu — bir-biriga bog'liq, o'zini kuzatib boruvchi
**mexanizm**: bozor holati, foydalanuvchi resurs sig'imi, halollik chegaralari va
texnik tahlil — barchasi markaziy **Bozor Salomatligi Indeksi** orqali
muvofiqlashtirilgan holda ishlaydi.

---

## Asosiy tamoyillar

| Tamoyil | Ma'nosi |
|---|---|
| **"Miya" va "tana" ajratilgan** | `core/` — sof Python mantig'i, `aiogram` importi YO'Q. `bot/` — yupqa Telegram qatlami. Kelajakda mobil ilova `core/` ni qayta yozmasdan ishlatadi. |
| **Foyda emas, to'g'ri qaror** | Maqsad "ko'proq signal" emas. Asosiy savol: *"Hozir signal berish to'g'rimi?"* Javob "yo'q" bo'lsa — signal berilmaydi, **bu normal holat**. |
| **Fail-safe** | Noaniqlik yoki xatolikda tizim signal **BERMASLIKKA** moyil bo'ladi, xato signal berishga emas. |
| **S/R birinchi** | Tahlil Support/Resistance zonalaridan boshlanadi. Indikatorlar — tasdiqlovchi, mustaqil signal manbai emas. |
| **Ko'p timeframe** | `15m → 30m → 1h → 4h → 1d`. Pastki TF yuqorisiga zid bo'lmasligi kerak. |
| **Halollik — brend negizi** | Faqat halol coinlar. Shubhali (mashbooh) ham harom kabi chetlab o'tiladi. |

---

## Arxitektura

```
core/                          "MIYA" — Telegram'ga bog'liq emas
├─ config/                     qatlamli konfiguratsiya (YAML + DB + env)
├─ domain/                     umumiy tiplar va modellar
├─ storage/                    DB sxemasi, repository'lar (15 jadval)
├─ services/                   obuna hayot-sikli                  ✅ tayyor
├─ market_data/                WebSocket, OHLCV, reyting          ✅ tayyor
├─ signals/                    holat mashinasi (⏳→✅→🎯→🎯🎯/🛑)   ✅ tayyor
├─ halal_screening/            Top 30 Halal mantig'i              ✅ tayyor
├─ analysis/
│   ├─ support_resistance/     S/R zonalari (BIRLAMCHI)           ✅ tayyor
│   ├─ indicators/             EMA/RSI/MACD/ADX/ATR/hajm          ✅ tayyor
│   ├─ scoring/                darajalar, ball, reyting           ✅ tayyor
│   ├─ market_health/          Bozor Salomatligi Indeksi          [10-bosqich]
│   ├─ postmortem/             Signal Xotirasi (o'z-o'zini audit) [13-bosqich]
│   └─ strategies/             classic_ta ✅ | opening_range      [12-bosqich]
├─ risk_engine/                13 ta risk qoidasi                 ✅ tayyor
├─ position_sizing/            pozitsiya hajmi + agregat sig'im   ✅ tayyor
├─ backtest/                   tarixiy sinov                      [16-bosqich]
└─ utils/                      vaqt (timezone-aware), logging     ✅ tayyor

bot/                           "TANA" — yupqa Telegram qatlami
├─ handlers/                   user.py, admin.py, signals.py      ✅ tayyor
├─ services/                   narx kuzatuvchisi (fon vazifasi)   ✅ tayyor
├─ i18n/                       matnlar JSON'da (ko'p tillilikka tayyor)
├─ keyboards.py                tarifga qarab menyu qurish
├─ middlewares.py              foydalanuvchi konteksti, admin himoyasi
├─ states.py                   FSM dialoglari
├─ formatting.py               signal-kartochka
├─ settings.py                 muhit sozlamalari
└─ database.py                 core/storage ustidan qayta-eksport

scripts/seed.py                boshlang'ich narxlar va coin qarorlari

config/default.yaml            BARCHA sozlanadigan raqamlar shu yerda
```

---

## Ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env        # BOT_TOKEN va ADMIN_IDS ni to'ldiring
python -m scripts.seed      # boshlang'ich narxlar va coin qarorlari
pytest                      # testlar
python -m bot.main          # botni ishga tushirish
```

---

## Konfiguratsiya

**Kodda birorta ham "sehrli raqam" yo'q.** RSI chegaralari, ball vaznlari, risk
foizlari, Juma vaqt oralig'i — hammasi `config/default.yaml` da. Admin panel
orqali o'zgartiriladigan qiymatlar bazadagi `risk_config` jadvalidan ustun
keladi.

Konfiguratsiya ishga tushishda **tekshiriladi**: vaznlar yig'indisi 100 emasmi,
pog'onalar tartibsizmi, noma'lum kalit bormi — barchasi darhol xato beradi,
signal berish paytida emas.

---

## Nima allaqachon ishlayapti

- **Halol skrining (3.4)** — reyting bo'yicha pastga tushib, harom/shubhali
  coinlarni o'tkazib yuborib, aynan 30 ta halol coin yig'adi
- **Risk Engine (4)** — 13 ta qoida, "VA" mantig'i, barcha rad sabablari
  yig'iladi (admin "nega berilmadi?" savoliga to'liq javob oladi)
- **Juma namozi filtri (4.8)** — UTC+5, 11:00–15:00, faqat YANGI signal
  to'xtaydi; mavjud signallar kuzatuvi davom etadi
- **Pozitsiya hajmi (5.1/5.1.1/5.2)** — pog'onali xavf, kunlik byudjetni
  taqsimlash, agregat foydalanuvchi sig'imi
- **Kirish buyurtmasi (5.1.0)** — narx zonaga yetmagan bo'lsa LIMIT, allaqachon
  zonada bo'lsa MARKET; chiqish har doim OCO. Signal-kartochka shabloni tayyor
- **DB sxemasi** — 15 jadval, SQLite → PostgreSQL ko'chishga tayyor
- **Telegram bot (1-bo'lim)** — obuna, to'lov cheki va admin tasdig'i, kontent
  `protect_content` bilan, admin panel (narxlar, halol ro'yxat, broadcast,
  qoidabuzarlik), tarifga qarab quriladigan menyu
- **Signal moduli (2-bo'lim)** — admin qo'lda kiritadi (FSM + preview),
  Binance WebSocket narxni kuzatadi, holat avtomatik yangilanadi, kill switch
- **S/R zonalari (3.1-band)** — swing pivotlar, zonaga birlashtirish, test
  sanash, Fibonacci yordamchi sifatida; barchasi ATR birligida o'lchanadi
- **Discount / Premium** — narx diapazonning arzon yoki qimmat yarmidami.
  Kirish faqat "Support zonasida VA Discount zonada" bo'lganda ko'rib chiqiladi
- **Indikatorlar (3.1-band)** — EMA50/200, RSI(14), MACD(12/26/9), ADX(14),
  hajm. Faqat TASDIQLOVCHI: `zone_ready=False` bo'lsa signal chiqmaydi
- **Ball tizimi (3.5-band)** — 6 omil, jami 100, darajali baholash. Chegara
  statik emas — Bozor Salomatligi Indeksiga qarab moslashadi
- **`classic_ta` strategiyasi** — to'liq zanjir: S/R → Discount → ko'p
  timeframe → indikatorlar → darajalar → ball

---

## Testlar

```bash
pytest -q
```

Eng muhim test — `tests/core/test_position_sizing.py::test_barcha_signallar_stop_yesa_limitdan_oshmaydi`.
Spetsifikatsiyaning 5.1.1-bandida u sinov sharti sifatida ochiq belgilangan:
*"qaysi usul tanlanmasin, barcha faol signallar bir vaqtda Stop yesa, jami
zarar kunlik limit foizidan oshmasligi KERAK"*. 120 ta kombinatsiyada
tekshiriladi.

---

## Ogohlantirish

Bu tizim **moliyaviy maslahat bermaydi**. Bot hech qachon haqiqiy hisobga
ulanmaydi, pulni ushlab turmaydi va "shuncha oling/soting" demaydi — pozitsiya
hajmi moduli faqat hisob-kitob yordamchisi. Hech qachon "X% aniqlik" da'vosi
qilinmaydi; faqat real statistika ko'rsatiladi.
