# Fundamental blok — manbalar tarixi bormi?

**Savol:** 2-promptning 8-qismi har bir ichki tekshiruvni ABLATSIYA
bilan sinashni talab qiladi. Ablatsiya esa TARIXIY ma'lumot talab
qiladi — kamida 2 yillik. Fundamental blokning 9 manbasidan
nechtasida shunday tarix bor?

Bu hujjat kod yozilishidan OLDIN tuzildi. Sabab: 4 ta modul qurib,
keyin "buni o'lchab bo'lmaydi" deb topish — bir oy ish va nol dalil.

---

## Jadval

| # | Manba | Tarix bormi | Bepulmi | Backtestga yaroqlimi |
|---|---|---|---|---|
| 1 | **Funding Rate** (Binance `/fapi/v1/fundingRate`) | ✅ 2019-dan | ✅ | ✅ **HA** |
| 2 | Open Interest (Binance `openInterestHist`) | ❌ **faqat 30 kun** | ✅ | ❌ yo'q |
| 3 | DXY (dollar indeksi) | ✅ o'nlab yil | ✅ (stooq/FRED) | ⚠️ boshqa host kerak |
| 4 | Exchange Netflow | ✅ | ❌ **pullik** (CryptoQuant/Glassnode) | ❌ yo'q |
| 5 | Stablecoin zaxirasi (CoinGecko) | ⚠️ bepul planda 365 kun | ✅ | ⚠️ yarim |
| 6 | Listing/Delisting | ❌ tarixiy API yo'q | ✅ | ❌ yo'q |
| 7 | Token Unlock (DefiLlama emissions) | ⚠️ jadval oldinga qaraydi | ✅ | ⚠️ yarim |
| 8 | **Fear & Greed** (alternative.me) | ✅ 2018-dan | ✅ | ✅ **HA** |
| 9 | Sektor rotatsiyasi (CoinGecko Categories) | ❌ faqat hozirgi holat | ✅ | ❌ yo'q |
| 10 | Yangiliklar (CryptoPanic) | ❌ bepul planda deyarli yo'q | ✅ | ❌ yo'q |

---

## Bu 1-blokning to'rt ichki tekshiruviga qanday tegadi

    1.1 Bozor holati    Funding ✅ + OI ❌ + DXY ⚠️   ->  3 dan 1 tasi o'lchanadi
    1.2 Pul oqimi       Netflow ❌ + Stablecoin ⚠️    ->  2 dan 0 tasi to'liq
    1.3 Katalizator     Listing ❌ + Unlock ⚠️        ->  2 dan 0 tasi
    1.4 Kayfiyat        F&G ✅ + Sektor ❌ + Yangilik ❌ -> 3 dan 1 tasi

Ya'ni 1-blokni prompt yozilganidek qurib bo'ladi, lekin uni
**O'LCHAB bo'lmaydi**. O'lchanmagan qism esa — aynan eski tizimni
o'ldirgan narsa: 100 balldan 60 tasi hech nima qilmayotgani
ablatsiyada chiqqan edi (`OLCHOVLAR_XULOSASI.md` #13).

## Muhim nuqta: 1.3 (katalizator) boshqacha

Prompt uni BALL emas, **QATTIQ TO'SIQ** deb belgilaydi: Unlock yaqin
va katta bo'lsa — coin butunlay chetlashtiriladi. Qattiq to'siqni
ablatsiya bilan o'lchash shart emas — u foyda qidirmaydi, zararning
oldini oladi. Uni JONLI rejimda ishlatib, backtestda "noma'lum ->
o'tkazish" deb qoldirish mantiqan to'g'ri.

## Nima o'lchanadi, nima yo'q — aniq chegara

    O'LCHANADI    Funding Rate, Fear & Greed  (+ DXY, agar stooq
                  GitHub Actions'da ochilsa)
    O'LCHANMAYDI  OI, Netflow, Sektor, Yangiliklar
    JONLI-ONLY    Token Unlock / Delisting qattiq to'sig'i

## Solishtirish uchun: 2, 3 va 4-bloklar

    BLOK 2 Struktura     shamdan hisoblanadi  ->  100% o'lchanadi
    BLOK 3 Zona sifati   shamdan hisoblanadi  ->  100% o'lchanadi
    BLOK 4 Tasdiqlash    shamdan hisoblanadi  ->  100% o'lchanadi
                         (4.4 bandi 1-blokka qaraydi)

Uchala blok ham bizda ALLAQACHON bor ma'lumot (Binance/Bitget
shamlari) bilan to'liq o'lchanadi.


---

# 2026-09-13 QO'SHIMCHA: kuzatuv paneli uchun manbalar ulandi

## Yuqoridagi xulosa BEKOR QILINMADI

"1-blokni O'LCHAB bo'lmaydi" — bu **hamon to'g'ri**, va u
**backtest** haqida. Ablatsiya va walk-forward ikki yillik tarix
talab qiladi; Open Interest (30 kun), sektor, yangiliklarda
bunday tarix yo'q.

## Lekin kuzatuv paneli boshqa savol so'raydi

Kuzatuv paneli (`9_prompt_yakuniy_kuzatuv_moduli.md`):

