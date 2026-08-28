import assert from "node:assert/strict";
import { test } from "node:test";

import {
  obunaKunlari,
  salomatlikBandlari,
  savdoQoidalari,
  tp1Ulushi,
} from "../src/lib/config.ts";

/** Bu testlar 2-naqshga qarshi: "e'lon qilingan, lekin ulanmagan".
 *
 * `config.ts` dagi `yol()` funksiyasi kalit topilmasa XATO BERMAYDI —
 * zaxira qiymatni qaytaradi. Bu ataylab shunday (bitta noto'g'ri kalit
 * saytni yiqitmasligi kerak), lekin narxi bor: yo'lni noto'g'ri yozsak,
 * sayt ishlayveradi va biz YAML ni umuman o'qimayotganimizni bilmaymiz.
 *
 * Shuning uchun test zaxira qiymatga TAYANMAYDI — u YAML faylining
 * o'zidan boshqa yo'l bilan o'qib, ikkalasini solishtiradi.
 */

import { readFileSync } from "node:fs";
import path from "node:path";

import { parse } from "yaml";

const yaml = parse(
  readFileSync(path.resolve(process.cwd(), "..", "config", "default.yaml"), "utf8"),
) as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

test("obuna muddati YAML dan o'qiladi, ko'chirib yozilmagan", () => {
  const kunlar = obunaKunlari();
  assert.equal(kunlar.daily, yaml.subscriptions.periods.daily);
  assert.equal(kunlar.monthly, yaml.subscriptions.periods.monthly);
});

test("salomatlik bandlari YAML dan o'qiladi", () => {
  const band = salomatlikBandlari();
  assert.equal(band.high, yaml.scoring.thresholds.health_high_min);
  assert.equal(band.mid, yaml.scoring.thresholds.health_mid_min);
});

test("bandlar mantiqan to'g'ri tartibda", () => {
  const { high, mid } = salomatlikBandlari();
  assert.ok(mid < high, "o'rta band yuqori banddan past bo'lishi kerak");
  assert.ok(mid > 0 && high < 100);
});

test("nisbiy HCS_CONFIG_FILE ildizga nisbatan hisoblanadi", async () => {
  // Bot va sayt bir xil `HCS_CONFIG_FILE` ni ishlatadi, lekin turli
  // papkadan ishga tushadi. Nisbiy yo'l `web/` ga nisbatan hisoblansa,
  // sayt faylni topolmaydi va JIMGINA zaxira qiymatlarga o'tib ketadi.
  const oldingi = process.env.HCS_CONFIG_FILE;
  process.env.HCS_CONFIG_FILE = "config/default.yaml";
  try {
    const yangi = await import(`../src/lib/config.ts?nusxa=${Date.now()}`);
    assert.equal(yangi.obunaKunlari().monthly, yaml.subscriptions.periods.monthly);
  } finally {
    if (oldingi === undefined) delete process.env.HCS_CONFIG_FILE;
    else process.env.HCS_CONFIG_FILE = oldingi;
  }
});

test("savdo qoidalari YAML dan o'qiladi", () => {
  const q = savdoQoidalari();
  assert.equal(q.maxStopPct, yaml.trade_rules.max_stop_distance_pct);
  assert.equal(q.minTpPct, yaml.trade_rules.min_tp_distance_pct);
  assert.equal(q.maxTpPct, yaml.trade_rules.max_tp_distance_pct);
  assert.equal(q.minRiskReward, yaml.trade_rules.min_risk_reward);
});

/** Bot kartochkasida TP1 ulushi shu qiymatdan yoziladi
 *  (`bot/formatting.py` -> `render_levels`). Yo'l noto'g'ri bo'lsa
 *  `yol()` jimgina zaxira qiymatni qaytaradi — ya'ni xato ko'rinmaydi
 *  va sayt bilan bot boshqa-boshqa ulush ko'rsatib turaveradi. */
test("TP1 ulushi YAML dagi haqiqiy yo'ldan o'qiladi", () => {
  const ulush = tp1Ulushi();
  assert.ok(ulush > 0 && ulush <= 100, `mantiqsiz ulush: ${ulush}`);
  assert.equal(ulush, yaml.portfolio.tp1_close_pct);
});
