import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import {
  chiziqMaydoni,
  chiziqNuqtalari,
  foizRangi,
  narxMatn,
  qisqaSon,
  sarala,
  treemap,
  xaritaUlushi,
  type CoinHolati,
} from "../src/lib/bozor.ts";
import { COINGECKO_ID, TEKSHIRILMAGAN } from "../src/lib/coingecko-id.ts";

function coin(qism: Partial<CoinHolati>): CoinHolati {
  return {
    ticker: "X",
    nom: "X",
    logo: null,
    narx: null,
    ozgarish24: null,
    ozgarish7k: null,
    kapital: null,
    hajm24: null,
    chiziq: [],
    ...qism,
  };
}

// --------------------------------------------------------------------- //
//  Jadval kuzatiladigan ro'yxat bilan bir qadamda yursin
// --------------------------------------------------------------------- //

/** `core/config/schema.py` dagi 80 talikni o'qiydi. */
function kuzatiladiganCoinlar(): string[] {
  const sxema = readFileSync(
    path.join(import.meta.dirname, "..", "..", "core", "config", "schema.py"),
    "utf8",
  );
  const boshi = sxema.indexOf("kuzatiladigan_coinlar");
  assert.ok(boshi > 0, "schema.py da kuzatiladigan_coinlar topilmadi");

  const ochilish = sxema.indexOf("default_factory=lambda: [", boshi);
  assert.ok(ochilish > 0, "ro'yxat boshlanishi topilmadi");

  let chuqurlik = 0;
  let i = sxema.indexOf("[", ochilish);
  const bosh = i;
  for (; i < sxema.length; i++) {
    if (sxema[i] === "[") chuqurlik++;
    else if (sxema[i] === "]") {
      chuqurlik--;
      if (chuqurlik === 0) break;
    }
  }
  return [...sxema.slice(bosh, i).matchAll(/"([A-Z0-9]+)"/g)].map((m) => m[1]);
}

/** Jadval ro'yxatdan ORQADA QOLMASIN.
 *
 * Ro'yxatga yangi coin qo'shilib jadvalga unutilsa, u saytda
 * abadiy "ma'lumot yo'q" bo'lib turadi va sabab hech qayerda
 * ko'rinmaydi — xato ham bermaydi, log ham yozmaydi. Shuning uchun
 * bog'lanish shu yerda mexanik tekshiriladi.
 */
test("COINGECKO_ID kuzatiladigan har bir coinni qamraydi", () => {
  const yoq = kuzatiladiganCoinlar().filter((t) => !(t in COINGECKO_ID));
  assert.deepEqual(
    yoq,
    [],
    `bu coinlarning CoinGecko id si yozilmagan: ${yoq.join(", ")}`,
  );
});

test("jadvalda ortiqcha coin yo'q", () => {
  const kerak = new Set(kuzatiladiganCoinlar());
  const ortiqcha = Object.keys(COINGECKO_ID).filter((t) => !kerak.has(t));
  assert.deepEqual(
    ortiqcha,
    [],
    `bu coinlar ro'yxatdan chiqarilgan, jadvaldan ham chiqsin: ${ortiqcha.join(", ")}`,
  );
});

/** Bir xil `id` ikki tickerga berilsa, ikkalasida bitta coin narxi
 *  chiqadi va bu jimgina yuz beradi. */
test("ikki ticker bitta CoinGecko id ga ishora qilmaydi", () => {
  const korgan = new Map<string, string>();
  const takror: string[] = [];
  for (const [ticker, id] of Object.entries(COINGECKO_ID)) {
    const avvalgi = korgan.get(id);
    if (avvalgi !== undefined) takror.push(`${avvalgi} va ${ticker} -> ${id}`);
    else korgan.set(id, ticker);
  }
  assert.deepEqual(takror, []);
});

test("TEKSHIRILMAGAN ro'yxatidagilar jadvalda mavjud", () => {
  const yetim = [...TEKSHIRILMAGAN].filter((t) => !(t in COINGECKO_ID));
  assert.deepEqual(yetim, [], `jadvalda yo'q: ${yetim.join(", ")}`);
});

