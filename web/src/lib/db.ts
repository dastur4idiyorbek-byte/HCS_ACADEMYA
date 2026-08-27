import Database from "better-sqlite3";

import { bazaYoli } from "./env.ts";

/** Botning bazasiga ulanish.
 *
 * Arxitektura qarori: sayt bot bilan BIR XIL SQLite faylini o'qiydi va
 * shu sababli bot bilan BIR XIL serverda (Railway) ishlaydi. Railway'da
 * doimiy disk faqat bitta xizmatga ulanadi — ya'ni saytni alohida
 * xizmatga (yoki Vercel'ga) qo'ysak, u faylni umuman ko'rmaydi.
 *
 * Bot ulanishida WAL yoqilgan (`core/storage/database.py`), shuning uchun
 * o'qish yozishni bloklamaydi. `busy_timeout` — ikkinchi jarayon yozayotgan
 * lahzaga to'g'ri kelib qolsak, darhol xato bermay 5 soniya kutamiz.
 */

let ulanish: Database.Database | null = null;

export function db(): Database.Database {
  if (ulanish) return ulanish;
  ulanish = new Database(bazaYoli(), { fileMustExist: true });
  ulanish.pragma("busy_timeout = 5000");
  return ulanish;
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
  const zonali = /[Z+]|-\d\d:\d\d$/.test(tozalangan) ? tozalangan : `${tozalangan}Z`;
  const d = new Date(zonali);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** `Date` -> SQLite formati (bot o'qiy oladigan ko'rinishda). */
export function vaqtSatri(d: Date): string {
  return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, "");
}
