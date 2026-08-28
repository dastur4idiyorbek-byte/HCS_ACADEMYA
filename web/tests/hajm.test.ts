import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import { hajmTaklifi, kunlikXavfFoizi } from "../src/lib/hajm.ts";

/** Bu testning butun maqsadi: SAYT hisobi BOT hisobidan ayrilib
 *  ketmasin.
 *
 *  Etalon qiymatlarni Python chiqaradi (`scripts/hajm_fixtures.py`) va
 *  ular `tests/hajm_fixtures.json` da yotadi. Python testi ham shu
 *  faylga solishtiradi. Ya'ni:
 *
 *    - Python hisobi o'zgarsa  -> Python testi yiqiladi;
 *    - sayt hisobi o'zgarsa    -> shu test yiqiladi;
 *    - etalon yangilansa-yu, sayt yangilanmasa -> shu test yiqiladi.
 *
 *  Pul hisobini ikki tilda saqlashning yagona xavfsiz yo'li shu. */
type Etalon = {
  balans: number;
  entry: number;
  stop: number;
  kunlikXavfFoiz: number;
  kunlikByudjet: number;
  hajm: number;
  xavf: number;
};

const etalonlar = JSON.parse(
  readFileSync(
    path.resolve(process.cwd(), "..", "tests", "hajm_fixtures.json"),
    "utf8",
  ),
) as Etalon[];

test("sayt hisobi bot hisobiga MOS", () => {
  assert.ok(etalonlar.length >= 5, "etalon fayl bo'sh yoki topilmadi");

  for (const e of etalonlar) {
    const t = hajmTaklifi(e.balans, e.entry, e.stop);
    assert.ok(t, `taklif hisoblanmadi: ${JSON.stringify(e)}`);

    const yaqin = (a: number, b: number, nom: string) =>
      assert.ok(
        Math.abs(a - b) < 1e-6,
        `${nom}: sayt ${a} != bot ${b} (balans ${e.balans}, stop ${e.stop})`,
      );

    yaqin(t.kunlikXavfFoiz, e.kunlikXavfFoiz, "kunlikXavfFoiz");
    yaqin(t.kunlikByudjet, e.kunlikByudjet, "kunlikByudjet");
    yaqin(t.hajm, e.hajm, "hajm");
    yaqin(t.xavf, e.xavf, "xavf");
  }
});

test("xavf foizi balans pog'onasidan olinadi", () => {
  // Pog'onalar YAML da: <=1000 -> 3%, <=10000 -> 2%, undan yuqori -> 1.5%
  assert.ok(kunlikXavfFoizi(500) >= kunlikXavfFoizi(5000));
  assert.ok(kunlikXavfFoizi(5000) >= kunlikXavfFoizi(50000));
});

test("mantiqsiz kirishda null", () => {
  assert.equal(hajmTaklifi(0, 100, 97), null, "balanssiz taklif bo'lmaydi");
  assert.equal(hajmTaklifi(1000, 100, 100), null, "Stop kirishga teng");
  assert.equal(hajmTaklifi(1000, 100, 105), null, "Stop kirishdan yuqori");
  assert.equal(hajmTaklifi(-5, 100, 97), null);
});

test("hajm hech qachon balansdan oshmaydi (spot: leverage yo'q)", () => {
  for (const balans of [100, 1000, 25000]) {
    const t = hajmTaklifi(balans, 100, 99.9); // juda yaqin Stop
    assert.ok(t && t.hajm <= balans, `${balans}: hajm ${t?.hajm}`);
    assert.ok(t?.kesilgan, "bunday holatda kesilgani aytilishi kerak");
  }
});
