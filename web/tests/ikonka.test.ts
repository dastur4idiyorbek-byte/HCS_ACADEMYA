import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import { MENYU, PASTKI_TABLAR } from "../src/lib/menyu.ts";

/** HCS ikonka tizimi — to'plam va uni chaqiruvchilar ajralib
 *  ketmasin.
 *
 * Ikonka nomi TypeScript tipida qulflangan (`IkonkaNomi`), ya'ni
 * mavjud bo'lmagan nom kompilyatsiyada tutiladi. Bu testlar esa
 * TIP TUTA OLMAYDIGAN narsalarni tekshiradi: chizmasi bormi,
 * chaqiruvchida jadval to'liqmi, va emoji qaytib kelmadimi.
 */

const IKONKA_FAYLI = path.join(
  import.meta.dirname,
  "..",
  "src",
  "components",
  "ui",
  "Ikonka.tsx",
);
const manba = readFileSync(IKONKA_FAYLI, "utf8");

/** `nom: (` ko'rinishidagi chizma kalitlari. */
const CHIZMALAR = [...manba.matchAll(/^ {2}([a-z_0-9]+): \(/gm)].map(
  (m) => m[1],
);

test("ikonka to'plami bo'sh emas va nomlar takrorlanmaydi", () => {
  assert.ok(CHIZMALAR.length > 40, `faqat ${CHIZMALAR.length} ta ikonka`);
  assert.equal(new Set(CHIZMALAR).size, CHIZMALAR.length, "nom takrorlandi");
});

/** Menyudagi har bir band ikonkasiz qolmasin. */
test("menyudagi har bir bandning ikonkasi mavjud", () => {
  const bor = new Set(CHIZMALAR);
  const yoq = MENYU.filter((b) => !bor.has(b.belgi));
  assert.deepEqual(
    yoq.map((b) => `${b.kod}: ${b.belgi}`),
    [],
  );
});

/** Pastki navdagi jadval to'liq bo'lsin.
 *
 * Tab qo'shilib, jadvalga yozilmasa, TypeScript indamaydi
 * (`Record<string, ...>` har qanday kalitni qabul qiladi) va
 * telefonda o'sha tab BO'SH JOY bilan chiqardi. */
test("har bir pastki tabning ikonkasi bor", () => {
  const nav = readFileSync(
    path.join(import.meta.dirname, "..", "src", "components", "PastkiNav.tsx"),
    "utf8",
  );
  const yoq = PASTKI_TABLAR.filter((tab) => !nav.includes(`  ${tab.kod}: "`));
  assert.deepEqual(
    yoq.map((t) => t.kod),
    [],
  );
});

/** Emoji QAYTIB KELMASIN.
 *
 * Sabab `ui/Ikonka.tsx` da: emoji har platformada boshqacha
 * chiziladi va bizning palitramizga bo'ysunmaydi. Bitta joyda
 * qaytib paydo bo'lsa, to'plam "bir joydan yig'ilgan" ko'rinishini
 * yo'qotadi.
 *
 * ISTISNO: `lib/format.ts` dagi `HOLAT_BELGISI` — u TELEGRAM uchun,
 * bot SVG chiza olmaydi. */
const EMOJI = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}]/u;
const ISTISNO = new Set(["src/lib/format.ts"]);

function fayllar(jild: string): string[] {
  const natija: string[] = [];
  for (const nom of readdirSync(jild)) {
    const toliq = path.join(jild, nom);
    if (statSync(toliq).isDirectory()) natija.push(...fayllar(toliq));
    else if (/\.tsx?$/.test(nom)) natija.push(toliq);
  }
  return natija;
}

test("interfeys kodida emoji qolmadi", () => {
  const ildiz = path.join(import.meta.dirname, "..");
  const buzuq: string[] = [];
  for (const fayl of fayllar(path.join(ildiz, "src"))) {
    const nisbiy = path.relative(ildiz, fayl).split(path.sep).join("/");
    if (ISTISNO.has(nisbiy)) continue;
    const qatorlar = readFileSync(fayl, "utf8").split("\n");
    qatorlar.forEach((q, i) => {
      // Izohlar hisobga olinmaydi — ular ekranga chiqmaydi
      const toza = q.trim();
      if (toza.startsWith("*") || toza.startsWith("//")) return;
      if (EMOJI.test(q)) buzuq.push(`${nisbiy}:${i + 1}: ${toza.slice(0, 60)}`);
    });
  }
  assert.deepEqual(buzuq, []);
});
