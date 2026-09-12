# Hozirgi tizim — zanjir moduli va ML yo'li

**Kim uchun:** loyiha egasi va bu loyihaga yangi kelgan odam (yoki
yangi Claude sessiyasi) uchun. Dasturchi bo'lish shart emas.

**Sana:** 2026-09-12
**Manba:** kodning o'zi o'qib chiqilgan (taxmin emas)

**Bog'liq hujjatlar:** `ML_ISHIMIZ_XULOSASI.md` (o'lchov tarixi),
`OLCHOVLAR_XULOSASI.md`, `GIPOTEZA_DAFTARI.md`, `ARXITEKTURA.md`.

---

## Bir jumlada

Zanjir **ishlashda davom etyapti va ekranga ma'lumot berib turibdi**
— to'xtatilgani faqat undan savdo signali yasash. ML yo'li esa
**tugmada turibdi**: ishlamaydi, lekin o'chirilmagan — chunki u
keyingi g'oyani o'lchash uchun tayyor mashina.

---

# 1. ZANJIR MODULI — qanday ishlaydi

## 1.1 Qayerda turadi

Hammasi `core/analysis/` papkasida, har bir blok o'z papkasida:

| Blok | Papka | Bosh fayl |
|---|---|---|
| Zanjirni yurituvchi | `chain/` | `block_chain_engine.py` |
| 1. Fundamental | `fundamental/` | `fundamental_block.py` |
| 2. Struktura | `structure/` | `structure_block.py` |
| 3. Zona Sifati | `zone_quality/` | `zone_block.py` |
| 4. Tasdiqlash | `confirmation/` | `confirmation_block.py` |
| Alternativ yo'llar | `alternatives/` | `alternative_chain.py` |
| AI tekshiruvi (5-blok) | `ai_verification/` | `ai_verifier.py` |

Jonli yuritish: `core/services/zanjir_sikl.py`
Vaqt jadvali: `bot/services/scheduler.py`

## 1.2 Har bir blok nimani tekshiradi

### 1-BLOK — Fundamental

Savol: **"Bu coinga umuman tegish mumkinmi?"**

To'rt tekshiruv: bozorning umumiy holati, pul oqimi (coinga pul
kirayaptimi), yaqinlashayotgan voqea-katalizator, kayfiyat va sektor.

Uchta **qattiq to'siq** ham bor — bulardan biri bo'lsa zanjir
shu yerdayoq uziladi:

- birjadan olib tashlanish xavfi (delisting)
- yaqin kunlarda katta token unlock
- xavfli voqea

> ⚠️ **Muhim:** hozir bu blokka **manba ulanmagan**. U "o'lchanmadi"
> holatida turadi va hech kimni to'smaydi. Ya'ni amalda hozir zanjir
> 1-blokdan deyarli hammani o'tkazib yuboradi. Manba ulanganda signal
> soni kamayadi — qanchaga, noma'lum (`GIPOTEZA_DAFTARI.md`).

### 2-BLOK — Struktura

Savol: **"Grafik ko'tarilish shaklidami?"**

- swing nuqtalar ko'tarilib boryaptimi (HH/HL)
- BOS (struktura buzilishi) tasdiqlanganmi
- teskari tomonga CHOCH yo'qmi
- coin BTC ga nisbatan kuchlimi

Yangi coinlar uchun (90 kundan yosh) soddalashtirilgan qoida
ishlaydi — ularda uzoq tarix yo'q.

### 3-BLOK — Zona Sifati

Savol: **"Qayerdan kirsa bo'ladi?"**

Bu blok boshqalardan **farq qiladi**. Fibonacci, Order Block va FVG
mustaqil ovoz EMAS — ular bir-birining **ustiga tushishi** kerak:

| qatlam | daraja |
|---|---|
| faqat Fib | ZAIF |
| Fib + OB | O'RTA |
| Fib + OB + FVG | KUCHLI |

Nega shunday: OB va FVG mustaqil ovoz bo'lganda, grafikning
boshqa-boshqa joyidagi uchta zona "kuchli" deb o'qilardi — aslida
ularning bir-biriga aloqasi yo'q. Konfluensiya esa aynan **ustma-ust
tushishni** anglatadi.

Volume Profile alohida, mustaqil ovoz.

Bu blok faqat baho bermaydi — u **Entry va Stop uchun aniq narx
oralig'ini** ham qaytaradi.

### 4-BLOK — Tasdiqlash

Savol: **"Hozir kirish vaqtimi?"**