- backtest **qilmaydi**
- savdo qarori **qabul qilmaydi**
- faqat **hozirgi** holatni ko'rsatadi

Unga tarix umuman kerak emas. Shuning uchun o'sha manbalarni shu
yerda ishlatish mumkin — chegara "o'lchash" bilan "ko'rsatish"
orasida.

## Nima ulandi (`core/watch_panel/fundamental_manba.py`)

| manba | qayerdan | kalit kerakmi | qanday olinadi |
|---|---|---|---|
| **Fear & Greed** | alternative.me | yo'q | skanda bir marta |
| **Funding Rate** | Binance futures `premiumIndex` | yo'q | **bitta so'rov — barcha juftlik** |
| **Open Interest** | Binance `openInterestHist` | yo'q | coin boshiga, 7 kunlik o'zgarish |
| **Stablecoin zaxira** | CoinGecko `market_chart` | yo'q | USDT+USDC, 7 kunlik kapitalizatsiya |
| **Sektor rotatsiyasi** | CoinGecko `coins/categories` + `global` | yo'q | **bitta so'rov — barcha kategoriya** |
| **Token Unlock** | DefiLlama `emissions` | yo'q | **bitta so'rov — barcha loyiha** |

Natijada 1-blokning **to'rtala** tekshiruvi ham endi ishlaydi:

    1.1 Bozor holati   funding ✅ + OI ✅ + DXY ❌      ->  3 dan 2 tasi
    1.2 Pul oqimi      netflow ❌ + stablecoin ✅       ->  2 dan 1 tasi
    1.3 Katalizator    unlock ✅ + delisting ❌         ->  2 dan 1 tasi
    1.4 Kayfiyat       F&G ✅ + sektor ✅ + yangilik ❌ ->  3 dan 2 tasi

## Qattiq to'siq endi HAQIQATAN ishlaydi

`catalyst_watch.py` boshidanoq qattiq to'siq yozgan edi: unlock
**yaqin** (7 kundan kam) va **katta** (muomaladagi tokenning 5%
idan ko'p) bo'lsa, coin butunlay chetlashtiriladi.

Lekin kalendar ulanmagani uchun `unlock_kun` **har doim `None`**
edi va to'siq **hech qachon** ishlamasdi. Ya'ni kodda yozilgan
himoya amalda yo'q edi. Endi bor.

## Sektor kuchi MUTLAQ emas, NISBIY

"Sektor kuchli" = shu kategoriya **butun bozordan** tez o'sgan.
Shuning uchun `/global` ham so'raladi: hamma narsa 9% o'sgan
kunda 2% o'sgan sektor aslida **orqada qolgan**, garchi raqam
musbat bo'lsa ham. Test buni qulflaydi
(`test_sektor_MUTLAQ_emas_NISBIY_olchanadi`).

Oyna — **24 soat**, `Kayfiyat.sektor_kuchli` izohidagi "7 kun"
emas: CoinGecko bepul kategoriya endpointida faqat sutkalik
o'zgarish bor. Farq kodda ham, `GIPOTEZA_DAFTARI.md` da ham ochiq
yozildi.

## Sektor xaritasi qo'lda yozilgan

CoinGecko coinning kategoriyasini `/coins/{id}` da beradi — coin
boshiga bitta so'rov, 80 coin uchun 80 qo'shimcha so'rov. Shuning
uchun `core/watch_panel/sektor_xaritasi.py` da symbol -> kategoriya
xaritasi bir marta yozildi.

**Xato identifikator hech narsani buzmaydi**: kategoriya topilmasa
`sektor_kuchli` `None` bo'ladi (MALUMOT_YOQ, "zaif" emas), va
skaner topilmagan identifikatorlarni **logga** yozadi — admin
qaysi qatorni tuzatish kerakligini ko'radi.

## Nima ulanmadi va nima uchun

| manba | sabab |
|---|---|
| Exchange Netflow | CryptoQuant / Glassnode — **pullik** |
| Yangiliklar | CryptoPanic bepul planda deyarli hech narsa bermaydi |
| Delisting | jonli API yo'q — faqat qo'lda kuzatish |
| DXY | stooq — hali ulanmagan |

Ulanmaganlari `None` bo'lib qoladi va tekshiruvda **MALUMOT_YOQ**
beradi — "yo'q" emas. Ular maxrajga kirmaydi, ya'ni blok
ma'lumot yo'qligi uchun jazolanmaydi.

## O'zim qilgan xato

Birinchi yozuvda stablecoin zaxirasi CoinGecko ning **narx**
o'zgarishi maydonidan olingan edi. Stablecoinning narxi ta'rifi
bo'yicha $1 atrofida — ya'ni u qiymat deyarli **har doim ~0%**
bo'lardi va tekshiruv abadiy "o'zgarish yo'q" deb turaverardi.

Kerak bo'lgan narsa — **kapitalizatsiya** o'zgarishi: u yangi pul
chiqarilganini bildiradi. `market_chart` tarixni beradi va undan
aniq 7 kunlik farq hisoblanadi. Test buni qulflaydi: agar kod
narx maydoniga qaytsa, u yiqiladi.
