import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import { KITOB_BOLIMLARI, KITOB_FAYLI, KITOB_TARIFI } from "../src/lib/kitob.ts";
import { MENYU } from "../src/lib/menyu.ts";

// --------------------------------------------------------------------------- //
//  Kitob himoyasi
// --------------------------------------------------------------------------- //

test("kitob fayli `public/` da TURMAYDI", () => {
  // ENG MUHIM TEKSHIRUV. `public/` ichidagi fayl manzilini bilgan har
  // kimga ochiq bo'ladi — obuna tekshiruvi butunlay chetlab o'tilardi.
  // Video darsliklar ham aynan shu sababdan `api/video` orqali
  // beriladi; kitob undan farq qilmasligi kerak.
  const ochiq = path.resolve(import.meta.dirname, "..", "public", KITOB_FAYLI);
  assert.equal(
    existsSync(ochiq),
    false,
    `Kitob ${ochiq} da turibdi — u hammaga ochiq bo'lib qoladi.`,
  );
  const ochiqJild = path.resolve(import.meta.dirname, "..", "public", "kitob");
  assert.equal(existsSync(ochiqJild), false, "public/kitob/ bo'lmasligi kerak");
});

test("kitob fayli himoyalangan jildda turibdi", () => {
  const yol = path.resolve(import.meta.dirname, "..", "kitob", KITOB_FAYLI);
  assert.ok(existsSync(yol), `Kitob topilmadi: ${yol}`);
});

test("yuklash yo'li obunani tekshiradi", () => {
  // Kodni O'QIB tekshiramiz: HTTP so'rovsiz ham darvoza borligiga
  // ishonch hosil qilish kerak. Kimdir tekshiruvni olib tashlasa,
  // shu test yiqiladi.
  const manba = readFileSync(
    path.resolve(import.meta.dirname, "..", "src", "app", "api", "kitob", "route.ts"),
    "utf8",
  );
  assert.match(manba, /tarifQamraydi\(tarif, KITOB_TARIFI\)/);
  assert.match(manba, /status:\s*403/);
});

test("menyudagi band ham o'sha tarifni talab qiladi", () => {
  // Ikki joyda ikki xil tarif bo'lsa, menyuda ko'rinadigan, lekin
  // ochilmaydigan bo'lim paydo bo'lardi.
  const band = MENYU.find((b) => b.kod === "kitob");
  assert.ok(band, "menyuda kitob bandi yo'q");
  assert.equal(band.talab, KITOB_TARIFI);
});

test("kitob tarkibi barcha olti bo'limni qamraydi", () => {
  assert.equal(KITOB_BOLIMLARI.length, 6);
  const boblar = KITOB_BOLIMLARI.map((b) => b.boblar).join(" ");
  for (const bob of ["1–7", "8–10", "11–16", "17–18", "19–20", "21–23"]) {
    assert.ok(boblar.includes(bob), `tarkibda ${bob} yo'q`);
  }
});
