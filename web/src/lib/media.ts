import { dirname, extname, resolve } from "node:path";

import { bazaYoli } from "./env.ts";

/** Saytga yuklangan video fayllar.
 *
 * JILD BAZA FAYLI YONIDAN hisoblanadi, alohida muhit o'zgaruvchisi
 * yo'q. Sabab: Railway'da doimiy disk `RAILWAY_VOLUME_MOUNT_PATH` ga
 * ulanadi va baza o'sha yerga qo'yiladi (`bot/hosting.py`). Video ham
 * o'sha diskda bo'lishi shart — konteyner diski har yangilanishda
 * tozalanadi. Bazadan hisoblasak, disk ko'chganda ikkalasi BIRGA
 * ko'chadi va sozlamani ikki joyda yangilash kerak bo'lmaydi.
 *
 * Bazada esa TO'LIQ YO'L emas, faqat FAYL NOMI saqlanadi — shu sababdan.
 */
export function videoJildi(): string {
  return resolve(dirname(resolve(bazaYoli())), "video");
}

/** Brauzer o'ynata oladigan turlar. Ro'yxat ATAYLAB qisqa. */
const TURLAR: Record<string, string> = {
  ".mp4": "video/mp4",
  ".m4v": "video/mp4",
  ".webm": "video/webm",
  ".mov": "video/quicktime",
};

export function turiMaqbulmi(nom: string): boolean {
  return extname(nom).toLowerCase() in TURLAR;
}

export function mimeTuri(nom: string): string {
  return TURLAR[extname(nom).toLowerCase()] ?? "application/octet-stream";
}

export class MediaXatosi extends Error {}

/** Fayl nomidan xavfsiz to'liq yo'l yasaydi.
 *
 * NEGA IKKI QAVAT TEKSHIRUV: nom bazadan keladi, lekin u bir vaqtlar
 * so'rovdan kelgan. `../../etc/passwd` kabi nom qo'shilib qolsa, uni
 * o'qish butun serverni ochib qo'yardi. Shuning uchun avval nomning
 * o'zi tekshiriladi, keyin natija jild ichida ekani ALOHIDA
 * tasdiqlanadi — birinchisi o'tkazib yuborsa, ikkinchisi tutadi.
 */
export function videoYoli(nom: string): string {
  if (!nom || nom.includes("/") || nom.includes("\\") || nom.includes("\0")) {
    throw new MediaXatosi(`Fayl nomi noto'g'ri: ${nom}`);
  }
  const jild = videoJildi();
  const toliq = resolve(jild, nom);
  if (toliq !== resolve(jild, "./" + nom) || !toliq.startsWith(jild + "/")) {
    throw new MediaXatosi(`Fayl jilddan tashqarida: ${nom}`);
  }
  return toliq;
}

/** Yuklanadigan faylning eng katta hajmi (bayt). */
export function engKattaHajm(): number {
  const xom = process.env.VIDEO_MAX_MB?.trim();
  const mb = xom ? Number(xom) : 512;
  if (!Number.isFinite(mb) || mb <= 0) {
    throw new MediaXatosi(`VIDEO_MAX_MB noto'g'ri qiymat: ${xom}`);
  }
  return mb * 1024 * 1024;
}

/** Yangi fayl uchun takrorlanmaydigan nom.
 *
 * Asl nom ISHLATILMAYDI: unda bo'sh joy, kirill harflar yoki xavfli
 * belgilar bo'lishi mumkin. Kengaytma esa saqlanadi — brauzerga
 * qaysi turdaligini shu aytadi.
 */
export function yangiNom(aslNom: string, tasodif = crypto.randomUUID()): string {
  const kengaytma = extname(aslNom).toLowerCase();
  if (!(kengaytma in TURLAR)) {
    throw new MediaXatosi(
      `Bu turdagi fayl qo'llab-quvvatlanmaydi: ${kengaytma || aslNom}. ` +
        `Ruxsat etilgan: ${Object.keys(TURLAR).join(", ")}`,
    );
  }
  return `${tasodif}${kengaytma}`;
}

/** `Range: bytes=100-199` sarlavhasini o'qiydi.
 *
 * Qaytadi: `null` — sarlavha yo'q (butun fayl), `"yaroqsiz"` — noto'g'ri
 * so'ralgan (416), yoki aniq oraliq.
 *
 * Faqat BITTA oraliq qo'llab-quvvatlanadi. Ko'p oraliqli so'rov
 * (`bytes=0-99,200-299`) amalda video pleyerlardan kelmaydi, uni
 * qo'llab-quvvatlash esa `multipart/byteranges` javobini talab qiladi.
 */
export function oraliqniOqi(
  xom: string | null,
  hajm: number,
): { boshi: number; oxiri: number } | null | "yaroqsiz" {
  if (!xom) return null;
  const moslik = /^bytes=(\d*)-(\d*)$/.exec(xom.trim());
  if (!moslik) return "yaroqsiz";

  const [, boshMatn, oxirMatn] = moslik;
  if (boshMatn === "" && oxirMatn === "") return "yaroqsiz";

  // `bytes=-500` — OXIRGI 500 bayt, "0 dan 500 gacha" emas.
  if (boshMatn === "") {
    const nechta = Number(oxirMatn);
    if (nechta <= 0) return "yaroqsiz";
    return { boshi: Math.max(0, hajm - nechta), oxiri: hajm - 1 };
  }

  const boshi = Number(boshMatn);
  if (boshi >= hajm) return "yaroqsiz";
  const oxiri = oxirMatn === "" ? hajm - 1 : Math.min(Number(oxirMatn), hajm - 1);
  if (oxiri < boshi) return "yaroqsiz";
  return { boshi, oxiri };
}
