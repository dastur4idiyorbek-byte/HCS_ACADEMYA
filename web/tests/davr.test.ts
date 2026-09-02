import assert from "node:assert/strict";
import { test } from "node:test";

import { TARTIB, davrmi, keyingiDavr } from "../src/lib/davr.ts";

/** Davr endi SOATDAN hisoblanmaydi — u bazadan HARF sifatida keladi.
 *  Bu yerda faqat ko'rsatish yordamchilari sinaladi. */

test("AMDX tartibi aylanma", () => {
  assert.deepEqual(TARTIB, ["A", "M", "D", "X"]);
  assert.equal(keyingiDavr("A"), "M");
  assert.equal(keyingiDavr("X"), "A");
});

test("noma'lum qiymat davr deb qabul qilinmaydi", () => {
  // Bazada `NULL` bo'lishi mumkin (davr aniqlanmagan) — u holda
  // sahifa "aniqlanmadi" deb yozadi, davr O'YLAB TOPILMAYDI.
  assert.equal(davrmi("A"), true);
  assert.equal(davrmi(null), false);
  assert.equal(davrmi("Z"), false);
  assert.equal(davrmi(""), false);
});
