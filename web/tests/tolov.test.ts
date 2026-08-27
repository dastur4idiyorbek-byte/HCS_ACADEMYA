import assert from "node:assert/strict";
import { copyFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";

/* Baza yo'li import'dan OLDIN o'rnatiladi: `db()` ulanishni birinchi
   chaqiruvda ochib, keshlab qo'yadi. Sxemani qo'lda yozmaymiz — haqiqiy
   bazadan NUSXA olamiz, aks holda test sxemasi asl sxemadan sezilmasdan
   uzoqlashib ketadi. */
const vaqtinchalik = path.join(mkdtempSync(path.join(tmpdir(), "hcs-test-")), "test.db");
copyFileSync(path.resolve(process.cwd(), "..", "data", "hcs.db"), vaqtinchalik);
process.env.DATABASE_URL = `sqlite+aiosqlite:///${vaqtinchalik}`;

const { db, vaqtSatri } = await import("../src/lib/db.ts");
const { tolovniTasdiqla, tolovniRadEt, faolObuna, kutilayotganTolovlar } = await import(
  "../src/lib/queries.ts"
);
const { obunaKunlari } = await import("../src/lib/config.ts");

const HOZIR = new Date("2026-08-27T12:00:00Z");

function oxirgiId(): number {
  const q = db().prepare("select last_insert_rowid() as id").get() as { id: number };
  return Number(q.id);
}

function fixtura(period: "daily" | "monthly" = "monthly"): number {
  const baza = db();
  baza
    .prepare(
      `insert into users (telegram_id, username, full_name, role, language,
                          is_blocked, created_at, updated_at)
       values (?, 'test', 'Test User', 'user', 'uz', 0, ?, ?)`,
    )
    .run(900000 + Math.floor(Math.random() * 90000), vaqtSatri(HOZIR), vaqtSatri(HOZIR));
  const userId = oxirgiId();
  baza
    .prepare(
      `insert into payments (user_id, tier, period, amount, currency, status,
                             created_at, updated_at)
       values (?, 'pro', ?, 100000, 'KGS', 'pending', ?, ?)`,
    )
    .run(userId, period, vaqtSatri(HOZIR), vaqtSatri(HOZIR));
  return oxirgiId();
}

test("tasdiqlash obunani ochadi va muddat YAML dan olinadi", () => {
  const tolovId = fixtura("monthly");
  const natija = tolovniTasdiqla(tolovId, 111, HOZIR);
  assert.ok(natija.ok);

  const tolov = db()
    .prepare("select user_id, status, reviewed_by, subscription_id from payments where id = ?")
    .get(tolovId) as Record<string, unknown>;
  assert.equal(tolov.status, "approved");
  assert.equal(tolov.reviewed_by, 111);
  assert.ok(tolov.subscription_id);

  const obuna = faolObuna(Number(tolov.user_id), HOZIR);
  assert.equal(obuna?.tier, "pro");
  const kutilgan = HOZIR.getTime() + obunaKunlari().monthly * 86_400_000;
  assert.equal(obuna?.expiresAt?.getTime(), kutilgan);
});

test("kunlik tarif sinov muddati sifatida belgilanadi", () => {
  const tolovId = fixtura("daily");
  const natija = tolovniTasdiqla(tolovId, 111, HOZIR);
  assert.ok(natija.ok);
  const tolov = db().prepare("select user_id from payments where id = ?").get(tolovId) as {
    user_id: number;
  };
  const obuna = faolObuna(tolov.user_id, HOZIR);
  assert.equal(obuna?.isTrial, true);
  assert.equal(obuna?.expiresAt?.getTime(), HOZIR.getTime() + obunaKunlari().daily * 86_400_000);
});

test("bir to'lov IKKI MARTA tasdiqlanmaydi", () => {
  const tolovId = fixtura();
  assert.ok(tolovniTasdiqla(tolovId, 111, HOZIR).ok);
  const ikkinchi = tolovniTasdiqla(tolovId, 111, HOZIR);
  assert.equal(ikkinchi.ok, false);
  // Ikkinchi urinishdan obuna qo'shilib qolmagan bo'lishi kerak
  const tolov = db().prepare("select user_id from payments where id = ?").get(tolovId) as {
    user_id: number;
  };
  const soni = db()
    .prepare("select count(*) as n from subscriptions where user_id = ?")
    .get(tolov.user_id) as { n: number };
  assert.equal(soni.n, 1);
});

test("rad etilgan to'lov obuna ochmaydi", () => {
  const tolovId = fixtura();
  const natija = tolovniRadEt(tolovId, 111, "Chek o'qilmadi", HOZIR);
  assert.ok(natija.ok);
  const tolov = db()
    .prepare("select user_id, status, reject_reason from payments where id = ?")
    .get(tolovId) as Record<string, unknown>;
  assert.equal(tolov.status, "rejected");
  assert.equal(tolov.reject_reason, "Chek o'qilmadi");
  assert.equal(faolObuna(Number(tolov.user_id), HOZIR), null);
});

test("rad etilgan to'lov keyin tasdiqlanmaydi", () => {
  const tolovId = fixtura();
  tolovniRadEt(tolovId, 111, "sabab", HOZIR);
  assert.equal(tolovniTasdiqla(tolovId, 111, HOZIR).ok, false);
});

test("mavjud bo'lmagan to'lov xato bermaydi, `topilmadi` qaytaradi", () => {
  const natija = tolovniTasdiqla(999999, 111, HOZIR);
  assert.deepEqual(natija, { ok: false, sabab: "topilmadi" });
});

test("kutilayotganlar ro'yxatiga tasdiqlangani kirmaydi", () => {
  const tolovId = fixtura();
  assert.ok(kutilayotganTolovlar(100).some((t) => t.id === tolovId));
  tolovniTasdiqla(tolovId, 111, HOZIR);
  assert.ok(!kutilayotganTolovlar(100).some((t) => t.id === tolovId));
});
