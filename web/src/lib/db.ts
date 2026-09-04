import { existsSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";

import { bazaYoli } from "./env.ts";

/** Botning bazasiga ulanish.
 *
 * Arxitektura qarori: sayt bot bilan BIR XIL SQLite faylini o'qiydi va
 * shu sababli bot bilan BIR XIL serverda (Railway) ishlaydi. Railway'da
 * doimiy disk faqat bitta xizmatga ulanadi — ya'ni saytni alohida
 * xizmatga qo'ysak, u faylni umuman ko'rmaydi.
 *
 * NIMA UCHUN `node:sqlite`, `better-sqlite3` EMAS:
 *
 * `better-sqlite3` — mahalliy (native) modul: ichida `.node` ikkilik
 * fayli bor. Serverda u bilan bog'liq har qanday nomuvofiqlik (bundler
 * ikkilik faylni ko'chirmasligi, Node ABI farqi, kutubxona versiyasi)
 * toza xato bermaydi — JARAYONNI O'LDIRADI. Tashqaridan bu 502 bo'lib
 * ko'rinadi: ilova xato qaytarmaydi, umuman javob bermaydi. Aynan shu
 * hol yuz berdi: bazaga tegmaydigan sahifalar 200 qaytardi, bazaga
 * tegadigan birinchi so'rov esa 502.
 *
 * `node:sqlite` — Node'ning O'ZIGA kirgan modul (22.5 dan beri).
 * Ikkilik fayl yo'q, qurish bosqichi yo'q, ABI mosligi masalasi yo'q.
 * Ya'ni muammoning butun sinfi yo'qoladi.
 *
 * DIQQAT: import ATAYLAB statik. Uni kechiktirishga urinildi
 * (`createRequire`, keyin oddiy `require`) — Turbopack ikkalasini ham
 * rad etadi: "Unsupported external type Url for commonjs reference".
 * Ya'ni Node versiyasi qurish MUHITIDA ham 22.5+ bo'lishi shart; bu
 * `nixpacks.toml` da `nodejs_24` bilan ta'minlanadi.
 *
 * Bot ulanishida WAL yoqilgan (`core/storage/database.py`), shuning uchun
 * o'qish yozishni bloklamaydi. `busy_timeout` — ikkinchi jarayon
 * yozayotgan lahzaga to'g'ri kelib qolsak, darhol xato bermay kutamiz.
 */

let ulanish: DatabaseSync | null = null;

export class BazaXatosi extends Error {}

export function db(): DatabaseSync {
  if (ulanish) return ulanish;

  const yol = bazaYoli();
  // Faylni O'ZIMIZ tekshiramiz: `node:sqlite` mavjud bo'lmagan faylni
  // jimgina YARATADI. Bo'sh bazada esa sayt "jadval yo'q" deb yiqilardi
  // va sabab — noto'g'ri yo'l ekani — ko'rinmay qolardi.
  if (!existsSync(yol)) {
    throw new BazaXatosi(
      `Baza fayli topilmadi: ${yol}. DATABASE_URL to'g'rimi va migratsiya ` +
        `(alembic upgrade head) o'tganmi — shuni tekshiring.`,
    );
  }

  const baza = new DatabaseSync(yol);
  baza.exec("PRAGMA busy_timeout = 5000");
  ulanish = baza;
  return baza;
}

/** SQLite'dagi vaqtni `Date` ga aylantiradi.
 *
 * Bot vaqtni DOIM UTC'da, `2026-08-20 02:27:28` ko'rinishida saqlaydi —
 * zona belgisisiz. `new Date(...)` bunday satrni MAHALLIY vaqt deb
 * o'qiydi, ya'ni O'zbekistonda 5 soatlik xato paydo bo'ladi. Shuning
 * uchun "Z" ni o'zimiz qo'shamiz.
 */
export function vaqt(xom: string | null | undefined): Date | null {
  if (!xom) return null;
  const tozalangan = xom.includes("T") ? xom : xom.replace(" ", "T");
  const zonali = /[Z+]|-\d\d:\d\d$/.test(tozalangan)
    ? tozalangan
    : `${tozalangan}Z`;
  const d = new Date(zonali);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** `Date` -> SQLite formati (bot o'qiy oladigan ko'rinishda). */
export function vaqtSatri(d: Date): string {
  return d
    .toISOString()
    .replace("T", " ")
    .replace(/\.\d+Z$/, "");
}

/** Oxirgi qo'shilgan qatorning id si.
 *
 * `node:sqlite` uni BigInt qilib qaytarishi mumkin — u JSON ga ham
 * tushmaydi, `Number` bilan taqqoslanmaydi ham. Shuning uchun bitta
 * joyda oddiy songa aylantiriladi.
 */
export function songaAylantir(x: unknown): number {
  return typeof x === "bigint" ? Number(x) : Number(x ?? 0);
}
