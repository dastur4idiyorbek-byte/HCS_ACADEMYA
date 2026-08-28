import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ULUSH_JAMI,
  asosiyAktiv,
  birjaJuftligi,
  hisobla,
  musbatSon,
  narxMatni,
  tengUlushlar,
} from "../src/lib/kalkulyator.ts";

/** Topshiriqdagi misolning o'zi: $1000, kirish 100, stop 97,
 *  TP1 103 (50%), TP2 106 (30%), TP3 109 (20%). */
const MISOL = () =>
  hisobla(1000, 100, 97, [
    { narx: 103, ulush: 50 },
    { narx: 106, ulush: 30 },
    { narx: 109, ulush: 20 },
  ])!;

test("umumiy miqdor = summa / kirish narxi", () => {
  assert.equal(MISOL().umumiyMiqdor, 10);
});

test("har bir TP alohida hisoblanadi", () => {
  const h = MISOL();
  // TP1: 10 x 50% = 5 dona, 5 x 103 = 515, kirish qiymati 500 -> foyda 15
  assert.equal(h.tplar[0].miqdor, 5);
  assert.equal(h.tplar[0].tushum, 515);
  assert.ok(Math.abs(h.tplar[0].foyda - 15) < 1e-9);
  // TP2: 3 dona, 318 - 300 = 18
  assert.ok(Math.abs(h.tplar[1].foyda - 18) < 1e-9);
  // TP3: 2 dona, 218 - 200 = 18
  assert.ok(Math.abs(h.tplar[2].foyda - 18) < 1e-9);
});

/** Foiz — narx harakati, ya'ni ULUSHGA bog'liq emas. Ulushni
 *  o'zgartirsak foyda summasi o'zgaradi, foiz esa o'sha-o'sha qoladi. */
test("TP foizi ulushga bog'liq emas", () => {
  const h = MISOL();
  assert.ok(Math.abs(h.tplar[0].foizOzgarish - 3) < 1e-9);
  assert.ok(Math.abs(h.tplar[2].foizOzgarish - 9) < 1e-9);

  const boshqa = hisobla(1000, 100, 97, [{ narx: 103, ulush: 10 }])!;
  assert.ok(
    Math.abs(boshqa.tplar[0].foizOzgarish - 3) < 1e-9,
    "ulush 50% dan 10% ga tushsa ham foiz o'zgarmasligi kerak",
  );
});

test("jami foyda va uning foizi", () => {
  const h = MISOL();
  assert.ok(Math.abs(h.jamiFoyda - 51) < 1e-9);
  assert.ok(Math.abs(h.jamiFoiz - 5.1) < 1e-9);
});

/** Stop butun pozitsiyaga qo'llanadi — TP ulushlaridan qat'i nazar.
 *  Aks holda kalkulyator zararni kam ko'rsatib, xavfni yashirardi. */
test("Stop butun pozitsiyaga hisoblanadi", () => {
  const h = MISOL();
  assert.ok(Math.abs(h.stopZarar - 30) < 1e-9, "10 dona x (100-97) = 30");
  assert.ok(Math.abs(h.stopFoiz - -3) < 1e-9);
});

test("ulushlar yig'indisi tekshiriladi", () => {
  assert.equal(MISOL().toliqmi, true);
  const kam = hisobla(1000, 100, 97, [{ narx: 103, ulush: 40 }])!;
  assert.equal(kam.toliqmi, false);
  assert.equal(kam.ulushJami, 40);
});

test("teng bo'lishda qoldiq yo'qolmaydi", () => {
  for (const n of [1, 2, 3, 4, 7]) {
    const u = tengUlushlar(n);
    assert.equal(u.length, n);
    const jami = u.reduce((a, b) => a + b, 0);
    assert.ok(Math.abs(jami - ULUSH_JAMI) < 1e-9, `${n} ta TP: ${u} -> ${jami}`);
  }
});

test("yaroqsiz kiritmada hisob qaytmaydi", () => {
  assert.equal(hisobla(0, 100, 97, []), null);
  assert.equal(hisobla(1000, 0, 97, []), null);
  assert.equal(hisobla(Number.NaN, 100, 97, []), null);
});

