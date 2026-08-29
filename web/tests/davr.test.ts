import assert from "node:assert/strict";
import { test } from "node:test";

import { CHORAKLAR, davr, keyingiDavr } from "../src/lib/davr.ts";

/** MANBA: `core/analysis/market_health/quarterly.py`.
 *
 * Bu chegaralar Python tomonda ham tekshiriladi
 * (`tests/core/test_score_bonuses.py`). Biri o'zgarsa, ikkinchisi
 * yiqiladi — ya'ni ikki nusxa jimgina ajralib keta olmaydi.
 */
const vaqt = (soat: number) => new Date(Date.UTC(2026, 7, 21, soat));

test("sutka to'rt chorakka bo'linadi", () => {
  assert.equal(CHORAKLAR, 4);
  assert.equal(davr(vaqt(0)), "A");
  assert.equal(davr(vaqt(5)), "A");
  assert.equal(davr(vaqt(6)), "M");
  assert.equal(davr(vaqt(11)), "M");
  assert.equal(davr(vaqt(12)), "D");
  assert.equal(davr(vaqt(17)), "D");
  assert.equal(davr(vaqt(18)), "X");
  assert.equal(davr(vaqt(23)), "X");
});

test("davrlar aylanma tartibda", () => {
  assert.equal(keyingiDavr("A"), "M");
  assert.equal(keyingiDavr("M"), "D");
  assert.equal(keyingiDavr("D"), "X");
  assert.equal(keyingiDavr("X"), "A");
});

test("mahalliy vaqt emas, UTC ishlatiladi", () => {
  // Server qaysi mintaqada turishidan qat'i nazar natija bir xil
  // bo'lishi kerak: bot ham UTC da hisoblaydi.
  const utc = new Date("2026-08-21T14:00:00Z");
  assert.equal(davr(utc), "D");
});

test("har bir soat uchun davr aniqlanadi", () => {
  for (let soat = 0; soat < 24; soat += 1) {
    assert.ok(["A", "M", "D", "X"].includes(davr(vaqt(soat))), `soat ${soat}`);
  }
});
