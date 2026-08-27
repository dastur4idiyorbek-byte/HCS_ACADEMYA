import assert from "node:assert/strict";
import { copyFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";

const vaqtinchalik = path.join(mkdtempSync(path.join(tmpdir(), "hcs-hav-")), "test.db");
copyFileSync(path.resolve(process.cwd(), "..", "data", "hcs.db"), vaqtinchalik);
process.env.DATABASE_URL = `sqlite+aiosqlite:///${vaqtinchalik}`;

const { barchaHavolalar, havolaOchir, havolaSaqla, havolalar } = await import(
  "../src/lib/queries.ts"
);

const ASOS = { title: "Telegram kanal", url: "https://t.me/hcs", icon: "telegram", position: 0, active: true };

test("havola qo'shiladi va ko'rinadi", () => {
  const n = havolaSaqla(null, ASOS);
  assert.ok(n.ok);
  const h = havolalar().find((x) => x.id === n.id);
  assert.equal(h?.title, "Telegram kanal");
  assert.equal(h?.icon, "telegram");
  havolaOchir(n.id);
});

/** `javascript:` manzili havolaga qo'yilsa, uni bosgan foydalanuvchining
 *  brauzerida ixtiyoriy kod ishga tushardi. */
test("javascript: va boshqa xavfli manzillar rad etiladi", () => {
  for (const yomon of ["javascript:alert(1)", "data:text/html,<script>", "t.me/hcs", ""]) {
    const n = havolaSaqla(null, { ...ASOS, url: yomon });
    assert.equal(n.ok, false, `${yomon} qabul qilinmasligi kerak`);
  }
});

test("noma'lum ikonka `web` ga tushadi", () => {
  const n = havolaSaqla(null, { ...ASOS, icon: "tiktok-yoq" });
  assert.ok(n.ok);
  assert.equal(barchaHavolalar().find((x) => x.id === n.id)?.icon, "web");
  havolaOchir(n.id);
});

test("o'chirilgan havola saytda ko'rinmaydi, adminda ko'rinadi", () => {
  const n = havolaSaqla(null, { ...ASOS, active: false });
  assert.ok(n.ok);
  assert.ok(!havolalar().some((x) => x.id === n.id), "saytda ko'rinmasligi kerak");
  assert.ok(barchaHavolalar().some((x) => x.id === n.id), "adminda ko'rinishi kerak");
  havolaOchir(n.id);
});

test("nomsiz havola rad etiladi", () => {
  assert.equal(havolaSaqla(null, { ...ASOS, title: "  " }).ok, false);
});

test("tartib bo'yicha saralanadi", () => {
  const a = havolaSaqla(null, { ...ASOS, title: "Ikkinchi", position: 5 });
  const b = havolaSaqla(null, { ...ASOS, title: "Birinchi", position: 1 });
  assert.ok(a.ok && b.ok);
  const nomlar = havolalar().map((x) => x.title);
  assert.ok(nomlar.indexOf("Birinchi") < nomlar.indexOf("Ikkinchi"));
  havolaOchir(a.id);
  havolaOchir(b.id);
});
