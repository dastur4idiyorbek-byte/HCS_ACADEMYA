import assert from "node:assert/strict";
import { test } from "node:test";

import {
  amaldagiStop,
  kechQoldimi,
  kutilmoqdami,
  uzoqlashish,
} from "../src/lib/kirish-holati.ts";

test("TP1 olinmagan bo'lsa Stop o'zgarmaydi", () => {
  assert.equal(amaldagiStop(100, 99, false), 99);
});

test("TP1 olingach Stop kirish narxiga ko'tariladi", () => {
  // Botdagi `Signal.effective_stop` bilan bir xil javob bo'lishi SHART:
  // aks holda foydalanuvchi tizim kuzatayotgan darajadan boshqa joyga
  // Stop qo'yardi.
  assert.equal(amaldagiStop(100, 99, true), 100);
});

test("uzoqlashish ikkala tomonda ham musbat", () => {
  assert.equal(uzoqlashish(100, 101.2)?.toFixed(2), "1.20");
  assert.equal(uzoqlashish(100, 98.8)?.toFixed(2), "1.20");
});

test("chegaradan oshsa kech deb belgilanadi — ikkala tomonga", () => {
  assert.equal(kechQoldimi(100, 101.3, 1.2, "active"), true);
  assert.equal(kechQoldimi(100, 98.7, 1.2, "active"), true);
});

test("chegaraga yetmasa kech emas", () => {
  assert.equal(kechQoldimi(100, 100.5, 1.2, "active"), false);
  assert.equal(kechQoldimi(100, 99.5, 1.2, "active"), false);
});

test("aynan chegarada — kech deb hisoblanadi", () => {
  assert.equal(kechQoldimi(100, 101.2, 1.2, "active"), true);
});

test("narx noma'lum bo'lsa ogohlantirish yo'q", () => {
  // "Ehtimol xavflidir" deb yozish ham yolg'on bo'lardi.
  assert.equal(kechQoldimi(100, null, 1.2, "active"), false);
});

test("mantiqsiz kirish narxida ogohlantirish yo'q", () => {
  assert.equal(uzoqlashish(0, 100), null);
  assert.equal(kechQoldimi(0, 100, 1.2, "active"), false);
});

// --------------------------------------------------------------------- //
//  KUTAYOTGAN LIMIT SIGNAL — ogohlantirish CHIQMAYDI
// --------------------------------------------------------------------- //

/** 2026-09-04 da saytda topilgan xato.
 *
 * Limit signal berilgan, narx entry'dan 3-4% YUQORIDA turibdi va
 * unga tushishi KUTILMOQDA. Sayt esa "bu signalga hozir kelish
 * tavsiya etilmaydi, xavf oshgan" deb yozardi.
 *
 * Bu chalg'ituvchi edi va TESKARI ma'no berardi: o'sha masofa
 * signalning kamchiligi emas, uning REJASI. Narx hali kirish
 * nuqtasiga tushmagan — xavf yo'q, kutilmoqda.
 */
test("KUTAYOTGAN limit signalda ogohlantirish CHIQMAYDI", () => {
  // Narx entry'dan 4% yuqorida — limit hali kutilmoqda.
  assert.equal(kechQoldimi(100, 104, 1.2, "pending"), false);
  // 10% bo'lsa ham: narx entry'ga hali yetmagan.
  assert.equal(kechQoldimi(100, 110, 1.2, "pending"), false);
});

test("narx entry'ga YETGACH ogohlantirish o'z ma'nosini topadi", () => {
  // Aynan o'sha masofa, lekin signal endi faol — narx entry'ga
  // yetgan va undan uzoqlashgan.
  assert.equal(kechQoldimi(100, 104, 1.2, "active"), true);
  assert.equal(kechQoldimi(100, 96, 1.2, "active"), true);
});

test("faol signalda chegaraga yetmagan harakat baribir tinch", () => {
  assert.equal(kechQoldimi(100, 100.5, 1.2, "active"), false);
});

test("kutilmoqdami faqat pending uchun rost", () => {
  assert.equal(kutilmoqdami("pending"), true);
  for (const holat of ["active", "tp1_hit", "weakening", "stopped", ""]) {
    assert.equal(
      kutilmoqdami(holat),
      false,
      `${holat} kutayotgan deb belgilandi`,
    );
  }
});
