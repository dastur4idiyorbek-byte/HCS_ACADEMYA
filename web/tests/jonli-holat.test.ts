import assert from "node:assert/strict";
import { test } from "node:test";

import { bazadanNusxa } from "./nusxa.ts";

const vaqtinchalik = bazadanNusxa("hcs-jonli-");
process.env.DATABASE_URL = `sqlite+aiosqlite:///${vaqtinchalik}`;

const { db } = await import("../src/lib/db.ts");
const { jonliHolat } = await import("../src/lib/queries.ts");

const ESKI = "2026-08-29 09:00:00";
const YANGI = "2026-08-29 10:00:00";

function yoz(
  symbol: string,
  stage: string,
  status: string,
  reason: string | null,
  score: number | null,
  cycleAt: string,
): void {
  db()
    .prepare(
      `insert into pipeline_events (symbol, stage, status, reason, score, cycle_at)
       values (?, ?, ?, ?, ?, ?)`,
    )
    .run(symbol, stage, status, reason, score, cycleAt);
}

test.before(() => {
  db().prepare("delete from pipeline_events").run();

  // Eski sikl — ekranda KO'RINMASLIGI kerak
  yoz("OLD", "classic_ta:halal", "fail", "eski sikl", null, ESKI);

  // Signal chiqqan coin
  for (const bosqich of ["classic_ta:halal", "classic_ta:data", "threshold"]) {
    yoz("SOL", bosqich, "pass", null, 82, YANGI);
  }
  // Yarim yo'lda to'xtagan
  yoz("ETH", "classic_ta:halal", "pass", null, null, YANGI);
  yoz("ETH", "classic_ta:data", "fail", "sham yetarli emas", null, YANGI);
  // Eng erta to'xtagan
  yoz("DOGE", "classic_ta:halal", "fail", "ro'yxatda yo'q", null, YANGI);
});

test("faqat OXIRGI sikl ko'rsatiladi", () => {
  // Ikki siklni aralashtirsak, bir coin ikki marta va ikki xil
  // natija bilan chiqardi — monitor "hozir" degan savolga javob beradi.
  const holat = jonliHolat();
  assert.ok(!holat.coinlar.some((c) => c.symbol === "OLD"));
  assert.equal(holat.cycleAt?.toISOString().slice(0, 13), "2026-08-29T10");
});

test("signal chiqqan coin YUQORIDA turadi", () => {
  const holat = jonliHolat();
  assert.equal(holat.coinlar[0].symbol, "SOL");
  assert.equal(holat.coinlar[0].signal, true);
  assert.equal(holat.coinlar[0].score, 82);
});

test("qolganlar qanchalik uzoq borgani bo'yicha tartiblanadi", () => {
  const holat = jonliHolat();
  assert.deepEqual(
    holat.coinlar.map((c) => c.symbol),
    ["SOL", "ETH", "DOGE"],
  );
});

test("to'xtagan bosqichda SABAB qoladi", () => {
  const eth = jonliHolat().coinlar.find((c) => c.symbol === "ETH");
  const yiqilgan = eth?.bosqichlar.filter((b) => b.status === "fail") ?? [];
  assert.equal(yiqilgan.length, 1);
  assert.equal(yiqilgan[0].reason, "sham yetarli emas");
});

test("sikl darajasidagi to'xtash alohida qaytadi", () => {
  yoz("*", "market_health", "fail", "indeks 32/100", null, YANGI);
  const holat = jonliHolat();
  assert.equal(holat.siklToxtadi, "indeks 32/100");
  // `*` coin kartochkasi bo'lib chiqmasligi kerak
  assert.ok(!holat.coinlar.some((c) => c.symbol === "*"));
});

test("bo'sh jadval xato bermaydi", () => {
  db().prepare("delete from pipeline_events").run();
  assert.deepEqual(jonliHolat(), { cycleAt: null, coinlar: [], siklToxtadi: null });
});
