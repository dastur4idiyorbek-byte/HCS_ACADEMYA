import assert from "node:assert/strict";
import { test } from "node:test";

import {
  bosqichNomi,
  bosqichTartibi,
  nechtaBosqichNomiBor,
  vaqtDarvozasimi,
  voronkaTartibi,
} from "../src/lib/bosqichlar.ts";

/** Bu testlar Python faylini O'QIY OLAYOTGANIMIZNI tekshiradi.
 *
 * `bosqichNomi()` topilmasa kodning o'zini qaytaradi — ya'ni parser
 * butunlay ishlamay qolsa ham sayt "ishlayotgandek" ko'rinadi, ekranda
 * esa `classic_ta:zones` kabi xom kodlar chiqadi. Test aynan shu
 * jimgina buzilishni tutadi.
 */

test("Python faylidan bosqich nomlari o'qildi", () => {
  assert.ok(
    nechtaBosqichNomiBor() > 30,
    `faqat ${nechtaBosqichNomiBor()} ta nom o'qildi — parser buzilgan bo'lishi mumkin`,
  );
});

test("aniq bosqichlar to'g'ri tarjima qilinadi", () => {
  assert.equal(bosqichNomi("threshold"), "Ball chegaradan past");
  assert.equal(bosqichNomi("classic_ta:zones"), "Support/Resistance zonasi topilmadi");
  assert.equal(bosqichNomi("risk_engine:btc_market_filter"), "BTC tushmoqda (4.5)");
});

test("nomi yo'q bosqich kodning o'zi bo'lib qaytadi", () => {
  assert.equal(bosqichNomi("yangi:bosqich"), "yangi:bosqich");
});

test("vaqt darvozalari ajratiladi", () => {
  assert.ok(vaqtDarvozasimi("opening_range_scalp:window"));
  assert.ok(vaqtDarvozasimi("opening_range_scalp:session"));
  assert.ok(!vaqtDarvozasimi("threshold"));
  assert.ok(!vaqtDarvozasimi("classic_ta:zones"));
});

test("tartib quvur bo'ylab: salomatlik -> chegara -> strategiya", () => {
  assert.ok(bosqichTartibi("market_health") < bosqichTartibi("threshold"));
  assert.ok(bosqichTartibi("threshold") < bosqichTartibi("classic_ta:zones"));
  assert.equal(bosqichTartibi("nomalum:bosqich"), nechtaBosqichNomiBor());
});

/** Voronka nomzod HAQIQATDA o'tadigan ketma-ketlikda chizilishi kerak.
 *  Python'dagi `STAGE_LABELS` boshqa mantiq bo'yicha guruhlangan — o'sha
 *  tartibni to'g'ridan-to'g'ri ishlatganimizda ekranda "ball chegarasi"
 *  birinchi bo'lib chiqdi, holbuki nomzod unga eng oxirida yetib boradi. */
test("voronka: strategiya -> ball -> risk engine", () => {
  assert.ok(
    voronkaTartibi("classic_ta:zone_position") < voronkaTartibi("threshold"),
    "strategiya filtri ball chegarasidan oldin turishi kerak",
  );
  assert.ok(
    voronkaTartibi("threshold") < voronkaTartibi("risk_engine:btc_market_filter"),
    "ball chegarasi Risk Engine dan oldin turishi kerak",
  );
  assert.ok(
    voronkaTartibi("opening_range_scalp:breakout") < voronkaTartibi("threshold"),
    "yangi strategiya ham 1-guruhga tushadi",
  );
  assert.ok(voronkaTartibi("classic_ta:zones") < voronkaTartibi("classic_ta:levels"));
});
