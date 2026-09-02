# Backtestni qanday qilish — sodda qo'llanma

Bu hujjat bitta savolga javob berish uchun: **yangi Correction Entry
strategiyasini yoqamizmi yoki yo'q?**

Taxmin bilan emas, raqam bilan hal qilinadi. Shuning uchun strategiya
hozir **o'chirilgan** holatda turibdi.

Qo'llanma soddalashtirilgan: har qadamda nima yozish va nima ko'rish
kerakligi aytilgan.

---

## Nimaga bu kerak

Bozor Salomatligi past bo'lganda eski tizim signal qidirishni butunlay
to'xtatardi. Yangi tizim to'xtamaydi — u tuzilmaviy kirish qidiradi.

Qaysi biri yaxshi? Buni faqat tarixiy ma'lumot aytadi.

---

## 1-qadam. Kodni yangilash (Linux / macOS)

> Windows'da bo'lsangiz — pastdagi **Windows (PowerShell)** bo'limiga
> o'ting.

Terminalni ochib, loyiha papkasiga kiring:

```bash
cd HCS_ACADEMYA
git checkout claude/assalomu-alaykum-hncsjy
git pull
```

**Ko'rishingiz kerak:** `Updating ...` va o'zgargan fayllar ro'yxati.

---

## Windows (PowerShell) — eng sodda yo'l

Windows'da ishlayotgan bo'lsangiz, shu bo'limni o'qing va 2-5 qadamlarni
o'tkazib yuboring.

**Muhim maslahat: `activate` ni ishlatmang.** PowerShell odatda uni
bloklaydi ("running scripts is disabled on this system" degan xato).
Buning o'rniga Python'ni to'g'ridan-to'g'ri chaqiramiz — bir xil
natija, lekin hech qanday xato yo'q.

### Bir marta o'rnatiladigan narsalar

1. **Python 3.11** — https://www.python.org/downloads/
   O'rnatishda **"Add python.exe to PATH"** katagini albatta belgilang.
2. **Git** — https://git-scm.com/download/win
   Barcha savollarga standart javob (Next, Next).

Tekshirish — PowerShell'ni ochib:

```powershell
python --version
git --version
```

`Python 3.11.x` va `git version ...` chiqsa — tayyor.

### Loyihani olish (birinchi marta)

```powershell
cd $HOME
git clone https://github.com/dastur4idiyorbek-byte/HCS_ACADEMYA.git
cd HCS_ACADEMYA
git checkout claude/assalomu-alaykum-hncsjy
```

### Muhit (birinchi marta)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Bir necha daqiqa oladi. Oxirida `Successfully installed ...` chiqadi.

### Ishga tushirish

Avval kichik sinov:

```powershell
.venv\Scripts\python.exe -m scripts.backtest --compare --days 90 --symbols BTC
```

Xatosiz tugasa — asosiysi:

```powershell
.venv\Scripts\python.exe -m scripts.backtest --compare --days 730
```

### Keyingi safar

```powershell
cd $HOME\HCS_ACADEMYA
git pull
.venv\Scripts\python.exe -m scripts.backtest --compare --days 730
```

Shu xolos. Natijani o'qish — 5- va 6-qadamda.

> **Diqqat:** buyruqlarda `/` emas, `\` ishlatiladi va `python`
> o'rniga `.venv\Scripts\python.exe` yoziladi. Boshqa hamma narsa
> bir xil.

---

## 2-qadam. Muhitni tayyorlash (Linux / macOS)

Buni faqat BIRINCHI marta qilasiz. Keyingi safar 3-qadamdan boshlaysiz.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows'da uchinchi qator o'rniga: `.venv\Scripts\activate`

**Ko'rishingiz kerak:** terminal boshida `(.venv)` yozuvi paydo bo'ladi.

> Baza ham, `BOT_TOKEN` ham kerak emas. Backtest faqat sozlama faylini
> o'qiydi va Binance'dan tarixiy narxlarni yuklaydi.

---

## 3-qadam. Avval kichik sinov

Katta backtestdan oldin hammasi ishlayotganini tekshiring:

```bash
python -m scripts.backtest --compare --days 90 --symbols BTC
```

**Ko'rishingiz kerak:**

```
Ma'lumot tayyorlanmoqda: BTC (90 kun)
Yuklanmoqda: BTC 4h (540 sham)
...
Yuklandi: 1 coin, 540 qadam
  ishlamoqda: eski: past bandda to'xtash ...