// --------------------------------------------------------------------- //
//  Saralash
// --------------------------------------------------------------------- //

/** `null` — "ma'lumot olinmadi", nol emas. Nol deb saralansa, narxi
 *  olinmagan coin "eng arzon" bo'lib ro'yxat boshiga chiqib qolardi. */
test("ma'lumoti yo'q coin saralashda oxirida qoladi", () => {
  const royxat = [
    coin({ ticker: "A", kapital: 100 }),
    coin({ ticker: "B", kapital: null }),
    coin({ ticker: "C", kapital: 900 }),
  ];

  assert.deepEqual(
    sarala(royxat, "kapital").map((c) => c.ticker),
    ["C", "A", "B"],
  );
  // O'sish tartibida ham `null` oxirida — boshida emas.
  assert.deepEqual(
    sarala(royxat, "kapital", true).map((c) => c.ticker),
    ["A", "C", "B"],
  );
});

test("saralash asl ro'yxatni o'zgartirmaydi", () => {
  const royxat = [coin({ ticker: "A" }), coin({ ticker: "B" })];
  sarala(royxat, "narx");
  assert.deepEqual(
    royxat.map((c) => c.ticker),
    ["A", "B"],
  );
});

// --------------------------------------------------------------------- //
//  Ko'rsatish
// --------------------------------------------------------------------- //

/** Nol atrofidagi tebranish o'sish ham, tushish ham emas — shovqin.
 *  Uni yashil qilish foydalanuvchini adashtiradi. */
test("kichik tebranish neytral qoladi", () => {
  assert.equal(foizRangi(0.05), "neytral");
  assert.equal(foizRangi(-0.05), "neytral");
  assert.equal(foizRangi(2), "yaxshi");
  assert.equal(foizRangi(-2), "past");
  assert.equal(foizRangi(null), "neytral");
});

test("ma'lumot yo'qligi nol emas, chiziqcha", () => {
  assert.equal(qisqaSon(null), "—");
  assert.equal(narxMatn(null), "—");
});

test("katta son qisqaradi", () => {
  assert.equal(qisqaSon(1_234_000_000_000), "1.23T");
  assert.equal(qisqaSon(2_500_000_000), "2.50B");
  assert.equal(qisqaSon(7_800_000), "7.80M");
  assert.equal(qisqaSon(-3_000), "-3.00K");
});

/** Arzon coinda ikki xona yetmaydi: $0.00 narx emas, xato. */
test("arzon coin narxi nolga aylanmaydi", () => {
  assert.equal(narxMatn(0.00001234), "$0.00001234");
  assert.equal(narxMatn(0.0456), "$0.0456");
  assert.equal(narxMatn(12.3456), "$12.35");
});

// --------------------------------------------------------------------- //
//  Xarita va grafik
// --------------------------------------------------------------------- //

/** Kapital farqi juda katta. To'g'ridan-to'g'ri ulushda BTC butun
 *  ekranni egallardi, shuning uchun kvadrat ildiz olinadi. */
test("xarita ulushi kichik coinni ko'rinmas qilmaydi", () => {
  const katta = xaritaUlushi(9_000, 10_000);
  const kichik = xaritaUlushi(100, 10_000);
  assert.ok(kichik > 100 / 10_000, "kichik coin ulushi kattalashishi kerak");
  assert.ok(katta < 1);
  assert.equal(xaritaUlushi(null, 10_000), 0);
  assert.equal(xaritaUlushi(500, 0), 0);
});

test("bitta nuqtadan grafik chiqmaydi", () => {
  assert.equal(chiziqNuqtalari([], 100, 30), null);
  assert.equal(chiziqNuqtalari([5], 100, 30), null);
});

test("tekis chiziq o'rtadan o'tadi", () => {
  const nuqtalar = chiziqNuqtalari([7, 7, 7], 100, 30);
  assert.ok(nuqtalar !== null);
  for (const juft of nuqtalar.split(" ")) {
    assert.equal(juft.split(",")[1], "15.00");
  }
});

