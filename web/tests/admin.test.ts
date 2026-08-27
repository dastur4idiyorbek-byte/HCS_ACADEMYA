import assert from "node:assert/strict";
import { test } from "node:test";

import { bazadanNusxa } from "./nusxa.ts";

const vaqtinchalik = bazadanNusxa("hcs-admin-");
process.env.DATABASE_URL = `sqlite+aiosqlite:///${vaqtinchalik}`;

const { db } = await import("../src/lib/db.ts");
const {
  coinQarorlari,
  coinQaroriniBelgila,
  coinQaroriniOchir,
  narxlar,
  narxniYangila,
} = await import("../src/lib/queries.ts");

const ADMIN = 5000002;

// --------------------------------------------------------------------------- //
//  Narxlar
// --------------------------------------------------------------------------- //

test("mavjud narx yangilanadi, dublikat yaratilmaydi", () => {
  const oldin = narxlar().filter((n) => n.tier === "pro" && n.period === "monthly");
  assert.ok(oldin.length > 0, "seed narxlari bo'lishi kerak");
  const valyuta = oldin[0].currency;

  assert.deepEqual(narxniYangila("pro", "monthly", valyuta, 123456, null), { ok: true });

  const keyin = narxlar().filter(
    (n) => n.tier === "pro" && n.period === "monthly" && n.currency === valyuta,
  );
  assert.equal(keyin.length, 1, "bir tarif+muddat+valyuta uchun bitta qator");
  assert.equal(keyin[0].amount, 123456);
});

test("yangi valyuta uchun narx qo'shiladi", () => {
  assert.deepEqual(narxniYangila("lite", "daily", "USDT", 3, "TRC20: T..."), { ok: true });
  const n = narxlar().find(
    (x) => x.tier === "lite" && x.period === "daily" && x.currency === "USDT",
  );
  assert.equal(n?.amount, 3);
  assert.equal(n?.paymentDetails, "TRC20: T...");
});

/** Botda `PriceRepository.upsert` manfiy narxda `ValueError` beradi.
 *  Sayt ham xuddi shu qoidaga bo'ysunishi kerak, aks holda veb orqali
 *  0 so'mlik tarif yaratib qo'yish mumkin bo'lardi. */
test("nol va manfiy narx RAD ETILADI", () => {
  for (const summa of [0, -1, Number.NaN, Number.POSITIVE_INFINITY]) {
    const natija = narxniYangila("pro", "monthly", "KGS", summa, null);
    assert.equal(natija.ok, false, `${summa} qabul qilinmasligi kerak`);
  }
});

test("noma'lum muddat rad etiladi", () => {
  assert.equal(narxniYangila("pro", "yillik", "KGS", 100, null).ok, false);
});

test("to'lov rekvizitlari bo'sh berilsa eskisi saqlanadi", () => {
  narxniYangila("premium", "monthly", "KGS", 5000, "Karta: 1234");
  narxniYangila("premium", "monthly", "KGS", 6000, null);
  const n = narxlar().find(
    (x) => x.tier === "premium" && x.period === "monthly" && x.currency === "KGS",
  );
  assert.equal(n?.amount, 6000);
  assert.equal(n?.paymentDetails, "Karta: 1234", "rekvizit yo'qolmasligi kerak");
});

// --------------------------------------------------------------------------- //
//  Halol ro'yxat
// --------------------------------------------------------------------------- //

test("coin qarori yoziladi va yangilanadi", () => {
  assert.deepEqual(
    coinQaroriniBelgila("xyztest", "haram", "Qimor platformasi", ADMIN),
    { ok: true },
  );
  let q = coinQarorlari().find((x) => x.symbol === "XYZTEST");
  assert.equal(q?.status, "haram");
  assert.equal(q?.setBy, ADMIN);

  coinQaroriniBelgila("XYZTEST", "mashbooh", "Qayta ko'rib chiqildi", ADMIN);
  q = coinQarorlari().find((x) => x.symbol === "XYZTEST");
  assert.equal(q?.status, "mashbooh");
  assert.equal(q?.reason, "Qayta ko'rib chiqildi");
  assert.equal(
    coinQarorlari().filter((x) => x.symbol === "XYZTEST").length,
    1,
    "dublikat yaratilmasligi kerak",
  );
});

/** `reason` bazada nullable EMAS. Bo'sh sababni o'tkazib yuborsak,
 *  oradan olti oy o'tib "bu coin nega harom deb belgilangan?" degan
 *  savolga javob qolmaydi. */
test("sababsiz qaror qabul qilinmaydi", () => {
  assert.equal(coinQaroriniBelgila("ABC", "haram", "", ADMIN).ok, false);
  assert.equal(coinQaroriniBelgila("ABC", "haram", "   ", ADMIN).ok, false);
  assert.ok(!coinQarorlari().some((x) => x.symbol === "ABC"));
});

test("noto'g'ri symbol rad etiladi", () => {
  for (const yomon of ["", "A", "BTC USDT", "BTC'; drop table users;--", "üü"]) {
    assert.equal(
      coinQaroriniBelgila(yomon, "halal", "sabab", ADMIN).ok,
      false,
      `${yomon} qabul qilinmasligi kerak`,
    );
  }
  // Jadval hali joyidami — SQL in'ektsiyasi o'tmaganini tekshiramiz
  assert.ok((db().prepare("select count(*) c from users").get() as { c: number }).c >= 0);
});

test("symbol katta harfga keltiriladi", () => {
  coinQaroriniBelgila("  doge  ", "halal", "Foizsiz", ADMIN);
  assert.ok(coinQarorlari().some((x) => x.symbol === "DOGE"));
});

test("qaror o'chiriladi", () => {
  coinQaroriniBelgila("TESTDEL", "haram", "sinov", ADMIN);
  assert.equal(coinQaroriniOchir("testdel"), true);
  assert.ok(!coinQarorlari().some((x) => x.symbol === "TESTDEL"));
  assert.equal(coinQaroriniOchir("TESTDEL"), false, "yo'q qarorni o'chirish `false`");
});
