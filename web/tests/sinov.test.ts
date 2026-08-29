import assert from "node:assert/strict";
import { test } from "node:test";

import { sinovDavri, sinovHolati } from "../src/lib/config.ts";

/** Sinov davri sana mantiqi. Sayt va bot BITTA YAML dan o'qiydi —
 *  bu yerda o'sha qiymatlar to'g'ri o'qilayotgani tekshiriladi. */

test("YAML dagi sinov sozlamasi o'qiladi", () => {
  const s = sinovDavri();
  assert.equal(s.kunlar, 100);
  assert.ok(s.chiqarilgan.includes("aggregate_user_capacity"));
});

test("boshlanish kunida sinov FAOL", () => {
  const s = sinovDavri();
  const holat = sinovHolati(new Date(`${s.boshlanish}T00:00:00Z`));
  assert.equal(holat.faol, true);
  assert.equal(holat.qolganKun, s.kunlar);
});

test("100-kundan keyin sinov tugaydi", () => {
  const s = sinovDavri();
  const bosh = new Date(`${s.boshlanish}T00:00:00Z`).getTime();
  const tugash = new Date(bosh + s.kunlar * 86_400_000);
  assert.equal(sinovHolati(tugash).faol, false);
  assert.equal(sinovHolati(tugash).qolganKun, 0);

  // Oxirgi kun hali sinov ichida
  const oxirgi = new Date(bosh + (s.kunlar - 1) * 86_400_000);
  assert.equal(sinovHolati(oxirgi).faol, true);
  assert.equal(sinovHolati(oxirgi).qolganKun, 1);
});

test("boshlanishdan oldin sinov yo'q", () => {
  const s = sinovDavri();
  const oldin = new Date(new Date(`${s.boshlanish}T00:00:00Z`).getTime() - 86_400_000);
  assert.equal(sinovHolati(oldin).faol, false);
});

test("kun ichidagi soat natijani o'zgartirmaydi", () => {
  // Sana bo'yicha hisoblanadi: 23:59 da ham o'sha kun.
  const s = sinovDavri();
  const ertalab = new Date(`${s.boshlanish}T00:10:00Z`);
  const kechqurun = new Date(`${s.boshlanish}T23:59:00Z`);
  assert.equal(sinovHolati(ertalab).qolganKun, sinovHolati(kechqurun).qolganKun);
});