test("grafik nuqtalari chegaradan chiqmaydi", () => {
  const nuqtalar = chiziqNuqtalari([1, 5, 3, 9, 2], 120, 40);
  assert.ok(nuqtalar !== null);
  for (const juft of nuqtalar.split(" ")) {
    const [x, y] = juft.split(",").map(Number);
    assert.ok(x >= 0 && x <= 120, `x chegaradan chiqdi: ${x}`);
    assert.ok(y >= 0 && y <= 40, `y chegaradan chiqdi: ${y}`);
  }
});

// --------------------------------------------------------------------- //
//  Treemap
// --------------------------------------------------------------------- //

/** Katakchalar bir-birining ustiga chiqmasligi va maydon ulushi
 *  og'irlikka mos bo'lishi — xaritaning butun ma'nosi shunda. */
test("treemap maydonlari og'irlikka mos", () => {
  const kataklar = treemap([
    { kalit: "A", ogirlik: 50 },
    { kalit: "B", ogirlik: 30 },
    { kalit: "C", ogirlik: 20 },
  ]);
  assert.equal(kataklar.length, 3);

  const jamiMaydon = kataklar.reduce((s, k) => s + k.en * k.boy, 0);
  const a = kataklar.find((k) => k.kalit === "A")!;
  const c = kataklar.find((k) => k.kalit === "C")!;

  // A ning maydoni C nikidan ~2.5 barobar katta bo'lishi kerak.
  const nisbat = (a.en * a.boy) / (c.en * c.boy);
  assert.ok(nisbat > 2.2 && nisbat < 2.8, `nisbat: ${nisbat}`);
  // Butun maydon to'ldirilgan (100 x 100), kichik xatolik bilan.
  assert.ok(Math.abs(jamiMaydon - 10_000) < 50, `jami: ${jamiMaydon}`);
});

test("treemap katakchalari chegaradan chiqmaydi", () => {
  const kataklar = treemap(
    Array.from({ length: 24 }, (_, i) => ({
      kalit: `K${i}`,
      ogirlik: (24 - i) ** 2,
    })),
  );
  for (const k of kataklar) {
    assert.ok(k.x >= -0.01 && k.x + k.en <= 100.01, `x: ${k.x} + ${k.en}`);
    assert.ok(k.y >= -0.01 && k.y + k.boy <= 100.01, `y: ${k.y} + ${k.boy}`);
  }
});

/** Kattaroq element HAR DOIM kattaroq maydon olsin — aks holda
 *  xarita yolg'on gapiradi. */
test("kattaroq og'irlik kattaroq maydon oladi", () => {
  const kataklar = treemap([
    { kalit: "kichik", ogirlik: 5 },
    { kalit: "katta", ogirlik: 95 },
  ]);
  const kichik = kataklar.find((k) => k.kalit === "kichik")!;
  const katta = kataklar.find((k) => k.kalit === "katta")!;
  assert.ok(katta.en * katta.boy > kichik.en * kichik.boy);
});

test("nol va manfiy og'irlik xaritaga tushmaydi", () => {
  const kataklar = treemap([
    { kalit: "A", ogirlik: 10 },
    { kalit: "B", ogirlik: 0 },
    { kalit: "C", ogirlik: -5 },
  ]);
  assert.deepEqual(
    kataklar.map((k) => k.kalit),
    ["A"],
  );
});

test("bo'sh ro'yxatdan xarita chiqmaydi", () => {
  assert.deepEqual(treemap([]), []);
});

test("to'ldirilgan grafik yopiq yo'l qaytaradi", () => {
  const yol = chiziqMaydoni([1, 3, 2], 100, 30);
  assert.ok(yol !== null);
  assert.ok(yol.startsWith("M0,30"), yol);
  assert.ok(yol.endsWith("Z"), yol);
  assert.equal(chiziqMaydoni([7], 100, 30), null);
});