- likvidlik supurilishi (liquidity sweep) bo'ldimi
- pastki timeframe tasdiqlayaptimi
- RSI divergensiyasi bormi
- 1-blokdagi fundamental **hali ham o'sha holatdami** (zanjir
  boshlanganidan beri o'zgarmadimi)

## 1.3 Zanjir mantig'i — qachon uziladi

Qoida sodda:

> **Blok butunlay bo'sh bo'lsa (0/4) zanjir uziladi va keyingi
> bloklar UMUMAN HISOBLANMAYDI.** Kamida bitta ijobiy tekshiruv
> bo'lsa — o'tadi.

Bu eski ball tizimidan **tub farq**. Eski tizimda 6 omil
*qo'shilardi*, ya'ni bitta kuchli omil qolgan beshtasining yo'qligini
yopib ketardi. Zanjirda bunday almashtirish mumkin emas — har bir
blok o'z halqasi, halqa uzilsa zanjir tugaydi.

"Hisoblanmaydi" degani **ataylab** shunday:

1. **Tezlik.** Zona va tasdiqlash bloklari eng qimmat qismlar.
   Strukturasi yo'q coin uchun ularni hisoblash — bekorga vaqt.
2. **Halollik.** Hisoblab keyin tashlab yuborish "biz buni ko'rdik"
   degan yolg'on tuyg'u berardi. Aslida ko'rmadik — zanjir uzilgan edi.

**Alternativ yo'l.** Blok 1/4 (zaif) chiqsa, `alternatives/`
papkasidagi zaxira usullar ketma-ket sinab ko'riladi — Trend Line +
Flag, Double Bottom, hajm sakrashi, tez harakat, qayta sinov. Biri
ishlasa blok qutqariladi va zanjir davom etadi.

**5-blok (AI).** To'rtala blok o'tgandan keyin DeepSeek ga so'rov
yuboriladi. Hozir **o'chiq** (`enabled = False`).

## 1.4 Hozir ISHLAYAPTIMI

**Ha — zanjirning o'zi ishlayapti. To'xtagani faqat signal yozish.**

- Bot har **4 soatda** zanjirni yuritadi
- Har bir coin uchun to'rt blok hisoblanadi, natija bazaga yoziladi
- Eng oxirida, hamma tekshiruvdan o'tgandan **KEYIN**, bitta darvoza
  turadi: `zanjir.avtomatik_signal = False` → signal **yozilmaydi**
- Kimdir hamma tekshiruvdan o'tsa, adminga Telegramda xabar keladi:
  *"N ta coin hamma tekshiruvdan o'tdi — avtomatik signal o'chiq,
  yozilmadi"*

Darvoza ataylab **oxirida** turibdi. Boshida turganida zanjir umuman
hisoblanmasdi va biz hech narsani ko'ra olmasdik. Hozir esa modul
ishlashda davom etadi, faqat qo'li bog'langan.

**Qayta yoqish:** `core/config/schema.py` dagi `avtomatik_signal`
ni `True` qilish yetarli. Lekin undan oldin o'lchov **musbat**
natija berishi kerak — aks holda to'xtatishning ma'nosi yo'q.

## 1.5 Natija qayerga yoziladi

**`zanjir_holatlari` jadvali** — har coinning oxirgi holati:
to'rt blokning kuchi, zanjir qayerda uzilgani, ishonch darajasi,
sabab izohi. Tarix saqlanmaydi — har yugurishda o'sha qator ustiga
yoziladi.

Saytda ikki joyda ko'rinadi: **Bozor holati** sahifasi va **Bosh
sahifa** dagi xulosa.

Oqim **qat'iy bir tomonlama**:

    modul -> hisoblaydi -> zanjir_holatlari -> ekran

Teskarisi taqiqlanadi: saytdagi hech bir raqam modulga qaytib
kirmaydi va signal qaroriga ta'sir qilmaydi. Eski tizimda aynan shu
qoida buzilgan edi — Bozor Salomatligi "ko'rsatkich" deb boshlanib,
keyin signalni to'sadigan darvozaga aylangan va tekshirib
bo'lmaydigan halqa paydo bo'lgandi.

Saytda halol xabar turibdi: *"Avtomatik signal 2026-09-10 dan beri
TO'XTATILGAN. Zanjir har 4 soatda coinlarni tekshirishda davom
etadi va natijani shu yerda ko'rsatadi, lekin signal yozilmaydi."*

---

# 2. ALTERNATIV YO'L — ML / XGBoost

## 2.1 Qayerda turadi