test("musbatSon bo'sh va nol qiymatni rad etadi", () => {
  assert.equal(musbatSon(""), null);
  assert.equal(musbatSon("0"), null);
  assert.equal(musbatSon("-5"), null);
  assert.equal(musbatSon("abc"), null);
  assert.equal(musbatSon("1 234,56"), 1234.56);
  assert.equal(musbatSon(12), 12);
});

test("asosiy aktiv juftlikdan ajratiladi", () => {
  assert.equal(asosiyAktiv("BTCUSDT"), "BTC");
  assert.equal(asosiyAktiv("ETHUSDT"), "ETH");
  assert.equal(asosiyAktiv("BTC"), "BTC", "kotirovkasiz nom o'zgarmaydi");
  assert.equal(asosiyAktiv("USDT"), "USDT", "faqat kotirovkaning o'zi bo'lsa kesilmaydi");
});

test("TP soni moslashuvchan — 2 ta ham, 4 ta ham ishlaydi", () => {
  for (const soni of [2, 3, 4]) {
    const ulushlar = tengUlushlar(soni);
    const h = hisobla(
      1000, 100, 97,
      ulushlar.map((u, i) => ({ narx: 105 + i, ulush: u })),
    )!;
    assert.equal(h.tplar.length, soni);
    assert.equal(h.toliqmi, true);
  }
});

// --------------------------------------------------------------------- //
//  Birja juftligi — grafik shunga bog'liq
// --------------------------------------------------------------------- //

/** ISHLAB CHIQARISHDAGI SHAKL: bazada `symbol` — ASOSIY AKTIV (`DOT`),
 *  juftlik emas. Bot uni `quote_asset` bilan qo'shib yasaydi
 *  (`core/halal_screening/screener.py` -> `pair_for()`).
 *
 *  Bu testlar aynan shu sababdan yozildi: grafikka `BINANCE:DOT`
 *  berilgan edi va TradingView "This symbol doesn't exist" deb turdi.
 *  Mahalliy sinov bazasida coinlar `BTCUSDT` deb yozilgani uchun xato
 *  ko'rinmadi — sinov ma'lumoti haqiqatdan boshqacha edi. */
test("asosiy aktivdan birja juftligi yasaladi", () => {
  assert.equal(birjaJuftligi("DOT"), "DOTUSDT");
  assert.equal(birjaJuftligi("BTC"), "BTCUSDT");
  assert.equal(birjaJuftligi("dot"), "DOTUSDT");
});

test("juftlik allaqachon berilgan bo'lsa ikkinchi marta qo'shilmaydi", () => {
  // Ikkala shakl ham kelishi mumkin, natija bir xil bo'lishi shart.
  assert.equal(birjaJuftligi("DOTUSDT"), "DOTUSDT");
  assert.equal(birjaJuftligi("BTCUSDT"), "BTCUSDT");
});

test("boshqa kotirovka ham ishlaydi", () => {
  assert.equal(birjaJuftligi("DOT", "USDC"), "DOTUSDC");
  assert.equal(birjaJuftligi("DOTUSDC", "USDC"), "DOTUSDC");
});

// --------------------------------------------------------------------- //
//  Narx matni — maydonga tushadigan qiymat
// --------------------------------------------------------------------- //

test("narx kattaligiga qarab kasr xonalari tanlanadi", () => {
  assert.equal(narxMatni(0.8294354680460917), "0.829435");
  assert.equal(narxMatni(61250.5), "61250.5");
  assert.equal(narxMatni(17.42), "17.42");
  assert.equal(narxMatni(0.0001234567), "0.00012346");
});

test("narx matnida guruh ajratgichi YO'Q", () => {
  // Vergul bo'lsa, `musbatSon()` uni kasr belgisi deb o'qib yuboradi
  // va "1,150.74" -> "1.150.74" -> NaN bo'lardi.
  const matn = narxMatni(1150.74798619);
  assert.ok(!matn.includes(","), matn);
  assert.equal(musbatSon(matn), 1150.75);
});
