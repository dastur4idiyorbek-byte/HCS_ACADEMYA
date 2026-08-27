import assert from "node:assert/strict";
import { createHash, createHmac } from "node:crypto";
import { test } from "node:test";

import {
  SESSIYA_SEK,
  sessiyaOqi,
  sessiyaYarat,
  telegramLoginTekshir,
} from "../src/lib/auth.ts";

const TOKEN = "123456:TEST-BOT-TOKEN";

/** Telegram qanday imzolasa — biz ham shunday imzolab, haqiqiy so'rovni
 *  taqlid qilamiz. Testda hash'ni QO'LDA yozib qo'ysak, algoritm
 *  o'zgarganda test ham, kod ham birga xato bo'lib qolardi. */
function imzola(maydonlar: Record<string, string>, token = TOKEN): Record<string, string> {
  const satr = Object.keys(maydonlar)
    .sort()
    .map((k) => `${k}=${maydonlar[k]}`)
    .join("\n");
  const kalit = createHash("sha256").update(token).digest();
  const hash = createHmac("sha256", kalit).update(satr).digest("hex");
  return { ...maydonlar, hash };
}

const HOZIR = new Date("2026-08-27T12:00:00Z");
const AUTH_DATE = String(Math.floor(HOZIR.getTime() / 1000) - 10);

test("to'g'ri imzolangan ma'lumot qabul qilinadi", () => {
  const xom = imzola({ id: "777", first_name: "Diyorbek", auth_date: AUTH_DATE });
  const natija = telegramLoginTekshir(xom, TOKEN, HOZIR);
  assert.equal(natija?.id, 777);
  assert.equal(natija?.first_name, "Diyorbek");
});

test("SOXTA ma'lumot rad etiladi — bu butun himoyaning o'zi", () => {
  // Hujumchi "men admin man" deb yozadi, lekin bot tokenini bilmaydi
  const soxta = { id: "777", first_name: "Hujumchi", auth_date: AUTH_DATE, hash: "0".repeat(64) };
  assert.equal(telegramLoginTekshir(soxta, TOKEN, HOZIR), null);
});

test("bitta maydon o'zgartirilsa ham rad etiladi", () => {
  const xom = imzola({ id: "777", first_name: "Diyorbek", auth_date: AUTH_DATE });
  // Imzo o'sha, lekin id boshqa — ya'ni "boshqa odam bo'lib kirish"
  assert.equal(telegramLoginTekshir({ ...xom, id: "999" }, TOKEN, HOZIR), null);
});

test("boshqa bot tokeni bilan imzolangan ma'lumot o'tmaydi", () => {
  const xom = imzola({ id: "777", auth_date: AUTH_DATE }, "boshqa:token");
  assert.equal(telegramLoginTekshir(xom, TOKEN, HOZIR), null);
});

test("eskirgan tasdiq qayta ishlatilmaydi (replay)", () => {
  const eski = String(Math.floor(HOZIR.getTime() / 1000) - 86_401);
  const xom = imzola({ id: "777", auth_date: eski });
  assert.equal(telegramLoginTekshir(xom, TOKEN, HOZIR), null);
});

test("hash umuman bo'lmasa rad etiladi", () => {
  assert.equal(telegramLoginTekshir({ id: "777", auth_date: AUTH_DATE }, TOKEN, HOZIR), null);
});

test("sessiya 144 soat amal qiladi", () => {
  const { token, expires } = sessiyaYarat(777, TOKEN, HOZIR);
  assert.equal(Math.round((expires.getTime() - HOZIR.getTime()) / 1000), SESSIYA_SEK);
  assert.equal(sessiyaOqi(token, TOKEN, HOZIR), 777);
});

test("144 soatdan keyin sessiya tugaydi", () => {
  const { token } = sessiyaYarat(777, TOKEN, HOZIR);
  const keyin = new Date(HOZIR.getTime() + (SESSIYA_SEK + 1) * 1000);
  assert.equal(sessiyaOqi(token, TOKEN, keyin), null);
  // Bir soniya oldin esa hali ishlaydi
  const oldin = new Date(HOZIR.getTime() + (SESSIYA_SEK - 1) * 1000);
  assert.equal(sessiyaOqi(token, TOKEN, oldin), 777);
});

test("o'zgartirilgan sessiya tokeni rad etiladi", () => {
  const { token } = sessiyaYarat(777, TOKEN, HOZIR);
  const [tana, imzo] = token.split(".");
  // Foydalanuvchi o'z ID sini adminnikiga almashtirmoqchi
  const yangiTana = Buffer.from(
    JSON.stringify({ tid: 111, exp: Math.floor(HOZIR.getTime() / 1000) + 999 }),
  ).toString("base64url");
  assert.equal(sessiyaOqi(`${yangiTana}.${imzo}`, TOKEN, HOZIR), null);
  assert.equal(sessiyaOqi(`${tana}.${"A".repeat(43)}`, TOKEN, HOZIR), null);
  assert.equal(sessiyaOqi("axlat", TOKEN, HOZIR), null);
  assert.equal(sessiyaOqi(undefined, TOKEN, HOZIR), null);
});

test("boshqa bot tokeni bilan sessiya o'qilmaydi", () => {
  const { token } = sessiyaYarat(777, TOKEN, HOZIR);
  assert.equal(sessiyaOqi(token, "boshqa:token", HOZIR), null);
});
