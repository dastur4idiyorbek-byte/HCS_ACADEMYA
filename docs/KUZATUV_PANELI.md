# Kuzatuv paneli — 80 coin, signal bermaydi

**Kim uchun:** loyiha egasi va bu loyihaga yangi kelgan odam.
**Sana:** 2026-09-12
**Manba:** `9_prompt_yakuniy_kuzatuv_moduli.md`

---

## Bir jumlada

80 halol coin doimiy kuzatiladi. Modul **faqat ko'rsatadi** —
kirish, stop va nishon narxlari hech qachon hisoblanmaydi. Qarorni
admin o'zi, ko'rgan ma'lumot asosida qabul qiladi.

---

## Ikki rejim — bitta hisoblash

| | Rejim A (signal moduli) | Rejim B (kuzatuv paneli) |
|---|---|---|
| Blok "yo'q" desa | **zanjir uziladi**, keyingilari hisoblanmaydi | **hech narsa uzilmaydi** |
| Delisting/unlock xavfi | coinni chetlatadi | **faqat ogohlantiradi** |
| Natijasi | signal (hozir o'chiq) | ro'yxatdagi o'rin |
| Fayl | `chain/block_chain_engine.py` | `analysis/observation_mode.py` |

**Ikkalasi AYNAN bir xil blok funksiyalarini chaqiradi.** Blok
mantig'i ko'chirilmagan — import qilingan. Ikki nusxa bo'lganda
ular vaqt o'tib ajralib ketardi va panel signal modulidan boshqa
narsa ko'rsatardi.

Signal moduliga **bir harf ham tegilmagan**.

---

## Eng qat'iy qoida: faqat yuqoriga yurish

Biz SPOT savdo qilamiz — faqat xarid, short yo'q. Shuning uchun:

> Coin Downtrend bo'lsa, Diqqat darajasi qanchalik yuqori
> chiqishidan **qat'i nazar**, na Top 20 ga, na "+10" ga kiradi.

Ikki holat o'tadi:
- **Uptrend** — HH/HL ketma-ketligi davom etmoqda
- **Yangi burilish** — tushishdan endi chiqdi (oxirgi 10 sham ichida)

Filtr Diqqat darajasini hisoblashdan **oldin** qo'llanadi:
o'tmagan coin uchun qolgan uch blok umuman hisoblanmaydi.

**"Yangi burilish" tushunchasi loyihada yo'q edi.** Mavjud
`bos_choch.py` burilishni faqat bir tomonga biladi ("ko'tarilish
tugadi"). Uni o'sha faylga qo'shish signal modulining javobini ham
o'zgartirardi, shuning uchun aniqlash yangi modul ichida yozildi
(`analysis/structure/uptrend_filter.py`).

---

## Ikkinchi darvoza: coin hali yurmagan bo'lsin

Yo'nalish darvozasi yetarli EMAS. `HH/HL ketma-ketligi` coin
**allaqachon yurganda ham** to'g'ri bo'ladi — aslida u eng kuchli
aynan shunda ko'rinadi.

> **Bu xato jonli panelda ko'rindi.** Loyiha egasi Top 20 ni ochdi
> va u yerda harakatini tugatgan coinlarni ko'rdi. To'g'ri savol
> shu edi: bizga yurish potensiali bor, lekin **hali yurmagan**
> coin kerak.

Endi narxning o'rni ham tekshiriladi. O'lchov — loyihaning **o'z**
Fibonacci zonasi (`fib_zona`), yangi raqam o'ylab topilmadi:

| narx qayerda | bosqich | ro'yxatga kiradimi |
|---|---|---|
| zona **tepasida** | `yurgan` | ❌ harakat bo'lib bo'lgan |
| zona **ichida** (38.2–61.8%) | `korreksiya` | ✅ klassik qaytish |
| zona **pastida** | `chuqur` | ✅ chuqurroq qaytgan |
| impuls topilmadi | `nomalum` | ✅ bilmaslik jazo emas |

Coin nomzod bo'lishi uchun **ikkala darvoza** ham ochiq bo'lishi
kerak: struktura yuqoriga qarasin **va** harakat tugamagan bo'lsin.

Chuqur ko'rinishda narx impulsning qayerida ekani shkala bilan
chiziladi — qaytish zonasi alohida rangda.

### Shu bilan birga topilgan ikkinchi xato

Ro'yxatdagi "arzon/qimmat" ustuni zona **markazini** narx deb
olardi. Markazning nisbati esa doim 0.5 — ya'ni ustun **har doim
"o'rtada"** deb turardi va hech narsa aytmasdi. Joriy narx endi
bazada saqlanadi va ustun haqiqiy javob beradi.

---

## Alternativ yo'llar — to'liq saqlanadi

Blok **zaif** (1/N) chiqsa, zaxira usullar ketma-ket sinaladi.
Biri ishlasa — blok qutqariladi va 2/N ga chiqadi.

| blok | zaxira usullar |
|---|---|
| Struktura | `trend_flag`, `qosh_tub` |
| Zona sifati | `qosh_tub` (zona beradi), `oldingi_swing` (zona beradi) |
| Tasdiqlash | `hajm_sakrashi`, `tez_harakat`, `qayta_sinov` |

G'olib usul blokka `alternativ:<nom>` degan ijobiy tekshiruv
bo'lib qo'shiladi va **ekranda ko'rinadi** — admin qaysi usul
ishlaganini biladi.

Zona blokida g'olib alternativ **o'z zonasini** beradi va u asosiy
zona o'rnini oladi: keyingi blok ham, ekran ham o'shani ko'radi.

Usullar `alternatives/alternative_chain.py` dan aynan o'sha holda
chaqiriladi — ko'chirilmagan.

> **Bu qism birinchi yozuvda tushib qolgan edi.** Alternativ
> usullar zanjir uzish mantig'i bilan bitta faylda turadi; o'sha
> fayldan qochganda ular ham yo'qolgan. Loyiha egasi buni
> so'raganda tuzatildi, va endi `test_alternativ_generatorlar_chaqiriladi`
> ularning chaqirilishini qulflab turadi — test ataylab buzib
> sinaldi.

---

## Diqqat darajasi — to'rt ichki tekshiruv

Segmentlar **bloklarga emas**, ichki tekshiruvlarga bog'langan:

1. Zona konfluensiyasi (kamida O'RTA: Fib + OB)
2. Volume Profile
3. Liquidity Sweep
4. RSI divergensiyasi

**Nega bloklarga emas.** Struktura filtrdan o'tganlar uchun doim
to'la, Fundamental esa o'sha paytda umuman bo'sh edi.
Ya'ni blok segmentlarining ikkitasi qotib qolardi va 20 coin
bir-biridan atigi ikki segment bilan farq qilardi.

To'rt blokning o'zi yo'qolmadi — ular chuqur ko'rinishda alohida
karta bo'lib qoladi.

**Uchinchi holat bor.** Segment ✅, ❌ dan tashqari ⚪ ham
bo'lishi mumkin — o'lchanmagan. Uni "yo'q" deb chizish yolg'on
bo'lardi: biz salbiy javob olmadik, biz umuman o'lchamadik.

---

## Timeframe

| | grafik |
|---|---|
| Struktura va Uptrend filtri | 4 soatlik |
| Zona, Liquidity Sweep, RSI | 1 soatlik |
| Pastki TF tasdig'i | 15 daqiqalik |

Har bir segment o'z timeframeini natijada olib yuradi — ekranda
qo'lda yozilmaydi. Config o'zgarsa, ekrandagi yozuv ham o'zgaradi.

---

## Ikki darajali ro'yxat — ikki MA'NO

Ro'yxatlar tartib bo'yicha bo'linmaydi ("birinchi 20, keyingi
10"). Har birining o'z ma'nosi bor:

| ro'yxat | kim tushadi |
|---|---|
| 🟢 **Top 20 — xarid uchun tayyor** | struktura yuqoriga qaragan **va** narx hali yurmagan |
| 🟡 **+10 — hali tayyor emas** | struktura yuqoriga qaragan, lekin harakat **allaqachon bo'lgan** |

Ikkinchi yorliq aynan shuni anglatadi: coin yomon emas, shunchaki
**hozir kech**. Narx qaytsa, keyingi skanda tepaga ko'tariladi.

> **Bu ham ikki qadamda topildi.** Avval bosqich darvozasi yurib
> bo'lgan coinni butunlay chetlatardi, va 80 tadan atigi **4 tasi**
> qolgan — promptning "20 + 10" tuzilmasi buzilgandi. Loyiha
> egasi buni ekranda ko'rdi. Endi bosqich coinni chetlatmaydi,
> **ro'yxatini tanlaydi**.

Teng ball chiqqanda tartib: zona darajasi → nisbiy kuch → alifbo.
Oxirgisi promptda yo'q, lekin zarur: ansiz teng coinlar har
yugurishda o'rin almashardi.

**Sun'iy to'ldirish yo'q.** Nomzod kam bo'lsa, ro'yxat kamroq
ko'rinadi — pastroq coinni ko'tarish foydalanuvchini chalg'itardi.

---

## Jonli bozor ma'lumoti — ikki manbadan

| nima | qayerdan | nega |
|---|---|---|
| Stakan, savdo lentasi | **brauzer** to'g'ridan-to'g'ri birjadan | Sekundiga o'nlab marta o'zgaradi. Serverga nol yuk, ma'lumot chinakam jonli |
| Xarid bosimi, yirik savdolar | **bot** uzluksiz yig'adi | "So'nggi 15 daqiqa" haqida — brauzer sahifani endi ochgan va o'tganini ko'rmagan |

Faqat **Top 20** uchun. "+10" va qolganlarga oqim ulanmaydi.
Coin Top 20 dan chiqsa, jonli qatori o'chiriladi: unga oqim
ulanmaydi va qator muzlab qolardi.

Chuqur ko'rinishda ko'rsatiladi:

- **Jonli narx** — savdo oqimidan, bazadan emas. Bazadagi narx
  skan paytidagi, ya'ni soatlab eskirgan bo'lishi mumkin
- **Stakan** — 10 daraja, gorizontal bar bilan
- **Savdo lentasi** — so'nggi 20 savdo
- **Xarid bosimi** — vizual shkala
- **Katta operatsiyalar ro'yxati** — so'nggi 15 daqiqada
  $50 000+ bo'lgan savdolar, vaqti va summasi bilan

CoinGecko jadvali **ikonkali** (prompt talabi) va likvidlik
ko'rsatkichi ham unda.

**Eng oson adashiladigan joy** — Binance `m` bayrog'i. U "xaridor
MAKER edimi" deydi, ya'ni `true` bo'lsa tashabbuskor **sotuvchi**.
Uni to'g'ridan-to'g'ri "xarid" deb o'qish bosimni teskari
ko'rsatardi.

Xarid bosimi **summa** bo'yicha o'lchanadi, savdolar soni bo'yicha
emas: bitta $9 000 lik xarid o'nta $1 000 lik sotishdan og'irroq.

---

## Chuqur ko'rinishda nima bor (5.3-qism)

Prompt uch marta **ANIQ NARX** so'raydi va bu talab birinchi
yozuvda bajarilmagan edi. Blok tekshiruvlarining izohi faqat
"bor / yo'q" deydi — ular ball hisoblash uchun yozilgan,
ko'rsatish uchun emas.

Endi alohida bo'lim bor:

| daraja | qayerdan |
|---|---|
| Qo'llab-quvvatlash / Qarshilik | zona oralig'i |
| BOS tasdiqlangan daraja | `bos_choch_topish` |
| Sweep sinagan daraja | oxirgi swing past — `sweep_bormi` aynan shuni sinaydi |

Har blok kartasida **ikonka** bor (prompt: "IKONKA bilan"), va
alternativ bilan qutqarilgan blok qaysi usul ishlaganini yozadi.

Timeframe **qo'lda yozilmagan** — u segmentdan olinadi, ya'ni
config o'zgarsa ekrandagi yozuv ham o'zgaradi.

---

## Kim nimani ko'radi

| | admin | foydalanuvchi |
|---|---|---|
| Top 20 ro'yxati | ✅ | — |
| "+10 kuzatuvda" | ✅ | ❌ |
| Blok kartalari, segment tafsiloti | ✅ | ❌ |
| Stakan, savdo lentasi, xarid bosimi | ✅ | ❌ |
| Coin qidirish (narx, kapitalizatsiya, hajm, yo'nalish) | ✅ | ✅ chegara bilan |

Kunlik qidiruv: obunasiz 1, lite 3, pro 10, premium 30. Raqamlar
`config/default.yaml` da — sayt ham, bot ham o'sha yerdan o'qiydi.

Chegara faqat **topilgan** qidiruvda ishlatiladi: mavjud bo'lmagan
coin nomini yozish limitni yemaydi.

---

## Qat'iy chegara va u qanday qulflangan

> Entry, Stop yoki TP **hech qayerda** hisoblanmaydi va
> ko'rsatilmaydi.

Buni ikki test qo'riqlaydi va ikkalasi ham **kod matnini** o'qiydi,
chaqiruv natijasini emas:

- `tests/core/test_kuzatuv_chegara.py` — Python tomonida
  `entry_stop_tp` import qilinmaganini va Rejim A
  chaqirilmaganini tekshiradi
- `web/tests/kuzatuv.test.ts` — sayt tomonida kalkulyator moduli
  ishlatilmaganini tekshiradi

Chegara testi **ataylab buzib ko'rildi** — taqiqlangan importlar
qo'shilganda ikkalasini ham qo'lga oldi, keyin tiklandi. Bu
loyihada testlar uch marta noto'g'ri narsani kuzatib turgani
aniqlangan, shuning uchun yangi qulf yozilganda avval sindirib
ko'riladi.

---

## Fayllar

```
core/analysis/observation_mode.py          Rejim B
core/analysis/structure/uptrend_filter.py  3-qism filtri
core/watch_panel/top20_selector.py         saralash
core/watch_panel/coin_scanner.py           80 coin skani
core/watch_panel/live_market_data.py       jonli yig'ma
core/watch_panel/cmc_snapshot.py           CoinGecko
core/watch_panel/search_limiter.py         kunlik chegara
core/watch_panel/repository.py             bazaga yozish

web/src/lib/kuzatuv.ts                     tiplar va ko'rinish
web/src/components/kuzatuv/                segment, qator, stakan
web/src/app/(ichki)/kuzatuv/               admin paneli
web/src/app/(ichki)/qidiruv/               foydalanuvchi qidiruvi
```

Jadvallar: `kuzatuv_holatlari`, `kuzatuv_skani`, `kuzatuv_bozor`,
`kunlik_qidiruv`.

---

## Ishlash tartibi

1. Skan har **4 soatda** o'zi yuradi
2. Admin istalgan paytda **bitta qo'shimcha skanni** qo'lda
   ishga tushira oladi — u tugagach o'zi to'xtaydi
3. "To'xtatish" tugmasi **yo'q**: to'xtatadigan narsa yo'q
4. Sayt skanni bajarmaydi — u bazaga bayroq qo'yadi, bot bir
   daqiqada ko'radi. Hisob Pythonda qoladi

---

## O'lchanmagan raqamlar

`skan_soat`, `tf_struktura`, `tf_zona`, `tf_pastki`, `YANGI_OYNA`,
qidiruv chegaralari — hammasi 🔴 o'lchanmagan va
`GIPOTEZA_DAFTARI.md` da shunday belgilangan.

Ular **pulga ta'sir qilmaydi**, chunki panel qaror qabul qilmaydi.
Agar kelajakda panel asosida savdo qilinadigan bo'lsa, avval
ular o'lchanishi **shart**.


---

## Fundamental blok — endi jonli

Blok uzoq vaqt bo'sh turdi: `FUNDAMENTAL_MALUMOT_MANBALARI.md`
"uni o'lchab bo'lmaydi" degan edi. O'sha xulosa **backtest**
haqida — kuzatuv paneli esa backtest qilmaydi va qaror qabul
qilmaydi, unga faqat hozirgi holat kerak.

Ulangan manbalar (hammasi **kalitsiz va bepul**):

| ko'rsatkich | manba |
|---|---|
| Fear & Greed | alternative.me |
| Funding Rate | Binance futures — **bitta so'rov, barcha juftlik** |
| Open Interest (7 kun) | Binance futures |
| Stablecoin zaxirasi (7 kun) | CoinGecko |

Ulanmaganlar — Netflow (pullik), yangiliklar (bepul planda yo'q),
delisting (API yo'q). Ular `MALUMOT_YOQ` bo'lib qoladi va
**maxrajga kirmaydi**: blok ma'lumot yo'qligi uchun jazolanmaydi.

Ekranda fundamental kartasi ostida qaysi manba jonli, qaysi biri
ulanmagani ochiq yozilgan.
