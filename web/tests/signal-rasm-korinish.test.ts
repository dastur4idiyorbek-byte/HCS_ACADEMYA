import assert from "node:assert/strict";
import { test } from "node:test";

import { signalRasmlari } from "../src/lib/signal-rasm.ts";

const t = (kalit: string) => kalit;

/** 2026-09-04: rasm admin panelda biriktirildi, lekin signal
 *  bo'limida KO'RINMADI. Sabab kodda emas — ish yarim qolgan edi:
 *  rasm faqat `/signallar/[id]` sahifasiga qo'shilgan, foydalanuvchi
 *  esa ro'yxatdagi ochiladigan "Grafik va kalkulyator" bo'limiga
 *  qaraydi. Endi ikkalasi ham SHU funksiyadan o'qiydi. */

test("rasm yo'q bo'lsa bo'sh ro'yxat", () => {
  assert.deepEqual(
    signalRasmlari({ entryChartImage: null, resultChartImage: null }, t),
    [],
  );
});

test("faqat kirish rasmi", () => {
  const r = signalRasmlari(
    { entryChartImage: "a1.png", resultChartImage: null },
    t,
  );
  assert.equal(r.length, 1);
  assert.equal(r[0].manzil, "/api/signal-media/a1.png");
  assert.equal(r[0].izoh, "signal.rasm_kirish");
});

test("ikkala rasm — KIRISH birinchi", () => {
  const r = signalRasmlari(
    { entryChartImage: "a1.png", resultChartImage: "b2.png" },
    t,
  );
  assert.deepEqual(
    r.map((x) => x.izoh),
    ["signal.rasm_kirish", "signal.rasm_natija"],
  );
});

/** Manzil `/api/signal-media/` bo'lishi SHART: o'sha yo'l obunani
 *  tekshiradi. Boshqa yo'lga o'tsa, rasm himoyani chetlab o'tadigan
 *  teshik bo'lardi. */
test("manzil obuna tekshiradigan yo'ldan o'tadi", () => {
  const r = signalRasmlari(
    { entryChartImage: "a1.png", resultChartImage: "b2.png" },
    t,
  );
  for (const x of r) {
    assert.ok(
      x.manzil.startsWith("/api/signal-media/"),
      `himoyasiz manzil: ${x.manzil}`,
    );
  }
});
