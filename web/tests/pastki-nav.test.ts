import assert from "node:assert/strict";
import { test } from "node:test";

import { MENYU, PASTKI_TABLAR, tabSahifalari } from "../src/lib/menyu.ts";

/** Pastki nav va MENYU bir-biridan AYRILIB KETMASIN.
 *
 * Pastki nav bo'limlari sahifalarini MENYU dagi `kod` orqali ko'rsatadi.
 * Agar yangi sahifa MENYU ga qo'shilib, PASTKI_TABLAR ga unutilsa — u
 * mobil pastki navdan ham, bo'lim tablaridan ham hech qayerdan
 * ochilmaydi va bu xato faqat qo'lda sinashda seziladi. Bu test shu
 * uzilishni qurish paytida tutadi.
 */

const sahifaKodlari = (tab: { sahifalar: string[] }) => tab.sahifalar;

test("MENYU dagi har bir kod kamida bitta tabda qamralgan", () => {
  const qamralgan = new Set(PASTKI_TABLAR.flatMap(sahifaKodlari));
  const ochiq = MENYU.map((b) => b.kod).filter((kod) => !qamralgan.has(kod));
  assert.deepEqual(
    ochiq,
    [],
    `bu kodlar pastki navda qamralmagan: ${ochiq.join(", ")}`,
  );
});

test("sahifalardagi har bir kod haqiqatan MENYU da mavjud", () => {
  const mavjud = new Set(MENYU.map((b) => b.kod));
  const yetim = [
    ...new Set(PASTKI_TABLAR.flatMap(sahifaKodlari).filter((k) => !mavjud.has(k))),
  ];
  assert.deepEqual(
    yetim,
    [],
    `bu kodlar MENYU da yo'q — bo'sh havola bo'lardi: ${yetim.join(", ")}`,
  );
});

test("bitta kod ikkita tabda takrorlanmaydi", () => {
  const korgan = new Set<string>();
  const takror = new Set<string>();
  for (const kod of PASTKI_TABLAR.flatMap(sahifaKodlari)) {
    if (korgan.has(kod)) takror.add(kod);
    else korgan.add(kod);
  }
  assert.deepEqual(
    [...takror],
    [],
    `bu kodlar bir necha tabda takrorlangan: ${[...takror].join(", ")}`,
  );
});

test("tabSahifalari admin bo'lmaganga 'admin' bandini qaytarmaydi", () => {
  const kabinet = PASTKI_TABLAR.find((t) => t.kod === "kabinet");
  assert.ok(kabinet, "kabinet tabi topilmadi");

  const oddiy = tabSahifalari(kabinet, false).map((s) => s.kod);
  assert.deepEqual(
    oddiy,
    ["profil", "portfel"],
    "admin bo'lmaganga admin bandi tushmasligi kerak",
  );

  const admin = tabSahifalari(kabinet, true).map((s) => s.kod);
  // "kuzatuv" — kuzatuv paneli (9-prompt), faqat adminlarga.
  assert.deepEqual(admin, ["profil", "portfel", "kuzatuv", "admin"]);
});
