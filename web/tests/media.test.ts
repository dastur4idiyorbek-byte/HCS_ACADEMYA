import assert from "node:assert/strict";
import { test } from "node:test";

import {
  MediaXatosi,
  engKattaHajm,
  mimeTuri,
  oraliqniOqi,
  turiMaqbulmi,
  videoJildi,
  videoYoli,
  yangiNom,
} from "../src/lib/media.ts";

function bilan<T>(qiymatlar: Record<string, string | undefined>, ish: () => T): T {
  const eski = { ...process.env };
  Object.assign(process.env, qiymatlar);
  try {
    return ish();
  } finally {
    process.env = eski;
  }
}

// --------------------------------------------------------------------- //
//  Jild — bot bilan BIR XIL qoida
// --------------------------------------------------------------------- //

test("video jildi baza fayli yonida turadi", () => {
  const jild = bilan({ DATABASE_URL: "sqlite+aiosqlite:////data/hcs.db" }, videoJildi);
  assert.equal(jild, "/data/video");
});

test("nisbiy baza manzili ham jildni to'g'ri beradi", () => {
  const jild = bilan({ DATABASE_URL: "sqlite+aiosqlite:///data/hcs.db" }, videoJildi);
  // Nisbiy yo'l joriy jildga nisbatan hisoblanadi, lekin oxiri
  // har doim `data/video` bo'lishi shart.
  assert.ok(jild.endsWith("/data/video"), jild);
});

// --------------------------------------------------------------------- //
//  Yo'l xavfsizligi — eng muhim qism
// --------------------------------------------------------------------- //

test("jilddan tashqariga chiqadigan nom rad etiladi", () => {
  bilan({ DATABASE_URL: "sqlite+aiosqlite:////data/hcs.db" }, () => {
    for (const yomon of [
      "../hcs.db",
      "../../etc/passwd",
      "a/b.mp4",
      "a\\b.mp4",
      "",
    ]) {
      assert.throws(() => videoYoli(yomon), MediaXatosi, `o'tkazib yubordi: ${yomon}`);
    }
  });
});

test("oddiy nom jild ichida qoladi", () => {
  bilan({ DATABASE_URL: "sqlite+aiosqlite:////data/hcs.db" }, () => {
    assert.equal(videoYoli("abc.mp4"), "/data/video/abc.mp4");
  });
});

// --------------------------------------------------------------------- //
//  Fayl turi
// --------------------------------------------------------------------- //

test("faqat brauzer o'ynay oladigan turlar qabul qilinadi", () => {
  assert.ok(turiMaqbulmi("dars.mp4"));
  assert.ok(turiMaqbulmi("DARS.MP4"));
  assert.ok(turiMaqbulmi("dars.webm"));
  assert.ok(!turiMaqbulmi("dars.avi"));
  assert.ok(!turiMaqbulmi("dars.exe"));
  assert.ok(!turiMaqbulmi("dars"));
});

test("yangi nom asl nomni tashlaydi, kengaytmani saqlaydi", () => {
  assert.equal(yangiNom("Mening darsim (1).mp4", "aaa"), "aaa.mp4");
  // Kengaytma katta harfda kelsa ham kichraytiriladi — bir xil fayl
  // ikki xil turda ko'rinmasin.
  assert.equal(yangiNom("dars.MOV", "bbb"), "bbb.mov");
});

test("noma'lum turdagi fayl yuklashda rad etiladi", () => {
  assert.throws(() => yangiNom("virus.exe"), MediaXatosi);
});

test("mime turi kengaytmadan aniqlanadi", () => {
  assert.equal(mimeTuri("a.mp4"), "video/mp4");
  assert.equal(mimeTuri("a.webm"), "video/webm");
});

// --------------------------------------------------------------------- //
//  Hajm chegarasi
// --------------------------------------------------------------------- //

test("hajm chegarasi sozlanadi, standarti 512 MB", () => {
  assert.equal(bilan({ VIDEO_MAX_MB: undefined }, engKattaHajm), 512 * 1024 * 1024);
  assert.equal(bilan({ VIDEO_MAX_MB: "100" }, engKattaHajm), 100 * 1024 * 1024);
});

test("noto'g'ri chegara JIMGINA o'tmaydi", () => {
  // Xato sozlama standart qiymatga tushib qolsa, admin chegarani
  // o'zgartirdim deb o'ylaydi-yu, aslida u ishlamaydi.
  assert.throws(() => bilan({ VIDEO_MAX_MB: "juda-kop" }, engKattaHajm), MediaXatosi);
  assert.throws(() => bilan({ VIDEO_MAX_MB: "0" }, engKattaHajm), MediaXatosi);
  assert.throws(() => bilan({ VIDEO_MAX_MB: "-5" }, engKattaHajm), MediaXatosi);
});

// --------------------------------------------------------------------- //
//  Range — videoda o'rtaga sakrash shunga bog'liq
// --------------------------------------------------------------------- //

test("sarlavha yo'q bo'lsa butun fayl beriladi", () => {
  assert.equal(oraliqniOqi(null, 1000), null);
});

test("oddiy oraliq o'qiladi", () => {
  assert.deepEqual(oraliqniOqi("bytes=0-99", 1000), { boshi: 0, oxiri: 99 });
  assert.deepEqual(oraliqniOqi("bytes=500-", 1000), { boshi: 500, oxiri: 999 });
});

test("oxiri fayl hajmidan oshsa qisqartiriladi", () => {
  assert.deepEqual(oraliqniOqi("bytes=900-5000", 1000), { boshi: 900, oxiri: 999 });
});

test("`bytes=-500` OXIRGI 500 baytni bildiradi", () => {
  // Bu — Range spetsifikatsiyasidagi eng ko'p adashtiradigan joy:
  // "0 dan 500 gacha" EMAS.
  assert.deepEqual(oraliqniOqi("bytes=-500", 1000), { boshi: 500, oxiri: 999 });
  // Fayl so'ralgandan kichik bo'lsa — boshidan beriladi, manfiy emas.
  assert.deepEqual(oraliqniOqi("bytes=-5000", 1000), { boshi: 0, oxiri: 999 });
});

test("yaroqsiz so'rovlar 416 ga olib boradi", () => {
  for (const yomon of [
    "bytes=1000-1100", // butunlay hajmdan tashqarida
    "bytes=200-100", // teskari
    "bytes=-0",
    "bytes=-",
    "baytlar=0-10",
    "bytes=0-99,200-299", // ko'p oraliq qo'llab-quvvatlanmaydi
  ]) {
    assert.equal(oraliqniOqi(yomon, 1000), "yaroqsiz", `o'tkazib yubordi: ${yomon}`);
  }
});