- `scripts/zanjir_dataset.py` — jadval yig'adi
- `scripts/zanjir_model.py` — modelni o'rgatadi va imtihon qiladi
- `requirements-ml.txt` — og'ir kutubxonalar (numpy, pandas, xgboost)
- `.github/workflows/zanjir.yml` — ularni GitHub da yuritadigan tugma

## 2.2 Nima qiladi

**Birinchi qadam — jadval.** Skript 4 yillik tarixni qayta
o'ynatadi va **har bir nomzod uchun bitta qator** yozadi: o'sha
paytdagi 56 ta ko'rsatkich (blok kuchlari, 16 ta ichki tekshiruv,
stop masofasi, nisbat va h.k.) va **haqiqatan nima bo'lgani** (TP ga
yetdimi, stop bo'ldimi, limit umuman bajarilmadimi).

Natija: **16 486 qator, 56 ustun, 24 halol coin, 4 yil.**

| yakun | soni | ulush |
|---|---|---|
| bekor (limit bajarilmadi) | 10 883 | 66.0% |
| stop | 4 482 | 27.2% |
| tp | 1 014 | 6.2% |
| muddat | 107 | 0.6% |

**Ikkinchi qadam — model.** XGBoost bu jadvalni o'qib, minglab
kichik "agar-unda" shartlar daraxtini quradi. Masalan: *"agar stop
3% dan kichik VA nisbat 1.5 dan katta VA FVG bor — ehtimol
yutadi"*. Eng qimmatli tomoni — u **qaysi ko'rsatkich qanchalik
ishlatilganini** ro'yxat qilib beradi, ya'ni ablatsiya ishini
avtomatik bajaradi.

## 2.3 Zanjirdan farqi

| | Zanjir | XGBoost |
|---|---|---|
| Qoidalarni kim yozgan | **Biz** — qo'lda | **Mashina** — ma'lumotdan topadi |
| Nechta omilni birga ko'radi | Bittalab (har blok mustaqil) | **Birikmalarni** ("A faqat B yuqori bo'lganda ishlaydi") |
| Ma'lumot | Bir xil | Bir xil |

**Ma'lumot bir xil.** Bu muhim: `zanjir_dataset.py` aynan o'sha
`zanjir_yur_alternativ` funksiyasini chaqiradi. Ya'ni ikki yo'l bir
xil ma'lumotni ko'rgan — javob farqi **usuldan**, ma'lumotdan emas.

**Bitta muhim tafovut:** dataset da **zanjir filtri yo'q**.
Zanjirdan o'tmagan nomzodlar ham yoziladi, zanjirning xulosasi esa
modelning **ustuni** bo'ladi (filtr emas). Filtr qo'yilganda model
atigi 66 ta qator ko'rardi va shovqinni yodlab olardi.

## 2.4 Hozir ISHLAYAPTIMI

**Yo'q.** Faqat odam GitHub da tugmani bossa yuradi
(`workflow_dispatch`). Jadval (`schedule`) **ataylab yo'q** — hech
narsa o'z-o'zidan yugurmaydi.

Kod **o'chirilmagan va o'chirilmaydi** — o'lchov mashinasi
kelajakdagi g'oya uchun tayyor turishi kerak.

Serverda bu kutubxonalar umuman o'rnatilmaydi (~100 MB, kerak emas).
O'rgatilgan model hech qayerda saqlanmagan va jonli tizimda
ishlatilmaydi.

## 2.5 Qanday natija berdi

Bitta gapda: **foyda beradigan birorta qoida topilmadi.**

**Ablatsiya.** 16 ta ichki tekshiruvni birma-bir o'chirib ko'rdik —
birortasi natijani na yaxshiladi, na yomonlashtirdi.

**Zanjirsiz solishtiruv.**

| nima | savdo | PF |
|---|---|---|
| To'liq zanjir (4 blok) | 153 | 0.83 |
| Zanjir UMUMAN yo'q | 310 | **0.84** |

Ya'ni butun tahlil modulimiz **saralamayapti**.

> PF (Profit Factor) — yutgan pulning yutqazgan pulga nisbati.
> 1.0 dan past = zarar.

**Chegara supurgisi.** Nishonni 1.67 barobar uzoqlashtirganda
g'alaba foizi 1.57 barobar tushdi — deyarli aynan mutanosib. Bu
tasodifiy kirishning imzosi: ustunlik bo'lganida uzoqroq nishon
ko'proq foyda berardi.

**XGBoost.** Barcha oynalarda bitta chegara bilan:

