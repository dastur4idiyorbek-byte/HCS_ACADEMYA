import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import {
  SUKUT_VIDJETLAR,
  VIDJETLAR,
  korinadiganVidjetlar,
  type VidjetKod,
} from "../src/lib/vidjetlar.ts";

/** Ro'yxat va CHIZUVCHI ajralib ketmasin.
 *
 * Vidjet ikki joyda yashaydi: `vidjetlar.ts` da ro'yxat, `Vidjetlar.tsx`
 * da esa uni chizadigan `switch`. Ro'yxatga qo'shilib chizuvchiga
 * unutilsa, foydalanuvchi vidjetni tanlaydi-yu, sahifada BO'SH JOY
 * ko'radi — xato ham bermaydi, log ham yozmaydi.
 */
test("har bir vidjetni chizadigan kod bor", () => {
  const chizuvchi = readFileSync(
    path.join(import.meta.dirname, "..", "src", "components", "Vidjetlar.tsx"),
    "utf8",
  );
  const yoq = VIDJETLAR.filter((v) => !chizuvchi.includes(`case "${v.kod}"`));
  assert.deepEqual(
    yoq.map((v) => v.kod),
    [],
    `bu vidjetlar chizilmaydi: ${yoq.map((v) => v.kod).join(", ")}`,
  );
});

test("sukut ro'yxatidagilar hammasi mavjud", () => {
  const mavjud = new Set(VIDJETLAR.map((v) => v.kod));
  const yetim = SUKUT_VIDJETLAR.filter((k) => !mavjud.has(k));
  assert.deepEqual(yetim, []);
});

/** Oltita — birinchi ekranga sig'adigan son. Ko'paysa tanlov o'rniga
 *  shovqin bo'ladi. */
test("sukut bo'yicha oltita vidjet", () => {
  assert.equal(SUKUT_VIDJETLAR.length, 6);
});

test("vidjet kodi takrorlanmaydi", () => {
  const kodlar = VIDJETLAR.map((v) => v.kod);
  assert.equal(new Set(kodlar).size, kodlar.length);
});

/** Bo'sh tanlov "hech narsa tanlamagan" degani, "hech narsa
 *  ko'rsatma" emas: yangi kelgan odam bo'sh sahifa ko'rmasin. */
test("tanlov bo'sh bo'lsa sukut to'plami chiqadi", () => {
  const natija = korinadiganVidjetlar([]);
  assert.deepEqual(
    natija.map((v) => v.kod),
    SUKUT_VIDJETLAR,
  );
});

test("tanlov tartibi saqlanadi", () => {
  const tanlov: VidjetKod[] = ["tarif", "salomatlik", "qorquv"];
  assert.deepEqual(
    korinadiganVidjetlar(tanlov).map((v) => v.kod),
    tanlov,
  );
});

/** Bazada eski, olib tashlangan vidjet qolib ketishi mumkin —
 *  u sahifani buzmasligi kerak. */
test("noma'lum kod jimgina tashlanadi", () => {
  const natija = korinadiganVidjetlar([
    "salomatlik",
    "yoq_boldi" as VidjetKod,
    "qorquv",
  ]);
  assert.deepEqual(
    natija.map((v) => v.kod),
    ["salomatlik", "qorquv"],
  );
});
