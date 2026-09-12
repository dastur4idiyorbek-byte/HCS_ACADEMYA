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

**Nega bloklarga emas.** Fundamental blokka manba ulanmagan — u
doim bo'sh; Struktura esa filtrdan o'tganlar uchun doim to'la.
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

## Ikki darajali ro'yxat

- **Top 20** — yuqorida, to'liq o'lchamda
- **Diqqatga molik +10** — pastroqda, kichikroq va xiraroq

Teng ball chiqqanda tartib: zona darajasi → nisbiy kuch → alifbo.
Oxirgisi promptda yo'q, lekin zarur: ansiz teng coinlar har
yugurishda o'rin almashardi.

**Sun'iy to'ldirish yo'q.** Nomzod 20 tadan kam bo'lsa, ro'yxat
kamroq ko'rinadi. Bozor tushayotganda xarid nomzodi kam bo'lishi
**kerak**.

---

## Jonli bozor ma'lumoti — ikki manbadan

| nima | qayerdan | nega |
|---|---|---|
| Stakan, savdo lentasi | **brauzer** to'g'ridan-to'g'ri birjadan | Sekundiga o'nlab marta o'zgaradi. Serverga nol yuk, ma'lumot chinakam jonli |
| Xarid bosimi, yirik savdolar | **bot** uzluksiz yig'adi | "So'nggi 15 daqiqa" haqida — brauzer sahifani endi ochgan va o'tganini ko'rmagan |

Faqat **Top 20** uchun. "+10" va qolganlarga oqim ulanmaydi.
Coin Top 20 dan chiqsa, jonli qatori o'chiriladi: unga oqim
ulanmaydi va qator muzlab qolardi.

**Eng oson adashiladigan joy** — Binance `m` bayrog'i. U "xaridor
MAKER edimi" deydi, ya'ni `true` bo'lsa tashabbuskor **sotuvchi**.
Uni to'g'ridan-to'g'ri "xarid" deb o'qish bosimni teskari
ko'rsatardi.

Xarid bosimi **summa** bo'yicha o'lchanadi, savdolar soni bo'yicha
emas: bitta $9 000 lik xarid o'nta $1 000 lik sotishdan og'irroq.

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
