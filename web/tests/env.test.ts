import assert from "node:assert/strict";
import { test } from "node:test";

import { sqliteYoli } from "../src/lib/env.ts";

/** SQLAlchemy manzilida UCH va TO'RT qiyshiq chiziq boshqa-boshqa
 *  ma'noni bildiradi. Bu farqni chalkashtirsak, sayt bazani topolmaydi
 *  yoki bundan ham yomoni — BOSHQA fayl ochib, bo'sh ma'lumot ko'rsatadi.
 *
 *  Bu test bir marta haqiqiy xatoni tutdi: dastlabki kodda
 *  `const [, , yol] = url.split(":///")` yozilgan edi — massivda esa
 *  atigi 2 element bor, ya'ni natija doim `undefined` edi. Xato
 *  ko'rinmadi, chunki zaxira yo'l MUTLAQ manzillar uchun tasodifan
 *  to'g'ri ishlardi va testda aynan mutlaq manzil ishlatilgandi. */
test("uch chiziq — nisbiy yo'l", () => {
  assert.equal(sqliteYoli("sqlite+aiosqlite:///data/hcs.db"), "data/hcs.db");
  assert.equal(sqliteYoli("sqlite:///data/hcs.db"), "data/hcs.db");
});

test("to'rt chiziq — mutlaq yo'l (Railway shu variantni beradi)", () => {
  assert.equal(sqliteYoli("sqlite+aiosqlite:////data/hcs.db"), "/data/hcs.db");
  assert.equal(sqliteYoli("sqlite+aiosqlite:////tmp/x/test.db"), "/tmp/x/test.db");
});

test("`..` bilan boshlanuvchi nisbiy yo'l saqlanadi", () => {
  assert.equal(sqliteYoli("sqlite+aiosqlite:///../data/hcs.db"), "../data/hcs.db");
});

test("bo'sh qiymatda standart yo'l", () => {
  assert.equal(sqliteYoli(undefined), "data/hcs.db");
  assert.equal(sqliteYoli("  "), "data/hcs.db");
});

test("SQLite bo'lmagan manzil aniq xato beradi", () => {
  assert.throws(
    () => sqliteYoli("postgresql+asyncpg://u:p@host/db"),
    /SQLite emas/,
    "Postgres manzili jimgina qabul qilinmasligi kerak",
  );
});