| konfiguratsiya | savdo | jami % | musbat oyna |
|---|---|---|---|
| TAYANCH (hozirgi qoidalar) | 162 | −169.1 | 0/4 |
| kutilgan foyda ≥ 1.5% | 132 | −94.8 | 2/4 |
| kutilgan foyda ≥ 0.0% | 1215 | −428.7 | 1/4 |

**Bitta ham konfiguratsiya foyda bermadi.** Musbat natijalarning
deyarli hammasi bitta qulay bozor davrida to'plangan. Bu ustunlik
emas, bu **ob-havo**.

> Bu ishda ikkita xato bo'lgan va ikkalasi ham o'lchovni **yolg'on
> yashil** qilib ko'rsatgandi: (1) modelga noto'g'ri savol berilgan
> ("musbat tugadimi?" — "foydalimi?" o'rniga); (2) chegara imtihon
> natijasini ko'rgandan KEYIN tanlangan. Ikkalasi ham
> `ML_ISHIMIZ_XULOSASI.md` da ochiq yozilgan va regressiya testi
> bilan qulflangan (`tests/core/test_zanjir_model.py`).
>
> **Sabog'i:** o'lchov kodining o'zi ham xato qilishi mumkin, va
> uning xatosi eng xavflisi — chunki u sizga yashil chiroq
> ko'rsatadi.

---

# 3. UMUMIY QISMLAR — kelajakda qayta ishlatish mumkin

Ikkala yo'l ham bir xil poydevorga tayanadi. Bular **ishlaydi va
tekshirilgan** — ular bilan muammo yo'q edi; muammo *ulardan
chiqarilgan savdo qaroridagi* edi. Shuning uchun "faqat kuzatuv,
signal bermaydigan" yangi funksiya uchun to'g'ridan-to'g'ri olsa
bo'ladi.

## 3.1 Tahlil qismlari

| fayl | nima qiladi |
|---|---|
| `structure/swing_detector.py` | grafikdagi cho'qqi va tublarni topadi — **butun tizimning poydevori**, hamma joyda ishlatiladi |
| `structure/bos_choch.py` | struktura buzilishi (BOS) va yo'nalish o'zgarishi (CHOCH) |
| `structure/relative_strength.py` | coin BTC ga nisbatan kuchlimi |
| `zone_quality/fibonacci.py` | Fib zonasi |
| `zone_quality/order_block.py` | Order Block |
| `zone_quality/fvg.py` | FVG (bo'shliq) |
| `zone_quality/volume_profile.py` | hajm bo'yicha eng ko'p savdo bo'lgan narx |
| `confirmation/liquidity_sweep.py` | likvidlik supurilishi |
| `confirmation/rsi_divergence.py` | RSI va divergensiya |

Har biri **mustaqil** — biri ikkinchisisiz ham ishlatiladi.

## 3.2 Ma'lumot va infratuzilma

- `core/market_data/binance.py` — sham yuklovchi, keshli
- `core/backtest/` — backtest motori: istalgan yangi g'oyani 4
  yillik tarixda sinash uchun tayyor
- `core/storage/zanjir_repository.py` — hisob natijasini ekranga
  chiqaradigan bir tomonlama kanal
- `core/position/entry_stop_tp.py` — zonadan Entry/Stop/TP yasash

## 3.3 Zanjirga umuman bog'liq bo'lmagan qismlar

Bular bu qarordan **mutlaqo ta'sirlanmadi** va to'liq ishlaydi:

- halol skrining (uch manbali konsensus)
- obuna, to'lov, admin panel
- Telegram Login (HMAC tekshiruvi bilan)
- akademiya, video darsliklar, kitob
- trading kalkulyatori
- bozor ko'rinishi (haftalik/kunlik)

---

# 4. Qisqacha javob jadvali

| savol | javob |
|---|---|
| Zanjir ishlayaptimi? | **Ha**, har 4 soatda |
| Signal yozayaptimi? | **Yo'q**, 2026-09-10 dan beri o'chiq |
| Natija qayerda ko'rinadi? | Saytda: Bozor holati + Bosh sahifa |
| ML ishlayaptimi? | **Yo'q**, faqat qo'lda tugma bilan |
| ML kodi o'chirilganmi? | **Yo'q**, saqlanadi |
| Nega to'xtatildi? | To'rtta mustaqil o'lchov: ustunlik yo'q |
| Qayta yoqish oson? | Bitta sozlama. Lekin avval o'lchov musbat bo'lishi kerak |
