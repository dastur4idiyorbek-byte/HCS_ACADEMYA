import assert from "node:assert/strict";
import { test } from "node:test";

import { STANDART_TIL, TILLAR, tarjima, tilmi } from "../src/lib/i18n/index.ts";

function kalitlar(obj: unknown, prefiks = ""): string[] {
  if (typeof obj !== "object" || obj === null) return [prefiks];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    typeof v === "object" && v !== null ? kalitlar(v, `${prefiks}${k}.`) : [`${prefiks}${k}`],
  );
}

/** Bu test 4-naqshga qarshi: "qattiq yozilgan qiymat jimgina eskiradi".
 *  Yangi matn uz.json ga qo'shilib, ru.json da unutilsa — rus tilidagi
 *  sayt o'zbekcha matn ko'rsata boshlaydi va buni hech kim sezmaydi. */
test("barcha tillarda kalitlar to'liq mos", () => {
  const asos = kalitlar(TILLAR[STANDART_TIL]).sort();
  for (const [til, lugat] of Object.entries(TILLAR)) {
    if (til === STANDART_TIL) continue;
    const boshqa = kalitlar(lugat).sort();
    assert.deepEqual(
      boshqa,
      asos,
      `${til}.json kalitlari ${STANDART_TIL}.json bilan mos emas`,
    );
  }
});

test("birorta matn bo'sh emas", () => {
  for (const [til, lugat] of Object.entries(TILLAR)) {
    for (const kalit of kalitlar(lugat)) {
      const matn = tarjima(til as "uz" | "ru", kalit);
      assert.ok(matn.trim().length > 0, `${til}.json: ${kalit} bo'sh`);
    }
  }
});

test("topilmagan kalit sahifani yiqitmaydi", () => {
  assert.equal(tarjima("uz", "yoq.bunday.kalit"), "yoq.bunday.kalit");
});

test("tilmi() faqat qo'llab-quvvatlanadigan tilni qabul qiladi", () => {
  assert.ok(tilmi("uz"));
  assert.ok(tilmi("ru"));
  assert.ok(!tilmi("en"));
  assert.ok(!tilmi(undefined));
});
