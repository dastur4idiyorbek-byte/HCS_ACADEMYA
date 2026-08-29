import assert from "node:assert/strict";
import { test } from "node:test";

import { bosqichKaliti } from "../src/lib/oshxona.ts";

test("strategiya prefiksi olib tashlanadi", () => {
  assert.equal(bosqichKaliti("classic_ta:zone_position"), "zone_position");
  assert.equal(bosqichKaliti("opening_range_scalp:window"), "window");
});

test("aniqroq kod ham asosiy bosqichga tegishli", () => {
  // `classic_ta:levels:stop_too_close` — bu baribir `levels` bosqichi.
  assert.equal(bosqichKaliti("classic_ta:levels:stop_too_close"), "levels");
});

test("Risk Engine qoidalari bitta bosqich", () => {
  // 13 ta qoida 13 ta bosqich bo'lib ko'rinsa, kartochka ma'nosini
  // yo'qotardi — qaysi qoida ekani SABAB qatorida yoziladi.
  assert.equal(bosqichKaliti("risk_engine:daily_loss_limit"), "risk_engine");
  assert.equal(bosqichKaliti("risk_engine"), "risk_engine");
});

test("prefiksiz kod o'zgarmaydi", () => {
  assert.equal(bosqichKaliti("threshold"), "threshold");
  assert.equal(bosqichKaliti("market_health"), "market_health");
});
