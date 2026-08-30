import assert from "node:assert/strict";
import { test } from "node:test";

import { amaldagiStop, kechQoldimi, uzoqlashish } from "../src/lib/kirish-holati.ts";

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
  assert.equal(kechQoldimi(100, 101.3, 1.2), true);
  assert.equal(kechQoldimi(100, 98.7, 1.2), true);
});

test("chegaraga yetmasa kech emas", () => {
  assert.equal(kechQoldimi(100, 100.5, 1.2), false);
  assert.equal(kechQoldimi(100, 99.5, 1.2), false);
});

test("aynan chegarada — kech deb hisoblanadi", () => {
  assert.equal(kechQoldimi(100, 101.2, 1.2), true);
});

test("narx noma'lum bo'lsa ogohlantirish yo'q", () => {
  // "Ehtimol xavflidir" deb yozish ham yolg'on bo'lardi.
  assert.equal(kechQoldimi(100, null, 1.2), false);
});

test("mantiqsiz kirish narxida ogohlantirish yo'q", () => {
  assert.equal(uzoqlashish(0, 100), null);
  assert.equal(kechQoldimi(0, 100, 1.2), false);
});
