import assert from "node:assert/strict";
import { test } from "node:test";

import { suvBelgisiUslubi } from "../src/lib/himoya.ts";

function svgni_ochi(uslub: { backgroundImage: string }): string {
  const m = uslub.backgroundImage.match(/data:image\/svg\+xml,(.*)"\)$/);
  assert.ok(m, "data URI topilmadi");
  return decodeURIComponent(m[1]);
}

test("belgi SVG ichiga tushadi", () => {
  const svg = svgni_ochi(suvBelgisiUslubi("HCS · 5000001"));
  assert.match(svg, /HCS · 5000001/);
  assert.match(svg, /^<svg /);
});

test("kafel takrorlanadi", () => {
  assert.equal(suvBelgisiUslubi("HCS · 1").backgroundRepeat, "repeat");
});

/** Belgi bazadan keladi (foydalanuvchi nomi bo'lishi ham mumkin), ya'ni
 *  unga ishonib bo'lmaydi. SVG — XML: `<` va tirnoq strukturani buzadi,
 *  buzilgan SVG esa umuman chizilmaydi — suv belgisi jimgina yo'qoladi. */
test("XML ni buzadigan belgilar tozalanadi", () => {
  const svg = svgni_ochi(suvBelgisiUslubi(`HCS <script>alert(1)</script> "x" 'y' &z`));
  assert.ok(!svg.includes("<script"), "teg qolmasligi kerak");
  assert.equal((svg.match(/<text/g) ?? []).length, 1, "faqat bitta <text> bo'lishi kerak");
  assert.equal((svg.match(/<\/svg>/g) ?? []).length, 1);
});

test("juda uzun belgi qisqartiriladi", () => {
  const svg = svgni_ochi(suvBelgisiUslubi("A".repeat(500)));
  assert.ok(svg.includes("A".repeat(64)));
  assert.ok(!svg.includes("A".repeat(65)));
});
