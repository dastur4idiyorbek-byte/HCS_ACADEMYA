/** "use client" fayl SERVER kutubxonasini import qilmasin.
 *
 * NIMA UCHUN BU TEST BOR. 2026-09-03 da Railway'da bir kun davomida
 * BIRORTA deploy o'tmadi. Sabab kodda emas, CHEGARADA edi:
 *
 *     SignalOchish.tsx  ("use client")
 *       -> @/lib/config
 *         -> node:fs
 *
 * Turbopack mijoz to'plamiga `node:fs` ni joylashtira olmaydi va
 * `next build` panika bilan yiqiladi:
 *
 *     the chunking context does not support external modules
 *     (request: node:fs)
 *
 * Xato xabari sabab ko'rsatmaydi — u faqat qaysi sahifa yiqilganini
 * aytadi. Shuning uchun tekshiruv testga ko'chirildi: u aynan qaysi
 * FAYL va qaysi IMPORT aybdor ekanini aytadi.
 *
 * Qiymat kerak bo'lsa u PROPS bo'lib serverdan o'tadi.
 */

import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const ILDIZ = path.join(process.cwd(), "src");

/** Ichida `node:` moduli bor kutubxonalar — mijozga tushmasligi shart. */
const SERVER_KUTUBXONALARI = new Set([
  "@/lib/config",
  "@/lib/db",
  "@/lib/queries",
  "@/lib/jonli-server",
  "@/lib/session",
]);

function fayllar(dir: string): string[] {
  const natija: string[] = [];
  for (const nom of readdirSync(dir)) {
    const yol = path.join(dir, nom);
    if (statSync(yol).isDirectory()) {
      natija.push(...fayllar(yol));
    } else if (/\.tsx?$/.test(nom)) {
      natija.push(yol);
    }
  }
  return natija;
}

/** Faqat QIYMAT importlari. `import type { ... }` kompilyatsiyada
 *  yo'qoladi, ya'ni to'plamga tushmaydi va muammo emas. */
function qiymatImportlari(matn: string): string[] {
  const natija: string[] = [];
  const naqsh = /^import\s+(?!type\s)([\s\S]*?)from\s+"([^"]+)"/gm;
  let mos: RegExpExecArray | null;
  while ((mos = naqsh.exec(matn)) !== null) {
    natija.push(mos[2]);
  }
  return natija;
}

function mijozFayllari(): string[] {
  return fayllar(ILDIZ).filter((yol) =>
    /^\s*"use client"/m.test(readFileSync(yol, "utf8")),
  );
}

test("mijoz komponentlari topildi", () => {
  assert.ok(
    mijozFayllari().length > 5,
    "skaner hech narsa topmadi — yo'l noto'g'ri bo'lishi mumkin",
  );
});

test("mijoz fayllari server kutubxonasini import qilmaydi", () => {
  const buzilganlar: string[] = [];
  for (const yol of mijozFayllari()) {
    const yomon = qiymatImportlari(readFileSync(yol, "utf8")).filter((m) =>
      SERVER_KUTUBXONALARI.has(m),
    );
    if (yomon.length > 0) {
      buzilganlar.push(`${path.relative(process.cwd(), yol)} -> ${yomon.join(", ")}`);
    }
  }
  assert.deepEqual(
    buzilganlar,
    [],
    "Mijoz komponenti server kutubxonasini import qilmoqda:\n  " +
      `${buzilganlar.join("\n  ")}\n` +
      "Qiymatni PROPS bo'lib serverdan uzating — aks holda `next build` " +
      "Turbopack panikasi bilan yiqiladi.",
  );
});

test("ro'yxatdagi kutubxonalar haqiqatan node moduli ishlatadi", () => {
  // Ro'yxat eskirsa test soxta xotirjamlik berardi.
  for (const kutubxona of ["@/lib/config", "@/lib/db"]) {
    const yol = path.join(ILDIZ, "lib", `${kutubxona.split("/").pop()}.ts`);
    assert.match(
      readFileSync(yol, "utf8"),
      /^import .*"node:/m,
      `${kutubxona} endi node moduli ishlatmaydi — ro'yxatni yangilang`,
    );
  }
});
