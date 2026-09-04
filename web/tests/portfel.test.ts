import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

import { dashboardQur, umumiyXavfPct } from "../src/lib/portfel.ts";

/** Bu testning butun maqsadi: SAYT hisobi BOT hisobidan ayrilib
 *  ketmasin.
 *
 *  Etalon qiymatlarni Python chiqaradi (`scripts/portfel_fixtures.py`)
 *  va ular `tests/portfel_fixtures.json` da yotadi. Python testi ham
 *  shu faylga solishtiradi. Ya'ni:
 *
 *    - Python hisobi o'zgarsa  -> Python testi yiqiladi;
 *    - sayt hisobi o'zgarsa    -> shu test yiqiladi;
 *    - etalon yangilansa-yu, sayt yangilanmasa -> shu test yiqiladi.
 *
 *  3-promptning "BITTA MANBA, IKKI EKRAN" talabi shu juftlik bilan
 *  bajariladi. */
type Etalon = {
  nom: string;
  balans: number;
  hozir: string;
  qismlar: { signalId: number; yopilganVaqt: string; natijaUsd: number }[];
  ochiqlar: {
    signalId: number;
    entry: number;
    ochiqMiqdorUsd: number;
    joriyNarx: number | null;
  }[];
  bolaklar: {
    raqam: number;
    hajm: number;
    bandKapital: number;
    bandXavf: number;
  }[];
  kutilgan: {
    qatorlar: { nom: string; usd: number; pct: number }[];
    unrealizedUsd: number;
    ochiqSoni: number;
    baholanmaganSoni: number;
    bandBolaklar: number[];
    boshBolaklar: number[];
    xavfPct: number;
    bosh: boolean;
  };
};

const etalonlar = JSON.parse(
  readFileSync(
    path.join(
      import.meta.dirname,
      "..",
      "..",
      "tests",
      "portfel_fixtures.json",
    ),
    "utf8",
  ),
) as Etalon[];

/** Suzuvchi nuqta ikki tilda oxirgi bitda farq qilishi mumkin. */
function yaqin(a: number, b: number, izoh: string): void {
  assert.ok(
    Math.abs(a - b) < 1e-9,
    `${izoh}: sayt ${a}, Python ${b} — hisob ayrilib ketdi`,
  );
}

test("etalon fayl bo'sh emas", () => {
  assert.ok(etalonlar.length >= 5, "etalon holatlari yetarli bo'lsin");
});

for (const e of etalonlar) {
  test(`portfel dashboardi Python bilan bir xil: ${e.nom}`, () => {
    const natija = dashboardQur(
      e.qismlar.map((q) => ({
        signalId: q.signalId,
        yopilganVaqt: new Date(q.yopilganVaqt),
        natijaUsd: q.natijaUsd,
      })),
      e.ochiqlar,
      e.bolaklar,
      e.balans,
      new Date(e.hozir),
    );

    assert.equal(natija.qatorlar.length, e.kutilgan.qatorlar.length);
    natija.qatorlar.forEach((qator, i) => {
      const kutilgan = e.kutilgan.qatorlar[i];
      assert.equal(qator.nom, kutilgan.nom);
      yaqin(qator.usd, kutilgan.usd, `${e.nom} / ${kutilgan.nom} usd`);
      yaqin(qator.pct, kutilgan.pct, `${e.nom} / ${kutilgan.nom} pct`);
    });

    yaqin(
      natija.unrealizedUsd,
      e.kutilgan.unrealizedUsd,
      `${e.nom} unrealized`,
    );
    assert.equal(natija.ochiqSoni, e.kutilgan.ochiqSoni);
    assert.equal(natija.baholanmaganSoni, e.kutilgan.baholanmaganSoni);
    assert.deepEqual(natija.bandBolaklar, e.kutilgan.bandBolaklar);
    assert.deepEqual(natija.boshBolaklar, e.kutilgan.boshBolaklar);
    yaqin(natija.xavfPct, e.kutilgan.xavfPct, `${e.nom} xavf`);
    assert.equal(natija.bosh, e.kutilgan.bosh);
  });
}

test("bo'sh bo'laklarda xavf nol", () => {
  assert.equal(
    umumiyXavfPct([
      { raqam: 1, hajm: 300, bandKapital: 0, bandXavf: 0 },
      { raqam: 2, hajm: 300, bandKapital: 0, bandXavf: 0 },
    ]),
    0,
  );
});

test("balans nol bo'lsa foiz nolga bo'linmaydi", () => {
  const natija = dashboardQur(
    [
      {
        signalId: 1,
        yopilganVaqt: new Date("2026-09-04T10:00:00Z"),
        natijaUsd: 50,
      },
    ],
    [],
    [],
    0,
    new Date("2026-09-04T15:00:00Z"),
  );
  assert.ok(natija.qatorlar.every((q) => Number.isFinite(q.pct)));
  assert.equal(natija.qatorlar[0].pct, 0);
});