```

Xatosiz tugasa — hammasi joyida, keyingi qadamga o'ting.

---

## 4-qadam. Asosiy backtest

```bash
python -m scripts.backtest --compare --days 730
```

Bu 2 yillik ma'lumot, 5 ta coin. **Birinchi marta 10-20 daqiqa**
ketishi mumkin — ma'lumot yuklanadi va `data/candles/` ga saqlanadi.
Keyingi safar qayta yuklanmaydi, tez ishlaydi.

Kompyuterni yopmang, terminal ochiq tursin.

---

## 5-qadam. Natijani o'qish

Oxirida shunday jadval chiqadi:

```
konfiguratsiya              signal  savdo     win   o'rt.%    jami%  pasayish
---------------------------------------------------------------------------
eski: past bandda to'xtash      64     61     54%   +0.82    +49.9     12.4%
yangi: Correction Entry         71     68     56%   +0.91    +61.6     13.1%
CE: confluence 3                58     55     60%   +1.04    +57.2      9.8%
CE: R/R 1.5                     83     79     48%   +0.61    +48.2     16.7%
CE: R/R 2.5                     52     50     58%   +1.11    +55.5      9.1%
```

> Yuqoridagi raqamlar — MISOL, haqiqiy natija emas. Sizniki boshqacha
> chiqadi.

Ustunlar ma'nosi:

| Ustun | Nimani bildiradi |
|---|---|
| **signal** | necha marta signal berilgan |
| **savdo** | shundan nechtasi yopilgan (TP yoki Stop) |
| **win** | nechta foizi foyda bilan yopilgan |
| **o'rt.%** | bitta savdodagi o'rtacha natija |
| **jami%** | umumiy natija — **eng muhim ustun** |
| **pasayish** | eng yomon paytda hisob qanchaga tushgan (drawdown) |

---

## 6-qadam. Qaror

Faqat ikkita qatorni taqqoslang: **eski** va **yangi**.

| Ko'rgan narsangiz | Qaror |
|---|---|
| yangi'ning **jami%** i katta VA **pasayish** i katta emas | ✅ yoqamiz |
| yangi'ning jami% i katta, lekin pasayish sezilarli chuqurroq | ❌ yoqmaymiz — foyda ko'proq xavf evaziga kelgan |
| yangi'ning jami% i kichik | ❌ yoqmaymiz |
| ⚠️ "30 ta savdo yig'ilmadi" degan yozuv chiqdi | ⏸ xulosa yo'q — `--days` ni oshiring yoki coin qo'shing |

Agar `CE: confluence 3` yoki boshqa variant eng yaxshi chiqsa — o'sha
sozlamani ham yozib qo'yamiz.

**Muhim:** natijani menga ko'rsating, birga o'qiymiz. Men strategiyani
sun'iy ma'lumotda sinaganman, haqiqiy bozorda emas.

---

## 7-qadam. Yoqish (faqat natija yaxshi bo'lsa)

`config/default.yaml` faylini oching, `correction_entry` bo'limini
toping (taxminan 470-qator) va bitta so'zni o'zgartiring:

```yaml
  correction_entry:
    enabled: true          # false edi
```

Saqlang, botni qayta ishga tushiring. Tamom.

---

## Kod to'g'ri ishlayotganini tekshirish

Bu backtestdan alohida narsa — kodning o'zi sinaladi. Tarmoq kerak
emas, bir necha soniya oladi:

```bash
python -m pytest -q          # 1270 ta test
ruff check .                 # kod uslubi
```

Veb sayt uchun:

```bash
cd web
npm test                     # 167 ta test
```

Hammasi `passed` bo'lsa — kod joyida.

---

## Muammolar

**`running scripts is disabled on this system`** (faqat Windows)
Siz `activate` ni ishlatibsiz. Uni tashlang va Python'ni to'g'ridan-
to'g'ri chaqiring: `.venv\Scripts\python.exe -m scripts.backtest ...`

**`python is not recognized`** (faqat Windows)
Python o'rnatilmagan yoki PATH'ga qo'shilmagan. Qayta o'rnating va
**"Add python.exe to PATH"** katagini belgilang.

**`ModuleNotFoundError`**
Muhit yoqilmagan. Linux/macOS'da `source .venv/bin/activate` ni qayta
yozing. Windows'da `.venv\Scripts\python.exe` orqali chaqiring.

**`Connection error` yoki `403`**
Internetda Binance yopiq bo'lishi mumkin (ba'zi mamlakatlarda). VPN
bilan urinib ko'ring yoki serverda ishga tushiring.

**`429` yoki `418`**
Binance juda ko'p so'rovdan shikoyat qilyapti. 10-15 daqiqa kutib,
qaytadan ishga tushiring — yuklangan ma'lumot saqlanib qolgan, u
qayta yuklanmaydi.

**Juda sekin ishlayapti**
Kamroq coin bilan boshlang:
`--symbols BTC,ETH` yoki `--days 365`.

**Ma'lumotni qaytadan yuklash kerak**
`--refresh` qo'shing yoki `data/candles/` papkasini o'chiring.

---

## Tarmoqsiz kompyuterda ishlatish

Agar backtestni internetsiz mashinada qilmoqchi bo'lsangiz:

1. Internetli kompyuterda bir marta oddiy ishga tushiring
2. `data/candles/` papkasini ko'chiring
3. U yerda `--offline` bilan ishga tushiring:

```bash
python -m scripts.backtest --compare --offline
```

Biror fayl yetishmasa, dastur uning nomini aniq aytadi.

---

## Barcha buyruqlar

| Buyruq | Nima qiladi |
|---|---|
| `--compare` | eski va yangi tizimni taqqoslaydi |
| `--days 730` | necha kunlik tarix (2 yil tavsiya etiladi) |
| `--symbols BTC,ETH` | qaysi coinlar (standart: BTC, ETH, SOL, BNB, XRP) |
| `--refresh` | ma'lumotni qaytadan yuklaydi |
| `--offline` | internetsiz — faqat saqlangan ma'lumot |
