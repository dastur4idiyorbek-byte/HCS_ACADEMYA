import assert from "node:assert/strict";
import { test } from "node:test";

import { kerakliWinRate, tahlil, xulosa, yakuni } from "../src/lib/signal-tahlil.ts";

const BOSH = new Date("2026-08-30T10:00:00Z");

test("Stop masofasi va R/R nisbati hisoblanadi", () => {
  // DOT: kirish 0.869, stop 0.829, TP2 0.928
  const t = tahlil({
    status: "stopped",
    entry: 0.869,
    stop: 0.829,
    tp2: 0.928,
    tp1Reached: false,
    createdAt: BOSH,
    closedAt: new Date("2026-08-30T22:00:00Z"),
  });
  assert.equal(t.stopFoiz?.toFixed(2), "4.60");
  assert.equal(t.tp2Foiz?.toFixed(2), "6.79");
  assert.equal(t.nisbat?.toFixed(2), "1.48");
  assert.equal(t.soat, 12);
});

test("yakun TP1 dan keyingi Stopni ajratadi", () => {
  // Bu MUHIM farq: TP1 olib, keyin nolga qaytgan savdo — zarar emas.
  assert.equal(yakuni("stopped", true), "tp1_stop");
  assert.equal(yakuni("stopped", false), "stop");
  assert.equal(yakuni("tp2_hit", true), "tp2");
  assert.equal(yakuni("cancelled", false), "bekor");
});

test("bekor qilinganlar win-rate maxrajiga kirmaydi", () => {
  // Ular savdoga aylanmagan — na yutuq, na yutqazish.
  const x = xulosa([
    { yakun: "tp2", natijaFoiz: 4 },
    { yakun: "stop", natijaFoiz: -4.6 },
    { yakun: "bekor", natijaFoiz: null },
  ]);
  assert.equal(x.savdo, 2);
  assert.equal(x.yutuq, 1);
  assert.equal(x.winRate, 50);
});

test("kerakli win-rate nisbatdan chiqadi", () => {
  // 1:1.5 -> 40%, 1:3 -> 25%. "20% yomonmi?" degan savolga javob
  // nisbatni bilmasdan berilmaydi.
  assert.equal(kerakliWinRate(1.5)?.toFixed(1), "40.0");
  assert.equal(kerakliWinRate(3)?.toFixed(1), "25.0");
  assert.equal(kerakliWinRate(1)?.toFixed(1), "50.0");
});

test("mantiqsiz qiymatlarda raqam o'ylab topilmaydi", () => {
  const t = tahlil({
    status: "stopped",
    entry: 0,
    stop: 0,
    tp2: 0,
    tp1Reached: false,
    createdAt: null,
    closedAt: null,
  });
  assert.equal(t.stopFoiz, null);
  assert.equal(t.nisbat, null);
  assert.equal(t.soat, null);
  assert.equal(kerakliWinRate(0), null);
});

test("natija yo'q bo'lsa xulosa bo'sh qoladi", () => {
  const x = xulosa([{ yakun: "stop", natijaFoiz: null }]);
  assert.equal(x.winRate, null);
  assert.equal(x.ortachaNatija, null);
});
