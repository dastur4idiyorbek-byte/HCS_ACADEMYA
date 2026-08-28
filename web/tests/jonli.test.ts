import assert from "node:assert/strict";
import { test } from "node:test";

import { ozgarishFoizi } from "../src/lib/jonli.ts";

/** Bu foiz — foydalanuvchi ko'radigan YASHIL yoki QIZIL raqam.
 *  Belgisi teskari bo'lsa, u zararni foyda deb o'qirdi. */

test("yuqoriga yurgan narx MUSBAT foiz beradi", () => {
  assert.equal(ozgarishFoizi(100, 105), 5);
  assert.equal(ozgarishFoizi(0.869, 0.9124)?.toFixed(2), "4.99");
});

test("pastga yurgan narx MANFIY foiz beradi", () => {
  assert.equal(ozgarishFoizi(100, 95), -5);
  assert.equal(ozgarishFoizi(1481.17, 1466.36)?.toFixed(2), "-1.00");
});

test("narx o'zgarmagan bo'lsa nol", () => {
  assert.equal(ozgarishFoizi(100, 100), 0);
});

test("arzon coinda ham aniq", () => {
  // 0.0581 -> 0.0587 = +1.03%
  assert.equal(ozgarishFoizi(0.0581, 0.0587)?.toFixed(2), "1.03");
});

test("mantiqsiz kirishda null", () => {
  // Nol yoki manfiy kirish narxi bo'lishi mumkin emas — bunda foiz
  // ham ma'noga ega emas. "0.00%" ko'rsatish YOLG'ON bo'lardi: u
  // "narx o'zgarmadi" degan ma'noni beradi.
  assert.equal(ozgarishFoizi(0, 100), null);
  assert.equal(ozgarishFoizi(-5, 100), null);
  assert.equal(ozgarishFoizi(100, Number.NaN), null);
  assert.equal(ozgarishFoizi(Number.NaN, 100), null);
});
