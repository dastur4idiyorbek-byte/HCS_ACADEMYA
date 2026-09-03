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
