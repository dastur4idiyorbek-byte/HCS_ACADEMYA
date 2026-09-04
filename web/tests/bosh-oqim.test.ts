import assert from "node:assert/strict";
import { test } from "node:test";

import { bazadanNusxa } from "./nusxa.ts";

const vaqtinchalik = bazadanNusxa("hcs-oqim-");
process.env.DATABASE_URL = `sqlite+aiosqlite:///${vaqtinchalik}`;

const {
  boshPostQoshish,
  boshPostOchirish,
  boshPostlar,
  boshPostlarSoni,
  postTuriniAniqla,
} = await import("../src/lib/queries.ts");

/** Bosh sahifa oqimi (4-prompt, 1-qism).
 *
 * Eng muhimi TARTIB: eng yangi post TEPADA bo'lishi kerak. Teskari
 * bo'lsa, foydalanuvchi sahifani ochib eng eski xabarni ko'rardi va
 * yangisi borligini bilmasdi. */

test("eng yangi post TEPADA turadi", () => {
  const a = boshPostQoshish("birinchi", null, null);
  const b = boshPostQoshish("ikkinchi", null, null);
  const c = boshPostQoshish("uchinchi", null, null);

  const royxat = boshPostlar(10);
  assert.deepEqual(
    royxat.slice(0, 3).map((p) => p.matn),
    ["uchinchi", "ikkinchi", "birinchi"],
  );

  for (const n of [a, b, c]) boshPostOchirish(n.id!);
});

test("bo'sh post YOZILMAYDI", () => {
  const oldin = boshPostlarSoni();
  assert.equal(boshPostQoshish(null, null, null).ok, false);
  assert.equal(boshPostQoshish("   ", null, null).ok, false);
  assert.equal(boshPostlarSoni(), oldin, "bo'sh post baribir yozildi");
});

test("noma'lum fayl turi rad etiladi", () => {
  const natija = boshPostQoshish("matn", "zararli.exe", null);
  assert.equal(natija.ok, false);
});

test("faqat fayldan iborat post ham yoziladi", () => {
  const n = boshPostQoshish(null, "a1b2.jpg", null);
  assert.ok(n.ok);
  const post = boshPostlar(5).find((p) => p.id === n.id);
  assert.equal(post?.turi, "image");
  assert.equal(post?.mediaTuri, "image");
  boshPostOchirish(n.id!);
});

test("tur TARKIBDAN hisoblanadi, admindan so'ralmaydi", () => {
  assert.equal(postTuriniAniqla("salom", null), "text");
  assert.equal(postTuriniAniqla(null, "image"), "image");
  assert.equal(postTuriniAniqla("  ", "audio"), "audio");
  assert.equal(postTuriniAniqla("izoh", "image"), "mixed");
});

/** "Ko'proq yuklash" id bo'yicha ishlaydi, offset bilan emas: sahifa
 *  ochilgandan keyin yangi post qo'shilsa, offset bilan bitta post ikki
 *  marta ko'rinardi yoki bittasi tushib qolardi. */
test("keyingi sahifa faqat ESKIROQ postlarni beradi", () => {
  const idlar = ["1", "2", "3", "4"].map(
    (m) => boshPostQoshish(m, null, null).id!,
  );

  const birinchi = boshPostlar(2);
  const ikkinchi = boshPostlar(2, birinchi[birinchi.length - 1].id);

  assert.equal(ikkinchi.length, 2);
  for (const p of ikkinchi) {
    assert.ok(
      p.id < birinchi[birinchi.length - 1].id,
      "keyingi sahifada eskiroq bo'lmagan post bor",
    );
  }
  const kesishma = ikkinchi.filter((p) => birinchi.some((b) => b.id === p.id));
  assert.equal(kesishma.length, 0, "post ikki sahifada takrorlandi");

  for (const id of idlar) boshPostOchirish(id);
});

test("o'chirilgan post media faylining nomini qaytaradi", () => {
  const n = boshPostQoshish("rasmli", "c3d4.png", null);
  const natija = boshPostOchirish(n.id!);
  assert.equal(natija.ok, true);
  assert.equal(natija.media, "c3d4.png", "disk tozalash uchun nom kerak");
  assert.equal(boshPostOchirish(n.id!).ok, false);
});
