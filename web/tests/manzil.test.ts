import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

/** Bu test butun BIR SINF xatoni to'sadi.
 *
 * `NextResponse.redirect(new URL("/bosh", request.url))` manzilni so'rov
 * kelgan domendan emas, serverning BOG'LANISH manzilidan quradi.
 * Railway'da server `0.0.0.0` da tinglaydi — natijada brauzerga
 * `https://0.0.0.0:8080/bosh` yuboriladi va foydalanuvchi hech qayerga
 * bora olmaydi. Sahifalar esa ishlab turaveradi, ya'ni tashqaridan
 * "kirish tugmasi buzuq" bo'lib ko'rinadi.
 *
 * ENG YOMONI: mahalliy ishlab chiqishda buni sezib bo'lmaydi —
 * `localhost` da bog'lanish manzili bilan so'rov manzili bir xil. Xato
 * faqat serverda, faqat proksi ortida ochiladi. Aynan shuning uchun uni
 * ishga tushirib emas, MANBA MATNIDAN tutamiz.
 *
 * `src/lib/manzil.ts` — yagona istisno: yo'naltirish o'sha yerda,
 * nisbiy manzil bilan quriladi.
 */

const ISTISNO = "manzil.ts";

function tsFayllar(papka: string): string[] {
  const natija: string[] = [];
  for (const band of readdirSync(papka, { withFileTypes: true })) {
    const toliq = path.join(papka, band.name);
    if (band.isDirectory()) natija.push(...tsFayllar(toliq));
    else if (/\.tsx?$/.test(band.name)) natija.push(toliq);
  }
  return natija;
}

test("birorta fayl NextResponse.redirect ishlatmaydi", () => {
  const ildiz = path.resolve(process.cwd(), "src");
  const yomonlar = tsFayllar(ildiz)
    .filter((f) => path.basename(f) !== ISTISNO)
    .filter((f) => readFileSync(f, "utf8").includes("NextResponse.redirect"))
    .map((f) => path.relative(ildiz, f));

  assert.deepEqual(
    yomonlar,
    [],
    "Bu fayllar NextResponse.redirect ishlatyapti — o'rniga " +
      `src/lib/manzil.ts dagi yonaltir() dan foydalaning:\n  ${yomonlar.join("\n  ")}`,
  );
});

test("yo'naltirish manzili so'rov URL idan qurilmaydi", () => {
  const ildiz = path.resolve(process.cwd(), "src");
  const yomonlar = tsFayllar(ildiz)
    .filter((f) => path.basename(f) !== ISTISNO)
    .filter((f) => /new URL\([^)]*request\.url/.test(readFileSync(f, "utf8")))
    .map((f) => path.relative(ildiz, f));

  assert.deepEqual(yomonlar, [], `\`new URL(..., request.url)\` topildi: ${yomonlar.join(", ")}`);
});

test("yonaltir() NISBIY manzil qaytaradi", () => {
  // `next/server` ni oddiy Node yecha olmaydi, shuning uchun manba
  // matnini tekshiramiz: manzil o'zgaruvchining O'ZI bo'lishi kerak,
  // hech qanday domen qo'shilmasligi kerak.
  const xom = readFileSync(path.resolve(process.cwd(), "src", "lib", "manzil.ts"), "utf8");
  // Izohlar olib tashlanadi: ular muammoni TUSHUNTIRADI, ya'ni ichida
  // `request.url` kabi iboralar ataylab bor.
  const kod = xom
    .split("\n")
    .filter((q) => !/^\s*(\/\/|\*|\/\*)/.test(q))
    .join("\n");

  assert.match(kod, /headers:\s*\{\s*Location:\s*yol\s*\}/, "Location to'g'ridan-to'g'ri yo'l bo'lsin");
  assert.ok(!kod.includes("request.url"), "manzil.ts so'rov URL iga tegmasligi kerak");
});
